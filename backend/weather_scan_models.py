from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


@dataclass(slots=True)
class WeatherScanRequest:
    family_id: str
    scan_scope: str
    start_datetime: str
    end_datetime: str
    time_step_hours: int
    top_k: int
    location: Optional[str] = None
    timezone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    region_id: Optional[str] = None
    resolution: Optional[str] = None
    candidate_limit: Optional[int] = None
    house_system_code: Optional[str] = None
    source_preference: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
