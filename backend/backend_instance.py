from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import os
import re
from collections.abc import Mapping

INSTANCE_SECRET_ENV = "VOX_STELLA_BACKEND_INSTANCE_SECRET_B64"
INSTANCE_CHALLENGE_HEADER = "X-VoxStella-Instance-Challenge"
INSTANCE_PROOF_HEADER = "X-VoxStella-Instance-Proof"
_CHALLENGE_RE = re.compile(r"^[A-Za-z0-9_-]{43}$")


def _truthy(value: object) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def load_backend_instance_secret(
    environ: Mapping[str, str] | None = None,
    *,
    required: bool | None = None,
) -> bytes | None:
    env = os.environ if environ is None else environ
    if required is None:
        required = _truthy(env.get("APP_IS_PACKAGED"))
    encoded = str(env.get(INSTANCE_SECRET_ENV) or "").strip()
    if not encoded:
        if required:
            raise RuntimeError("Packaged backend instance secret is missing")
        return None
    try:
        secret = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise RuntimeError("Backend instance secret is not valid base64") from exc
    if len(secret) != 32:
        raise RuntimeError("Backend instance secret must decode to exactly 32 bytes")
    return secret


def is_valid_instance_challenge(challenge: object) -> bool:
    return isinstance(challenge, str) and bool(_CHALLENGE_RE.fullmatch(challenge))


def build_backend_instance_proof(
    secret: bytes,
    challenge: str,
    request_path: str,
) -> str:
    if not isinstance(secret, bytes) or len(secret) != 32:
        raise ValueError("Backend instance proof requires a 32-byte secret")
    if not is_valid_instance_challenge(challenge):
        raise ValueError("Backend instance challenge is invalid")
    path = str(request_path or "")
    if not path.startswith("/") or "\n" in path or "\r" in path:
        raise ValueError("Backend instance request path is invalid")
    message = f"{challenge}\n{path}".encode("utf-8")
    return hmac.new(secret, message, hashlib.sha256).hexdigest()
