# Crew Command & Corporate Office Hub — 15–30 Man Framing & Field Operations Suite

**"Connect the blueprint pull sheets, material staging gates, and a 15–30 man framing crew directly to Corporate Office job costing, QuickBooks payroll, Procore, and Bluebeam."**

Created by **James M. Doyle** (UBC Local 1781 Journeyman Carpenter; Founder of Doyle's Contracting LLC, 2015–2021, 100+ residential & commercial projects).

> **Prototype & Field-Testing Notice:** This repository and Progressive Web App suite reconstruct the field-to-office crew dispatch, timekeeping, job-costing, and daily reporting workflow built from my 15+ years of residential and commercial carpentry experience and 6+ years running Doyle's Contracting LLC (2015–2021). It is built with zero external dependencies so employers and contractors can test both the Mobile Foreman PWA and Corporate Office Dashboard immediately.

---

## The Connected 3-App Jobsite Operations Suite

| App | Focus | Live Link / Role |
| :--- | :--- | :--- |
| **1. Blueprint & Pre-Staging** | Material cut sheets, left-end X-and-Go tape pulls, wall IDs (`W-1`–`W-8`), stairs, staging zones, and `1-Man / 2-Man / Full-Crew` goal hours | [framing-factory-planner](https://jimboskipe.github.io/framing-factory-planner/) |
| **2. Foreman Material & QC** | 2,000 SF sorting warehouse (`9'` pitch, `8` deep) -> floor/jobsite staging -> set/caulk -> 1st/2nd/3rd foreman verify -> GC turnover | [highrise-window-tracker](https://jimboskipe.github.io/highrise-window-tracker/) |
| **3. Personnel, Schedule & Corporate Office** *(this repo)* | 22-man framing roster (scalable 15–30), mobile roll call, weekly OT warnings (`>=36h`), equipment ticket enforcement (`SkyTrak/Lift`), material-blocked schedule gates, burdened job costing (`1.28x`), QuickBooks payroll CSV, and Procore + Bluebeam sync | `docs/index.html` (Mobile PWA) & `docs/office.html` (Corporate Dashboard) |

---

## Enterprise Workflow: Connecting Procore & Bluebeam

```text
[Bluebeam Revu / Studio]
   │  Markups Summary CSV / Studio Prime API (Wall IDs, Window Tags, QC Pins)
   ▼
[Framing Factory Planner] + [High-Rise Window Tracker]
   │  Task Budget Hours, Bidding Tiers & Material-Ready Gates (JSON)
   ▼
[Crew Command Mobile PWA]  <── Morning Roll Call, Pod Dispatch, % Complete, Holds
   │  End-of-Day Field Daily Report Sync
   ▼
[Corporate Office Dashboard]
   ├──► Procore REST API v1.0 (Manpower Logs, Timecards by Cost Code, Delay Logs)
   ├──► QuickBooks / Payroll CSV (Employee ST/OT Hours + 1.28x Burdened Job Cost)
   └──► Bluebeam Status CSV (Round-trip Completed / Hold-Material statuses to PDFs)
```

---

## Run Locally (Python 3.9+, Standard Library Only)

```powershell
python build_suite_apps.py                   # export crew_data.json, Procore/Bluebeam/QB files & build docs/
python -m unittest discover -s tests -v      # run automated unit tests
```
