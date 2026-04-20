from __future__ import annotations

from pathlib import Path

from tests.trait_profile_replay_utils import (
    load_trait_replay_cases,
    make_trait_replay_app,
    patch_trait_replay_geocode,
    replay_trait_case,
)


SLICE_2_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "trait_profile_replay_slice_2.json"


def test_trait_profile_replay_slice_2_intellectual_summary_presence(monkeypatch):
    fixture = load_trait_replay_cases(SLICE_2_FIXTURE)
    cases = fixture["cases"]

    patch_trait_replay_geocode(monkeypatch, cases)
    app = make_trait_replay_app()
    client = app.test_client()

    for case in cases:
        response, payload = replay_trait_case(client, case)

        assert response.status_code == 200, case["subject"]
        assert payload["success"] is True, case["subject"]

        data = payload["data"]
        top_ids = {trait["id"] for trait in (data.get("top_traits") or [])}
        summary_ids = {trait["id"] for trait in (data.get("summary_traits") or [])}
        positive_ids = {
            trait["id"]
            for trait in ((data.get("top_traits_by_polarity") or {}).get("positive") or [])
        }

        top_matches = [trait_id for trait_id in case["expected_top_traits"] if trait_id in top_ids]
        summary_matches = [
            trait_id for trait_id in case["expected_summary_traits"] if trait_id in summary_ids
        ]
        positive_matches = [
            trait_id
            for trait_id in case["expected_positive_polarity"]
            if trait_id in positive_ids
        ]

        assert len(top_matches) >= int(case["min_top_matches"]), (
            f"{case['subject']}: expected >= {case['min_top_matches']} top intellectual matches, "
            f"got {top_matches}. Top traits: "
            f"{[(t['id'], t['score'], t.get('band')) for t in (data.get('top_traits') or [])[:10]]}"
        )
        assert len(summary_matches) >= int(case["min_summary_matches"]), (
            f"{case['subject']}: expected >= {case['min_summary_matches']} summary intellectual matches, "
            f"got {summary_matches}. Summary traits: "
            f"{[(t['id'], t['score'], t.get('band')) for t in (data.get('summary_traits') or [])[:12]]}"
        )
        assert len(positive_matches) >= int(case["min_positive_matches"]), (
            f"{case['subject']}: expected >= {case['min_positive_matches']} positive-polarity intellectual matches, "
            f"got {positive_matches}. Positive polarity: "
            f"{[(t['id'], t['score'], t.get('band')) for t in ((data.get('top_traits_by_polarity') or {}).get('positive') or [])[:12]]}"
        )
