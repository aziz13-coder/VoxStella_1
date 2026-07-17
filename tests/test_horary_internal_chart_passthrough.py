from __future__ import annotations

import sys
from pathlib import Path


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

import backend.app as app_module


class _SentinelChart:
    pass


def test_calculate_chart_prefers_internal_raw_chart_over_deserialization(monkeypatch):
    sentinel = _SentinelChart()

    def _fake_judge(question, settings):
        assert question == "Will I get a job?"
        assert settings["include_internal_chart"] is True
        return {
            "judgment": "YES",
            "confidence": 61,
            "reasoning": [],
            "chart_data": {"planets": {}, "houses": [], "house_rulers": {}},
            "traditional_factors": {},
            "solar_factors": {},
            "_raw_chart": sentinel,
        }

    def _fake_evaluate(chart_obj, use_dsl=False):
        assert use_dsl is False
        assert chart_obj is sentinel
        return {"ledger": [], "rationale": ["used raw chart"]}

    monkeypatch.setattr(app_module.horary_engine, "judge", _fake_judge)
    monkeypatch.setattr(app_module, "evaluate_chart", _fake_evaluate)
    monkeypatch.setattr(app_module, "should_bypass_license", lambda: True)
    monkeypatch.setattr(
        app_module,
        "deserialize_chart_for_evaluation",
        lambda _chart_data: (_ for _ in ()).throw(AssertionError("deserialize should not be called")),
    )

    app_module.app.testing = True
    client = app_module.app.test_client()

    response = client.post(
        "/api/calculate-chart",
        json={
            "question": "Will I get a job?",
            "location": "Washington, District of Columbia",
            "useCurrentTime": True,
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["rationale"] == []
    assert payload["diagnostic_evaluation"]["rationale"] == ["used raw chart"]
    assert payload["evaluation_consistency"]["status"] == "unavailable"
    assert "_raw_chart" not in payload


def test_calculate_chart_keeps_primary_reasoning_when_evaluator_disagrees(monkeypatch):
    sentinel = _SentinelChart()
    primary_reasoning = [
        {
            "stage": "Primary judgment",
            "rule": "Direct perfection supports yes",
            "weight": 1,
        }
    ]

    monkeypatch.setattr(
        app_module.horary_engine,
        "judge",
        lambda _question, _settings: {
            "judgment": "YES",
            "confidence": 70,
            "reasoning": primary_reasoning,
            "chart_data": {"planets": {}, "houses": [], "house_rulers": {}},
            "_raw_chart": sentinel,
        },
    )
    monkeypatch.setattr(
        app_module,
        "evaluate_chart",
        lambda _chart, use_dsl=False: {
            "verdict": "NO",
            "ledger": [{"key": "secondary_denial", "weight": -1}],
            "rationale": ["secondary evaluator says no"],
        },
    )
    monkeypatch.setattr(app_module, "should_bypass_license", lambda: True)

    response = app_module.app.test_client().post(
        "/api/calculate-chart",
        json={
            "question": "Will I get a job?",
            "location": "Washington, District of Columbia",
            "useCurrentTime": True,
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["judgment"] == "YES"
    assert payload["rationale"] == primary_reasoning
    assert "ledger" not in payload
    assert payload["evaluation_consistency"] == {
        "status": "mismatch",
        "primary_verdict": "YES",
        "secondary_verdict": "NO",
    }
    assert payload["diagnostic_evaluation"]["verdict"] == "NO"
    assert payload["diagnostic_evaluation"]["rationale"] == [
        "secondary evaluator says no"
    ]


def test_calculate_chart_reasoning_v1_keeps_object_schema(monkeypatch):
    sentinel = _SentinelChart()
    primary_reasoning = [
        {
            "stage": "Primary judgment",
            "rule": "Direct perfection supports yes",
            "weight": 1,
        }
    ]

    monkeypatch.setattr(
        app_module.horary_engine,
        "judge",
        lambda _question, _settings: {
            "judgment": "YES",
            "confidence": 70,
            "reasoning": primary_reasoning,
            "chart_data": {"planets": {}, "houses": [], "house_rulers": {}},
            "_raw_chart": sentinel,
        },
    )
    monkeypatch.setattr(
        app_module,
        "evaluate_chart",
        lambda _chart, use_dsl=False: {
            "verdict": "YES",
            "ledger": [],
            "rationale": ["secondary rationale"],
        },
    )
    monkeypatch.setattr(app_module, "should_bypass_license", lambda: True)

    response = app_module.app.test_client().post(
        "/api/calculate-chart?useReasoningV1=true",
        json={
            "question": "Will I get a job?",
            "location": "Washington, District of Columbia",
            "useCurrentTime": True,
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["reasoning_v1"]["version"] == "reasoning.v1"
    assert isinstance(payload["reasoning_v1"]["entries"], list)
    assert payload["reasoning_v1"]["entries"][0]["text"] == (
        "Direct perfection supports yes"
    )
    assert "rationale" not in payload
    assert payload["diagnostic_evaluation"]["agrees_with_primary"] is True
    assert payload["diagnostic_evaluation"]["rationale"] == [
        "secondary rationale"
    ]
