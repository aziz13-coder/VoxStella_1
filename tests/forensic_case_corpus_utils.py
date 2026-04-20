import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = REPO_ROOT / "tests" / "fixtures" / "forensic_case_corpus.json"


AXIS_KEYWORDS = {
    "violence_homicide": [
        "murder",
        "homicide",
        "violent",
        "violence",
        "death",
        "killing",
        "blunt force",
        "strangulation",
        "gunshot",
        "stab",
    ],
    "abduction_missing_person": [
        "abduction",
        "kidnapping",
        "missing",
        "disappearance",
        "taken",
    ],
    "deception_coverup": [
        "deception",
        "cover-up",
        "coverup",
        "lie",
        "lies",
        "staged",
        "conceal",
        "concealment",
        "hidden",
    ],
    "domestic_partner_involvement": [
        "spouse",
        "wife",
        "husband",
        "partner",
        "relationship",
        "domestic",
        "7th house",
    ],
    "family_involvement": [
        "family",
        "mother",
        "father",
        "parent",
        "parents",
        "home",
        "domestic",
    ],
    "child_victim": [
        "child",
        "children",
        "baby",
        "infant",
        "daughter",
        "son",
        "5th house",
    ],
    "water_disappearance_or_drowning": [
        "water",
        "drowning",
        "marina",
        "sea",
        "boat",
        "harbor",
        "fluids",
    ],
    "accident_or_disaster": [
        "accident",
        "disaster",
        "mechanical",
        "unintentional",
        "natural",
        "catastrophic accident",
    ],
    "friend_or_close_associate": [
        "friend",
        "close associate",
        "acquaintance",
        "known to",
    ],
    "authority_or_public_case": [
        "public",
        "authority",
        "institution",
        "celebrity",
        "leader",
        "law",
        "police",
    ],
    "accomplice_or_witness": [
        "accomplice",
        "witness",
        "helper",
        "two perpetrators",
        "more than one",
    ],
}


def load_forensic_case_corpus(path=CORPUS_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _result_text_blob(forensic_result, include_rationales=True):
    findings = forensic_result.get("findings") or []
    categories = forensic_result.get("categories") or {}
    dominance = forensic_result.get("dominance") or {}
    text_parts = []
    for finding in findings:
        keys = ("title", "category", "rationale") if include_rationales else ("title", "category")
        for key in keys:
            value = finding.get(key)
            if value:
                text_parts.append(str(value))
    text_parts.extend(str(k) for k in categories.keys())
    if isinstance(dominance, dict):
        text_parts.extend(str(k) for k in dominance.keys())
        for value in dominance.values():
            if isinstance(value, dict):
                for sub in value.values():
                    if sub:
                        text_parts.append(str(sub))
    return " ".join(text_parts).lower()


def compare_case_to_forensic_output(case, forensic_result):
    blob = _result_text_blob(forensic_result, include_rationales=True)
    contradiction_blob = _result_text_blob(forensic_result, include_rationales=False)
    matched = []
    missed = []
    contradicted = []

    for axis in case.get("expected_primary_axes") or []:
        keywords = AXIS_KEYWORDS.get(axis, [])
        if any(keyword.lower() in blob for keyword in keywords):
            matched.append(axis)
        else:
            missed.append(axis)

    for axis in case.get("contradictory_axes") or []:
        keywords = AXIS_KEYWORDS.get(axis, [])
        if any(keyword.lower() in contradiction_blob for keyword in keywords):
            contradicted.append(axis)

    if contradicted:
        status = "misaligned"
    elif not missed:
        status = "aligned"
    elif matched:
        status = "partially_aligned"
    else:
        status = "misaligned"

    return {
        "status": status,
        "matched_axes": matched,
        "missed_axes": missed,
        "contradicted_axes": contradicted,
    }
