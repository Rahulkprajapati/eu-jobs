from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable
from .models import Job

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    title TEXT,
    company TEXT,
    location TEXT,
    url TEXT,
    description TEXT,
    tags TEXT,
    remote INTEGER,
    posted_at TEXT,
    visa_sponsorship INTEGER,
    score INTEGER,
    reject_reason TEXT,
    discovered_at TEXT,
    status TEXT DEFAULT 'new',
    PRIMARY KEY (source, external_id)
);
"""


def connect(db_path: str | Path = "data/jobs.sqlite") -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute(SCHEMA)
    return conn


def upsert_jobs(conn: sqlite3.Connection, jobs: Iterable[Job]) -> int:
    count = 0
    for job in jobs:
        conn.execute(
            """
            INSERT INTO jobs (
                source, external_id, title, company, location, url, description,
                tags, remote, posted_at, visa_sponsorship, score, reject_reason, discovered_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source, external_id) DO UPDATE SET
                title=excluded.title,
                company=excluded.company,
                location=excluded.location,
                url=excluded.url,
                description=excluded.description,
                tags=excluded.tags,
                remote=excluded.remote,
                posted_at=excluded.posted_at,
                visa_sponsorship=excluded.visa_sponsorship,
                score=excluded.score,
                reject_reason=excluded.reject_reason
            """,
            (
                job.source, job.external_id, job.title, job.company, job.location,
                job.url, job.description, job.tags, int(job.remote), job.posted_at,
                None if job.visa_sponsorship is None else int(job.visa_sponsorship),
                job.score, job.reject_reason, job.discovered_at,
            ),
        )
        count += 1
    conn.commit()
    return count


def get_scored_jobs(conn: sqlite3.Connection, min_score: int) -> list[dict]:
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT * FROM jobs
        WHERE score >= ? AND reject_reason = ''
        ORDER BY score DESC, posted_at DESC
        """,
        (min_score,),
    ).fetchall()
    return [dict(r) for r in rows]
