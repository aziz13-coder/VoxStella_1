from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

from mundane_models import MundaneContextRequest


@dataclass(slots=True)
class MundaneScanRequest:
    context_request: MundaneContextRequest
    scan_mode: str
    region_id: str
    resolution: str
    top_k: int
    minimum_score: float = 0.0
    candidate_limit: Optional[int] = None
    fixed_datetime: Optional[str] = None
    start_datetime: Optional[str] = None
    end_datetime: Optional[str] = None
    time_step_hours: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["context_request"] = self.context_request.to_dict()
        return payload
