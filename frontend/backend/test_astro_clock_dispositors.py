from astro_clock_api import _build_dispositors_payload, _compute_final_dispositors
from astro_clock_engine import AstroClockEngine
from astro_dispositors import calculate_dispositor_chains


def _rows(placements):
    return [
        {"planet": planet, "sign": sign}
        for planet, sign in placements.items()
    ]


def test_mutual_reception_has_no_single_final_dispositor():
    placements = {"Mars": "Taurus", "Venus": "Aries"}

    chains = calculate_dispositor_chains(_rows(placements))

    assert chains["Mars"].chain == ["Mars", "Venus"]
    assert chains["Mars"].terminal_type == "mutual_reception"
    assert chains["Mars"].mutual_reception is True
    assert chains["Mars"].reception_partner == "Venus"
    assert chains["Mars"].final_dispositor is None
    assert chains["Mars"].has_final_dispositor is False
    assert _compute_final_dispositors(placements) == {}


def test_domicile_terminates_as_genuine_final_dispositor():
    placements = {"Moon": "Pisces", "Jupiter": "Sagittarius"}

    chains = calculate_dispositor_chains(_rows(placements))

    assert chains["Moon"].chain == ["Moon", "Jupiter"]
    assert chains["Moon"].terminal_type == "domicile"
    assert chains["Moon"].final_dispositor == "Jupiter"
    assert chains["Moon"].has_final_dispositor is True
    assert _compute_final_dispositors(placements) == {
        "Moon": "Jupiter",
        "Jupiter": "Jupiter",
    }


def test_long_dispositor_cycle_is_not_reported_as_final():
    placements = {"Sun": "Aries", "Mars": "Gemini", "Mercury": "Leo"}

    chains = calculate_dispositor_chains(_rows(placements))

    assert chains["Sun"].chain == ["Sun", "Mars", "Mercury"]
    assert chains["Sun"].terminal_type == "cycle"
    assert chains["Sun"].cycle == ["Sun", "Mars", "Mercury"]
    assert chains["Sun"].final_dispositor is None
    assert chains["Sun"].has_final_dispositor is False
    assert _compute_final_dispositors(placements) == {}


def test_chain_can_terminate_in_mutual_reception_pair_after_anchor():
    placements = {"Moon": "Taurus", "Venus": "Aries", "Mars": "Libra"}

    chains = calculate_dispositor_chains(_rows(placements))

    assert chains["Moon"].chain == ["Moon", "Venus", "Mars"]
    assert chains["Moon"].terminal_type == "mutual_reception"
    assert chains["Moon"].mutual_reception is True
    assert chains["Moon"].reception_partner is None
    assert chains["Moon"].cycle == ["Venus", "Mars"]
    assert chains["Moon"].final_dispositor is None
    assert _compute_final_dispositors(placements) == {}


def test_engine_uses_shared_dispositor_logic():
    engine = AstroClockEngine.__new__(AstroClockEngine)
    chains = engine._calculate_dispositor_chains(_rows({"Mars": "Taurus", "Venus": "Aries"}))

    assert chains["Mars"].terminal_type == "mutual_reception"
    assert chains["Mars"].final_dispositor is None


def test_dashboard_dispositor_payload_uses_final_chart_planet_rows():
    payload = _build_dispositors_payload(
        {"dispositor_chains": {"Uranus": {"chain": ["stale"], "final_dispositor": "stale"}}},
        {"planets": _rows({"Uranus": "Taurus", "Venus": "Libra"})},
    )

    assert payload["Uranus"]["dispositor"] == "Venus"
    assert payload["Uranus"]["chain"] == ["Uranus", "Venus"]
    assert payload["Uranus"]["final_dispositor"] == "Venus"
    assert payload["Uranus"]["has_final_dispositor"] is True
