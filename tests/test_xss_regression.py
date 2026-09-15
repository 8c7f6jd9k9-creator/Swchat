"""Regression guard for a real stored-XSS finding: club.html and admin.html
build DOM via innerHTML template literals containing member-supplied text
(profile alias/about/city/looking_for/profile_type, complaint reason). Any
of those interpolated unescaped is stored XSS - in admin.html specifically,
XSS running inside a signed-in moderator's session.

Confirmed with Playwright during the fix: the same template-literal pattern
without esc() executed an injected onerror handler; with esc() it didn't
and the payload rendered as inert text. Playwright/a browser isn't part of
this project's normal dependencies, so that isn't re-run on every test
run - this is a fast, dependency-free static check that every known
dangerous interpolation site stays wrapped in esc(), so someone editing
these templates later can't silently drop the escaping.
"""
import re
from pathlib import Path

TEMPLATES = Path(__file__).parent.parent / "app" / "templates"


def _script_body(html: str) -> str:
    m = re.search(r"<script>(.*)</script>", html, re.DOTALL)
    assert m, "expected an inline <script> block"
    return m.group(1)


def test_esc_helper_is_defined_in_both_templates():
    for name in ["club.html", "admin.html"]:
        js = _script_body((TEMPLATES / name).read_text())
        assert "function esc(" in js, f"{name}: esc() helper missing"


def test_club_html_escapes_member_supplied_fields():
    js = _script_body((TEMPLATES / "club.html").read_text())
    for field in ["p.alias", "p.about", "p.city", "p.looking_for", "p.profile_type", "m.alias", "m.contact"]:
        assert f"esc({field})" in js, f"club.html: {field} interpolated without esc()"


def test_admin_html_escapes_member_supplied_fields():
    js = _script_body((TEMPLATES / "admin.html").read_text())
    for field in ["x.profile?.alias", "x.profile?.city", "x.profile?.profile_type", "x.profile?.about",
                  "x.status", "x.verification?.status", "c.status", "c.reason", "c.created_at"]:
        assert f"esc({field})" in js, f"admin.html: {field} interpolated without esc()"
