import base64
import datetime as dt
import hashlib
import json
import os
import secrets
import sqlite3
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from nacl.signing import SigningKey, VerifyKey
from nacl.exceptions import BadSignatureError

DB_PATH = Path(__file__).with_name("licenses.db")

# Token expiry policy
_ttl_env = os.environ.get("LICENSE_TOKEN_TTL_SECONDS", "").strip()
try:
    _ttl_value = int(_ttl_env) if _ttl_env else 7 * 24 * 3600
except ValueError:
    _ttl_value = 7 * 24 * 3600
DEFAULT_EXP_SECONDS = _ttl_value if _ttl_value > 0 else None
SUBS_GRACE_SECONDS = int(os.environ.get("LICENSE_SUBS_GRACE_SECONDS", str(48 * 3600)))
_perpetual_verify_interval_env = os.environ.get("LICENSE_PERPETUAL_VERIFY_INTERVAL_SECONDS", "").strip()
try:
    _perpetual_verify_interval_value = (
        int(_perpetual_verify_interval_env) if _perpetual_verify_interval_env else 0
    )
except ValueError:
    _perpetual_verify_interval_value = 0
PERPETUAL_VERIFY_INTERVAL_SECONDS = (
    _perpetual_verify_interval_value if _perpetual_verify_interval_value > 0 else 0
)
_perpetual_grace_env = os.environ.get("LICENSE_PERPETUAL_GRACE_SECONDS", "").strip()
try:
    _perpetual_grace_value = int(_perpetual_grace_env) if _perpetual_grace_env else 72 * 3600
except ValueError:
    _perpetual_grace_value = 72 * 3600
PERPETUAL_GRACE_SECONDS = _perpetual_grace_value if _perpetual_grace_value > 0 else 72 * 3600
_default_sub_term_env = os.environ.get("LICENSE_SUBSCRIPTION_TERM_DAYS", "").strip()
try:
    _default_sub_term_days = int(_default_sub_term_env) if _default_sub_term_env else 30
except ValueError:
    _default_sub_term_days = 30
if _default_sub_term_days <= 0:
    _default_sub_term_days = 30
DEFAULT_SUBSCRIPTION_TERM_DAYS = _default_sub_term_days
DEFAULT_SUBSCRIPTION_TERM_SECONDS = DEFAULT_SUBSCRIPTION_TERM_DAYS * 24 * 3600
_verify_interval_env = os.environ.get("LICENSE_VERIFY_INTERVAL_SECONDS", "").strip()
try:
    _verify_interval_value = int(_verify_interval_env) if _verify_interval_env else 7 * 24 * 3600
except ValueError:
    _verify_interval_value = 7 * 24 * 3600
VERIFY_INTERVAL_SECONDS = _verify_interval_value if _verify_interval_value > 0 else 0

PERPETUAL_LICENSE_KINDS = {"perpetual", "lifetime", "forever"}
RENEWABLE_LICENSE_KINDS = {"subscription", "renewable", "term"}

@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Vox Stella Licensing", lifespan=lifespan)
raw_origins = os.environ.get("LICENSE_CORS_ORIGINS", "https://license.voxstella.app")
allow_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
if not allow_origins:
    allow_origins = ["https://license.voxstella.app"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"]
)

# Templates / static
TEMPLATES = Jinja2Templates(directory=str(Path(__file__).with_name("templates")))
def _fmt_ts(ts: int | None):
    try:
        ts = int(ts)
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))
    except Exception:
        return '—'
TEMPLATES.env.filters['dt'] = _fmt_ts
STATIC_DIR = Path(__file__).with_name("static")


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def canon_key(s: str) -> str:
    s = (s or '').strip().upper()
    return ''.join(ch for ch in s if ch.isalnum())  # remove hyphens/spaces

def fetch_license_by_key(conn: sqlite3.Connection, key_input: str):
    """Fetch license by exact key or hyphenless canonical form (case-insensitive)."""
    key_raw = (key_input or '').strip()
    key_canon = canon_key(key_raw)
    # Try exact
    row = conn.execute("select * from licenses where license_key=?", (key_raw,)).fetchone()
    if row:
        return row
    # Try uppercase exact
    row = conn.execute("select * from licenses where license_key=?", (key_raw.upper(),)).fetchone()
    if row:
        return row
    # Try hyphenless compare
    row = conn.execute("select * from licenses where replace(license_key,'-','')=?", (key_canon,)).fetchone()
    return row


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with db() as conn:
        conn.executescript(
            """
            create table if not exists licenses (
              license_key text primary key,
              plan text not null default 'pro',
              max_devices integer not null default 1,
              active integer not null default 1,
              issued_at integer not null,
              notes text
            );
            create table if not exists activations (
              id integer primary key autoincrement,
              license_key text not null,
              device_id text not null,
              activated_at integer not null,
              unique(license_key, device_id)
            );
            """
        )
        # Migrate: add owner_email if missing
        cols = {r[1] for r in conn.execute("pragma table_info(licenses)").fetchall()}
        if 'owner_email' not in cols:
            conn.execute("alter table licenses add column owner_email text")
        if 'last_seen' not in cols:
            conn.execute("alter table licenses add column last_seen integer")
        # Subscription model columns (manual entitlement management)
        if 'kind' not in cols:
            conn.execute("alter table licenses add column kind text default 'perpetual'")
        if 'status' not in cols:
            conn.execute("alter table licenses add column status text default 'active'")
        if 'current_period_end' not in cols:
            conn.execute("alter table licenses add column current_period_end integer")
        if 'cancel_at_period_end' not in cols:
            conn.execute("alter table licenses add column cancel_at_period_end integer")
        # Add last_activity to activations table
        a_cols = {r[1] for r in conn.execute("pragma table_info(activations)").fetchall()}
        if 'last_activity' not in a_cols:
            conn.execute("alter table activations add column last_activity integer")
        _backfill_subscription_period_end(conn)


def load_signing_key() -> SigningKey:
    key_b64 = (os.environ.get("LICENSE_PRIVATE_KEY_B64") or "").strip()
    if key_b64:
        try:
            seed = base64.b64decode(key_b64)
        except Exception as exc:
            raise RuntimeError("Invalid LICENSE_PRIVATE_KEY_B64 value") from exc
    else:
        key_file = (os.environ.get("LICENSE_PRIVATE_KEY_FILE") or "").strip()
        if not key_file:
            raise RuntimeError(
                "License signing key is not configured. Set LICENSE_PRIVATE_KEY_B64 or LICENSE_PRIVATE_KEY_FILE."
            )
        key_path = Path(key_file)
        if not key_path.exists():
            raise RuntimeError(f"Private key file not found: {key_path}")
        seed = key_path.read_bytes()
    if len(seed) != 32:
        raise RuntimeError("Invalid private key seed length")
    return SigningKey(seed)

def load_verify_key() -> VerifyKey:
    return load_signing_key().verify_key


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode('ascii')


def sign_payload(payload: dict) -> str:
    sk = load_signing_key()
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    sig = sk.sign(body).signature
    return f"{b64(sig)}.{b64(body)}"


def parse_and_verify_token(token: str) -> dict:
    """Decode token and verify Ed25519 signature, returning payload."""
    try:
        sig_b64, body_b64 = token.split(".")
        sig = base64.b64decode(sig_b64)
        body = base64.b64decode(body_b64)
        vk = load_verify_key()
        vk.verify(body, sig)
        payload = json.loads(body.decode("utf-8"))
    except (ValueError, BadSignatureError, json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=400, detail="invalid-token")
    except Exception:
        raise HTTPException(status_code=400, detail="invalid-token")

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="invalid-token")
    return payload


class ActivateReq(BaseModel):
    key: str
    deviceId: str
    email: Optional[str] = None


class RefreshReq(BaseModel):
    token: str
    deviceId: str


class DeactivateReq(BaseModel):
    token: Optional[str] = None
    key: Optional[str] = None
    deviceId: str


def count_devices(conn: sqlite3.Connection, key: str) -> int:
    row = conn.execute(
        """
        select count(*) as c
        from activations
        where replace(upper(license_key),'-','') = replace(upper(?),'-','')
        """,
        (key,),
    ).fetchone()
    return int(row[0]) if row else 0


def _is_device_activated(conn: sqlite3.Connection, key: str, device_id: str) -> bool:
    row = conn.execute(
        """
        select 1
        from activations
        where replace(upper(license_key),'-','') = replace(upper(?),'-','')
          and device_id=?
        """,
        (key, device_id),
    ).fetchone()
    return bool(row)


def normalize_license_kind(kind: str | None) -> str:
    normalized = (kind or "").strip().lower()
    if normalized in RENEWABLE_LICENSE_KINDS:
        return "subscription"
    return "perpetual"


def _parse_period_end_input(value: str | None) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.isdigit():
        parsed = int(text)
    else:
        parsed = int(
            dt.datetime.strptime(text, "%Y-%m-%d")
            .replace(hour=23, minute=59, second=59)
            .timestamp()
        )
    if parsed <= 0:
        raise ValueError("period-end-must-be-positive")
    return parsed


def _default_subscription_period_end(now: int, issued_at: int | None = None) -> int:
    base = int(issued_at or 0)
    if base <= 0:
        base = int(now)
    return base + DEFAULT_SUBSCRIPTION_TERM_SECONDS


def _resolve_admin_period_end(
    *,
    kind: str | None,
    raw_value: str | None,
    now: int,
    existing_period_end: int | None = None,
) -> int | None:
    try:
        parsed = _parse_period_end_input(raw_value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid-period-end") from exc

    if normalize_license_kind(kind) != "subscription":
        return None
    if parsed is not None:
        return parsed

    existing = int(existing_period_end or 0)
    if existing > 0:
        return existing
    return _default_subscription_period_end(now)


def _backfill_subscription_period_end(conn: sqlite3.Connection) -> None:
    fallback = int(time.time()) + DEFAULT_SUBSCRIPTION_TERM_SECONDS
    conn.execute(
        """
        update licenses
           set current_period_end = case
               when coalesce(issued_at, 0) > 0 then issued_at + ?
               else ?
           end
         where lower(coalesce(kind, 'perpetual')) in ('subscription', 'renewable', 'term')
           and coalesce(current_period_end, 0) <= 0
        """,
        (DEFAULT_SUBSCRIPTION_TERM_SECONDS, fallback),
    )


def kind_requires_entitlement_refresh(kind: str | None) -> bool:
    return _token_policy_for_kind(kind)["requires_entitlement_refresh"]


def _token_policy_for_kind(kind: str | None) -> dict[str, int | bool]:
    normalized_kind = normalize_license_kind(kind)
    if normalized_kind == "subscription":
        interval = VERIFY_INTERVAL_SECONDS
        grace = SUBS_GRACE_SECONDS
        return {
            "requires_entitlement_refresh": interval > 0,
            "interval_seconds": interval,
            "grace_seconds": grace,
        }
    if normalized_kind == "perpetual":
        interval = PERPETUAL_VERIFY_INTERVAL_SECONDS
        grace = PERPETUAL_GRACE_SECONDS
        return {
            "requires_entitlement_refresh": interval > 0,
            "interval_seconds": interval,
            "grace_seconds": grace,
        }
    return {
        "requires_entitlement_refresh": False,
        "interval_seconds": 0,
        "grace_seconds": 0,
    }


def _evaluate_license_state(lic, now: int) -> dict:
    if not lic or int(lic["active"]) != 1:
        return {"allowed": False, "reason": "license-inactive", "server_time": now}

    canonical_key = lic["license_key"]
    kind = normalize_license_kind(lic["kind"])
    status = (lic["status"] or "active").lower()
    period_end = int(lic["current_period_end"] or 0)
    result = {
        "allowed": True,
        "reason": "ok",
        "server_time": now,
        "license_key": canonical_key,
        "kind": kind,
        "status": status,
    }

    if kind == "subscription":
        result["current_period_end"] = period_end
        result["grace"] = SUBS_GRACE_SECONDS
        if status != "active":
            result.update({"allowed": False, "reason": "subscription-inactive"})
            return result
        if period_end <= 0:
            result.update({"allowed": False, "reason": "subscription-misconfigured"})
            return result
        if now > period_end + SUBS_GRACE_SECONDS:
            result.update({"allowed": False, "reason": "subscription-expired"})
            return result

    return result


def _evaluate_entitlement(conn: sqlite3.Connection, lic, device_id: str, now: int) -> dict:
    result = _evaluate_license_state(lic, now)
    if not result.get("allowed"):
        return result
    canonical_key = result["license_key"]
    if not _is_device_activated(conn, canonical_key, device_id):
        result.update({"allowed": False, "reason": "device-not-activated"})
        return result
    return result


def _build_signed_payload(
    *,
    subject: str,
    license_key: str,
    plan: str,
    license_kind: str,
    device_id: str,
    now: int,
) -> dict:
    normalized_kind = normalize_license_kind(license_kind)
    token_policy = _token_policy_for_kind(normalized_kind)
    requires_entitlement_refresh = bool(token_policy["requires_entitlement_refresh"])
    refresh_interval_seconds = int(token_policy["interval_seconds"])
    refresh_grace_seconds = int(token_policy["grace_seconds"])
    next_verify_at = None
    if requires_entitlement_refresh and refresh_interval_seconds > 0:
        next_verify_at = now + refresh_interval_seconds
    payload = {
        "sub": subject,
        "lic": license_key,
        "plan": plan,
        "kind": normalized_kind,
        "device": device_id,
        "iat": now,
        "verified_at": now,
        "requires_entitlement_refresh": requires_entitlement_refresh,
        "offline_capable": not requires_entitlement_refresh,
    }
    if next_verify_at is not None:
        payload["next_verify_at"] = next_verify_at
    if requires_entitlement_refresh and DEFAULT_EXP_SECONDS:
        renewable_ttl_seconds = DEFAULT_EXP_SECONDS
        minimum_ttl = (
            refresh_interval_seconds + refresh_grace_seconds
            if refresh_interval_seconds > 0
            else 0
        )
        if minimum_ttl > renewable_ttl_seconds:
            renewable_ttl_seconds = minimum_ttl
        payload["exp"] = now + renewable_ttl_seconds
    return payload


@app.post("/license/activate")
def activate(req: ActivateReq):
    now = int(time.time())
    with db() as conn:
        lic = fetch_license_by_key(conn, req.key)
        if not lic:
            raise HTTPException(status_code=400, detail="invalid-key")
        state = _evaluate_license_state(lic, now)
        if not state.get("allowed"):
            raise HTTPException(status_code=400, detail=state["reason"])
        canonical_key = state["license_key"]
        max_devices = int(lic["max_devices"]) or 1
        # Allow idempotent activation of same device; normalize any legacy key variant rows.
        existing = conn.execute(
            """
            select *
            from activations
            where replace(upper(license_key),'-','') = replace(upper(?),'-','')
              and device_id=?
            order by id desc
            limit 1
            """,
            (canonical_key, req.deviceId),
        ).fetchone()
        if not existing:
            if count_devices(conn, canonical_key) >= max_devices:
                raise HTTPException(status_code=409, detail="device-limit-reached")
            conn.execute(
                "insert into activations (license_key, device_id, activated_at, last_activity) values (?,?,?,?)",
                (canonical_key, req.deviceId, now, now),
            )
        else:
            conn.execute(
                "update activations set license_key=?, last_activity=? where id=?",
                (canonical_key, now, int(existing["id"])),
            )
            conn.execute(
                """
                delete from activations
                where id<>?
                  and replace(upper(license_key),'-','') = replace(upper(?),'-','')
                  and device_id=?
                """,
                (int(existing["id"]), canonical_key, req.deviceId),
            )
        # Update license last_seen
        conn.execute("update licenses set last_seen=? where license_key=?", (now, canonical_key))

        payload = _build_signed_payload(
            subject=req.email or canonical_key,
            license_key=canonical_key,
            plan=lic["plan"],
            license_kind=state["kind"],
            device_id=req.deviceId,
            now=now,
        )
        token = sign_payload(payload)
        return {"token": token}


@app.post("/license/refresh")
def refresh(req: RefreshReq):
    payload = parse_and_verify_token(req.token)

    key = payload.get("lic")
    device = req.deviceId

    with db() as conn:
        now = int(time.time())
        lic = fetch_license_by_key(conn, key)
        state = _evaluate_entitlement(conn, lic, device, now)
        if not state.get("allowed"):
            raise HTTPException(status_code=400, detail=state["reason"])
        canonical_key = state["license_key"]
        new_payload = _build_signed_payload(
            subject=payload.get("sub") or canonical_key,
            license_key=canonical_key,
            plan=lic["plan"],
            license_kind=state["kind"],
            device_id=device,
            now=now,
        )
        token = sign_payload(new_payload)
        # Bump last activity and last seen
        conn.execute(
            """
            update activations
            set license_key=?, last_activity=?
            where replace(upper(license_key),'-','') = replace(upper(?),'-','')
              and device_id=?
            """,
            (canonical_key, now, canonical_key, device),
        )
        conn.execute("update licenses set last_seen=? where license_key=?", (now, canonical_key))
        return {"token": token}


@app.post("/license/deactivate")
def deactivate(req: DeactivateReq):
    key = req.key
    if not key and req.token:
        payload = parse_and_verify_token(req.token)
        key = payload.get("lic")

    if not key:
        raise HTTPException(status_code=400, detail="missing-key")

    with db() as conn:
        lic = fetch_license_by_key(conn, key)
        if lic:
            key = lic["license_key"]
        conn.execute(
            """
            delete from activations
            where replace(upper(license_key),'-','') = replace(upper(?),'-','')
              and device_id=?
            """,
            (key, req.deviceId)
        )
    return {"ok": True}


class VerifyReq(BaseModel):
    token: str
    deviceId: str


@app.post("/license/verify")
def verify(req: VerifyReq):
    """Verify current entitlement for a device."""
    payload = parse_and_verify_token(req.token)

    key = payload.get("lic")
    token_device = payload.get("device")
    if not key or token_device != req.deviceId:
        raise HTTPException(status_code=400, detail="device-mismatch")

    now = int(time.time())
    with db() as conn:
        lic = fetch_license_by_key(conn, key)
        result = _evaluate_entitlement(conn, lic, req.deviceId, now)
        result.pop("license_key", None)
        return result


def load_admin_token():
    tok = os.environ.get("ADMIN_TOKEN")
    if tok and tok.strip():
        return tok.strip()
    token_file = (os.environ.get("ADMIN_TOKEN_FILE") or "").strip()
    if token_file:
        tf = Path(token_file)
        if tf.exists():
            try:
                v = tf.read_text(encoding='utf-8').strip()
                if v:
                    return v
            except Exception:
                pass
    return None


def _require_admin_token() -> str:
    token = load_admin_token()
    if not token:
        raise HTTPException(status_code=503, detail="admin-ui-disabled")
    return token


CSRF_COOKIE_NAME = "adm_csrf"

def require_admin(request: Request):
    admin_token = _require_admin_token()
    token = request.cookies.get('adm')
    if not token or not secrets.compare_digest(token, admin_token):
        raise HTTPException(status_code=401, detail="unauthorized")
    return True


def _is_secure_admin_cookie(request: Request) -> bool:
    remote_host = ""
    try:
        remote_host = (request.client.host or "").strip().lower() if request.client else ""
    except Exception:
        remote_host = ""
    cookie_secure = remote_host not in {"127.0.0.1", "::1", "localhost"}
    secure_override = (os.environ.get("ADMIN_COOKIE_SECURE") or "").strip().lower()
    if secure_override in {"1", "true", "yes"}:
        cookie_secure = True
    elif secure_override in {"0", "false", "no"}:
        cookie_secure = False
    return cookie_secure


def _issue_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def _set_csrf_cookie(response: Response, request: Request, token: str) -> None:
    response.set_cookie(
        CSRF_COOKIE_NAME,
        token,
        httponly=True,
        secure=_is_secure_admin_cookie(request),
        samesite='Strict',
        path='/',
        max_age=8 * 3600,
    )


def _request_origin_allowed(request: Request) -> bool:
    host = (request.headers.get("host") or "").strip().lower()
    if not host:
        return False
    candidate = request.headers.get("origin") or request.headers.get("referer")
    if not candidate:
        return False
    try:
        parsed = urlparse(candidate)
    except Exception:
        return False
    netloc = (parsed.netloc or "").strip().lower()
    if not netloc:
        return False
    return netloc == host


def _assert_csrf(request: Request, csrf_token: str) -> None:
    if not _request_origin_allowed(request):
        raise HTTPException(status_code=403, detail="csrf-origin-mismatch")
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME) or ""
    body_token = str(csrf_token or "")
    if not cookie_token or not body_token or not secrets.compare_digest(cookie_token, body_token):
        raise HTTPException(status_code=403, detail="csrf-token-invalid")


def require_admin_csrf(request: Request, csrf_token: str = Form(...)):
    require_admin(request)
    _assert_csrf(request, csrf_token)
    return True

@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request, _: bool = Depends(require_admin), q: str | None = None):
    with db() as conn:
        if q:
            like = f"%{q.strip()}%"
            rows = conn.execute(
                "select * from licenses where license_key like ? or ifnull(owner_email,'') like ? order by issued_at desc",
                (like, like)
            ).fetchall()
        else:
            rows = conn.execute("select * from licenses order by issued_at desc limit 200").fetchall()
    csrf_token = _issue_csrf_token()
    response = TEMPLATES.TemplateResponse("dashboard.html", {
        "request": request,
        "rows": rows,
        "q": q or "",
        "csrf_token": csrf_token,
        "default_subscription_term_days": DEFAULT_SUBSCRIPTION_TERM_DAYS,
    })
    _set_csrf_cookie(response, request, csrf_token)
    return response

@app.post("/admin/create")
def admin_create(request: Request,
                 count: int = Form(1),
                 plan: str = Form("pro"),
                 max_devices: int = Form(1),
                 owner_email: str = Form(""),
                 kind: str = Form("perpetual"),
                 status: str = Form("active"),
                 period_end: str = Form("") ,
                 _: bool = Depends(require_admin_csrf)):
    now = int(time.time())
    ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    def gen():
        return '-'.join(''.join(secrets.choice(ALPHABET) for _ in range(4)) for _ in range(4))
    with db() as conn:
        keys = []
        for _ in range(max(1, int(count))):
            k = gen()
            cpe = _resolve_admin_period_end(
                kind=kind,
                raw_value=period_end,
                now=now,
            )
            conn.execute(
                "insert or replace into licenses (license_key, plan, max_devices, active, issued_at, notes, owner_email, kind, status, current_period_end) values (?,?,?,?,?,?,?,?,?,?)",
                (k, plan, max_devices, 1, now, None, owner_email or None, normalize_license_kind(kind), (status or 'active'), cpe)
            )
            keys.append(k)
    return RedirectResponse(url=str(request.url_for('admin_dashboard')), status_code=302)

@app.get('/admin/license/{key}', response_class=HTMLResponse)
def admin_license_detail(request: Request, key: str, _: bool = Depends(require_admin)):
    with db() as conn:
        lic = conn.execute("select * from licenses where license_key=?", (key,)).fetchone()
        if not lic:
            raise HTTPException(status_code=404)
        acts = conn.execute("select * from activations where license_key=? order by activated_at desc", (key,)).fetchall()
    csrf_token = _issue_csrf_token()
    response = TEMPLATES.TemplateResponse("license_detail.html", {
        "request": request,
        "lic": lic,
        "acts": acts,
        "csrf_token": csrf_token,
        "default_subscription_term_days": DEFAULT_SUBSCRIPTION_TERM_DAYS,
    })
    _set_csrf_cookie(response, request, csrf_token)
    return response

@app.post('/admin/license/{key}/update')
def admin_update_license(request: Request,
                         key: str,
                         kind: str = Form("perpetual"),
                         status: str = Form("active"),
                         current_period_end: str = Form(""),
                         cancel_at_period_end: int = Form(0),
                         max_devices: int = Form(1),
                         plan: str = Form("pro"),
                         owner_email: str = Form("") ,
                         _: bool = Depends(require_admin_csrf)):
    now = int(time.time())
    with db() as conn:
        lic = conn.execute("select * from licenses where license_key=?", (key,)).fetchone()
        if not lic:
            raise HTTPException(status_code=404)
        cpe = _resolve_admin_period_end(
            kind=kind,
            raw_value=current_period_end,
            now=now,
            existing_period_end=lic["current_period_end"],
        )
        conn.execute(
            "update licenses set kind=?, status=?, current_period_end=?, cancel_at_period_end=?, max_devices=?, plan=?, owner_email=? where license_key=?",
            (normalize_license_kind(kind), status or 'active', cpe, int(cancel_at_period_end or 0), int(max_devices or 1), plan or 'pro', owner_email or None, key)
        )
    return RedirectResponse(url=str(request.url_for('admin_license_detail', key=key)), status_code=302)

@app.post('/admin/license/{key}/toggle')
def admin_toggle_license(request: Request, key: str, _: bool = Depends(require_admin_csrf)):
    with db() as conn:
        lic = conn.execute("select * from licenses where license_key=?", (key,)).fetchone()
        if not lic:
            raise HTTPException(status_code=404)
        new = 0 if int(lic['active']) == 1 else 1
        conn.execute("update licenses set active=? where license_key=?", (new, key))
    return RedirectResponse(url=str(request.url_for('admin_license_detail', key=key)), status_code=302)

@app.post('/admin/license/{key}/delete')
def admin_delete_license(request: Request, key: str, _: bool = Depends(require_admin_csrf)):
    with db() as conn:
        conn.execute("delete from activations where license_key=?", (key,))
        conn.execute("delete from licenses where license_key=?", (key,))
    return RedirectResponse(url=str(request.url_for('admin_dashboard')), status_code=302)

@app.post('/admin/license/{key}/deactivate-device')
def admin_deactivate_device(request: Request, key: str, deviceId: str = Form(...), _: bool = Depends(require_admin_csrf)):
    with db() as conn:
        conn.execute("delete from activations where license_key=? and device_id=?", (key, deviceId))
    return RedirectResponse(url=str(request.url_for('admin_license_detail', key=key)), status_code=302)

@app.get('/', response_class=HTMLResponse)
def index(request: Request):
    admin_enabled = load_admin_token() is not None
    admin_text = (
        "<p>Admin UI requires login. Go to <a href='/admin/login'>Admin Login</a> and paste your admin token.</p>"
        if admin_enabled
        else "<p>Admin UI is disabled until ADMIN_TOKEN or ADMIN_TOKEN_FILE is configured. Public /license/* endpoints remain available.</p>"
    )
    return HTMLResponse(f"""
    <html><body style='font-family:system-ui;color:#e6e7ee;background:#0b1020'>
    <div style='max-width:720px;margin:40px auto;padding:16px;border:1px solid #334;border-radius:12px;background:#11152b'>
    <h2>Vox Stella Licensing Server</h2>
    {admin_text}
    </div></body></html>
    """)

@app.get('/admin/login', response_class=HTMLResponse)
def admin_login_get(request: Request):
    if load_admin_token() is None:
        return HTMLResponse(
            "Admin UI is disabled until ADMIN_TOKEN or ADMIN_TOKEN_FILE is configured.",
            status_code=503,
        )
    csrf_token = _issue_csrf_token()
    response = HTMLResponse(f"""
    <html><body style='font-family:system-ui;color:#e6e7ee;background:#0b1020'>
    <div style='max-width:520px;margin:40px auto;padding:16px;border:1px solid #334;border-radius:12px;background:#11152b'>
    <h3>Admin Login</h3>
    <form method='post'>
      <input type='hidden' name='csrf_token' value='{csrf_token}' />
      <label>Token <input name='token' style='width:100%'/></label>
      <div style='margin-top:10px'><button type='submit'>Login</button></div>
    </form>
    </div></body></html>
    """)
    _set_csrf_cookie(response, request, csrf_token)
    return response

@app.post('/admin/login')
def admin_login_post(request: Request, token: str = Form(...), csrf_token: str = Form(...)):
    _assert_csrf(request, csrf_token)
    admin_token = load_admin_token()
    if admin_token is None:
        return HTMLResponse(
            "Admin UI is disabled until ADMIN_TOKEN or ADMIN_TOKEN_FILE is configured.",
            status_code=503,
        )
    if not secrets.compare_digest(token, admin_token):
        return HTMLResponse("Invalid token", status_code=401)

    resp = RedirectResponse(url='/admin', status_code=302)
    resp.set_cookie(
        'adm',
        token,
        httponly=True,
        secure=_is_secure_admin_cookie(request),
        samesite='Strict',
        path='/',
        max_age=8 * 3600,
    )
    return resp


@app.post('/admin/logout')
def admin_logout(request: Request, _: bool = Depends(require_admin_csrf)):
    resp = RedirectResponse(url='/admin/login', status_code=302)
    resp.delete_cookie('adm', path='/')
    resp.delete_cookie(CSRF_COOKIE_NAME, path='/')
    return resp

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8787"))
    uvicorn.run(app, host="127.0.0.1", port=port)
