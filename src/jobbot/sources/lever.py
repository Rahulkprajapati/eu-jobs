from __future__ import annotations

import requests
from bs4 import BeautifulSoup
from ..models import Job


def _clean(value: str | None) -> str:
    return BeautifulSoup(value or "", "html.parser").get_text(" ").strip()


def fetch_lever(config: dict):
    companies = config.get("sources", {}).get("lever", {}).get("companies", []) or []
    session = requests.Session()
    for company in companies:
        url = f"https://api.lever.co/v0/postings/{company}"
        response = session.get(url, params={"mode": "json"}, timeout=30)
        response.raise_for_status()
        for item in response.json():
            categories = item.get("categories") or {}
            description = " ".join(
                [_clean(item.get("description"))]
                + [_clean(section.get("content")) for section in item.get("lists", [])]
            )
            yield Job(
                source=f"lever:{company}",
                external_id=str(item.get("id")),
                title=item.get("text") or "",
                company=company,
                location=categories.get("location", ""),
                url=item.get("hostedUrl") or item.get("applyUrl") or "",
                description=description,
                tags=", ".join([str(v) for v in categories.values() if v]),
                remote="remote" in str(categories).lower(),
                posted_at=str(item.get("createdAt") or ""),
            )
