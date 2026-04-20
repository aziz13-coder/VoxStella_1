from __future__ import annotations

from math import sqrt
from typing import Any, Dict, List, Sequence, Tuple

from astrocartography_goal_engine import evaluate_goal_model, extract_relocation_features
from astrocartography_goal_models import list_goal_models


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


def evaluate_scenario(scenario: Dict[str, Any]) -> Dict[str, Any]:
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


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    dot = sum(float(a) * float(b) for a, b in zip(left, right))
    left_norm = sqrt(sum(float(a) * float(a) for a in left))
    right_norm = sqrt(sum(float(b) * float(b) for b in right))
    if left_norm <= 0.0 or right_norm <= 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def run_stress_suite() -> Dict[str, Any]:
    scenario_results = [evaluate_scenario(scenario) for scenario in SCENARIOS]
    goal_ids = [str(model.get("id") or "") for model in list_goal_models()]
    score_matrix: Dict[str, List[float]] = {goal_id: [] for goal_id in goal_ids}
    expectation_failures: List[Dict[str, Any]] = []

    for result in scenario_results:
        ranking = result.get("ranking") or []
        top_ids = [str(item.get("goal_id") or "") for item in ranking[:3]]
        top_id = top_ids[0] if top_ids else ""
        expected = [str(item) for item in result.get("expected") or []]
        expected_lead = str(result.get("expected_lead") or "")
        if expected_lead and top_id != expected_lead:
            expectation_failures.append(
                {
                    "scenario": result.get("id"),
                    "expected_lead": expected_lead,
                    "top_id": top_id,
                    "top_ids": top_ids,
                }
            )
        if expected and not any(goal_id in top_ids for goal_id in expected):
            expectation_failures.append(
                {
                    "scenario": result.get("id"),
                    "expected": expected,
                    "top_ids": top_ids,
                }
            )
        scores_by_goal = {str(item.get("goal_id") or ""): float(item.get("raw_score") or 0.0) for item in ranking}
        for goal_id in goal_ids:
            score_matrix[goal_id].append(scores_by_goal.get(goal_id, 0.0))

    overlap_pairs: List[Dict[str, Any]] = []
    for index, left_goal in enumerate(goal_ids):
        for right_goal in goal_ids[index + 1:]:
            similarity = cosine_similarity(score_matrix[left_goal], score_matrix[right_goal])
            if similarity >= 0.92:
                overlap_pairs.append(
                    {
                        "left": left_goal,
                        "right": right_goal,
                        "similarity": round(similarity, 3),
                    }
                )
    overlap_pairs.sort(key=lambda item: (-float(item.get("similarity") or 0.0), item.get("left"), item.get("right")))

    return {
        "scenario_count": len(scenario_results),
        "goal_count": len(goal_ids),
        "scenarios": scenario_results,
        "expectation_failures": expectation_failures,
        "high_overlap_pairs": overlap_pairs,
    }
