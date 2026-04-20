from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from mundane_models import ActiveClockContext


@dataclass(slots=True)
class WeatherContextRequest:
    family_id: str
    forecast_datetime: Optional[str] = None
    location: Optional[str] = None
    timezone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    house_system_code: Optional[str] = None
    source_preference: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class WeatherLayer:
    id: str
    label: str
    summary: str
    source_tags: List[str] = field(default_factory=list)
    notes: List[Dict[str, Any]] = field(default_factory=list)
    items: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ResolvedWeatherContext:
    request: WeatherContextRequest
    active_clock: ActiveClockContext
    family: Dict[str, Any]
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
class WeatherAnalysis:
    context: ResolvedWeatherContext
    framework_layer: WeatherLayer
    trigger_layer: WeatherLayer
    locality_layer: WeatherLayer
    family_assessment: Dict[str, Any]
    doctrine: Dict[str, Any]
    research: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context": self.context.to_dict(),
            "framework_layer": self.framework_layer.to_dict(),
            "trigger_layer": self.trigger_layer.to_dict(),
            "locality_layer": self.locality_layer.to_dict(),
            "family_assessment": self.family_assessment,
            "doctrine": self.doctrine,
            "research": self.research,
        }
