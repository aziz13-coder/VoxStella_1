import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
OUTPUT_PATH = REPO_ROOT / "tests" / "fixtures" / "synastry_historical_replay_slice_3.json"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from astro_clock_api import _compute_chart_for


CASES = [
    {
        "id": "frank_sinatra_ava_gardner",
        "title": "Frank Sinatra and Ava Gardner",
        "partner_a": "Frank Sinatra",
        "partner_b": "Ava Gardner",
        "relationship_type": "marriage",
        "public_outcome_summary": "An iconic high-chemistry marriage marked by glamour, volatility, and repeated instability rather than calm ease.",
        "birth_data_confidence": "A/AA",
        "source_basis": "public_biographical_consensus_with_timed_astrology_sources",
        "execution_tier": "tier_2_replay_ready",
        "expected_dimensions": {
            "attraction": {"min_band": 4, "max_band": 5, "priority": "primary"},
            "friction": {"min_band": 4, "max_band": 5, "priority": "primary"},
            "burden": {"min_band": 3, "max_band": 5, "priority": "secondary"},
        },
        "birth_metadata_a": {
            "datetime_iso": "1915-12-12T03:00:00-05:00",
            "location": "Hoboken, New Jersey",
            "timezone": "America/New_York",
            "confidence": "A",
            "source_note": "Astro-Databank lists Frank Sinatra as born on 12 December 1915 at 03:00 in Hoboken, New Jersey with Rodden Rating A, sourced from family memory.",
            "sources": [
                "https://www.astro.com/astro-databank/Sinatra,_Frank",
            ],
        },
        "birth_metadata_b": {
            "datetime_iso": "1922-12-24T19:10:00-05:00",
            "location": "Boon Hill, North Carolina",
            "timezone": "America/New_York",
            "confidence": "AA",
            "source_note": "Astro-Databank lists Ava Gardner as born on 24 December 1922 at 19:10 in Boon Hill, North Carolina with Rodden Rating AA from quoted birth record data.",
            "sources": [
                "https://www.astro.com/astro-databank/Gardner,_Ava",
            ],
        },
        "source_references": [
            "https://www.astro.com/astro-databank/Sinatra,_Frank",
            "https://www.astro.com/astro-databank/Gardner,_Ava",
        ],
        "chart_capture_note": "Frozen from the local AstroClock backend to add a better-timed glamour-and-volatility marriage to the replay surface after the attraction-family audit.",
        "options": {
            "include_modern": True,
            "include_nodes": True,
            "include_chiron": False,
            "orb_profile": "balanced",
        },
    },
    {
        "id": "sartre_beauvoir",
        "title": "Jean-Paul Sartre and Simone de Beauvoir",
        "partner_a": "Jean-Paul Sartre",
        "partner_b": "Simone de Beauvoir",
        "relationship_type": "lifelong_companionship",
        "public_outcome_summary": "A lifelong intellectually fused bond with unusual commitment, growth, and complexity rather than conventional romance or simplicity.",
        "birth_data_confidence": "AA/AA",
        "source_basis": "public_biographical_consensus_with_timed_astrology_sources",
        "execution_tier": "tier_2_replay_ready",
        "expected_dimensions": {
            "attachment": {"min_band": 4, "max_band": 5, "priority": "primary"},
            "growth": {"min_band": 4, "max_band": 5, "priority": "primary"},
            "burden": {"min_band": 2, "max_band": 4, "priority": "secondary"},
        },
        "birth_metadata_a": {
            "datetime_iso": "1905-06-21T18:45:00+00:09:21",
            "location": "Paris, France",
            "timezone": "Europe/Paris",
            "confidence": "AA",
            "source_note": "Astro-Databank lists Jean-Paul Sartre as born on 21 June 1905 at 18:45 in Paris with Rodden Rating AA from birth record data. The source record uses Paris mean time, so the frozen snapshot preserves the source instant via explicit offset.",
            "sources": [
                "https://www.astro.com/astro-databank/Sartre,_Jean-Paul",
            ],
        },
        "birth_metadata_b": {
            "datetime_iso": "1908-01-09T04:30:00+00:09:21",
            "location": "Paris Arrondissement 6, France",
            "timezone": "Europe/Paris",
            "confidence": "AA",
            "source_note": "Astro-Databank lists Simone de Beauvoir as born on 9 January 1908 at 04:30 in Paris Arrondissement 6 with Rodden Rating AA from birth record data. The source record uses Paris mean time, so the frozen snapshot preserves the source instant via explicit offset.",
            "sources": [
                "https://www.astro.com/astro-databank/Beauvoir,_Simone_de",
            ],
        },
        "source_references": [
            "https://www.astro.com/astro-databank/Sartre,_Jean-Paul",
            "https://www.astro.com/astro-databank/Beauvoir,_Simone_de",
        ],
        "chart_capture_note": "Frozen from the local AstroClock backend to add a stronger-timed lifelong companionship case with heavy intellectual attachment and non-conventional structure.",
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
        "generated_at": "2026-04-03T15:20:00+03:00",
        "purpose": "Third replay-ready synastry historical validation slice extending the attraction audit with a better-timed glamour pair and a stronger-timed lifelong-companionship control.",
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
