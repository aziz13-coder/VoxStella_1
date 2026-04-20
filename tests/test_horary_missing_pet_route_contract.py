from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

import backend.app as app_module  # noqa: E402
import horary_engine.engine as route_engine_module  # noqa: E402


def _post_chart(
    question: str,
    *,
    location: str = "Naples, New York",
    date: str = "2025-01-06",
    time: str = "23:19",
    timezone: str = "America/New_York",
    coords=(42.6152778, -77.4027778, "Naples, New York"),
):
    app_module.app.testing = True
    client = app_module.app.test_client()

    with mock.patch.object(app_module, "should_bypass_license", return_value=True), mock.patch.object(
        route_engine_module,
        "safe_geocode",
        lambda _location: coords,
    ):
        return client.post(
            "/api/calculate-chart",
            json={
                "question": question,
                "location": location,
                "date": date,
                "time": time,
                "timezone": timezone,
                "useCurrentTime": False,
            },
        )


def test_calculate_chart_missing_pet_replay_honors_manual_timestamp_and_emits_location_projection():
    response = _post_chart("Will my dog come home?")

    assert response.status_code == 200
    payload = response.get_json()

    timezone_info = payload["chart_data"]["timezone_info"]
    question_analysis = payload["question_analysis"]
    location_projection = payload["lost_object_location"]

    assert payload["judgment"] == "YES"
    assert payload["confidence"] >= 80
    assert question_analysis["question_type"] == "pet"
    assert question_analysis["pet_analysis"]["family"] == "missing"
    assert question_analysis["relevant_houses"] == [1, 6]
    assert payload["traditional_factors"]["perfection_type"] == "pet_missing_balance"
    assert timezone_info["timezone"] == "America/New_York"
    assert timezone_info["local_time"] == "2025-01-06T23:19:00-05:00"
    assert timezone_info["utc_time"] == "2025-01-07T04:19:00+00:00"
    assert location_projection["applies"] is True
    assert len(location_projection["primary_places"]) >= 1
    assert len(location_projection["directional_cues"]) >= 1
    assert location_projection["directional_cues"][0]["label"] == "West by South"


def test_calculate_chart_pet_recovery_prompt_stays_off_the_missing_pet_location_path():
    response = _post_chart("Will my dog get better?")

    assert response.status_code == 200
    payload = response.get_json()

    question_analysis = payload["question_analysis"]

    assert question_analysis["question_type"] == "pet"
    assert question_analysis["pet_analysis"]["family"] == "recovery"
    assert question_analysis["relevant_houses"] == [1, 6]
    assert payload["traditional_factors"]["perfection_type"] != "pet_missing_balance"
    assert "lost_object_location" not in payload


def test_calculate_chart_missing_cat_alive_replay_denies_when_earlier_frustration_blocks_recovery():
    response = _post_chart(
        "Will I find my cat alive?",
        location="Phoenix, Arizona",
        date="2021-08-03",
        time="02:46",
        timezone="America/Phoenix",
        coords=(33.4484, -112.0740, "Phoenix, Arizona"),
    )

    assert response.status_code == 200
    payload = response.get_json()

    assert payload["judgment"] == "NO"
    assert payload["question_analysis"]["question_type"] == "pet"
    assert payload["question_analysis"]["pet_analysis"]["family"] == "missing"
    assert payload["traditional_factors"]["perfection_type"] == "pet_missing_balance"
    assert payload["chart_data"]["timezone_info"]["local_time"] == "2021-08-03T02:46:00-07:00"
    assert any(
        "pre-empts the apparent recovery route" in entry.get("rule", "")
        for entry in payload.get("reasoning", [])
    )


def test_calculate_chart_biggie_missing_dog_replay_aligns_on_return_and_location_clues():
    response = _post_chart(
        "Where is my pet chow chow Biggie?",
        location="Opelousas, Louisiana",
        date="2005-12-28",
        time="13:18",
        timezone="America/Chicago",
        coords=(30.5335, -92.0815, "Opelousas, Louisiana"),
    )

    assert response.status_code == 200
    payload = response.get_json()

    location_projection = payload["lost_object_location"]

    assert payload["judgment"] == "YES"
    assert payload["question_analysis"]["question_type"] == "pet"
    assert payload["question_analysis"]["pet_analysis"]["family"] == "missing"
    assert payload["traditional_factors"]["perfection_type"] == "pet_missing_balance"
    assert payload["chart_data"]["timezone_info"]["local_time"] == "2005-12-28T13:18:00-06:00"
    assert location_projection["applies"] is True
    assert location_projection["directional_cues"][0]["label"] == "East by South"
    assert any(
        "nearby route" in entry.get("label", "").lower() or "local streets" in entry.get("label", "").lower()
        for entry in location_projection["primary_places"]
    )


def test_calculate_chart_frawley_missing_cat_replay_aligns_on_fast_return_and_hidden_place_clues():
    response = _post_chart(
        "Where is the missing cat?",
        location="London, England",
        date="1993-08-30",
        time="09:20",
        timezone="Europe/London",
        coords=(51.5074, -0.1278, "London, England"),
    )

    assert response.status_code == 200
    payload = response.get_json()

    location_projection = payload["lost_object_location"]

    assert payload["judgment"] == "YES"
    assert payload["question_analysis"]["question_type"] == "pet"
    assert payload["question_analysis"]["pet_analysis"]["family"] == "missing"
    assert payload["traditional_factors"]["perfection_type"] == "pet_missing_balance"
    assert payload["chart_data"]["timezone_info"]["timezone"] == "Europe/London"
    assert payload["chart_data"]["timezone_info"]["local_time"] == "1993-08-30T09:20:00+01:00"
    assert location_projection["applies"] is True
    assert location_projection["directional_cues"][0]["label"] == "West"
    assert any(
        "hidden" in entry.get("label", "").lower() or "difficult-to-reach" in entry.get("label", "").lower()
        for entry in location_projection["primary_places"]
    )
    assert any(
        "supports the animal being found" in entry.get("rule", "")
        for entry in payload.get("reasoning", [])
    )


def test_calculate_chart_pukka_missing_cat_replay_aligns_on_return_and_close_to_home_clues():
    response = _post_chart(
        "Where is the cat?",
        location="Melbourne, Australia",
        date="2007-11-04",
        time="16:48",
        timezone="Australia/Melbourne",
        coords=(-37.8136, 144.9631, "Melbourne, Australia"),
    )

    assert response.status_code == 200
    payload = response.get_json()

    location_projection = payload["lost_object_location"]

    assert payload["judgment"] == "YES"
    assert payload["confidence"] >= 80
    assert payload["question_analysis"]["question_type"] == "pet"
    assert payload["question_analysis"]["pet_analysis"]["family"] == "missing"
    assert payload["traditional_factors"]["perfection_type"] == "pet_missing_balance"
    assert payload["chart_data"]["timezone_info"]["timezone"] == "Australia/Melbourne"
    assert payload["chart_data"]["timezone_info"]["local_time"] == "2007-11-04T16:48:00+11:00"
    assert location_projection["applies"] is True
    assert location_projection["directional_cues"][0]["label"] == "West"
    assert any(
        "close to home" in entry.get("label", "").lower() or "yard" in entry.get("label", "").lower()
        for entry in location_projection["secondary_places"]
    )
    assert any(
        "threshold" in entry.get("label", "").lower() or "entrance" in entry.get("label", "").lower()
        for entry in location_projection["environment_traits"]
    )
