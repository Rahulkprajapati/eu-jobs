from __future__ import annotations

import os
import requests


def notify_slack(config: dict, message: str) -> None:
    notif = config.get("notifications", {})
    if not notif.get("slack_enabled"):
        return
    webhook = os.getenv(notif.get("slack_webhook_env", "SLACK_WEBHOOK_URL"))
    if not webhook:
        return
    requests.post(webhook, json={"text": message}, timeout=15).raise_for_status()
