from datetime import datetime, timedelta
import secrets
from fastapi import FastAPI, Depends, HTTPException, Form, Request, Header
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import select, or_, func, text
from .db import Base, engine, get_db
from .models import *
from .config import settings
from .security import validate_telegram_init_data

if settings.database_url.startswith("sqlite"):
    # Postgres (staging/production) is schema-managed exclusively by Alembic;
    # this only bootstraps the throwaway sqlite databases used by tests/local dev.
    Base.metadata.create_all(engine)
app=FastAPI(title=settings.app_name, version="10.0")
from .production_guard import validate_production
validate_production()
from .middleware.security_headers import SecurityHeaders
app.add_middleware(SecurityHeaders)
if settings.environment=="production":
    # Reject requests carrying a forged/unexpected Host header (cache
    # poisoning, absolute-URL confusion) instead of trusting whatever the
    # client sends. Derived from PUBLIC_BASE_URL, which production_guard()
    # above has already required to be set.
    from starlette.middleware.trustedhost import TrustedHostMiddleware
    from urllib.parse import urlparse
    _host = urlparse(settings.public_base_url).hostname
    if _host:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=[_host])
templates=Jinja2Templates(directory="app/templates")

def user(db, uid):
    u=db.get(User,uid)
    if not u: raise HTTPException(404,"Пользователь не найден")
    return u

def approved(u):
    if u.status!="APPROVED": raise HTTPException(403,"Доступ предоставляется только после одобрения администратора")

def blocked_pair(db,a,b):
    return db.execute(select(Block).where(or_(
        (Block.from_user_id==a)&(Block.to_user_id==b),
        (Block.from_user_id==b)&(Block.to_user_id==a)
    ))).scalar_one_or_none() is not None

@app.get("/",response_class=HTMLResponse)
def home(request:Request): return templates.TemplateResponse("index.html",{"request":request,"app_name":settings.app_name,"is_production":settings.environment=="production","bot_username":settings.telegram_bot_username})

@app.get("/admin",response_class=HTMLResponse)
def admin_page(request:Request): return templates.TemplateResponse("admin.html",{"request":request})

@app.get("/rules",response_class=HTMLResponse)
def rules(request:Request): return templates.TemplateResponse("rules.html",{"request":request,"version":settings.rules_version})

if settings.environment != "production":
    # Local/dev-only convenience endpoints that bypass real Telegram authentication.
    # Never registered in production - see the uid-path helpers below, which are
    # genuine IDOR (no session/ownership check) by construction and exist only so
    # this shortcut can drive them from a browser during local development.
    @app.post("/api/demo/register")
    def demo_register(alias:str=Form(...),age:int=Form(...),city:str=Form(...),profile_type:str=Form(...),looking_for:str=Form(...),about:str=Form(""),db:Session=Depends(get_db)):
        if age<18: raise HTTPException(403,"Только 18+")
        u=User(status="PROFILE_CREATED"); db.add(u); db.flush()
        db.add(Profile(user_id=u.id,alias=alias.strip(),age=age,city=city.strip(),profile_type=profile_type,looking_for=looking_for,about=about))
        db.add(Consent(user_id=u.id,kind="RULES_18_PLUS",version=settings.rules_version)); db.commit()
        return {"user_id":u.id,"status":u.status}

    @app.post("/api/users/{uid}/verification")
    def demo_start_verification(uid:int,db:Session=Depends(get_db)):
        return start_verification(uid,db)

    @app.get("/api/users/{uid}/catalog")
    def demo_catalog(uid:int,city:str|None=None,min_age:int=18,max_age:int=99,profile_type:str|None=None,db:Session=Depends(get_db)):
        return catalog(uid,city,min_age,max_age,profile_type,db)

    @app.post("/api/users/{uid}/like/{target}")
    def demo_like(uid:int,target:int,db:Session=Depends(get_db)):
        return like(uid,target,db)

    @app.delete("/api/users/{uid}")
    def demo_delete_account(uid:int,db:Session=Depends(get_db)):
        return delete_account(uid,db)

def start_verification(uid:int,db:Session=Depends(get_db)):
    u=user(db,uid)
    if u.status not in {"PROFILE_CREATED","REVISION_REQUIRED"}: raise HTTPException(409,"Недоступно для текущего статуса")
    code=f"{secrets.randbelow(10000):04d}"
    db.add(Verification(user_id=uid,code=code,status="PENDING"))
    u.status="VERIFICATION_PENDING"; db.commit()
    return {"code":code,"instruction":f"Отправьте боту фото или короткое видео, выполнив задание и показав код {code}."}

def catalog(uid:int,city:str|None=None,min_age:int=18,max_age:int=99,profile_type:str|None=None,db:Session=Depends(get_db)):
    me=user(db,uid); approved(me)
    rows=db.execute(select(User,Profile).join(Profile,Profile.user_id==User.id).where(
        User.status=="APPROVED",User.id!=uid,User.is_hidden==False,
        Profile.age>=max(18,min_age),Profile.age<=min(99,max_age)
    )).all()
    out=[]
    for u,p in rows:
        if blocked_pair(db,uid,u.id): continue
        if city and p.city.casefold()!=city.casefold(): continue
        if profile_type and p.profile_type.casefold()!=profile_type.casefold(): continue
        out.append({"user_id":u.id,"alias":p.alias,"age":p.age,"city":p.city,"profile_type":p.profile_type,"looking_for":p.looking_for,"about":p.about})
    return out

def like(uid:int,target:int,db:Session=Depends(get_db)):
    a=user(db,uid); b=user(db,target); approved(a); approved(b)
    if uid==target: raise HTTPException(400,"Нельзя поставить лайк себе")
    if blocked_pair(db,uid,target): raise HTTPException(403,"Взаимодействие недоступно")
    exists=db.execute(select(Like).where(Like.from_user_id==uid,Like.to_user_id==target)).scalar_one_or_none()
    if not exists: db.add(Like(from_user_id=uid,to_user_id=target)); db.flush()
    mutual=db.execute(select(Like).where(Like.from_user_id==target,Like.to_user_id==uid)).scalar_one_or_none() is not None
    if mutual:
        x,y=sorted((uid,target))
        if not db.execute(select(Match).where(Match.user1_id==x,Match.user2_id==y)).scalar_one_or_none():
            db.add(Match(user1_id=x,user2_id=y))
    db.commit(); return {"matched":mutual}

def matches(uid:int,db:Session=Depends(get_db)):
    me=user(db,uid); approved(me)
    ms=db.execute(select(Match).where(or_(Match.user1_id==uid,Match.user2_id==uid))).scalars().all()
    result=[]
    for m in ms:
        oid=m.user2_id if m.user1_id==uid else m.user1_id
        if blocked_pair(db,uid,oid): continue
        other=user(db,oid); p=db.execute(select(Profile).where(Profile.user_id==oid)).scalar_one_or_none()
        contact=None
        if me.contact_reveal and other.contact_reveal and other.telegram_username:
            contact="@"+other.telegram_username
        result.append({"user_id":oid,"alias":p.alias if p else "Участник","contact":contact})
    return result

def reveal(uid:int,value:bool=Form(...),db:Session=Depends(get_db)):
    u=user(db,uid); approved(u); u.contact_reveal=value; db.commit(); return {"value":value}

def visibility(uid:int,hidden:bool=Form(...),db:Session=Depends(get_db)):
    u=user(db,uid); approved(u); u.is_hidden=hidden; db.commit(); return {"hidden":hidden}

def block(uid:int,target:int,db:Session=Depends(get_db)):
    approved(user(db,uid)); user(db,target)
    if uid==target: raise HTTPException(400,"Нельзя заблокировать себя")
    if not blocked_pair(db,uid,target):
        db.add(Block(from_user_id=uid,to_user_id=target))
    db.commit(); return {"ok":True}

def complaint(uid:int,target:int,reason:str=Form(...),db:Session=Depends(get_db)):
    approved(user(db,uid)); user(db,target)
    if uid==target: raise HTTPException(400,"Некорректная жалоба")
    if len(reason.strip())<3: raise HTTPException(422,"Укажите причину")
    db.add(Complaint(from_user_id=uid,to_user_id=target,reason=reason.strip()))
    db.commit(); return {"ok":True}

def delete_account(uid:int,db:Session=Depends(get_db)):
    u=user(db,uid)
    from .services.object_storage import delete_object
    from .redis_store import revoke_all_sessions

    p=db.execute(select(Profile).where(Profile.user_id==uid)).scalar_one_or_none()
    if p:
        p.alias="Удалённый участник"; p.about=""; p.city=""; p.looking_for=""

    for photo in db.execute(select(ProfilePhoto).where(ProfilePhoto.user_id==uid)).scalars().all():
        if photo.storage_key:
            try:
                delete_object(photo.storage_key)
                photo.storage_key=None
            except Exception:
                pass  # object store unreachable: keep the key so the retention worker retries the real delete
        photo.status="REJECTED"; photo.approved=False

    for v in db.execute(select(Verification).where(Verification.user_id==uid)).scalars().all():
        _clear_verification_media(v)

    u.status="DELETED"; u.is_hidden=True; u.contact_reveal=False
    u.telegram_id=None; u.telegram_username=None
    revoke_all_sessions(uid)
    db.add(Audit(actor=f"user:{uid}",action="delete_account",target_user_id=uid))
    db.commit(); return {"status":"DELETED"}

def _clear_verification_media(v:Verification):
    """Delete the actual object-store object, not just the DB pointer to it."""
    if v.storage_key:
        try:
            from .services.object_storage import delete_object
            delete_object(v.storage_key)
        except Exception:
            return  # leave the pointer so the retention worker retries the real delete
        v.storage_key=None
    v.media_file_id=None

@app.get("/health")
def health(): return {"status":"ok","version":app.version}

@app.get("/club",response_class=HTMLResponse)
def club_page(request:Request): return templates.TemplateResponse("club.html",{"request":request})

from .auth_v6 import issue as v6_issue,current as v6_current,rate as v6_rate
from .redis_store import revoke_session as v6_revoke
from .services.object_storage import signed_profile_url

def _photo_urls(db:Session,uid:int):
    photos=db.execute(select(ProfilePhoto).where(ProfilePhoto.user_id==uid,ProfilePhoto.status=="APPROVED").order_by(ProfilePhoto.position)).scalars().all()
    out=[]
    for p in photos:
        if not p.storage_key: continue
        try: out.append(signed_profile_url(p.storage_key))
        except Exception: continue
    return out

@app.post("/api/v6/auth/telegram")
def v6_auth(init_data:str=Form(...),db:Session=Depends(get_db)):
    tg=validate_telegram_init_data(init_data); tid=int(tg["id"]); v6_rate(f"auth:{tid}",10,60)
    u=db.execute(select(User).where(User.telegram_id==tid)).scalar_one_or_none()
    if not u:
        u=User(telegram_id=tid,telegram_username=tg.get("username"),status="NEW"); db.add(u); db.commit(); db.refresh(u)
    return {"access_token":v6_issue(u.id),"token_type":"bearer","status":u.status,"role":u.role}
@app.post("/api/v6/logout")
def v6_logout(authorization:str|None=Header(None)):
    if authorization and authorization.startswith("Bearer "): v6_revoke(authorization[7:])
    return {"ok":True}
@app.get("/api/v6/me")
def v6_me(authorization:str|None=Header(None),db:Session=Depends(get_db)):
    u=v6_current(db,authorization)
    p=db.execute(select(Profile).where(Profile.user_id==u.id)).scalar_one_or_none()
    return {"id":u.id,"status":u.status,"role":u.role,"hidden":u.is_hidden,"contact_reveal":u.contact_reveal,
            "profile":({"alias":p.alias,"age":p.age,"city":p.city,"profile_type":p.profile_type,"looking_for":p.looking_for,"about":p.about} if p else None),
            "photos":_photo_urls(db,u.id)}
@app.post("/api/v6/profile")
def v6_create_profile(alias:str=Form(...),age:int=Form(...),city:str=Form(...),profile_type:str=Form(...),looking_for:str=Form(...),about:str=Form(""),authorization:str|None=Header(None),db:Session=Depends(get_db)):
    u=v6_current(db,authorization); v6_rate(f"profile:{u.id}",20,3600)
    if age<18: raise HTTPException(403,"Только 18+")
    if u.status not in {"NEW","AGE_CONFIRMED","REVISION_REQUIRED"}: raise HTTPException(409,"Недоступно для текущего статуса")
    existing=db.execute(select(Profile).where(Profile.user_id==u.id)).scalar_one_or_none()
    if existing:
        existing.alias=alias.strip();existing.age=age;existing.city=city.strip();existing.profile_type=profile_type;existing.looking_for=looking_for;existing.about=about
    else:
        db.add(Profile(user_id=u.id,alias=alias.strip(),age=age,city=city.strip(),profile_type=profile_type,looking_for=looking_for,about=about))
        db.add(Consent(user_id=u.id,kind="RULES_18_PLUS",version=settings.rules_version))
    u.status="PROFILE_CREATED"; db.commit()
    return {"status":u.status}
@app.post("/api/v6/verification")
def v6_start_verification(authorization:str|None=Header(None),db:Session=Depends(get_db)):
    u=v6_current(db,authorization); v6_rate(f"verification:{u.id}",10,3600); return start_verification(u.id,db)
@app.get("/api/v6/catalog")
def v6_catalog(city:str|None=None,min_age:int=18,max_age:int=99,authorization:str|None=Header(None),db:Session=Depends(get_db)):
    u=v6_current(db,authorization); approved(u); v6_rate(f"catalog:{u.id}",60,60)
    rows=catalog(u.id,city,min_age,max_age,None,db)
    for r in rows: r["photos"]=_photo_urls(db,r["user_id"])
    return rows
@app.post("/api/v6/like/{target}")
def v6_like(target:int,authorization:str|None=Header(None),db:Session=Depends(get_db)):
    u=v6_current(db,authorization); v6_rate(f"like:{u.id}",40,60); return like(u.id,target,db)
@app.get("/api/v6/matches")
def v6_matches(authorization:str|None=Header(None),db:Session=Depends(get_db)):
    u=v6_current(db,authorization); return matches(u.id,db)
@app.post("/api/v6/contact-reveal")
def v6_contact_reveal(value:bool=Form(...),authorization:str|None=Header(None),db:Session=Depends(get_db)):
    u=v6_current(db,authorization); return reveal(u.id,value,db)
@app.post("/api/v6/visibility")
def v6_visibility(hidden:bool=Form(...),authorization:str|None=Header(None),db:Session=Depends(get_db)):
    u=v6_current(db,authorization); return visibility(u.id,hidden,db)
@app.post("/api/v6/block/{target}")
def v6_block(target:int,authorization:str|None=Header(None),db:Session=Depends(get_db)):
    u=v6_current(db,authorization); return block(u.id,target,db)
@app.post("/api/v6/complaint/{target}")
def v6_complaint(target:int,reason:str=Form(...),authorization:str|None=Header(None),db:Session=Depends(get_db)):
    u=v6_current(db,authorization); v6_rate(f"complaint:{u.id}",10,3600); return complaint(u.id,target,reason,db)
@app.delete("/api/v6/me")
def v6_delete(authorization:str|None=Header(None),db:Session=Depends(get_db)):
    # delete_account() revokes every active session for this user (not just
    # the current one), so no separate v6_revoke() call is needed here.
    u=v6_current(db,authorization); return delete_account(u.id,db)

# ---- Staff API: Telegram allowlist + TOTP second factor + transactional outbox ----
# Staff sign-in is v8's TOTP-gated /api/v8/staff/auth/telegram only - there is no
# TOTP-less staff login path in production; day-to-day staff operations below just
# consume the session that login already issued.
import json as _json
from .staff_auth import login_staff as v7_staff_login,staff_current as v7_staff_current

@app.get("/api/v7/staff/pending")
def v7_staff_pending(authorization:str|None=Header(None),db:Session=Depends(get_db)):
    staff=v7_staff_current(db,authorization)
    rows=db.execute(select(User).where(User.status.in_(["ADMIN_REVIEW","VERIFICATION_PENDING"])).order_by(User.created_at)).scalars().all()
    result=[]
    for u in rows:
        p=db.execute(select(Profile).where(Profile.user_id==u.id)).scalar_one_or_none()
        v=db.execute(select(Verification).where(Verification.user_id==u.id).order_by(Verification.id.desc())).scalars().first()
        result.append({"id":u.id,"status":u.status,"risk_score":u.risk_score,
                       "profile":{"alias":p.alias,"age":p.age,"city":p.city,"profile_type":p.profile_type,"looking_for":p.looking_for,"about":p.about} if p else None,
                       "verification":{"id":v.id,"status":v.status,"media_type":v.media_type,"submitted":bool(v.storage_key)} if v else None})
    return result

@app.get("/api/v7/staff/verification/{vid}/media")
def v7_staff_verification_media(vid:int,authorization:str|None=Header(None),db:Session=Depends(get_db)):
    staff=v7_staff_current(db,authorization)
    v=db.get(Verification,vid)
    if not v or not v.storage_key: raise HTTPException(404,"Материал недоступен")
    from .services.object_storage import staff_signed_verification_url
    url=staff_signed_verification_url(v.storage_key)
    db.add(Audit(actor=f"staff:{staff.id}",action="view_verification_media",target_user_id=v.user_id,detail=f"verification={vid}"))
    db.commit()
    return {"url":url,"expires_in_seconds":300}

@app.get("/api/v7/staff/photos/pending")
def v7_staff_photos_pending(authorization:str|None=Header(None),db:Session=Depends(get_db)):
    v7_staff_current(db,authorization)
    rows=db.execute(select(ProfilePhoto).where(ProfilePhoto.status=="PENDING").order_by(ProfilePhoto.id)).scalars().all()
    out=[]
    for p in rows:
        url=None
        if p.storage_key:
            try: url=signed_profile_url(p.storage_key,minutes=5)
            except Exception: pass
        out.append({"id":p.id,"user_id":p.user_id,"url":url})
    return out

@app.post("/api/v7/staff/photos/{pid}/{decision}")
def v7_staff_photo_decision(pid:int,decision:str,authorization:str|None=Header(None),db:Session=Depends(get_db)):
    staff=v7_staff_current(db,authorization)
    if decision not in {"approve","reject"}: raise HTTPException(400,"Неизвестное решение")
    p=db.get(ProfilePhoto,pid)
    if not p: raise HTTPException(404,"Фото не найдено")
    p.status="APPROVED" if decision=="approve" else "REJECTED"
    p.approved = decision=="approve"
    db.add(Audit(actor=f"staff:{staff.id}",action=f"photo_{decision}",target_user_id=p.user_id,detail=f"photo={pid}"))
    db.commit()
    return {"id":pid,"status":p.status}

@app.post("/api/v7/staff/users/{uid}/{decision}")
def v7_staff_moderate(uid:int,decision:str,reason:str=Form(""),authorization:str|None=Header(None),db:Session=Depends(get_db)):
    staff=v7_staff_current(db,authorization)
    mapping={"approve":"APPROVED","reject":"REJECTED","revise":"REVISION_REQUIRED","suspend":"SUSPENDED","ban":"BANNED"}
    if decision not in mapping: raise HTTPException(400,"Неизвестное решение")
    if decision=="ban" and staff.role!="ADMIN": raise HTTPException(403,"Permanent ban requires ADMIN")
    u=user(db,uid);u.status=mapping[decision]
    if decision in {"ban","suspend"}:
        from .redis_store import revoke_all_sessions
        revoke_all_sessions(uid)
    v=db.execute(select(Verification).where(Verification.user_id==uid).order_by(Verification.id.desc())).scalars().first()
    if v:
        v.status={"approve":"APPROVED","reject":"REJECTED","revise":"REVISION_REQUIRED"}.get(decision,v.status)
        v.note=reason;v.reviewed_at=datetime.utcnow()
        if decision=="approve": _clear_verification_media(v)
    msg={"approve":"Ваша анкета одобрена. Доступ к закрытому каталогу открыт.",
          "revise":"Администратор запросил повторную верификацию.",
          "reject":"Заявка не одобрена.",
          "suspend":"Доступ временно ограничен.",
          "ban":"Доступ прекращён администрацией."}[decision]
    db.add(Outbox(kind="TELEGRAM",target_user_id=uid,payload=_json.dumps({"text":msg},ensure_ascii=False)))
    db.add(Audit(actor=f"staff:{staff.id}",action=decision,target_user_id=uid,detail=reason))
    db.commit()
    return {"id":uid,"status":u.status}

@app.get("/api/v7/staff/complaints")
def v7_staff_complaints(authorization:str|None=Header(None),db:Session=Depends(get_db)):
    v7_staff_current(db,authorization)
    return [{"id":c.id,"from":c.from_user_id,"to":c.to_user_id,"reason":c.reason,"status":c.status,"created_at":c.created_at.isoformat()}
            for c in db.execute(select(Complaint).order_by(Complaint.id.desc())).scalars()]

@app.post("/api/v7/staff/complaints/{cid}/close")
def v7_staff_close_complaint(cid:int,authorization:str|None=Header(None),db:Session=Depends(get_db)):
    staff=v7_staff_current(db,authorization)
    c=db.get(Complaint,cid)
    if not c: raise HTTPException(404,"Жалоба не найдена")
    c.status="CLOSED"; db.add(Audit(actor=f"staff:{staff.id}",action="close_complaint",target_user_id=c.to_user_id,detail=str(cid))); db.commit()
    return {"ok":True}

@app.get("/api/v7/staff/dashboard")
def v7_staff_dashboard(authorization:str|None=Header(None),db:Session=Depends(get_db)):
    v7_staff_current(db,authorization)
    counts={s:db.scalar(select(func.count()).select_from(User).where(User.status==s)) for s in ["ADMIN_REVIEW","APPROVED","SUSPENDED","BANNED"]}
    counts["OPEN_COMPLAINTS"]=db.scalar(select(func.count()).select_from(Complaint).where(Complaint.status=="OPEN"))
    counts["PENDING_PHOTOS"]=db.scalar(select(func.count()).select_from(ProfilePhoto).where(ProfilePhoto.status=="PENDING"))
    return counts

@app.post("/api/v7/staff/cleanup-verification")
def v7_staff_cleanup_verification(authorization:str|None=Header(None),db:Session=Depends(get_db)):
    staff=v7_staff_current(db,authorization)
    cutoff=datetime.utcnow()-timedelta(days=settings.verification_retention_days)
    rows=db.execute(select(Verification).where(Verification.created_at<cutoff).where(
        or_(Verification.media_file_id.is_not(None),Verification.storage_key.is_not(None)))).scalars().all()
    for v in rows: _clear_verification_media(v)
    if rows: db.add(Audit(actor=f"staff:{staff.id}",action="manual_verification_cleanup",detail=f"cleared={len(rows)}"))
    db.commit(); return {"cleared":len(rows)}

# ---- Staff sign-in: Telegram allowlist + TOTP second factor (v8) ----
from .staff_2fa import verify as v8_verify_totp
@app.post("/api/v8/staff/auth/telegram")
def v8_staff_auth(init_data:str=Form(...),totp_code:str=Form(...),db:Session=Depends(get_db)):
    tg=validate_telegram_init_data(init_data)
    v6_rate(f"staff-totp:{tg['id']}",5,300)
    v8_verify_totp(totp_code)
    return v7_staff_login(init_data,db)

@app.get("/ready")
def readiness():
    checks={"database":False,"redis":False}
    try:
        with engine.connect() as c: c.execute(text("SELECT 1")); checks["database"]=True
    except Exception: pass
    try:
        from .redis_store import r as _redis
        checks["redis"]=bool(_redis().ping())
    except Exception: pass
    if not all(checks.values()): raise HTTPException(503,detail=checks)
    return {"ready":True,"checks":checks}
