import importlib.util
import json
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent


def _load_app_module():
    app_path = BACKEND_DIR / "app.py"
    spec = importlib.util.spec_from_file_location("backend_app_metadata_test", app_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _load_build_metadata_module():
    module_path = BACKEND_DIR / "build_metadata.py"
    spec = importlib.util.spec_from_file_location("backend_build_metadata_test", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_version_endpoint_returns_coherent_metadata():
    module = _load_app_module()
    client = module.app.test_client()
    frontend_package = json.loads(
        (BACKEND_DIR.parent / "frontend" / "package.json").read_text(encoding="utf-8")
    )

    response = client.get("/api/version")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["app_version"] == module.APP_VERSION
    assert module.APP_VERSION == frontend_package["version"]
    assert payload["api_version"] == module.API_VERSION
    assert payload["engine_version"] == module.ENGINE_VERSION
    assert payload["release_date"] == module.RELEASE_DATE
    assert isinstance(payload.get("backend_build"), dict)
    assert payload["backend_build"].get("metadata_source")
    assert isinstance((payload["backend_build"].get("git") or {}), dict)
    assert isinstance(payload.get("features"), list)
    assert payload["ready"] is True
    assert payload["status"] == "ready"
    assert payload["readiness"]["astro_clock_blueprint"]["status"] == "ready"


def test_health_endpoint_exposes_app_and_api_versions():
    module = _load_app_module()
    client = module.app.test_client()

    response = client.get("/api/health?skip_network=true")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["version"] == module.APP_VERSION
    assert payload["api_version"] == module.API_VERSION
    assert payload["engine_version"] == module.ENGINE_VERSION
    assert payload["release_date"] == module.RELEASE_DATE
    assert isinstance(payload.get("backend_build"), dict)
    assert payload["ready"] is True
    assert payload["services"]["astro_clock_blueprint"]["status"] == "healthy"


def test_metrics_endpoint_aggregates_bounded_astro_clock_runtime(monkeypatch):
    module = _load_app_module()
    client = module.app.test_client()
    expected = {
        "restart_volatile": True,
        "executor": {"workers": 2, "queued": 1, "queue_capacity": 4},
        "sessions": {"research_compile": {"total": 2, "active": 1, "terminal": 1}},
    }
    monkeypatch.setattr(module, "should_bypass_license", lambda: True)
    monkeypatch.setattr(module, "_ASTRO_CLOCK_BACKGROUND_METRICS", lambda: expected)

    response = client.get("/api/metrics")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["astro_clock_background"] == {
        "available": True,
        **expected,
    }


def test_readiness_endpoints_fail_when_astro_clock_blueprint_is_unavailable(
    monkeypatch,
):
    module = _load_app_module()
    client = module.app.test_client()
    monkeypatch.setattr(module, "_ASTRO_CLOCK_BLUEPRINT_READY", False)
    monkeypatch.setattr(module, "_ASTRO_CLOCK_BLUEPRINT_ERROR", "ImportError")

    version_response = client.get("/api/version")
    health_response = client.get("/api/health?skip_network=true")

    assert version_response.status_code == 503
    version_payload = version_response.get_json()
    assert version_payload["ready"] is False
    assert version_payload["status"] == "not_ready"
    assert version_payload["readiness"]["astro_clock_blueprint"] == {
        "status": "unavailable",
        "error": "ImportError",
    }

    assert health_response.status_code == 503
    health_payload = health_response.get_json()
    assert health_payload["ready"] is False
    assert health_payload["status"] == "unhealthy"
    assert health_payload["services"]["astro_clock_blueprint"] == {
        "status": "unhealthy",
        "error": "ImportError",
    }


def test_build_metadata_loader_reads_pyinstaller_internal_path(tmp_path):
    build_metadata = _load_build_metadata_module()

    internal_dir = tmp_path / "_internal"
    internal_dir.mkdir(parents=True)
    expected = {
        "metadata_version": 1,
        "runtime_kind": "pyinstaller_bundle",
        "built_at_utc": "2026-04-18T12:45:00+00:00",
    }
    (internal_dir / "build_metadata.json").write_text(json.dumps(expected), encoding="utf-8")

    payload = build_metadata.load_build_metadata(tmp_path)

    assert payload["metadata_source"] == "file"
    assert payload["runtime_kind"] == "pyinstaller_bundle"
    assert payload["built_at_utc"] == expected["built_at_utc"]


def test_git_metadata_distinguishes_clean_dirty_and_unavailable_status(monkeypatch, tmp_path):
    build_metadata = _load_build_metadata_module()

    base_values = {
        ("rev-parse", "HEAD"): "a" * 40,
        ("rev-parse", "--short", "HEAD"): "a" * 7,
        ("rev-parse", "--abbrev-ref", "HEAD"): "main",
        ("rev-parse", "HEAD^{tree}"): "b" * 40,
    }

    def probe_with(status):
        monkeypatch.setattr(
            build_metadata,
            "_run_git",
            lambda args, *, cwd: (
                status
                if tuple(args) == ("status", "--short", "--untracked-files=all")
                else base_values.get(tuple(args))
            ),
        )
        return build_metadata.detect_git_metadata(tmp_path)

    assert probe_with("")["dirty"] is False
    assert probe_with(" M backend/app.py")["dirty"] is True
    assert "dirty" not in probe_with(None)


def test_chart_request_log_summary_redacts_raw_values():
    module = _load_app_module()

    question = "Will I get the job?"
    location = "Jerusalem, Israel"
    summary = module._chart_request_log_summary(
        question=question,
        location=location,
        date_str="02/04/2026",
        time_str="13:37",
        timezone_str="Asia/Jerusalem",
        use_current_time=False,
        manual_houses="1st=Aries",
        use_reasoning_v1=True,
    )

    assert summary == {
        "question_chars": len(question),
        "location_chars": len(location),
        "custom_date_supplied": True,
        "custom_time_supplied": True,
        "timezone_supplied": True,
        "use_current_time": False,
        "manual_houses": True,
        "use_reasoning_v1": True,
    }
    assert question not in str(summary)
    assert location not in str(summary)


def test_calculate_chart_forwards_coordinate_overrides(monkeypatch):
    module = _load_app_module()
    client = module.app.test_client()

    captured = {}

    class DummyEngine:
        def judge(self, question, settings):
            captured["question"] = question
            captured["settings"] = settings
            return {
                "judgment": "YES",
                "confidence": 77,
                "reasoning": [],
                "chart_data": None,
            }

    monkeypatch.setattr(module, "horary_engine", DummyEngine())
    monkeypatch.setattr(module, "should_bypass_license", lambda: True)

    response = client.post(
        "/api/calculate-chart",
        json={
            "question": "Will I get the job?",
            "location": "New York, NY, USA",
            "useCurrentTime": False,
            "date": "18/04/2026",
            "time": "06:30",
            "timezone": "America/New_York",
            "latitude": 40.7128,
            "longitude": -74.006,
            "locationName": "New York, New York, United States",
        },
    )

    assert response.status_code == 200
    assert captured["question"] == "Will I get the job?"
    assert captured["settings"]["location"] == "New York, NY, USA"
    assert captured["settings"]["location_name"] == "New York, New York, United States"
    assert captured["settings"]["latitude"] == 40.7128
    assert captured["settings"]["longitude"] == -74.006


def test_calculate_chart_maps_engine_location_error_to_bad_request(monkeypatch):
    module = _load_app_module()
    client = module.app.test_client()

    class LocationFailureEngine:
        def judge(self, _question, _settings):
            return {
                "error": "Location was not found",
                "judgment": "LOCATION_ERROR",
                "confidence": 0,
                "reasoning": [],
                "error_type": "LocationError",
            }

    monkeypatch.setattr(module, "horary_engine", LocationFailureEngine())
    monkeypatch.setattr(module, "should_bypass_license", lambda: True)

    response = client.post(
        "/api/calculate-chart",
        json={
            "question": "Will I get the job?",
            "location": "Missing Place",
            "useCurrentTime": True,
        },
    )

    assert response.status_code == 400
    payload = response.get_json()
    assert payload["judgment"] == "LOCATION_ERROR"
    assert payload["error_type"] == "LocationError"
