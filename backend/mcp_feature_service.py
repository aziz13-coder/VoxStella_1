"""Explicit-input adapters for licensed AstroClock MCP feature tools.

The adapters in this module are deliberately request- and storage-independent.
They never read saved charts or license state; Electron and Flask enforce the
license boundary before these functions are reached.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping

from mcp_chart_service import MCP_SCHEMA_VERSION, McpInputError, build_chart_bundle


SYNASTRY_INPUT_FIELDS = frozenset({
    "chart_a",
    "chart_b",
    "engine_id",
    "profile_a",
    "profile_b",
    "include_modern",
    "include_nodes",
    "include_chiron",
    "orb_profile",
})
SYNASTRY_ENGINES = frozenset({"memo", "life_themes", "union_dynamics", "work_alliance"})
SYNASTRY_PROFILES = frozenset({"blended", "feminine", "masculine"})
SYNASTRY_ORB_PROFILES = frozenset({"tight", "balanced", "wide"})


def _known_fields(payload: Mapping[str, Any], allowed: frozenset[str]) -> None:
    unknown = sorted(str(key) for key in payload if key not in allowed)
    if unknown:
        raise McpInputError("unsupported request fields: " + ", ".join(unknown))


def _enum(payload: Mapping[str, Any], field: str, allowed: frozenset[str], default: str) -> str:
    value = str(payload.get(field) or default).strip().lower()
    if value not in allowed:
        raise McpInputError(f"{field} must be one of " + ", ".join(sorted(allowed)))
    return value


def _explicit_chart(payload: Mapping[str, Any], field: str, *, include_modern: bool, include_chiron: bool):
    chart = payload.get(field)
    if not isinstance(chart, Mapping):
        raise McpInputError(f"{field} must be an explicit chart input object")
    label = str(chart.get("label") or ("Chart A" if field == "chart_a" else "Chart B")).strip()
    if not label or len(label) > 200:
        raise McpInputError(f"{field}.label must contain 1 to 200 characters")
    chart_payload = {key: value for key, value in chart.items() if key != "label"}
    chart_payload["include_modern"] = include_modern
    chart_payload["include_chiron"] = include_chiron
    bundle, context = build_chart_bundle(chart_payload)
    meta = bundle.get("meta") if isinstance(bundle.get("meta"), Mapping) else {}
    chart_meta = {
        "id": None,
        "label": label,
        "effective_datetime": meta.get("timestamp") or context["calculation_time"].isoformat(),
        "location": meta.get("location") or context["location"],
        "timezone": meta.get("timezone") or context["timezone_name"],
        "coordinate_provenance": {
            "source": "explicit_mcp_input",
            "persisted_with_chart": False,
            "inferred_at_read_time": False,
            "review_required": False,
        },
        "calculation_context": {"review_required": False},
        "context_warnings": [],
    }
    return bundle, chart_meta


def calculate_synastry(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Calculate full synastry without reading or creating saved charts."""

    if not isinstance(payload, Mapping):
        raise McpInputError("request body must be a JSON object")
    _known_fields(payload, SYNASTRY_INPUT_FIELDS)
    engine_id = _enum(payload, "engine_id", SYNASTRY_ENGINES, "memo")
    profile_a = _enum(payload, "profile_a", SYNASTRY_PROFILES, "blended")
    profile_b = _enum(payload, "profile_b", SYNASTRY_PROFILES, "blended")
    orb_profile = _enum(payload, "orb_profile", SYNASTRY_ORB_PROFILES, "balanced")
    include_modern = payload.get("include_modern", True) is not False
    include_nodes = payload.get("include_nodes", True) is not False
    include_chiron = payload.get("include_chiron", False) is True

    bundle_a, chart_a = _explicit_chart(
        payload,
        "chart_a",
        include_modern=include_modern,
        include_chiron=include_chiron,
    )
    bundle_b, chart_b = _explicit_chart(
        payload,
        "chart_b",
        include_modern=include_modern,
        include_chiron=include_chiron,
    )

    # Import lazily to avoid pulling the large AstroClock graph into MCP
    # capability discovery and to keep application blueprint startup acyclic.
    from astro_clock_api import _extend_chart_data_for_synastry, _synastry_point_capability
    from synastry_multi_engine import build_synastry_engine_report

    capability_a = _synastry_point_capability(bundle_a.get("meta") or {})
    capability_b = _synastry_point_capability(bundle_b.get("meta") or {})
    bundle_a["chart_data"] = _extend_chart_data_for_synastry(
        bundle_a.get("chart_data") or {},
        bundle_a.get("meta") or {},
        include_modern=bool(include_modern and capability_a.get("modern_supported")),
        include_chiron=bool(include_chiron and capability_a.get("chiron_supported")),
    )
    bundle_b["chart_data"] = _extend_chart_data_for_synastry(
        bundle_b.get("chart_data") or {},
        bundle_b.get("meta") or {},
        include_modern=bool(include_modern and capability_b.get("modern_supported")),
        include_chiron=bool(include_chiron and capability_b.get("chiron_supported")),
    )
    report = build_synastry_engine_report(
        bundle_a,
        bundle_b,
        chart_a,
        chart_b,
        options={
            "include_modern": include_modern,
            "include_nodes": include_nodes,
            "include_chiron": include_chiron,
            "orb_profile": orb_profile,
        },
        engine_id=engine_id,
        profile_a=profile_a,
        profile_b=profile_b,
    )
    report["schema_version"] = MCP_SCHEMA_VERSION
    report.setdefault("governance", {})["mcp_context"] = {
        "input_mode": "explicit",
        "saved_chart_access": False,
        "point_capability": {
            "modern_supported": bool(
                capability_a.get("modern_supported") and capability_b.get("modern_supported")
            ),
            "chiron_supported": bool(
                capability_a.get("chiron_supported") and capability_b.get("chiron_supported")
            ),
        },
    }
    return report


__all__ = ["calculate_synastry"]
