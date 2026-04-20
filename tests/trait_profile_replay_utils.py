from __future__ import annotations

import io
import json
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

from flask import Flask


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

import backend.astro_clock_api as astro_clock_api
import backend.astro_clock_engine as astro_clock_engine
import backend.horary_engine.engine as horary_engine_engine
import horary_engine.services.geolocation as geolocation_service


TRAIT_REPLAY_FIXTURE = repo_root / "tests" / "fixtures" / "trait_profile_replay_slice_1.json"


def load_trait_replay_cases(path: Path | None = None) -> Dict[str, Any]:
    target = path or TRAIT_REPLAY_FIXTURE
    return json.loads(Path(target).read_text(encoding="utf-8"))


def make_trait_replay_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(astro_clock_api.astro_clock_bp)
    app.testing = True
    return app


def patch_trait_replay_geocode(monkeypatch, cases: Iterable[Dict[str, Any]]):
    coord_map = {
        case["location"]: (
            case["coordinates"]["lat"],
            case["coordinates"]["lon"],
            case.get("country_label") or "",
        )
        for case in cases
    }

    def fake_geocode(location: str) -> Tuple[float, float, str]:
        if location in coord_map:
            return coord_map[location]
        raise RuntimeError(f"Unmapped replay location: {location!r}")

    monkeypatch.setattr(astro_clock_api, "safe_geocode", fake_geocode)
    monkeypatch.setattr(astro_clock_engine, "safe_geocode", fake_geocode)
    monkeypatch.setattr(geolocation_service, "safe_geocode", fake_geocode)
    monkeypatch.setattr(horary_engine_engine, "safe_geocode", fake_geocode)
    return fake_geocode


def replay_trait_case(client, case: Dict[str, Any]):
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        response = client.get(
            "/api/astro-clock/traits/profile",
            query_string={
                "mode": "manual",
                "datetime": case["replay_datetime_utc"],
                "location": case["location"],
                "timezone": case["timezone"],
                "house_system_code": case["house_system_code"],
            },
        )
    return response, response.get_json()
