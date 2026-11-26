"""Build both synchronized Crew Command UIs:
  1. docs/index.html   -> 430px Mobile Foreman Field PWA (Roll Call, Dispatch, Schedule, Office Sync)
  2. docs/office.html  -> Wide Corporate Office Command Dashboard (Job Costing, Certs, Procore/Bluebeam)
  3. docs/manifest.json -> PWA manifest
"""

from __future__ import annotations

import json
from pathlib import Path
import crew_engine as ce
import integrations as integ

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"


def write_manifest() -> None:
    manifest = {
        "name": "Crew Command — Field & Office Suite",
        "short_name": "Crew Command",
        "start_url": "./index.html",
        "display": "standalone",
        "background_color": "#020617",
        "theme_color": "#0f172a",
    }
    (DOCS / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def build_mobile_pwa(data: dict, procore_payload: dict) -> Path:
    data_js = json.dumps(data)
    procore_js = json.dumps(procore_payload)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<meta name="theme-color" content="#0f172a">
<title>Crew Command — Mobile Foreman App (15–30 Man Suite)</title>
<link rel="manifest" href="manifest.json">
<style>
  :root {{
    --bg:#020617; --phone:#0f172a; --card:#1e293b; --border:#334155;
    --text:#f8fafc; --muted:#94a3b8; --accent:#10b981; --orange:#ea580c;
    --blue:#0284c7; --amber:#f59e0b; --red:#ef4444;
  }}
  * {{ box-sizing:border-box; -webkit-tap-highlight-color:transparent; }}
  body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:var(--bg); color:var(--text); display:flex; justify-content:center; }}
  .phone {{ width:100%; max-width:430px; min-height:100vh; background:var(--phone); border-left:1px solid #1e293b; border-right:1px solid #1e293b; padding-bottom:78px; }}
  header {{ background:#020617; border-bottom:2px solid var(--accent); padding:11px 13px; position:sticky; top:0; z-index:20; display:flex; justify-content:space-between; align-items:center; gap:8px; }}
  h1 {{ margin:0; font-size:15px; letter-spacing:0.2px; }}
  .sub {{ font-size:10.5px; color:var(--muted); }}
  .office-link {{ background:#1d4ed8; color:#fff; text-decoration:none; padding:7px 10px; border-radius:7px; font-size:11.5px; font-weight:800; white-space:nowrap; }}
  .content {{ padding:12px; }}
  .kpi-grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:6px; margin-bottom:10px; }}
  .kpi {{ background:var(--card); border:1px solid var(--border); border-radius:8px; padding:7px; text-align:center; }}
  .kpi .l {{ font-size:9.5px; color:var(--muted); text-transform:uppercase; font-weight:700; }}
  .kpi .v {{ font-size:16px; font-weight:900; color:#34d399; margin-top:2px; }}
  .kpi.warn .v {{ color:#fbbf24; }}
  .kpi.bad .v {{ color:#f87171; }}
  .strip {{ display:flex; overflow-x:auto; gap:6px; padding-bottom:8px; margin-bottom:8px; }}
  .pill {{ flex:0 0 auto; padding:7px 11px; border-radius:8px; border:1.5px solid var(--border); background:var(--card); color:var(--text); font-weight:800; font-size:12px; cursor:pointer; }}
  .pill.active {{ border-color:var(--accent); background:#020617; color:#34d399; }}
  .card {{ background:var(--card); border:1px solid var(--border); border-radius:9px; padding:10px 11px; margin-bottom:8px; font-size:12.5px; }}
  .row {{ display:flex; justify-content:space-between; align-items:center; gap:6px; }}
  .name {{ font-weight:800; font-size:13.5px; }}
  .meta {{ font-size:11px; color:var(--muted); margin-top:2px; }}
  .badge {{ display:inline-block; padding:2px 7px; border-radius:5px; font-size:10.5px; font-weight:800; }}
  .b-ok {{ background:rgba(16,185,129,0.2); color:#6ee7b7; border:1px solid #10b981; }}
  .b-warn {{ background:rgba(245,158,11,0.2); color:#fde68a; border:1px solid #f59e0b; }}
  .b-bad {{ background:rgba(239,68,68,0.22); color:#fca5a5; border:1px solid #ef4444; }}
  .b-blu {{ background:rgba(2,132,199,0.22); color:#7dd3fc; border:1px solid #0284c7; }}
  .st-btns {{ display:grid; grid-template-columns:repeat(4,1fr); gap:4px; margin-top:7px; }}
  .sbtn {{ border:1px solid var(--border); background:#020617; color:var(--muted); border-radius:6px; padding:6px 2px; font-size:10.5px; font-weight:800; cursor:pointer; }}
  .sbtn.on {{ background:#065f46; border-color:#10b981; color:#fff; }}
  .sbtn.late {{ background:#92400e; border-color:#f59e0b; color:#fff; }}
  .sbtn.out {{ background:#7f1d1d; border-color:#ef4444; color:#fff; }}
  .sbtn.re {{ background:#1e3a8a; border-color:#3b82f6; color:#fff; }}
  .btn {{ width:100%; border:none; border-radius:8px; padding:10px 12px; font-weight:800; font-size:12.5px; cursor:pointer; color:#fff; background:var(--accent); margin-top:7px; }}
  .btn.ora {{ background:var(--orange); }}
  .btn.blu {{ background:var(--blue); }}
  .btn.dark {{ background:#020617; border:1px solid var(--border); color:#e2e8f0; }}
  .link-card {{ display:block; text-decoration:none; color:var(--text); background:#020617; border:1.5px solid var(--border); border-radius:8px; padding:9px 11px; margin-top:6px; }}
  .link-card strong {{ color:#38bdf8; display:block; font-size:12.5px; }}
  .link-card span {{ font-size:11px; color:var(--muted); }}
  .sec {{ font-size:11px; font-weight:800; text-transform:uppercase; letter-spacing:0.6px; color:var(--muted); margin:12px 0 6px; }}
  textarea {{ width:100%; min-height:74px; background:#020617; color:#f8fafc; border:1px solid var(--border); border-radius:7px; padding:8px; font-family:inherit; font-size:12px; }}
  input[type=range] {{ width:100%; accent-color:#10b981; }}
  .bottom-nav {{ position:fixed; bottom:0; width:100%; max-width:430px; background:#020617; border-top:2px solid var(--border); display:grid; grid-template-columns:repeat(4,1fr); z-index:30; }}
  .nav-btn {{ background:none; border:none; color:var(--muted); padding:10px 4px; font-size:11px; font-weight:800; cursor:pointer; }}
  .nav-btn.active {{ color:#fff; background:var(--accent); }}
</style>
</head>
<body>
<div class="phone">
  <header>
    <div>
      <h1>CREW COMMAND</h1>
      <div class="sub">15–30 Man Framing Suite &bull; Field PWA</div>
    </div>
    <a class="office-link" href="office.html">Office View &rarr;</a>
  </header>

  <div class="content">
    <div class="kpi-grid" id="kpiBar"></div>

    <div id="tab-rollcall">
      <div class="strip" id="jobStrip"></div>
      <div id="rosterList"></div>
    </div>

    <div id="tab-dispatch" style="display:none">
      <div class="sec">Connected Field Suite Apps</div>
      <div class="card">
        <div class="meta">Jump straight into pre-staged pull sheets or 4-gate material tracking for today's pods:</div>
        <a class="link-card" href="{data['suite_links']['blueprint_app']}" target="_blank">
          <strong>1. Framing Factory Planner (Blueprint App) &rarr;</strong>
          <span>Left-end X-and-Go pulls, wall sheets (W-1..W-8), cut bench, stairs &amp; goal hours</span>
        </a>
        <a class="link-card" href="{data['suite_links']['foreman_logistics_app']}" target="_blank">
          <strong>2. High-Rise Window Tracker (Foreman Logistics) &rarr;</strong>
          <span>2,000 SF warehouse rows (9' pitch, 8 deep) &rarr; floor staging &rarr; 3-stage GC verify</span>
        </a>
        <a class="link-card" href="office.html">
          <strong>3. Corporate Office Command Dashboard &rarr;</strong>
          <span>Job costing, QuickBooks payroll CSV, Procore REST payload &amp; Bluebeam sync</span>
        </a>
      </div>
      <div class="sec">Active Jobsites &amp; Material Gates</div>
      <div id="jobsList"></div>
    </div>

    <div id="tab-schedule" style="display:none">
      <div class="sec">Live Schedule &amp; Material-Ready Interlocks</div>
      <div id="schedList"></div>
    </div>

    <div id="tab-office" style="display:none">
      <div class="sec">End-of-Day Field Report &rarr; Corporate Office &amp; Procore</div>
      <div class="card" id="fdrSummary"></div>
      <div class="card">
        <label style="font-size:11px;color:#94a3b8;font-weight:800;display:block;margin-bottom:5px;">FOREMAN FIELD NOTES / DELAYS (SENT TO PROCORE DELAY LOG)</label>
        <textarea id="foremanNotes">JOB-101 on track (W-6/W-7 complete, W-2/W-3 95%). JOB-102 Floor 7 window set 88%. JOB-103 ridge LVL delayed until Fri 07:30 AM — crew shifted to interior partitions with zero lost time.</textarea>
        <button class="btn" onclick="downloadPayrollCSV()">Download QuickBooks Payroll CSV</button>
        <button class="btn blu" onclick="downloadProcoreJSON()">Export Procore Daily Sync JSON</button>
        <button class="btn ora" onclick="downloadBluebeamCSV()">Export Bluebeam Markups Status CSV</button>
      </div>
      <div class="sec">Compliance &amp; Ticket Alerts</div>
      <div id="alertsList"></div>
    </div>
  </div>

  <nav class="bottom-nav">
    <button class="nav-btn active" onclick="showTab('rollcall', this)">1. Roll Call</button>
    <button class="nav-btn" onclick="showTab('dispatch', this)">2. Suite/Sites</button>
    <button class="nav-btn" onclick="showTab('schedule', this)">3. Schedule</button>
    <button class="nav-btn" onclick="showTab('office', this)">4. Office Sync</button>
  </nav>
</div>

<script>
const STATE = {data_js};
const PROCORE = {procore_js};
let activeJob = 'ALL';

function showTab(name, btn) {{
  ['rollcall','dispatch','schedule','office'].forEach(t => document.getElementById('tab-'+t).style.display = (t===name?'block':'none'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  renderAll();
}}

function setStatus(empId, st) {{
  const m = STATE.roster.find(x => x.emp_id === empId);
  if (!m) return;
  m.status = st;
  if (st === 'OUT') m.today_hrs = 0;
  else if (m.today_hrs === 0) m.today_hrs = 8.5;
  recalc(m);
  renderAll();
}}

function updatePct(taskId, val) {{
  const t = STATE.schedule.find(x => x.task_id === taskId);
  if (!t) return;
  t.pct_complete = parseInt(val, 10);
  t.earned_hrs = +(t.budget_hrs * (t.pct_complete / 100)).toFixed(2);
  t.variance_hrs = +(t.earned_hrs - t.actual_hrs).toFixed(2);
  renderAll();
}}

function recalc(m) {{
  m.total_week_hrs = +(m.week_hrs_prior + m.today_hrs).toFixed(2);
  m.st_hrs = Math.min(40, m.total_week_hrs);
  m.ot_hrs = Math.max(0, +(m.total_week_hrs - 40).toFixed(2));
  m.gross_wages = +((m.st_hrs * m.base_rate) + (m.ot_hrs * m.base_rate * 1.5)).toFixed(2);
  m.burdened_cost = +(m.gross_wages * 1.28).toFixed(2);
  m.ot_warning = m.total_week_hrs >= 36;
}}

function renderKPIs() {{
  const active = STATE.roster.filter(m => m.status !== 'OUT').length;
  const otWarn = STATE.roster.filter(m => m.total_week_hrs >= 36).length;
  const blocked = STATE.schedule.filter(t => t.material_gate === 'BLOCKED').length;
  const cost = STATE.roster.reduce((a,m) => a + m.burdened_cost, 0);
  const earned = STATE.schedule.reduce((a,t) => a + t.earned_hrs, 0);
  const actual = STATE.schedule.reduce((a,t) => a + t.actual_hrs, 0);
  const cpi = actual > 0 ? (earned / actual).toFixed(2) : '1.00';
  document.getElementById('kpiBar').innerHTML = `
    <div class="kpi"><div class="l">On Site</div><div class="v">${{active}}/${{STATE.roster.length}}</div></div>
    <div class="kpi ${{otWarn>0?'warn':''}}"><div class="l">OT Risk</div><div class="v">${{otWarn}} men</div></div>
    <div class="kpi ${{blocked>0?'bad':''}}"><div class="l">Mat. Holds</div><div class="v">${{blocked}}</div></div>
    <div class="kpi"><div class="l">Wk Labor</div><div class="v">$${{(cost/1000).toFixed(1)}}k</div></div>
    <div class="kpi"><div class="l">Prod CPI</div><div class="v">${{cpi}}x</div></div>
    <div class="kpi warn"><div class="l">Cert Alerts</div><div class="v">${{STATE.compliance_alerts.length}}</div></div>
  `;
}}

function renderRollCall() {{
  const jobs = ['ALL', ...STATE.jobsites.map(j => j.job_id)];
  document.getElementById('jobStrip').innerHTML = jobs.map(j =>
    `<button class="pill ${{activeJob===j?'active':''}}" onclick="activeJob='${{j}}';renderRollCall()">${{j}}</button>`
  ).join('');
  const list = STATE.roster.filter(m => activeJob==='ALL' || m.job_id===activeJob);
  document.getElementById('rosterList').innerHTML = list.map(m => `
    <div class="card">
      <div class="row">
        <div>
          <div class="name">${{m.name}} <span style="color:#64748b;font-size:11px">${{m.emp_id}}</span></div>
          <div class="meta">${{m.role}} &bull; ${{m.job_id}} &bull; ${{m.pod}}</div>
        </div>
        <div style="text-align:right">
          <span class="badge ${{m.ot_hrs>0?'b-bad':(m.ot_warning?'b-warn':'b-ok')}}">${{m.total_week_hrs}}h wk</span>
          <div class="meta">$${{m.base_rate.toFixed(0)}}/hr &bull; ${{m.cost_code.split(' ')[0]}}</div>
        </div>
      </div>
      ${{m.cert_alerts.length ? `<div style="margin-top:5px"><span class="badge b-bad">! ${{m.cert_alerts.join(' | ')}}</span></div>` : ''}}
      <div class="st-btns">
        <button class="sbtn ${{m.status==='ON_SITE'?'on':''}}" onclick="setStatus('${{m.emp_id}}','ON_SITE')">ON SITE</button>
        <button class="sbtn ${{m.status==='LATE'?'late':''}}" onclick="setStatus('${{m.emp_id}}','LATE')">LATE</button>
        <button class="sbtn ${{m.status==='REASSIGNED'?'re':''}}" onclick="setStatus('${{m.emp_id}}','REASSIGNED')">MOVED</button>
        <button class="sbtn ${{m.status==='OUT'?'out':''}}" onclick="setStatus('${{m.emp_id}}','OUT')">OUT</button>
      </div>
    </div>
  `).join('');
}}

function renderJobs() {{
  document.getElementById('jobsList').innerHTML = STATE.jobsites.map(j => {{
    const cnt = STATE.roster.filter(m => m.job_id===j.job_id && m.status!=='OUT').length;
    const bc = j.material_status==='READY'?'b-ok':(j.material_status==='WATCH'?'b-warn':'b-bad');
    return `
      <div class="card">
        <div class="row">
          <div class="name">${{j.job_id}} — ${{j.name}}</div>
          <span class="badge ${{bc}}">${{j.material_status}}</span>
        </div>
        <div class="meta">${{j.location}} &bull; Foreman: ${{j.foreman}} &bull; Active Crew: ${{cnt}}</div>
        <div class="meta" style="color:#cbd5e1;margin-top:5px">${{j.notes}}</div>
        <a class="link-card" href="${{j.linked_url}}" target="_blank"><strong>Open ${{j.linked_app}} &rarr;</strong><span>View live drawings, pull sheets &amp; material staging</span></a>
      </div>
    `;
  }}).join('');
}}

function renderSchedule() {{
  document.getElementById('schedList').innerHTML = STATE.schedule.map(t => {{
    const bc = t.material_gate==='READY'?'b-ok':(t.material_gate==='WATCH'?'b-warn':'b-bad');
    const vc = t.variance_hrs >= 0 ? '#4ade80' : '#f87171';
    return `
      <div class="card">
        <div class="row">
          <div class="name">${{t.task_id}}: ${{t.title}}</div>
          <span class="badge ${{bc}}">${{t.material_gate}}</span>
        </div>
        <div class="meta">${{t.job_id}} &bull; ${{t.scheduled_day}} &bull; ${{t.bidding_tier}} (${{t.assigned_pod}})</div>
        <div class="meta" style="color:#cbd5e1;margin-top:4px">${{t.material_note}}</div>
        <div class="row" style="margin-top:7px">
          <span class="meta">Budget: <b>${{t.budget_hrs}}h</b> | Actual: <b>${{t.actual_hrs}}h</b> | Var: <b style="color:${{vc}}">${{t.variance_hrs>=0?'+':''}}${{t.variance_hrs}}h</b></span>
          <span class="badge b-blu">${{t.pct_complete}}%</span>
        </div>
        <input type="range" min="0" max="100" step="5" value="${{t.pct_complete}}" oninput="updatePct('${{t.task_id}}', this.value)">
      </div>
    `;
  }}).join('');
}}

function renderOfficeTab() {{
  const active = STATE.roster.filter(m => m.status !== 'OUT').length;
  const totalToday = STATE.roster.reduce((a,m) => a + m.today_hrs, 0).toFixed(1);
  const burden = STATE.roster.reduce((a,m) => a + m.burdened_cost, 0);
  document.getElementById('fdrSummary').innerHTML = `
    <div class="name">Daily Sync Ready — ${{STATE.as_of}}</div>
    <div class="meta" style="margin-top:4px">Headcount: <b>${{active}}/${{STATE.roster.length}}</b> &bull; Today Man-Hours: <b>${{totalToday}}h</b> &bull; Weekly Burdened Labor: <b>$${{burden.toLocaleString('en-US',{{minimumFractionDigits:2}})}}</b></div>
    <div class="meta" style="margin-top:4px">Procore Queue: <b>${{PROCORE.summary.manpower_logs_count}}</b> Manpower Logs &bull; <b>${{PROCORE.summary.timecard_entries_count}}</b> Timecards &bull; <b>${{PROCORE.summary.delay_logs_count}}</b> Delay Logs</div>
  `;
  document.getElementById('alertsList').innerHTML = STATE.compliance_alerts.map(a =>
    `<div class="card"><span class="badge ${{a.severity==='BLOCK'?'b-bad':'b-warn'}}">${{a.severity}}</span> <span style="margin-left:5px">${{a.message}}</span></div>`
  ).join('');
}}

function dl(filename, text, mime) {{
  const blob = new Blob([text], {{type: mime}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
}}

function downloadPayrollCSV() {{
  const hdr = ['emp_id','name','role','job_id','cost_code','status','base_rate','st_hrs','ot_hrs','total_week_hrs','gross_wages','burdened_cost'];
  const rows = STATE.roster.map(m => [m.emp_id, `"${{m.name}}"`, `"${{m.role}}"`, m.job_id, `"${{m.cost_code}}"`, m.status, m.base_rate, m.st_hrs, m.ot_hrs, m.total_week_hrs, m.gross_wages, m.burdened_cost].join(','));
  dl('quickbooks_payroll_export.csv', [hdr.join(','), ...rows].join('\\n'), 'text/csv');
}}

function downloadProcoreJSON() {{
  const copy = JSON.parse(JSON.stringify(PROCORE));
  copy.foreman_eod_note = document.getElementById('foremanNotes').value;
  dl('procore_daily_sync_payload.json', JSON.stringify(copy, null, 2), 'application/json');
}}

function downloadBluebeamCSV() {{
  const hdr = ['Subject','Page Label','Label','Author','Status','Cost Code','Budget Hrs','Actual Hrs','Pct Complete','Comments'];
  const rows = STATE.schedule.map(t => [t.source_app, t.job_id, t.task_id, `"${{t.assigned_pod}}"`, t.pct_complete>=100?'Completed':(t.material_gate==='BLOCKED'?'Hold - Material':'In Progress'), `"${{t.cost_code}}"`, t.budget_hrs, t.actual_hrs, t.pct_complete+'%', `"${{t.title}}"`].join(','));
  dl('bluebeam_markups_sync.csv', [hdr.join(','), ...rows].join('\\n'), 'text/csv');
}}

function renderAll() {{ renderKPIs(); renderRollCall(); renderJobs(); renderSchedule(); renderOfficeTab(); }}
renderAll();
</script>
</body>
</html>
"""
    out = DOCS / "index.html"
    out.write_text(html, encoding="utf-8")
    return out


def build_office_dashboard(data: dict, procore_payload: dict) -> Path:
    data_js = json.dumps(data)
    procore_js = json.dumps(procore_payload)
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Corporate Office Command Dashboard — 15–30 Man Framing &amp; Construction Suite</title>
<style>
  :root {{
    --bg:#020617; --panel:#0f172a; --card:#1e293b; --border:#334155;
    --text:#f8fafc; --muted:#94a3b8; --green:#10b981; --blue:#38bdf8; --orange:#ea580c; --amber:#f59e0b; --red:#ef4444;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:var(--bg); color:var(--text); }}
  header {{ background:#0f172a; border-bottom:2px solid var(--green); padding:16px 26px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; }}
  h1 {{ margin:0; font-size:20px; }}
  .sub {{ font-size:12.5px; color:var(--muted); margin-top:3px; }}
  .nav-links {{ display:flex; gap:8px; flex-wrap:wrap; }}
  .nbtn {{ text-decoration:none; color:#fff; background:#1e293b; border:1px solid var(--border); padding:8px 13px; border-radius:7px; font-size:12.5px; font-weight:700; cursor:pointer; }}
  .nbtn.primary {{ background:#10b981; border-color:#10b981; color:#022c22; }}
  .nbtn.blue {{ background:#0284c7; border-color:#0284c7; }}
  .nbtn.ora {{ background:#ea580c; border-color:#ea580c; }}
  main {{ max-width:1360px; margin:0 auto; padding:20px 24px 48px; }}
  .kpis {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; margin-bottom:20px; }}
  .kpi {{ background:var(--panel); border:1px solid var(--border); border-radius:10px; padding:14px; }}
  .kpi .l {{ font-size:11px; text-transform:uppercase; color:var(--muted); font-weight:800; letter-spacing:0.5px; }}
  .kpi .v {{ font-size:24px; font-weight:900; color:#34d399; margin-top:4px; }}
  .kpi .s {{ font-size:11.5px; color:var(--muted); margin-top:3px; }}
  .grid-2 {{ display:grid; grid-template-columns:1.2fr 1fr; gap:16px; margin-bottom:18px; }}
  @media (max-width: 960px) {{ .grid-2 {{ grid-template-columns:1fr; }} }}
  .panel {{ background:var(--panel); border:1px solid var(--border); border-radius:10px; padding:16px; margin-bottom:18px; }}
  h2 {{ margin:0 0 10px; font-size:15px; color:#e2e8f0; border-bottom:1px solid var(--border); padding-bottom:7px; }}
  table {{ width:100%; border-collapse:collapse; font-size:12.5px; }}
  th {{ text-align:left; background:#020617; color:#94a3b8; padding:8px; font-size:11px; text-transform:uppercase; }}
  td {{ padding:8px; border-bottom:1px solid #1e293b; }}
  tr:hover td {{ background:rgba(30,41,59,0.45); }}
  .badge {{ display:inline-block; padding:2px 8px; border-radius:5px; font-size:11px; font-weight:800; }}
  .b-ok {{ background:rgba(16,185,129,0.2); color:#6ee7b7; border:1px solid #10b981; }}
  .b-warn {{ background:rgba(245,158,11,0.2); color:#fde68a; border:1px solid #f59e0b; }}
  .b-bad {{ background:rgba(239,68,68,0.22); color:#fca5a5; border:1px solid #ef4444; }}
  .suite-flow {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:12px; }}
  .flow-box {{ background:#020617; border:1.5px solid var(--border); border-radius:9px; padding:12px; }}
  .flow-box h3 {{ margin:0 0 6px; font-size:13.5px; color:var(--blue); }}
  .flow-box p {{ margin:0 0 8px; font-size:12px; color:#cbd5e1; line-height:1.45; }}
  .flow-box a {{ color:#34d399; font-weight:700; font-size:12px; text-decoration:none; }}
  pre {{ background:#020617; border:1px solid var(--border); border-radius:8px; padding:12px; overflow:auto; max-height:240px; font-size:11.5px; color:#bae6fd; }}
</style>
</head>
<body>
<header>
  <div>
    <h1>CORPORATE OFFICE COMMAND — 15–30 MAN FRAMING &amp; FIELD SUITE</h1>
    <div class="sub">Unified Personnel, Schedule, Material Gates, Job Costing, QuickBooks Payroll &amp; Procore / Bluebeam Sync &bull; Built by James M. Doyle</div>
  </div>
  <div class="nav-links">
    <a class="nbtn primary" href="index.html">&larr; Mobile Foreman App</a>
    <a class="nbtn" href="{data['suite_links']['blueprint_app']}" target="_blank">Blueprint App</a>
    <a class="nbtn" href="{data['suite_links']['foreman_logistics_app']}" target="_blank">Window Logistics App</a>
    <button class="nbtn blue" onclick="dlPayroll()">Export QuickBooks CSV</button>
    <button class="nbtn ora" onclick="dlProcore()">Export Procore JSON</button>
  </div>
</header>

<main>
  <div class="kpis" id="kpiStrip"></div>

  <div class="panel">
    <h2>Connected 3-App Field Suite + Enterprise Procore &amp; Bluebeam Workflow</h2>
    <div class="suite-flow">
      <div class="flow-box">
        <h3>1. Bluebeam Revu &rarr; Blueprint App</h3>
        <p>Architectural PDF markups &amp; takeoffs feed pre-staged left-end tape pulls, wall IDs (W-1..W-8), cut bench batches, and 1-Man / 2-Man / Full-Crew bid hours.</p>
        <a href="{data['suite_links']['blueprint_app']}" target="_blank">Open Framing Factory Planner &rarr;</a>
      </div>
      <div class="flow-box">
        <h3>2. Warehouse &amp; Material Gate App</h3>
        <p>Tracks 2,000 SF sorting warehouse (9' pitch, 8 deep) &rarr; jobsite/floor staging &rarr; Set &amp; Caulk &rarr; Foreman 1st/2nd/3rd verify before GC hand-in.</p>
        <a href="{data['suite_links']['foreman_logistics_app']}" target="_blank">Open High-Rise Window Tracker &rarr;</a>
      </div>
      <div class="flow-box">
        <h3>3. Crew Command (Personnel &amp; Schedule)</h3>
        <p>22-man framing roster, mobile roll call, weekly OT guardrails (&gt;36h), equipment ticket checks (SkyTrak/Lift), and material-blocked task interlocks.</p>
        <a href="index.html">Open Mobile Foreman PWA &rarr;</a>
      </div>
      <div class="flow-box">
        <h3>4. Corporate Office &rarr; Procore / QuickBooks</h3>
        <p>Converts daily field updates into QuickBooks payroll CSV (1.28x burdened labor by cost code), Procore REST v1.0 Manpower/Timecard/Delay payloads &amp; Bluebeam status CSV.</p>
        <a href="#procoreBox">Inspect Live Procore Payload &darr;</a>
      </div>
    </div>
  </div>

  <div class="grid-2">
    <div class="panel">
      <h2>Job Costing &amp; Earned-Value Variance by Jobsite</h2>
      <table id="jobTable"></table>
    </div>
    <div class="panel">
      <h2>Weekly Labor Burn by Cost Code (QuickBooks Ready)</h2>
      <table id="ccTable"></table>
    </div>
  </div>

  <div class="panel">
    <h2>22-Man Crew Roster — Live Attendance, OT Risk &amp; Equipment Tickets</h2>
    <table id="rosterTable"></table>
  </div>

  <div class="panel" id="procoreBox">
    <h2>Live Procore REST v1.0 Sync Preview &amp; Compliance Alerts</h2>
    <div id="alertsBox" style="margin-bottom:10px"></div>
    <pre id="procorePre"></pre>
  </div>
</main>

<script>
const D = {data_js};
const P = {procore_js};
const k = D.kpis;

document.getElementById('kpiStrip').innerHTML = `
  <div class="kpi"><div class="l">Active Field Crew</div><div class="v">${{k.on_site + k.late}} / ${{k.total_crew}}</div><div class="s">${{k.late}} Late &bull; ${{k.out}} Out</div></div>
  <div class="kpi"><div class="l">Weekly Burdened Labor</div><div class="v">$${{k.total_burdened_cost.toLocaleString('en-US',{{maximumFractionDigits:0}})}}</div><div class="s">Gross $${{k.total_gross_wages.toLocaleString('en-US',{{maximumFractionDigits:0}})}} &times; ${{k.burden_multiplier}}x load</div></div>
  <div class="kpi"><div class="l">Straight / Overtime Hrs</div><div class="v">${{k.total_st_hrs}}h / ${{k.total_ot_hrs}}h</div><div class="s">${{k.ot_risk_count}} crew at &ge;36h OT watch</div></div>
  <div class="kpi"><div class="l">Field Productivity (CPI)</div><div class="v">${{k.productivity_index.toFixed(2)}}x</div><div class="s">Earned ${{k.earned_hrs}}h vs Actual ${{k.actual_hrs}}h</div></div>
  <div class="kpi"><div class="l">Material Gates</div><div class="v" style="color:${{k.blocked_material_gates>0?'#f87171':'#34d399'}}">${{k.blocked_material_gates}} Blocked</div><div class="s">${{k.watch_material_gates}} Watch &bull; Auto-logged to Procore</div></div>
  <div class="kpi"><div class="l">Ticket / Cert Alerts</div><div class="v" style="color:#fbbf24">${{k.compliance_alert_count}}</div><div class="s">SkyTrak / Lift gate enforcement</div></div>
`;

document.getElementById('jobTable').innerHTML = `
  <thead><tr><th>Job</th><th>Crew</th><th>Earned / Actual</th><th>Variance</th><th>Wk Burdened</th><th>Materials</th></tr></thead>
  <tbody>${{k.job_rollup.map(j => `
    <tr>
      <td><b>${{j.job_id}}</b><br><span style="color:#94a3b8;font-size:11px">${{j.name}}</span></td>
      <td>${{j.on_site}}/${{j.headcount}}</td>
      <td>${{j.earned_hrs}}h / ${{j.actual_hrs}}h</td>
      <td style="font-weight:800;color:${{j.variance_hrs>=0?'#4ade80':'#f87171'}}">${{j.variance_hrs>=0?'+':''}}${{j.variance_hrs}}h</td>
      <td>$${{j.weekly_burdened_cost.toLocaleString('en-US',{{minimumFractionDigits:2}})}}</td>
      <td><span class="badge ${{j.material_status==='READY'?'b-ok':(j.material_status==='WATCH'?'b-warn':'b-bad')}}">${{j.material_status}}</span></td>
    </tr>`).join('')}}</tbody>
`;

document.getElementById('ccTable').innerHTML = `
  <thead><tr><th>Cost Code</th><th>Men</th><th>ST Hrs</th><th>OT Hrs</th><th>Burdened Cost</th></tr></thead>
  <tbody>${{k.cost_code_rollup.map(c => `
    <tr>
      <td><b>${{c.cost_code}}</b></td>
      <td>${{c.headcount}}</td>
      <td>${{c.st_hrs}}</td>
      <td style="color:${{c.ot_hrs>0?'#fbbf24':'#94a3b8'}}">${{c.ot_hrs}}</td>
      <td>$${{c.burdened_cost.toLocaleString('en-US',{{minimumFractionDigits:2}})}}</td>
    </tr>`).join('')}}</tbody>
`;

document.getElementById('rosterTable').innerHTML = `
  <thead><tr><th>ID</th><th>Employee</th><th>Role / Pod</th><th>Job</th><th>Status</th><th>Cost Code</th><th>Wk Hrs (ST/OT)</th><th>Burdened ($)</th><th>Certs &amp; Alerts</th></tr></thead>
  <tbody>${{D.roster.map(m => `
    <tr>
      <td>${{m.emp_id}}</td>
      <td><b>${{m.name}}</b></td>
      <td>${{m.role}}<br><span style="color:#94a3b8;font-size:11px">${{m.pod}}</span></td>
      <td>${{m.job_id}}</td>
      <td><span class="badge ${{m.status==='ON_SITE'?'b-ok':(m.status==='OUT'?'b-bad':'b-warn')}}">${{m.status}}</span></td>
      <td>${{m.cost_code}}</td>
      <td><b>${{m.total_week_hrs}}h</b> (${{m.st_hrs}}/${{m.ot_hrs}})</td>
      <td>$${{m.burdened_cost.toLocaleString('en-US',{{minimumFractionDigits:2}})}}</td>
      <td>${{m.certs.join(', ')}${{m.cert_alerts.length?` <span class="badge b-bad">${{m.cert_alerts.join(' | ')}}</span>`:''}}</td>
    </tr>`).join('')}}</tbody>
`;

document.getElementById('alertsBox').innerHTML = D.compliance_alerts.map(a =>
  `<div style="margin-bottom:6px"><span class="badge ${{a.severity==='BLOCK'?'b-bad':'b-warn'}}">${{a.severity}}</span> <span style="margin-left:6px;font-size:12.5px">${{a.message}}</span></div>`
).join('');

document.getElementById('procorePre').textContent = JSON.stringify({{
  integration: P.integration,
  sync_date: P.sync_date,
  summary: P.summary,
  sample_manpower_log: P.manpower_logs[0],
  sample_timecard_entry: P.timecard_entries[0],
  sample_delay_log: P.delay_logs[0] || null
}}, null, 2);

function dl(name, text, mime) {{
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([text], {{type: mime}}));
  a.download = name;
  a.click();
}}
function dlPayroll() {{
  const hdr = ['emp_id','name','role','job_id','cost_code','status','base_rate','st_hrs','ot_hrs','total_week_hrs','gross_wages','burdened_cost'];
  const rows = D.roster.map(m => [m.emp_id, `"${{m.name}}"`, `"${{m.role}}"`, m.job_id, `"${{m.cost_code}}"`, m.status, m.base_rate, m.st_hrs, m.ot_hrs, m.total_week_hrs, m.gross_wages, m.burdened_cost].join(','));
  dl('quickbooks_payroll_export.csv', [hdr.join(','), ...rows].join('\\n'), 'text/csv');
}}
function dlProcore() {{ dl('procore_daily_sync_payload.json', JSON.stringify(P, null, 2), 'application/json'); }}
</script>
</body>
</html>
"""
    out = DOCS / "office.html"
    out.write_text(html, encoding="utf-8")
    return out


def build_all() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    data = ce.export_suite_json()
    integ_res = integ.export_all_integrations(data)
    procore_payload = json.loads(Path(integ_res["procore_payload_path"]).read_text(encoding="utf-8"))
    write_manifest()
    p_mob = build_mobile_pwa(data, procore_payload)
    p_off = build_office_dashboard(data, procore_payload)
    print(f"Built Mobile Foreman PWA   -> {p_mob}")
    print(f"Built Corporate Dashboard  -> {p_off}")
    print(f"Exported Procore Payload   -> {integ_res['procore_payload_path']} ({integ_res['procore_summary']})")
    print(f"Exported Bluebeam CSV      -> {integ_res['bluebeam_csv_path']}")


if __name__ == "__main__":
    build_all()
