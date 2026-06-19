from __future__ import annotations

import argparse
from pathlib import Path

from .config import load_config
from .db import connect, upsert_jobs, get_scored_jobs
from .scoring import score_job
from .packager import package_jobs
from .notify import notify_slack
from .sources.arbeitnow import fetch_arbeitnow
from .sources.greenhouse import fetch_greenhouse
from .sources.lever import fetch_lever


def discover(config_path: str) -> None:
    config = load_config(config_path)
    Path("data").mkdir(exist_ok=True)
    all_jobs = []

    sources = config.get("sources", {})
    if sources.get("arbeitnow", {}).get("enabled"):
        all_jobs.extend(list(fetch_arbeitnow(config)))
    if sources.get("greenhouse", {}).get("enabled"):
        all_jobs.extend(list(fetch_greenhouse(config)))
    if sources.get("lever", {}).get("enabled"):
        all_jobs.extend(list(fetch_lever(config)))

    scored = [score_job(job, config) for job in all_jobs]
    conn = connect("data/jobs.sqlite")
    saved = upsert_jobs(conn, scored)
    top = [j for j in scored if j.score >= config["search"].get("min_score", 70) and not j.reject_reason]
    notify_slack(config, f"Europe jobbot: discovered {saved} jobs, {len(top)} matched above threshold.")
    print(f"Discovered {saved} jobs. {len(top)} matched above threshold.")


def package(config_path: str, min_score: int | None) -> None:
    config = load_config(config_path)
    threshold = min_score if min_score is not None else config["search"].get("min_score", 70)
    conn = connect("data/jobs.sqlite")
    jobs = get_scored_jobs(conn, threshold)
    queue = package_jobs(config, jobs)
    print(f"Packaged {len(jobs)} jobs into {queue}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Europe DevOps job automation")
    sub = parser.add_subparsers(dest="command", required=True)

    p1 = sub.add_parser("discover")
    p1.add_argument("--config", default="config/config.yaml")

    p2 = sub.add_parser("package")
    p2.add_argument("--config", default="config/config.yaml")
    p2.add_argument("--min-score", type=int, default=None)

    args = parser.parse_args()
    if args.command == "discover":
        discover(args.config)
    elif args.command == "package":
        package(args.config, args.min_score)


if __name__ == "__main__":
    main()
