from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional


@dataclass
class Job:
    source: str
    external_id: str
    title: str
    company: str
    location: str
    url: str
    description: str
    tags: str = ""
    remote: bool = False
    posted_at: Optional[str] = None
    visa_sponsorship: Optional[bool] = None
    score: int = 0
    reject_reason: str = ""
    discovered_at: str = datetime.now(timezone.utc).isoformat()

    def asdict(self) -> dict:
        return asdict(self)
