from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"
OUTPUT_PATH = FIXTURES_DIR / "horary_external_source_pass_metadata_census.json"


def _tri(value: str) -> str:
    return value


def _classify_case(case: dict, fixture_name: str) -> dict:
    parsed = urlparse(case["source_url"])
    host = (parsed.netloc or "").lower()
    article_expected_verdict = case.get("article_expected_verdict")

    replay_track = "doctrine_only"
    publication_timestamp_available = _tri("unknown")
    chart_image_available = _tri("unknown")
    house_cusps_readable = _tri("unknown")
    planetary_positions_readable = _tri("unknown")
    future_track_if_chart_captured = None
    promotion_priority = "low"
    basis = ""

    if "cunning-man.co.uk" in host:
        replay_track = "image_reconstructable"
        publication_timestamp_available = _tri("yes")
        chart_image_available = _tri("yes")
        house_cusps_readable = _tri("unknown")
        planetary_positions_readable = _tri("unknown")
        promotion_priority = "high"
        basis = (
            "Cunning Man article pages are chart-centric and this source already has "
            "image-assisted replay precedent in the external corpus. Exact cast location "
            "still remains unverified, so these stay below direct replay."
        )
    elif "wordpress.com" in host:
        replay_track = "image_reconstructable"
        publication_timestamp_available = _tri("yes")
        chart_image_available = _tri("yes")
        house_cusps_readable = _tri("unknown")
        planetary_positions_readable = _tri("unknown")
        promotion_priority = "high"
        basis = (
            "Accessible WordPress article with published timestamp and embedded chart imagery; "
            "safe next step is image-assisted replay review rather than direct recast."
        )
    elif "reddit.com" in host:
        replay_track = "doctrine_only"
        publication_timestamp_available = _tri("unknown")
        chart_image_available = _tri("no")
        house_cusps_readable = _tri("no")
        planetary_positions_readable = _tri("no")
        promotion_priority = "low"
        basis = (
            "Reddit sources are blocked or removed in the current environment, so they remain "
            "routing-only doctrine audits unless a preserved chart payload is captured elsewhere."
        )
    elif any(
        domain in host
        for domain in (
            "astrologyweekly.com",
            "skyscript.co.uk",
        )
    ):
        replay_track = "doctrine_only"
        publication_timestamp_available = _tri("unknown")
        chart_image_available = _tri("unknown")
        house_cusps_readable = _tri("unknown")
        planetary_positions_readable = _tri("unknown")
        future_track_if_chart_captured = "image_reconstructable"
        promotion_priority = "medium"
        basis = (
            "Forum-thread source with doctrine value, but current non-interactive census cannot "
            "verify attached chart images or exact cast metadata safely. Keep as doctrine-only "
            "until manual or browser-assisted chart capture is done."
        )
    else:
        basis = "Unrecognized source host; keep as doctrine-only pending manual review."

    slice_token = fixture_name.replace(".json", "")
    slice_number = slice_token.split("slice")[-1]

    return {
        "id": case["id"],
        "slice_fixture": fixture_name,
        "slice_number": slice_number,
        "question": case["question"],
        "source_url": case["source_url"],
        "source_host": host,
        "audit_type_current": "source_pass_routing",
        "replay_track": replay_track,
        "future_track_if_chart_captured": future_track_if_chart_captured,
        "promotion_priority": promotion_priority,
        "cast_date_explicit": _tri("no"),
        "cast_time_explicit": _tri("no"),
        "cast_location_explicit": _tri("no"),
        "publication_timestamp_available": publication_timestamp_available,
        "chart_image_available": chart_image_available,
        "house_cusps_readable": house_cusps_readable,
        "planetary_positions_readable": planetary_positions_readable,
        "source_verdict_explicit": _tri("yes" if article_expected_verdict else "unknown"),
        "source_outcome_explicit": _tri("unknown"),
        "census_basis": basis,
    }


def build_census() -> list[dict]:
    entries: list[dict] = []
    for path in sorted(FIXTURES_DIR.glob("horary_*source_pass_slice*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for case in data:
            entries.append(_classify_case(case, path.name))
    return entries


def main() -> None:
    entries = build_census()
    OUTPUT_PATH.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(entries)} source-pass census entries to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
