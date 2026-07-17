import base64
import hashlib
import hmac
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from backend_instance import (
    INSTANCE_CHALLENGE_HEADER,
    INSTANCE_PROOF_HEADER,
    build_backend_instance_proof,
    is_valid_instance_challenge,
    load_backend_instance_secret,
)


def test_backend_instance_secret_is_required_and_exact_in_packaged_mode():
    secret = bytes(range(32))
    encoded = base64.b64encode(secret).decode("ascii")

    assert load_backend_instance_secret(
        {
            "APP_IS_PACKAGED": "1",
            "VOX_STELLA_BACKEND_INSTANCE_SECRET_B64": encoded,
        }
    ) == secret

    with pytest.raises(RuntimeError, match="missing"):
        load_backend_instance_secret({"APP_IS_PACKAGED": "1"})
    with pytest.raises(RuntimeError, match="exactly 32"):
        load_backend_instance_secret(
            {
                "APP_IS_PACKAGED": "1",
                "VOX_STELLA_BACKEND_INSTANCE_SECRET_B64": base64.b64encode(b"short").decode("ascii"),
            }
        )


def test_backend_instance_proof_contract_is_path_bound_and_deterministic():
    secret = bytes(range(32))
    challenge = "A" * 43
    expected = hmac.new(
        secret,
        f"{challenge}\n/api/health".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    assert is_valid_instance_challenge(challenge) is True
    assert build_backend_instance_proof(secret, challenge, "/api/health") == expected
    assert build_backend_instance_proof(secret, challenge, "/api/version") != expected
    assert INSTANCE_CHALLENGE_HEADER == "X-VoxStella-Instance-Challenge"
    assert INSTANCE_PROOF_HEADER == "X-VoxStella-Instance-Proof"

    for invalid in ("", "A" * 42, "A" * 44, "!" * 43, None):
        assert is_valid_instance_challenge(invalid) is False


def test_app_proves_instance_without_exposing_secret_or_query(monkeypatch):
    import app as backend_app

    secret = bytes(range(32))
    challenge = "B" * 43
    monkeypatch.setattr(backend_app, "_BACKEND_INSTANCE_SECRET", secret)
    client = backend_app.app.test_client()

    response = client.get(
        "/api/version?ignored=query",
        headers={INSTANCE_CHALLENGE_HEADER: challenge},
    )

    assert response.headers[INSTANCE_PROOF_HEADER] == build_backend_instance_proof(
        secret,
        challenge,
        "/api/version",
    )
    assert base64.b64encode(secret).decode("ascii") not in response.get_data(as_text=True)
    assert INSTANCE_PROOF_HEADER not in str(response.headers.get("Access-Control-Expose-Headers", ""))
