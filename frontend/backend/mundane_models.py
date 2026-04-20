from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(slots=True)
class ActiveClockContext:
    timestamp: str
    location: Optional[str]
    timezone: Optional[str]
    mode: Optional[str] = None
    house_system_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class MundaneContextRequest:
    chart_type: str
    domain: Optional[str] = None
    polity_id: Optional[str] = None
    custom_polity_label: Optional[str] = None
    location_context_type: Optional[str] = None
    reference_location: Optional[str] = None
    reference_latitude: Optional[float] = None
    reference_longitude: Optional[float] = None
    event_datetime: Optional[str] = None
    event_location: Optional[str] = None
    event_timezone: Optional[str] = None
    national_chart_id: Optional[str] = None
    custom_chart_label: Optional[str] = None
    custom_chart_datetime: Optional[str] = None
    custom_chart_location: Optional[str] = None
    custom_chart_timezone: Optional[str] = None
    visibility_scope: Optional[str] = None
    source_preference: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class MundaneLayer:
    id: str
    label: str
    summary: str
    source_tags: List[str] = field(default_factory=list)
    notes: List[Dict[str, Any]] = field(default_factory=list)
    items: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ResolvedMundaneContext:
    request: MundaneContextRequest
    active_clock: ActiveClockContext
    chart_type: Dict[str, Any]
    domain: Dict[str, Any]
    location_context: Dict[str, Any]
    polity: Optional[Dict[str, Any]]
    reference_chart: Optional[Dict[str, Any]]
    event_context: Dict[str, Any]
    chart_resolution: Dict[str, Any] = field(default_factory=dict)
    research_flags: List[str] = field(default_factory=list)
    source_tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["request"] = self.request.to_dict()
        payload["active_clock"] = self.active_clock.to_dict()
        return payload


@dataclass(slots=True)
class MundaneAnalysis:
    context: ResolvedMundaneContext
    framework_layer: MundaneLayer
    trigger_layer: MundaneLayer
    activation_layer: MundaneLayer
    domain_assessment: Dict[str, Any]
    doctrine: Dict[str, Any]
    research: Dict[str, Any]
    trigger_profiles: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context": self.context.to_dict(),
            "framework_layer": self.framework_layer.to_dict(),
            "trigger_layer": self.trigger_layer.to_dict(),
            "activation_layer": self.activation_layer.to_dict(),
            "trigger_profiles": self.trigger_profiles,
            "domain_assessment": self.domain_assessment,
            "doctrine": self.doctrine,
            "research": self.research,
        }
