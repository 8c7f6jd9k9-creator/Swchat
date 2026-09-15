from datetime import datetime, timedelta
import secrets
from fastapi import FastAPI, Depends, HTTPException, Form, Request, Header
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import select, or_, func
from .db import Base, engine, get_db
from .models import *
from .config import settings
from .security import validate_telegram_init_data, require_admin_key

Base.metadata.create_all(engine)
app=FastAPI(title=settings.app_name, version="8.0")
from .production_guard import validate_production
validate_production()
from .middleware.security_headers import SecurityHeaders
app.add_middleware(SecurityHeaders)
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
def home(request:Request): return templates.TemplateResponse("index.html",{"request":request,"app_name":settings.app_name})

@app.get("/admin",response_class=HTMLResponse)
def admin_page(request:Request): return templates.TemplateResponse("admin.html",{"request":request})

@app.get("/rules",response_class=HTMLResponse)
def rules(request:Request): return templates.TemplateResponse("rules.html",{"request":request,"version":settings.rules_version})

@app.post("/api/auth/telegram")
def telegram_auth(init_data:str=Form(...),db:Session=Depends(get_db)):
    tg=validate_telegram_init_data(init_data)
    tid=int(tg["id"])
    u=db.execute(select(User).where(User.telegram_id==tid)).scalar_one_or_none()
    if not u:
        u=User(telegram_id=tid,telegram_username=tg.get("username"),status="NEW")
        db.add(u); db.commit(); db.refresh(u)
    return {"user_id":u.id,"status":u.status,"role":u.role}

@app.post("/api/demo/register")
def demo_register(alias:str=Form(...),age:int=Form(...),city:str=Form(...),profile_type:str=Form(...),looking_for:str=Form(...),about:str=Form(""),db:Session=Depends(get_db)):
    if age<18: raise HTTPException(403,"Только 18+")
    u=User(status="PROFILE_CREATED"); db.add(u); db.flush()
    db.add(Profile(user_id=u.id,alias=alias.strip(),age=age,city=city.strip(),profile_type=profile_type,looking_for=looking_for,about=about))
    db.add(Consent(user_id=u.id,kind="RULES_18_PLUS",version=settings.rules_version)); db.commit()
    return {"user_id":u.id,"status":u.status}

@app.post("/api/users/{uid}/verification")
def start_verification(uid:int,db:Session=Depends(get_db)):
    u=user(db,uid)
    if u.status not in {"PROFILE_CREATED","REVISION_REQUIRED"}: raise HTTPException(409,"Недоступно для текущего статуса")
    code=f"{secrets.randbelow(10000):04d}"
    db.add(Verification(user_id=uid,code=code,status="PENDING"))
    u.status="VERIFICATION_PENDING"; db.commit()
    return {"code":code,"instruction":f"Отправьте боту фото или короткое видео, выполнив задание и показав код {code}."}

@app.get("/api/users/{uid}/catalog")
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

@app.post("/api/users/{uid}/like/{target}")
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

@app.get("/api/users/{uid}/matches")
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

@app.post("/api/users/{uid}/contact-reveal")
def reveal(uid:int,value:bool=Form(...),db:Session=Depends(get_db)):
    u=user(db,uid); approved(u); u.contact_reveal=value; db.commit(); return {"value":value}

@app.post("/api/users/{uid}/visibility")
def visibility(uid:int,hidden:bool=Form(...),db:Session=Depends(get_db)):
    u=user(db,uid); approved(u); u.is_hidden=hidden; db.commit(); return {"hidden":hidden}

@app.post("/api/users/{uid}/block/{target}")
def block(uid:int,target:int,db:Session=Depends(get_db)):
    approved(user(db,uid)); user(db,target)
    if uid==target: raise HTTPException(400,"Нельзя заблокировать себя")
    if not blocked_pair(db,uid,target):
        db.add(Block(from_user_id=uid,to_user_id=target))
    db.commit(); return {"ok":True}

@app.post("/api/users/{uid}/complaint/{target}")
def complaint(uid:int,target:int,reason:str=Form(...),db:Session=Depends(get_db)):
    approved(user(db,uid)); user(db,target)
    if uid==target: raise HTTPException(400,"Некорректная жалоба")
    if len(reason.strip())<3: raise HTTPException(422,"Укажите причину")
    db.add(Complaint(from_user_id=uid,to_user_id=target,reason=reason.strip()))
    db.commit(); return {"ok":True}

@app.delete("/api/users/{uid}")
def delete_account(uid:int,db:Session=Depends(get_db)):
    u=user(db,uid); u.status="DELETED"; u.is_hidden=True; u.contact_reveal=False
    db.add(Audit(actor=f"user:{uid}",action="delete_account",target_user_id=uid))
    db.commit(); return {"status":"DELETED"}

@app.get("/api/admin/dashboard")
def dashboard(x_admin_key:str|None=Header(None),db:Session=Depends(get_db)):
    require_admin_key(x_admin_key)
    counts={s:db.scalar(select(func.count()).select_from(User).where(User.status==s)) for s in ["ADMIN_REVIEW","APPROVED","SUSPENDED","BANNED"]}
    counts["OPEN_COMPLAINTS"]=db.scalar(select(func.count()).select_from(Complaint).where(Complaint.status=="OPEN"))
    return counts

@app.get("/api/admin/pending")
def pending(x_admin_key:str|None=Header(None),db:Session=Depends(get_db)):
    require_admin_key(x_admin_key)
    rows=db.execute(select(User).where(User.status.in_(["ADMIN_REVIEW","VERIFICATION_PENDING"])).order_by(User.created_at)).scalars().all()
    result=[]
    for u in rows:
        p=db.execute(select(Profile).where(Profile.user_id==u.id)).scalar_one_or_none()
        v=db.execute(select(Verification).where(Verification.user_id==u.id).order_by(Verification.id.desc())).scalars().first()
        result.append({"id":u.id,"status":u.status,"risk_score":u.risk_score,
          "profile":({"alias":p.alias,"age":p.age,"city":p.city,"profile_type":p.profile_type,"looking_for":p.looking_for,"about":p.about} if p else None),
          "verification":({"id":v.id,"status":v.status,"media_type":v.media_type,"submitted":bool(v.media_file_id)} if v else None)})
    return result

@app.get("/api/admin/complaints")
def complaints(x_admin_key:str|None=Header(None),db:Session=Depends(get_db)):
    require_admin_key(x_admin_key)
    return [{"id":c.id,"from":c.from_user_id,"to":c.to_user_id,"reason":c.reason,"status":c.status,"created_at":c.created_at.isoformat()} for c in db.execute(select(Complaint).order_by(Complaint.id.desc())).scalars()]

@app.post("/api/admin/complaints/{cid}/close")
def close_complaint(cid:int,x_admin_key:str|None=Header(None),db:Session=Depends(get_db)):
    require_admin_key(x_admin_key); c=db.get(Complaint,cid)
    if not c: raise HTTPException(404,"Жалоба не найдена")
    c.status="CLOSED"; db.add(Audit(actor="admin",action="close_complaint",target_user_id=c.to_user_id,detail=str(cid))); db.commit()
    return {"ok":True}

@app.post("/api/admin/users/{uid}/{decision}")
def moderate(uid:int,decision:str,reason:str=Form(""),x_admin_key:str|None=Header(None),db:Session=Depends(get_db)):
    require_admin_key(x_admin_key); u=user(db,uid)
    mapping={"approve":"APPROVED","reject":"REJECTED","revise":"REVISION_REQUIRED","suspend":"SUSPENDED","ban":"BANNED"}
    if decision not in mapping: raise HTTPException(400,"Неизвестное решение")
    u.status=mapping[decision]
    v=db.execute(select(Verification).where(Verification.user_id==uid).order_by(Verification.id.desc())).scalars().first()
    if v:
        v.status={"approve":"APPROVED","reject":"REJECTED","revise":"REVISION_REQUIRED"}.get(decision,v.status)
        v.note=reason; v.reviewed_at=datetime.utcnow()
        if decision=="approve":
            v.media_file_id=None  # минимизация хранения после решения
    db.add(Audit(actor="admin",action=decision,target_user_id=uid,detail=reason)); db.commit()
    return {"id":uid,"status":u.status}

@app.post("/api/admin/cleanup-verification")
def cleanup_verification(x_admin_key:str|None=Header(None),db:Session=Depends(get_db)):
    require_admin_key(x_admin_key)
    cutoff=datetime.utcnow()-timedelta(days=settings.verification_retention_days)
    rows=db.execute(select(Verification).where(Verification.created_at<cutoff,Verification.media_file_id.is_not(None))).scalars().all()
    for v in rows: v.media_file_id=None
    db.commit(); return {"cleared":len(rows)}

@app.get("/health")
def health(): return {"status":"ok","version":"3.0"}


# ---- V4 authenticated API ----
from fastapi import Body
from .auth import issue_session, current_user, require_staff
from .rate_limit import check as rate_check

@app.post("/api/v4/auth/telegram")
def v4_auth(init_data:str=Form(...),db:Session=Depends(get_db)):
    tg=validate_telegram_init_data(init_data)
    tid=int(tg["id"]); rate_check(f"auth:{tid}",10,60)
    u=db.execute(select(User).where(User.telegram_id==tid)).scalar_one_or_none()
    if not u:
        u=User(telegram_id=tid,telegram_username=tg.get("username"),status="NEW")
        db.add(u); db.commit(); db.refresh(u)
    else:
        u.telegram_username=tg.get("username"); db.commit()
    return {"access_token":issue_session(u.id),"token_type":"bearer","status":u.status,"role":u.role}

@app.get("/api/v4/me")
def v4_me(authorization:str|None=Header(None),db:Session=Depends(get_db)):
    u=current_user(db,authorization)
    p=db.execute(select(Profile).where(Profile.user_id==u.id)).scalar_one_or_none()
    return {"id":u.id,"status":u.status,"role":u.role,"hidden":u.is_hidden,"contact_reveal":u.contact_reveal,
            "profile":({"alias":p.alias,"age":p.age,"city":p.city,"profile_type":p.profile_type,"looking_for":p.looking_for,"about":p.about} if p else None)}

@app.get("/api/v4/catalog")
def v4_catalog(city:str|None=None,min_age:int=18,max_age:int=99,authorization:str|None=Header(None),db:Session=Depends(get_db)):
    me=current_user(db,authorization); approved(me); rate_check(f"catalog:{me.id}",60,60)
    return catalog(me.id,city,min_age,max_age,None,db)

@app.post("/api/v4/like/{target}")
def v4_like(target:int,authorization:str|None=Header(None),db:Session=Depends(get_db)):
    me=current_user(db,authorization); rate_check(f"like:{me.id}",40,60)
    return like(me.id,target,db)

@app.get("/api/v4/matches")
def v4_matches(authorization:str|None=Header(None),db:Session=Depends(get_db)):
    me=current_user(db,authorization); return matches(me.id,db)

@app.post("/api/v4/block/{target}")
def v4_block(target:int,authorization:str|None=Header(None),db:Session=Depends(get_db)):
    me=current_user(db,authorization); return block(me.id,target,db)

@app.post("/api/v4/complaint/{target}")
def v4_complaint(target:int,reason:str=Form(...),authorization:str|None=Header(None),db:Session=Depends(get_db)):
    me=current_user(db,authorization); rate_check(f"complaint:{me.id}",10,3600)
    return complaint(me.id,target,reason,db)

@app.post("/api/v4/settings")
def v4_settings(hidden:bool=Form(False),contact_reveal:bool=Form(False),authorization:str|None=Header(None),db:Session=Depends(get_db)):
    me=current_user(db,authorization); approved(me)
    me.is_hidden=hidden; me.contact_reveal=contact_reveal; db.commit()
    return {"hidden":hidden,"contact_reveal":contact_reveal}

@app.delete("/api/v4/me")
def v4_delete(authorization:str|None=Header(None),db:Session=Depends(get_db)):
    me=current_user(db,authorization); return delete_account(me.id,db)

@app.get("/api/v4/staff/dashboard")
def v4_staff_dashboard(authorization:str|None=Header(None),db:Session=Depends(get_db)):
    staff=require_staff(db,authorization)
    counts={s:db.scalar(select(func.count()).select_from(User).where(User.status==s)) for s in ["ADMIN_REVIEW","APPROVED","SUSPENDED","BANNED"]}
    counts["OPEN_COMPLAINTS"]=db.scalar(select(func.count()).select_from(Complaint).where(Complaint.status=="OPEN"))
    return counts

@app.post("/api/v4/staff/users/{uid}/{decision}")
def v4_staff_moderate(uid:int,decision:str,reason:str=Form(""),authorization:str|None=Header(None),db:Session=Depends(get_db)):
    staff=require_staff(db,authorization)
    mapping={"approve":"APPROVED","reject":"REJECTED","revise":"REVISION_REQUIRED","suspend":"SUSPENDED","ban":"BANNED"}
    if decision not in mapping: raise HTTPException(400,"Неизвестное решение")
    if decision=="ban" and staff.role!="ADMIN": raise HTTPException(403,"Блокировка навсегда доступна только ADMIN")
    u=user(db,uid); u.status=mapping[decision]
    v=db.execute(select(Verification).where(Verification.user_id==uid).order_by(Verification.id.desc())).scalars().first()
    if v:
        v.status={"approve":"APPROVED","reject":"REJECTED","revise":"REVISION_REQUIRED"}.get(decision,v.status)
        v.note=reason; v.reviewed_at=datetime.utcnow()
        if decision=="approve": v.media_file_id=None
    db.add(Audit(actor=f"staff:{staff.id}",action=decision,target_user_id=uid,detail=reason)); db.commit()
    return {"id":uid,"status":u.status}

@app.get("/club",response_class=HTMLResponse)
def club_page(request:Request): return templates.TemplateResponse("club.html",{"request":request})

from .auth_v6 import issue as v6_issue,current as v6_current,rate as v6_rate
from .redis_store import revoke_session as v6_revoke
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
    u=v6_current(db,authorization); return {"id":u.id,"status":u.status,"role":u.role,"hidden":u.is_hidden}
@app.get("/api/v6/catalog")
def v6_catalog(city:str|None=None,min_age:int=18,max_age:int=99,authorization:str|None=Header(None),db:Session=Depends(get_db)):
    u=v6_current(db,authorization); approved(u); v6_rate(f"catalog:{u.id}",60,60); return catalog(u.id,city,min_age,max_age,None,db)
@app.post("/api/v6/like/{target}")
def v6_like(target:int,authorization:str|None=Header(None),db:Session=Depends(get_db)):
    u=v6_current(db,authorization); v6_rate(f"like:{u.id}",40,60); return like(u.id,target,db)
@app.get("/api/v6/matches")
def v6_matches(authorization:str|None=Header(None),db:Session=Depends(get_db)):
    u=v6_current(db,authorization); return matches(u.id,db)

# ---- V7 staff auth + transactional notification outbox ----
import json as _json
from .staff_auth import login_staff as v7_staff_login,staff_current as v7_staff_current

@app.post("/api/v7/staff/auth/telegram")
def v7_staff_auth(init_data:str=Form(...),db:Session=Depends(get_db)):
    return v7_staff_login(init_data,db)

@app.get("/api/v7/staff/pending")
def v7_staff_pending(authorization:str|None=Header(None),db:Session=Depends(get_db)):
    staff=v7_staff_current(db,authorization)
    rows=db.execute(select(User).where(User.status.in_(["ADMIN_REVIEW","VERIFICATION_PENDING"])).order_by(User.created_at)).scalars().all()
    result=[]
    for u in rows:
        p=db.execute(select(Profile).where(Profile.user_id==u.id)).scalar_one_or_none()
        v=db.execute(select(Verification).where(Verification.user_id==u.id).order_by(Verification.id.desc())).scalars().first()
        result.append({"id":u.id,"status":u.status,"profile":{"alias":p.alias,"age":p.age,"city":p.city,"profile_type":p.profile_type} if p else None,
                       "verification":{"status":v.status,"submitted":bool(v.media_file_id)} if v else None})
    return result

@app.post("/api/v7/staff/users/{uid}/{decision}")
def v7_staff_moderate(uid:int,decision:str,reason:str=Form(""),authorization:str|None=Header(None),db:Session=Depends(get_db)):
    staff=v7_staff_current(db,authorization)
    mapping={"approve":"APPROVED","reject":"REJECTED","revise":"REVISION_REQUIRED","suspend":"SUSPENDED","ban":"BANNED"}
    if decision not in mapping: raise HTTPException(400,"Неизвестное решение")
    if decision=="ban" and staff.role!="ADMIN": raise HTTPException(403,"Permanent ban requires ADMIN")
    u=user(db,uid);u.status=mapping[decision]
    v=db.execute(select(Verification).where(Verification.user_id==uid).order_by(Verification.id.desc())).scalars().first()
    if v:
        v.status={"approve":"APPROVED","reject":"REJECTED","revise":"REVISION_REQUIRED"}.get(decision,v.status)
        v.note=reason;v.reviewed_at=datetime.utcnow()
        if decision=="approve":v.media_file_id=None
    text={"approve":"Ваша анкета одобрена. Доступ к закрытому каталогу открыт.",
          "revise":"Администратор запросил повторную верификацию.",
          "reject":"Заявка не одобрена.",
          "suspend":"Доступ временно ограничен.",
          "ban":"Доступ прекращён администрацией."}[decision]
    db.add(Outbox(kind="TELEGRAM",target_user_id=uid,payload=_json.dumps({"text":text},ensure_ascii=False)))
    db.add(Audit(actor=f"staff:{staff.id}",action=decision,target_user_id=uid,detail=reason))
    db.commit()
    return {"id":uid,"status":u.status}

# ---- V8 staff second factor ----
from .staff_2fa import verify as v8_verify_totp
@app.post("/api/v8/staff/auth/telegram")
def v8_staff_auth(init_data:str=Form(...),totp_code:str=Form(...),db:Session=Depends(get_db)):
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
