import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
OUTPUT_PATH = REPO_ROOT / "tests" / "fixtures" / "synastry_historical_replay_slice_2.json"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from astro_clock_api import _compute_chart_for


CASES = [
    {
        "id": "frida_kahlo_diego_rivera",
        "title": "Frida Kahlo and Diego Rivera",
        "partner_a": "Frida Kahlo",
        "partner_b": "Diego Rivera",
        "relationship_type": "marriage",
        "public_outcome_summary": "A creatively important and deeply impactful bond marked by growth, attraction, strain, and burden.",
        "birth_data_confidence": "AA/DD",
        "source_basis": "public_biographical_consensus_with_timed_astrology_sources",
        "execution_tier": "tier_2_replay_ready",
        "expected_dimensions": {
            "growth": {"min_band": 4, "max_band": 5, "priority": "primary"},
            "burden": {"min_band": 3, "max_band": 5, "priority": "primary"},
            "attraction": {"min_band": 3, "max_band": 5, "priority": "secondary"},
        },
        "birth_metadata_a": {
            "datetime_iso": "1907-07-06T08:30:00-06:36:40",
            "location": "Coyoacan, Mexico City, Mexico",
            "timezone": "America/Mexico_City",
            "confidence": "AA",
            "source_note": "Astro-Databank lists Frida Kahlo as born on 6 July 1907 at 08:30 in Coyoacan, Mexico City; search snippets and mirror references indicate the data was upgraded to Rodden AA from the birth registry. The recorded time is expressed against historical local mean time for Mexico City, so the frozen snapshot preserves the source instant via explicit offset.",
            "sources": [
                "https://www.astro.com/astro-databank/Kahlo,_Frida",
            ],
        },
        "birth_metadata_b": {
            "datetime_iso": "1886-12-08T19:30:00-06:45:00",
            "location": "Guanajuato, Guanajuato, Mexico",
            "timezone": "America/Mexico_City",
            "confidence": "DD",
            "source_note": "Astro-Databank lists Diego Rivera as born on 8 December 1886 at 19:30 in Guanajuato, Mexico with Rodden DD, quoting a biographical source and noting conflicting timed data. The source is given in historical local mean time; the frozen snapshot preserves the source instant via explicit offset.",
            "sources": [
                "https://www.astro.com/astro-databank/Rivera,_Diego",
            ],
        },
        "source_references": [
            "https://www.astro.com/astro-databank/Kahlo,_Frida",
            "https://www.astro.com/astro-databank/Rivera,_Diego",
        ],
        "chart_capture_note": "Frozen from the local AstroClock backend to expand replay coverage beyond the original two couples. This pair is replay-ready but uses mixed-confidence public timed data.",
        "options": {
            "include_modern": True,
            "include_nodes": True,
            "include_chiron": False,
            "orb_profile": "balanced",
        },
    },
    {
        "id": "sid_nancy",
        "title": "Sid Vicious and Nancy Spungen",
        "partner_a": "Sid Vicious",
        "partner_b": "Nancy Spungen",
        "relationship_type": "romantic_relationship",
        "public_outcome_summary": "A highly intense bond associated with volatility, burden, and destructive pressure.",
        "birth_data_confidence": "A/B",
        "source_basis": "public_biographical_consensus_with_timed_astrology_sources",
        "execution_tier": "tier_2_replay_ready",
        "expected_dimensions": {
            "friction": {"min_band": 4, "max_band": 5, "priority": "primary"},
            "burden": {"min_band": 4, "max_band": 5, "priority": "primary"},
            "attraction": {"min_band": 3, "max_band": 5, "priority": "secondary"},
        },
        "birth_metadata_a": {
            "datetime_iso": "1957-05-10T19:09:00+01:00",
            "location": "London, England",
            "timezone": "Europe/London",
            "confidence": "A",
            "source_note": "Astro-Databank lists Sid Vicious as born on 10 May 1957 at 19:09 in London with Rodden A from his mother.",
            "sources": [
                "https://www.astro.com/astro-databank/Vicious,_Sid",
            ],
        },
        "birth_metadata_b": {
            "datetime_iso": "1958-02-27T06:52:00-05:00",
            "location": "Philadelphia, Pennsylvania",
            "timezone": "America/New_York",
            "confidence": "B",
            "source_note": "Astro-Databank lists Nancy Spungen as born on 27 February 1958 at 06:52 in Philadelphia with Rodden B, sourced from biography/autobiography style material.",
            "sources": [
                "https://www.astro.com/astro-databank/Spungen,_Nancy",
            ],
        },
        "source_references": [
            "https://www.astro.com/astro-databank/Vicious,_Sid",
            "https://www.astro.com/astro-databank/Spungen,_Nancy",
        ],
        "chart_capture_note": "Frozen from the local AstroClock backend to add a destructive-intensity real-world case to the replay audit.",
        "options": {
            "include_modern": True,
            "include_nodes": True,
            "include_chiron": False,
            "orb_profile": "balanced",
        },
    },
    {
        "id": "elizabeth_taylor_richard_burton",
        "title": "Elizabeth Taylor and Richard Burton",
        "partner_a": "Elizabeth Taylor",
        "partner_b": "Richard Burton",
        "relationship_type": "marriage",
        "public_outcome_summary": "Very strong attraction and attachment, but also conflict, volatility, and repeated instability.",
        "birth_data_confidence": "AA/DD",
        "source_basis": "public_biographical_consensus_with_timed_astrology_sources",
        "execution_tier": "tier_2_replay_ready",
        "expected_dimensions": {
            "attraction": {"min_band": 4, "max_band": 5, "priority": "primary"},
            "friction": {"min_band": 4, "max_band": 5, "priority": "primary"},
            "attachment": {"min_band": 3, "max_band": 5, "priority": "secondary"},
        },
        "birth_metadata_a": {
            "datetime_iso": "1932-02-27T02:30:00+00:00",
            "location": "London, England",
            "timezone": "Europe/London",
            "confidence": "AA",
            "source_note": "Astro-Databank lists Elizabeth Taylor as born on 27 February 1932 at 02:30 in London with Rodden AA from the birth certificate.",
            "sources": [
                "https://www.astro.com/astro-databank/Taylor,_Elizabeth",
            ],
        },
        "birth_metadata_b": {
            "datetime_iso": "1925-11-10T15:00:00+00:00",
            "location": "Pontrhydyfen, Wales, United Kingdom",
            "timezone": "Europe/London",
            "confidence": "DD",
            "source_note": "Astro-Databank lists Richard Burton as born on 10 November 1925 at 15:00 in Pontrhydyfen, Wales with Rodden DD, citing biographical reporting and noting that the timed data is not secure.",
            "sources": [
                "https://www.astro.com/astro-databank/Burton,_Richard_(1925)",
            ],
        },
        "source_references": [
            "https://www.astro.com/astro-databank/Taylor,_Elizabeth",
            "https://www.astro.com/astro-databank/Burton,_Richard_(1925)",
        ],
        "chart_capture_note": "Frozen from the local AstroClock backend to add a high-chemistry unstable marriage to the replay audit with explicit mixed-confidence sourcing.",
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
        "generated_at": "2026-04-03T14:30:00+03:00",
        "purpose": "Second replay-ready synastry historical validation slice with broader real-couple archetypes and frozen chart snapshots.",
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
