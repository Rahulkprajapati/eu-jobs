from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Any


SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"


def _env_enabled(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _sheet_config(config: dict[str, Any]) -> dict[str, Any]:
    return config.get("google_sheets", {})


def is_sheets_sync_enabled(config: dict[str, Any]) -> bool:
    sheets = _sheet_config(config)
    return bool(sheets.get("enabled")) or _env_enabled(os.getenv("JOBBOT_GOOGLE_SHEETS_ENABLED"))


def _spreadsheet_id(config: dict[str, Any]) -> str:
    sheets = _sheet_config(config)
    env_name = sheets.get("spreadsheet_id_env", "GOOGLE_SHEET_ID")
    value = os.getenv(env_name, "").strip()
    if value:
        return value
    return str(sheets.get("spreadsheet_id", "")).strip()


def _read_queue(queue_path: Path) -> list[list[str]]:
    with queue_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        rows = [[str(row.get(field, "")) for field in header] for row in reader]
    return [header, *rows] if header else []


def _quote_sheet_name(worksheet_name: str) -> str:
    escaped = worksheet_name.replace("'", "''")
    return f"'{escaped}'"


def _ensure_sheet(service: Any, spreadsheet_id: str, worksheet_name: str) -> None:
    metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    existing_titles = {sheet["properties"]["title"] for sheet in metadata.get("sheets", [])}
    if worksheet_name in existing_titles:
        return

    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={
            "requests": [
                {
                    "addSheet": {
                        "properties": {
                            "title": worksheet_name,
                            "gridProperties": {"frozenRowCount": 1},
                        }
                    }
                }
            ]
        },
    ).execute()


def _read_existing_values(service: Any, spreadsheet_id: str, worksheet_name: str) -> list[list[str]]:
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"{_quote_sheet_name(worksheet_name)}!A:Z",
    ).execute()
    return result.get("values", [])


def _merge_existing_rows(new_values: list[list[str]], existing_values: list[list[str]]) -> list[list[str]]:
    if len(new_values) < 2 or len(existing_values) < 2:
        return new_values

    header = new_values[0]
    existing_header = existing_values[0]
    if "apply_url" not in header or "apply_url" not in existing_header:
        return new_values

    new_apply_idx = header.index("apply_url")
    existing_apply_idx = existing_header.index("apply_url")
    status_idx = header.index("status") if "status" in header else None
    existing_status_idx = existing_header.index("status") if "status" in existing_header else None

    existing_by_url = {
        row[existing_apply_idx]: row
        for row in existing_values[1:]
        if len(row) > existing_apply_idx and row[existing_apply_idx]
    }
    new_urls = set()
    merged_rows = []

    for row in new_values[1:]:
        apply_url = row[new_apply_idx] if len(row) > new_apply_idx else ""
        new_urls.add(apply_url)
        existing = existing_by_url.get(apply_url)
        if status_idx is not None and existing_status_idx is not None and existing:
            existing_status = existing[existing_status_idx] if len(existing) > existing_status_idx else ""
            if existing_status:
                row[status_idx] = existing_status
        merged_rows.append(row)

    for row in existing_values[1:]:
        apply_url = row[existing_apply_idx] if len(row) > existing_apply_idx else ""
        if not apply_url or apply_url in new_urls:
            continue
        merged_rows.append([row[i] if i < len(row) else "" for i in range(len(header))])

    return [header, *merged_rows]


def sync_application_queue(config: dict[str, Any], queue_path: str | Path | None = None) -> None:
    if not is_sheets_sync_enabled(config):
        print("Google Sheets sync disabled.")
        return

    spreadsheet_id = _spreadsheet_id(config)
    if not spreadsheet_id:
        raise RuntimeError("Google Sheets sync is enabled, but GOOGLE_SHEET_ID is not set.")

    sheets = _sheet_config(config)
    worksheet_name = sheets.get("worksheet_name", "Application Queue")
    output_dir = Path(config["application"].get("output_dir", "out"))
    queue = Path(queue_path) if queue_path else output_dir / "application_queue.csv"
    values = _read_queue(queue)
    if not values:
        print(f"No queue rows found in {queue}. Skipping Google Sheets sync.")
        return

    import google.auth
    from googleapiclient.discovery import build

    credentials, _ = google.auth.default(scopes=[SHEETS_SCOPE])
    service = build("sheets", "v4", credentials=credentials, cache_discovery=False)

    _ensure_sheet(service, spreadsheet_id, worksheet_name)
    if sheets.get("preserve_existing_rows", True):
        existing_values = _read_existing_values(service, spreadsheet_id, worksheet_name)
        values = _merge_existing_rows(values, existing_values)

    if sheets.get("clear_existing", True):
        service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id,
            range=f"{_quote_sheet_name(worksheet_name)}!A:Z",
            body={},
        ).execute()

    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"{_quote_sheet_name(worksheet_name)}!A1",
        valueInputOption="RAW",
        body={"values": values},
    ).execute()
    print(f"Synced {len(values) - 1} application rows to Google Sheets.")
