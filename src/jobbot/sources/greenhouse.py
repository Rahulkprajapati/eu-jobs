from __future__ import annotations

import requests
from bs4 import BeautifulSoup
from ..models import Job


def _clean(html_text: str | None) -> str:
    return BeautifulSoup(html_text or "", "html.parser").get_text(" ").strip()


def fetch_greenhouse(config: dict):
    tokens = config.get("sources", {}).get("greenhouse", {}).get("board_tokens", []) or []
    session = requests.Session()
    for token in tokens:
        url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
        response = session.get(url, params={"content": "true"}, timeout=30)
        response.raise_for_status()
        payload = response.json()
        for item in payload.get("jobs", []):
            offices = item.get("offices") or []
            locations = ", ".join([o.get("name", "") for o in offices if o.get("name")])
            yield Job(
                source=f"greenhouse:{token}",
                external_id=str(item.get("id")),
                title=item.get("title") or "",
                company=token,
                location=locations or item.get("location", {}).get("name", ""),
                url=item.get("absolute_url") or "",
                description=_clean(item.get("content")),
                tags="greenhouse",
                remote="remote" in (locations or "").lower(),
                posted_at=str(item.get("updated_at") or ""),
            )
