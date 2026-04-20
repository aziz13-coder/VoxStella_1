from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict


_TRANSITS_CONTEXT_MATURITY: Dict[str, Dict[str, Any]] = {
    "primary_directions": {
        "level": "partial",
        "surface_scope": "window_concordance_and_auto_context",
        "summary": "Primary directions are computed as time windows and used in concordance, but the runtime does not expose a full directions workspace or complete directional chart layer.",
        "available_outputs": [
            "pd_windows",
            "pd_selected",
            "status.pd",
            "transit concordance enrichment",
        ],
        "gaps": [
            "No first-class directions surface",
            "Window-based support only",
        ],
    },
    "solar_arc": {
        "level": "partial",
        "surface_scope": "auto_context_windowing",
        "summary": "Solar arc is available as suggested windows and selection support, but not as a fully modeled standalone runtime layer.",
        "available_outputs": [
            "sa_windows",
            "sa_selected",
            "status.sa",
        ],
        "gaps": [
            "No dedicated solar-arc interpretive layer",
        ],
    },
    "secondary_progressions": {
        "level": "partial",
        "surface_scope": "auto_context_windowing",
        "summary": "Progressed Moon and progressed-planet windows are available for timing support, but progression logic is not surfaced as a full chart-analysis layer.",
        "available_outputs": [
            "progression_windows",
            "progression_windows_outer",
            "prog_window",
            "status.prog",
        ],
        "gaps": [
            "No full progression chart surface",
            "Window helpers dominate current exposure",
        ],
    },
    "solar_return": {
        "level": "partial",
        "surface_scope": "analysis_concordance_helpers",
        "summary": "Solar-return markers and similarity helpers inform transit concordance, but solar return is not exposed through the auto-context contract as a first-class selectable layer.",
        "available_outputs": [
            "revolutions context in transit analysis",
            "solar-return helper calculations",
        ],
        "gaps": [
            "Not surfaced in /context/auto",
            "No explicit maturity metadata in runtime before this inventory",
        ],
    },
    "lunar_return": {
        "level": "helper_only",
        "surface_scope": "timing_helpers",
        "summary": "Lunar return utilities exist for timing support and helper calculations, but lunar return is not currently a first-class transits context layer.",
        "available_outputs": [
            "helper timestamps",
            "support calculations inside context helpers",
        ],
        "gaps": [
            "No first-class runtime exposure",
            "No dedicated API surface",
        ],
    },
    "focus_suggestions": {
        "level": "helper_only",
        "surface_scope": "auto_context_assistance",
        "summary": "Focus houses and focus planets are heuristic suggestions derived from natal structure. They are assistant hints, not an independent context layer.",
        "available_outputs": [
            "focus_houses",
            "focus_planets",
        ],
        "gaps": [
            "Heuristic only",
            "No independent chart or window model",
        ],
    },
}


def get_transits_context_maturity() -> Dict[str, Dict[str, Any]]:
    return deepcopy(_TRANSITS_CONTEXT_MATURITY)
