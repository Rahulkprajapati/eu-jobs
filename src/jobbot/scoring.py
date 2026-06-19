from __future__ import annotations

import re
from .models import Job


def contains_any(text: str, keywords: list[str]) -> bool:
    lower = text.lower()
    return any(k.lower() in lower for k in keywords)


def count_matches(text: str, keywords: list[str]) -> int:
    lower = text.lower()
    return sum(1 for k in keywords if k.lower() in lower)


def score_job(job: Job, config: dict) -> Job:
    search = config["search"]
    text = " ".join([job.title, job.company, job.location, job.tags, job.description]).lower()

    for bad in search.get("visa_negative_keywords", []):
        if bad.lower() in text:
            job.reject_reason = f"Rejected due to visa negative keyword: {bad}"
            job.score = 0
            return job

    score = 0

    role_matches = count_matches(job.title, search.get("roles", []))
    if role_matches:
        score += 25
    elif any(word in job.title.lower() for word in ["devops", "platform", "sre", "cloud", "infrastructure", "kubernetes"]):
        score += 18

    skill_matches = count_matches(text, search.get("required_keywords", []))
    score += min(30, skill_matches * 4)

    if job.visa_sponsorship is True:
        score += 25
    elif contains_any(text, search.get("visa_positive_keywords", [])):
        score += 20

    if contains_any(job.location, search.get("target_locations", [])) or contains_any(text, search.get("target_countries", [])):
        score += 10

    if re.search(r"\b(senior|sr\.?|lead|staff)\b", text):
        score += 8
    elif re.search(r"\b(mid|intermediate|engineer)\b", text):
        score += 6

    job.score = min(score, 100)
    return job
