import base64
import datetime as dt
import hashlib
import html
import ipaddress
import json
import os
import re
import secrets
import sqlite3
import threading
import time
from collections import OrderedDict, deque
from contextlib import asynccontextmanager
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request as UrlRequest, urlopen

from fastapi import FastAPI, HTTPException, Request, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from nacl.signing import SigningKey, VerifyKey
from nacl.exceptions import BadSignatureError

DB_PATH = Path(__file__).with_name("licenses.db")


def _load_local_env_files() -> None:
    try:
        from dotenv import load_dotenv
    except Exception:
        return
    for filename in (".env", "paypal.env"):
        env_path = DB_PATH.parent / filename
        if env_path.exists():
            load_dotenv(env_path, override=False)


_load_local_env_files()

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
LICENSE_KEY_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
PAYPAL_SUBSCRIPTION_EVENTS = {
    "BILLING.SUBSCRIPTION.CREATED",
    "BILLING.SUBSCRIPTION.ACTIVATED",
    "BILLING.SUBSCRIPTION.RE-ACTIVATED",
    "BILLING.SUBSCRIPTION.UPDATED",
    "BILLING.SUBSCRIPTION.CANCELLED",
    "BILLING.SUBSCRIPTION.SUSPENDED",
    "BILLING.SUBSCRIPTION.EXPIRED",
    "BILLING.SUBSCRIPTION.PAYMENT.FAILED",
    "PAYMENT.SALE.COMPLETED",
    "PAYMENT.SALE.REFUNDED",
    "PAYMENT.SALE.REVERSED",
}
PAYPAL_ONETIME_COMPLETED_EVENTS = {
    "PAYMENT.CAPTURE.COMPLETED",
}
PAYPAL_ONETIME_REVOKE_EVENTS = {
    "PAYMENT.CAPTURE.REFUNDED",
    "PAYMENT.CAPTURE.REVERSED",
    "PAYMENT.CAPTURE.DENIED",
    "PAYMENT.CAPTURE.DECLINED",
}
DEFAULT_PAYPAL_SUBSCRIPTION_PLAN_IDS = (
    "P-83N24493LW950963HNIIXO7Q",  # in-app $25 offer
    "P-4L214935JK8549417NIAB5KY",  # website $35 monthly plan
)
DEFAULT_PAYPAL_DESKTOP_CLIENT_ID = (
    "AU6EnBtp-2lZ9HuTzba9ozvumDNGsvmg6ECoAG4p1-XkR2zBh0k2wPgz4Fw_GrONEn_o6tEyKvrkzfxh"
)
DEFAULT_PAYPAL_DESKTOP_PLAN_ID = "P-83N24493LW950963HNIIXO7Q"
_PAYPAL_PUBLIC_CLIENT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{20,256}$")
_PAYPAL_PLAN_ID_RE = re.compile(r"^P-[A-Z0-9]{8,64}$")
_PAYPAL_SUBSCRIPTION_ID_RE = re.compile(r"^I-[A-Za-z0-9-]{3,127}$")
_PAYPAL_RESOURCE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,128}$")


def _bounded_positive_int_env(name: str, default: int, maximum: int) -> int:
    try:
        value = int((os.environ.get(name) or str(default)).strip())
    except ValueError:
        value = default
    return min(max(1, value), maximum)


RATE_LIMIT_WINDOW_SECONDS = _bounded_positive_int_env(
    "LICENSE_RATE_LIMIT_WINDOW_SECONDS",
    60,
    3600,
)
RATE_LIMIT_MAX_CLIENTS = _bounded_positive_int_env(
    "LICENSE_RATE_LIMIT_MAX_CLIENTS",
    4096,
    100_000,
)
PUBLIC_LICENSE_RATE_LIMIT_REQUESTS = _bounded_positive_int_env(
    "LICENSE_PUBLIC_RATE_LIMIT_REQUESTS",
    60,
    10_000,
)
PAYPAL_ACTIVATION_RATE_LIMIT_REQUESTS = _bounded_positive_int_env(
    "PAYPAL_ACTIVATION_RATE_LIMIT_REQUESTS",
    10,
    10_000,
)
PAYPAL_WEBHOOK_RATE_LIMIT_REQUESTS = _bounded_positive_int_env(
    "PAYPAL_WEBHOOK_RATE_LIMIT_REQUESTS",
    120,
    10_000,
)
PAYPAL_CHECKOUT_RATE_LIMIT_REQUESTS = _bounded_positive_int_env(
    "PAYPAL_CHECKOUT_RATE_LIMIT_REQUESTS",
    60,
    10_000,
)
ADMIN_LOGIN_RATE_LIMIT_REQUESTS = _bounded_positive_int_env(
    "ADMIN_LOGIN_RATE_LIMIT_REQUESTS",
    10,
    10_000,
)
TOKEN_FUTURE_SKEW_SECONDS = _bounded_positive_int_env(
    "LICENSE_TOKEN_FUTURE_SKEW_SECONDS",
    300,
    3600,
)


class _BoundedRateLimiter:
    """Small in-process sliding-window limiter with bounded client state."""

    def __init__(self, max_requests: int, window_seconds: int, max_clients: int):
        self.max_requests = max(1, int(max_requests))
        self.window_seconds = max(1, int(window_seconds))
        self.max_clients = max(1, int(max_clients))
        self._buckets: OrderedDict[str, deque[float]] = OrderedDict()
        self._lock = threading.Lock()

    def check(self, key: str, now: float | None = None) -> int | None:
        current = time.monotonic() if now is None else float(now)
        cutoff = current - self.window_seconds
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                while len(self._buckets) >= self.max_clients:
                    self._buckets.popitem(last=False)
                bucket = deque()
                self._buckets[key] = bucket
            else:
                self._buckets.move_to_end(key)

            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= self.max_requests:
                retry_after = max(1, int(bucket[0] + self.window_seconds - current) + 1)
                return retry_after
            bucket.append(current)
        return None


_PUBLIC_LICENSE_RATE_LIMITER = _BoundedRateLimiter(
    PUBLIC_LICENSE_RATE_LIMIT_REQUESTS,
    RATE_LIMIT_WINDOW_SECONDS,
    RATE_LIMIT_MAX_CLIENTS,
)
_PAYPAL_ACTIVATION_RATE_LIMITER = _BoundedRateLimiter(
    PAYPAL_ACTIVATION_RATE_LIMIT_REQUESTS,
    RATE_LIMIT_WINDOW_SECONDS,
    RATE_LIMIT_MAX_CLIENTS,
)
_PAYPAL_WEBHOOK_RATE_LIMITER = _BoundedRateLimiter(
    PAYPAL_WEBHOOK_RATE_LIMIT_REQUESTS,
    RATE_LIMIT_WINDOW_SECONDS,
    RATE_LIMIT_MAX_CLIENTS,
)
_PAYPAL_CHECKOUT_RATE_LIMITER = _BoundedRateLimiter(
    PAYPAL_CHECKOUT_RATE_LIMIT_REQUESTS,
    RATE_LIMIT_WINDOW_SECONDS,
    RATE_LIMIT_MAX_CLIENTS,
)
_ADMIN_LOGIN_RATE_LIMITER = _BoundedRateLimiter(
    ADMIN_LOGIN_RATE_LIMIT_REQUESTS,
    RATE_LIMIT_WINDOW_SECONDS,
    RATE_LIMIT_MAX_CLIENTS,
)


def _rate_limit_client_id(request: Request) -> str:
    peer = ""
    try:
        peer = (request.client.host or "").strip() if request.client else ""
    except Exception:
        peer = ""

    # The production server is loopback-bound behind Cloudflare Tunnel. Only in
    # that topology is CF-Connecting-IP accepted as the original peer.
    if peer in {"127.0.0.1", "::1", "localhost", "testclient"}:
        forwarded = (request.headers.get("CF-Connecting-IP") or "").strip()
        try:
            if forwarded:
                return str(ipaddress.ip_address(forwarded))
        except ValueError:
            pass
    return peer or "unknown"


_PAYPAL_OAUTH_LOCK = threading.Lock()
_PAYPAL_OAUTH_CACHE: dict[str, str | float | tuple[str, str, str] | None] = {
    "key": None,
    "token": None,
    "expires_at": 0.0,
}


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Vox Stella Licensing", lifespan=lifespan)
raw_origins = os.environ.get("LICENSE_CORS_ORIGINS", "https://license.voxstella.app")
allow_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
if not allow_origins:
    allow_origins = ["https://license.voxstella.app"]


@app.middleware("http")
async def bounded_rate_limit_middleware(request: Request, call_next):
    limiter = None
    method = request.method.upper()
    if method == "GET" and request.url.path == "/checkout/desktop-monthly":
        limiter = _PAYPAL_CHECKOUT_RATE_LIMITER
    elif method == "POST":
        path = request.url.path
        if path in {"/license/activate-paypal", "/license/activate-paypal-purchase"}:
            limiter = _PAYPAL_ACTIVATION_RATE_LIMITER
        elif path == "/paypal/webhook":
            limiter = _PAYPAL_WEBHOOK_RATE_LIMITER
        elif path == "/admin/login":
            limiter = _ADMIN_LOGIN_RATE_LIMITER
        elif path.startswith("/license/"):
            limiter = _PUBLIC_LICENSE_RATE_LIMITER

    if limiter is not None:
        retry_after = limiter.check(_rate_limit_client_id(request))
        if retry_after is not None:
            return JSONResponse(
                status_code=429,
                content={"detail": "rate-limit-exceeded"},
                headers={"Retry-After": str(retry_after)},
            )
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
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


def _begin_immediate_transaction(conn: sqlite3.Connection) -> None:
    """Acquire SQLite's write reservation before a read/modify/write decision."""
    if not conn.in_transaction:
        conn.execute("begin immediate")


def _migrate_duplicate_paypal_identity_ids(
    conn: sqlite3.Connection,
    *,
    column: str,
    resource_label: str,
    duplicate_status: str,
) -> None:
    """Retain one entitlement per PayPal identity and disable duplicate rows."""
    column_kinds = {
        "paypal_subscription_id": "subscription",
        "paypal_capture_id": "capture",
        "paypal_order_id": "order",
    }
    identity_kind = column_kinds.get(column)
    if identity_kind is None:
        raise ValueError("unsupported-paypal-identity-column")
    conn.execute(
        """
        update licenses
           set paypal_subscription_id=case
                 when ?='subscription'
                  and trim(paypal_subscription_id)=''
                 then null else paypal_subscription_id end,
               paypal_capture_id=case
                 when ?='capture' and trim(paypal_capture_id)=''
                 then null else paypal_capture_id end,
               paypal_order_id=case
                 when ?='order' and trim(paypal_order_id)=''
                 then null else paypal_order_id end
        """,
        (identity_kind, identity_kind, identity_kind),
    )
    duplicate_ids = [
        row["resource_id"]
        for row in conn.execute(
            """
            select case ?
                     when 'subscription' then paypal_subscription_id
                     when 'capture' then paypal_capture_id
                     when 'order' then paypal_order_id
                   end as resource_id
              from licenses
             where case ?
                     when 'subscription' then paypal_subscription_id
                     when 'capture' then paypal_capture_id
                     when 'order' then paypal_order_id
                   end is not null
             group by resource_id
            having count(*) > 1
            """,
            (identity_kind, identity_kind),
        ).fetchall()
    ]
    for resource_id in duplicate_ids:
        rows = conn.execute(
            """
            select *
              from licenses
             where case ?
                     when 'subscription' then paypal_subscription_id
                     when 'capture' then paypal_capture_id
                     when 'order' then paypal_order_id
                   end=?
             order by active desc, issued_at asc, license_key asc
            """,
            (identity_kind, resource_id),
        ).fetchall()
        winner = rows[0]
        for duplicate in rows[1:]:
            note = (
                f"Deactivated duplicate PayPal {resource_label} {resource_id}; "
                f"retained license {winner['license_key']}"
            )
            conn.execute(
                """
                update licenses
                   set active=0,
                       status='duplicate',
                       paypal_status=?,
                       paypal_subscription_id=case
                         when ?='subscription' then null
                         else paypal_subscription_id end,
                       paypal_capture_id=case
                         when ?='capture' then null
                         else paypal_capture_id end,
                       paypal_order_id=case
                         when ?='order' then null
                         else paypal_order_id end,
                       notes=case
                          when notes is null or trim(notes)='' then ?
                          else notes || char(10) || ?
                        end
                 where license_key=?
                """,
                (
                    duplicate_status,
                    identity_kind,
                    identity_kind,
                    identity_kind,
                    note,
                    note,
                    duplicate["license_key"],
                ),
            )
            conn.execute(
                "delete from activations where license_key=?",
                (duplicate["license_key"],),
            )


def _migrate_duplicate_paypal_order_ids(conn: sqlite3.Connection) -> None:
    _migrate_duplicate_paypal_identity_ids(
        conn,
        column="paypal_order_id",
        resource_label="order",
        duplicate_status="DUPLICATE_ORDER",
    )


def _persist_migrated_paypal_terminal_state(
    conn: sqlite3.Connection,
    *,
    resource_kind: str,
    resource_id: str,
    state_status: str,
    source_id: str,
    migration_time: int,
) -> None:
    conn.execute(
        """
        insert into paypal_resource_states (
          resource_kind, resource_id, state_time_us, state_status,
          state_rank, terminal, provisional, source_id, updated_at
        ) values (?, ?, 0, ?, 100, 1, 0, ?, ?)
        on conflict(resource_kind, resource_id) do update set
          state_time_us=max(
            paypal_resource_states.state_time_us,
            excluded.state_time_us
          ),
          state_status=excluded.state_status,
          state_rank=excluded.state_rank,
          terminal=1,
          provisional=0,
          source_id=excluded.source_id,
          updated_at=excluded.updated_at
        """,
        (
            resource_kind,
            resource_id,
            state_status,
            source_id,
            migration_time,
        ),
    )


def _backfill_paypal_resource_states(
    conn: sqlite3.Connection,
    migration_time: int,
) -> None:
    capture_rows = conn.execute(
        """
        select *
          from licenses
         where paypal_capture_id is not null
            or paypal_order_id is not null
        """
    ).fetchall()
    terminal_paypal_statuses = {
        *PAYPAL_ONETIME_REVOKE_EVENTS,
        "REFUNDED",
        "REVERSED",
        "DENIED",
        "DECLINED",
    }
    terminal_capture_ids: set[str] = set()
    terminal_order_ids: set[str] = set()
    for row in capture_rows:
        license_status = str(row["status"] or "").strip().lower()
        paypal_status = str(row["paypal_status"] or "").strip().upper()
        terminal = (
            license_status in {"refunded", "revoked"}
            or paypal_status in terminal_paypal_statuses
        )
        if not terminal:
            continue
        state_status = f"MIGRATED_TERMINAL:{paypal_status or license_status or 'UNKNOWN'}"
        for resource_kind, resource_id in (
            ("capture", str(row["paypal_capture_id"] or "").strip()),
            ("order", str(row["paypal_order_id"] or "").strip()),
        ):
            if not resource_id:
                continue
            _persist_migrated_paypal_terminal_state(
                conn,
                resource_kind=resource_kind,
                resource_id=resource_id,
                state_status=state_status,
                source_id="migration:terminal",
                migration_time=migration_time,
            )
            if resource_kind == "capture":
                terminal_capture_ids.add(resource_id)
            elif resource_kind == "order":
                terminal_order_ids.add(resource_id)

    terminal_capture_ids.update(
        str(row["resource_id"])
        for row in conn.execute(
            """
            select resource_id
              from paypal_resource_states
             where resource_kind='capture' and terminal=1
            """
        ).fetchall()
    )
    terminal_order_ids.update(
        str(row["resource_id"])
        for row in conn.execute(
            """
            select resource_id
              from paypal_resource_states
             where resource_kind='order' and terminal=1
            """
        ).fetchall()
    )
    seeded_capture_ids = set(terminal_capture_ids)
    seeded_order_ids = set(terminal_order_ids)
    while True:
        prior_size = len(terminal_capture_ids) + len(terminal_order_ids)
        for row in capture_rows:
            capture_id = str(row["paypal_capture_id"] or "").strip()
            order_id = str(row["paypal_order_id"] or "").strip()
            connected_to_terminal = (
                bool(capture_id and capture_id in terminal_capture_ids)
                or bool(order_id and order_id in terminal_order_ids)
            )
            if not connected_to_terminal:
                continue
            if capture_id:
                terminal_capture_ids.add(capture_id)
            if order_id:
                terminal_order_ids.add(order_id)
        if len(terminal_capture_ids) + len(terminal_order_ids) == prior_size:
            break

    closure_id_groups = (
        ("capture", terminal_capture_ids - seeded_capture_ids),
        ("order", terminal_order_ids - seeded_order_ids),
    )
    for resource_kind, resource_ids in closure_id_groups:
        for resource_id in resource_ids:
            _persist_migrated_paypal_terminal_state(
                conn,
                resource_kind=resource_kind,
                resource_id=resource_id,
                state_status="MIGRATED_TERMINAL:ALIAS_CLOSURE",
                source_id="migration:terminal-closure",
                migration_time=migration_time,
            )

    terminal_id_groups = (
        ("capture", terminal_capture_ids),
        ("order", terminal_order_ids),
    )
    for resource_kind, resource_ids in terminal_id_groups:
        for resource_id in resource_ids:
            active_rows = conn.execute(
                """
                select license_key from licenses
                where case ?
                        when 'capture' then paypal_capture_id
                        when 'order' then paypal_order_id
                      end=?
                  and active=1
                """,
                (resource_kind, resource_id),
            ).fetchall()
            for active_row in active_rows:
                conn.execute(
                    """
                    update licenses
                       set active=0,
                           status='refunded',
                           paypal_status=coalesce(
                             paypal_status,
                             'MIGRATED_TERMINAL_RESOURCE'
                           )
                     where license_key=?
                    """,
                    (active_row["license_key"],),
                )
                conn.execute(
                    "delete from activations where license_key=?",
                    (active_row["license_key"],),
                )

    subscription_rows = conn.execute(
        """
        select *
          from licenses
         where paypal_subscription_id is not null
        """
    ).fetchall()
    for row in subscription_rows:
        license_status = str(row["status"] or "").strip().lower()
        paypal_status = str(row["paypal_status"] or "").strip().upper()
        cancel_at_period_end = int(row["cancel_at_period_end"] or 0)
        restrictive = (
            int(row["active"] or 0) != 1
            or license_status != "active"
            or cancel_at_period_end == 1
            or paypal_status in {"CANCELLED", "SUSPENDED", "EXPIRED"}
        )
        if not restrictive:
            continue
        state_rank = 40 if license_status == "expired" else 30
        if license_status == "active" and cancel_at_period_end:
            state_rank = 20
        conn.execute(
            """
            insert into paypal_resource_states (
              resource_kind, resource_id, state_time_us, state_status,
              state_rank, terminal, provisional, source_id, updated_at
            ) values ('subscription', ?, 0, ?, ?, 0, 1, ?, ?)
            on conflict(resource_kind, resource_id) do nothing
            """,
            (
                str(row["paypal_subscription_id"]).strip(),
                f"MIGRATED:{paypal_status or license_status or 'UNKNOWN'}",
                state_rank,
                "migration:restrictive",
                migration_time,
            ),
        )


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
        if 'paypal_subscription_id' not in cols:
            conn.execute("alter table licenses add column paypal_subscription_id text")
        if 'paypal_plan_id' not in cols:
            conn.execute("alter table licenses add column paypal_plan_id text")
        if 'paypal_payer_id' not in cols:
            conn.execute("alter table licenses add column paypal_payer_id text")
        if 'paypal_status' not in cols:
            conn.execute("alter table licenses add column paypal_status text")
        if 'paypal_order_id' not in cols:
            conn.execute("alter table licenses add column paypal_order_id text")
        if 'paypal_capture_id' not in cols:
            conn.execute("alter table licenses add column paypal_capture_id text")
        # Add last_activity to activations table
        a_cols = {r[1] for r in conn.execute("pragma table_info(activations)").fetchall()}
        if 'last_activity' not in a_cols:
            conn.execute("alter table activations add column last_activity integer")
        conn.executescript(
            """
            create table if not exists paypal_events (
              event_id text primary key,
              event_type text not null,
              subscription_id text,
              processed_at integer not null,
              event_time_us integer,
              disposition text not null default 'claimed'
            );
            create table if not exists paypal_resource_states (
              resource_kind text not null,
              resource_id text not null,
              state_time_us integer not null,
              provider_status_time_us integer,
              provider_update_time_us integer,
              state_status text not null,
              state_rank integer not null,
              terminal integer not null default 0 check(terminal in (0, 1)),
              provisional integer not null default 0 check(provisional in (0, 1)),
              source_id text,
              updated_at integer not null,
              primary key(resource_kind, resource_id)
            );
            """
        )
        event_cols = {
            row[1]
            for row in conn.execute("pragma table_info(paypal_events)").fetchall()
        }
        if "event_time_us" not in event_cols:
            conn.execute("alter table paypal_events add column event_time_us integer")
        if "disposition" not in event_cols:
            conn.execute(
                "alter table paypal_events add column disposition text not null default 'claimed'"
            )
        state_cols = {
            row[1]
            for row in conn.execute(
                "pragma table_info(paypal_resource_states)"
            ).fetchall()
        }
        if "provider_status_time_us" not in state_cols:
            conn.execute(
                "alter table paypal_resource_states "
                "add column provider_status_time_us integer"
            )
        if "provider_update_time_us" not in state_cols:
            conn.execute(
                "alter table paypal_resource_states "
                "add column provider_update_time_us integer"
            )
        if "provisional" not in state_cols:
            conn.execute(
                "alter table paypal_resource_states "
                "add column provisional integer not null default 0"
            )
        _begin_immediate_transaction(conn)
        conn.execute(
            """
            update paypal_events
               set disposition='legacy_processed'
             where disposition is null or disposition='claimed'
            """
        )
        conn.execute(
            """
            update paypal_resource_states
               set provisional=1
            where terminal=0 and source_id='migration:restrictive'
            """
        )
        migration_time = int(time.time())
        _backfill_paypal_resource_states(conn, migration_time)
        _migrate_duplicate_paypal_identity_ids(
            conn,
            column="paypal_subscription_id",
            resource_label="subscription",
            duplicate_status="DUPLICATE_SUBSCRIPTION",
        )
        _migrate_duplicate_paypal_identity_ids(
            conn,
            column="paypal_capture_id",
            resource_label="capture",
            duplicate_status="DUPLICATE_CAPTURE",
        )
        _migrate_duplicate_paypal_order_ids(conn)
        _backfill_paypal_resource_states(conn, migration_time)
        paypal_unique_index_statements = (
            (
                "drop index if exists idx_licenses_paypal_subscription_id",
                """
                create unique index idx_licenses_paypal_subscription_id
                  on licenses(paypal_subscription_id)
                  where paypal_subscription_id is not null
                """,
            ),
            (
                "drop index if exists idx_licenses_paypal_capture_id",
                """
                create unique index idx_licenses_paypal_capture_id
                  on licenses(paypal_capture_id)
                  where paypal_capture_id is not null
                """,
            ),
            (
                "drop index if exists idx_licenses_paypal_order_id",
                """
                create unique index idx_licenses_paypal_order_id
                  on licenses(paypal_order_id)
                  where paypal_order_id is not null
                """,
            ),
        )
        for drop_statement, create_statement in paypal_unique_index_statements:
            conn.execute(drop_statement)
            conn.execute(create_statement)
        _backfill_subscription_period_end(conn)


def _generate_license_key() -> str:
    return '-'.join(
        ''.join(secrets.choice(LICENSE_KEY_ALPHABET) for _ in range(4))
        for _ in range(4)
    )


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


class PayPalActivateReq(BaseModel):
    subscriptionId: str
    deviceId: str
    email: Optional[str] = None


class PayPalPurchaseActivateReq(BaseModel):
    paypalId: str
    deviceId: str
    email: Optional[str] = None


class RefreshReq(BaseModel):
    token: str
    deviceId: str


class DeactivateReq(BaseModel):
    token: str
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
    if normalize_license_kind(kind) != "subscription":
        return None

    try:
        parsed = _parse_period_end_input(raw_value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid-period-end") from exc

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
        if now >= period_end + SUBS_GRACE_SECONDS:
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
    current_period_end: int | None = None,
) -> dict:
    normalized_kind = normalize_license_kind(license_kind)
    token_policy = _token_policy_for_kind(normalized_kind)
    requires_entitlement_refresh = bool(token_policy["requires_entitlement_refresh"])
    refresh_interval_seconds = int(token_policy["interval_seconds"])
    refresh_grace_seconds = int(token_policy["grace_seconds"])
    entitlement_deadline = None
    if normalized_kind == "subscription":
        paid_through = int(current_period_end or 0)
        if paid_through <= 0:
            raise RuntimeError("Subscription token requires a paid-through boundary")
        entitlement_deadline = paid_through + SUBS_GRACE_SECONDS
        if entitlement_deadline <= now:
            raise RuntimeError("Subscription entitlement boundary has expired")

    next_verify_at = None
    if requires_entitlement_refresh and refresh_interval_seconds > 0:
        next_verify_at = now + refresh_interval_seconds
        if entitlement_deadline is not None:
            next_verify_at = min(next_verify_at, entitlement_deadline)
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

    if normalized_kind == "subscription":
        if not requires_entitlement_refresh:
            payload["exp"] = int(entitlement_deadline or now)
        else:
            renewable_ttl_seconds = DEFAULT_EXP_SECONDS
            if renewable_ttl_seconds is None:
                renewable_ttl_seconds = max(1, int(entitlement_deadline or now) - now)
            minimum_ttl = refresh_interval_seconds + refresh_grace_seconds
            if minimum_ttl > renewable_ttl_seconds:
                renewable_ttl_seconds = minimum_ttl
            payload["exp"] = min(
                now + renewable_ttl_seconds,
                int(entitlement_deadline or now),
            )
    elif requires_entitlement_refresh and DEFAULT_EXP_SECONDS:
        renewable_ttl_seconds = max(
            DEFAULT_EXP_SECONDS,
            refresh_interval_seconds + refresh_grace_seconds,
        )
        payload["exp"] = now + renewable_ttl_seconds
    return payload


def _validate_refresh_token(payload: dict, requested_device: str, now: int) -> tuple[str, str]:
    key = payload.get("lic")
    token_device = payload.get("device")
    if not isinstance(key, str) or not key.strip():
        raise HTTPException(status_code=400, detail="invalid-token")
    if not isinstance(token_device, str) or not token_device:
        raise HTTPException(status_code=400, detail="invalid-token")
    if not isinstance(requested_device, str) or not requested_device:
        raise HTTPException(status_code=400, detail="missing-device-id")
    if not secrets.compare_digest(token_device, requested_device):
        raise HTTPException(status_code=400, detail="device-mismatch")

    issued_at = payload.get("iat")
    if isinstance(issued_at, bool):
        raise HTTPException(status_code=400, detail="invalid-token")
    try:
        issued_at_int = int(issued_at)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="invalid-token")
    if issued_at_int <= 0 or issued_at_int > now + TOKEN_FUTURE_SKEW_SECONDS:
        raise HTTPException(status_code=400, detail="invalid-token")

    expires_at = payload.get("exp")
    if expires_at is not None:
        if isinstance(expires_at, bool):
            raise HTTPException(status_code=400, detail="invalid-token")
        try:
            expires_at_int = int(expires_at)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="invalid-token")
        if expires_at_int <= 0 or expires_at_int < issued_at_int:
            raise HTTPException(status_code=400, detail="invalid-token")
        # Expiry bounds offline use. Refresh intentionally permits recovery
        # after expiry only because the database entitlement and exact device
        # activation are authoritatively revalidated below.

    return key.strip(), requested_device


def _activate_license_row(conn: sqlite3.Connection, lic, device_id: str, now: int) -> dict:
    _begin_immediate_transaction(conn)
    state = _evaluate_license_state(lic, now)
    if not state.get("allowed"):
        raise HTTPException(status_code=400, detail=state["reason"])
    canonical_key = state["license_key"]
    max_devices = int(lic["max_devices"]) or 1
    existing = conn.execute(
        """
        select *
        from activations
        where replace(upper(license_key),'-','') = replace(upper(?),'-','')
          and device_id=?
        order by id desc
        limit 1
        """,
        (canonical_key, device_id),
    ).fetchone()
    if not existing:
        if count_devices(conn, canonical_key) >= max_devices:
            raise HTTPException(status_code=409, detail="device-limit-reached")
        conn.execute(
            "insert into activations (license_key, device_id, activated_at, last_activity) values (?,?,?,?)",
            (canonical_key, device_id, now, now),
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
            (int(existing["id"]), canonical_key, device_id),
        )
    conn.execute("update licenses set last_seen=? where license_key=?", (now, canonical_key))
    return state


def _paypal_api_base() -> str:
    raw_base = (
        os.environ.get("PAYPAL_API_BASE") or "https://api-m.paypal.com"
    ).strip().rstrip("/")
    parsed = urlparse(raw_base)
    allowed_hosts = {
        "api-m.paypal.com",
        "api-m.sandbox.paypal.com",
    }
    try:
        parsed_port = parsed.port
    except ValueError:
        parsed_port = -1
    if (
        parsed.scheme.lower() != "https"
        or parsed.hostname not in allowed_hosts
        or parsed.username is not None
        or parsed.password is not None
        or parsed_port not in (None, 443)
        or parsed.path not in ("", "/")
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise HTTPException(
            status_code=503,
            detail="paypal-api-base-invalid",
        )
    return f"https://{parsed.hostname}"


def _paypal_expected_plan_id() -> str:
    return (os.environ.get("PAYPAL_PLAN_ID") or os.environ.get("PAYPAL_SUBSCRIPTION_PLAN_ID") or "").strip()


def _split_env_csv(value: str | None) -> list[str]:
    return [part.strip() for part in str(value or "").split(",") if part.strip()]


def _paypal_allowed_plan_ids() -> set[str]:
    ids: list[str] = []
    ids.extend(_split_env_csv(os.environ.get("PAYPAL_ALLOWED_PLAN_IDS")))
    ids.extend(_split_env_csv(os.environ.get("PAYPAL_PLAN_IDS")))
    legacy_plan_id = _paypal_expected_plan_id()
    if legacy_plan_id:
        ids.append(legacy_plan_id)
    ids.extend(DEFAULT_PAYPAL_SUBSCRIPTION_PLAN_IDS)
    return {plan_id for plan_id in ids if plan_id}


def _paypal_desktop_checkout_config() -> tuple[str, str]:
    client_id = (
        os.environ.get("PAYPAL_DESKTOP_CLIENT_ID")
        or DEFAULT_PAYPAL_DESKTOP_CLIENT_ID
    ).strip()
    plan_id = (
        os.environ.get("PAYPAL_DESKTOP_PLAN_ID")
        or _paypal_expected_plan_id()
        or DEFAULT_PAYPAL_DESKTOP_PLAN_ID
    ).strip().upper()
    if not _PAYPAL_PUBLIC_CLIENT_ID_RE.fullmatch(client_id):
        raise HTTPException(status_code=503, detail="paypal-checkout-client-id-invalid")
    if not _PAYPAL_PLAN_ID_RE.fullmatch(plan_id):
        raise HTTPException(status_code=503, detail="paypal-checkout-plan-id-invalid")
    if plan_id not in _paypal_allowed_plan_ids():
        raise HTTPException(status_code=503, detail="paypal-checkout-plan-not-allowed")
    return client_id, plan_id


def _render_paypal_desktop_checkout(client_id: str, plan_id: str, nonce: str) -> str:
    sdk_query = urlencode(
        {
            "client-id": client_id,
            "vault": "true",
            "intent": "subscription",
            "components": "buttons",
        }
    )
    sdk_url = html.escape(
        f"https://www.paypal.com/sdk/js?{sdk_query}",
        quote=True,
    )
    safe_plan_id = html.escape(plan_id, quote=True)
    safe_nonce = html.escape(nonce, quote=True)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Vox Stella Premium checkout</title>
  <style nonce="{safe_nonce}">
    :root {{ color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; min-height: 100vh; background: #f5f3ee; color: #18181b; }}
    main {{ width: min(680px, calc(100% - 32px)); margin: 48px auto; padding: 32px;
      border: 1px solid #d6d3d1; border-radius: 18px; background: #fff; box-shadow: 0 24px 64px #1c19170f; }}
    h1, h2 {{ margin: 0 0 12px; letter-spacing: -.02em; }}
    p {{ color: #57534e; line-height: 1.6; }}
    .eyebrow {{ color: #7c3aed; font-size: 12px; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }}
    #paypal-button-container {{ min-height: 48px; margin-top: 24px; }}
    .result {{ display: none; margin-top: 24px; padding: 22px; border: 2px solid #059669;
      border-radius: 14px; background: #ecfdf5; }}
    .result.visible {{ display: block; }}
    .id-row {{ display: flex; gap: 10px; margin-top: 14px; }}
    input {{ min-width: 0; flex: 1; padding: 12px; border: 1px solid #6ee7b7; border-radius: 9px;
      background: #fff; color: #064e3b; font: 700 17px ui-monospace, SFMono-Regular, Menlo, monospace; }}
    button {{ padding: 11px 16px; border: 0; border-radius: 9px; background: #047857; color: #fff;
      font-weight: 800; cursor: pointer; }}
    .status {{ min-height: 24px; margin-top: 12px; color: #57534e; }}
    .error {{ color: #b91c1c; }}
    @media (max-width: 560px) {{ main {{ margin: 20px auto; padding: 22px; }} .id-row {{ flex-direction: column; }} }}
  </style>
</head>
<body>
  <main>
    <p class="eyebrow">Vox Stella Premium</p>
    <h1>Complete your monthly subscription</h1>
    <p>Pay securely with PayPal. After approval, copy the subscription ID shown here and paste it into Vox Stella to activate this device.</p>
    <div id="checkout-config" data-plan-id="{safe_plan_id}">
      <div id="paypal-button-container" aria-label="PayPal subscription checkout"></div>
    </div>
    <p id="checkout-status" class="status" role="status" aria-live="polite">Loading secure PayPal checkout…</p>
    <section id="subscription-result" class="result" aria-labelledby="result-title">
      <h2 id="result-title">Subscription approved</h2>
      <p>Copy this PayPal subscription ID, return to Vox Stella, and paste it into the activation field.</p>
      <div class="id-row">
        <input id="subscription-id" type="text" readonly aria-label="PayPal subscription ID">
        <button id="copy-subscription-id" type="button">Copy ID</button>
      </div>
      <p id="copy-status" class="status" role="status" aria-live="polite"></p>
    </section>
  </main>
  <script nonce="{safe_nonce}" data-csp-nonce="{safe_nonce}" src="{sdk_url}"></script>
  <script nonce="{safe_nonce}">
    (() => {{
      'use strict';
      const config = document.getElementById('checkout-config');
      const status = document.getElementById('checkout-status');
      const result = document.getElementById('subscription-result');
      const idField = document.getElementById('subscription-id');
      const copyButton = document.getElementById('copy-subscription-id');
      const copyStatus = document.getElementById('copy-status');
      const planId = config.dataset.planId;

      const showError = (message) => {{
        status.textContent = message;
        status.classList.add('error');
      }};

      if (!window.paypal || typeof window.paypal.Buttons !== 'function') {{
        showError('PayPal checkout could not load. Refresh the page or try again later.');
        return;
      }}

      try {{
        const buttons = window.paypal.Buttons({{
          style: {{ shape: 'rect', color: 'gold', layout: 'vertical', label: 'subscribe' }},
          createSubscription: (_data, actions) => actions.subscription.create({{ plan_id: planId }}),
          onApprove: (data) => {{
            const subscriptionId = String(data && data.subscriptionID || '').trim();
            if (!/^I-[A-Z0-9-]{{3,127}}$/i.test(subscriptionId)) {{
              showError('PayPal approved the checkout but did not return a valid subscription ID. Contact support with your PayPal receipt.');
              return;
            }}
            idField.value = subscriptionId;
            result.classList.add('visible');
            status.textContent = 'Payment approved. Copy the subscription ID below.';
            status.classList.remove('error');
            idField.focus();
            idField.select();
          }},
          onCancel: () => {{ status.textContent = 'Checkout cancelled. No activation was performed.'; }},
          onError: () => showError('PayPal checkout failed. No activation was performed.'),
        }});
        Promise.resolve(buttons.render('#paypal-button-container'))
          .then(() => {{ status.textContent = 'PayPal checkout is ready.'; }})
          .catch(() => showError('PayPal checkout could not be rendered.'));
      }} catch (_error) {{
        showError('PayPal checkout could not be initialized.');
      }}

      copyButton.addEventListener('click', async () => {{
        if (!idField.value) return;
        try {{
          await navigator.clipboard.writeText(idField.value);
          copyStatus.textContent = 'Subscription ID copied. Return to Vox Stella to activate.';
        }} catch (_error) {{
          idField.focus();
          idField.select();
          copyStatus.textContent = 'Select the ID and copy it manually, then return to Vox Stella.';
        }}
      }});
    }})();
  </script>
</body>
</html>"""


@app.get("/checkout/desktop-monthly", response_class=HTMLResponse)
def paypal_desktop_checkout():
    client_id, plan_id = _paypal_desktop_checkout_config()
    nonce = base64.b64encode(secrets.token_bytes(18)).decode("ascii")
    paypal_origins = (
        "https://www.paypal.com https://*.paypal.com "
        "https://www.paypalobjects.com https://*.paypalobjects.com "
        "https://*.venmo.com"
    )
    csp = "; ".join(
        (
            "default-src 'none'",
            "base-uri 'none'",
            "object-src 'none'",
            "frame-ancestors 'none'",
            "form-action 'none'",
            f"script-src 'nonce-{nonce}' {paypal_origins}",
            f"style-src 'nonce-{nonce}' {paypal_origins}",
            f"img-src data: {paypal_origins}",
            f"connect-src {paypal_origins}",
            f"child-src {paypal_origins}",
            f"frame-src {paypal_origins}",
        )
    )
    return HTMLResponse(
        _render_paypal_desktop_checkout(client_id, plan_id, nonce),
        headers={
            "Cache-Control": "no-store",
            "Content-Security-Policy": csp,
            "Cross-Origin-Opener-Policy": "same-origin-allow-popups",
            "Permissions-Policy": "camera=(), microphone=(), geolocation=(), clipboard-write=(self)",
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
        },
    )


def _paypal_license_plan() -> str:
    return (os.environ.get("PAYPAL_LICENSE_PLAN") or "premium-desktop-monthly").strip() or "premium-desktop-monthly"


def _paypal_onetime_license_plan() -> str:
    return (os.environ.get("PAYPAL_ONETIME_LICENSE_PLAN") or "premium-desktop-lifetime").strip() or "premium-desktop-lifetime"


def _paypal_license_max_devices() -> int:
    try:
        parsed = int((os.environ.get("PAYPAL_LICENSE_MAX_DEVICES") or "1").strip())
        return parsed if parsed > 0 else 1
    except ValueError:
        return 1


def _paypal_onetime_license_max_devices() -> int:
    try:
        parsed = int((os.environ.get("PAYPAL_ONETIME_LICENSE_MAX_DEVICES") or "1").strip())
        return parsed if parsed > 0 else 1
    except ValueError:
        return 1


def _paypal_onetime_expected_amount() -> Decimal:
    raw = (os.environ.get("PAYPAL_ONETIME_AMOUNT") or "250.00").strip()
    try:
        amount = Decimal(raw)
    except InvalidOperation:
        amount = Decimal("250.00")
    return amount.quantize(Decimal("0.01"))


def _paypal_onetime_expected_currency() -> str:
    return (os.environ.get("PAYPAL_ONETIME_CURRENCY") or "USD").strip().upper() or "USD"


def _paypal_credentials() -> tuple[str, str]:
    client_id = (os.environ.get("PAYPAL_CLIENT_ID") or "").strip()
    client_secret = (os.environ.get("PAYPAL_CLIENT_SECRET") or "").strip()
    if not client_id or not client_secret:
        raise HTTPException(status_code=503, detail="paypal-not-configured")
    return client_id, client_secret


def _paypal_oauth_cache_key(client_id: str, client_secret: str) -> tuple[str, str, str]:
    secret_fingerprint = hashlib.sha256(client_secret.encode("utf-8")).hexdigest()
    return (_paypal_api_base(), client_id, secret_fingerprint)


def _invalidate_paypal_oauth_cache() -> None:
    with _PAYPAL_OAUTH_LOCK:
        _PAYPAL_OAUTH_CACHE.update({"key": None, "token": None, "expires_at": 0.0})


def _paypal_access_token(*, force_refresh: bool = False) -> str:
    client_id, client_secret = _paypal_credentials()
    cache_key = _paypal_oauth_cache_key(client_id, client_secret)
    with _PAYPAL_OAUTH_LOCK:
        now = time.monotonic()
        cached_token = _PAYPAL_OAUTH_CACHE.get("token")
        cached_expiry = float(_PAYPAL_OAUTH_CACHE.get("expires_at") or 0)
        if (
            not force_refresh
            and _PAYPAL_OAUTH_CACHE.get("key") == cache_key
            and isinstance(cached_token, str)
            and cached_token
            and cached_expiry > now
        ):
            return cached_token

        auth = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
        body = urlencode({"grant_type": "client_credentials"}).encode("utf-8")
        req = UrlRequest(
            f"{_paypal_api_base()}/v1/oauth2/token",
            data=body,
            headers={
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            # URL is constructed from the HTTPS PayPal host allowlist above.
            with urlopen(req, timeout=20) as resp:  # nosec B310
                data = json.loads(resp.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=502, detail="paypal-token-failed") from exc
        token = str(data.get("access_token") or "").strip()
        if not token:
            raise HTTPException(status_code=502, detail="paypal-token-missing")
        try:
            expires_in = int(data.get("expires_in") or 300)
        except (TypeError, ValueError):
            expires_in = 300
        expires_in = min(max(1, expires_in), 24 * 3600)
        safety_margin = min(60, max(1, expires_in // 10))
        cache_ttl = max(1, expires_in - safety_margin)
        _PAYPAL_OAUTH_CACHE.update(
            {
                "key": cache_key,
                "token": token,
                "expires_at": now + cache_ttl,
            }
        )
        return token


def _paypal_api_request(method: str, path: str, payload: dict | None = None) -> dict:
    data = None
    if payload is not None:
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    for attempt in range(2):
        token = _paypal_access_token(force_refresh=attempt > 0)
        req = UrlRequest(
            f"{_paypal_api_base()}{path}",
            data=data,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method=method.upper(),
        )
        try:
            # URL is constructed from the HTTPS PayPal host allowlist above.
            with urlopen(req, timeout=20) as resp:  # nosec B310
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except HTTPError as exc:
            if exc.code == 401 and attempt == 0:
                _invalidate_paypal_oauth_cache()
                continue
            try:
                detail = json.loads(exc.read().decode("utf-8"))
            except Exception:
                detail = None
            raise HTTPException(
                status_code=502,
                detail=detail.get("name") if isinstance(detail, dict) and detail.get("name") else "paypal-api-failed",
            ) from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=502, detail="paypal-api-failed") from exc
    raise HTTPException(status_code=502, detail="paypal-api-failed")


def _fetch_paypal_subscription(subscription_id: str) -> dict:
    subscription_id = str(subscription_id or "").strip()
    if not subscription_id:
        raise HTTPException(status_code=400, detail="missing-paypal-subscription-id")
    if not _PAYPAL_SUBSCRIPTION_ID_RE.fullmatch(subscription_id):
        raise HTTPException(status_code=400, detail="invalid-paypal-subscription-id")
    subscription = _paypal_api_request("GET", f"/v1/billing/subscriptions/{subscription_id}")
    if str(subscription.get("id") or "").strip() != subscription_id:
        raise HTTPException(status_code=502, detail="paypal-subscription-id-mismatch")
    return subscription


def _fetch_paypal_capture(capture_id: str) -> dict:
    capture_id = str(capture_id or "").strip()
    if not capture_id:
        raise HTTPException(status_code=400, detail="missing-paypal-capture-id")
    if not _PAYPAL_RESOURCE_ID_RE.fullmatch(capture_id):
        raise HTTPException(status_code=400, detail="invalid-paypal-capture-id")
    capture = _paypal_api_request("GET", f"/v2/payments/captures/{capture_id}")
    if str(capture.get("id") or "").strip() != capture_id:
        raise HTTPException(status_code=502, detail="paypal-capture-id-mismatch")
    return capture


def _fetch_paypal_order(order_id: str) -> dict:
    order_id = str(order_id or "").strip()
    if not order_id:
        raise HTTPException(status_code=400, detail="missing-paypal-order-id")
    if not _PAYPAL_RESOURCE_ID_RE.fullmatch(order_id):
        raise HTTPException(status_code=400, detail="invalid-paypal-order-id")
    order = _paypal_api_request("GET", f"/v2/checkout/orders/{order_id}")
    if str(order.get("id") or "").strip() != order_id:
        raise HTTPException(status_code=502, detail="paypal-order-id-mismatch")
    return order


def _verify_paypal_webhook_signature(request: Request, event: dict) -> None:
    webhook_id = (os.environ.get("PAYPAL_WEBHOOK_ID") or "").strip()
    if not webhook_id:
        raise HTTPException(status_code=503, detail="paypal-webhook-not-configured")
    verification = _paypal_api_request(
        "POST",
        "/v1/notifications/verify-webhook-signature",
        {
            "auth_algo": request.headers.get("PAYPAL-AUTH-ALGO"),
            "cert_url": request.headers.get("PAYPAL-CERT-URL"),
            "transmission_id": request.headers.get("PAYPAL-TRANSMISSION-ID"),
            "transmission_sig": request.headers.get("PAYPAL-TRANSMISSION-SIG"),
            "transmission_time": request.headers.get("PAYPAL-TRANSMISSION-TIME"),
            "webhook_id": webhook_id,
            "webhook_event": event,
        },
    )
    if verification.get("verification_status") != "SUCCESS":
        raise HTTPException(status_code=400, detail="paypal-webhook-verification-failed")


def _parse_paypal_timestamp(value: str | None) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return int(parsed.timestamp())


def _parse_paypal_ordering_timestamp(value: str | None) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    parsed = parsed.astimezone(dt.timezone.utc)
    return int(parsed.timestamp()) * 1_000_000 + parsed.microsecond


def _paypal_subscription_ordering_version(
    subscription: dict,
) -> tuple[int | None, int | None]:
    """Return PayPal's lifecycle and general resource clocks."""
    update_time_us = _parse_paypal_ordering_timestamp(
        subscription.get("update_time")
    )
    status_time_us = _parse_paypal_ordering_timestamp(
        subscription.get("status_update_time")
    )
    if status_time_us is None:
        status_time_us = update_time_us
    if update_time_us is None:
        update_time_us = status_time_us
    return status_time_us, update_time_us


def _paypal_subscription_ordering_timestamp(subscription: dict) -> int | None:
    """Compatibility projection for callers that only need one resource clock."""
    status_time_us, update_time_us = _paypal_subscription_ordering_version(
        subscription
    )
    if status_time_us is None:
        return update_time_us
    if update_time_us is None:
        return status_time_us
    return max(status_time_us, update_time_us)


def _apply_paypal_resource_state(
    conn: sqlite3.Connection,
    *,
    resource_kind: str,
    resource_id: str,
    state_time_us: int | None,
    provider_status_time_us: int | None = None,
    provider_update_time_us: int | None = None,
    state_status: str,
    state_rank: int,
    terminal: bool,
    source_id: str | None,
    now: int,
) -> bool:
    status_time_us = provider_status_time_us
    update_time_us = provider_update_time_us
    if status_time_us is None:
        status_time_us = state_time_us
    if update_time_us is None:
        update_time_us = state_time_us

    supplied_times = [
        value
        for value in (status_time_us, update_time_us)
        if value is not None
    ]
    invalid_time = any(
        value <= 0
        or value > (now + TOKEN_FUTURE_SKEW_SECONDS) * 1_000_000
        for value in supplied_times
    )
    if terminal and (not supplied_times or invalid_time):
        # A verified refund/reversal is absorbing even if its notification clock
        # is absent or malformed. Do not let that clock poison later ordering.
        status_time_us = 0
        update_time_us = 0
    elif not supplied_times:
        raise HTTPException(
            status_code=502,
            detail=f"paypal-{resource_kind}-state-time-missing",
        )
    elif invalid_time:
        raise HTTPException(
            status_code=502,
            detail=f"paypal-{resource_kind}-state-time-invalid",
        )
    else:
        if status_time_us is None:
            status_time_us = update_time_us
        if update_time_us is None:
            update_time_us = status_time_us

    incoming_version = (int(status_time_us or 0), int(update_time_us or 0))

    current = conn.execute(
        """
        select * from paypal_resource_states
        where resource_kind=? and resource_id=?
        """,
        (resource_kind, resource_id),
    ).fetchone()

    current_version = (0, 0)
    if current:
        legacy_time_us = int(current["state_time_us"] or 0)
        current_version = (
            int(current["provider_status_time_us"] or legacy_time_us),
            int(current["provider_update_time_us"] or legacy_time_us),
        )

    if current and int(current["terminal"] or 0) == 1:
        if not terminal:
            raise HTTPException(
                status_code=409,
                detail=f"paypal-{resource_kind}-revoked",
            )
        if incoming_version <= current_version:
            return False
        effective_version = incoming_version
    elif terminal:
        effective_version = max(incoming_version, current_version)
    elif current:
        current_status = str(current["state_status"])
        current_rank = int(current["state_rank"])
        if int(current["provisional"] or 0) == 1:
            effective_version = incoming_version
        elif incoming_version < current_version:
            raise HTTPException(
                status_code=409,
                detail=f"paypal-{resource_kind}-state-stale",
            )
        elif incoming_version == current_version:
            if state_status == current_status and state_rank == current_rank:
                return False
            if state_rank > current_rank:
                effective_version = incoming_version
            else:
                raise HTTPException(
                    status_code=409,
                    detail=f"paypal-{resource_kind}-state-stale",
                )
        else:
            effective_version = incoming_version
    else:
        effective_version = incoming_version

    effective_time_us = max(effective_version)

    conn.execute(
        """
        insert into paypal_resource_states (
          resource_kind, resource_id, state_time_us,
          provider_status_time_us, provider_update_time_us,
          state_status, state_rank, terminal, provisional,
          source_id, updated_at
        ) values (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
        on conflict(resource_kind, resource_id) do update set
          state_time_us=excluded.state_time_us,
          provider_status_time_us=excluded.provider_status_time_us,
          provider_update_time_us=excluded.provider_update_time_us,
          state_status=excluded.state_status,
          state_rank=excluded.state_rank,
          terminal=excluded.terminal,
          provisional=0,
          source_id=excluded.source_id,
          updated_at=excluded.updated_at
        """,
        (
            resource_kind,
            resource_id,
            effective_time_us,
            effective_version[0],
            effective_version[1],
            state_status,
            int(state_rank),
            1 if terminal else 0,
            source_id,
            now,
        ),
    )
    return True


def _paypal_subscription_email(subscription: dict, fallback: str | None = None) -> str | None:
    for value in (
        subscription.get("subscriber", {}).get("email_address") if isinstance(subscription.get("subscriber"), dict) else None,
        subscription.get("payer", {}).get("email_address") if isinstance(subscription.get("payer"), dict) else None,
        fallback,
    ):
        text = str(value or "").strip()
        if text:
            return text
    return None


def _paypal_subscription_payer_id(subscription: dict) -> str | None:
    subscriber = subscription.get("subscriber") if isinstance(subscription.get("subscriber"), dict) else {}
    payer = subscription.get("payer") if isinstance(subscription.get("payer"), dict) else {}
    for value in (subscriber.get("payer_id"), payer.get("payer_id")):
        text = str(value or "").strip()
        if text:
            return text
    return None


def _paypal_subscription_period_end(
    subscription: dict,
    now: int,
    existing_period_end: int | None = None,
) -> int:
    billing_info = subscription.get("billing_info") if isinstance(subscription.get("billing_info"), dict) else {}
    parsed = _parse_paypal_timestamp(billing_info.get("next_billing_time"))
    if parsed and parsed > 0:
        return parsed
    existing = int(existing_period_end or 0)
    if existing > 0:
        return existing
    raise HTTPException(status_code=400, detail="paypal-subscription-period-missing")


def _paypal_subscription_license_state(event_type: str | None, subscription: dict, period_end: int, now: int) -> tuple[str, int]:
    normalized_event = str(event_type or "").strip().upper()
    paypal_status = str(subscription.get("status") or "").strip().upper()
    if normalized_event == "BILLING.SUBSCRIPTION.CANCELLED" or paypal_status == "CANCELLED":
        return ("active" if period_end > now else "expired", 1)
    if normalized_event == "BILLING.SUBSCRIPTION.EXPIRED" or paypal_status == "EXPIRED":
        return "expired", 0
    if normalized_event in {
        "BILLING.SUBSCRIPTION.SUSPENDED",
        "BILLING.SUBSCRIPTION.PAYMENT.FAILED",
        "PAYMENT.SALE.REFUNDED",
        "PAYMENT.SALE.REVERSED",
    } or paypal_status == "SUSPENDED":
        return "suspended", 0
    if paypal_status == "ACTIVE" or normalized_event in {
        "BILLING.SUBSCRIPTION.ACTIVATED",
        "BILLING.SUBSCRIPTION.RE-ACTIVATED",
        "PAYMENT.SALE.COMPLETED",
    }:
        return "active", 0
    return (paypal_status.lower() or "pending"), 0


def _paypal_subscription_ordering_state(
    subscription: dict,
    license_status: str,
    cancel_at_period_end: int,
) -> tuple[str, int]:
    paypal_status = str(subscription.get("status") or "UNKNOWN").strip().upper()
    normalized_status = str(license_status or "pending").strip().lower()
    state_status = (
        f"{paypal_status}:{normalized_status}:"
        f"{int(cancel_at_period_end or 0)}"
    )
    if normalized_status == "expired":
        state_rank = 40
    elif normalized_status == "suspended":
        state_rank = 30
    elif normalized_status != "active":
        state_rank = 25
    elif int(cancel_at_period_end or 0) == 1:
        state_rank = 20
    else:
        state_rank = 10
    return state_status, state_rank


def _assert_paypal_plan_allowed(subscription: dict) -> str:
    allowed_plan_ids = _paypal_allowed_plan_ids()
    if not allowed_plan_ids:
        raise HTTPException(status_code=503, detail="paypal-plan-not-configured")
    plan_id = str(subscription.get("plan_id") or "").strip()
    if plan_id not in allowed_plan_ids:
        raise HTTPException(status_code=400, detail="paypal-plan-mismatch")
    return plan_id


def _is_license_key_collision(exc: sqlite3.IntegrityError) -> bool:
    return "licenses.license_key" in str(exc).lower()


def _update_paypal_subscription_license_row(
    conn: sqlite3.Connection,
    existing,
    *,
    subscription_id: str,
    license_plan: str,
    max_devices: int,
    owner_email: str | None,
    status: str,
    period_end: int,
    cancel_at_period_end: int,
    plan_id: str,
    payer_id: str | None,
    paypal_status: str | None,
):
    conn.execute(
        """
        update licenses
           set plan=?,
               max_devices=?,
               active=1,
               notes=?,
               owner_email=coalesce(?, owner_email),
               kind='subscription',
               status=?,
               current_period_end=?,
               cancel_at_period_end=?,
               paypal_plan_id=?,
               paypal_payer_id=coalesce(?, paypal_payer_id),
               paypal_status=?
         where license_key=?
        """,
        (
            license_plan,
            max_devices,
            f"PayPal subscription {subscription_id}",
            owner_email,
            status,
            period_end,
            cancel_at_period_end,
            plan_id,
            payer_id,
            paypal_status,
            existing["license_key"],
        ),
    )
    return conn.execute(
        "select * from licenses where license_key=?",
        (existing["license_key"],),
    ).fetchone()


def _upsert_paypal_subscription_license(
    conn: sqlite3.Connection,
    subscription: dict,
    *,
    event_type: str | None = None,
    email: str | None = None,
    now: int | None = None,
    state_source_id: str | None = None,
):
    now = int(now or time.time())
    subscription_id = str(subscription.get("id") or "").strip()
    if not subscription_id:
        raise HTTPException(status_code=400, detail="missing-paypal-subscription-id")
    if not _PAYPAL_SUBSCRIPTION_ID_RE.fullmatch(subscription_id):
        raise HTTPException(status_code=400, detail="invalid-paypal-subscription-id")
    plan_id = _assert_paypal_plan_allowed(subscription)
    _begin_immediate_transaction(conn)
    existing = conn.execute(
        "select * from licenses where paypal_subscription_id=?",
        (subscription_id,),
    ).fetchone()
    period_end = _paypal_subscription_period_end(
        subscription,
        now,
        existing["current_period_end"] if existing else None,
    )
    status, cancel_at_period_end = _paypal_subscription_license_state(
        None,
        subscription,
        period_end,
        now,
    )
    owner_email = _paypal_subscription_email(subscription, email)
    payer_id = _paypal_subscription_payer_id(subscription)
    paypal_status = str(subscription.get("status") or "").strip() or None
    license_plan = _paypal_license_plan()
    max_devices = _paypal_license_max_devices()
    state_status, state_rank = _paypal_subscription_ordering_state(
        subscription,
        status,
        cancel_at_period_end,
    )
    status_time_us, update_time_us = _paypal_subscription_ordering_version(
        subscription
    )
    incoming_time_us = max(
        int(status_time_us or 0),
        int(update_time_us or 0),
    ) or None
    should_apply = _apply_paypal_resource_state(
        conn,
        resource_kind="subscription",
        resource_id=subscription_id,
        state_time_us=incoming_time_us,
        provider_status_time_us=status_time_us,
        provider_update_time_us=update_time_us,
        state_status=state_status,
        state_rank=state_rank,
        terminal=False,
        source_id=state_source_id or f"resource:{subscription_id}",
        now=now,
    )
    if not should_apply:
        if existing:
            return existing
        raise HTTPException(
            status_code=409,
            detail="paypal-subscription-state-stale",
        )

    if existing:
        return _update_paypal_subscription_license_row(
            conn,
            existing,
            subscription_id=subscription_id,
            license_plan=license_plan,
            max_devices=max_devices,
            owner_email=owner_email,
            status=status,
            period_end=period_end,
            cancel_at_period_end=cancel_at_period_end,
            plan_id=plan_id,
            payer_id=payer_id,
            paypal_status=paypal_status,
        )

    for _ in range(20):
        license_key = _generate_license_key()
        try:
            conn.execute(
                """
                insert into licenses (
                  license_key, plan, max_devices, active, issued_at, notes,
                  owner_email, kind, status, current_period_end, cancel_at_period_end,
                  paypal_subscription_id, paypal_plan_id, paypal_payer_id, paypal_status
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    license_key,
                    license_plan,
                    max_devices,
                    1,
                    now,
                    f"PayPal subscription {subscription_id}",
                    owner_email,
                    "subscription",
                    status,
                    period_end,
                    cancel_at_period_end,
                    subscription_id,
                    plan_id,
                    payer_id,
                    paypal_status,
                ),
            )
            return conn.execute(
                "select * from licenses where license_key=?",
                (license_key,),
            ).fetchone()
        except sqlite3.IntegrityError as exc:
            winner = conn.execute(
                "select * from licenses where paypal_subscription_id=?",
                (subscription_id,),
            ).fetchone()
            if winner:
                return _update_paypal_subscription_license_row(
                    conn,
                    winner,
                    subscription_id=subscription_id,
                    license_plan=license_plan,
                    max_devices=max_devices,
                    owner_email=owner_email,
                    status=status,
                    period_end=period_end,
                    cancel_at_period_end=cancel_at_period_end,
                    plan_id=plan_id,
                    payer_id=payer_id,
                    paypal_status=paypal_status,
                )
            if _is_license_key_collision(exc):
                continue
            raise
    raise HTTPException(status_code=500, detail="license-key-generation-failed")


def _paypal_related_order_id(resource: dict) -> str | None:
    candidates = [resource.get("order_id")]
    supplementary = resource.get("supplementary_data") if isinstance(resource.get("supplementary_data"), dict) else {}
    related_ids = supplementary.get("related_ids") if isinstance(supplementary.get("related_ids"), dict) else {}
    candidates.append(related_ids.get("order_id"))
    for candidate in candidates:
        text = str(candidate or "").strip()
        if text:
            return text
    return None


def _first_configured_env(*names: str) -> str | None:
    for name in names:
        value = (os.environ.get(name) or "").strip()
        if value:
            return value
    return None


def _require_paypal_onetime_identity_contract() -> None:
    merchant_id = _first_configured_env(
        "PAYPAL_PAYEE_MERCHANT_ID",
        "PAYPAL_ONETIME_PAYEE_MERCHANT_ID",
    )
    if not merchant_id:
        raise HTTPException(
            status_code=503,
            detail="paypal-onetime-merchant-binding-not-configured",
        )

    stable_purchase_binding = _first_configured_env(
        "PAYPAL_ONETIME_PRODUCT_ID",
        "PAYPAL_ONETIME_EXPECTED_PRODUCT_ID",
        "PAYPAL_ONETIME_CUSTOM_ID",
        "PAYPAL_ONETIME_EXPECTED_CUSTOM_ID",
        "PAYPAL_ONETIME_CUSTOM_ID_PREFIX",
        "PAYPAL_ONETIME_INVOICE_ID",
        "PAYPAL_ONETIME_EXPECTED_INVOICE_ID",
        "PAYPAL_ONETIME_INVOICE_ID_PREFIX",
    )
    if not stable_purchase_binding:
        raise HTTPException(
            status_code=503,
            detail="paypal-onetime-purchase-binding-not-configured",
        )


def _paypal_capture_purchase_unit(capture: dict, order: dict | None) -> dict:
    order = order if isinstance(order, dict) else {}
    purchase_units = order.get("purchase_units")
    if not isinstance(purchase_units, list):
        return {}
    units = [unit for unit in purchase_units if isinstance(unit, dict)]
    if not units:
        return {}

    capture_id = str(capture.get("id") or "").strip()
    captures_were_listed = False
    for unit in units:
        payments = unit.get("payments") if isinstance(unit.get("payments"), dict) else {}
        captures = payments.get("captures")
        if not isinstance(captures, list):
            continue
        captures_were_listed = True
        for item in captures:
            item_id = item.get("id") if isinstance(item, dict) else None
            if str(item_id or "").strip() == capture_id:
                return unit

    if captures_were_listed:
        raise HTTPException(status_code=400, detail="paypal-capture-order-mismatch")
    if len(units) == 1:
        return units[0]
    raise HTTPException(status_code=400, detail="paypal-capture-order-ambiguous")


def _paypal_identity_values(*values) -> set[str]:
    result: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if text:
            result.add(text)
    return result


def _assert_paypal_onetime_identity(capture: dict, order: dict | None) -> None:
    _require_paypal_onetime_identity_contract()
    order = order if isinstance(order, dict) else {}
    related_order_id = _paypal_related_order_id(capture)
    if order:
        order_id = str(order.get("id") or "").strip()
        if related_order_id and order_id != related_order_id:
            raise HTTPException(status_code=400, detail="paypal-capture-order-mismatch")
    purchase_unit = _paypal_capture_purchase_unit(capture, order)

    items = purchase_unit.get("items")
    items = [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []
    product_values = _paypal_identity_values(
        capture.get("product_id"),
        capture.get("reference_id"),
        purchase_unit.get("product_id"),
        purchase_unit.get("reference_id"),
        *(item.get("product_id") for item in items),
        *(item.get("sku") for item in items),
    )
    expected_product = _first_configured_env(
        "PAYPAL_ONETIME_PRODUCT_ID",
        "PAYPAL_ONETIME_EXPECTED_PRODUCT_ID",
    )
    if expected_product and expected_product not in product_values:
        raise HTTPException(status_code=400, detail="paypal-capture-product-mismatch")

    custom_values = _paypal_identity_values(
        capture.get("custom_id"),
        purchase_unit.get("custom_id"),
    )
    expected_custom = _first_configured_env(
        "PAYPAL_ONETIME_CUSTOM_ID",
        "PAYPAL_ONETIME_EXPECTED_CUSTOM_ID",
    )
    if expected_custom and expected_custom not in custom_values:
        raise HTTPException(status_code=400, detail="paypal-capture-custom-id-mismatch")
    custom_prefix = _first_configured_env("PAYPAL_ONETIME_CUSTOM_ID_PREFIX")
    if custom_prefix and not any(value.startswith(custom_prefix) for value in custom_values):
        raise HTTPException(status_code=400, detail="paypal-capture-custom-id-mismatch")

    invoice_values = _paypal_identity_values(
        capture.get("invoice_id"),
        purchase_unit.get("invoice_id"),
    )
    expected_invoice = _first_configured_env(
        "PAYPAL_ONETIME_INVOICE_ID",
        "PAYPAL_ONETIME_EXPECTED_INVOICE_ID",
    )
    if expected_invoice and expected_invoice not in invoice_values:
        raise HTTPException(status_code=400, detail="paypal-capture-invoice-id-mismatch")
    invoice_prefix = _first_configured_env("PAYPAL_ONETIME_INVOICE_ID_PREFIX")
    if invoice_prefix and not any(value.startswith(invoice_prefix) for value in invoice_values):
        raise HTTPException(status_code=400, detail="paypal-capture-invoice-id-mismatch")

    capture_payee = capture.get("payee") if isinstance(capture.get("payee"), dict) else {}
    unit_payee = purchase_unit.get("payee") if isinstance(purchase_unit.get("payee"), dict) else {}
    merchant_ids = _paypal_identity_values(
        capture_payee.get("merchant_id"),
        unit_payee.get("merchant_id"),
    )
    expected_merchant_id = _first_configured_env(
        "PAYPAL_PAYEE_MERCHANT_ID",
        "PAYPAL_ONETIME_PAYEE_MERCHANT_ID",
    )
    if expected_merchant_id and expected_merchant_id not in merchant_ids:
        raise HTTPException(status_code=400, detail="paypal-capture-payee-mismatch")

    payee_emails = {
        value.lower()
        for value in _paypal_identity_values(
            capture_payee.get("email_address"),
            unit_payee.get("email_address"),
        )
    }
    expected_payee_email = _first_configured_env(
        "PAYPAL_PAYEE_EMAIL",
        "PAYPAL_ONETIME_PAYEE_EMAIL",
    )
    if expected_payee_email and expected_payee_email.lower() not in payee_emails:
        raise HTTPException(status_code=400, detail="paypal-capture-payee-mismatch")


def _paypal_onetime_email(capture: dict, order: dict | None = None, fallback: str | None = None) -> str | None:
    order = order if isinstance(order, dict) else {}
    capture_payer = capture.get("payer") if isinstance(capture.get("payer"), dict) else {}
    order_payer = order.get("payer") if isinstance(order.get("payer"), dict) else {}
    for value in (
        order_payer.get("email_address"),
        capture_payer.get("email_address"),
        fallback,
    ):
        text = str(value or "").strip()
        if text:
            return text
    return None


def _paypal_onetime_payer_id(capture: dict, order: dict | None = None) -> str | None:
    order = order if isinstance(order, dict) else {}
    capture_payer = capture.get("payer") if isinstance(capture.get("payer"), dict) else {}
    order_payer = order.get("payer") if isinstance(order.get("payer"), dict) else {}
    for value in (order_payer.get("payer_id"), capture_payer.get("payer_id")):
        text = str(value or "").strip()
        if text:
            return text
    return None


def _assert_paypal_onetime_allowed(capture: dict, order: dict | None = None) -> None:
    status = str(capture.get("status") or "").strip().upper()
    if status != "COMPLETED":
        raise HTTPException(status_code=400, detail="paypal-capture-not-completed")
    amount = capture.get("amount") if isinstance(capture.get("amount"), dict) else {}
    currency = str(amount.get("currency_code") or amount.get("currency") or "").strip().upper()
    value_raw = str(amount.get("value") or "").strip()
    try:
        value = Decimal(value_raw).quantize(Decimal("0.01"))
    except InvalidOperation:
        raise HTTPException(status_code=400, detail="paypal-capture-amount-invalid")
    if currency != _paypal_onetime_expected_currency() or value != _paypal_onetime_expected_amount():
        raise HTTPException(status_code=400, detail="paypal-capture-amount-mismatch")
    _assert_paypal_onetime_identity(capture, order)


def _resolve_paypal_onetime_license_row(
    conn: sqlite3.Connection,
    *,
    capture_id: str,
    order_id: str | None,
):
    by_capture = conn.execute(
        "select * from licenses where paypal_capture_id=?",
        (capture_id,),
    ).fetchone()
    by_order = None
    if order_id:
        by_order = conn.execute(
            "select * from licenses where paypal_order_id=?",
            (order_id,),
        ).fetchone()

    if (
        by_capture
        and by_order
        and by_capture["license_key"] != by_order["license_key"]
    ):
        raise HTTPException(status_code=409, detail="paypal-order-already-claimed")

    if by_capture:
        existing_order_id = str(by_capture["paypal_order_id"] or "").strip()
        if existing_order_id and order_id and existing_order_id != order_id:
            raise HTTPException(status_code=409, detail="paypal-capture-already-claimed")
        return by_capture

    if by_order:
        existing_capture_id = str(by_order["paypal_capture_id"] or "").strip()
        if existing_capture_id and existing_capture_id != capture_id:
            raise HTTPException(status_code=409, detail="paypal-order-already-claimed")
        return by_order

    return None


def _update_paypal_onetime_license_row(
    conn: sqlite3.Connection,
    existing,
    *,
    capture_id: str,
    order_id: str | None,
    owner_email: str | None,
    payer_id: str | None,
    paypal_status: str | None,
    license_plan: str,
    max_devices: int,
):
    conn.execute(
        """
        update licenses
           set plan=?,
               max_devices=?,
               active=1,
               notes=?,
               owner_email=coalesce(?, owner_email),
               kind='perpetual',
               status='active',
               current_period_end=null,
               cancel_at_period_end=0,
               paypal_capture_id=?,
               paypal_order_id=coalesce(?, paypal_order_id),
               paypal_payer_id=coalesce(?, paypal_payer_id),
               paypal_status=?
         where license_key=?
        """,
        (
            license_plan,
            max_devices,
            f"PayPal one-time payment {capture_id}",
            owner_email,
            capture_id,
            order_id,
            payer_id,
            paypal_status,
            existing["license_key"],
        ),
    )
    return conn.execute(
        "select * from licenses where license_key=?",
        (existing["license_key"],),
    ).fetchone()


def _upsert_paypal_onetime_license(
    conn: sqlite3.Connection,
    capture: dict,
    *,
    order: dict | None = None,
    email: str | None = None,
    now: int | None = None,
    state_source_id: str | None = None,
):
    now = int(now or time.time())
    capture_id = str(capture.get("id") or "").strip()
    if not capture_id:
        raise HTTPException(status_code=400, detail="missing-paypal-capture-id")
    if not _PAYPAL_RESOURCE_ID_RE.fullmatch(capture_id):
        raise HTTPException(status_code=400, detail="invalid-paypal-capture-id")
    _assert_paypal_onetime_allowed(capture, order)
    order_id = _paypal_related_order_id(capture)
    owner_email = _paypal_onetime_email(capture, order, email)
    payer_id = _paypal_onetime_payer_id(capture, order)
    paypal_status = str(capture.get("status") or "").strip() or None
    license_plan = _paypal_onetime_license_plan()
    max_devices = _paypal_onetime_license_max_devices()
    incoming_time_us = _parse_paypal_ordering_timestamp(
        capture.get("update_time")
    )
    _begin_immediate_transaction(conn)
    should_apply = _apply_paypal_resource_state(
        conn,
        resource_kind="capture",
        resource_id=capture_id,
        state_time_us=incoming_time_us,
        state_status="COMPLETED",
        state_rank=10,
        terminal=False,
        source_id=state_source_id or f"resource:{capture_id}",
        now=now,
    )
    if order_id:
        should_apply = (
            _apply_paypal_resource_state(
                conn,
                resource_kind="order",
                resource_id=order_id,
                state_time_us=incoming_time_us,
                state_status="COMPLETED",
                state_rank=10,
                terminal=False,
                source_id=state_source_id or f"resource:{capture_id}",
                now=now,
            )
            or should_apply
        )
    existing = _resolve_paypal_onetime_license_row(
        conn,
        capture_id=capture_id,
        order_id=order_id,
    )
    if not should_apply:
        if existing:
            return existing
        raise HTTPException(
            status_code=409,
            detail="paypal-capture-state-stale",
        )

    if existing:
        return _update_paypal_onetime_license_row(
            conn,
            existing,
            capture_id=capture_id,
            order_id=order_id,
            owner_email=owner_email,
            payer_id=payer_id,
            paypal_status=paypal_status,
            license_plan=license_plan,
            max_devices=max_devices,
        )

    for _ in range(20):
        license_key = _generate_license_key()
        try:
            conn.execute(
                """
                insert into licenses (
                  license_key, plan, max_devices, active, issued_at, notes,
                  owner_email, kind, status, current_period_end, cancel_at_period_end,
                  paypal_capture_id, paypal_order_id, paypal_payer_id, paypal_status
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    license_key,
                    license_plan,
                    max_devices,
                    1,
                    now,
                    f"PayPal one-time payment {capture_id}",
                    owner_email,
                    "perpetual",
                    "active",
                    None,
                    0,
                    capture_id,
                    order_id,
                    payer_id,
                    paypal_status,
                ),
            )
            return conn.execute(
                "select * from licenses where license_key=?",
                (license_key,),
            ).fetchone()
        except sqlite3.IntegrityError as exc:
            winner = _resolve_paypal_onetime_license_row(
                conn,
                capture_id=capture_id,
                order_id=order_id,
            )
            if winner:
                return _update_paypal_onetime_license_row(
                    conn,
                    winner,
                    capture_id=capture_id,
                    order_id=order_id,
                    owner_email=owner_email,
                    payer_id=payer_id,
                    paypal_status=paypal_status,
                    license_plan=license_plan,
                    max_devices=max_devices,
                )
            if _is_license_key_collision(exc):
                continue
            raise
    raise HTTPException(status_code=500, detail="license-key-generation-failed")


def _fetch_order_for_capture(capture: dict) -> dict | None:
    order_id = _paypal_related_order_id(capture)
    if not order_id:
        return None
    return _fetch_paypal_order(order_id)


def _paypal_capture_id_from_event(event: dict) -> str | None:
    resource = event.get("resource") if isinstance(event.get("resource"), dict) else {}
    supplementary = resource.get("supplementary_data") if isinstance(resource.get("supplementary_data"), dict) else {}
    related_ids = supplementary.get("related_ids") if isinstance(supplementary.get("related_ids"), dict) else {}
    candidates = [
        resource.get("capture_id"),
        related_ids.get("capture_id"),
    ]
    event_type = str(event.get("event_type") or "").strip().upper()
    if event_type in PAYPAL_ONETIME_COMPLETED_EVENTS or event_type in {
        "PAYMENT.CAPTURE.REVERSED",
        "PAYMENT.CAPTURE.DENIED",
        "PAYMENT.CAPTURE.DECLINED",
    }:
        candidates.append(resource.get("id"))
    for candidate in candidates:
        text = str(candidate or "").strip()
        if text:
            return text
    return None


def _paypal_order_id_from_event(event: dict) -> str | None:
    resource = event.get("resource") if isinstance(event.get("resource"), dict) else {}
    supplementary = resource.get("supplementary_data") if isinstance(resource.get("supplementary_data"), dict) else {}
    related_ids = supplementary.get("related_ids") if isinstance(supplementary.get("related_ids"), dict) else {}
    for candidate in (
        resource.get("order_id"),
        related_ids.get("order_id"),
    ):
        text = str(candidate or "").strip()
        if text:
            return text
    return None


def _paypal_capture_id_from_order(order: dict) -> str | None:
    purchase_units = (
        order.get("purchase_units")
        if isinstance(order.get("purchase_units"), list)
        else []
    )
    capture_ids: list[str] = []
    for unit in purchase_units:
        if not isinstance(unit, dict):
            continue
        payments = (
            unit.get("payments")
            if isinstance(unit.get("payments"), dict)
            else {}
        )
        captures = (
            payments.get("captures")
            if isinstance(payments.get("captures"), list)
            else []
        )
        for capture in captures:
            capture_id = (
                str(capture.get("id") or "").strip()
                if isinstance(capture, dict)
                else ""
            )
            if capture_id and capture_id not in capture_ids:
                capture_ids.append(capture_id)
    return capture_ids[0] if len(capture_ids) == 1 else None


def _resolve_paypal_onetime_revoke_aliases(
    capture_id: str | None,
    order_id: str | None,
) -> tuple[str | None, str | None]:
    """Resolve a missing alias or fail so PayPal retries the webhook."""
    resolved_capture_id = capture_id
    resolved_order_id = order_id
    if resolved_capture_id and not resolved_order_id:
        capture = _fetch_paypal_capture(resolved_capture_id)
        resolved_order_id = _paypal_related_order_id(capture)
    elif resolved_order_id and not resolved_capture_id:
        order = _fetch_paypal_order(resolved_order_id)
        resolved_capture_id = _paypal_capture_id_from_order(order)
    if not resolved_capture_id or not resolved_order_id:
        raise HTTPException(
            status_code=502,
            detail="paypal-revoke-alias-missing",
        )
    return resolved_capture_id, resolved_order_id


def _revoke_paypal_onetime_license(
    conn: sqlite3.Connection,
    capture_id: str | None,
    order_id: str | None,
    event_type: str,
    now: int,
    *,
    authoritative_time_us: int | None,
    state_source_id: str,
) -> bool:
    if not capture_id and not order_id:
        return False
    _begin_immediate_transaction(conn)
    state_changed = False
    for resource_kind, resource_id in (
        ("capture", capture_id),
        ("order", order_id),
    ):
        if resource_id:
            state_changed = (
                _apply_paypal_resource_state(
                    conn,
                    resource_kind=resource_kind,
                    resource_id=resource_id,
                    state_time_us=authoritative_time_us,
                    state_status=event_type,
                    state_rank=100,
                    terminal=True,
                    source_id=state_source_id,
                    now=now,
                )
                or state_changed
            )

    rows = conn.execute(
        """
        select * from licenses
         where (? is not null and paypal_capture_id=?)
            or (? is not null and paypal_order_id=?)
        """,
        (capture_id, capture_id, order_id, order_id),
    ).fetchall()
    for row in rows:
        resource_label = capture_id or order_id
        conn.execute(
            """
            update licenses
               set active=0,
                   status='refunded',
                   paypal_status=?,
                   notes=?
             where license_key=?
            """,
            (
                event_type,
                f"PayPal one-time payment revoked {resource_label} at {now}",
                row["license_key"],
            ),
        )
        conn.execute(
            "delete from activations where license_key=?",
            (row["license_key"],),
        )
    return state_changed or bool(rows)


def _subscription_id_from_paypal_event(event: dict) -> str | None:
    resource = event.get("resource") if isinstance(event.get("resource"), dict) else {}
    candidates = [
        resource.get("id"),
        resource.get("subscription_id"),
        resource.get("billing_agreement_id"),
    ]
    supplementary = resource.get("supplementary_data") if isinstance(resource.get("supplementary_data"), dict) else {}
    related_ids = supplementary.get("related_ids") if isinstance(supplementary.get("related_ids"), dict) else {}
    candidates.append(related_ids.get("subscription_id"))
    for candidate in candidates:
        text = str(candidate or "").strip()
        if text and text.upper().startswith("I-"):
            return text
    return None


def _paypal_event_already_processed(conn: sqlite3.Connection, event_id: str) -> bool:
    row = conn.execute("select 1 from paypal_events where event_id=?", (event_id,)).fetchone()
    return bool(row)


def _claim_paypal_event(
    conn: sqlite3.Connection,
    *,
    event_id: str,
    event_type: str,
    subscription_id: str | None,
    now: int,
    event_time_us: int | None,
) -> bool:
    cursor = conn.execute(
        """
        insert into paypal_events (
          event_id, event_type, subscription_id, processed_at,
          event_time_us, disposition
        ) values (?, ?, ?, ?, ?, 'claimed')
        on conflict(event_id) do nothing
        """,
        (event_id, event_type, subscription_id, now, event_time_us),
    )
    return cursor.rowcount == 1


def _set_paypal_event_disposition(
    conn: sqlite3.Connection,
    event_id: str,
    disposition: str,
) -> None:
    conn.execute(
        "update paypal_events set disposition=? where event_id=?",
        (disposition, event_id),
    )


def _paypal_event_applied_resource_state(
    conn: sqlite3.Connection,
    event_id: str,
    resource_pairs: tuple[tuple[str, str | None], ...],
) -> bool:
    for resource_kind, resource_id in resource_pairs:
        if not resource_id:
            continue
        row = conn.execute(
            """
            select 1 from paypal_resource_states
            where resource_kind=? and resource_id=? and source_id=?
            """,
            (resource_kind, resource_id, event_id),
        ).fetchone()
        if row:
            return True
    return False


def _activate_and_sign_license(conn: sqlite3.Connection, lic, device_id: str, subject_fallback: str | None, now: int) -> dict:
    state = _activate_license_row(conn, lic, device_id, now)
    canonical_key = state["license_key"]
    subject = lic["owner_email"] or subject_fallback or canonical_key
    payload = _build_signed_payload(
        subject=subject,
        license_key=canonical_key,
        plan=lic["plan"],
        license_kind=state["kind"],
        device_id=device_id,
        now=now,
        current_period_end=state.get("current_period_end"),
    )
    token = sign_payload(payload)
    return {
        "token": token,
        "status": {
            "active": True,
            "plan": lic["plan"],
            "kind": state["kind"],
            "currentPeriodEnd": state.get("current_period_end"),
        },
    }


@app.post("/license/activate")
def activate(req: ActivateReq):
    now = int(time.time())
    with db() as conn:
        _begin_immediate_transaction(conn)
        lic = fetch_license_by_key(conn, req.key)
        if not lic:
            raise HTTPException(status_code=400, detail="invalid-key")
        state = _activate_license_row(conn, lic, req.deviceId, now)
        canonical_key = state["license_key"]

        payload = _build_signed_payload(
            subject=req.email or canonical_key,
            license_key=canonical_key,
            plan=lic["plan"],
            license_kind=state["kind"],
            device_id=req.deviceId,
            now=now,
            current_period_end=state.get("current_period_end"),
        )
        token = sign_payload(payload)
        return {"token": token}


@app.post("/license/activate-paypal")
def activate_paypal_subscription(req: PayPalActivateReq):
    subscription_id = str(req.subscriptionId or "").strip()
    if not subscription_id:
        raise HTTPException(status_code=400, detail="missing-paypal-subscription-id")
    if not req.deviceId or not str(req.deviceId).strip():
        raise HTTPException(status_code=400, detail="missing-device-id")

    now = int(time.time())
    subscription = _fetch_paypal_subscription(subscription_id)
    if str(subscription.get("status") or "").strip().upper() != "ACTIVE":
        raise HTTPException(status_code=400, detail="paypal-subscription-not-active")

    with db() as conn:
        lic = _upsert_paypal_subscription_license(
            conn,
            subscription,
            event_type="BILLING.SUBSCRIPTION.ACTIVATED",
            email=req.email,
            now=now,
        )
        return _activate_and_sign_license(conn, lic, req.deviceId, req.email, now)


@app.post("/license/activate-paypal-purchase")
def activate_paypal_purchase(req: PayPalPurchaseActivateReq):
    paypal_id = str(req.paypalId or "").strip()
    if not paypal_id:
        raise HTTPException(status_code=400, detail="missing-paypal-purchase-id")
    if not req.deviceId or not str(req.deviceId).strip():
        raise HTTPException(status_code=400, detail="missing-device-id")

    now = int(time.time())
    if paypal_id.upper().startswith("I-"):
        subscription = _fetch_paypal_subscription(paypal_id)
        if str(subscription.get("status") or "").strip().upper() != "ACTIVE":
            raise HTTPException(status_code=400, detail="paypal-subscription-not-active")
        with db() as conn:
            lic = _upsert_paypal_subscription_license(
                conn,
                subscription,
                event_type="BILLING.SUBSCRIPTION.ACTIVATED",
                email=req.email,
                now=now,
            )
            return _activate_and_sign_license(conn, lic, req.deviceId, req.email, now)

    capture = _fetch_paypal_capture(paypal_id)
    order = _fetch_order_for_capture(capture)
    with db() as conn:
        lic = _upsert_paypal_onetime_license(
            conn,
            capture,
            order=order,
            email=req.email,
            now=now,
        )
        return _activate_and_sign_license(conn, lic, req.deviceId, req.email, now)


@app.post("/paypal/webhook")
def paypal_webhook(request: Request, event: dict):
    if not isinstance(event, dict):
        raise HTTPException(status_code=400, detail="invalid-paypal-webhook-json")

    _verify_paypal_webhook_signature(request, event)

    event_id = str(event.get("id") or "").strip()
    event_type = str(event.get("event_type") or "").strip().upper()
    if not event_id:
        raise HTTPException(status_code=400, detail="missing-paypal-event-id")

    now = int(time.time())
    event_time_us = _parse_paypal_ordering_timestamp(event.get("create_time"))
    subscription_id = _subscription_id_from_paypal_event(event)
    capture_id = _paypal_capture_id_from_event(event)
    order_id = _paypal_order_id_from_event(event)
    with db() as conn:
        if _paypal_event_already_processed(conn, event_id):
            return {"ok": True, "duplicate": True, "processed": False}

    subscription = None
    capture = None
    order = None
    if event_type in PAYPAL_SUBSCRIPTION_EVENTS and subscription_id:
        subscription = _fetch_paypal_subscription(subscription_id)
    elif event_type in PAYPAL_ONETIME_COMPLETED_EVENTS and capture_id:
        capture = _fetch_paypal_capture(capture_id)
        order = _fetch_order_for_capture(capture)
    elif event_type in PAYPAL_ONETIME_REVOKE_EVENTS and (
        capture_id or order_id
    ):
        capture_id, order_id = _resolve_paypal_onetime_revoke_aliases(
            capture_id,
            order_id,
        )

    processed = False
    with db() as conn:
        _begin_immediate_transaction(conn)
        claimed = _claim_paypal_event(
            conn,
            event_id=event_id,
            event_type=event_type or "unknown",
            subscription_id=subscription_id or capture_id or order_id,
            now=now,
            event_time_us=event_time_us,
        )
        if not claimed:
            return {"ok": True, "duplicate": True, "processed": False}

        if subscription is not None and subscription_id:
            try:
                lic = _upsert_paypal_subscription_license(
                    conn,
                    subscription,
                    event_type=event_type,
                    now=now,
                    state_source_id=event_id,
                )
                processed = bool(lic) and _paypal_event_applied_resource_state(
                    conn,
                    event_id,
                    (("subscription", subscription_id),),
                )
            except HTTPException as exc:
                if exc.detail != "paypal-subscription-state-stale":
                    raise
                _set_paypal_event_disposition(
                    conn,
                    event_id,
                    "ignored_stale",
                )
            else:
                _set_paypal_event_disposition(
                    conn,
                    event_id,
                    "applied" if processed else "already_current",
                )
        elif capture is not None and capture_id:
            conn.execute("savepoint paypal_onetime_mutation")
            try:
                lic = _upsert_paypal_onetime_license(
                    conn,
                    capture,
                    order=order,
                    now=now,
                    state_source_id=event_id,
                )
                processed = bool(lic) and _paypal_event_applied_resource_state(
                    conn,
                    event_id,
                    (
                        ("capture", capture_id),
                        (
                            "order",
                            _paypal_related_order_id(capture),
                        ),
                    ),
                )
            except HTTPException as exc:
                conn.execute("rollback to paypal_onetime_mutation")
                conn.execute("release paypal_onetime_mutation")
                if exc.detail not in {
                    "paypal-capture-revoked",
                    "paypal-order-revoked",
                    "paypal-capture-state-stale",
                    "paypal-order-state-stale",
                }:
                    raise
                disposition = (
                    "terminal_blocked"
                    if exc.detail.endswith("-revoked")
                    else "ignored_stale"
                )
                _set_paypal_event_disposition(
                    conn,
                    event_id,
                    disposition,
                )
            except Exception:
                conn.execute("rollback to paypal_onetime_mutation")
                conn.execute("release paypal_onetime_mutation")
                raise
            else:
                conn.execute("release paypal_onetime_mutation")
                _set_paypal_event_disposition(
                    conn,
                    event_id,
                    "applied" if processed else "already_current",
                )
        elif event_type in PAYPAL_ONETIME_REVOKE_EVENTS and (capture_id or order_id):
            processed = _revoke_paypal_onetime_license(
                conn,
                capture_id,
                order_id,
                event_type,
                now,
                authoritative_time_us=event_time_us,
                state_source_id=event_id,
            )
            _set_paypal_event_disposition(
                conn,
                event_id,
                "applied" if processed else "already_terminal",
            )
        else:
            _set_paypal_event_disposition(
                conn,
                event_id,
                "ignored_unsupported",
            )

    return {
        "ok": True,
        "duplicate": False,
        "processed": processed,
    }


@app.post("/license/refresh")
def refresh(req: RefreshReq):
    payload = parse_and_verify_token(req.token)
    now = int(time.time())
    key, device = _validate_refresh_token(payload, req.deviceId, now)

    with db() as conn:
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
            current_period_end=state.get("current_period_end"),
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
    payload = parse_and_verify_token(req.token)
    key, device = _validate_refresh_token(payload, req.deviceId, int(time.time()))
    token_license_identity = canon_key(key)
    if not token_license_identity:
        raise HTTPException(status_code=400, detail="invalid-token")
    if req.key is not None:
        requested_license_identity = canon_key(req.key)
        if (
            not requested_license_identity
            or not secrets.compare_digest(
                token_license_identity,
                requested_license_identity,
            )
        ):
            raise HTTPException(status_code=400, detail="license-mismatch")

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
            (key, device),
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
_ADMIN_CSRF_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{32,128}$")

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


def _csrf_token_for_request(request: Request) -> str:
    existing = str(request.cookies.get(CSRF_COOKIE_NAME) or "")
    if _ADMIN_CSRF_TOKEN_RE.fullmatch(existing):
        return existing
    return _issue_csrf_token()


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
    csrf_token = _csrf_token_for_request(request)
    response = TEMPLATES.TemplateResponse(
        request,
        "dashboard.html",
        {
            "rows": rows,
            "q": q or "",
            "csrf_token": csrf_token,
            "default_subscription_term_days": DEFAULT_SUBSCRIPTION_TERM_DAYS,
        },
    )
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
    with db() as conn:
        keys = []
        for _ in range(max(1, int(count))):
            k = _generate_license_key()
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
    csrf_token = _csrf_token_for_request(request)
    response = TEMPLATES.TemplateResponse(
        request,
        "license_detail.html",
        {
            "lic": lic,
            "acts": acts,
            "csrf_token": csrf_token,
            "default_subscription_term_days": DEFAULT_SUBSCRIPTION_TERM_DAYS,
        },
    )
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
    csrf_token = _csrf_token_for_request(request)
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
def admin_login_post(
    request: Request,
    token: str = Form(...),
    csrf_token: str = Form(...),
):
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
    _set_csrf_cookie(resp, request, _issue_csrf_token())
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
