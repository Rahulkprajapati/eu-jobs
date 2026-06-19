from __future__ import annotations

import csv
import json
import re
import shutil
from pathlib import Path
from jinja2 import Environment, FileSystemLoader


def _safe_name(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return value[:90] or "job"


def render_cover_letter(config: dict, job: dict) -> str:
    template_path = Path(config["application"]["cover_letter_template"])
    env = Environment(loader=FileSystemLoader(str(template_path.parent)))
    template = env.get_template(template_path.name)
    return template.render(candidate=config["candidate"], job=job)


def package_jobs(config: dict, jobs: list[dict]) -> Path:
    out_dir = Path(config["application"].get("output_dir", "out"))
    app_dir = out_dir / "applications"
    app_dir.mkdir(parents=True, exist_ok=True)
    queue_path = out_dir / "application_queue.csv"

    rows = []
    cv_path = Path(config["candidate"].get("cv_path", ""))

    for job in jobs:
        folder = app_dir / _safe_name(f"{job['company']}-{job['title']}")
        folder.mkdir(parents=True, exist_ok=True)
        cover_letter = render_cover_letter(config, job)
        (folder / "cover_letter.md").write_text(cover_letter, encoding="utf-8")
        (folder / "metadata.json").write_text(json.dumps(job, indent=2), encoding="utf-8")
        if cv_path.exists():
            shutil.copy2(cv_path, folder / cv_path.name)
        rows.append({
            "status": job.get("status", config["application"].get("default_status", "new")),
            "score": job["score"],
            "title": job["title"],
            "company": job["company"],
            "location": job["location"],
            "source": job["source"],
            "apply_url": job["url"],
            "package_path": str(folder),
        })

    with queue_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["status", "score", "title", "company", "location", "source", "apply_url", "package_path"])
        writer.writeheader()
        writer.writerows(rows)

    return queue_path
