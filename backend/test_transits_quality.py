from __future__ import annotations

import copy
from pathlib import Path
import sys
from typing import Any, Dict, List

import pytest

repo_root = Path(__file__).resolve().parents[1]
sys.path.append(str(repo_root))
sys.path.append(str(repo_root / "backend"))

try:
    import backend.transits_morin as tm
except Exception:
    import transits_morin as tm

try:
    from backend.nlg_templates import render_prediction
except Exception:
    from nlg_templates import render_prediction

try:
    from backend.nlg_templates import _label_event
except Exception:
    from nlg_templates import _label_event

try:
    from backend.nlg_templates import _label_area
except Exception:
    from nlg_templates import _label_area


@pytest.fixture(autouse=True)
def _disable_ephemeris(monkeypatch):
    """Remove heavy external dependencies for deterministic unit tests."""
    monkeypatch.setattr(tm, "swe", None)
    monkeypatch.setattr(tm, "HoraryEngine", None)


def _run_enrich(monkeypatch, det_ctx: Dict[str, Any], hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    natal_chart = {"houses": [0.0] * 12}
    monkeypatch.setattr(tm, "compute_determinations", lambda *_: copy.deepcopy(det_ctx))
    return tm.enrich_hits_with_concordance(
        natal_chart,
        copy.deepcopy(hits),
        "2024-05-09T12:00:00+00:00",
        pd_windows=None,
    )


def test_morin_doctorate_example_strengthens_honors(monkeypatch):
    det_ctx = {
        "by_planet": {
            "Jupiter": {
                "determinationScores": {"by_area": {"honors": 0.9, "education": 0.8}},
                "nature": {"conditionScore": 0.2},
            },
            "MC": {"housePosition": {"house": 10}},
        }
    }
    hits = [
        {
            "transiting": "Jupiter",
            "target_label": "MC",
            "target_type": "cusp",
            "aspect": "Trine",
            "orb": 0.3,
            "max_orb": 4.0,
            "score": 7.5,
            "enriched_keywords": ["honors"],
        }
    ]
    enriched = _run_enrich(monkeypatch, det_ctx, hits)
    row = enriched[0]
    assert row["determination_strength"] > 0.6
    assert row["quality_score"] > 0
    assert row["quality_label"] in {"benefic", "very_benefic", "moderately_benefic"}


def test_morin_near_drowning_example_flags_malefic(monkeypatch):
    det_ctx = {
        "by_planet": {
            "Saturn": {
                "determinationScores": {"by_area": {"death": -0.8}},
                "nature": {"conditionScore": -0.3},
            },
            "Asc": {"housePosition": {"house": 1}},
        }
    }
    hits = [
        {
            "transiting": "Saturn",
            "target_label": "Asc",
            "target_type": "cusp",
            "aspect": "Conjunction",
            "orb": 0.1,
            "max_orb": 5.0,
            "score": 8.8,
            "enriched_keywords": [],
        }
    ]
    enriched = _run_enrich(monkeypatch, det_ctx, hits)
    row = enriched[0]
    assert row["determination_strength"] < -0.6
    assert row["quality_score"] < -5
    assert row["quality_label"] in {"malefic", "very_malefic"}


def test_unmatched_determination_does_not_carry_strength(monkeypatch):
    det_ctx = {
        "by_planet": {
            "Jupiter": {
                "determinationScores": {"by_area": {"honors": 0.9}},
                "nature": {"conditionScore": 0.0},
            },
            "C6": {"housePosition": {"house": 6}},
        }
    }
    hits = [
        {
            "transiting": "Jupiter",
            "target_label": "C6",
            "target_type": "cusp",
            "aspect": "Trine",
            "orb": 0.5,
            "max_orb": 5.0,
            "score": 6.0,
            "enriched_keywords": ["health"],
        }
    ]
    enriched = _run_enrich(monkeypatch, det_ctx, hits)
    row = enriched[0]
    assert pytest.approx(row["determination_strength"], abs=1e-6) == 0.0
    assert row["quality_score"] <= 0.0
    law1 = next(item for item in row["laws_applied"] if item["lawNumber"] == 1)
    assert law1["applies"] is False


def test_prediction_object_persists_and_uses_event_tokens(monkeypatch):
    det_ctx = {
        "by_planet": {
            "Mars": {
                "determinationScores": {"by_area": {"conflict": -0.8, "danger": -0.7}},
                "nature": {"conditionScore": -0.4},
            },
            "C7": {"housePosition": {"house": 7}},
        }
    }
    hits = [
        {
            "transiting": "Mars",
            "target_label": "C7",
            "target_type": "cusp",
            "aspect": "Square",
            "orb": 0.2,
            "max_orb": 5.0,
            "score": 8.2,
            "phase": "applying",
            "enriched_keywords": ["marriage", "attack_violence", "conflict"],
        }
    ]
    enriched = _run_enrich(monkeypatch, det_ctx, hits)
    row = enriched[0]
    assert row["prediction"]["eventType"] == "attack_violence"
    assert row["prediction"]["lifeArea"] == "conflict"
    assert row["event_domain"] == "conflict"
    assert row["target_primary_area"] == "conflict"
    assert row["prediction"]["label"] == "Mars Square C7"
    assert row["prediction"]["description"]
    assert "attack" in row["prediction"]["description"].lower() or "assault" in row["prediction"]["description"].lower()


def test_event_type_selection_prefers_candidate_matching_life_area(monkeypatch):
    det_ctx = {
        "by_planet": {
            "Jupiter": {
                "determinationScores": {"by_area": {"wealth": 0.9, "honors": 0.5}},
                "nature": {"conditionScore": 0.2},
            },
            "C2": {"housePosition": {"house": 2}},
        }
    }
    hits = [
        {
            "transiting": "Jupiter",
            "target_label": "C2",
            "target_type": "cusp",
            "aspect": "Trine",
            "orb": 0.2,
            "max_orb": 5.0,
            "score": 8.1,
            "phase": "applying",
            "enriched_keywords": ["promotion", "financial_gain", "wealth"],
        }
    ]
    enriched = _run_enrich(monkeypatch, det_ctx, hits)
    row = enriched[0]
    assert row["prediction"]["lifeArea"] == "wealth"
    assert row["prediction"]["eventType"] == "financial_gain"


def test_hidden_crisis_hit_does_not_default_to_arrest_without_legal_support(monkeypatch):
    det_ctx = {
        "by_planet": {
            "Mars": {
                "determinationScores": {"by_area": {"conflict": -0.8, "danger": -0.7}},
                "nature": {"conditionScore": -0.4},
            },
            "C12": {"housePosition": {"house": 12}},
        }
    }
    hits = [
        {
            "transiting": "Mars",
            "target_label": "C12",
            "target_type": "cusp",
            "aspect": "Quincunx",
            "orb": 0.4,
            "max_orb": 5.0,
            "score": 8.0,
            "phase": "applying",
            "keywords": ["Hidden", "Relationship", "C12"],
            "enriched_keywords": ["conflict", "secrets"],
        }
    ]
    enriched = _run_enrich(monkeypatch, det_ctx, hits)
    row = enriched[0]
    assert "arrest_imprisonment" not in (row.get("enriched_keywords") or [])
    assert row["prediction"]["eventType"] != "arrest_imprisonment"


def test_render_prediction_softens_when_concordance_is_weak():
    hit = {
        "transiting": "Mars",
        "aspect": "Quincunx",
        "target_label": "C12",
        "prediction": {
            "lifeArea": "secrets",
            "eventType": "attack_violence",
        },
        "determination_strength": 0.18,
        "concordance": {
            "direction_concordance": 0.0,
            "overall_concordance": 0.2,
            "solar_score": 0.0,
            "lunar_score": 0.0,
        },
    }
    description = render_prediction(hit)
    assert "can coincide with" in description.lower() or "can point to" in description.lower()
    assert "indicates" not in description.lower()


def test_render_prediction_uses_open_enemy_wording_for_seventh_house_war_rows():
    hit = {
        "transiting": "Mars",
        "aspect": "Square",
        "target_label": "C7",
        "prediction": {
            "lifeArea": "relationships",
            "eventType": "war_response_defensive",
        },
        "determination_strength": 0.72,
        "concordance": {
            "direction_concordance": 0.42,
            "overall_concordance": 0.67,
            "solar_score": 0.0,
            "lunar_score": 0.0,
        },
    }
    description = render_prediction(hit)
    assert "open enemies" in description.lower()
    assert "relationships and partnerships" not in description.lower()


def test_render_prediction_uses_imprisonment_or_exile_wording():
    hit = {
        "transiting": "Saturn",
        "aspect": "Conjunction",
        "target_label": "C12",
        "prediction": {
            "lifeArea": "secrets",
            "eventType": "arrest_imprisonment",
        },
        "determination_strength": 0.69,
        "concordance": {
            "direction_concordance": 0.35,
            "overall_concordance": 0.61,
            "solar_score": 0.0,
            "lunar_score": 0.0,
        },
    }
    description = render_prediction(hit)
    assert "imprisonment or exile" in description.lower()
    assert "arrest or imprisonment" not in description.lower()


def test_house_domain_defaults_follow_source_sensitive_morin_baseline():
    assert tm._DOMAIN_PRIMARY_HOUSE["contracts"] == 7
    assert tm._HOUSE_DEFAULT_DOMAIN[3] == "siblings"
    assert tm._HOUSE_DEFAULT_DOMAIN[6] == "service"
    assert tm._HOUSE_DEFAULT_DOMAIN[12] == "hidden_enemies"
    assert tm._HOUSE_CONTEXT_DOMAINS[3][0] == "siblings"
    assert tm._HOUSE_CONTEXT_DOMAINS[6][0] == "service"
    assert tm._HOUSE_CONTEXT_DOMAINS[12][0] == "hidden_enemies"


def test_house_domain_label_wording_stays_close_to_morin_baseline():
    assert _label_area("wealth") == "wealth and acquired goods"
    assert _label_area("children") == "children and bodily pleasures"
    assert _label_area("health") == "illness, service, and subordinates"
    assert _label_area("relationships") == "marriage, contracts, lawsuits, and open enemies"
    assert _label_area("death") == "death and mortality"
    assert _label_area("belief") == "religion and journeys"
    assert _label_area("honors") == "action, profession, dignity, and fame"
    assert _label_area("shared_resources") == "inheritance, debts, and shared burdens"


def test_generic_journey_synonyms_no_longer_collapse_to_third_house_only():
    assert tm._DOMAIN_SYNONYMS["journey"] == "long_travel"
    assert tm._DOMAIN_SYNONYMS["journeys"] == "long_travel"
    assert tm._EVENT_TAG_MAP["friends"] == "friends"


def test_event_label_wording_is_more_source_sensitive():
    assert _label_event("public_recognition") == "public fame or distinction"
    assert _label_event("recognition") == "fame, recognition, or public notice"
    assert _label_event("business_deal") == "a business or contract agreement"
    assert _label_event("contract_signing") == "a contract or agreement"
    assert _label_event("financial_gain") == "gain in wealth or income"
    assert _label_event("financial_loss") == "loss of wealth or expense"
    assert _label_event("recovery_health") == "recovery from illness"
    assert _label_event("romantic_connection") == "a courtship or affectionate attachment"
    assert _label_event("reconciliation") == "reconciliation or renewed accord"
    assert _label_event("engagement") == "an engagement or betrothal"
    assert _label_event("divorce") == "a divorce or dissolution of union"
    assert _label_event("separation") == "a separation or estrangement"
    assert _label_event("relationship_conflict") == "partnership conflict or open dispute"
    assert _label_event("betrayal") == "a breach of trust or faith"
    assert _label_event("speculation_gain") == "gain through speculation or hazard"
    assert _label_event("speculation_loss") == "loss through speculation or hazard"
    assert _label_event("inheritance_windfall") == "inheritance or succession gain"
    assert _label_event("shared_resource_loss") == "loss through debts or shared burdens"
    assert _label_event("degree_completion") == "completion of studies or degree"
    assert _label_event("exam_success") == "success in examination or trial"
    assert _label_event("exam_failure") == "failure or setback in examination"
    assert _label_event("enrollment_admission") == "admission or entrance into study"
    assert _label_event("spiritual_awakening") == "a religious or spiritual awakening"
    assert _label_event("religious_conversion") == "a change of religion or faith"
    assert _label_event("pilgrimage") == "a pilgrimage or religious journey"
    assert _label_event("mystical_experience") == "a visionary or mystical experience"
    assert _label_event("publication") == "a publication or issued work"
    assert _label_event("artistic_success") == "artistic distinction or success"
    assert _label_event("family_celebration") == "a family or domestic celebration"
    assert _label_event("family_conflict") == "family conflict or household strife"
    assert _label_event("moving_home") == "a change of home or residence"
    assert _label_event("purchase_property") == "purchase of land, home, or property"
    assert _label_event("short_journey") == "a short journey or local movement"
    assert _label_event("long_journey") == "a long journey or distant travel"
    assert _label_event("relocation_permanent") == "a permanent change of residence"


def test_shared_and_hidden_domains_do_not_default_to_death_without_death_testimony(monkeypatch):
    det_ctx = {
        "by_planet": {
            "Mercury": {
                "determinationScores": {"by_area": {"shared_resources": 0.7, "secrets": 0.6}},
                "nature": {"conditionScore": -0.1},
            },
            "C8": {"housePosition": {"house": 8}},
            "C12": {"housePosition": {"house": 12}},
        }
    }
    hits = [
        {
            "transiting": "Mercury",
            "target_label": "C8",
            "target_type": "cusp",
            "aspect": "Sextile",
            "orb": 0.3,
            "max_orb": 4.0,
            "score": 7.2,
            "phase": "applying",
            "keywords": ["Shared", "Hidden", "C8", "C12"],
            "enriched_keywords": ["shared_resources", "secrets"],
        }
    ]
    enriched = _run_enrich(monkeypatch, det_ctx, hits)
    row = enriched[0]
    assert row["event_domain"] == "shared_resources"
    assert row["prediction"]["lifeArea"] in {"shared_resources", "secrets"}
    assert row["prediction"]["eventType"] != "death_natural"
    assert row["prediction"]["eventType"] != "death_violent"
