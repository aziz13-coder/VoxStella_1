from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Dict, Iterable, Mapping, Optional

from mundane_assets import (
    get_activation_watchpoints,
    get_chart_type_definitions,
    get_context_type_definitions,
    get_domain_definitions,
    get_polity_definitions,
    get_reference_notes,
    get_source_index,
    get_trigger_family_definitions,
)
from mundane_domain_rules import evaluate_domain_context
from mundane_models import (
    ActiveClockContext,
    MundaneAnalysis,
    MundaneContextRequest,
    MundaneLayer,
    ResolvedMundaneContext,
)
from mundane_chart_rules import resolve_chart_resolution
from mundane_trigger_rules import compute_trigger_profiles


def _normalize_id(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_")


def _coerce_optional_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except Exception as exc:
        raise ValueError(f"Invalid numeric value: {value}") from exc


def _coerce_optional_text(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    return text or None


def _index_by_id(rows: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    indexed: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        row_id = _normalize_id(row.get("id"))
        if row_id:
            indexed[row_id] = dict(row)
    return indexed


def _index_polities(rows: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    indexed = _index_by_id(rows)
    for row in rows:
        row_id = _normalize_id(row.get("id"))
        if not row_id:
            continue
        payload = indexed.get(row_id) or dict(row)
        aliases = row.get("aliases") or []
        if not isinstance(aliases, list):
            continue
        for alias in aliases:
            normalized = _normalize_id(alias)
            if normalized and normalized not in indexed:
                indexed[normalized] = payload
    return indexed


def _source_payload(tags: Iterable[str]) -> list[Dict[str, Any]]:
    source_index = get_source_index()
    resolved: list[Dict[str, Any]] = []
    seen: set[str] = set()
    for tag in tags:
        normalized = _normalize_id(tag)
        if not normalized or normalized in seen:
            continue
        source_info = source_index.get(normalized)
        if isinstance(source_info, dict):
            resolved.append({"id": normalized, **source_info})
            seen.add(normalized)
    return resolved


def _note_payload(note_ids: Iterable[str]) -> list[Dict[str, Any]]:
    doctrine_notes = get_reference_notes()
    note_index = doctrine_notes.get("note_index") or {}
    if not isinstance(note_index, dict):
        return []
    notes: list[Dict[str, Any]] = []
    seen: set[str] = set()
    for note_id in note_ids:
        normalized = _normalize_id(note_id)
        if not normalized or normalized in seen:
            continue
        note = note_index.get(normalized)
        if isinstance(note, dict):
            notes.append({"id": normalized, **note})
            seen.add(normalized)
    return notes


def _parse_iso_date(value: Any) -> Optional[date]:
    text = str(value or "").strip()
    if not text:
        return None
    candidate = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        try:
            parsed = datetime.fromisoformat(candidate[:10])
        except ValueError:
            return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed.date()


def _chart_status_rank(chart: Dict[str, Any]) -> int:
    status = _normalize_id(chart.get("status"))
    ranking = {
        "preferred": 0,
        "preferred_by_source": 0,
        "listed_candidate": 1,
        "listed": 1,
        "candidate": 2,
        "alternate": 3,
        "contested": 4,
    }
    return ranking.get(status, 5)


def _chart_matches_anchor(chart: Dict[str, Any], anchor_date: date) -> bool:
    start_date = _parse_iso_date(chart.get("valid_from") or chart.get("datetime"))
    end_date = _parse_iso_date(chart.get("valid_to"))
    if start_date and anchor_date < start_date:
        return False
    if end_date and anchor_date > end_date:
        return False
    return True


def _pick_polity_chart(
    polity: Dict[str, Any],
    national_chart_id: Optional[str],
    *,
    anchor_datetime: Optional[str] = None,
    allow_period_fallback: bool = False,
) -> Optional[Dict[str, Any]]:
    charts = polity.get("national_charts") or []
    if not isinstance(charts, list):
        return None
    requested_id = _normalize_id(national_chart_id)
    if requested_id:
        for chart in charts:
            if _normalize_id(chart.get("id")) == requested_id:
                payload = dict(chart)
                payload["selection_basis"] = "requested_chart_id"
                return payload
    anchor_date = _parse_iso_date(anchor_datetime)
    if anchor_date is not None:
        matching = [dict(chart) for chart in charts if _chart_matches_anchor(chart, anchor_date)]
        if matching:
            matching.sort(key=lambda row: (_chart_status_rank(row), _normalize_id(row.get("label"))))
            payload = matching[0]
            payload["selection_basis"] = "period_match"
            return payload
        if not allow_period_fallback:
            return None
    for chart in charts:
        if str(chart.get("status") or "").strip().lower() == "preferred":
            payload = dict(chart)
            payload["selection_basis"] = "preferred_default"
            return payload
    if charts:
        payload = dict(charts[0])
        payload["selection_basis"] = "first_available"
        return payload
    return None


def _custom_reference_chart(request_model: MundaneContextRequest) -> Optional[Dict[str, Any]]:
    custom_datetime = _coerce_optional_text(request_model.custom_chart_datetime)
    custom_location = _coerce_optional_text(request_model.custom_chart_location)
    custom_timezone = _coerce_optional_text(request_model.custom_chart_timezone)
    if not (custom_datetime and custom_location and custom_timezone):
        return None
    custom_label = _coerce_optional_text(request_model.custom_chart_label) or "Custom National Chart"
    return {
        "id": "custom_user_chart",
        "label": custom_label,
        "datetime": custom_datetime,
        "location": custom_location,
        "timezone": custom_timezone,
        "status": "user_supplied",
        "source_tags": [],
        "research_flags": ["user_supplied_chart", "unverified_chart_provenance", "not_registry_backed"],
    }


def _custom_polity(request_model: MundaneContextRequest, active_clock: ActiveClockContext) -> Optional[Dict[str, Any]]:
    label = _coerce_optional_text(request_model.custom_polity_label)
    if not label:
        return None
    default_location = (
        _coerce_optional_text(request_model.reference_location)
        or _coerce_optional_text(request_model.event_location)
        or _coerce_optional_text(active_clock.location)
    )
    timezone_name = _coerce_optional_text(request_model.event_timezone) or _coerce_optional_text(active_clock.timezone)
    return {
        "id": f"custom:{_normalize_id(label) or 'polity'}",
        "label": label,
        "capital": default_location,
        "default_location": default_location,
        "timezone": timezone_name,
        "visibility_scope": request_model.visibility_scope or "national",
        "source_tags": [],
        "research_flags": ["user_supplied_polity", "not_registry_backed"],
        "national_charts": [],
    }


def _default_location_context(chart_type: Dict[str, Any], requested_context: Optional[str]) -> str:
    normalized = _normalize_id(requested_context)
    if normalized:
        return normalized
    return _normalize_id(chart_type.get("default_location_context_type"))


def _resolve_reference_chart(
    request_model: MundaneContextRequest,
    chart_type: Dict[str, Any],
    polity: Optional[Dict[str, Any]],
    *,
    anchor_datetime: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    custom_chart = _custom_reference_chart(request_model)
    if custom_chart is not None:
        return custom_chart
    if _normalize_id(chart_type.get("id")) == "national_chart":
        if polity is None:
            raise ValueError("polity_id or custom_polity_label is required for national_chart analysis")
        chart = _pick_polity_chart(
            polity,
            request_model.national_chart_id,
            anchor_datetime=anchor_datetime,
            allow_period_fallback=False,
        )
        if chart is None:
            raise ValueError("No national chart period matches the selected polity and event context")
        return chart
    if polity is not None and request_model.national_chart_id:
        chart = _pick_polity_chart(
            polity,
            request_model.national_chart_id,
            anchor_datetime=anchor_datetime,
            allow_period_fallback=True,
        )
        if chart is not None:
            return chart
    if polity is not None and str(chart_type.get("requires_polity") or "").lower() == "true":
        chart = _pick_polity_chart(
            polity,
            None,
            anchor_datetime=anchor_datetime,
            allow_period_fallback=False,
        )
        if chart is not None:
            return chart
    return None


def _resolve_event_context(
    request_model: MundaneContextRequest,
    active_clock: ActiveClockContext,
    chart_type: Dict[str, Any],
    polity: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    location_context_type = _default_location_context(chart_type, request_model.location_context_type)
    reference_location = request_model.reference_location
    if not reference_location and polity is not None:
        reference_location = str(polity.get("capital") or polity.get("default_location") or "").strip() or None
    if not reference_location:
        reference_location = active_clock.location

    event_datetime = request_model.event_datetime or active_clock.timestamp
    event_location = request_model.event_location or active_clock.location or reference_location
    event_timezone = request_model.event_timezone or active_clock.timezone

    return {
        "location_context_type": location_context_type,
        "reference_location": reference_location,
        "reference_latitude": request_model.reference_latitude,
        "reference_longitude": request_model.reference_longitude,
        "event_datetime": event_datetime,
        "event_location": event_location,
        "event_timezone": event_timezone,
        "visibility_scope": request_model.visibility_scope or (polity.get("visibility_scope") if polity else None) or "national"
    }


_CHART_TYPE_DOMAIN_PROFILE_SEED: Dict[str, Dict[str, Any]] = {
    "war_event": {
        "default_domain_id": "war_outbreak",
        "preferred_domain_ids": [
            "war_outbreak",
            "campaign_escalation",
            "military_reversal",
        ],
        "supported_domain_ids": [
            "war_conflict",
            "diplomacy_foreign_affairs",
            "alliance_stress",
            "leadership_transition",
            "regime_stability",
            "civil_unrest",
        ],
        "discouraged_domain_ids": [
            "public_health",
            "epidemic_wave_pressure",
            "finance_economy",
            "trade_and_commerce",
        ],
        "domain_scope_summary": "Use event charts for first hostilities, campaign heat, reversals, and immediate foreign-policy fallout.",
    },
    "aries_ingress": {
        "default_domain_id": "regime_stability",
        "preferred_domain_ids": [
            "regime_stability",
            "leadership_transition",
            "civil_unrest",
            "finance_economy",
            "trade_and_commerce",
            "public_health",
            "epidemic_wave_pressure",
            "diplomacy_foreign_affairs",
            "alliance_stress",
            "campaign_escalation",
            "military_reversal",
        ],
        "supported_domain_ids": [
            "government_stability",
            "war_conflict",
        ],
        "discouraged_domain_ids": [
            "war_outbreak",
        ],
        "domain_scope_summary": "Use the ingress for annual public climate, sustained pressure, and institutional burden rather than first-strike localization.",
    },
    "lunation": {
        "default_domain_id": "civil_unrest",
        "preferred_domain_ids": [
            "civil_unrest",
            "public_health",
            "epidemic_wave_pressure",
            "leadership_transition",
            "diplomacy_foreign_affairs",
            "alliance_stress",
            "campaign_escalation",
            "military_reversal",
        ],
        "supported_domain_ids": [
            "regime_stability",
            "finance_economy",
            "trade_and_commerce",
            "war_conflict",
            "government_stability",
        ],
        "discouraged_domain_ids": [
            "war_outbreak",
        ],
        "domain_scope_summary": "Use lunations for short trigger windows inside a larger polity frame, not as standalone outbreak anchors.",
    },
    "eclipse": {
        "default_domain_id": "regime_stability",
        "preferred_domain_ids": [
            "regime_stability",
            "leadership_transition",
            "public_health",
            "epidemic_wave_pressure",
            "civil_unrest",
            "campaign_escalation",
            "military_reversal",
        ],
        "supported_domain_ids": [
            "diplomacy_foreign_affairs",
            "alliance_stress",
            "finance_economy",
            "trade_and_commerce",
            "war_conflict",
            "government_stability",
        ],
        "discouraged_domain_ids": [
            "war_outbreak",
        ],
        "domain_scope_summary": "Use eclipses for intensified activation, escalation, and institutional shocks rather than literal outbreak charts.",
    },
    "national_chart": {
        "default_domain_id": "regime_stability",
        "preferred_domain_ids": [
            "regime_stability",
            "leadership_transition",
            "civil_unrest",
            "finance_economy",
            "trade_and_commerce",
            "public_health",
            "epidemic_wave_pressure",
            "diplomacy_foreign_affairs",
            "alliance_stress",
        ],
        "supported_domain_ids": [
            "campaign_escalation",
            "military_reversal",
            "war_conflict",
            "government_stability",
        ],
        "discouraged_domain_ids": [
            "war_outbreak",
        ],
        "domain_scope_summary": "Use national charts for enduring polity structure and longer-lived strain, with event charts supplying the trigger when needed.",
    },
}


def get_chart_type_domain_profiles(
    domain_rows: Optional[Iterable[Dict[str, Any]]] = None,
) -> Dict[str, Dict[str, Any]]:
    domain_ids = {
        _normalize_id(row.get("id"))
        for row in (domain_rows or get_domain_definitions())
        if _normalize_id(row.get("id"))
    }
    profiles: Dict[str, Dict[str, Any]] = {}
    for chart_type_id, raw_profile in _CHART_TYPE_DOMAIN_PROFILE_SEED.items():
        preferred: list[str] = []
        supported: list[str] = []
        discouraged: list[str] = []

        for domain_id in raw_profile.get("preferred_domain_ids") or []:
            normalized = _normalize_id(domain_id)
            if normalized and normalized in domain_ids and normalized not in preferred:
                preferred.append(normalized)

        for domain_id in raw_profile.get("supported_domain_ids") or []:
            normalized = _normalize_id(domain_id)
            if normalized and normalized in domain_ids and normalized not in preferred and normalized not in supported:
                supported.append(normalized)

        for domain_id in raw_profile.get("discouraged_domain_ids") or []:
            normalized = _normalize_id(domain_id)
            if (
                normalized
                and normalized in domain_ids
                and normalized not in preferred
                and normalized not in supported
                and normalized not in discouraged
            ):
                discouraged.append(normalized)

        default_domain_id = _normalize_id(raw_profile.get("default_domain_id"))
        if default_domain_id not in preferred and default_domain_id not in supported:
            default_domain_id = preferred[0] if preferred else (supported[0] if supported else "")

        profiles[chart_type_id] = {
            "default_domain_id": default_domain_id or None,
            "preferred_domain_ids": preferred,
            "supported_domain_ids": supported,
            "discouraged_domain_ids": discouraged,
            "domain_scope_summary": str(raw_profile.get("domain_scope_summary") or "").strip(),
        }
    return profiles


def get_chart_type_domain_pairing_policy(
    chart_type_id: str,
    domain_id: Optional[str],
    *,
    domain_rows: Optional[Iterable[Dict[str, Any]]] = None,
    chart_rows: Optional[Iterable[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    normalized_chart_type_id = _normalize_id(chart_type_id)
    normalized_domain_id = _normalize_id(domain_id)
    domain_index = _index_by_id(domain_rows or get_domain_definitions())
    chart_index = _index_by_id(chart_rows or get_chart_type_definitions())
    chart_type = chart_index.get(normalized_chart_type_id) or {}
    domain = domain_index.get(normalized_domain_id) or {}
    profiles = get_chart_type_domain_profiles(domain_index.values())
    profile = profiles.get(normalized_chart_type_id) or {}

    preferred_ids = set(profile.get("preferred_domain_ids") or [])
    supported_ids = set(profile.get("supported_domain_ids") or [])
    discouraged_ids = set(profile.get("discouraged_domain_ids") or [])
    explicit_profile = bool(preferred_ids or supported_ids or discouraged_ids)

    status = "unselected"
    allowed = True
    if normalized_domain_id:
        if normalized_domain_id in preferred_ids:
            status = "preferred"
        elif normalized_domain_id in supported_ids:
            status = "supported"
        elif normalized_domain_id in discouraged_ids:
            status = "discouraged"
            allowed = False
        elif explicit_profile:
            status = "unsupported"
            allowed = False
        else:
            status = "unprofiled"

    default_domain_id = _normalize_id(profile.get("default_domain_id")) or None
    domain_label = str(domain.get("label") or normalized_domain_id or "Unselected Domain Lens")
    chart_label = str(chart_type.get("label") or normalized_chart_type_id or "Selected Chart")

    message = ""
    if status in {"discouraged", "unsupported"}:
        if normalized_domain_id == "war_outbreak" and normalized_chart_type_id != "war_event":
            message = (
                f"{domain_label} requires the War Event chart type. "
                f"Use Campaign Escalation or Military Reversal with {chart_label}, or switch chart type."
            )
        else:
            preferred_labels = [
                str((domain_index.get(item) or {}).get("label") or item).strip()
                for item in (profile.get("preferred_domain_ids") or [])
                if (domain_index.get(item) or {}).get("label") or item
            ]
            fallback = ", ".join(preferred_labels[:3])
            if fallback:
                message = f"{domain_label} is not supported with {chart_label}. Use one of: {fallback}."
            else:
                message = f"{domain_label} is not supported with {chart_label}."

    return {
        "chart_type_id": normalized_chart_type_id,
        "domain_id": normalized_domain_id or None,
        "status": status,
        "allowed": allowed,
        "default_domain_id": default_domain_id,
        "preferred_domain_ids": list(profile.get("preferred_domain_ids") or []),
        "supported_domain_ids": list(profile.get("supported_domain_ids") or []),
        "discouraged_domain_ids": list(profile.get("discouraged_domain_ids") or []),
        "message": message,
    }


def enforce_chart_type_domain_pairing(
    chart_type_id: str,
    domain_id: Optional[str],
    *,
    execution_mode: str = "analysis",
    domain_rows: Optional[Iterable[Dict[str, Any]]] = None,
    chart_rows: Optional[Iterable[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    policy = get_chart_type_domain_pairing_policy(
        chart_type_id,
        domain_id,
        domain_rows=domain_rows,
        chart_rows=chart_rows,
    )
    if not policy.get("allowed", True):
        prefix = "Scan pairing invalid" if _normalize_id(execution_mode) == "scan" else "Analysis pairing invalid"
        raise ValueError(f"{prefix}: {policy.get('message')}")
    return policy


def get_runtime_catalog() -> Dict[str, Any]:
    domains = get_domain_definitions()
    chart_type_profiles = get_chart_type_domain_profiles(domains)
    chart_types: list[Dict[str, Any]] = []
    for row in get_chart_type_definitions():
        payload = dict(row)
        payload.update(chart_type_profiles.get(_normalize_id(row.get("id"))) or {})
        chart_types.append(payload)
    return {
        "chart_types": chart_types,
        "domains": domains,
        "context_types": get_context_type_definitions(),
        "polities": get_polity_definitions(),
        "trigger_families": get_trigger_family_definitions(),
        "source_index": get_source_index(),
        "chart_type_domain_profiles": chart_type_profiles,
    }


def build_context_request(args: Mapping[str, Any], *, require_domain: bool = True) -> MundaneContextRequest:
    chart_type = _normalize_id(args.get("chart_type"))
    if not chart_type:
        raise ValueError("chart_type is required")
    domain = _normalize_id(args.get("domain") or args.get("domain_lens"))
    if require_domain and not domain:
        raise ValueError("domain is required")
    return MundaneContextRequest(
        chart_type=chart_type,
        domain=domain or None,
        polity_id=_normalize_id(args.get("polity_id") or args.get("country_id") or args.get("nation_id")) or None,
        custom_polity_label=_coerce_optional_text(args.get("custom_polity_label") or args.get("polity_label")),
        location_context_type=_normalize_id(args.get("location_context_type") or args.get("context_type")) or None,
        reference_location=_coerce_optional_text(args.get("reference_location")),
        reference_latitude=_coerce_optional_float(args.get("reference_latitude")),
        reference_longitude=_coerce_optional_float(args.get("reference_longitude")),
        event_datetime=_coerce_optional_text(args.get("event_datetime")),
        event_location=_coerce_optional_text(args.get("event_location")),
        event_timezone=_coerce_optional_text(args.get("event_timezone")),
        national_chart_id=_normalize_id(args.get("national_chart_id")) or None,
        custom_chart_label=_coerce_optional_text(args.get("custom_chart_label")),
        custom_chart_datetime=_coerce_optional_text(args.get("custom_chart_datetime")),
        custom_chart_location=_coerce_optional_text(args.get("custom_chart_location")),
        custom_chart_timezone=_coerce_optional_text(args.get("custom_chart_timezone")),
        visibility_scope=_normalize_id(args.get("visibility_scope")) or None,
        source_preference=_normalize_id(args.get("source_preference")) or None,
    )


def resolve_context(
    request_model: MundaneContextRequest,
    *,
    active_clock: ActiveClockContext,
    bundle_resolver=None,
) -> ResolvedMundaneContext:
    chart_types = _index_by_id(get_chart_type_definitions())
    domains = _index_by_id(get_domain_definitions())
    context_types = _index_by_id(get_context_type_definitions())
    polities = _index_polities(get_polity_definitions())

    chart_type = chart_types.get(request_model.chart_type)
    if chart_type is None:
        raise ValueError(f"Unsupported chart_type: {request_model.chart_type}")

    domain = None
    if request_model.domain:
        domain = domains.get(request_model.domain)
    if request_model.domain and domain is None:
        raise ValueError(f"Unsupported domain: {request_model.domain}")
    if domain is None:
        domain = {
            "id": None,
            "label": "Unselected Domain Lens",
            "summary": "Chart context is resolved, but no domain lens has been selected yet.",
            "research_status": "context_only",
            "benchmark_status": "not_applicable",
            "framework_note_ids": [],
            "domain_note_ids": [],
            "trigger_note_ids": [],
            "activation_note_ids": [],
            "trigger_summary": "",
            "activation_summary": "",
            "activation_focus": [],
            "source_tags": [],
            "research_flags": [],
        }

    enforce_chart_type_domain_pairing(
        request_model.chart_type,
        (domain or {}).get("id"),
        execution_mode="analysis",
        domain_rows=domains.values(),
        chart_rows=chart_types.values(),
    )

    polity = None
    if request_model.polity_id:
        polity = polities.get(request_model.polity_id)
        if polity is None:
            raise ValueError(f"Unknown polity_id: {request_model.polity_id}")
    if polity is None:
        polity = _custom_polity(request_model, active_clock)
    if polity is None and bool(chart_type.get("requires_polity")):
        raise ValueError(f"polity_id or custom_polity_label is required for chart_type {request_model.chart_type}")

    location_context_type = _default_location_context(chart_type, request_model.location_context_type)
    location_context = context_types.get(location_context_type)
    if location_context is None:
        raise ValueError(f"Unsupported location_context_type: {location_context_type}")

    event_context = _resolve_event_context(request_model, active_clock, chart_type, polity)
    reference_chart = _resolve_reference_chart(
        request_model,
        chart_type,
        polity,
        anchor_datetime=event_context.get("event_datetime"),
    )

    source_tags = list(chart_type.get("source_tags") or [])
    source_tags.extend(domain.get("source_tags") or [])
    source_tags.extend(location_context.get("source_tags") or [])
    if polity is not None:
        source_tags.extend(polity.get("source_tags") or [])
    if reference_chart is not None:
        source_tags.extend(reference_chart.get("source_tags") or [])

    research_flags = list(chart_type.get("research_flags") or [])
    research_flags.extend(domain.get("research_flags") or [])
    if polity is not None:
        research_flags.extend(polity.get("research_flags") or [])
    if reference_chart is not None:
        research_flags.extend(reference_chart.get("research_flags") or [])

    chart_resolution: Dict[str, Any] = {}
    if bundle_resolver is not None:
        chart_resolution = resolve_chart_resolution(
            chart_type_id=request_model.chart_type,
            anchor_datetime=request_model.event_datetime or active_clock.timestamp,
            location=event_context.get("reference_location"),
            timezone_name=event_context.get("event_timezone"),
            house_system_code=active_clock.house_system_code,
            bundle_resolver=bundle_resolver,
            reference_chart=reference_chart,
            event_location=event_context.get("event_location"),
            event_timezone=event_context.get("event_timezone"),
            event_datetime=event_context.get("event_datetime"),
            location_latitude=event_context.get("reference_latitude"),
            location_longitude=event_context.get("reference_longitude"),
            visibility_scope=event_context.get("visibility_scope"),
            location_context_type=event_context.get("location_context_type"),
        )

    return ResolvedMundaneContext(
        request=request_model,
        active_clock=active_clock,
        chart_type=chart_type,
        domain=domain,
        location_context=location_context,
        polity=polity,
        reference_chart=reference_chart,
        event_context=event_context,
        chart_resolution=chart_resolution,
        research_flags=sorted({flag for flag in research_flags if flag}),
        source_tags=sorted({_normalize_id(tag) for tag in source_tags if _normalize_id(tag)}),
    )


def analyze_context(context: ResolvedMundaneContext) -> MundaneAnalysis:
    chart_type = context.chart_type
    domain = context.domain
    doctrine_notes = get_reference_notes()
    activation_watchpoints = get_activation_watchpoints()
    chart_resolution = context.chart_resolution if isinstance(context.chart_resolution, dict) else {}
    domain_assessment = evaluate_domain_context(context)

    framework_note_ids = list(chart_type.get("note_ids") or [])
    framework_note_ids.extend(domain.get("framework_note_ids") or [])
    trigger_ids = list(chart_type.get("trigger_families") or [])
    trigger_note_ids = list(domain.get("trigger_note_ids") or [])
    activation_note_ids = list(domain.get("activation_note_ids") or [])
    activation_focus = {_normalize_id(item) for item in (domain.get("activation_focus") or [])}
    profile_ids = list(trigger_ids)
    profile_ids.extend(sorted(activation_focus))
    trigger_profiles = compute_trigger_profiles(context, trigger_ids=profile_ids)
    trigger_profile_index = {_normalize_id(item.get("id")): item for item in trigger_profiles}

    framework_layer = MundaneLayer(
        id="framework",
        label="Framework Layer",
        summary=str(chart_type.get("summary") or ""),
        source_tags=list(chart_type.get("source_tags") or []),
        notes=_note_payload(framework_note_ids),
        items=[
            {
                "chart_type": chart_type.get("id"),
                "role": chart_type.get("framework_role"),
                "location_context_type": context.event_context.get("location_context_type"),
                "reference_location": context.event_context.get("reference_location"),
                "reference_chart_id": (context.reference_chart or {}).get("id"),
            },
            *(chart_resolution.get("framework_items") or []),
        ],
    )

    trigger_defs = _index_by_id(get_trigger_family_definitions())
    trigger_items: list[Dict[str, Any]] = []
    trigger_source_tags: list[str] = []
    trigger_note_ids.extend(trigger_ids)
    for trigger_id in trigger_ids:
        trigger_def = trigger_defs.get(_normalize_id(trigger_id))
        if trigger_def is None:
            continue
        trigger_source_tags.extend(trigger_def.get("source_tags") or [])
        profile = trigger_profile_index.get(_normalize_id(trigger_id)) or {}
        trigger_items.append(
            {
                "id": trigger_def.get("id"),
                "label": trigger_def.get("label"),
                "summary": trigger_def.get("summary"),
                "status": trigger_def.get("status"),
                "watch_for": trigger_def.get("watch_for") or [],
                "computed_status": profile.get("status"),
                "active": bool(profile.get("active")),
                "strength": profile.get("strength"),
                "score": int(profile.get("score") or 0),
                "evidence": list(profile.get("evidence") or []),
                "metrics": dict(profile.get("metrics") or {}),
            }
        )
        trigger_source_tags.extend(profile.get("source_tags") or [])

    trigger_layer = MundaneLayer(
        id="trigger",
        label="Trigger Layer",
        summary=str(chart_type.get("trigger_summary") or domain.get("trigger_summary") or ""),
        source_tags=sorted({_normalize_id(tag) for tag in trigger_source_tags if _normalize_id(tag)}),
        notes=_note_payload(trigger_note_ids),
        items=trigger_items,
    )
    trigger_layer.items.extend(chart_resolution.get("trigger_items") or [])

    activation_items = []
    activation_source_tags = []
    for watchpoint in activation_watchpoints:
        watchpoint_id = _normalize_id(watchpoint.get("id"))
        if watchpoint_id not in activation_focus:
            continue
        profile = trigger_profile_index.get(watchpoint_id) or {}
        activation_items.append(
            {
                "watchpoint": watchpoint.get("id"),
                "label": watchpoint.get("label"),
                "summary": watchpoint.get("summary"),
                "status": watchpoint.get("status"),
                "computed_status": profile.get("status"),
                "active": bool(profile.get("active")),
                "strength": profile.get("strength"),
                "score": int(profile.get("score") or 0),
                "evidence": list(profile.get("evidence") or []),
            }
        )
        activation_source_tags.extend(watchpoint.get("source_tags") or [])
        activation_source_tags.extend(profile.get("source_tags") or [])

    activation_layer = MundaneLayer(
        id="activation",
        label="Activation Layer",
        summary=str(domain.get("activation_summary") or ""),
        source_tags=sorted({_normalize_id(tag) for tag in activation_source_tags if _normalize_id(tag)}),
        notes=_note_payload(activation_note_ids),
        items=activation_items,
    )
    activation_layer.items.extend(chart_resolution.get("activation_items") or [])

    doctrine = {
        "chart_type_notes": _note_payload(chart_type.get("note_ids") or []),
        "domain_notes": _note_payload(domain.get("domain_note_ids") or []),
        "context_notes": _note_payload(context.location_context.get("note_ids") or []),
        "sources": _source_payload(context.source_tags),
        "chart_resolution": chart_resolution,
        "trigger_profiles": trigger_profiles,
        "matched_rule_sources": _source_payload(
            tag
            for rule in domain_assessment.get("matched_rules") or []
            for tag in (rule.get("source_tags") or [])
        ),
    }
    research = {
        "status": str(domain.get("research_status") or "research_gated"),
        "benchmark_status": str(domain.get("benchmark_status") or "unrated"),
        "flags": context.research_flags,
        "benchmark_profile": domain_assessment.get("calibration") or {},
        "runtime_scope": "computed_chart_context",
        "active_triggers": [row["id"] for row in trigger_profiles if row.get("active")],
    }

    return MundaneAnalysis(
        context=context,
        framework_layer=framework_layer,
        trigger_layer=trigger_layer,
        activation_layer=activation_layer,
        domain_assessment=domain_assessment,
        doctrine=doctrine,
        research=research,
        trigger_profiles=trigger_profiles,
    )
