import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = REPO_ROOT / "tests" / "fixtures" / "forensic_case_corpus.json"


AXIS_KEYWORDS = {
    "violence_homicide": [
        "assault",
        "beaten",
        "bodily injury",
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
        "captivity",
        "confine",
        "confinement",
        "kidnapping",
        "missing",
        "disappearance",
        "detention",
        "seizure",
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
    "immediate_scene_or_vicinity_context": [
        "front of the victim",
        "immediate scene",
        "in the vicinity",
        "near the victim",
        "not been taken",
        "residence",
        "voluntarily left",
    ],
    "trafficking_or_possession_context": [
        "exploitation",
        "human trafficking",
        "made a possession",
        "person a possession",
        "possession",
        "possession or value motive",
        "sex trafficking",
        "sex trade",
        "sold",
        "taken for trafficking",
        "trafficking",
        "treated as a possession",
        "value motive",
    ],
    "communication_vehicle_short_distance_context": [
        "communication issue",
        "cousins",
        "local movement",
        "short distance",
        "sibling",
        "verbal argument",
        "vehicle",
        "vehicles involved",
    ],
    "family_home_end_matter_context": [
        "end of the matter",
        "family",
        "home",
        "house of the end",
        "tomb",
        "womb",
    ],
    "party_entertainment_context": [
        "dancing",
        "drinking",
        "entertainment",
        "fun",
        "party",
        "partying",
    ],
    "routine_disruption_stalker_context": [
        "disrupted",
        "normal thing",
        "routine",
        "stalker",
        "watching the victim",
    ],
    "suspect_territory_context": [
        "open enemy",
        "right in front of the suspect",
        "suspect territory",
        "suspects nose",
        "where the suspect feels comfortable",
    ],
    "death_financial_entanglement_context": [
        "debts",
        "deceased person",
        "financial disagreement",
        "house of death",
        "inheritance",
    ],
    "far_distance_departure_context": [
        "far away",
        "farther away",
        "further away",
        "going further away",
    ],
    "public_authority_witness_context": [
        "authorities",
        "boss",
        "government",
        "out in the open",
        "police",
        "public",
        "seen by a witness",
        "witness",
    ],
    "friends_social_circle_context": [
        "friends",
        "friends may know",
        "hopes and dreams",
        "social circle",
        "surrounded by friends",
    ],
    "hidden_captive_kidnapped_context": [
        "enclosed area",
        "hidden",
        "kept hidden",
        "kidnapped",
        "may not be found",
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
        "custody",
        "family",
        "mother",
        "father",
        "parent",
        "parents",
        "household",
    ],
    "child_victim": [
        "child",
        "children",
        "custody",
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
    "route_vehicle_transport": [
        "car",
        "highway",
        "jeep",
        "license plate",
        "movement",
        "road",
        "roads",
        "route",
        "transport",
        "travel",
        "trunk",
        "vehicle",
        "vehicles",
    ],
}


def _keyword_matches(blob: str, keyword: str) -> bool:
    if not blob or not keyword:
        return False
    escaped = re.escape(keyword.lower())
    return re.search(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", blob) is not None


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
        if any(_keyword_matches(blob, keyword) for keyword in keywords):
            matched.append(axis)
        else:
            missed.append(axis)

    for axis in case.get("contradictory_axes") or []:
        keywords = AXIS_KEYWORDS.get(axis, [])
        if any(_keyword_matches(contradiction_blob, keyword) for keyword in keywords):
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
