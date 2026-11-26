"""Crew Command & Corporate Office Hub — Core Engine (15-30 Man Framing Crew).

Connects:
  1. Blueprint / Pre-Staging App  (framing-factory-planner) -> wall tasks, bidding tiers, goal hours
  2. Material & QC Foreman App    (highrise-window-tracker) -> warehouse/floor readiness & QC gates
  3. Personnel, Schedule & Office (crew-command-office)     -> 22-man crew roster, certs, time/OT,
                                                               schedule dispatch, job costing, and
                                                               QuickBooks/Payroll CSV export.

Zero external dependencies (Python 3.9+ standard library only).
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent
DOCS_DIR = ROOT / "docs"
EXPORTS_DIR = ROOT / "exports"
SIBLING_FRAMING_JSON = ROOT.parent / "framing-factory-planner" / "docs" / "project_data.json"
SIBLING_WINDOW_JSON = ROOT.parent / "highrise-window-tracker" / "docs" / "window_data.json"

SUITE_LINKS = {
    "blueprint_app": "https://jimboskipe.github.io/framing-factory-planner/",
    "blueprint_repo": "https://github.com/Jimboskipe/framing-factory-planner",
    "foreman_logistics_app": "https://jimboskipe.github.io/highrise-window-tracker/",
    "foreman_logistics_repo": "https://github.com/Jimboskipe/highrise-window-tracker",
    "ops_control_repo": "https://github.com/Jimboskipe/ops-control-tower",
    "crew_command_repo": "https://github.com/Jimboskipe/crew-command-office",
}

BURDEN_MULTIPLIER = 1.28  # Payroll tax, workers' comp, GL & benefits load factor
OT_THRESHOLD_HRS = 40.0
OT_RATE_MULT = 1.50


@dataclass
class Jobsite:
    job_id: str
    name: str
    location: str
    client: str
    foreman: str
    target_completion: str
    linked_app: str
    linked_url: str
    budgeted_labor_hrs: float
    logged_labor_hrs: float
    material_status: str  # READY, WATCH, BLOCKED
    notes: str


@dataclass
class CrewMember:
    emp_id: str
    name: str
    role: str
    skill_tier: str       # Lead, Journeyman, Specialist, Operator, Apprentice, Runner
    job_id: str
    pod: str              # e.g. "Pod A (2-Man Walls)", "Pod B (Cut Bench)", "SkyTrak/Crane"
    base_rate: float
    week_hrs_prior: float  # Hours already worked Mon-Wed before today
    today_hrs: float       # Hours logged today (Thu)
    cost_code: str
    status: str            # ON_SITE, LATE, OUT, REASSIGNED
    certs: List[str]
    cert_alerts: List[str] = field(default_factory=list)  # e.g., ["SkyTrak expires in 14d"]

    @property
    def total_week_hrs(self) -> float:
        return round(self.week_hrs_prior + self.today_hrs, 2)

    @property
    def st_hrs(self) -> float:
        return round(min(OT_THRESHOLD_HRS, self.total_week_hrs), 2)

    @property
    def ot_hrs(self) -> float:
        return round(max(0.0, self.total_week_hrs - OT_THRESHOLD_HRS), 2)

    @property
    def gross_wages(self) -> float:
        return round((self.st_hrs * self.base_rate) + (self.ot_hrs * self.base_rate * OT_RATE_MULT), 2)

    @property
    def burdened_cost(self) -> float:
        return round(self.gross_wages * BURDEN_MULTIPLIER, 2)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d.update(
            {
                "total_week_hrs": self.total_week_hrs,
                "st_hrs": self.st_hrs,
                "ot_hrs": self.ot_hrs,
                "gross_wages": self.gross_wages,
                "burdened_cost": self.burdened_cost,
                "ot_warning": self.total_week_hrs >= 36.0,
            }
        )
        return d


@dataclass
class ScheduleTask:
    task_id: str
    job_id: str
    title: str
    source_app: str           # framing-factory-planner, highrise-window-tracker, crew-command
    bidding_tier: str         # 1-Man Solo, 2-Man Team, Full-Crew, Logistics
    assigned_pod: str
    assigned_emp_ids: List[str]
    cost_code: str
    scheduled_day: str
    budget_hrs: float
    actual_hrs: float
    pct_complete: int
    material_gate: str        # READY, WATCH, BLOCKED
    material_note: str
    required_cert: Optional[str] = None

    @property
    def earned_hrs(self) -> float:
        return round(self.budget_hrs * (self.pct_complete / 100.0), 2)

    @property
    def variance_hrs(self) -> float:
        """Positive = ahead of budget (under hours); negative = over budget."""
        return round(self.earned_hrs - self.actual_hrs, 2)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["earned_hrs"] = self.earned_hrs
        d["variance_hrs"] = self.variance_hrs
        return d


def load_sibling_suite_context() -> Dict[str, Any]:
    """Read live specs from framing-factory-planner and highrise-window-tracker if present."""
    ctx: Dict[str, Any] = {
        "framing_connected": False,
        "framing_project": "3-Bedroom Custom Walkout Ranch (9'/10' Tall Walls, Tray Ceilings)",
        "framing_wall_count": 8,
        "framing_header_batches": 0,
        "framing_daily_goal": "Day 2 Goal: 2-Man Teams frame W-2 & W-3; Solo frames W-6 & W-7; Full-Crew sets LIFO truss packs.",
        "window_connected": False,
        "window_project": "15-Story Commercial High-Rise Window Logistics (468 Units)",
        "window_warehouse_sqft": 2000,
        "window_row_pitch_ft": 9,
        "window_max_depth": 8,
        "window_pallets_in_room_a": 26,
        "window_active_floor_note": "Floor 7 active set/caulk; Floors 9-15 staged in Room A.",
    }

    if SIBLING_FRAMING_JSON.exists():
        try:
            fdata = json.loads(SIBLING_FRAMING_JSON.read_text(encoding="utf-8"))
            ctx["framing_connected"] = True
            ctx["framing_project"] = fdata.get("project_name", ctx["framing_project"])
            ctx["framing_daily_goal"] = fdata.get("daily_goal", ctx["framing_daily_goal"])
            walls = fdata.get("walls", [])
            if walls:
                ctx["framing_wall_count"] = len(walls)
            headers = fdata.get("batches", {}).get("headers", [])
            ctx["framing_header_batches"] = len(headers)
        except Exception:
            pass

    if SIBLING_WINDOW_JSON.exists():
        try:
            wdata = json.loads(SIBLING_WINDOW_JSON.read_text(encoding="utf-8"))
            ctx["window_connected"] = True
            ctx["window_project"] = wdata.get("project_name", ctx["window_project"])
            wh = wdata.get("warehouse", {})
            ctx["window_warehouse_sqft"] = wh.get("total_sq_ft", 2000)
            ctx["window_row_pitch_ft"] = wh.get("row_spacing_ft", 9)
            ctx["window_max_depth"] = wh.get("max_pallets_per_row", 8)
            rooms = wh.get("rooms", [])
            if rooms:
                ctx["window_pallets_in_room_a"] = sum(
                    r.get("pallets_loaded", 0) for r in rooms[0].get("rows", [])
                )
        except Exception:
            pass

    return ctx


def build_default_jobsites(ctx: Dict[str, Any]) -> List[Jobsite]:
    return [
        Jobsite(
            job_id="JOB-101",
            name="Weston Custom Walkout Ranch (Framing Factory)",
            location="Weston / Wausau, WI",
            client="Private Custom Homeowner",
            foreman="Mike Kowalski (Lead Foreman)",
            target_completion="2026-12-11",
            linked_app="Framing Factory Planner",
            linked_url=SUITE_LINKS["blueprint_app"],
            budgeted_labor_hrs=420.0,
            logged_labor_hrs=268.0,
            material_status="READY",
            notes=ctx["framing_daily_goal"],
        ),
        Jobsite(
            job_id="JOB-102",
            name="15-Story Commercial Tower — Windows & Infill",
            location="Madison, WI (Travel Crew)",
            client="Midwest Commercial GC",
            foreman="Carlos Mendez (Commercial Foreman)",
            target_completion="2027-02-28",
            linked_app="High-Rise Window Tracker",
            linked_url=SUITE_LINKS["foreman_logistics_app"],
            budgeted_labor_hrs=640.0,
            logged_labor_hrs=392.0,
            material_status="WATCH",
            notes=ctx["window_active_floor_note"],
        ),
        Jobsite(
            job_id="JOB-103",
            name="Lake DuBay Custom Addition & Timber Porch",
            location="Mosinee / Lake DuBay, WI",
            client="Northwoods Custom Build",
            foreman="Derek Halvorsen (Lead Carpenter)",
            target_completion="2026-12-19",
            linked_app="Framing Factory Planner",
            linked_url=SUITE_LINKS["blueprint_app"],
            budgeted_labor_hrs=210.0,
            logged_labor_hrs=94.0,
            material_status="BLOCKED",
            notes="Hold on ridge LVL beam delivery (ETA Fri 07:30 AM) — crew shifted to interior partition prep.",
        ),
    ]


def build_default_roster() -> List[CrewMember]:
    """Realistic 22-man framing & commercial carpentry crew (fits 15-30 man company scale)."""
    return [
        # Leadership & Foremen (3)
        CrewMember("E-01", "James M. Doyle", "Field Superintendent", "Lead", "JOB-101", "Command / All Sites", 46.00, 31.0, 9.0, "01-100 Supervision", "ON_SITE", ["Fall Protection", "SkyTrak/Telehandler", "Aerial Lift", "Rigging/Signal", "First Aid/CPR"]),
        CrewMember("E-02", "Mike Kowalski", "Lead Framing Foreman", "Lead", "JOB-101", "Pod A (2-Man Walls)", 38.00, 30.0, 9.0, "06-110 Walls", "ON_SITE", ["Fall Protection", "SkyTrak/Telehandler", "Rigging/Signal", "First Aid/CPR"]),
        CrewMember("E-03", "Carlos Mendez", "Commercial Foreman", "Lead", "JOB-102", "Window Set & QC", 40.00, 32.0, 9.5, "08-500 Windows", "ON_SITE", ["Fall Protection", "Aerial Lift", "Rigging/Signal", "First Aid/CPR"]),

        # JOB-101 Framing Factory Crew (10 men)
        CrewMember("E-04", "Tyler Bergstrom", "Journeyman Framer", "Journeyman", "JOB-101", "Pod A (2-Man Walls)", 33.00, 29.0, 9.0, "06-110 Walls", "ON_SITE", ["Fall Protection", "Aerial Lift"]),
        CrewMember("E-05", "Nate Olson", "Journeyman Framer", "Journeyman", "JOB-101", "Pod B (2-Man Walls)", 33.00, 28.0, 8.5, "06-110 Walls", "ON_SITE", ["Fall Protection"]),
        CrewMember("E-06", "Brandon Schulz", "Journeyman Framer", "Journeyman", "JOB-101", "Pod B (2-Man Walls)", 32.00, 28.0, 8.5, "06-110 Walls", "ON_SITE", ["Fall Protection", "Aerial Lift"]),
        CrewMember("E-07", "Travis Novak", "Solo Wall & Layout Spec.", "Specialist", "JOB-101", "Pod C (1-Man Solo)", 35.00, 30.0, 8.5, "06-110 Walls", "ON_SITE", ["Fall Protection", "First Aid/CPR"]),
        CrewMember("E-08", "Gavin Krueger", "Cut Bench & Stair Spec.", "Specialist", "JOB-101", "Cut Bench / Stairs", 34.50, 29.5, 8.5, "06-120 Stairs/Cut", "ON_SITE", ["Fall Protection"]),
        CrewMember("E-09", "Brett Zimmermann", "SkyTrak / Rigging Op.", "Operator", "JOB-101", "Material / SkyTrak", 34.00, 31.0, 9.5, "01-500 Staging", "ON_SITE", ["Fall Protection", "SkyTrak/Telehandler", "Rigging/Signal"], ["SkyTrak card renews in 18d"]),
        CrewMember("E-10", "Cole Sorensen", "2nd-Yr Apprentice", "Apprentice", "JOB-101", "Pod A (2-Man Walls)", 24.00, 27.0, 8.5, "06-110 Walls", "ON_SITE", ["Fall Protection"]),
        CrewMember("E-11", "Ethan Miller", "1st-Yr Apprentice", "Apprentice", "JOB-101", "Cut Bench / Stairs", 21.50, 26.0, 8.0, "06-120 Stairs/Cut", "LATE", ["Fall Protection"]),
        CrewMember("E-12", "Jordan Perez", "Yard & Material Runner", "Runner", "JOB-101", "Material / SkyTrak", 22.00, 28.0, 8.5, "01-500 Staging", "ON_SITE", ["Fall Protection", "First Aid/CPR"]),

        # JOB-102 High-Rise Window & Commercial Crew (6 men)
        CrewMember("E-13", "Marcus Jenkins", "Journeyman Carpenter", "Journeyman", "JOB-102", "Window Set Crew", 36.00, 31.0, 9.5, "08-500 Windows", "ON_SITE", ["Fall Protection", "Aerial Lift", "Rigging/Signal"]),
        CrewMember("E-14", "Kyle Peterson", "Journeyman Carpenter", "Journeyman", "JOB-102", "Window Set Crew", 35.00, 30.0, 9.0, "08-500 Windows", "ON_SITE", ["Fall Protection", "Aerial Lift"]),
        CrewMember("E-15", "Samir Patel", "Caulk & Envelope Tech", "Specialist", "JOB-102", "Caulk / Drywall-Ready", 31.00, 29.0, 8.5, "08-510 Envelope", "ON_SITE", ["Fall Protection", "Aerial Lift"]),
        CrewMember("E-16", "Devon Brooks", "Warehouse / Forklift Op.", "Operator", "JOB-102", "2,000 SF Warehouse", 30.00, 30.0, 8.5, "01-500 Staging", "ON_SITE", ["Fall Protection", "SkyTrak/Telehandler", "Rigging/Signal"]),
        CrewMember("E-17", "Lucas Meyer", "Apprentice Carpenter", "Apprentice", "JOB-102", "Caulk / Drywall-Ready", 24.50, 27.0, 8.5, "08-510 Envelope", "ON_SITE", ["Fall Protection"]),
        CrewMember("E-18", "Noah Gallagher", "Apprentice Carpenter", "Apprentice", "JOB-102", "Window Set Crew", 23.00, 24.0, 0.0, "08-500 Windows", "OUT", ["Fall Protection"]),

        # JOB-103 Lake DuBay Addition Crew (4 men)
        CrewMember("E-19", "Derek Halvorsen", "Lead Carpenter", "Lead", "JOB-103", "Lake DuBay Lead", 36.50, 30.0, 8.5, "06-110 Walls", "ON_SITE", ["Fall Protection", "First Aid/CPR"]),
        CrewMember("E-20", "Austin Bauer", "Journeyman Framer", "Journeyman", "JOB-103", "Lake DuBay Framing", 31.50, 29.0, 8.5, "06-110 Walls", "ON_SITE", ["Fall Protection"]),
        CrewMember("E-21", "Caleb Larson", "Apprentice Framer", "Apprentice", "JOB-103", "Lake DuBay Framing", 23.50, 27.5, 8.5, "06-110 Walls", "ON_SITE", ["Fall Protection"]),
        CrewMember("E-22", "Owen Lindstrom", "Material Runner / Driver", "Runner", "JOB-103", "Multi-Site Supply", 22.50, 29.0, 8.5, "01-500 Staging", "REASSIGNED", ["Fall Protection"], ["Aerial Lift ticket EXPIRED — do not assign lift"]),
    ]


def build_default_schedule() -> List[ScheduleTask]:
    """Schedule linking Framing Factory walls/trusses + High-Rise Window floors + Lake DuBay."""
    return [
        ScheduleTask("T-101", "JOB-101", "Frame & Tyvek W-2 (10' Great Room) + W-3 (Master/Tray)", "framing-factory-planner", "2-Man Team", "Pod A (2-Man Walls)", ["E-02", "E-04", "E-10"], "06-110 Walls", "Thu Nov 26", 16.0, 14.5, 95, "READY", "Green/Orange stud bunks spotted on deck; window openings MS1-60 & GRW1-60 verified."),
        ScheduleTask("T-102", "JOB-101", "Frame W-1 Walkout Exposure + W-4 Bedrooms", "framing-factory-planner", "2-Man Team", "Pod B (2-Man Walls)", ["E-05", "E-06"], "06-110 Walls", "Thu Nov 26", 15.0, 14.0, 90, "READY", "Headers LLPD1-82 & BR2W1-48 pre-cut at bench; on-deck partition channels marked."),
        ScheduleTask("T-103", "JOB-101", "Solo Build W-6 Garage Portal + W-7 Interior Corridor", "framing-factory-planner", "1-Man Solo", "Pod C (1-Man Solo)", ["E-07"], "06-110 Walls", "Thu Nov 26", 8.5, 8.0, 100, "READY", "Left-end X-and-Go pull sheets verified; Kitchen 109-1/2\" rough cabinet run locked."),
        ScheduleTask("T-104", "JOB-101", "Chop-Saw Header/Shoulder Batch + Stair Stringer Cut", "framing-factory-planner", "1-Man Solo", "Cut Bench / Stairs", ["E-08", "E-11"], "06-120 Stairs/Cut", "Thu Nov 26", 11.0, 10.5, 90, "READY", "Field rise 121-1/4\" verified (1/2\" delta from plan); 16 risers @ 7-7/12\"."),
        ScheduleTask("T-105", "JOB-101", "LIFO Reverse-Staged Floor/Roof Truss Pack Lift", "framing-factory-planner", "Full-Crew", "Material / SkyTrak", ["E-09", "E-12", "E-02", "E-04"], "06-115 Roof/Truss", "Fri Nov 27", 18.0, 4.0, 20, "READY", "4-6 pack trusses reverse-staged North->South; ground gable ends ready to boom.", required_cert="SkyTrak/Telehandler"),
        ScheduleTask("T-201", "JOB-102", "Floor 7 Commercial Window Set (32 Units)", "highrise-window-tracker", "2-Man Team", "Window Set Crew", ["E-03", "E-13", "E-14"], "08-500 Windows", "Thu Nov 26", 24.0, 22.0, 88, "READY", "All Floor 7 pallets hoisted from Room B dispatch rows into clear floor staging bay.", required_cert="Aerial Lift"),
        ScheduleTask("T-202", "JOB-102", "Floor 6 Caulk/Drywall-Ready + Foreman 2nd Verify", "highrise-window-tracker", "2-Man Team", "Caulk / Drywall-Ready", ["E-15", "E-17"], "08-510 Envelope", "Thu Nov 26", 16.0, 17.0, 95, "READY", "30/32 units drywall-ready; 2 touch-up units queued for Foreman Verify #2."),
        ScheduleTask("T-203", "JOB-102", "Room A -> Room B Weekly Pallet Pull (Floors 8-9)", "highrise-window-tracker", "Logistics", "2,000 SF Warehouse", ["E-16"], "01-500 Staging", "Fri Nov 27", 8.0, 6.0, 75, "WATCH", "Row A-R1 full (8/8 pallets deep); pull 6 pallets through Room A-B transfer opening.", required_cert="SkyTrak/Telehandler"),
        ScheduleTask("T-301", "JOB-103", "Lake DuBay Ridge Beam Set & Timber Porch Roof", "crew-command", "Full-Crew", "Lake DuBay Framing", ["E-19", "E-20", "E-21"], "06-115 Roof/Truss", "Fri Nov 27", 20.0, 6.0, 25, "BLOCKED", "BLOCKED: 3-ply LVL ridge beam delayed at lumber yard (ETA Fri 07:30 AM). Crew re-tasked to interior partitions."),
    ]


def validate_cert_assignments(roster: List[CrewMember], tasks: List[ScheduleTask]) -> List[Dict[str, str]]:
    """Flag any scheduled task where an assigned worker lacks a required ticket or has an expired cert."""
    by_id = {m.emp_id: m for m in roster}
    violations: List[Dict[str, str]] = []
    for t in tasks:
        if not t.required_cert:
            continue
        # For Full-Crew/Lift tasks, verify at least one assigned lead/operator holds the ticket
        holders = [
            by_id[eid] for eid in t.assigned_emp_ids
            if eid in by_id and t.required_cert in by_id[eid].certs
        ]
        if not holders:
            violations.append(
                {
                    "severity": "BLOCK",
                    "task_id": t.task_id,
                    "message": f"{t.task_id} ({t.title}) requires '{t.required_cert}' — NO assigned crew member holds this ticket.",
                }
            )
    for m in roster:
        for alert in m.cert_alerts:
            sev = "BLOCK" if "EXPIRED" in alert.upper() else "WARN"
            violations.append(
                {
                    "severity": sev,
                    "task_id": m.emp_id,
                    "message": f"{m.name} ({m.emp_id}): {alert}",
                }
            )
    return violations


def summarize_corporate_kpis(
    jobsites: List[Jobsite],
    roster: List[CrewMember],
    tasks: List[ScheduleTask],
    compliance_alerts: List[Dict[str, str]],
) -> Dict[str, Any]:
    total_crew = len(roster)
    on_site = sum(1 for m in roster if m.status in ("ON_SITE", "REASSIGNED"))
    late = sum(1 for m in roster if m.status == "LATE")
    out = sum(1 for m in roster if m.status == "OUT")

    total_st = round(sum(m.st_hrs for m in roster), 2)
    total_ot = round(sum(m.ot_hrs for m in roster), 2)
    ot_risk_count = sum(1 for m in roster if m.total_week_hrs >= 36.0)
    total_gross = round(sum(m.gross_wages for m in roster), 2)
    total_burdened = round(sum(m.burdened_cost for m in roster), 2)

    budget_hrs = round(sum(t.budget_hrs for t in tasks), 2)
    earned_hrs = round(sum(t.earned_hrs for t in tasks), 2)
    actual_hrs = round(sum(t.actual_hrs for t in tasks), 2)
    prod_index = round(earned_hrs / actual_hrs, 3) if actual_hrs > 0 else 1.0

    blocked_gates = sum(1 for t in tasks if t.material_gate == "BLOCKED")
    watch_gates = sum(1 for t in tasks if t.material_gate == "WATCH")

    # Cost-code rollup for Corporate Office / QuickBooks
    cc_rollup: Dict[str, Dict[str, Any]] = {}
    for m in roster:
        bucket = cc_rollup.setdefault(
            m.cost_code,
            {"cost_code": m.cost_code, "headcount": 0, "st_hrs": 0.0, "ot_hrs": 0.0, "gross_wages": 0.0, "burdened_cost": 0.0},
        )
        bucket["headcount"] += 1
        bucket["st_hrs"] = round(bucket["st_hrs"] + m.st_hrs, 2)
        bucket["ot_hrs"] = round(bucket["ot_hrs"] + m.ot_hrs, 2)
        bucket["gross_wages"] = round(bucket["gross_wages"] + m.gross_wages, 2)
        bucket["burdened_cost"] = round(bucket["burdened_cost"] + m.burdened_cost, 2)

    # Jobsite labor rollup
    job_rollup: Dict[str, Dict[str, Any]] = {}
    for j in jobsites:
        jm = [m for m in roster if m.job_id == j.job_id]
        jt = [t for t in tasks if t.job_id == j.job_id]
        j_earned = round(sum(t.earned_hrs for t in jt), 2)
        j_actual = round(sum(t.actual_hrs for t in jt), 2)
        job_rollup[j.job_id] = {
            "job_id": j.job_id,
            "name": j.name,
            "headcount": len(jm),
            "on_site": sum(1 for m in jm if m.status in ("ON_SITE", "LATE", "REASSIGNED")),
            "weekly_burdened_cost": round(sum(m.burdened_cost for m in jm), 2),
            "earned_hrs": j_earned,
            "actual_hrs": j_actual,
            "variance_hrs": round(j_earned - j_actual, 2),
            "material_status": j.material_status,
        }

    return {
        "total_crew": total_crew,
        "on_site": on_site,
        "late": late,
        "out": out,
        "total_st_hrs": total_st,
        "total_ot_hrs": total_ot,
        "ot_risk_count": ot_risk_count,
        "total_gross_wages": total_gross,
        "total_burdened_cost": total_burdened,
        "burden_multiplier": BURDEN_MULTIPLIER,
        "scheduled_budget_hrs": budget_hrs,
        "earned_hrs": earned_hrs,
        "actual_hrs": actual_hrs,
        "productivity_index": prod_index,
        "blocked_material_gates": blocked_gates,
        "watch_material_gates": watch_gates,
        "compliance_alert_count": len(compliance_alerts),
        "cost_code_rollup": sorted(cc_rollup.values(), key=lambda x: x["cost_code"]),
        "job_rollup": list(job_rollup.values()),
    }


def export_payroll_csv(roster: List[CrewMember], csv_path: Path = EXPORTS_DIR / "quickbooks_payroll_export.csv") -> Path:
    """Export QuickBooks / Corporate Payroll-ready CSV by Employee, Job ID, and Cost Code."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "emp_id",
                "employee_name",
                "role",
                "job_id",
                "cost_code",
                "status",
                "base_rate",
                "st_hrs",
                "ot_hrs",
                "total_week_hrs",
                "gross_wages",
                "burdened_cost_1_28x",
            ]
        )
        for m in roster:
            w.writerow(
                [
                    m.emp_id,
                    m.name,
                    m.role,
                    m.job_id,
                    m.cost_code,
                    m.status,
                    f"{m.base_rate:.2f}",
                    f"{m.st_hrs:.2f}",
                    f"{m.ot_hrs:.2f}",
                    f"{m.total_week_hrs:.2f}",
                    f"{m.gross_wages:.2f}",
                    f"{m.burdened_cost:.2f}",
                ]
            )
    return csv_path


def export_suite_json(json_path: Path = DOCS_DIR / "crew_data.json") -> Dict[str, Any]:
    ctx = load_sibling_suite_context()
    jobsites = build_default_jobsites(ctx)
    roster = build_default_roster()
    tasks = build_default_schedule()
    compliance_alerts = validate_cert_assignments(roster, tasks)
    kpis = summarize_corporate_kpis(jobsites, roster, tasks, compliance_alerts)
    payroll_csv = export_payroll_csv(roster)

    payload = {
        "suite_name": "Crew Command & Corporate Office Hub (15–30 Man Framing Suite)",
        "as_of": "Thursday, Nov 26, 2026 (End-of-Day Field -> Corporate Sync)",
        "prototype_notice": (
            "PROTOTYPE & ORIGIN NOTE: Built by James M. Doyle (UBC Local 1781 Journeyman Carpenter; "
            "Founder of Doyle's Contracting LLC, 2015–2021) to unify personnel, schedule, material gates, "
            "and corporate job costing across Framing Factory Planner and High-Rise Window Tracker."
        ),
        "suite_links": SUITE_LINKS,
        "suite_context": ctx,
        "kpis": kpis,
        "jobsites": [asdict(j) for j in jobsites],
        "roster": [m.to_dict() for m in roster],
        "schedule": [t.to_dict() for t in tasks],
        "compliance_alerts": compliance_alerts,
        "payroll_export_file": str(payroll_csv.name),
    }

    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    data = export_suite_json()
    k = data["kpis"]
    print(f"Crew Command Export Complete -> {DOCS_DIR / 'crew_data.json'}")
    print(
        f"Crew: {k['on_site']}/{k['total_crew']} active | ST: {k['total_st_hrs']}h | OT: {k['total_ot_hrs']}h | "
        f"Weekly Burdened Labor: ${k['total_burdened_cost']:,.2f} | Prod Index: {k['productivity_index']:.2f}x"
    )
    print(
        f"Suite Links -> Framing Connected: {data['suite_context']['framing_connected']} | "
        f"Window Tracker Connected: {data['suite_context']['window_connected']}"
    )
