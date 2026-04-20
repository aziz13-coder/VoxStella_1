import importlib.util
from pathlib import Path
from uuid import uuid4


APP_PATH = Path(__file__).with_name("app.py")


def _load_module():
    module_name = f"licensing_server_app_test_{uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, APP_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_public_routes_are_available_without_admin_token(monkeypatch):
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("ADMIN_TOKEN_FILE", raising=False)

    module = _load_module()

    root = module.index(request=None)
    assert root.status_code == 200
    assert "Public /license/* endpoints remain available." in root.body.decode("utf-8")

    admin_login = module.admin_login_get(request=None)
    assert admin_login.status_code == 503
    assert "Admin UI is disabled" in admin_login.body.decode("utf-8")
