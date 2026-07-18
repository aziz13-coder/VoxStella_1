from __future__ import annotations

from math import sqrt
from typing import Any, Dict, List, Sequence, Tuple

from astrocartography_goal_engine import evaluate_goal_model, extract_relocation_features
from astrocartography_goal_models import list_goal_models


DEFAULT_PEER_OVERLAP_THRESHOLD = 0.92
RESIDUAL_DISTINCTNESS_TOLERANCE = 1e-6
PUBLIC_MODEL_STATUS = "active"
STANDALONE_COMPOSITION_MODE = "standalone"
SPECIALIST_COMPOSITION_MODE = "specialist_residual"
RESEARCH_MODEL_STATUSES = {"experimental"}


def _line(body: str, angle: str, distance_km: float) -> Dict[str, Any]:
    return {
        "id": f"{body}:{angle}:{distance_km}",
        "body": body,
        "angle": angle,
        "label": f"{body} {angle}",
        "distance_km": float(distance_km),
        "zone": "primary" if distance_km <= 300 else "extended",
    }


def _crossing(pair: Sequence[str], distance_km: float) -> Dict[str, Any]:
    planets = [str(item) for item in pair]
    return {
        "id": f"{'|'.join(sorted(planets))}:{distance_km}",
        "planets": planets,
        "label": " x ".join(planets),
        "distance_km": float(distance_km),
        "zone": "primary" if distance_km <= 300 else "extended",
    }


def _relocation(planets: Dict[str, int]) -> Dict[str, Any]:
    return extract_relocation_features({"planets": {name: {"house": house} for name, house in planets.items()}})


SCENARIOS: List[Dict[str, Any]] = [
    {
        "id": "study_expansion",
        "label": "Study Expansion",
        "expected_lead": "education",
        "expected": ["education", "communication"],
        "natal_rows": [
            _line("Mercury", "MC", 25),
            _line("Jupiter", "ASC", 40),
            _line("Saturn", "MC", 120),
            _line("Moon", "IC", 110),
        ],
        "natal_crossings": [
            _crossing(["Mercury", "Jupiter"], 60),
            _crossing(["Mercury", "Uranus"], 150),
        ],
        "relocation": _relocation({"Mercury": 3, "Jupiter": 9, "Saturn": 10, "Moon": 4}),
    },
    {
        "id": "warm_partnership",
        "label": "Warm Partnership",
        "expected_lead": "love",
        "expected": ["love", "love_commitment", "partners"],
        "natal_rows": [
            _line("Venus", "DSC", 35),
            _line("Moon", "IC", 55),
            _line("Jupiter", "DSC", 95),
            _line("Saturn", "DSC", 220),
        ],
        "natal_crossings": [
            _crossing(["Venus", "Moon"], 45),
            _crossing(["Venus", "Jupiter"], 90),
        ],
        "relocation": _relocation({"Venus": 7, "Moon": 4, "Jupiter": 5, "Saturn": 7}),
    },
    {
        "id": "public_career",
        "label": "Public Career",
        "expected_lead": "career_public_profile",
        "expected": ["career_public_profile", "career", "work"],
        "natal_rows": [
            _line("Sun", "MC", 20),
            _line("Jupiter", "MC", 35),
            _line("Mercury", "ASC", 70),
            _line("Saturn", "MC", 85),
            _line("North Node", "MC", 100),
        ],
        "natal_crossings": [
            _crossing(["Sun", "Jupiter"], 55),
            _crossing(["Mercury", "Jupiter"], 120),
        ],
        "relocation": _relocation({"Sun": 10, "Jupiter": 11, "Saturn": 10, "Mercury": 1, "North Node": 10}),
    },
    {
        "id": "stable_income",
        "label": "Stable Income",
        "expected_lead": "money",
        "expected": ["money_stable_income", "money", "work"],
        "natal_rows": [
            _line("Jupiter", "MC", 30),
            _line("Venus", "MC", 55),
            _line("Sun", "MC", 80),
            _line("Saturn", "IC", 95),
            _line("Mercury", "MC", 110),
        ],
        "natal_crossings": [
            _crossing(["Jupiter", "Venus"], 50),
            _crossing(["Mercury", "Jupiter"], 130),
        ],
        "relocation": _relocation({"Jupiter": 2, "Venus": 10, "Saturn": 6, "Mercury": 11, "Sun": 10}),
    },
    {
        "id": "speculative_lucky_run",
        "label": "Speculative Lucky Run",
        "expected_lead": "gambling_luck",
        "expected": ["gambling_luck", "money"],
        "natal_rows": [
            _line("Jupiter", "ASC", 20),
            _line("Venus", "DSC", 35),
            _line("Sun", "MC", 70),
            _line("Mercury", "ASC", 80),
            _line("Saturn", "MC", 220),
        ],
        "natal_crossings": [
            _crossing(["Jupiter", "Venus"], 40),
            _crossing(["Mercury", "Jupiter"], 75),
            _crossing(["Sun", "Jupiter"], 115),
        ],
        "relocation": _relocation({"Jupiter": 5, "Venus": 2, "Mercury": 11, "Sun": 8, "Moon": 5}),
    },
    {
        "id": "home_sanctuary",
        "label": "Home Sanctuary",
        "expected_lead": "home",
        "expected": ["home_retreat", "home"],
        "natal_rows": [
            _line("Moon", "IC", 20),
            _line("Venus", "IC", 60),
            _line("Jupiter", "IC", 120),
            _line("Neptune", "IC", 100),
        ],
        "natal_crossings": [
            _crossing(["Moon", "Venus"], 55),
            _crossing(["Moon", "Jupiter"], 110),
        ],
        "relocation": _relocation({"Moon": 4, "Venus": 4, "Jupiter": 2, "Neptune": 12}),
    },
    {
        "id": "transformative_growth",
        "label": "Transformative Growth",
        "expected_lead": "personal_growth",
        "expected": ["personal_growth"],
        "natal_rows": [
            _line("Sun", "ASC", 30),
            _line("Jupiter", "MC", 55),
            _line("Uranus", "ASC", 45),
            _line("Pluto", "MC", 90),
            _line("North Node", "ASC", 105),
        ],
        "natal_crossings": [
            _crossing(["Sun", "Uranus"], 65),
            _crossing(["Jupiter", "Pluto"], 125),
        ],
        "relocation": _relocation({"Sun": 1, "Jupiter": 9, "Uranus": 11, "Pluto": 8, "North Node": 10}),
    },
    {
        "id": "communications_network",
        "label": "Communications Network",
        "expected_lead": "communication",
        "expected": ["communication", "education"],
        "natal_rows": [
            _line("Mercury", "ASC", 25),
            _line("Mercury", "MC", 40),
            _line("Jupiter", "MC", 70),
            _line("Venus", "DSC", 90),
            _line("Uranus", "MC", 110),
        ],
        "natal_crossings": [
            _crossing(["Mercury", "Jupiter"], 55),
            _crossing(["Mercury", "Venus"], 85),
            _crossing(["Mercury", "Uranus"], 120),
        ],
        "relocation": _relocation({"Mercury": 3, "Venus": 11, "Jupiter": 9, "Moon": 7}),
    },
    {
        "id": "chemistry_heat",
        "label": "Chemistry Heat",
        "expected_lead": "sex",
        "expected": ["sex", "love"],
        "natal_rows": [
            _line("Venus", "DSC", 20),
            _line("Mars", "ASC", 25),
            _line("Pluto", "DSC", 70),
            _line("Moon", "DSC", 95),
        ],
        "natal_crossings": [
            _crossing(["Venus", "Mars"], 40),
            _crossing(["Venus", "Pluto"], 70),
        ],
        "relocation": _relocation({"Venus": 7, "Mars": 5, "Pluto": 8, "Moon": 5}),
    },
    {
        "id": "conflict_hot",
        "label": "Conflict Hot",
        "expected_lead": "conflict",
        "expected": ["conflict"],
        "natal_rows": [
            _line("Mars", "DSC", 20),
            _line("Saturn", "DSC", 35),
            _line("Pluto", "MC", 60),
            _line("Uranus", "DSC", 80),
        ],
        "natal_crossings": [
            _crossing(["Mars", "Saturn"], 45),
            _crossing(["Mars", "Pluto"], 60),
            _crossing(["Mars", "Uranus"], 90),
        ],
        "relocation": _relocation({"Mars": 7, "Saturn": 7, "Pluto": 8, "Uranus": 12}),
    },
    {
        "id": "injury_illness_hotspot",
        "label": "Injury Illness Hotspot",
        "expected_lead": "health_risk",
        "expected": ["health_risk", "conflict"],
        "natal_rows": [
            _line("Mars", "ASC", 20),
            _line("Saturn", "ASC", 30),
            _line("Uranus", "ASC", 55),
            _line("Neptune", "ASC", 85),
            _line("Jupiter", "IC", 260),
        ],
        "natal_crossings": [
            _crossing(["Mars", "Saturn"], 45),
            _crossing(["Mars", "Uranus"], 70),
            _crossing(["Saturn", "Neptune"], 115),
        ],
        "relocation": _relocation({"Mars": 1, "Saturn": 6, "Uranus": 8, "Neptune": 12, "Pluto": 6}),
    },
    {
        "id": "contemplative_beliefs",
        "label": "Contemplative Beliefs",
        "expected_lead": "beliefs",
        "expected": ["beliefs"],
        "natal_rows": [
            _line("Jupiter", "ASC", 25),
            _line("Mercury", "MC", 60),
            _line("Sun", "ASC", 80),
            _line("Neptune", "IC", 70),
            _line("Moon", "IC", 90),
        ],
        "natal_crossings": [
            _crossing(["Jupiter", "Mercury"], 70),
            _crossing(["Jupiter", "Neptune"], 115),
        ],
        "relocation": _relocation({"Jupiter": 9, "Mercury": 9, "Sun": 12, "Neptune": 12, "Moon": 12}),
    },
    {
        "id": "noisy_drift",
        "label": "Noisy Drift",
        "expected_lead": "conflict",
        "expected": [],
        "natal_rows": [
            _line("Neptune", "MC", 35),
            _line("Uranus", "DSC", 50),
            _line("Saturn", "DSC", 100),
            _line("Mars", "MC", 140),
        ],
        "natal_crossings": [
            _crossing(["Mercury", "Neptune"], 100),
            _crossing(["Mars", "Saturn"], 140),
        ],
        "relocation": _relocation({"Neptune": 12, "Uranus": 7, "Saturn": 10, "Mars": 6}),
    },
    {
        "id": "formal_alliance",
        "label": "Formal Alliance",
        "expected_lead": "partners",
        "expected": ["partners", "love_commitment"],
        "natal_rows": [
            _line("Venus", "DSC", 30),
            _line("Jupiter", "DSC", 55),
            _line("Sun", "DSC", 95),
            _line("Saturn", "DSC", 70),
            _line("Mars", "DSC", 220),
        ],
        "natal_crossings": [
            _crossing(["Venus", "Jupiter"], 65),
            _crossing(["Venus", "Saturn"], 110),
        ],
        "relocation": _relocation({"Venus": 7, "Jupiter": 7, "Sun": 7, "Saturn": 7, "Moon": 11}),
    },
    {
        "id": "social_circle",
        "label": "Social Circle",
        "expected_lead": "friends",
        "expected": ["friends", "communication"],
        "natal_rows": [
            _line("Venus", "ASC", 25),
            _line("Jupiter", "DSC", 40),
            _line("Mercury", "ASC", 60),
            _line("Moon", "ASC", 90),
        ],
        "natal_crossings": [
            _crossing(["Venus", "Jupiter"], 55),
            _crossing(["Mercury", "Venus"], 85),
        ],
        "relocation": _relocation({"Venus": 11, "Jupiter": 11, "Mercury": 3, "Moon": 11}),
    },
    {
        "id": "secure_salary",
        "label": "Secure Salary",
        "expected_lead": "money_stable_income",
        "expected": ["money_stable_income", "money", "work"],
        "natal_rows": [
            _line("Saturn", "MC", 30),
            _line("Jupiter", "ASC", 55),
            _line("Mercury", "MC", 80),
            _line("Venus", "ASC", 110),
        ],
        "natal_crossings": [
            _crossing(["Mercury", "Jupiter"], 70),
            _crossing(["Jupiter", "Venus"], 115),
        ],
        "relocation": _relocation({"Saturn": 6, "Jupiter": 2, "Mercury": 6, "Venus": 2}),
    },
    {
        "id": "craft_execution",
        "label": "Craft Execution",
        "expected_lead": "work",
        "expected": ["work", "career"],
        "natal_rows": [
            _line("Mercury", "ASC", 20),
            _line("Saturn", "MC", 35),
            _line("Mars", "MC", 65),
            _line("Mercury", "MC", 95),
        ],
        "natal_crossings": [
            _crossing(["Mercury", "Saturn"], 55),
            _crossing(["Mercury", "Mars"], 95),
        ],
        "relocation": _relocation({"Mercury": 6, "Saturn": 6, "Mars": 6, "Sun": 6}),
    },
    {
        "id": "retreat_contemplation",
        "label": "Retreat Contemplation",
        "expected_lead": "home_retreat",
        "expected": ["home_retreat", "beliefs", "home"],
        "natal_rows": [
            _line("Moon", "IC", 25),
            _line("Neptune", "IC", 40),
            _line("Jupiter", "IC", 75),
            _line("Venus", "IC", 120),
        ],
        "natal_crossings": [
            _crossing(["Moon", "Neptune"], 45),
            _crossing(["Moon", "Jupiter"], 95),
        ],
        "relocation": _relocation({"Moon": 4, "Neptune": 12, "Jupiter": 12, "Venus": 4}),
    },
    {
        "id": "authority_ladder",
        "label": "Authority Ladder",
        "expected_lead": "career",
        "expected": ["career", "career_public_profile", "work"],
        "natal_rows": [
            _line("Saturn", "MC", 20),
            _line("Jupiter", "MC", 40),
            _line("Sun", "MC", 65),
            _line("Pluto", "MC", 85),
            _line("Mercury", "MC", 120),
        ],
        "natal_crossings": [
            _crossing(["Jupiter", "Saturn"], 60),
            _crossing(["Sun", "Saturn"], 90),
        ],
        "relocation": _relocation({"Saturn": 10, "Jupiter": 10, "Sun": 11, "Pluto": 10}),
    },
    {
        "id": "public_teaching",
        "label": "Public Teaching",
        "expected_lead": "education",
        "expected": ["education", "communication", "beliefs"],
        "natal_rows": [
            _line("Jupiter", "MC", 25),
            _line("Mercury", "MC", 35),
            _line("Sun", "ASC", 85),
            _line("Saturn", "MC", 115),
        ],
        "natal_crossings": [
            _crossing(["Mercury", "Jupiter"], 45),
            _crossing(["Jupiter", "Sun"], 100),
        ],
        "relocation": _relocation({"Jupiter": 9, "Mercury": 3, "Sun": 10, "Saturn": 9}),
    },
    {
        "id": "rooted_commitment",
        "label": "Rooted Commitment",
        "expected_lead": "love_commitment",
        "expected": ["love_commitment", "partners", "home"],
        "natal_rows": [
            _line("Venus", "IC", 20),
            _line("Moon", "DSC", 40),
            _line("Saturn", "DSC", 80),
            _line("Jupiter", "IC", 105),
        ],
        "natal_crossings": [
            _crossing(["Venus", "Moon"], 55),
            _crossing(["Venus", "Saturn"], 95),
        ],
        "relocation": _relocation({"Venus": 7, "Moon": 4, "Saturn": 7, "Jupiter": 4}),
    },
    {
        "id": "volatile_reinvention",
        "label": "Volatile Reinvention",
        "expected_lead": "personal_growth",
        "expected": ["personal_growth", "conflict"],
        "natal_rows": [
            _line("Uranus", "ASC", 20),
            _line("Sun", "ASC", 45),
            _line("Jupiter", "MC", 70),
            _line("Pluto", "ASC", 95),
            _line("Mars", "DSC", 180),
        ],
        "natal_crossings": [
            _crossing(["Sun", "Uranus"], 55),
            _crossing(["Jupiter", "Pluto"], 100),
        ],
        "relocation": _relocation({"Uranus": 1, "Sun": 1, "Jupiter": 9, "Pluto": 8}),
    },
]


def _model_inventory_entry(model: Dict[str, Any]) -> Dict[str, Any]:
    goal_id = str(model.get("id") or "").strip().lower()
    status = str(model.get("status") or "").strip().lower()
    composition = model.get("composition") or {}
    composition_mode = str(composition.get("mode") or "").strip().lower()
    parent_id = str(composition.get("parent_id") or "").strip().lower()

    if status == PUBLIC_MODEL_STATUS and composition_mode == STANDALONE_COMPOSITION_MODE:
        gate_bucket = "public_peer"
        reason = (
            "Included: status is active and composition is standalone, so this "
            "model participates in the default public semantic and peer-overlap gate."
        )
    elif status == PUBLIC_MODEL_STATUS and composition_mode == SPECIALIST_COMPOSITION_MODE:
        gate_bucket = "active_specialist_residual"
        reason = (
            "Excluded from the default standalone semantic/peer gate and from "
            "full-model peer cosine: this active specialist intentionally inherits "
            "its parent and is assessed with residual distinctness and lift."
        )
    elif status in RESEARCH_MODEL_STATUSES:
        gate_bucket = "non_public_research"
        reason = (
            f"Excluded from the default public gate because model status is {status}; "
            "reported separately as non-public research."
        )
    elif status == "deprecated":
        gate_bucket = "excluded"
        reason = "Excluded because the model is deprecated."
    else:
        gate_bucket = "excluded"
        reason = f"Excluded because model status {status or '<missing>'} is not active."

    return {
        "goal_id": goal_id,
        "label": str(model.get("label") or goal_id),
        "status": status,
        "source_status": str(model.get("source_status") or "").strip().lower(),
        "composition_mode": composition_mode,
        "parent_id": parent_id or None,
        "parent_weight": composition.get("parent_weight"),
        "max_abs_residual": composition.get("max_abs_residual"),
        "body_scope": str(model.get("body_scope") or "").strip().lower(),
        "gate_bucket": gate_bucket,
        "gate_reason": reason,
    }


def evaluate_scenario(
    scenario: Dict[str, Any],
    *,
    model_ids: Sequence[str] | None = None,
) -> Dict[str, Any]:
    if model_ids is None:
        model_ids = [str(model.get("id") or "") for model in list_goal_models()]
    ranking = []
    for goal_id in model_ids:
        evaluation = evaluate_goal_model(
            goal_id,
            natal_rows=scenario.get("natal_rows") or [],
            natal_crossings=scenario.get("natal_crossings") or [],
            relocation=scenario.get("relocation") or extract_relocation_features({}),
        )
        ranking.append(
            {
                "goal_id": goal_id,
                "label": evaluation.get("goal", {}).get("label"),
                "score": evaluation.get("score"),
                "raw_score": evaluation.get("raw_score"),
                "ranking_eligible": bool(evaluation.get("ranking_eligible")),
                "specialist_residual": float(
                    ((evaluation.get("breakdown") or {}).get("specialist_residual"))
                    or 0.0
                ),
                "top_support": (evaluation.get("top_supports") or [{}])[0].get("label"),
            }
        )
    ranking.sort(key=lambda item: (-float(item.get("score") or 0.0), -float(item.get("raw_score") or 0.0), str(item.get("goal_id") or "")))
    return {
        "id": scenario.get("id"),
        "label": scenario.get("label"),
        "expected_lead": scenario.get("expected_lead"),
        "expected": list(scenario.get("expected") or []),
        "ranking": ranking,
    }


def _filter_scenario_results(
    scenario_results: Sequence[Dict[str, Any]],
    model_ids: Sequence[str],
) -> List[Dict[str, Any]]:
    included = {str(goal_id) for goal_id in model_ids}
    filtered: List[Dict[str, Any]] = []
    for result in scenario_results:
        referenced_goals = {
            str(result.get("expected_lead") or "").strip().lower(),
            *(
                str(item).strip().lower()
                for item in (result.get("expected") or [])
            ),
        }
        referenced_goals.discard("")
        filtered.append(
            {
                "id": result.get("id"),
                "label": result.get("label"),
                "ranking": [
                dict(item)
                for item in (result.get("ranking") or [])
                if str(item.get("goal_id") or "") in included
                ],
                "historical_probe_references": sorted(
                    referenced_goals & included
                ),
                "semantic_assertions_applied": False,
            }
        )
    return filtered


def _expectation_exclusion(
    *,
    scenario_id: str,
    expectation: str,
    goal_id: str,
    inventory_by_id: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    inventory = inventory_by_id.get(goal_id) or {}
    return {
        "scenario": scenario_id,
        "expectation": expectation,
        "goal_id": goal_id,
        "status": inventory.get("status") or "unknown",
        "composition_mode": inventory.get("composition_mode") or "unknown",
        "gate_bucket": inventory.get("gate_bucket") or "unknown",
        "reason": inventory.get("gate_reason") or "Goal is not in the public peer inventory.",
    }


def evaluate_public_semantic_expectations(
    scenario_results: Sequence[Dict[str, Any]],
    *,
    public_peer_model_ids: Sequence[str],
    inventory_by_id: Dict[str, Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    eligible = {str(goal_id) for goal_id in public_peer_model_ids}
    failures: List[Dict[str, Any]] = []
    exclusions: List[Dict[str, Any]] = []
    annotated_results: List[Dict[str, Any]] = []

    for result in scenario_results:
        scenario_id = str(result.get("id") or "")
        ranking = [
            dict(item)
            for item in (result.get("ranking") or [])
            if str(item.get("goal_id") or "") in eligible
        ]
        top_ids = [str(item.get("goal_id") or "") for item in ranking[:3]]
        raw_expected_lead = str(result.get("expected_lead") or "").strip().lower()
        expected_lead = raw_expected_lead if raw_expected_lead in eligible else ""
        if raw_expected_lead and not expected_lead:
            exclusions.append(
                _expectation_exclusion(
                    scenario_id=scenario_id,
                    expectation="expected_lead",
                    goal_id=raw_expected_lead,
                    inventory_by_id=inventory_by_id,
                )
            )

        raw_expected = [
            str(item).strip().lower()
            for item in (result.get("expected") or [])
            if str(item).strip()
        ]
        expected = [goal_id for goal_id in raw_expected if goal_id in eligible]
        for excluded_goal in raw_expected:
            if excluded_goal not in eligible:
                exclusions.append(
                    _expectation_exclusion(
                        scenario_id=scenario_id,
                        expectation="expected_in_top_3",
                        goal_id=excluded_goal,
                        inventory_by_id=inventory_by_id,
                    )
                )

        if expected_lead:
            top_id = top_ids[0] if top_ids else ""
            if top_id != expected_lead:
                failures.append(
                    {
                        "scenario": scenario_id,
                        "expectation": "expected_lead",
                        "expected_lead": expected_lead,
                        "top_id": top_id,
                        "top_ids": top_ids,
                    }
                )
        if expected and not any(goal_id in top_ids for goal_id in expected):
            failures.append(
                {
                    "scenario": scenario_id,
                    "expectation": "expected_in_top_3",
                    "expected": expected,
                    "top_ids": top_ids,
                }
            )

        annotated_results.append(
            {
                "id": result.get("id"),
                "label": result.get("label"),
                "ranking": ranking,
                "public_expectations": {
                    "expected_lead": expected_lead or None,
                    "expected_in_top_3": expected,
                    "assertion_count": int(bool(expected_lead)) + int(bool(expected)),
                },
                "excluded_expectation_count": sum(
                    1
                    for item in exclusions
                    if str(item.get("scenario") or "") == scenario_id
                ),
            }
        )

    return annotated_results, failures, exclusions


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    dot = sum(float(a) * float(b) for a, b in zip(left, right))
    left_norm = sqrt(sum(float(a) * float(a) for a in left))
    right_norm = sqrt(sum(float(b) * float(b) for b in right))
    if left_norm <= 0.0 or right_norm <= 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def _find_high_overlap_pairs(
    scenario_results: Sequence[Dict[str, Any]],
    *,
    model_ids: Sequence[str],
    threshold: float,
) -> List[Dict[str, Any]]:
    score_matrix: Dict[str, List[float]] = {
        str(goal_id): [] for goal_id in model_ids
    }
    for result in scenario_results:
        scores_by_goal = {
            str(item.get("goal_id") or ""): float(item.get("raw_score") or 0.0)
            for item in (result.get("ranking") or [])
        }
        for goal_id in score_matrix:
            score_matrix[goal_id].append(scores_by_goal.get(goal_id, 0.0))

    overlap_pairs: List[Dict[str, Any]] = []
    ordered_ids = list(score_matrix)
    for index, left_goal in enumerate(ordered_ids):
        for right_goal in ordered_ids[index + 1:]:
            similarity = cosine_similarity(
                score_matrix[left_goal],
                score_matrix[right_goal],
            )
            if similarity >= threshold:
                overlap_pairs.append(
                    {
                        "left": left_goal,
                        "right": right_goal,
                        "similarity": round(similarity, 3),
                        "comparison_population": "active_standalone_public_peers",
                    }
                )
    overlap_pairs.sort(
        key=lambda item: (
            -float(item.get("similarity") or 0.0),
            item.get("left"),
            item.get("right"),
        )
    )
    return overlap_pairs


def _build_specialist_residual_checks(
    specialist_models: Sequence[Dict[str, Any]],
    scenario_results: Sequence[Dict[str, Any]],
    *,
    inventory_by_id: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []
    result_rows_by_scenario = {
        str(result.get("id") or ""): {
            str(item.get("goal_id") or ""): item
            for item in (result.get("ranking") or [])
        }
        for result in scenario_results
    }

    for model in specialist_models:
        specialist_id = str(model.get("id") or "").strip().lower()
        composition = model.get("composition") or {}
        parent_id = str(composition.get("parent_id") or "").strip().lower()
        configured_bound = float(composition.get("max_abs_residual") or 0.0)
        residuals: List[Dict[str, Any]] = []
        for scenario in SCENARIOS:
            scenario_id = str(scenario.get("id") or "")
            specialist_row = (
                result_rows_by_scenario.get(scenario_id, {}).get(specialist_id)
                or {}
            )
            residuals.append(
                {
                    "scenario": scenario_id,
                    "residual_lift": round(
                        float(specialist_row.get("specialist_residual") or 0.0),
                        6,
                    ),
                }
            )

        values = [float(item["residual_lift"]) for item in residuals]
        nonzero_values = [
            value
            for value in values
            if abs(value) > RESIDUAL_DISTINCTNESS_TOLERANCE
        ]
        minimum = min(values, default=0.0)
        maximum = max(values, default=0.0)
        residual_range = maximum - minimum
        max_abs_observed = max((abs(value) for value in values), default=0.0)
        distinctness_passed = bool(
            nonzero_values
            and residual_range > RESIDUAL_DISTINCTNESS_TOLERANCE
        )
        bound_passed = bool(
            configured_bound > 0.0
            and max_abs_observed
            <= configured_bound + RESIDUAL_DISTINCTNESS_TOLERANCE
        )
        inventory = inventory_by_id.get(specialist_id) or {}
        checks.append(
            {
                "specialist_id": specialist_id,
                "parent_id": parent_id,
                "status": inventory.get("status"),
                "gate_bucket": inventory.get("gate_bucket"),
                "method": "specialist_residual_vector",
                "raw_full_model_cosine_excluded": True,
                "exclusion_reason": (
                    "Full-model cosine is structurally inflated by declared parent "
                    "inheritance; only the bounded residual is assessed."
                ),
                "scenario_count": len(values),
                "nonzero_residual_count": len(nonzero_values),
                "positive_lift_count": sum(
                    1
                    for value in values
                    if value > RESIDUAL_DISTINCTNESS_TOLERANCE
                ),
                "negative_lift_count": sum(
                    1
                    for value in values
                    if value < -RESIDUAL_DISTINCTNESS_TOLERANCE
                ),
                "zero_lift_count": len(values) - len(nonzero_values),
                "minimum_residual_lift": round(minimum, 6),
                "maximum_residual_lift": round(maximum, 6),
                "residual_range": round(residual_range, 6),
                "configured_max_abs_residual": configured_bound,
                "observed_max_abs_residual": round(max_abs_observed, 6),
                "distinctness_passed": distinctness_passed,
                "bound_passed": bound_passed,
                "check_passed": distinctness_passed and bound_passed,
                "affects_default_public_gate": False,
                "residuals": residuals,
            }
        )
    checks.sort(key=lambda item: str(item.get("specialist_id") or ""))
    return checks


def run_stress_suite(
    *,
    overlap_threshold: float = DEFAULT_PEER_OVERLAP_THRESHOLD,
) -> Dict[str, Any]:
    threshold = float(overlap_threshold)
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("overlap_threshold must be between 0 and 1")

    models = list_goal_models(include_deprecated=True)
    inventory = [_model_inventory_entry(model) for model in models]
    inventory.sort(key=lambda item: str(item.get("goal_id") or ""))
    inventory_by_id = {
        str(item.get("goal_id") or ""): item for item in inventory
    }
    models_by_id = {
        str(model.get("id") or "").strip().lower(): model
        for model in models
    }

    public_peer_model_ids = [
        str(item["goal_id"])
        for item in inventory
        if item.get("gate_bucket") == "public_peer"
    ]
    active_specialist_models = [
        models_by_id[str(item["goal_id"])]
        for item in inventory
        if item.get("gate_bucket") == "active_specialist_residual"
    ]
    research_models = [
        models_by_id[str(item["goal_id"])]
        for item in inventory
        if item.get("gate_bucket") == "non_public_research"
    ]
    evaluated_model_ids = [
        str(item["goal_id"])
        for item in inventory
        if item.get("gate_bucket") != "excluded"
    ]

    all_scenario_results = [
        evaluate_scenario(scenario, model_ids=evaluated_model_ids)
        for scenario in SCENARIOS
    ]
    (
        public_scenarios,
        public_semantic_failures,
        semantic_exclusions,
    ) = evaluate_public_semantic_expectations(
        all_scenario_results,
        public_peer_model_ids=public_peer_model_ids,
        inventory_by_id=inventory_by_id,
    )
    public_overlap_pairs = _find_high_overlap_pairs(
        public_scenarios,
        model_ids=public_peer_model_ids,
        threshold=threshold,
    )
    public_gate_passed = not public_semantic_failures and not public_overlap_pairs

    active_specialist_checks = _build_specialist_residual_checks(
        active_specialist_models,
        all_scenario_results,
        inventory_by_id=inventory_by_id,
    )
    research_specialist_models = [
        model
        for model in research_models
        if str((model.get("composition") or {}).get("mode") or "")
        == SPECIALIST_COMPOSITION_MODE
    ]
    research_residual_checks = _build_specialist_residual_checks(
        research_specialist_models,
        all_scenario_results,
        inventory_by_id=inventory_by_id,
    )
    research_model_ids = [
        str(model.get("id") or "").strip().lower()
        for model in research_models
    ]
    research_scenarios = _filter_scenario_results(
        all_scenario_results,
        research_model_ids,
    )

    intentional_pair_exclusions = [
        {
            "parent_id": str((model.get("composition") or {}).get("parent_id") or ""),
            "specialist_id": str(model.get("id") or ""),
            "specialist_status": str(model.get("status") or ""),
            "excluded_comparison": "raw_full_model_cosine",
            "replacement_test": "specialist_residual_vector",
            "reason": (
                "The declared specialist inherits its parent by construction, so "
                "full-model cosine is not an independent peer-overlap test."
            ),
        }
        for model in [*active_specialist_models, *research_specialist_models]
    ]
    intentional_pair_exclusions.sort(
        key=lambda item: str(item.get("specialist_id") or "")
    )
    model_exclusions = [
        dict(item)
        for item in inventory
        if item.get("gate_bucket") != "public_peer"
    ]

    public_gate = {
        "name": "active_standalone_public_peer_gate",
        "model_ids": public_peer_model_ids,
        "model_count": len(public_peer_model_ids),
        "semantic_failures": public_semantic_failures,
        "semantic_failure_count": len(public_semantic_failures),
        "high_overlap_pairs": public_overlap_pairs,
        "high_overlap_pair_count": len(public_overlap_pairs),
        "overlap_threshold": threshold,
        "passed": public_gate_passed,
    }
    active_specialist_section = {
        "model_ids": [
            str(model.get("id") or "") for model in active_specialist_models
        ],
        "checks": active_specialist_checks,
        "all_checks_passed": all(
            bool(check.get("check_passed")) for check in active_specialist_checks
        ),
        "affects_default_public_gate": False,
        "reason": (
            "Active specialists are declared residual compositions, not independent "
            "standalone peers. Their residual diagnostics are reported separately."
        ),
    }
    research_section = {
        "non_public": True,
        "affects_default_public_gate": False,
        "model_ids": research_model_ids,
        "models": [
            dict(inventory_by_id[goal_id]) for goal_id in research_model_ids
        ],
        "scenarios": research_scenarios,
        "residual_checks": research_residual_checks,
        "note": (
            "Experimental models are research observations only. Synthetic rankings "
            "do not validate outcomes or promote these models to public use."
        ),
    }

    return {
        "scenario_count": len(all_scenario_results),
        "goal_count": len(inventory),
        "evaluated_goal_count": len(evaluated_model_ids),
        "model_inventory": inventory,
        "model_exclusions": model_exclusions,
        "intentional_parent_specialist_pair_exclusions": intentional_pair_exclusions,
        "public_gate": public_gate,
        "active_specialist_residuals": active_specialist_section,
        "non_public_research": research_section,
        "scenarios": public_scenarios,
        "expectation_failures": public_semantic_failures,
        "semantic_expectation_exclusions": semantic_exclusions,
        "high_overlap_pairs": public_overlap_pairs,
        "overlap_threshold": threshold,
        "gate_passed": public_gate_passed,
        "validation_scope": {
            "fixture_type": "synthetic_semantic_stress",
            "semantic_only": True,
            "outcome_validation": False,
            "default_public_gate": "active_standalone_peers_only",
            "active_specialist_assessment": "separate_residual_diagnostics",
            "experimental_models": "separate_non_public_research",
            "public_specialist_gate": "requires_held_out_lift",
            "promotion_requirement": "positive held-out lift on person-grouped historical outcomes",
        },
    }
