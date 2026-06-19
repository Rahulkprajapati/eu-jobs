from __future__ import annotations

import html
import re
from typing import Iterable
import requests
from bs4 import BeautifulSoup

from ..models import Job


def clean_html(value: str | None) -> str:
    if not value:
        return ""
    text = BeautifulSoup(value, "html.parser").get_text(" ")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def fetch_arbeitnow(config: dict) -> Iterable[Job]:
    source_cfg = config["sources"]["arbeitnow"]
    endpoint = source_cfg.get("endpoint", "https://www.arbeitnow.com/api/job-board-api")
    pages = int(source_cfg.get("pages", 1))
    visa_sponsorship = source_cfg.get("visa_sponsorship", True)

    session = requests.Session()
    for page in range(1, pages + 1):
        params = {"page": page}
        if visa_sponsorship is not None:
            params["visa_sponsorship"] = str(visa_sponsorship).lower()
        response = session.get(endpoint, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()
        for item in payload.get("data", []):
            tags = item.get("tags") or []
            description = clean_html(item.get("description"))
            yield Job(
                source="arbeitnow",
                external_id=str(item.get("slug") or item.get("id") or item.get("url")),
                title=item.get("title") or "",
                company=item.get("company_name") or item.get("company") or "",
                location=item.get("location") or "",
                url=item.get("url") or item.get("apply_url") or "",
                description=description,
                tags=", ".join(tags),
                remote=bool(item.get("remote")),
                posted_at=str(item.get("created_at") or item.get("posted_at") or ""),
                visa_sponsorship=item.get("visa_sponsorship"),
            )
