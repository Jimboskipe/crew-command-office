"""Procore REST API v1.0 & Bluebeam Revu / Studio Integration Adapters.

Generates production-schema integration artifacts with zero secrets committed:
  1. Procore REST v1.0 Payloads (`exports/procore_daily_sync_payload.json`):
     - POST /rest/v1.0/projects/{project_id}/manpower_logs
     - POST /rest/v1.0/projects/{project_id}/timecard_entries
     - POST /rest/v1.0/projects/{project_id}/delay_logs
  2. Bluebeam Revu Markups Summary CSV (`exports/bluebeam_markups_sync.csv`) + CSV Parser:
     - Bridges PDF blueprint markups (Wall IDs, Window Tags, QC Gates) <-> Field Apps
"""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent
EXPORTS_DIR = ROOT / "exports"

# Example Procore project ID mapping (replace with real company project IDs in local .env)
PROCORE_PROJECT_MAP = {
    "JOB-101": 500101,
    "JOB-102": 500102,
    "JOB-103": 500103,
}


def build_procore_sync_payload(suite_data: Dict[str, Any], sync_date: str | None = None) -> Dict[str, Any]:
    """Build Procore REST v1.0 compliant payloads from daily Crew Command state."""
    log_date = sync_date or date.today().isoformat()
    roster = suite_data["roster"]
    schedule = suite_data["schedule"]
    jobsites = suite_data["jobsites"]

    manpower_logs: List[Dict[str, Any]] = []
    timecard_entries: List[Dict[str, Any]] = []
    delay_logs: List[Dict[str, Any]] = []

    for job in jobsites:
        jid = job["job_id"]
        pid = PROCORE_PROJECT_MAP.get(jid, 0)
        site_crew = [m for m in roster if m["job_id"] == jid and m["status"] != "OUT"]
        total_today_hrs = round(sum(m["today_hrs"] for m in site_crew), 2)

        manpower_logs.append(
            {
                "endpoint": f"POST /rest/v1.0/projects/{pid}/manpower_logs",
                "job_id": jid,
                "payload": {
                    "manpower_log": {
                        "date": log_date,
                        "num_workers": len(site_crew),
                        "num_hours": total_today_hrs,
                        "notes": f"{job['foreman']} — {job['notes']}",
                    }
                },
            }
        )

    for m in roster:
        if m["today_hrs"] <= 0:
            continue
        pid = PROCORE_PROJECT_MAP.get(m["job_id"], 0)
        timecard_entries.append(
            {
                "endpoint": f"POST /rest/v1.0/projects/{pid}/timecard_entries",
                "job_id": m["job_id"],
                "emp_id": m["emp_id"],
                "payload": {
                    "timecard_entry": {
                        "date": log_date,
                        "hours": m["today_hrs"],
                        "billable": True,
                        "description": f"{m['name']} ({m['role']}) | Pod: {m['pod']} | Cost Code: {m['cost_code']}",
                        "cost_code_label": m["cost_code"],
                        "timecard_type": "Overtime" if m["ot_hrs"] > 0 else "Regular Time",
                    }
                },
            }
        )

    for t in schedule:
        if t["material_gate"] in ("BLOCKED", "WATCH"):
            pid = PROCORE_PROJECT_MAP.get(t["job_id"], 0)
            delay_logs.append(
                {
                    "endpoint": f"POST /rest/v1.0/projects/{pid}/delay_logs",
                    "job_id": t["job_id"],
                    "task_id": t["task_id"],
                    "payload": {
                        "delay_log": {
                            "date": log_date,
                            "delay_type": "Material Delivery" if t["material_gate"] == "BLOCKED" else "Logistics Watch",
                            "comments": f"[{t['task_id']}] {t['title']} — {t['material_note']}",
                            "start_time_hour": 7,
                            "start_time_minute": 0,
                        }
                    },
                }
            )

    return {
        "integration": "Procore REST API v1.0 (Dry-Run Sync Package)",
        "auth_mode": "OAuth 2.0 Client Credentials / User Token (configured via local .env, never committed)",
        "sync_date": log_date,
        "summary": {
            "manpower_logs_count": len(manpower_logs),
            "timecard_entries_count": len(timecard_entries),
            "delay_logs_count": len(delay_logs),
        },
        "manpower_logs": manpower_logs,
        "timecard_entries": timecard_entries,
        "delay_logs": delay_logs,
    }


def export_bluebeam_markups_csv(
    suite_data: Dict[str, Any],
    csv_path: Path = EXPORTS_DIR / "bluebeam_markups_sync.csv",
) -> Path:
    """Export Bluebeam Revu Markups Summary-compatible CSV for round-trip Studio/PDF status sync."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "Subject",
                "Page Label",
                "Label",
                "Author",
                "Status",
                "Cost Code",
                "Budget Hrs",
                "Actual Hrs",
                "Pct Complete",
                "Comments",
            ]
        )
        for t in suite_data["schedule"]:
            bb_status = (
                "Completed"
                if t["pct_complete"] >= 100
                else ("Hold - Material" if t["material_gate"] == "BLOCKED" else "In Progress")
            )
            w.writerow(
                [
                    t["source_app"],
                    t["job_id"],
                    t["task_id"],
                    t["assigned_pod"],
                    bb_status,
                    t["cost_code"],
                    f"{t['budget_hrs']:.1f}",
                    f"{t['actual_hrs']:.1f}",
                    f"{t['pct_complete']}%",
                    f"{t['title']} | {t['material_note']}",
                ]
            )
    return csv_path


def parse_bluebeam_markups_csv(csv_path: Path) -> List[Dict[str, str]]:
    """Ingest a Bluebeam Revu Markups Summary CSV back into structured task/opening records."""
    records: List[Dict[str, str]] = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row.get("Label"):
                continue
            records.append(
                {
                    "source_subject": row.get("Subject", "").strip(),
                    "job_or_sheet": row.get("Page Label", "").strip(),
                    "tag_label": row.get("Label", "").strip(),
                    "status": row.get("Status", "").strip(),
                    "comments": row.get("Comments", "").strip(),
                }
            )
    return records


def export_all_integrations(suite_data: Dict[str, Any]) -> Dict[str, Any]:
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    procore_payload = build_procore_sync_payload(suite_data)
    procore_path = EXPORTS_DIR / "procore_daily_sync_payload.json"
    procore_path.write_text(json.dumps(procore_payload, indent=2), encoding="utf-8")
    bluebeam_path = export_bluebeam_markups_csv(suite_data)
    return {
        "procore_payload_path": str(procore_path),
        "bluebeam_csv_path": str(bluebeam_path),
        "procore_summary": procore_payload["summary"],
    }
