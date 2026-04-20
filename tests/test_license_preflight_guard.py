from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest import TestCase, mock


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

if "licensing" not in sys.modules:
    licensing_stub = types.ModuleType("licensing")

    class _LicenseError(Exception):
        pass

    class _LicenseConfigError(Exception):
        pass

    licensing_stub.LicenseError = _LicenseError
    licensing_stub.LicenseConfigError = _LicenseConfigError
    licensing_stub.extract_bearer_token = lambda _headers: None
    licensing_stub.should_bypass_license = lambda: False
    licensing_stub.verify_license_token = lambda _token: {"sub": "test"}
    sys.modules["licensing"] = licensing_stub

import backend.app as app_module


def _cors_preflight(path: str, method: str):
    app_module.app.testing = True
    client = app_module.app.test_client()
    return client.options(
        path,
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": "content-type,x-license-token",
        },
    )


class LicensePreflightGuardTests(TestCase):
    def test_dev_runtime_helper_enables_local_license_bypass_env(self):
        with mock.patch.dict(app_module.os.environ, {}, clear=True):
            result = app_module.enable_dev_license_bypass_for_source_runtime()

        self.assertEqual(result["VOX_STELLA_ENV"], "development")
        self.assertEqual(result["ALLOW_DEV_LICENSE_BYPASS"], "1")

    def test_license_guard_allows_options_preflight_for_astroclock_mode(self):
        with mock.patch.object(app_module, "should_bypass_license", return_value=False), mock.patch.object(
            app_module,
            "verify_license_token",
            side_effect=AssertionError("verify_license_token should not run for OPTIONS"),
        ):
            response = _cors_preflight("/api/astro-clock/mode", "POST")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers.get("Access-Control-Allow-Origin"))

    def test_license_guard_allows_options_preflight_for_traits_profile(self):
        with mock.patch.object(app_module, "should_bypass_license", return_value=False), mock.patch.object(
            app_module,
            "verify_license_token",
            side_effect=AssertionError("verify_license_token should not run for OPTIONS"),
        ):
            response = _cors_preflight(
                "/api/astro-clock/traits/profile?mode=manual&datetime=2026-03-22T06:32:00&location=Israel&timezone=Asia/Jerusalem&house_system_code=R",
                "GET",
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers.get("Access-Control-Allow-Origin"))

    def test_license_guard_still_blocks_real_astroclock_requests_without_token(self):
        with mock.patch.object(app_module, "should_bypass_license", return_value=False):
            app_module.app.testing = True
            client = app_module.app.test_client()

            mode_response = client.post(
                "/api/astro-clock/mode",
                json={"mode": "manual", "datetime": "2026-03-22T06:32:00", "location": "Israel"},
            )
            traits_response = client.get(
                "/api/astro-clock/traits/profile?mode=manual&datetime=2026-03-22T06:32:00&location=Israel&timezone=Asia/Jerusalem&house_system_code=R"
            )

        self.assertEqual(mode_response.status_code, 402)
        self.assertEqual(traits_response.status_code, 402)
