"""Classical dispositor chain utilities for AstroClock.

The contract is deliberately narrow: traditional domicile rulers determine
the chain, and a final dispositor exists only when the chain terminates in a
planet occupying its own domicile. Mutual receptions and longer rulership
cycles are terminal states, but they do not have a single final dispositor.
"""

from types import SimpleNamespace
from typing import Any, Dict, List, Optional


TRADITIONAL_SIGN_RULERS: Dict[str, str] = {
    "Aries": "Mars",
    "Taurus": "Venus",
    "Gemini": "Mercury",
    "Cancer": "Moon",
    "Leo": "Sun",
    "Virgo": "Mercury",
    "Libra": "Venus",
    "Scorpio": "Mars",
    "Sagittarius": "Jupiter",
    "Capricorn": "Saturn",
    "Aquarius": "Saturn",
    "Pisces": "Jupiter",
}


FINAL_TERMINAL_TYPES = {"domicile", "final_dispositor"}


def _chain_payload(
    *,
    planet: str,
    dispositor: Optional[str],
    chain: List[str],
    final_dispositor: Optional[str],
    terminal_type: str,
    mutual_reception: bool = False,
    reception_partner: Optional[str] = None,
    cycle: Optional[List[str]] = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        planet=planet,
        dispositor=dispositor,
        chain=chain,
        final_dispositor=final_dispositor,
        mutual_reception=bool(mutual_reception),
        reception_partner=reception_partner,
        terminal_type=terminal_type,
        has_final_dispositor=bool(final_dispositor and terminal_type in FINAL_TERMINAL_TYPES),
        cycle=list(cycle or []),
    )


def build_dispositor_chain_from_data(
    planet_name: str,
    planet_sign: str,
    sign_rulers: Optional[Dict[str, str]] = None,
    planet_signs: Optional[Dict[str, str]] = None,
) -> SimpleNamespace:
    """Build one dispositor chain from normalized planet/sign dictionaries."""
    rulers = sign_rulers or TRADITIONAL_SIGN_RULERS
    placements = planet_signs or {}
    planet = str(planet_name)
    sign = str(planet_sign)
    direct_dispositor = rulers.get(sign)
    chain: List[str] = [planet]

    if not direct_dispositor:
        return _chain_payload(
            planet=planet,
            dispositor=None,
            chain=chain,
            final_dispositor=None,
            terminal_type="unknown",
        )

    visited = {planet: 0}
    current_sign = sign
    max_hops = max(2, len(placements) + 2)

    for _ in range(max_hops):
        ruler = rulers.get(current_sign)
        if not ruler:
            return _chain_payload(
                planet=planet,
                dispositor=direct_dispositor,
                chain=chain,
                final_dispositor=None,
                terminal_type="unknown",
            )

        if ruler in visited:
            cycle = chain[visited[ruler]:]
            if len(cycle) == 1:
                return _chain_payload(
                    planet=planet,
                    dispositor=direct_dispositor,
                    chain=chain,
                    final_dispositor=ruler,
                    terminal_type="domicile",
                )
            if len(cycle) == 2:
                reception_partner = None
                if planet in cycle:
                    reception_partner = cycle[1] if cycle[0] == planet else cycle[0]
                return _chain_payload(
                    planet=planet,
                    dispositor=direct_dispositor,
                    chain=chain,
                    final_dispositor=None,
                    terminal_type="mutual_reception",
                    mutual_reception=True,
                    reception_partner=reception_partner,
                    cycle=cycle,
                )
            return _chain_payload(
                planet=planet,
                dispositor=direct_dispositor,
                chain=chain,
                final_dispositor=None,
                terminal_type="cycle",
                cycle=cycle,
            )

        chain.append(ruler)
        visited[ruler] = len(chain) - 1
        ruler_sign = placements.get(ruler)
        if not ruler_sign:
            return _chain_payload(
                planet=planet,
                dispositor=direct_dispositor,
                chain=chain,
                final_dispositor=None,
                terminal_type="unknown",
            )
        current_sign = str(ruler_sign)

    return _chain_payload(
        planet=planet,
        dispositor=direct_dispositor,
        chain=chain,
        final_dispositor=None,
        terminal_type="cycle",
        cycle=chain,
    )


def calculate_dispositor_chains(planet_positions: List[Dict[str, Any]]) -> Dict[str, SimpleNamespace]:
    """Calculate traditional dispositor chains for all non-angle planet rows."""
    planet_signs: Dict[str, str] = {}
    for planet_data in planet_positions or []:
        if not isinstance(planet_data, dict):
            continue
        planet_name = planet_data.get("planet")
        planet_sign = planet_data.get("sign")
        if planet_name and planet_sign and planet_name not in {"Ascendant", "Midheaven"}:
            planet_signs[str(planet_name)] = str(planet_sign)

    return {
        planet_name: build_dispositor_chain_from_data(
            planet_name,
            planet_sign,
            TRADITIONAL_SIGN_RULERS,
            planet_signs,
        )
        for planet_name, planet_sign in planet_signs.items()
        if planet_sign in TRADITIONAL_SIGN_RULERS
    }


def compute_final_dispositors(planet_signs: Dict[str, str]) -> Dict[str, str]:
    """Return only genuine final dispositors.

    Mutual receptions and longer cycles intentionally produce no entry because
    they do not terminate in one planet's domicile.
    """
    result: Dict[str, str] = {}
    placements = {str(k): str(v) for k, v in (planet_signs or {}).items() if k and v}
    for planet, sign in placements.items():
        chain = build_dispositor_chain_from_data(
            planet,
            sign,
            TRADITIONAL_SIGN_RULERS,
            placements,
        )
        if chain.has_final_dispositor:
            result[planet] = chain.final_dispositor
    return result
