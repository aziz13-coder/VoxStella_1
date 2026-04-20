from __future__ import annotations

import sys
from pathlib import Path


repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

from tests.trait_profile_replay_utils import (
    load_trait_replay_cases,
    make_trait_replay_app,
    patch_trait_replay_geocode,
    replay_trait_case,
)


def test_trait_profile_replay_slice_1_expected_family_presence(monkeypatch):
    fixture = load_trait_replay_cases()
    cases = fixture["cases"]

    patch_trait_replay_geocode(monkeypatch, cases)
    app = make_trait_replay_app()
    client = app.test_client()

    for case in cases:
        response, payload = replay_trait_case(client, case)

        assert response.status_code == 200, case["subject"]
        assert payload["success"] is True, case["subject"]

        traits_by_id = {trait["id"]: trait for trait in (payload["data"].get("traits") or [])}
        matched = []
        for trait_id in case["expected_traits"]:
            trait = traits_by_id.get(trait_id)
            if trait and float(trait.get("score") or 0.0) >= float(case["min_score"]):
                matched.append((trait_id, trait["score"], trait.get("band")))

        assert len(matched) >= int(case["min_matches"]), (
            f"{case['subject']}: expected >= {case['min_matches']} family matches at >= {case['min_score']}, "
            f"got {matched}. Top traits: "
            f"{[(t['id'], t['score'], t.get('band')) for t in (payload['data'].get('top_traits') or [])[:8]]}"
        )


def test_trait_profile_replay_slice_1_returns_nonempty_profile_payload(monkeypatch):
    fixture = load_trait_replay_cases()
    cases = fixture["cases"]

    patch_trait_replay_geocode(monkeypatch, cases)
    app = make_trait_replay_app()
    client = app.test_client()

    for case in cases:
        response, payload = replay_trait_case(client, case)

        assert response.status_code == 200, case["subject"]
        assert payload["success"] is True, case["subject"]

        data = payload["data"]
        assert data["summary"] is not None, case["subject"]
        assert data["top_traits"], case["subject"]
        assert data["summary_traits"], case["subject"]
        assert data["top_traits_by_polarity"], case["subject"]
        assert data["traits"], case["subject"]
        assert data["chart_snapshot"]["location"] == case["location"], case["subject"]
        assert data["chart_snapshot"]["house_system"] == case["house_system_code"], case["subject"]


def test_trait_profile_replay_slice_1_summary_contract_invariants(monkeypatch):
    fixture = load_trait_replay_cases()
    cases = fixture["cases"]

    patch_trait_replay_geocode(monkeypatch, cases)
    app = make_trait_replay_app()
    client = app.test_client()

    for case in cases:
        response, payload = replay_trait_case(client, case)

        assert response.status_code == 200, case["subject"]
        assert payload["success"] is True, case["subject"]

        data = payload["data"]
        all_traits = data.get("traits") or []
        summary_traits = data.get("summary_traits") or []
        by_polarity = data.get("top_traits_by_polarity") or {}

        all_ids = {trait["id"] for trait in all_traits}
        summary_ids = {trait["id"] for trait in summary_traits}

        assert summary_traits, case["subject"]
        assert summary_ids.issubset(all_ids), case["subject"]
        assert all(trait.get("summary_eligible") is not False for trait in summary_traits), case["subject"]
        assert all(trait.get("family_representative") is not False for trait in summary_traits), case["subject"]

        for polarity in ("positive", "neutral", "negative"):
            entries = by_polarity.get(polarity) or []
            for entry in entries:
                assert entry["id"] in summary_ids, case["subject"]
                assert str(entry.get("polarity") or "").strip().lower() == polarity, case["subject"]
