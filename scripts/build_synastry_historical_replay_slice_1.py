import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
OUTPUT_PATH = REPO_ROOT / "tests" / "fixtures" / "synastry_historical_replay_slice_1.json"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from astro_clock_api import _compute_chart_for


CASES = [
    {
        "id": "paul_newman_joanne_woodward",
        "title": "Paul Newman and Joanne Woodward",
        "partner_a": "Paul Newman",
        "partner_b": "Joanne Woodward",
        "relationship_type": "marriage",
        "public_outcome_summary": "Widely regarded as a durable long-term bond with high loyalty and staying power.",
        "birth_data_confidence": "AA",
        "source_basis": "public_biographical_consensus_with_timed_astrology_sources",
        "execution_tier": "tier_2_replay_ready",
        "expected_dimensions": {
            "attachment": {"min_band": 4, "max_band": 5, "priority": "primary"},
            "compatibility": {"min_band": 3, "max_band": 5, "priority": "primary"},
            "burden": {"min_band": 0, "max_band": 2, "priority": "secondary"},
        },
        "birth_metadata_a": {
            "datetime_iso": "1925-01-26T06:30:00-05:00",
            "location": "Cleveland, Ohio",
            "timezone": "America/New_York",
            "confidence": "AA",
            "source_note": "Astro-Databank search snippet shows 6:30 AM in Cleveland with Rodden AA.",
            "sources": [
                "https://www.astro.com/astro-databank/Newman,_Paul",
            ],
        },
        "birth_metadata_b": {
            "datetime_iso": "1930-02-27T04:00:00-05:00",
            "location": "Thomasville, Georgia",
            "timezone": "America/New_York",
            "confidence": "AA",
            "source_note": "Astro-Databank search snippet shows 4:00 AM in Thomasville with Rodden AA.",
            "sources": [
                "https://www.astro.com/astro-databank/Woodward,_Joanne",
            ],
        },
        "source_references": [
            "https://www.astro.com/astro-databank/Newman,_Paul",
            "https://www.astro.com/astro-databank/Woodward,_Joanne",
        ],
        "chart_capture_note": "Frozen from the local AstroClock backend to avoid future geocoding drift during replay.",
        "options": {
            "include_modern": True,
            "include_nodes": True,
            "include_chiron": False,
            "orb_profile": "balanced",
        },
    },
    {
        "id": "charles_diana",
        "title": "Charles and Diana",
        "partner_a": "Charles",
        "partner_b": "Diana",
        "relationship_type": "marriage",
        "public_outcome_summary": "Publicly visible relationship with major strain, mismatch, and burden rather than easy compatibility.",
        "birth_data_confidence": "A",
        "source_basis": "public_biographical_consensus_with_timed_astrology_sources",
        "execution_tier": "tier_2_replay_ready",
        "expected_dimensions": {
            "burden": {"min_band": 4, "max_band": 5, "priority": "primary"},
            "friction": {"min_band": 3, "max_band": 5, "priority": "primary"},
            "compatibility": {"min_band": 0, "max_band": 2, "priority": "secondary"},
        },
        "birth_metadata_a": {
            "datetime_iso": "1948-11-14T21:14:00+00:00",
            "location": "London, England",
            "timezone": "Europe/London",
            "confidence": "A",
            "source_note": "Search snippet reproduces Astro-Databank's rectified 21:14 time with Rodden A / birth-certificate note.",
            "sources": [
                "https://www.astro.com/astro-databank/Charles_III,_King_of_the_United_Kingdom",
            ],
        },
        "birth_metadata_b": {
            "datetime_iso": "1961-07-01T19:45:00+01:00",
            "location": "Sandringham, England",
            "timezone": "Europe/London",
            "confidence": "A",
            "source_note": "Public astrology references consistently use 19:45 in Sandringham with Rodden A.",
            "sources": [
                "https://www.astro.com/astro-databank/Diana,_Princess_of_Wales",
            ],
        },
        "source_references": [
            "https://www.astro.com/astro-databank/Charles_III,_King_of_the_United_Kingdom",
            "https://www.astro.com/astro-databank/Diana,_Princess_of_Wales",
        ],
        "chart_capture_note": "Frozen from the local AstroClock backend to avoid future geocoding drift during replay.",
        "options": {
            "include_modern": True,
            "include_nodes": True,
            "include_chiron": False,
            "orb_profile": "balanced",
        },
    },
]


def _compute_snapshot(case, suffix):
    birth = case[f"birth_metadata_{suffix}"]
    sink = io.StringIO()
    with redirect_stdout(sink):
        chart_data, meta = _compute_chart_for(
            birth["datetime_iso"],
            birth["location"],
            birth["timezone"],
        )
    return {
        "chart_data": chart_data,
        "chart_meta": {
            "id": f"{case['id']}-{suffix}",
            "label": case[f"partner_{suffix}"],
            "effective_datetime": meta.get("timestamp") or birth["datetime_iso"],
            "location": meta.get("location") or birth["location"],
            "timezone": meta.get("timezone") or birth["timezone"],
            "birth_data_confidence": birth["confidence"],
        },
    }


def main():
    payload = {
        "generated_at": "2026-04-03T19:15:00+03:00",
        "purpose": "First replay-ready synastry historical validation slice with frozen chart snapshots.",
        "cases": [],
    }

    for case in CASES:
        case_payload = dict(case)
        snap_a = _compute_snapshot(case, "a")
        snap_b = _compute_snapshot(case, "b")
        case_payload["chart_data_a"] = snap_a["chart_data"]
        case_payload["chart_data_b"] = snap_b["chart_data"]
        case_payload["chart_meta_a"] = snap_a["chart_meta"]
        case_payload["chart_meta_b"] = snap_b["chart_meta"]
        payload["cases"].append(case_payload)

    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
