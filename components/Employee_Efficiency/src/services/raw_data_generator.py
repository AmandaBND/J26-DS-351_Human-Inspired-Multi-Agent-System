"""Generates a Metropolitan-style RAW export (CSV files) for the preprocessing pipeline.

SYNTHETIC. Calibrated to the prototype assumptions in docs (headcount 34, ~1,000 jobs/month,
seasonality, SLA rules, KPI targets). It deliberately contains realistic data-quality problems
(duplicates, mixed date formats, label variants, missing values, outliers, test rows) so the
preprocessing step has real work to do.

Outputs
  data/raw/              what Metropolitan would hand over (employee numbers like 001363)
  data/synthetic_truth/  NOT part of the export: ground-truth labels + list of injected issues + QA

Run:  uv run python -m src.services.raw_data_generator
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime, time, timedelta

import numpy as np
import pandas as pd

from src.config import DATA_DIR, RANDOM_SEED
from src.services.working_time import (FIXED_HOLIDAYS, HOLIDAYS, add_working_minutes, day_window,
                                       in_working_hours, is_working_day, next_working_start,
                                       working_days_between, working_minutes_between)

RAW_DIR = DATA_DIR / "raw"
TRUTH_DIR = DATA_DIR / "synthetic_truth"
START, END = "2024-01", "2026-09"
EXTRACT_DT = datetime(2026, 10, 2, 9, 0)           # date the (fictional) export was taken
SEASON = {1: 950, 2: 900, 3: 1050, 4: 850, 5: 1000, 6: 1100, 7: 1050, 8: 1100, 9: 1000, 10: 1050, 11: 1150, 12: 1300}
YEAR_FACTOR = {2024: 0.93, 2025: 0.97, 2026: 1.0}
LEGACY_ISO_UNTIL = "2024-06"                        # old system exported ISO dates; new one dd/mm/yyyy

TERRITORIES = {   # branches from metropolitan.lk/regional.html; grouping + weights are assumptions
    "Colombo Metro": (0.30, {"Colombo 03": .30, "Nugegoda": .25, "Battaramulla": .25, "Moratuwa": .20}),
    "North Western": (0.22, {"Gampaha": .40, "Negombo": .35, "Kurunegala": .25}),
    "Southern": (0.24, {"Galle": .30, "Matara": .25, "Kalutara": .25, "Ratnapura": .20}),
    "Central & North-East": (0.24, {"Kandy": .35, "Anuradhapura": .15, "Jaffna": .15, "Trincomalee": .15, "Batticaloa": .10, "Badulla": .10}),
}
PRODUCTS = {   # category -> (share, models)
    "Copier/MFP": (0.40, ["Canon imageRUNNER ADVANCE DX C3830i", "Canon imageRUNNER ADVANCE DX C3835i",
                          "Canon imageRUNNER 2224N", "Canon imageRUNNER ADVANCE C5535i III"]),
    "Printer/Scanner": (0.22, ["Canon imageCLASS LBP6030", "Canon PIXMA G3010", "Canon imageFORMULA DR-C225 II"]),
    "York AC": (0.22, ["York Split AC 12000 BTU", "York Split AC 18000 BTU", "York Inverter Split 24000 BTU", "York Central AC"]),
    "Other": (0.16, ["UPS 1kVA", "Network switch", "CCTV system", "Telephone exchange"]),
}
NEW_MODEL = "Canon imageRUNNER ADVANCE DX C3835i"
FAULTS = {   # fault -> complexity
    "Copier/MFP": {"Paper jam": "Low", "Print quality": "Medium", "Error code (E-series)": "Medium",
                   "Scanner fault": "Medium", "Network/connectivity": "Medium", "Fuser failure": "High"},
    "Printer/Scanner": {"Paper feed": "Low", "Cartridge/toner issue": "Low", "Print quality": "Medium", "Connectivity": "Medium"},
    "York AC": {"Not cooling": "Medium", "Water leakage": "Low", "Noise/vibration": "Low", "Remote/PCB fault": "High", "Compressor fault": "High"},
    "Other": {"Power failure": "Low", "No signal/link": "Medium", "Hardware fault": "High"},
}
COMPLEXITY_FAIL_MULT = {"Low": 0.75, "Medium": 1.0, "High": 1.8}
COMPLEXITY_REPAIR_MULT = {"Low": 0.7, "Medium": 1.0, "High": 1.8}


# ----------------------------------------------------------------------------- helpers
def month_range(start: str, end: str) -> list[str]:
    y, m = int(start[:4]), int(start[5:])
    out = []
    while (y, m) <= (int(end[:4]), int(end[5:])):
        out.append(f"{y}-{m:02d}")
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def midx(p: str) -> int:
    return int(p[:4]) * 12 + int(p[5:7]) - 1


def ramp(p: str, start: str, length: int = 3, rec_start: str | None = None, rec_len: int = 4) -> float:
    i, s = midx(p), midx(start)
    if i < s:
        return 0.0
    f = min(1.0, (i - s + 1) / length)
    if rec_start and i >= midx(rec_start):
        f *= max(0.0, 1 - (i - midx(rec_start) + 1) / rec_len)
    return f


def days_in_month(p: str) -> list[date]:
    d = date(int(p[:4]), int(p[5:]), 1)
    out = []
    while d.month == int(p[5:]):
        out.append(d)
        d += timedelta(days=1)
    return out


def pick(rng, items, weights=None):
    items = list(items)
    if weights is not None:
        w = np.array(list(weights), dtype=float)
        return items[rng.choice(len(items), p=w / w.sum())]
    return items[rng.integers(len(items))]


def lognorm(rng, median: float, sigma: float) -> float:
    return float(median * np.exp(rng.normal(0, sigma)))


def random_request_time(rng, d: date) -> datetime:
    """Call centre is 24h: most requests fall in working hours, the rest after hours / Sunday / holiday."""
    w = day_window(d)
    if w and rng.random() < 0.88:
        s, e = w
        return s + timedelta(minutes=float(rng.uniform(0, (e - s).total_seconds() / 60 - 1)))
    if rng.random() < 0.6:       # evening
        return datetime.combine(d, time(17, 0)) + timedelta(minutes=float(rng.uniform(1, 330)))
    return datetime.combine(d, time(6, 0)) + timedelta(minutes=float(rng.uniform(0, 149)))   # early morning


# ----------------------------------------------------------------------------- staff
def build_staff(rng) -> list[dict]:
    nums = sorted(rng.choice(np.arange(1000, 9999), size=34, replace=False).tolist())
    codes = [f"00{n:04d}" for n in nums]
    rng.shuffle(codes)
    tech_sc = (["stable"] * 16 + ["improving"] + ["scenA"] * 2 + ["workload"] * 2 + ["skill"] * 2 + ["recovered"])
    rng.shuffle(tech_sc)
    terr_names = list(TERRITORIES)
    staff = []
    for i in range(24):
        staff.append(dict(code=codes[i], role="technician", scenario=tech_sc[i], territory=terr_names[i // 6],
                          fail_off=rng.normal(0, 0.015), repair_off=lognorm(rng, 1, 0.08), rep_off=rng.normal(0, 0.015),
                          csat_off=rng.normal(0, 0.12), resp_off=lognorm(rng, 1, 0.10)))
    for i in range(4):
        staff.append(dict(code=codes[24 + i], role="tpo_service", scenario="tpo_leave" if i == 3 else "tpo_backlog",
                          territory="Central (Head Office)", assign_off=lognorm(rng, 1, 0.12), err_off=rng.normal(0, 0.005)))
    for i in range(3):
        staff.append(dict(code=codes[28 + i], role="amc_processing", scenario="proc_info" if i < 2 else "stable",
                          territory="Central (Head Office)", proc_off=lognorm(rng, 1, 0.10)))
    for i in range(3):
        staff.append(dict(code=codes[31 + i], role="contracts_coordinator", scenario="price_pressure",
                          territory="Central (Head Office)", conv_off=rng.normal(0, 0.025), contact_off=lognorm(rng, 1, 0.12)))
    return staff


def tech_params(t: dict, p: str) -> dict:
    sc = t["scenario"]
    fA = ramp(p, "2026-05", 3) if sc == "scenA" else 0.0
    fW = ramp(p, "2026-04", 3) if sc == "workload" else 0.0
    fS = ramp(p, "2026-05", 3) if sc == "skill" else 0.0
    fR = ramp(p, "2025-02", 3, "2025-06", 4) if sc == "recovered" else 0.0
    fI = ramp(p, "2025-03", 6) if sc == "improving" else 0.0
    return dict(
        fA=fA, fW=fW, fS=fS, fR=fR, fI=fI,
        fail=(0.165 + t["fail_off"] + 0.15 * fA + 0.13 * fR - 0.05 * fI + 0.03 * fW) / 0.946,
        new_model_fail=0.28 * fS,
        repair=t["repair_off"] * (1 + 0.15 * fA + 0.55 * fS + 0.25 * fW + 0.45 * fR) * (1 - 0.08 * fI),
        parts=0.05 + 0.25 * fA,
        resp=t["resp_off"] * (1 + 0.8 * fW) * (1 - 0.05 * fI),
        report=0.95 + t["rep_off"] - 0.06 * fW - 0.02 * fS - 0.03 * fR + 0.015 * fI,
        weight=1 + 0.45 * fW,
        csat=t["csat_off"] - 0.35 * fS - 0.30 * fW - 0.35 * fA - 0.40 * fR + 0.2 * fI,
        hi_complex=0.12 + 0.11 * fA)


def tpo_params(t: dict, p: str) -> dict:
    fB = ramp(p, "2026-06", 2) if t["scenario"] == "tpo_backlog" else 0.0
    return dict(fB=fB, assign=t["assign_off"] * (1 + 2.2 * fB), closure=1 + 0.8 * fB,
                reassign=0.025 + t["err_off"] + 0.015 * fB, admin_err=0.03 + t["err_off"] + 0.02 * fB,
                alert=0.93 - 0.20 * fB, rec_complete=0.945 - 0.04 * fB)


def tpo_active(t: dict, p: str) -> bool:
    return not (t["scenario"] == "tpo_leave" and p >= "2026-06")


def assign_delay_min(rng) -> float:
    u = rng.random()
    if u < .30:
        return rng.uniform(2, 15)
    if u < .60:
        return rng.uniform(15, 30)
    if u < .85:
        return rng.uniform(31, 60)
    if u < .95:
        return rng.uniform(60, 120)
    return rng.uniform(120, 360)


# ----------------------------------------------------------------------------- jobs
def generate_jobs(rng, staff: list[dict], periods: list[str]) -> tuple[list[dict], dict]:
    techs_by_terr = defaultdict(list)
    for s in staff:
        if s["role"] == "technician":
            techs_by_terr[s["territory"]].append(s)
    tpos = [s for s in staff if s["role"] == "tpo_service"]
    terr_names = list(TERRITORIES)
    terr_w = [TERRITORIES[t][0] for t in terr_names]
    jobs: list[dict] = []
    queue: dict[str, list[dict]] = defaultdict(list)    # repeat visits waiting for their month
    seq = 0
    for p in periods:
        target = int(round(SEASON[int(p[5:7])] * YEAR_FACTOR[int(p[:4])] * rng.uniform(0.93, 1.07)))
        n_new = int(round(0.90 * target))
        days = days_in_month(p)
        dw = np.array([0.4 if (d in HOLIDAYS or d.weekday() == 6) else (0.8 if d.weekday() == 5 else 1.0) for d in days])
        specs = []
        for _ in range(n_new):
            d = days[rng.choice(len(days), p=dw / dw.sum())]
            u = rng.random()
            jt = "Breakdown repair" if u < 0.62 else ("Preventive maintenance" if u < 0.89 else ("Installation" if u < 0.98 else "Other service"))
            specs.append(dict(job_type=jt, req=random_request_time(rng, d), parent=None))
        specs = queue.pop(p, []) + specs
        while specs:                       # repeat visits created while generating this month are processed too
            for sp in specs:
                seq += 1
                jobs.append(_make_job(rng, p, seq, sp, techs_by_terr, tpos, terr_names, terr_w, queue, periods))
            specs = queue.pop(p, [])
    meta = {"total_jobs": len(jobs)}
    return jobs, meta


def _make_job(rng, p, seq, sp, techs_by_terr, tpos, terr_names, terr_w, queue, periods) -> dict:
    jt = sp["job_type"]
    job_id = f"SR{p[2:4]}{p[5:7]}{seq:06d}"
    if sp.get("parent"):                     # repeat visit: same customer/product/fault/territory
        terr, branch = sp["terr"], sp["branch"]
        cat, model, fault, cx = sp["cat"], sp["model"], sp["fault"], sp["cx"]
        cust, prio = sp["cust"], sp["prio"]
    else:
        terr = pick(rng, terr_names, terr_w)
        bw = TERRITORIES[terr][1]
        branch = pick(rng, bw.keys(), bw.values())
        cust = f"C{rng.integers(10000, 99999)}"
        cat = pick(rng, PRODUCTS, [v[0] for v in PRODUCTS.values()])
    techs = techs_by_terr[terr]
    tp_all = [tech_params(t, p) for t in techs]
    ti = rng.choice(len(techs), p=np.array([x["weight"] for x in tp_all]) / sum(x["weight"] for x in tp_all))
    tech, tp = techs[ti], tp_all[ti]
    if not sp.get("parent"):
        models = PRODUCTS[cat][1]
        if cat == "Copier/MFP" and tech["scenario"] == "skill" and tp["fS"] > 0 and rng.random() < 0.55:
            model = NEW_MODEL
        else:
            model = pick(rng, models)
        fault = pick(rng, FAULTS[cat])
        cx = FAULTS[cat][fault]
        if tech["scenario"] == "scenA" and tp["fA"] > 0 and cx != "High" and rng.random() < tp["hi_complex"] - 0.12:
            cx = "High"
        if jt in ("Preventive maintenance",):
            fault, cx = "Scheduled maintenance", "Low"
        elif jt == "Installation":
            fault, cx = "New installation", "Medium"
        elif jt == "Other service":
            fault, cx = "General service request", "Low"
        if jt == "Breakdown repair":
            prio = pick(rng, ["P1", "P2", "P3"], [0.05, 0.20, 0.75])
        else:
            prio = "P4"
    contract = pick(rng, ["AMC", "Warranty", "Chargeable"], [0.45, 0.20, 0.35]) if jt != "Preventive maintenance" else "AMC"

    # --- assignment (TPO)
    req = sp["req"]
    active = [t for t in tpos if tpo_active(t, p)]
    tpo = active[rng.integers(len(active))]
    tpp = tpo_params(tpo, p)
    cancelled = rng.random() < 0.015
    if prio == "P4":
        assigned = add_working_minutes(req, float(rng.uniform(30, 2 * 510)))
    else:
        assigned = add_working_minutes(req, assign_delay_min(rng) * tpp["assign"])
    sla_start = next_working_start(req)
    if prio == "P1":
        sla_due = add_working_minutes(req, 240)
    elif prio == "P2":
        sla_due = add_working_minutes(req, 510)
    elif prio == "P3":
        sla_due = add_working_minutes(req, 3 * 510)
    # --- visit
    if prio == "P4":
        appt_day = assigned.date() + timedelta(days=int(rng.integers(1, 8)))
        while not is_working_day(appt_day):
            appt_day += timedelta(days=1)
        span = 150 if appt_day.weekday() == 5 else 165      # latest start keeps the visit inside the working day
        arrival = datetime.combine(appt_day, time(8, 45)) + timedelta(minutes=float(rng.uniform(0, span)))
        arrival = next_working_start(arrival)
        sla_due = datetime.combine(appt_day, time(17, 0)) if appt_day.weekday() < 5 else datetime.combine(appt_day, time(13, 0))
    else:
        med = {"P1": 35, "P2": 100, "P3": 240}[prio]
        arrival = add_working_minutes(assigned, lognorm(rng, med, 0.6) * tp["resp"])
    base_rep = {"Breakdown repair": 3.0, "Preventive maintenance": 1.8, "Installation": 4.5, "Other service": 2.5, "Repeat visit": 3.0}[jt]
    repair_h = lognorm(rng, base_rep * COMPLEXITY_REPAIR_MULT[cx] if jt in ("Breakdown repair", "Repeat visit") else base_rep, 0.45) * tp["repair"]
    repair_h = round(max(0.25, repair_h) * 4) / 4
    parts_h = 0.0
    if jt in ("Breakdown repair", "Repeat visit") and rng.random() < tp["parts"]:
        parts_h = round(float(rng.uniform(8, 70)), 1)
    completion = add_working_minutes(arrival, (repair_h + parts_h) * 60)
    closer = active[rng.integers(len(active))]
    closure = add_working_minutes(completion, lognorm(rng, 300, 0.7) * tpo_params(closer, p)["closure"])

    # --- outcome
    failed = False
    if jt in ("Breakdown repair", "Installation") and not sp.get("is_second"):
        pf = tp["fail"] * COMPLEXITY_FAIL_MULT[cx] + (tp["new_model_fail"] if model == NEW_MODEL else 0.0)
        pf = pf if jt == "Breakdown repair" else pf * 0.4
        failed = rng.random() < min(0.85, pf)
    if failed:
        rdt = completion + timedelta(days=float(rng.uniform(2, 10)))
        rdt = next_working_start(rdt) + timedelta(minutes=float(rng.uniform(0, 240)))
        rdt = rdt if in_working_hours(rdt) else next_working_start(rdt)
        rp = f"{rdt.year}-{rdt.month:02d}"
        if rp in periods:
            queue[rp].append(dict(job_type="Repeat visit", req=rdt, parent=job_id, terr=terr, branch=branch, cat=cat,
                                  model=model, fault=fault, cx=cx, cust=cust, prio=pick(rng, ["P2", "P3"], [0.3, 0.7]),
                                  is_second=True))
    sla_met = completion <= sla_due
    wait_resp = working_minutes_between(req, arrival) / 60 if prio != "P4" else None
    csat = None
    if rng.random() < 0.45 and not cancelled:
        v = 4.5 + tp["csat"] - 0.8 * (not sla_met) - 0.6 * bool(sp.get("parent")) - 0.5 * (parts_h > 0) + rng.normal(0, 0.7)
        csat = int(np.clip(round(v), 1, 5))
    alert = None
    if rng.random() < tpp["alert"] and prio != "P4":
        alert = sla_due - timedelta(minutes=float(rng.uniform(30, 240)))
    return dict(
        job_id=job_id, request_dt=req, assigned_dt=None if cancelled else assigned, assigned_by=tpo["code"],
        technician_no=tech["code"], arrival_dt=None if cancelled else arrival, completion_dt=None if cancelled else completion,
        closure_dt=None if cancelled else closure, sla_due_dt=sla_due, job_type=jt, product_type=model, product_category=cat,
        fault_type=fault, fault_complexity=cx, priority=prio, branch=branch, customer_ref=cust, contract_status=contract,
        repeat_visit_flag="Y" if sp.get("parent") else "N", parent_job_id=sp.get("parent"),
        repair_time_hrs=repair_h, parts_wait_hrs=parts_h, report_complete="Y" if rng.random() < tp["report"] else "N",
        csat=csat, status="Cancelled" if cancelled else "Closed", closed_by=closer["code"],
        sla_alert_dt=alert, reassigned_flag="Y" if rng.random() < tpp["reassign"] else "N",
        admin_error_flag="Y" if rng.random() < tpp["admin_err"] else "N",
        record_complete_flag="Y" if rng.random() < tpp["rec_complete"] else "N",
        _failed=failed, _period=p, _tech_scn=tech["scenario"], _terr=terr)


# ----------------------------------------------------------------------------- AMC proposals & contracts
PRICE_CHANGES = [  # effective date, change %, remark  (AMC list price)
    ("2024-04-01", 3.0, "Annual AMC list price revision"),
    ("2025-04-01", 5.0, "Annual AMC list price revision - parts cost increase"),
    ("2026-04-01", 12.0, "AMC list price revision - tax and imported parts cost increase"),
]
REJECT_REASONS = {
    "price": ["Price too high", "Too expensive", "Budget constraints", "Budget not approved"],
    "competitor": ["Competitor offer cheaper", "Going with another vendor"],
    "other": ["Not required now", "Equipment being replaced", "Decision postponed", "Existing in-house support"],
}


def price_index(d: date) -> float:
    idx = 1.0
    for eff, pct, _ in PRICE_CHANGES:
        if d >= date.fromisoformat(eff):
            idx *= 1 + pct / 100
    return idx


def _wh_time(rng, d: date) -> datetime:
    d2 = d
    while not is_working_day(d2):
        d2 += timedelta(days=1)
    s, e = day_window(d2)
    return s + timedelta(minutes=float(rng.uniform(0, 300)))


def generate_amc(rng, staff: list[dict], periods: list[str]) -> tuple[list[dict], list[dict]]:
    coords = [s for s in staff if s["role"] == "contracts_coordinator"]
    procs = [s for s in staff if s["role"] == "amc_processing"]
    proposals, contracts = [], []
    due_map: dict[str, list[dict]] = defaultdict(list)     # 'YYYY-MM' -> contracts whose renewal falls due
    cseq = 0

    def add_contract(**kw):
        nonlocal cseq
        cseq += 1
        c = dict(contract_id=f"AMC{cseq:06d}", **kw)
        contracts.append(c)
        due_map[f"{c['renewal_due'].year}-{c['renewal_due'].month:02d}"].append(c)
        return c

    def proc_params(pr: dict, p: str) -> dict:
        fC = ramp(p, "2026-05", 3) if pr["scenario"] == "proc_info" else 0.0
        return dict(fC=fC, speed=pr["proc_off"] * (1 + 2.4 * fC), incomplete=0.04 + 0.40 * fC,
                    error=0.012 + 0.02 * fC, pm_on_time=0.92 - 0.10 * fC, renew_on_time=0.90 - 0.08 * fC)

    # legacy stock: contracts created during 2023 that fall due for renewal during 2024
    for m in range(1, 13):
        for _ in range(int(rng.integers(50, 62))):
            start = date(2023, m, int(rng.integers(1, 28)))
            pr = procs[rng.integers(len(procs))]
            add_contract(proposal_id=None, contract_type="Legacy", processor_no=pr["code"], approval=None,
                         created=datetime.combine(start - timedelta(days=int(rng.integers(0, 6))), time(10, 0)),
                         start=start, renewal_due=start + timedelta(days=365), data_complete=True,
                         correction=False, value=round(float(lognorm(rng, 80000, 0.5)), -2), product=pick(rng, PRODUCTS),
                         pm_created=start + timedelta(days=int(rng.integers(0, 6))), _pf=0.0, status="Active")

    pseq = 0
    for p in periods:
        busy = SEASON[int(p[5:7])] >= 1100
        n_prop = int(round((260 if busy else 200) * rng.uniform(0.93, 1.07)))
        days = days_in_month(p)
        for _ in range(n_prop):
            pseq += 1
            d = pick(rng, [x for x in days if x.weekday() < 6 and x not in HOLIDAYS])
            cd = coords[rng.integers(len(coords))]
            fD = ramp(p, "2026-05", 2)
            seg = pick(rng, ["Corporate", "SME", "Government", "Individual"], [0.35, 0.30, 0.20, 0.15])
            prod = pick(rng, PRODUCTS, [0.45, 0.20, 0.25, 0.10])
            idx = price_index(d)
            value = round(float(lognorm(rng, 78000, 0.5)) * idx * {"Corporate": 1.4, "SME": 1.0, "Government": 1.2, "Individual": 0.6}[seg], -2)
            p_acc = (0.31 + cd["conv_off"]) * (0.84 if busy else 1.0) * (1 - 0.30 * fD) * {"Corporate": 1.1, "SME": 1.0, "Government": 0.9, "Individual": 0.8}[seg]
            ptime = datetime.combine(d, time(9, 0)) + timedelta(minutes=float(rng.uniform(0, 420)))
            first_contact = add_working_minutes(ptime, lognorm(rng, 300, 0.7) * cd["contact_off"])
            u = rng.random()
            if u < p_acc:
                status, out_days = "Accepted", min(90.0, lognorm(rng, 12, 0.6))
            elif u < p_acc + (1 - p_acc) * 0.55:
                status, out_days = "Rejected", min(60.0, lognorm(rng, 9, 0.5))
            else:
                status, out_days = "No Response", 60.0
            outcome_dt = ptime + timedelta(days=out_days)
            if outcome_dt > EXTRACT_DT:
                status, outcome_dt = "Pending", None
            due, done = [], []
            for off in (3, 7, 14):
                dd = d + timedelta(days=off)
                if outcome_dt is not None and datetime.combine(dd, time(0, 0)) > outcome_dt:
                    break
                if datetime.combine(dd, time(0, 0)) > EXTRACT_DT:
                    break
                due.append(dd)
                r = rng.random()
                if r < 0.945:
                    done.append(dd)
                elif r < 0.975:
                    done.append(dd + timedelta(days=int(rng.integers(2, 7))))
            reason = None
            if status == "Rejected":
                sp = 0.30 + 0.40 * fD
                sc = 0.15 + 0.20 * fD
                grp = pick(rng, ["price", "competitor", "other"], [sp, sc, max(0.05, 1 - sp - sc)])
                if rng.random() < 0.85:
                    reason = pick(rng, REJECT_REASONS[grp])
                else:
                    reason = ""
            proposals.append(dict(
                proposal_id=f"PR{p[2:4]}{p[5:7]}{pseq:05d}", coordinator_no=cd["code"], processor_no=None,
                proposal_dt=ptime, first_contact_dt=first_contact, followup_due=due, followup_done=done, status=status,
                rejection_reason=reason, approval_dt=outcome_dt if status == "Accepted" else None,
                quoted_price=value, customer_segment=seg, product_category=prod, customer_ref=f"C{rng.integers(10000, 99999)}",
                data_complete=True, contract_id=None, _period=p, _fD=fD))

        # contracts from proposals accepted this month's cohort are created when the approval date arrives (below)
    # accepted proposals -> contracts
    for pr_ in proposals:
        if pr_["status"] != "Accepted":
            continue
        pcode = procs[rng.integers(len(procs))]
        ap = proc_params(pcode, f"{pr_['approval_dt'].year}-{pr_['approval_dt'].month:02d}")
        pr_["processor_no"] = pcode["code"]
        pr_["data_complete"] = rng.random() > ap["incomplete"]
        wd = lognorm(rng, 1.5, 0.45) * ap["speed"]
        if not pr_["data_complete"]:
            wd += float(rng.uniform(1, 5)) * (1 + 1.3 * ap["fC"])
        created = add_working_minutes(pr_["approval_dt"], wd * 510)
        pending = created > EXTRACT_DT
        start = (created + timedelta(days=int(rng.integers(0, 14)))).date()
        c = add_contract(proposal_id=pr_["proposal_id"], contract_type="New", processor_no=pcode["code"],
                         approval=pr_["approval_dt"], created=None if pending else created, start=start,
                         renewal_due=start + timedelta(days=365), data_complete=pr_["data_complete"],
                         correction=bool(rng.random() < ap["error"]), value=pr_["quoted_price"], product=pr_["product_category"],
                         pm_created=None, _pf=ap["pm_on_time"], status="Pending" if pending else "Active", _proc=pcode)
        pr_["contract_id"] = c["contract_id"]
        if not pending:
            late = rng.random() > ap["pm_on_time"]
            c["pm_created"] = (created + timedelta(days=int(rng.integers(8, 30) if late else rng.integers(0, 7)))).date() if rng.random() > 0.03 else None

    # renewal chain, month by month
    for p in periods + month_range("2026-10", "2027-09"):
        for c in list(due_map.get(p, [])):
            if c.get("created") is None and c["contract_type"] != "Legacy":
                continue
            pcode = c.get("_proc") or next(s for s in procs if s["code"] == c["processor_no"])
            ap = proc_params(pcode, min(p, END))
            due = c["renewal_due"]
            c["renewal_followup"] = None
            if due <= date(2026, 12, 31):
                r = rng.random()
                if r < ap["renew_on_time"]:
                    fu = due - timedelta(days=int(rng.integers(32, 70)))
                elif r < 0.97:
                    fu = due - timedelta(days=int(rng.integers(0, 30)))
                else:
                    fu = None
                if fu is not None and datetime.combine(fu, time(9, 0)) <= EXTRACT_DT:
                    c["renewal_followup"] = fu
            c["renewed"] = None
            if due <= EXTRACT_DT.date():
                renewed = rng.random() < (0.80 if c["renewal_followup"] and c["renewal_followup"] <= due - timedelta(days=30) else 0.50)
                c["renewed"] = renewed
                if renewed:
                    new_created = datetime.combine(due - timedelta(days=int(rng.integers(0, 12))), time(11, 0))
                    nc = add_contract(proposal_id=None, contract_type="Renewal", processor_no=c["processor_no"],
                                      approval=None, created=new_created, start=due, renewal_due=due + timedelta(days=365),
                                      data_complete=bool(rng.random() > ap["incomplete"]), correction=bool(rng.random() < ap["error"]),
                                      value=round(c["value"] * rng.uniform(1.0, 1.08), -2), product=c["product"],
                                      pm_created=(due - timedelta(days=int(rng.integers(0, 7)))), _pf=ap["pm_on_time"],
                                      status="Active", _proc=pcode)
    return proposals, contracts


# ----------------------------------------------------------------------------- context, HR, feedback
def generate_attendance(rng, staff, periods) -> list[dict]:
    rows = []
    for e in staff:
        for p in periods:
            sc = e["scenario"]
            fW = ramp(p, "2026-04", 3) if sc == "workload" else 0
            fA = ramp(p, "2026-05", 3) if sc == "scenA" else 0
            fS = ramp(p, "2026-05", 3) if sc == "skill" else 0
            fB = ramp(p, "2026-06", 2) if sc == "tpo_backlog" else 0
            fC = ramp(p, "2026-05", 3) if sc == "proc_info" else 0
            fD = ramp(p, "2026-05", 2) if sc == "price_pressure" else 0
            leave = min(5, int(rng.poisson(1.3)))
            ot = {"technician": 8, "tpo_service": 6, "amc_processing": 4, "contracts_coordinator": 4}[e["role"]] + rng.normal(0, 2.5)
            ot += 30 * fW + 4 * fA + 2 * fS + 14 * fB + 10 * fC + 4 * fD
            if sc == "tpo_leave" and p >= "2026-06":
                leave, ot = int(rng.integers(19, 23)), 0
            rows.append(dict(employee_no=e["code"], period=p, leave_days=leave, overtime_hours=round(max(0, ot), 1)))
    return rows


def generate_downtime(rng, periods) -> list[dict]:
    rows, n = [], 0
    systems = ["Service Management System", "ERP", "Call Centre Telephony", "Email / Network"]
    for p in periods:
        for _ in range(int(rng.poisson(1.5))):
            n += 1
            d = pick(rng, days_in_month(p))
            st = datetime.combine(d, time(int(rng.integers(8, 16)), int(rng.integers(0, 59))))
            rows.append(dict(incident_id=f"INC{n:04d}", system=pick(rng, systems, [.35, .30, .20, .15]), start_dt=st,
                             end_dt=st + timedelta(hours=float(lognorm(rng, 1.5, 0.5))), severity="Minor", remarks="Brief outage, resolved by IT"))
    for sysn, st, hrs, rem in [("ERP", datetime(2025, 3, 18, 9, 5), 9.0, "Database server failure - restored from backup"),
                               ("Service Management System", datetime(2026, 7, 8, 8, 40), 14.0, "Application server outage, partial recovery next day")]:
        n += 1
        rows.append(dict(incident_id=f"INC{n:04d}", system=sysn, start_dt=st, end_dt=st + timedelta(hours=hrs), severity="Major", remarks=rem))
    return sorted(rows, key=lambda r: r["start_dt"])


def generate_competitor_notes(rng, periods) -> list[dict]:
    mild = ["No competitor activity reported this month.", "Customer comparing our AMC quote with another supplier.",
            "Customer asked for a discount on renewal.", "Customer satisfied with current AMC terms."]
    hard = ["Customer received a lower AMC quote from a local vendor.", "Competitor reported offering AMC at roughly 15% lower rate.",
            "Customer says our revised AMC price is higher than market.", "Several corporate customers asking for price match."]
    rows = []
    for p in periods:
        press = ramp(p, "2026-04", 2)
        for _ in range(int(rng.poisson(2 + 6 * press))):
            terr = pick(rng, TERRITORIES)
            rows.append(dict(note_date=pick(rng, days_in_month(p)), territory=terr, product_category=pick(rng, ["Copier/MFP", "York AC", "Printer/Scanner"]),
                             note_text=pick(rng, hard if rng.random() < 0.15 + 0.7 * press else mild), source=pick(rng, ["Coordinator call", "Customer feedback", "Sales visit"])))
    return rows


FEEDBACK = {
    "neutral": ["Routine month, no major issues.", "Handled assigned work as usual.", "Team coordination was fine this month."],
    "positive": ["Feeling confident with the workflow.", "Training helped, jobs are going smoothly.", "Good month, targets feel achievable."],
    "workload": ["Too many jobs assigned, working late most days.", "Backlog keeps growing and overtime is heavy.", "Struggling to keep up with the daily workload."],
    "skill": ["Unfamiliar with the new C3835i model, needed repeat visits.", "Would benefit from training on the latest product line.", "Not confident handling the new systems."],
    "parts": ["Many complex jobs and long waits for spare parts this month.", "Customers waiting for parts, repeat visits increased."],
    "tpo": ["A colleague is on leave and the assignment backlog keeps growing.", "Too many unassigned jobs, hard to keep up with requests."],
    "proc": ["Many proposals arrive with missing approval details, contracts stuck waiting.", "Spending most of the time chasing incomplete equipment details."],
    "market": ["Customers say a competitor's AMC price is cheaper.", "Customer budget limits make AMC renewals hard.", "Price increase is putting customers off."],
}


def generate_feedback(rng, staff, periods) -> list[dict]:
    rows = []
    for e in staff:
        sc = e["scenario"]
        for p in periods:
            if rng.random() > 0.80 or (sc == "tpo_leave" and p >= "2026-06"):
                continue
            key, f = "neutral", 0.0
            if sc == "workload":
                f, key = ramp(p, "2026-04", 3), "workload"
            elif sc == "skill":
                f, key = ramp(p, "2026-05", 3), "skill"
            elif sc == "scenA":
                f, key = ramp(p, "2026-05", 3), "parts"
            elif sc == "tpo_backlog":
                f, key = ramp(p, "2026-06", 2), "tpo"
            elif sc == "proc_info":
                f, key = ramp(p, "2026-05", 3), "proc"
            elif sc == "price_pressure":
                f, key = ramp(p, "2026-05", 2), "market"
            elif sc == "recovered":
                f = ramp(p, "2025-02", 3, "2025-06", 4)
                key = "skill"
                if p >= "2025-08":
                    f, key = 0, "positive"
            elif sc == "improving" and p >= "2025-06":
                key = "positive"
            use = key if (f > 0.3 and rng.random() < 0.85) or (key == "positive" and rng.random() < 0.7) else "neutral"
            rows.append(dict(employee_no=e["code"], period=p, comment_text=pick(rng, FEEDBACK[use])))
    return rows


def generate_reviews(rng, staff) -> list[dict]:
    cycles = [("2024 Year-End", "2024-12"), ("2025 Mid-Year", "2025-06"), ("2025 Year-End", "2025-12"), ("2026 Mid-Year", "2026-06")]
    rows = []
    for e in staff:
        off = rng.normal(0, 0.25)
        for label, p in cycles:
            sc, f, note = e["scenario"], 0.0, ""
            if sc == "workload": f, note = ramp(p, "2026-04", 3), "Higher job volume and overtime noted"
            elif sc == "skill": f, note = ramp(p, "2026-05", 3), "Repeat visits increased on the new copier model"
            elif sc == "scenA": f, note = ramp(p, "2026-05", 3), "First-time fix rate dropped; complex jobs and parts delays"
            elif sc == "recovered": f, note = ramp(p, "2025-02", 3, "2025-06", 4), "Repeat visits rose after new model rollout"
            elif sc == "tpo_backlog": f, note = ramp(p, "2026-06", 2), "Assignment times above target"
            elif sc == "proc_info": f, note = ramp(p, "2026-05", 3), "Contract processing slower than target"
            elif sc == "price_pressure": f, note = ramp(p, "2026-05", 2), "AMC conversion below target"
            if sc == "tpo_leave" and p >= "2026-06":
                rows.append(dict(employee_no=e["code"], review_cycle=label, rating="", manager_comment="On extended leave - not rated", action_taken="None"))
                continue
            rating = int(np.clip(round(3.7 + off - 1.6 * f + (0.4 * ramp(p, "2025-03", 6) if sc == "improving" else 0) + rng.normal(0, 0.45)), 1, 5))
            if sc == "recovered" and label == "2025 Year-End":
                rating, note = 4, "Improved after technical training"
            if f > 0.3:
                comment = f"{note}. Needs support." if rating <= 3 else f"{note}, monitoring."
                action = {"workload": "Workload to be reviewed", "skill": "Training scheduled", "scenA": "Review parts availability",
                          "recovered": "Training scheduled", "tpo_backlog": "Monitor", "proc_info": "Monitor",
                          "price_pressure": "Coaching on proposals"}.get(sc, "Monitor")
            else:
                comment = pick(rng, ["Consistent performer.", "Meets expectations.", "Good team player, reliable.", note or "Steady month-to-month results."])
                action = "None"
            rows.append(dict(employee_no=e["code"], review_cycle=label, rating=rating, manager_comment=comment, action_taken=action))
    return rows


# ----------------------------------------------------------------------------- rendering (raw, messy)
class Mess:
    """Applies realistic export quirks and counts every injected issue (for the truth log)."""

    def __init__(self, rng):
        self.rng, self.n = rng, defaultdict(int)

    def dt(self, v, legacy: bool) -> str:
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return ""
        return v.strftime("%Y-%m-%d %H:%M:%S") if legacy else v.strftime("%d/%m/%Y %H:%M")

    def d(self, v, legacy: bool) -> str:
        if v is None:
            return ""
        return v.strftime("%Y-%m-%d") if legacy else v.strftime("%d/%m/%Y")

    def yn(self, v, blank_p=0.0) -> str:
        if v is None or self.rng.random() < blank_p:
            if v is not None:
                self.n["missing_flag_values"] += 1
            return ""
        yes = v in (True, "Y")
        choice = pick(self.rng, ["Y", "Yes", "y", "1", "TRUE"] if yes else ["N", "No", "n", "0", "FALSE"], [.80, .08, .05, .04, .03])
        if choice not in ("Y", "N"):
            self.n["flag_format_variants"] += 1
        return choice

    def emp(self, code) -> str:
        if code is None:
            return ""
        r = self.rng.random()
        if r < 0.015:
            self.n["employee_no_missing_leading_zeros"] += 1
            return str(int(code))
        if r < 0.025:
            self.n["employee_no_trailing_space"] += 1
            return code + " "
        return code

    def priority(self, v) -> str:
        r = self.rng.random()
        if r < 0.85:
            return v
        self.n["priority_label_variants"] += 1
        if r < 0.90:
            return v.lower()
        return {"P1": "Critical", "P2": "High", "P3": "Normal", "P4": "Planned"}[v] if r < 0.97 else {"P1": "1 - Critical", "P2": "2 - High", "P3": "3 - Normal", "P4": "4 - Planned"}[v]

    def text_variant(self, s: str, p=0.06) -> str:
        if self.rng.random() < p:
            self.n["text_case_whitespace_variants"] += 1
            return pick(self.rng, [s.upper(), s.lower(), s + " ", " " + s])
        return s

    def product(self, s: str) -> str:
        if self.rng.random() < 0.07:
            self.n["product_name_variants"] += 1
            return pick(self.rng, [s.upper(), s.replace("imageRUNNER", "iR").replace("ADVANCE", "ADV"), s.replace("Canon ", ""), s.replace("York ", "YORK ")])
        return s

    def status(self, s: str) -> str:
        if self.rng.random() < 0.06:
            self.n["status_label_variants"] += 1
            return pick(self.rng, [s.upper(), s.lower()])
        return s

    def hhmm(self, hours: float) -> str:
        h = int(hours)
        return f"{h:02d}:{int(round((hours - h) * 60)):02d}"


def render_jobs(rng, jobs: list[dict], staff: list[dict], mess: Mess) -> pd.DataFrame:
    rows = []
    for j in jobs:
        legacy = j["_period"] <= LEGACY_ISO_UNTIL
        a, ar, co, cl, st = j["assigned_dt"], j["arrival_dt"], j["completion_dt"], j["closure_dt"], j["status"]
        if st != "Cancelled":                         # the export was taken on EXTRACT_DT: later events are not yet known
            if a is not None and a > EXTRACT_DT:
                a = ar = co = cl = None; st = "Open"
            elif ar is not None and ar > EXTRACT_DT:
                ar = co = cl = None; st = "Assigned"
            elif co is not None and co > EXTRACT_DT:
                co = cl = None; st = "In Progress"
            elif cl is not None and cl > EXTRACT_DT:
                cl = None; st = "Completed"
        req, alert = j["request_dt"], j["sla_alert_dt"]
        if alert is not None and alert > EXTRACT_DT:
            alert = None
        repair = j["repair_time_hrs"] if co is not None else None
        # --- injected faults
        if a is not None and rng.random() < 0.003:
            a = req - timedelta(minutes=float(rng.uniform(5, 90))); mess.n["assigned_before_request"] += 1
        if ar is not None and a is not None and rng.random() < 0.002:
            ar = a - timedelta(minutes=float(rng.uniform(5, 60))); mess.n["arrival_before_assignment"] += 1
        if ar is not None and co is not None and rng.random() < 0.006:
            ar = None; mess.n["arrival_dt_missing"] += 1
        repair_txt = "" if repair is None else f"{repair:g}"
        if repair is not None:
            r = rng.random()
            if r < 0.003:
                repair_txt = f"{repair * 10:g}"; mess.n["repair_time_outliers_x10"] += 1
            elif r < 0.013:
                repair_txt = mess.hhmm(repair); mess.n["repair_time_hhmm_format"] += 1
        fault = j["fault_type"]
        if rng.random() < 0.02:
            fault = ""; mess.n["fault_type_missing"] += 1
        tech = None if st in ("Cancelled", "Open") and rng.random() < 0.5 else j["technician_no"]
        rows.append(dict(
            job_id=j["job_id"], request_dt=mess.dt(req, legacy), assigned_dt=mess.dt(a, legacy), assigned_by=mess.emp(j["assigned_by"]),
            technician_no=mess.emp(tech), arrival_dt=mess.dt(ar, legacy), completion_dt=mess.dt(co, legacy), closure_dt=mess.dt(cl, legacy),
            sla_due_dt=mess.dt(j["sla_due_dt"], legacy), sla_alert_dt=mess.dt(alert, legacy), job_type=j["job_type"],
            product_type=mess.product(j["product_type"]), fault_type=fault, fault_complexity=j["fault_complexity"],
            priority=mess.priority(j["priority"]), branch=mess.text_variant(j["branch"]), customer_ref=j["customer_ref"],
            contract_status=j["contract_status"], repeat_visit_flag=mess.yn(j["repeat_visit_flag"]), parent_job_id=j["parent_job_id"] or "",
            repair_time_hrs=repair_txt, parts_wait_hrs="" if repair is None else f"{j['parts_wait_hrs']:g}",
            report_complete=mess.yn(j["report_complete"] if co is not None else None, 0.03),
            csat="" if (j["csat"] is None or co is None) else int(j["csat"]), status=mess.status(st),
            closed_by=mess.emp(j["closed_by"]) if cl is not None else "", reassigned_flag=mess.yn(j["reassigned_flag"]),
            admin_error_flag=mess.yn(j["admin_error_flag"] if cl is not None else None),
            record_complete_flag=mess.yn(j["record_complete_flag"] if cl is not None else None)))
    df = pd.DataFrame(rows)
    # test records created by staff while training on the system
    techs = [s["code"] for s in staff if s["role"] == "technician"]
    tests = []
    for i in range(12):
        t = df.iloc[int(rng.integers(len(df)))].copy()
        t["job_id"], t["customer_ref"], t["product_type"], t["technician_no"] = f"TEST-{i + 1:04d}", "TEST", "Test Printer", pick(rng, techs)
        tests.append(t)
    mess.n["test_records"] = len(tests)
    df = pd.concat([df, pd.DataFrame(tests)], ignore_index=True)
    # exact duplicates
    dup = df.sample(frac=0.005, random_state=int(rng.integers(1 << 30)))
    mess.n["duplicate_job_rows"] = len(dup)
    df = pd.concat([df, dup], ignore_index=True).sort_values("job_id", kind="stable").reset_index(drop=True)
    return df


def render_proposals(rng, proposals, mess: Mess) -> pd.DataFrame:
    rows = []
    for p in proposals:
        legacy = p["_period"] <= LEGACY_ISO_UNTIL
        status = {"Accepted": ["Accepted", "ACCEPTED", "Won"], "Rejected": ["Rejected", "REJECTED", "Declined"],
                  "No Response": ["No Response", "No response", "Lapsed"], "Pending": ["Pending"]}[p["status"]]
        st = pick(rng, status, [.85, .10, .05][:len(status)] if len(status) == 3 else None)
        if st not in ("Accepted", "Rejected", "No Response", "Pending"):
            mess.n["proposal_status_variants"] += 1
        price = p["quoted_price"]
        r = rng.random()
        price_txt = f"LKR {price:,.2f}" if r < 0.4 else (f"{price:.0f}" if r < 0.8 else f"{price:,.0f}")
        if r < 0.4 or r >= 0.8:
            mess.n["price_format_variants"] += 1
        reason = p["rejection_reason"]
        if p["status"] == "Rejected" and reason == "":
            reason = pick(rng, ["", "-", "N/A"], [.7, .2, .1])
        rows.append(dict(
            proposal_id=p["proposal_id"], coordinator_no=mess.emp(p["coordinator_no"]), processor_no=mess.emp(p["processor_no"]),
            proposal_dt=mess.dt(p["proposal_dt"], legacy), first_contact_dt=mess.dt(p["first_contact_dt"], legacy),
            followup_due_dates=";".join(mess.d(x, legacy) for x in p["followup_due"]),
            followup_done_dates=";".join(mess.d(x, legacy) for x in p["followup_done"]),
            status=st, rejection_reason=reason or "", approval_dt=mess.dt(p["approval_dt"], legacy),
            contract_id=p["contract_id"] or "", quoted_price=price_txt, customer_segment=p["customer_segment"],
            product_category=p["product_category"], customer_ref=p["customer_ref"],
            data_complete_flag=mess.yn(p["data_complete"]) if p["status"] == "Accepted" else ""))
    df = pd.DataFrame(rows)
    dup = df.sample(frac=0.005, random_state=int(rng.integers(1 << 30)))
    mess.n["duplicate_proposal_rows"] = len(dup)
    return pd.concat([df, dup], ignore_index=True).sort_values("proposal_id", kind="stable").reset_index(drop=True)


def render_contracts(rng, contracts, mess: Mess) -> pd.DataFrame:
    rows = []
    for c in contracts:
        created = c["created"]
        due = c["renewal_due"]
        if c.get("renewed") is True:
            status = "Renewed"
        elif c.get("renewed") is False:
            status = "Expired"
        else:
            status = "Pending" if created is None else "Active"
        start = c["start"]
        pm = c.get("pm_created")
        pm_dates = ";".join((start + timedelta(days=d)).strftime("%d/%m/%Y") for d in (90, 180, 270, 360)) if pm else ""
        rows.append(dict(
            contract_id=c["contract_id"], proposal_id=c["proposal_id"] or "", contract_type=c["contract_type"],
            processor_no=mess.emp(c["processor_no"]), approval_dt=mess.dt(c["approval"], False),
            contract_created_dt=mess.dt(created, False), contract_start_date=start.strftime("%d/%m/%Y"),
            renewal_due_date=due.strftime("%d/%m/%Y"), renewal_followup_date=c["renewal_followup"].strftime("%d/%m/%Y") if c.get("renewal_followup") else "",
            data_complete_flag=mess.yn(c["data_complete"]), correction_required_flag=mess.yn(c["correction"]),
            pm_schedule_created_date=pm.strftime("%d/%m/%Y") if pm else "", pm_schedule_dates=pm_dates,
            contract_value_lkr=f"{c['value']:.0f}", product_category=c["product"], status=status))
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- QA & truth
def qa_summary(jobs: list[dict], proposals: list[dict], contracts: list[dict]) -> pd.DataFrame:
    """Baseline-year (2024) monthly KPI ranges from the CLEAN data vs the prototype ranges supplied."""
    J = pd.DataFrame(jobs)
    J["m"] = J["request_dt"].dt.strftime("%Y-%m")
    J = J[(J.m < "2025-01") & (J.status == "Closed")]
    nonp4 = J[J.priority != "P4"]
    orig = J[J.job_type.isin(["Breakdown repair", "Installation"])]
    rows = []

    def add(name, s, lo, hi, scale=1.0):
        s = s * scale
        rows.append(dict(kpi=name, baseline_min=round(s.min(), 2), baseline_mean=round(s.mean(), 2), baseline_max=round(s.max(), 2),
                         prototype_range=f"{lo}-{hi}", mean_in_range=bool(lo <= s.mean() <= hi)))
    add("SLA compliance %", J.assign(ok=J.completion_dt <= J.sla_due_dt).groupby("m").ok.mean(), 85, 95, 100)
    add("First-time fix rate %", 1 - orig.groupby("m")._failed.mean(), 72, 88, 100)
    add("Repeat service rate %", J.assign(r=J.parent_job_id.notna()).groupby("m").r.mean(), 6, 15, 100)
    add("MTTR hours (breakdown, active repair)", J[J.job_type == "Breakdown repair"].groupby("m").repair_time_hrs.mean(), 2, 6)
    resp = nonp4.assign(h=[working_minutes_between(a, b) / 60 for a, b in zip(nonp4.request_dt, nonp4.arrival_dt)])
    add("Response time hours (working, mean)", resp.groupby("m").h.mean(), 3, 10)
    asg = nonp4.assign(mn=[working_minutes_between(a, b) for a, b in zip(nonp4.request_dt, nonp4.assigned_dt)])
    add("Assignment time median minutes", asg.groupby("m").mn.median(), 15, 60)
    add("Service report completion %", J.assign(r=J.report_complete == "Y").groupby("m").r.mean(), 90, 99, 100)
    P = pd.DataFrame(proposals)
    P["m"] = P.proposal_dt.dt.strftime("%Y-%m")
    P = P[P.m < "2025-01"]
    P["acc"] = (P.status == "Accepted") & ((P.approval_dt - P.proposal_dt).dt.days <= 45)
    add("AMC conversion % (45-day cohort)", P.groupby("m").acc.mean(), 20, 40, 100)
    fu = P.assign(c=[(len(d) == 0) or (len([x for x, y in zip(d, dn) if y <= x + timedelta(days=1)]) == len(d)) for d, dn in zip(P.followup_due, P.followup_done)])
    add("Follow-up compliance % (all follow-ups on time)", fu.groupby("m").c.mean(), 80, 99, 100)
    C = pd.DataFrame(contracts)
    C = C[C.approval.notna() & C.created.notna()].copy()
    C["m"] = C.created.dt.strftime("%Y-%m")
    C = C[C.m < "2025-01"]
    C["wd"] = [working_days_between(a, b) for a, b in zip(C.approval, C.created)]
    add("Contract processing median working days", C.groupby("m").wd.median(), 1, 4)
    add("Contract accuracy %", 1 - C.groupby("m").correction.mean(), 97, 100, 100)
    return pd.DataFrame(rows)


CAUSE = {"stable": "none", "improving": "none", "scenA": "process", "workload": "workload", "skill": "skill",
         "recovered": "none", "tpo_backlog": "workload", "tpo_leave": "none", "proc_info": "process",
         "stable_proc": "none", "price_pressure": "external"}
NOTES = {"scenA": "Scenario A: complex job mix + spare-part delays (cause = process/supply, not the technician)",
         "tpo_backlog": "Scenario B: one TPO on leave, remaining TPOs absorb the queue (capacity/workload)",
         "proc_info": "Scenario C: incoming proposals with missing approval/equipment details",
         "price_pressure": "Scenario D: AMC price rise + competitor offers; follow-up compliance stays high",
         "tpo_leave": "On extended leave from 2026-06: no activity after May (data gap, no performance judgement)",
         "recovered": "2025: quality decline after new model rollout, training in Jun 2025, recovered",
         "workload": "Overloaded from 2026-04", "skill": "Skill gap on new copier model from 2026-05", "improving": "Gradual improvement from 2025-03"}


def truth_labels(staff) -> pd.DataFrame:
    rows = []
    for e in staff:
        sc = e["scenario"]
        c26 = "none" if (sc == "stable" or e["scenario"] == "proc_info" and False) else CAUSE[sc]
        c25 = "skill" if sc == "recovered" else "none"
        for yr, c in ((2025, c25), (2026, c26)):
            rows.append(dict(employee_no=e["code"], role=e["role"], scenario=sc, cycle_year=yr,
                             has_deviation=c != "none", root_cause=c, note=NOTES.get(sc, "")))
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------- orchestration
def generate_all(seed: int = RANDOM_SEED) -> dict:
    rng = np.random.default_rng(seed)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    TRUTH_DIR.mkdir(parents=True, exist_ok=True)
    periods = month_range(START, END)
    staff = build_staff(rng)
    jobs, _ = generate_jobs(rng, staff, periods)
    proposals, contracts = generate_amc(rng, staff, periods)
    mess = Mess(rng)

    desig = {"technician": ["Technician", "Technician", "Technician", "TECHNICIAN", "Field Technician", "Sr. Technician"],
             "tpo_service": ["TPO - Service", "Transaction Processing Officer (Service)"],
             "amc_processing": ["AMC Processor", "Contract Processing Officer"],
             "contracts_coordinator": ["Contracts Coordinator", "Contract Co-ordinator"]}
    emp = pd.DataFrame([dict(employee_no=s["code"], designation=pick(rng, desig[s["role"]]), base_territory=s["territory"],
                             join_date=date(int(rng.integers(2012, 2025)), int(rng.integers(1, 13)), int(rng.integers(1, 28))).strftime("%d/%m/%Y"),
                             employment_status="On Leave" if s["scenario"] == "tpo_leave" else "Active") for s in staff])
    emp.to_csv(RAW_DIR / "employees.csv", index=False)
    render_jobs(rng, jobs, staff, mess).to_csv(RAW_DIR / "service_jobs.csv", index=False)
    render_proposals(rng, proposals, mess).to_csv(RAW_DIR / "amc_proposals.csv", index=False)
    render_contracts(rng, contracts, mess).to_csv(RAW_DIR / "amc_contracts.csv", index=False)

    att = pd.DataFrame(generate_attendance(rng, staff, periods))
    att["month"] = [pd.Timestamp(p + "-01").strftime("%b-%Y") if p >= "2025-01" else p for p in att.period]
    att[["employee_no", "month", "leave_days", "overtime_hours"]].to_csv(RAW_DIR / "hr_attendance_monthly.csv", index=False)
    dt = pd.DataFrame(generate_downtime(rng, periods))
    dt["start_dt"], dt["end_dt"] = dt.start_dt.dt.strftime("%d/%m/%Y %H:%M"), dt.end_dt.dt.strftime("%d/%m/%Y %H:%M")
    dt.to_csv(RAW_DIR / "system_downtime_log.csv", index=False)
    pd.DataFrame([dict(effective_date=date.fromisoformat(a).strftime("%d/%m/%Y"), product_group="AMC contracts", change_pct=b, remarks=c)
                  for a, b, c in PRICE_CHANGES]).to_csv(RAW_DIR / "price_list_changes.csv", index=False)
    cn = pd.DataFrame(generate_competitor_notes(rng, periods))
    cn["note_date"] = pd.to_datetime(cn.note_date).dt.strftime("%d/%m/%Y")
    cn.to_csv(RAW_DIR / "competitor_notes.csv", index=False)
    pd.DataFrame(generate_reviews(rng, staff)).to_csv(RAW_DIR / "hr_reviews.csv", index=False)
    pd.DataFrame(generate_feedback(rng, staff, periods)).to_csv(RAW_DIR / "employee_feedback.csv", index=False)
    pd.DataFrame([dict(branch=b, service_territory=t) for t, (_, bw) in TERRITORIES.items() for b in bw]).to_csv(RAW_DIR / "branch_territory_map.csv", index=False)
    pd.DataFrame([dict(date=date(y, m, d).strftime("%d/%m/%Y"), holiday=n) for y in (2024, 2025, 2026) for m, d, n in FIXED_HOLIDAYS]).to_csv(RAW_DIR / "public_holidays.csv", index=False)

    truth_labels(staff).to_csv(TRUTH_DIR / "ground_truth_labels.csv", index=False)
    qa = qa_summary(jobs, proposals, contracts)
    qa.to_csv(TRUTH_DIR / "calibration_qa.csv", index=False)
    (TRUTH_DIR / "injected_issues.json").write_text(json.dumps(dict(mess.n), indent=2))
    return {"jobs": len(jobs), "proposals": len(proposals), "contracts": len(contracts), "issues": dict(mess.n), "qa": qa}


if __name__ == "__main__":
    out = generate_all()
    print({k: v for k, v in out.items() if k not in ("qa",)})
    print(out["qa"].to_string(index=False))
