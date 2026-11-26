"""Unit tests for Crew Command & Corporate Office Hub + Procore/Bluebeam adapters."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import crew_engine as ce
import integrations as integ


class TestCrewCommandSuite(unittest.TestCase):
    def test_overtime_and_burdened_cost_math(self) -> None:
        m = ce.CrewMember(
            emp_id="E-99",
            name="Test Framer",
            role="Journeyman",
            skill_tier="Journeyman",
            job_id="JOB-101",
            pod="Pod A",
            base_rate=40.0,
            week_hrs_prior=34.0,
            today_hrs=10.0,
            cost_code="06-110 Walls",
            status="ON_SITE",
            certs=["Fall Protection"],
        )
        self.assertEqual(m.total_week_hrs, 44.0)
        self.assertEqual(m.st_hrs, 40.0)
        self.assertEqual(m.ot_hrs, 4.0)
        # 40*40 + 4*40*1.5 = 1600 + 240 = 1840
        self.assertAlmostEqual(m.gross_wages, 1840.0, places=2)
        self.assertAlmostEqual(m.burdened_cost, round(1840.0 * ce.BURDEN_MULTIPLIER, 2), places=2)

    def test_expired_and_missing_cert_detection(self) -> None:
        roster = [
            ce.CrewMember("E-1", "Uncertified Worker", "Apprentice", "Apprentice", "JOB-101", "Pod A", 24.0, 20.0, 8.0, "06-110", "ON_SITE", ["Fall Protection"], ["Aerial Lift EXPIRED"]),
        ]
        tasks = [
            ce.ScheduleTask("T-1", "JOB-101", "Truss Lift", "framing-factory-planner", "Full-Crew", "Pod A", ["E-1"], "06-115", "Fri", 8.0, 0.0, 0, "READY", "OK", required_cert="SkyTrak/Telehandler"),
        ]
        alerts = ce.validate_cert_assignments(roster, tasks)
        severities = [a["severity"] for a in alerts]
        self.assertEqual(severities.count("BLOCK"), 2)

    def test_default_22_man_roster_and_exports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            data = ce.export_suite_json(tmp_path / "crew_data.json")
            self.assertEqual(data["kpis"]["total_crew"], 22)
            self.assertGreaterEqual(data["kpis"]["total_crew"], 15)
            self.assertLessEqual(data["kpis"]["total_crew"], 30)
            self.assertGreater(data["kpis"]["total_burdened_cost"], 0)
            self.assertEqual(data["kpis"]["blocked_material_gates"], 1)

            # Procore payload schema checks
            procore = integ.build_procore_sync_payload(data, sync_date="2026-11-26")
            self.assertEqual(procore["summary"]["manpower_logs_count"], 3)
            self.assertEqual(procore["summary"]["timecard_entries_count"], 21)  # 1 worker OUT (0 hrs)
            self.assertGreaterEqual(procore["summary"]["delay_logs_count"], 1)

            # Bluebeam CSV round-trip
            bb_csv = integ.export_bluebeam_markups_csv(data, tmp_path / "bb.csv")
            parsed = integ.parse_bluebeam_markups_csv(bb_csv)
            self.assertEqual(len(parsed), len(data["schedule"]))
            self.assertTrue(any(r["status"] == "Hold - Material" for r in parsed))


if __name__ == "__main__":
    unittest.main()
