import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
REPLAY_FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "forensic_case_replay_slice_1.json"

if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))
if str(REPO_ROOT / "backend") not in sys.path:
    sys.path.append(str(REPO_ROOT / "backend"))


def load_forensic_replay_cases(path=REPLAY_FIXTURE_PATH):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return payload.get("cases") or []


def make_forensic_replay_app():
    from flask import Flask
    import backend.astro_clock_api as astro_clock_api

    app = Flask(__name__)
    app.register_blueprint(astro_clock_api.astro_clock_bp)
    app.testing = True
    return app


def build_forensic_query_string(case):
    query = dict(case.get("query") or {})
    return {
        "mode": query.get("mode") or "manual",
        "datetime": query.get("datetime_local"),
        "location": query.get("location"),
        "timezone": query.get("timezone"),
        "house_system_code": query.get("house_system_code") or "R",
    }
