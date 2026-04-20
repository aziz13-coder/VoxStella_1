import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = REPO_ROOT / "tests" / "fixtures" / "synastry_historical_validation_corpus.json"

DIMENSION_IDS = (
    "resonance",
    "communication",
    "attraction",
    "compatibility",
    "attachment",
    "growth",
    "friction",
    "burden",
)

STATUS_ORDER = (
    "aligned",
    "partially_aligned",
    "misaligned",
    "manual_review",
    "not_runnable_yet",
)


def load_synastry_historical_validation_corpus(path=CORPUS_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def score_to_band(score):
    try:
        value = float(score)
    except Exception:
        return 0
    if value < 20.0:
        return 0
    if value < 40.0:
        return 1
    if value < 55.0:
        return 2
    if value < 70.0:
        return 3
    if value < 85.0:
        return 4
    return 5


def _category_map(report):
    return {str(item.get("id")): item for item in report.get("categories") or []}


def compare_case_to_synastry_output(case, synastry_report):
    categories = _category_map(synastry_report)
    dimension_results = {}
    primary_misses = []
    secondary_misses = []
    matches = []

    for dimension, spec in (case.get("expected_dimensions") or {}).items():
        category = categories.get(dimension) or {}
        observed_score = float(category.get("score") or 0.0)
        observed_band = score_to_band(observed_score)
        min_band = int(spec.get("min_band", 0))
        max_band = int(spec.get("max_band", 5))
        priority = str(spec.get("priority") or "secondary")
        within_range = min_band <= observed_band <= max_band
        result = {
            "dimension": dimension,
            "priority": priority,
            "expected_band_range": [min_band, max_band],
            "observed_score": observed_score,
            "observed_band": observed_band,
            "within_range": within_range,
        }
        dimension_results[dimension] = result
        if within_range:
            matches.append(dimension)
        elif priority == "primary":
            primary_misses.append(dimension)
        else:
            secondary_misses.append(dimension)

    if primary_misses:
        status = "misaligned" if not matches else "partially_aligned"
    elif secondary_misses:
        status = "partially_aligned"
    else:
        status = "aligned"

    return {
        "status": status,
        "matched_dimensions": matches,
        "missed_primary_dimensions": primary_misses,
        "missed_secondary_dimensions": secondary_misses,
        "dimension_results": dimension_results,
    }


def runnable_cases(corpus):
    out = []
    for case in corpus.get("cases") or []:
        if case.get("chart_data_a") and case.get("chart_data_b"):
            out.append(case)
    return out
