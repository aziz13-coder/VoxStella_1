import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
OUTPUT_PATH = REPO_ROOT / "tests" / "fixtures" / "synastry_content_slice_1.json"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from astro_clock_api import _compute_chart_for


CASES = [
    {
        "id": "justin_bieber_selena_gomez",
        "title": "Justin Bieber and Selena Gomez",
        "partner_a": "Justin Bieber",
        "partner_b": "Selena Gomez",
        "relationship_type": "romantic_relationship",
        "usage_lane": "blog_content_only",
        "calibration_eligible": False,
        "content_eligible": True,
        "validation_recommendation": "blog_demo_only",
        "content_status": "captured_content_slice_1",
        "content_angle": "High-search-interest on/off celebrity romance with attraction, friction, and recurring attachment themes.",
        "target_queries": [
            "Justin Bieber Selena Gomez astrology",
            "Justin Bieber Selena Gomez synastry",
            "Justin Bieber Selena Gomez compatibility",
        ],
        "birth_data_summary": {
            "timed_data_confidence": "B",
            "summary": "Public timed data is usable for content work but not strong enough for calibration-grade validation.",
        },
        "birth_metadata_a": {
            "datetime_iso": "1994-03-01T00:56:00-05:00",
            "location": "London, Ontario, Canada",
            "timezone": "America/Toronto",
            "confidence": "B",
            "source_note": "Astro-Databank lists Justin Bieber as born on 1 March 1994 at 00:56 in London, Ontario with Rodden Rating B, sourced from biography/autobiography.",
            "sources": [
                "https://www.astro.com/astro-databank/Bieber,_Justin",
            ],
        },
        "birth_metadata_b": {
            "datetime_iso": "1992-07-22T07:19:00-05:00",
            "location": "Grand Prairie, Texas",
            "timezone": "America/Chicago",
            "confidence": "C",
            "source_note": "Astro-Databank lists Selena Gomez as born on 22 July 1992 at 07:19 in Grand Prairie, Texas with Rodden Rating C and origin source not known.",
            "sources": [
                "https://www.astro.com/astro-databank/Gomez,_Selena",
            ],
        },
        "source_references": [
            "https://www.astro.com/astro-databank/Bieber,_Justin",
            "https://www.astro.com/astro-databank/Gomez,_Selena",
        ],
        "what_to_trust": [
            "Broad planet-to-planet themes",
            "Sign-level chemistry and tension",
            "High-level attraction, friction, and attachment discussion",
        ],
        "what_not_to_trust": [
            "House-overlay-heavy claims without explicit chart capture review",
            "Angle-sensitive interpretation as hard evidence",
            "Any use of this pair for tuning or validating the synastry engine",
        ],
        "capture_requirements": [
            "Freeze chart_data_a from the local backend using the chosen public timed source",
            "Freeze chart_data_b from the local backend using the chosen public timed source",
            "Record the exact source note used for each birth time before publishing any engine output",
        ],
        "chart_capture_note": "Frozen from the local AstroClock backend for content use; this pair remains outside the calibration and historical-validation lanes.",
        "options": {
            "include_modern": True,
            "include_nodes": True,
            "include_chiron": False,
            "orb_profile": "balanced",
        },
    },
    {
        "id": "justin_bieber_hailey_bieber",
        "title": "Justin Bieber and Hailey Bieber",
        "partner_a": "Justin Bieber",
        "partner_b": "Hailey Bieber",
        "relationship_type": "marriage",
        "usage_lane": "blog_content_only",
        "calibration_eligible": False,
        "content_eligible": True,
        "validation_recommendation": "blog_demo_only",
        "content_status": "captured_content_slice_1",
        "content_angle": "High-search-interest celebrity marriage useful for a softer 'what the engine says' blog comparison.",
        "target_queries": [
            "Justin Bieber Hailey Bieber astrology",
            "Justin Bieber Hailey Bieber synastry",
            "Justin Bieber Hailey Bieber compatibility",
        ],
        "birth_data_summary": {
            "timed_data_confidence": "C",
            "summary": "Public timed data is weak and should only support lightweight content demonstrations.",
        },
        "birth_metadata_a": {
            "datetime_iso": "1994-03-01T00:56:00-05:00",
            "location": "London, Ontario, Canada",
            "timezone": "America/Toronto",
            "confidence": "B",
            "source_note": "Astro-Databank lists Justin Bieber as born on 1 March 1994 at 00:56 in London, Ontario with Rodden Rating B, sourced from biography/autobiography.",
            "sources": [
                "https://www.astro.com/astro-databank/Bieber,_Justin",
            ],
        },
        "birth_metadata_b": {
            "datetime_iso": "1996-11-22T08:15:00-07:00",
            "location": "Tucson, Arizona",
            "timezone": "America/Phoenix",
            "confidence": "C",
            "source_note": "Astro-Databank lists Hailey Bieber as born on 22 November 1996 at 08:15 in Tucson, Arizona with Rodden Rating C from a rectified approximate time.",
            "sources": [
                "https://www.astro.com/astro-databank/Bieber,_Hailey",
            ],
        },
        "source_references": [
            "https://www.astro.com/astro-databank/Bieber,_Justin",
            "https://www.astro.com/astro-databank/Bieber,_Hailey",
        ],
        "what_to_trust": [
            "Broad sign and planetary themes for public-facing discussion",
            "Lightweight narrative comparisons of how synastry can frame a relationship",
        ],
        "what_not_to_trust": [
            "House overlays as strong evidence",
            "Angular activation as a stable basis for claims",
            "Any use of this pair for tuning or validating the synastry engine",
        ],
        "capture_requirements": [
            "Freeze chart_data_a from the local backend only if the chosen public timed source is documented in the content notes",
            "Freeze chart_data_b from the local backend only if the chosen public timed source is documented in the content notes",
            "Keep interpretation framed as illustrative rather than validation-grade",
        ],
        "chart_capture_note": "Frozen from the local AstroClock backend for content use; this pair remains outside the calibration and historical-validation lanes.",
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
        "generated_at": "2026-04-03T12:00:00+03:00",
        "purpose": "Content-only synastry slice for blog posts, demos, and public-interest comparison pieces. These cases are explicitly outside the calibration lane.",
        "lane": "blog_content_only",
        "content_guidance": {
            "allowed_uses": [
                "blog posts",
                "demo walkthroughs",
                "marketing examples",
                "public-interest synastry explainers",
            ],
            "disallowed_uses": [
                "algorithm calibration",
                "rule-weight tuning",
                "historical validation",
                "replay-corpus promotion without explicit review",
            ],
        },
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
