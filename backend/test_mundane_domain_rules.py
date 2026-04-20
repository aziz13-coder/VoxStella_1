from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mundane_domain_rules import evaluate_domain_context
from mundane_models import ActiveClockContext, MundaneContextRequest, ResolvedMundaneContext


def _context(*, domain_id: str, chart_resolution, location_context_id: str = "event_chart", location: str = "Paris, France"):
    return ResolvedMundaneContext(
        request=MundaneContextRequest(chart_type="war_event", domain=domain_id, polity_id="france"),
        active_clock=ActiveClockContext(
            timestamp=datetime(2025, 4, 11, 12, 0, tzinfo=timezone.utc).isoformat(),
            location=location,
            timezone="Europe/Paris",
            mode="manual",
            house_system_code="P",
            latitude=48.8566,
            longitude=2.3522,
        ),
        chart_type={"id": "war_event", "label": "War Event"},
        domain={"id": domain_id, "label": domain_id},
        location_context={"id": location_context_id, "label": location_context_id},
        polity={"id": "france", "label": "France", "capital": "Paris, France", "default_location": "Paris, France"},
        reference_chart=None,
        event_context={"location_context_type": location_context_id, "reference_location": location},
        chart_resolution=chart_resolution,
        research_flags=["benchmark_backed"],
        source_tags=["watters_war_houses"],
    )


def test_evaluate_war_conflict_detects_mars_angular_and_retrograde():
    context = _context(
        domain_id="war_conflict",
        chart_resolution={
            "primary_chart": {
                "kind": "war_event",
                "house_rulers": {"1": "Mars", "7": "Venus"},
                "angles": {"ascendant": 0.0, "midheaven": 90.0},
                "planets": {
                    "Mars": {"house": 1, "retrograde": True, "longitude": 10.0},
                    "Saturn": {"house": 7, "retrograde": False, "longitude": 200.0},
                    "Venus": {"house": 11, "retrograde": False, "longitude": 150.0},
                },
            },
            "signals": {
                "aggressor_house": {"ruler": "Mars", "house_position": 1},
                "defender_house": {"ruler": "Venus", "house_position": 11},
                "mars_retrograde": True,
                "activation_hits": [{"planet": "Saturn", "target_point": "Sun", "orb_deg": 1.2}],
            },
        },
    )

    assessment = evaluate_domain_context(context)

    assert assessment["domain_id"] == "war_conflict"
    assert assessment["score"] >= 40
    assert assessment["level"] in {"elevated", "high", "critical"}
    labels = {row["label"] for row in assessment["matched_rules"]}
    assert "Mars angular" in labels
    assert "Mars retrograde" in labels
    assert "compatibility_umbrella" in assessment["research_flags"]


def test_evaluate_war_outbreak_tracks_first_hostilities_polarity():
    context = _context(
        domain_id="war_outbreak",
        chart_resolution={
            "primary_chart": {
                "kind": "war_event",
                "house_rulers": {"1": "Mars", "7": "Venus"},
                "angles": {"ascendant": 0.0, "midheaven": 90.0},
                "planets": {
                    "Mars": {"house": 1, "retrograde": False, "longitude": 3.0},
                    "Moon": {"house": 7, "retrograde": False, "longitude": 179.0},
                    "Venus": {"house": 10, "retrograde": False, "longitude": 92.0},
                },
            },
            "signals": {
                "aggressor_house": {"ruler": "Mars", "house_position": 1, "closest_angle": "ascendant", "angle_distance_deg": 3.0},
                "defender_house": {"ruler": "Venus", "house_position": 10, "closest_angle": "midheaven", "angle_distance_deg": 2.0},
            },
        },
    )

    assessment = evaluate_domain_context(context)

    assert assessment["domain_id"] == "war_outbreak"
    labels = {row["label"] for row in assessment["matched_rules"]}
    assert "War-event anchor" in labels
    assert "Mars angular" in labels
    assert "Aggressor ruler angular" in labels
    assert "Moon on conflict axis" in labels
    assert "Open conflict polarity" in labels
    assert assessment["raw_score"] >= 30
    assert assessment["calibration"]["coverage_tier"] in {"moderate", "supported", "broad"}


def test_evaluate_war_outbreak_downgrades_non_war_event_chart():
    context = ResolvedMundaneContext(
        request=MundaneContextRequest(chart_type="aries_ingress", domain="war_outbreak", polity_id="france"),
        active_clock=ActiveClockContext(
            timestamp=datetime(2025, 4, 11, 12, 0, tzinfo=timezone.utc).isoformat(),
            location="Paris, France",
            timezone="Europe/Paris",
            mode="manual",
            house_system_code="P",
            latitude=48.8566,
            longitude=2.3522,
        ),
        chart_type={"id": "aries_ingress", "label": "Aries Ingress"},
        domain={"id": "war_outbreak", "label": "War Outbreak"},
        location_context={"id": "capital_chart", "label": "capital_chart"},
        polity={"id": "france", "label": "France", "capital": "Paris, France", "default_location": "Paris, France"},
        reference_chart=None,
        event_context={"location_context_type": "capital_chart", "reference_location": "Paris, France"},
        chart_resolution={
            "primary_chart": {
                "kind": "aries_ingress",
                "house_rulers": {"1": "Mars", "7": "Venus"},
                "angles": {"ascendant": 0.0, "midheaven": 90.0},
                "planets": {
                    "Mars": {"house": 1, "retrograde": False, "longitude": 3.0},
                    "Moon": {"house": 7, "retrograde": False, "longitude": 179.0},
                    "Venus": {"house": 10, "retrograde": False, "longitude": 92.0},
                },
            },
            "signals": {
                "aggressor_house": {"ruler": "Mars", "house_position": 1, "closest_angle": "ascendant", "angle_distance_deg": 3.0},
                "defender_house": {"ruler": "Venus", "house_position": 10, "closest_angle": "midheaven", "angle_distance_deg": 2.0},
            },
        },
        research_flags=["benchmark_backed"],
        source_tags=["watters_war_houses"],
    )

    assessment = evaluate_domain_context(context)

    assert assessment["domain_id"] == "war_outbreak"
    assert "outbreak_chart_mismatch" in assessment["research_flags"]
    assert any("downgraded outside a war-event anchor" in item for item in assessment["cautions"])
    assert assessment["score"] < assessment["raw_score"]


def test_evaluate_campaign_escalation_tracks_sustained_malefic_and_activation_pressure():
    context = _context(
        domain_id="campaign_escalation",
        chart_resolution={
            "primary_chart": {
                "kind": "war_event",
                "house_rulers": {"1": "Mars", "7": "Moon"},
                "angles": {"ascendant": 0.0, "midheaven": 90.0},
                "planets": {
                    "Mars": {"house": 1, "retrograde": False, "longitude": 4.0},
                    "Saturn": {"house": 10, "retrograde": False, "longitude": 91.0},
                    "Moon": {"house": 7, "retrograde": False, "longitude": 181.0},
                },
            },
            "signals": {
                "aggressor_house": {"ruler": "Mars", "house_position": 1, "closest_angle": "ascendant", "angle_distance_deg": 4.0},
                "defender_house": {"ruler": "Moon", "house_position": 7, "closest_angle": "descendant", "angle_distance_deg": 1.0},
                "activation_hits": [{"planet": "Saturn", "target_point": "Eclipse", "orb_deg": 0.8}],
            },
        },
    )

    assessment = evaluate_domain_context(context)

    assert assessment["domain_id"] == "campaign_escalation"
    labels = {row["label"] for row in assessment["matched_rules"]}
    assert "Saturn angular" in labels
    assert "Escalating conflict polarity" in labels
    assert "Defender ruler angular" in labels
    assert "Joint malefic pressure" in labels
    assert "Eclipse-degree activation" in labels
    assert assessment["raw_score"] >= 35


def test_evaluate_military_reversal_tracks_retrograde_and_defender_strength():
    context = _context(
        domain_id="military_reversal",
        chart_resolution={
            "primary_chart": {
                "kind": "war_event",
                "house_rulers": {"1": "Mars", "7": "Venus"},
                "angles": {"ascendant": 0.0, "midheaven": 90.0},
                "planets": {
                    "Mars": {"house": 1, "retrograde": True, "longitude": 8.0},
                    "Venus": {"house": 7, "retrograde": False, "longitude": 179.0},
                    "Saturn": {"house": 6, "retrograde": False, "longitude": 140.0},
                },
            },
            "signals": {
                "aggressor_house": {"ruler": "Mars", "house_position": 1, "closest_angle": "ascendant", "angle_distance_deg": 8.0},
                "defender_house": {"ruler": "Venus", "house_position": 7, "closest_angle": "descendant", "angle_distance_deg": 1.0},
                "mars_retrograde": True,
                "activation_hits": [{"planet": "Mars", "target_point": "Eclipse", "orb_deg": 1.2}],
            },
        },
    )

    assessment = evaluate_domain_context(context)

    assert assessment["domain_id"] == "military_reversal"
    labels = {row["label"] for row in assessment["matched_rules"]}
    assert "Mars retrograde" in labels
    assert "Saturn in the sixth" in labels
    assert "Defender ruler angular" in labels
    assert "Defender resilience" in labels
    assert "Aggressor overreach under retrograde Mars" in labels
    assert assessment["raw_score"] >= 35


def test_evaluate_leadership_transition_tracks_solar_and_tenth_house_transition_pressure():
    context = _context(
        domain_id="leadership_transition",
        chart_resolution={
            "primary_chart": {
                "kind": "national_chart",
                "house_rulers": {"10": "Sun"},
                "angles": {"ascendant": 0.0, "midheaven": 90.0},
                "planets": {
                    "Sun": {"house": 10, "retrograde": False, "longitude": 91.2},
                    "Moon": {"house": 10, "retrograde": False, "longitude": 88.5},
                    "Mars": {"house": 1, "retrograde": True, "longitude": 4.0},
                    "Jupiter": {"house": 7, "retrograde": False, "longitude": 185.0},
                },
            },
            "signals": {
                "activation_hits": [{"planet": "Saturn", "target_point": "Sun", "orb_deg": 0.7}],
            },
        },
    )

    assessment = evaluate_domain_context(context)

    assert assessment["domain_id"] == "leadership_transition"
    labels = {row["label"] for row in assessment["matched_rules"]}
    assert "Sun angular" in labels
    assert "Sun in the tenth" in labels
    assert "Tenth-house ruler angular" in labels
    assert "Mars retrograde" in labels
    assert assessment["raw_score"] >= 35
    assert assessment["calibration"]["coverage_tier"] in {"moderate", "supported", "broad"}


def test_evaluate_regime_stability_tracks_capital_chart_and_parliamentary_stress():
    context = _context(
        domain_id="regime_stability",
        location_context_id="capital_chart",
        chart_resolution={
            "primary_chart": {
                "kind": "aries_ingress",
                "house_rulers": {"4": "Moon", "10": "Saturn", "11": "Mercury"},
                "angles": {"ascendant": 0.0, "midheaven": 90.0},
                "planets": {
                    "Saturn": {"house": 10, "retrograde": True, "longitude": 94.0},
                    "Mercury": {"house": 11, "retrograde": True, "longitude": 325.0},
                    "Uranus": {"house": 11, "retrograde": False, "longitude": 312.0},
                    "Jupiter": {"house": 1, "retrograde": False, "longitude": 2.2},
                },
            },
            "signals": {
                "activation_hits": [{"planet": "Mars", "target_point": "MC", "orb_deg": 1.1}],
            },
        },
    )

    assessment = evaluate_domain_context(context)

    assert assessment["domain_id"] == "regime_stability"
    labels = {row["label"] for row in assessment["matched_rules"]}
    assert "Tenth-house ruler retrograde" in labels
    assert "Eleventh-house ruler retrograde" in labels
    assert "Saturn in the 10th" in labels
    assert "Uranus in the 11th" in labels
    assert "Capital-chart alignment" in labels
    assert assessment["raw_score"] >= 35


def test_evaluate_regime_stability_tracks_neptune_and_saturn_parliamentary_collapse_signals():
    context = _context(
        domain_id="regime_stability",
        location_context_id="capital_chart",
        chart_resolution={
            "primary_chart": {
                "kind": "aries_ingress",
                "house_rulers": {"10": "Sun", "11": "Mercury"},
                "angles": {"ascendant": 0.0, "midheaven": 90.0},
                "planets": {
                    "Saturn": {"house": 11, "retrograde": False, "longitude": 301.0},
                    "Uranus": {"house": 11, "retrograde": False, "longitude": 312.0},
                    "Neptune": {"house": 10, "retrograde": False, "longitude": 95.0},
                    "Mercury": {"house": 11, "retrograde": False, "longitude": 319.0},
                },
            },
            "signals": {},
        },
    )

    assessment = evaluate_domain_context(context)

    labels = {row["label"] for row in assessment["matched_rules"]}
    assert "Saturn in the 11th" in labels
    assert "Uranus in the 11th" in labels
    assert "Neptune in the 10th" in labels


def test_evaluate_government_stability_keeps_compatibility_umbrella():
    context = _context(
        domain_id="government_stability",
        location_context_id="capital_chart",
        chart_resolution={
            "primary_chart": {
                "kind": "aries_ingress",
                "house_rulers": {"10": "Sun", "11": "Mercury"},
                "angles": {"ascendant": 0.0, "midheaven": 90.0},
                "planets": {
                    "Sun": {"house": 10, "retrograde": False, "longitude": 92.0},
                    "Mercury": {"house": 11, "retrograde": True, "longitude": 313.0},
                    "Mars": {"house": 10, "retrograde": False, "longitude": 96.0},
                },
            },
            "signals": {},
        },
    )

    assessment = evaluate_domain_context(context)

    assert assessment["domain_id"] == "government_stability"
    assert "compatibility_umbrella" in assessment["research_flags"]
    labels = {row["label"] for row in assessment["matched_rules"]}
    assert "Sun angular" in labels
    assert "Eleventh-house ruler retrograde" in labels
    assert assessment["raw_score"] >= 20


def test_evaluate_diplomacy_allows_benefic_support_to_reduce_strain():
    context = _context(
        domain_id="diplomacy_foreign_affairs",
        chart_resolution={
            "primary_chart": {
                "kind": "aries_ingress",
                "house_rulers": {"7": "Venus"},
                "angles": {"ascendant": 0.0, "midheaven": 90.0},
                "planets": {
                    "Venus": {"house": 7, "retrograde": False, "longitude": 185.0},
                    "Jupiter": {"house": 10, "retrograde": False, "longitude": 280.0},
                    "Mars": {"house": 3, "retrograde": False, "longitude": 70.0},
                },
            },
            "signals": {},
        },
    )

    assessment = evaluate_domain_context(context)

    assert assessment["domain_id"] == "diplomacy_foreign_affairs"
    assert assessment["score"] <= assessment["raw_score"]
    assert assessment["level"] in {"quiet", "elevated"}
    labels = {row["label"] for row in assessment["matched_rules"]}
    assert "Seventh-house ruler angular" in labels
    assert "Venus angular" in labels
    assert "Jupiter angular" in labels
    assert assessment["raw_score"] >= 0
    assert assessment["calibration"]["coverage_tier"] in {"seeded", "moderate", "supported", "broad"}


def test_evaluate_diplomacy_tracks_ninth_house_treaty_support():
    context = _context(
        domain_id="diplomacy_foreign_affairs",
        chart_resolution={
            "primary_chart": {
                "kind": "aries_ingress",
                "house_rulers": {"7": "Mercury", "9": "Venus", "11": "Moon"},
                "angles": {"ascendant": 0.0, "midheaven": 90.0},
                "planets": {
                    "Venus": {"house": 9, "retrograde": False, "longitude": 242.0},
                    "Jupiter": {"house": 9, "retrograde": False, "longitude": 251.0},
                    "Mercury": {"house": 3, "retrograde": False, "longitude": 40.0},
                    "Mars": {"house": 6, "retrograde": False, "longitude": 120.0},
                },
            },
            "signals": {},
        },
    )

    assessment = evaluate_domain_context(context)

    assert assessment["domain_id"] == "diplomacy_foreign_affairs"
    assert assessment["level"] == "quiet"
    labels = {row["label"] for row in assessment["matched_rules"]}
    assert "Venus in the ninth" in labels
    assert "Jupiter in the ninth" in labels
    assert assessment["score"] <= assessment["raw_score"]


def test_evaluate_diplomacy_tracks_ally_network_stress():
    context = _context(
        domain_id="diplomacy_foreign_affairs",
        chart_resolution={
            "primary_chart": {
                "kind": "national_chart",
                "house_rulers": {"7": "Venus", "9": "Mercury", "11": "Moon"},
                "angles": {"ascendant": 0.0, "midheaven": 90.0},
                "planets": {
                    "Moon": {"house": 11, "retrograde": False, "longitude": 140.0},
                    "Saturn": {"house": 11, "retrograde": False, "longitude": 144.5},
                    "Venus": {"house": 4, "retrograde": False, "longitude": 310.0},
                    "Mars": {"house": 2, "retrograde": False, "longitude": 30.0},
                },
            },
            "signals": {},
        },
    )

    assessment = evaluate_domain_context(context)

    assert assessment["domain_id"] == "diplomacy_foreign_affairs"
    assert assessment["raw_score"] >= 20
    labels = {row["label"] for row in assessment["matched_rules"]}
    assert "Moon-Saturn allied stress" in labels
    assert assessment["summary"].startswith("Diplomatic strain is evaluated from seventh-, ninth-, and eleventh-house condition")


def test_evaluate_diplomacy_tracks_mercury_seventh_breakdown():
    context = _context(
        domain_id="diplomacy_foreign_affairs",
        chart_resolution={
            "primary_chart": {
                "kind": "aries_ingress",
                "house_rulers": {"7": "Mercury", "9": "Jupiter", "11": "Venus"},
                "angles": {"ascendant": 0.0, "midheaven": 90.0},
                "planets": {
                    "Mercury": {"house": 7, "retrograde": True, "longitude": 182.0},
                    "Mars": {"house": 10, "retrograde": False, "longitude": 91.5},
                    "Venus": {"house": 11, "retrograde": False, "longitude": 315.0},
                },
            },
            "signals": {},
        },
    )

    assessment = evaluate_domain_context(context)

    assert assessment["domain_id"] == "diplomacy_foreign_affairs"
    labels = {row["label"] for row in assessment["matched_rules"]}
    assert "Mercury in the seventh under strain" in labels
    assert assessment["raw_score"] >= 20


def test_evaluate_alliance_stress_tracks_eleventh_house_support_failure():
    context = _context(
        domain_id="alliance_stress",
        chart_resolution={
            "primary_chart": {
                "kind": "national_chart",
                "house_rulers": {"7": "Mercury", "11": "Mercury"},
                "angles": {"ascendant": 0.0, "midheaven": 90.0},
                "planets": {
                    "Moon": {"house": 11, "retrograde": False, "longitude": 140.0},
                    "Saturn": {"house": 11, "retrograde": False, "longitude": 144.5},
                    "Mercury": {"house": 12, "retrograde": True, "longitude": 220.0},
                    "Venus": {"house": 4, "retrograde": False, "longitude": 315.0},
                },
            },
            "signals": {},
        },
    )

    assessment = evaluate_domain_context(context)

    assert assessment["domain_id"] == "alliance_stress"
    assert assessment["raw_score"] >= 20
    labels = {row["label"] for row in assessment["matched_rules"]}
    assert "Moon-Saturn allied stress" in labels
    assert "Eleventh-house ruler in a burden house" in labels
    assert "Seventh-house ruler retrograde" in labels
    assert assessment["summary"].startswith("Alliance stress is evaluated from the eleventh house")


def test_evaluate_alliance_stress_tracks_resource_and_foreign_relations_strain():
    context = _context(
        domain_id="alliance_stress",
        chart_resolution={
            "primary_chart": {
                "kind": "national_chart",
                "house_rulers": {"7": "Mars", "8": "Saturn", "9": "Mercury", "11": "Moon"},
                "angles": {"ascendant": 0.0, "midheaven": 90.0},
                "planets": {
                    "Mars": {"house": 8, "retrograde": True, "longitude": 210.0},
                    "Saturn": {"house": 11, "retrograde": False, "longitude": 315.0},
                    "Mercury": {"house": 12, "retrograde": True, "longitude": 333.0},
                    "Venus": {"house": 7, "retrograde": True, "longitude": 182.0},
                    "Moon": {"house": 11, "retrograde": False, "longitude": 140.0},
                },
            },
            "signals": {},
        },
    )

    assessment = evaluate_domain_context(context)

    labels = {row["label"] for row in assessment["matched_rules"]}
    assert "Seventh-house ruler in the eighth" in labels
    assert "Ninth-house ruler retrograde" in labels
    assert "Ninth-house ruler in a burden house" in labels
    assert "Eighth-house ruler in an alliance house" in labels
    assert "Venus in the seventh retrograde" in labels


def test_evaluate_alliance_stress_tracks_saturn_in_the_seventh():
    context = _context(
        domain_id="alliance_stress",
        chart_resolution={
            "primary_chart": {
                "kind": "aries_ingress",
                "house_rulers": {"7": "Saturn", "11": "Moon"},
                "angles": {"ascendant": 0.0, "midheaven": 90.0},
                "planets": {
                    "Saturn": {"house": 7, "retrograde": False, "longitude": 182.0},
                    "Moon": {"house": 11, "retrograde": False, "longitude": 140.0},
                },
            },
            "signals": {},
        },
    )

    assessment = evaluate_domain_context(context)

    labels = {row["label"] for row in assessment["matched_rules"]}
    assert "Saturn in the seventh" in labels


def test_evaluate_trade_and_commerce_tracks_foreign_trade_dispute():
    context = _context(
        domain_id="trade_and_commerce",
        chart_resolution={
            "primary_chart": {
                "kind": "aries_ingress",
                "house_rulers": {"2": "Mercury", "7": "Mercury", "9": "Jupiter", "11": "Saturn"},
                "angles": {"ascendant": 0.0, "midheaven": 90.0},
                "planets": {
                    "Mercury": {"house": 7, "retrograde": True, "longitude": 182.0},
                    "Mars": {"house": 10, "retrograde": False, "longitude": 91.5},
                    "Saturn": {"house": 11, "retrograde": False, "longitude": 312.0},
                    "Jupiter": {"house": 9, "retrograde": False, "longitude": 248.0},
                },
            },
            "signals": {},
        },
    )

    assessment = evaluate_domain_context(context)

    assert assessment["domain_id"] == "trade_and_commerce"
    labels = {row["label"] for row in assessment["matched_rules"]}
    assert "Mercury in the seventh under strain" in labels
    assert "Saturn in the eleventh" in labels
    assert "Foreign trade dispute axis" in labels
    assert assessment["summary"].startswith("Trade and commerce are evaluated from second-house commercial resources")


def test_evaluate_trade_and_commerce_tracks_mercurial_and_neptunian_commerce_strain():
    context = _context(
        domain_id="trade_and_commerce",
        chart_resolution={
            "primary_chart": {
                "kind": "aries_ingress",
                "house_rulers": {"2": "Mercury", "7": "Venus", "9": "Jupiter", "11": "Saturn"},
                "angles": {"ascendant": 0.0, "midheaven": 90.0},
                "planets": {
                    "Mercury": {"house": 2, "retrograde": True, "longitude": 15.0},
                    "Neptune": {"house": 9, "retrograde": False, "longitude": 245.0},
                    "Venus": {"house": 7, "retrograde": False, "longitude": 182.0},
                    "Saturn": {"house": 11, "retrograde": False, "longitude": 312.0},
                },
            },
            "signals": {},
        },
    )

    assessment = evaluate_domain_context(context)

    labels = {row["label"] for row in assessment["matched_rules"]}
    assert "Mercury in the second under strain" in labels
    assert "Neptune in the ninth" in labels
    assert "Venus in the seventh" in labels


def test_evaluate_trade_and_commerce_tracks_saturn_in_the_seventh():
    context = _context(
        domain_id="trade_and_commerce",
        chart_resolution={
            "primary_chart": {
                "kind": "aries_ingress",
                "house_rulers": {"2": "Mercury", "7": "Saturn", "9": "Jupiter", "11": "Venus"},
                "angles": {"ascendant": 0.0, "midheaven": 90.0},
                "planets": {
                    "Saturn": {"house": 7, "retrograde": False, "longitude": 185.0},
                    "Mercury": {"house": 2, "retrograde": False, "longitude": 25.0},
                    "Jupiter": {"house": 9, "retrograde": False, "longitude": 248.0},
                },
            },
            "signals": {},
        },
    )

    assessment = evaluate_domain_context(context)

    labels = {row["label"] for row in assessment["matched_rules"]}
    assert "Saturn in the seventh" in labels


def test_evaluate_trade_and_commerce_tracks_legislation_and_cycle_backdrop():
    context = _context(
        domain_id="trade_and_commerce",
        chart_resolution={
            "primary_chart": {
                "kind": "aries_ingress",
                "house_rulers": {"2": "Saturn", "7": "Venus", "9": "Jupiter", "11": "Mercury"},
                "angles": {"ascendant": 0.0, "midheaven": 90.0},
                "planets": {
                    "Saturn": {"house": 11, "retrograde": True, "longitude": 275.0},
                    "Mercury": {"house": 11, "retrograde": True, "longitude": 281.0},
                    "Venus": {"house": 7, "retrograde": False, "longitude": 185.0},
                },
            },
            "cycle_context": {
                "type": "jupiter_saturn_cycle",
                "nearest_conjunction_datetime": "2020-12-21T18:00:00+00:00",
                "nearest_distance_years": 2.8,
                "cycle_phase": "opening_cycle",
                "turning_window_active": True,
                "turning_window_level": "strong",
                "conjunction_sign": "Aquarius",
            },
            "signals": {},
        },
    )

    assessment = evaluate_domain_context(context)

    labels = {row["label"] for row in assessment["matched_rules"]}
    assert "Second-house ruler retrograde" in labels
    assert "Second-house ruler in the eleventh" in labels
    assert "Mercury in the eleventh" in labels
    assert "Commercial-legislation blockage" in labels
    assert "Mutation-cycle trade backdrop" in labels


def test_evaluate_public_health_tracks_institutional_burden_and_relief():
    context = _context(
        domain_id="public_health",
        chart_resolution={
            "primary_chart": {
                "kind": "aries_ingress",
                "house_rulers": {"6": "Moon", "8": "Saturn", "12": "Mercury"},
                "angles": {"ascendant": 0.0, "midheaven": 90.0},
                "planets": {
                    "Mars": {"house": 1, "retrograde": False, "longitude": 4.0},
                    "Mercury": {"house": 10, "retrograde": False, "longitude": 94.0},
                    "Saturn": {"house": 12, "retrograde": False, "longitude": 333.0},
                    "Jupiter": {"house": 12, "retrograde": False, "longitude": 340.0},
                },
            },
            "signals": {},
        },
    )

    assessment = evaluate_domain_context(context)

    assert assessment["domain_id"] == "public_health"
    labels = {row["label"] for row in assessment["matched_rules"]}
    assert "Mars in the first" in labels
    assert "Twelfth-house ruler angular" in labels
    assert "Saturn in the twelfth" in labels
    assert "Jupiter in the twelfth" in labels
    assert assessment["score"] <= assessment["raw_score"]


def test_evaluate_epidemic_wave_pressure_tracks_wave_recurrence_and_timing():
    context = _context(
        domain_id="epidemic_wave_pressure",
        location_context_id="capital_chart",
        chart_resolution={
            "primary_chart": {
                "kind": "lunation",
                "house_rulers": {"6": "Moon", "8": "Saturn", "12": "Mercury"},
                "angles": {"ascendant": 0.0, "midheaven": 90.0},
                "planets": {
                    "Moon": {"house": 8, "retrograde": False, "longitude": 181.0},
                    "Saturn": {"house": 6, "retrograde": False, "longitude": 88.0},
                    "Mercury": {"house": 12, "retrograde": False, "longitude": 2.0},
                    "Venus": {"house": 7, "retrograde": True, "longitude": 120.0},
                    "Uranus": {"house": 12, "retrograde": False, "longitude": 350.0},
                    "Jupiter": {"house": 12, "retrograde": False, "longitude": 5.0},
                },
            },
            "cycle_context": {
                "type": "jupiter_saturn_cycle",
                "nearest_conjunction_datetime": "2020-12-21T18:00:00+00:00",
                "nearest_distance_years": 2.8,
                "cycle_phase": "opening_cycle",
                "turning_window_active": True,
                "turning_window_level": "strong",
                "conjunction_sign": "Aquarius",
            },
            "signals": {
                "activation_hits": [{"planet": "Saturn", "target_point": "Moon", "orb_deg": 1.0}],
            },
        },
    )

    assessment = evaluate_domain_context(context)

    assert assessment["domain_id"] == "epidemic_wave_pressure"
    labels = {row["label"] for row in assessment["matched_rules"]}
    assert "Sixth-house ruler in a wave house" in labels
    assert "Venus retrograde" in labels
    assert "Uranus in a health-disruption house" in labels
    assert "Saturn-Uranus epidemic axis" in labels
    assert "Lunation wave trigger" in labels
    assert "Activation hits present" in labels
    assert "Mutation-cycle epidemic backdrop" in labels
    assert assessment["raw_score"] >= 35


def test_evaluate_epidemic_wave_pressure_tracks_mars_in_sixth_and_neptune_in_twelfth():
    context = _context(
        domain_id="epidemic_wave_pressure",
        chart_resolution={
            "primary_chart": {
                "kind": "aries_ingress",
                "house_rulers": {"6": "Mars", "8": "Moon", "12": "Neptune"},
                "angles": {"ascendant": 0.0, "midheaven": 90.0},
                "planets": {
                    "Mars": {"house": 6, "retrograde": False, "longitude": 182.0},
                    "Neptune": {"house": 12, "retrograde": False, "longitude": 350.0},
                    "Moon": {"house": 8, "retrograde": False, "longitude": 188.0},
                },
            },
            "signals": {},
        },
    )

    assessment = evaluate_domain_context(context)

    labels = {row["label"] for row in assessment["matched_rules"]}
    assert "Mars in the sixth" in labels
    assert "Neptune in the twelfth" in labels


def test_evaluate_civil_unrest_tracks_unrest_specific_signals():
    context = _context(
        domain_id="civil_unrest",
        chart_resolution={
            "primary_chart": {
                "kind": "aries_ingress",
                "house_rulers": {"11": "Mercury"},
                "angles": {"ascendant": 0.0, "midheaven": 90.0},
                "planets": {
                    "Mars": {"house": 1, "retrograde": True, "longitude": 10.0},
                    "Saturn": {"house": 10, "retrograde": False, "longitude": 270.0},
                    "Uranus": {"house": 7, "retrograde": False, "longitude": 183.0},
                    "Mercury": {"house": 11, "retrograde": True, "longitude": 121.0},
                },
            },
            "signals": {
                "activation_hits": [{"planet": "Saturn", "target_point": "Moon", "orb_deg": 1.1}],
            },
        },
    )

    assessment = evaluate_domain_context(context)

    assert assessment["domain_id"] == "civil_unrest"
    assert assessment["raw_score"] > assessment["score"] >= 40
    labels = {row["label"] for row in assessment["matched_rules"]}
    assert "Mars angular" in labels
    assert "Uranus angular" in labels
    assert assessment["calibration"]["unique_case_count"] >= 1


def test_evaluate_civil_unrest_tracks_people_government_and_parliament_axis():
    context = _context(
        domain_id="civil_unrest",
        chart_resolution={
            "primary_chart": {
                "kind": "aries_ingress",
                "house_rulers": {"4": "Moon", "10": "Saturn", "11": "Mercury"},
                "angles": {"ascendant": 0.0, "midheaven": 90.0},
                "planets": {
                    "Moon": {"house": 4, "retrograde": False, "longitude": 188.0},
                    "Mars": {"house": 1, "retrograde": False, "longitude": 8.0},
                    "Saturn": {"house": 11, "retrograde": False, "longitude": 302.0},
                    "Neptune": {"house": 10, "retrograde": False, "longitude": 91.2},
                    "Mercury": {"house": 11, "retrograde": True, "longitude": 320.0},
                },
            },
            "signals": {},
        },
    )

    assessment = evaluate_domain_context(context)

    labels = {row["label"] for row in assessment["matched_rules"]}
    assert "Moon in the fourth under pressure" in labels
    assert "Saturn in the eleventh" in labels
    assert "Neptune in the tenth" in labels
    assert "People-versus-government axis" in labels
    assert assessment["raw_score"] >= 35


def test_evaluate_civil_unrest_tracks_labor_and_union_pressure_in_the_sixth():
    context = _context(
        domain_id="civil_unrest",
        chart_resolution={
            "primary_chart": {
                "kind": "aries_ingress",
                "house_rulers": {"6": "Mercury", "11": "Saturn"},
                "angles": {"ascendant": 0.0, "midheaven": 90.0},
                "planets": {
                    "Mars": {"house": 6, "retrograde": False, "longitude": 182.0},
                    "Uranus": {"house": 6, "retrograde": False, "longitude": 188.0},
                    "Saturn": {"house": 11, "retrograde": False, "longitude": 301.0},
                },
            },
            "signals": {},
        },
    )

    assessment = evaluate_domain_context(context)

    labels = {row["label"] for row in assessment["matched_rules"]}
    assert "Mars in the 6th" in labels
    assert "Uranus in the 6th" in labels


def test_evaluate_civil_unrest_uses_mutation_cycle_backdrop_when_present():
    context = _context(
        domain_id="civil_unrest",
        chart_resolution={
            "primary_chart": {
                "kind": "aries_ingress",
                "house_rulers": {"4": "Moon", "10": "Saturn", "11": "Mercury"},
                "angles": {"ascendant": 0.0, "midheaven": 90.0},
                "planets": {
                    "Moon": {"house": 4, "retrograde": False, "longitude": 188.0},
                    "Mars": {"house": 1, "retrograde": False, "longitude": 8.0},
                    "Saturn": {"house": 11, "retrograde": False, "longitude": 302.0},
                    "Mercury": {"house": 11, "retrograde": True, "longitude": 320.0},
                },
            },
            "cycle_context": {
                "type": "jupiter_saturn_cycle",
                "nearest_conjunction_datetime": "2020-12-21T18:00:00+00:00",
                "nearest_distance_years": 2.8,
                "cycle_phase": "opening_cycle",
                "turning_window_active": True,
                "turning_window_level": "strong",
                "conjunction_sign": "Aquarius",
            },
            "signals": {},
        },
    )

    assessment = evaluate_domain_context(context)

    labels = {row["label"] for row in assessment["matched_rules"]}
    assert "Mutation-cycle unrest backdrop" in labels
    assert any("Long-cycle unrest testimony" in caution for caution in assessment["cautions"])


def test_evaluate_finance_economy_tracks_treasury_strain_and_relief():
    context = _context(
        domain_id="finance_economy",
        chart_resolution={
            "primary_chart": {
                "kind": "national_chart",
                "house_rulers": {"2": "Mercury"},
                "planets": {
                    "Mercury": {"house": 8, "retrograde": True, "longitude": 210.0},
                    "Saturn": {"house": 2, "retrograde": False, "longitude": 15.0},
                    "Venus": {"house": 10, "retrograde": False, "longitude": 44.0},
                },
            },
            "signals": {
                "activation_hits": [{"planet": "Mars", "target_point": "MC", "orb_deg": 0.9}],
            },
        },
    )

    assessment = evaluate_domain_context(context)

    assert assessment["domain_id"] == "finance_economy"
    assert assessment["raw_score"] >= 30
    assert assessment["score"] <= assessment["raw_score"]
    labels = {row["label"] for row in assessment["matched_rules"]}
    assert "Second-house ruler retrograde" in labels
    assert "Saturn in the second" in labels


def test_evaluate_finance_economy_uses_mutation_cycle_backdrop_when_present():
    context = _context(
        domain_id="finance_economy",
        chart_resolution={
            "primary_chart": {
                "kind": "aries_ingress",
                "house_rulers": {"2": "Mercury", "8": "Mars", "10": "Saturn", "11": "Jupiter"},
                "angles": {"ascendant": 0.0, "midheaven": 90.0},
                "planets": {
                    "Mercury": {"house": 8, "retrograde": True, "longitude": 205.0},
                    "Mars": {"house": 2, "retrograde": False, "longitude": 35.0},
                    "Saturn": {"house": 10, "retrograde": True, "longitude": 94.0},
                    "Jupiter": {"house": 11, "retrograde": False, "longitude": 311.0},
                },
            },
            "cycle_context": {
                "type": "jupiter_saturn_cycle",
                "nearest_conjunction_datetime": "2020-12-21T18:00:00+00:00",
                "nearest_distance_years": 2.8,
                "cycle_phase": "opening_cycle",
                "turning_window_active": True,
                "turning_window_level": "strong",
                "conjunction_sign": "Aquarius",
            },
            "signals": {},
        },
    )

    assessment = evaluate_domain_context(context)

    labels = {row["label"] for row in assessment["matched_rules"]}
    assert "Mutation-cycle financial backdrop" in labels
    assert any("Long-cycle finance testimony" in caution for caution in assessment["cautions"])


def test_evaluate_finance_economy_tracks_debt_and_budget_blockage():
    context = _context(
        domain_id="finance_economy",
        chart_resolution={
            "primary_chart": {
                "kind": "aries_ingress",
                "house_rulers": {"2": "Mercury", "8": "Mars", "10": "Saturn", "11": "Jupiter"},
                "angles": {"ascendant": 0.0, "midheaven": 90.0},
                "planets": {
                    "Mercury": {"house": 8, "retrograde": True, "longitude": 205.0},
                    "Mars": {"house": 2, "retrograde": False, "longitude": 35.0},
                    "Saturn": {"house": 10, "retrograde": True, "longitude": 94.0},
                    "Jupiter": {"house": 11, "retrograde": False, "longitude": 311.0},
                },
            },
            "signals": {},
        },
    )

    assessment = evaluate_domain_context(context)

    labels = {row["label"] for row in assessment["matched_rules"]}
    assert "Second-house ruler in the eighth" in labels
    assert "Eighth-house ruler in the second" in labels
    assert "Treasury-debt loop" in labels
    assert "Tenth-house ruler retrograde" in labels
    assert assessment["summary"].startswith("Finance and economy are evaluated from treasury condition, credit and debt pressure")
