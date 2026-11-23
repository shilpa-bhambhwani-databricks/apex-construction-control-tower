"""Synthetic data for the Control Tower demo — ONE shared, brand-neutral dataset.

Target: bhambs.construction_control_tower  (see PLAN.md)
Run:    .venv/bin/python -I data_gen/generate.py  → data_gen/out/*.parquet

Design
- Raw tables are shaped like Procore / Clearstory / SAP / P6 exports.
- Demo storylines are PLANTED in the raw records (Atlas: 14 RFIs > 21 days, $2.1M pending COs, CO-0142 …).
- Weekly signal sub-scores (project_signal_weekly) are COMPUTED from the raw records as of each week,
  so every number Genie quotes traces back to rows. Formulas live in SIGNAL_FORMULAS below and in the metric view.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import polars as pl

SEED = 20261118
TODAY = date(2026, 11, 9)  # data "as of" date (Monday)
WEEKS_OF_SIGNALS = 26
HISTORY_DAYS = 548  # ~18 months
OUT = Path(__file__).parent / "out"
rng = random.Random(SEED)

SIGNAL_FORMULAS = {
    "rfi": "min(100, 6.3 * open RFIs older than 21 days)",
    "co": "min(100, 50 * pending/disputed CO $M per $B of contract value)",
    "submittal": "min(100, 10 * submittals not returned that are past or within 14 days of required-on-site)",
    "schedule": "clamp(100 - 6 * critical-path float days, 0, 100)",
    "cost": "clamp(1000 * (EAC - budget) / budget, 0, 100)",
    "safety": "min(100, 25 * near-misses + 12 * high-severity + 3 * other observations, trailing 14 days)",
}
WEIGHTS = {"rfi": 0.15, "co": 0.20, "submittal": 0.10, "schedule": 0.20, "cost": 0.25, "safety": 0.10}
REGIONS = ["Northeast", "Midwest", "Southeast", "West", "Southwest"]

# --------------------------------------------------------------------------- projects


@dataclass
class P:
    id: str
    name: str
    sector: str
    region: str
    value_m: float
    pct: int
    target: dict  # current sub-score targets per signal
    trend: str  # 'rising' | 'falling' | 'flat'
    extra: dict = field(default_factory=dict)


# The 12 projects the UI already shows (targets = today's sub-scores in the UI mock).
NAMED = [
    P("P-1001", "Project Atlas — Data Center Campus, Bldg 3", "Data Center", "Northeast", 1240, 46, dict(rfi=88, co=84, submittal=62, schedule=71, cost=66, safety=58), "rising"),
    P("P-1002", "Project Helios — Hyperscale DC Phase 2", "Data Center", "Southwest", 980, 31, dict(rfi=55, co=78, submittal=48, schedule=82, cost=60, safety=40), "rising"),
    P("P-1003", "Project Vega — AI Data Hall", "Data Center", "Midwest", 760, 58, dict(rfi=62, co=70, submittal=74, schedule=54, cost=72, safety=35), "rising"),
    P("P-1004", "Project Meridian — Regional Medical Center", "Healthcare", "Midwest", 540, 64, dict(rfi=40, co=72, submittal=38, schedule=46, cost=81, safety=30), "rising"),
    P("P-1005", "Terminal C Modernization", "Aviation", "Southeast", 690, 39, dict(rfi=58, co=44, submittal=66, schedule=63, cost=47, safety=52), "rising"),
    P("P-1006", "Project Orion — Colocation Facility", "Data Center", "West", 410, 72, dict(rfi=46, co=52, submittal=41, schedule=58, cost=49, safety=62), "falling"),
    P("P-1007", "University Science Complex", "Education", "Northeast", 320, 51, dict(rfi=52, co=36, submittal=58, schedule=42, cost=38, safety=28), "flat"),
    P("P-1008", "Harborview Office Tower", "Commercial", "Northeast", 610, 83, dict(rfi=30, co=48, submittal=22, schedule=38, cost=52, safety=24), "falling"),
    P("P-1009", "Project Nova — Edge Data Center", "Data Center", "Southeast", 220, 22, dict(rfi=34, co=30, submittal=46, schedule=40, cost=28, safety=44), "rising"),
    P("P-1010", "Children’s Hospital Expansion", "Healthcare", "West", 470, 44, dict(rfi=38, co=34, submittal=32, schedule=36, cost=41, safety=26), "flat"),
    P("P-1011", "Riverside K-12 Campus", "Education", "Southwest", 140, 67, dict(rfi=22, co=18, submittal=30, schedule=26, cost=20, safety=34), "falling"),
    P("P-1012", "Concourse B Expansion", "Aviation", "West", 380, 18, dict(rfi=28, co=26, submittal=20, schedule=32, cost=24, safety=18), "flat"),
]

EXTRA_NAMES = {
    "Data Center": ["Project Lumen — Cloud Campus Bldg 1", "Project Tessera — Liquid-Cooled Data Hall", "Project Quarry — Edge DC Cluster"],
    "Healthcare": ["Lakeside Behavioral Health Center", "St. Brendan Surgical Tower", "Northgate Ambulatory Care", "Valley Cancer Institute", "Mercy West Patient Tower", "Bayfront Medical Office Building"],
    "Aviation": ["Terminal A Baggage Upgrade", "Airside Concourse D", "Consolidated Rental Car Facility", "Air Traffic Control Tower"],
    "Commercial": ["One Market Plaza Renovation", "Hudson Yards West Office", "Parkline Mixed-Use Tower", "Gateway Corporate HQ", "Riverfront Hotel & Residences", "Lakeshore Life Sciences Lab", "Midtown Office Retrofit", "Seaport Innovation Center"],
    "Education": ["State University Engineering Hall", "Westfield High School", "Community College Health Sciences", "Oakridge Middle School", "University Student Union", "Lincoln Elementary Replacement", "Medical School Research Wing"],
}


def make_projects() -> list[P]:
    ps = list(NAMED)
    n = 1013
    for sector, names in EXTRA_NAMES.items():
        for name in names:
            base = rng.randint(15, 45)
            tgt = {k: max(5, min(95, base + rng.randint(-15, 18))) for k in WEIGHTS}
            ps.append(P(f"P-{n}", name, sector, rng.choice(REGIONS), rng.choice([90, 140, 210, 280, 350, 420, 520, 650]),
                        rng.randint(12, 90), tgt, rng.choice(["flat", "flat", "rising", "falling"])))
            n += 1
    return ps


# --------------------------------------------------------------------------- helpers

SUBS = {
    "Data Center": [("Keystone Concrete LLC", "03-3000"), ("Ironline Steel Erectors", "05-1200"), ("Brightway Electric", "26-0500"), ("Northgate Mechanical", "23-0500"), ("Summit Sitework", "31-2000")],
    "Healthcare": [("Northgate Mechanical", "23-0500"), ("Riverbend Plumbing", "22-1000"), ("Summit Interiors", "09-2900"), ("Brightway Electric", "26-0500"), ("Keystone Concrete LLC", "03-3000")],
    "Aviation": [("Tarmac Partners", "32-1200"), ("Ironline Steel Erectors", "05-1200"), ("Brightway Electric", "26-0500"), ("Clearcut Demo", "02-4100")],
    "Education": [("Cornerstone Masonry", "04-2000"), ("Apex Roofing", "07-5000"), ("Keystone Concrete LLC", "03-3000"), ("Northgate Mechanical", "23-0500")],
    "Commercial": [("Keystone Concrete LLC", "03-3000"), ("Skyline Facades", "08-4400"), ("Brightway Electric", "26-0500"), ("Northgate Mechanical", "23-0500")],
}
DISCIPLINES = ["Structural", "Architectural", "Mechanical", "Electrical", "Plumbing", "Civil", "Fire Protection"]
RFI_SUBJECTS = {
    "Structural": ["Embed plate conflict at beam pocket", "Connection detail clarification", "Slab edge dimension mismatch", "Rebar congestion at column"],
    "Architectural": ["Door hardware schedule conflict", "Wall type at corridor", "Ceiling height clash with duct"],
    "Mechanical": ["Duct routing vs. structure", "Equipment pad dimensions", "Chilled water valve location"],
    "Electrical": ["Duct bank routing vs. footing", "Panel location conflict", "Conduit sleeve locations"],
    "Plumbing": ["Floor drain location", "Medical gas outlet count", "Sanitary invert elevation"],
    "Civil": ["Storm inlet elevation", "Utility crossing depth"],
    "Fire Protection": ["Sprinkler head layout vs. ceiling", "Standpipe location"],
}
SPEC = ["03 30 00", "05 12 00", "07 84 00", "08 44 13", "23 31 13", "26 24 13", "26 05 43", "22 11 16"]
COST_CODES = ["01-5000", "02-4100", "03-3000", "04-2000", "05-1200", "07-5000", "08-4400", "09-2900", "22-1000", "23-0500", "26-0500", "31-2000", "32-1200"]
OBS_CATS = ["Fall protection", "Housekeeping", "PPE", "Excavation", "Electrical", "Crane/rigging", "Ladders", "Struck-by"]


def d(days_ago: int) -> date:
    return TODAY - timedelta(days=days_ago)


def rid(prefix: str, n: int) -> str:
    return f"{prefix}-{n:04d}"


# --------------------------------------------------------------------------- generators


def gen_all(projects: list[P]):
    projects_rows, rfis, cos, subs, acts, floats, cost, obs = [], [], [], [], [], [], [], []
    rfi_n, co_n, sub_n, act_n, obs_n = 100, 100, 100, 100, 100
    pe_names = ["Jordan Ellis", "Priya Raman", "Marcus Hale", "Elena Ruiz", "Sam Okoye", "Grace Liu", "Tom Becker", "Nina Patel"]
    supers = ["Dana Morales", "Chris Okafor", "Sam Whitfield", "Lee Park", "Avery Brooks", "Morgan Diaz", "Jesse Nguyen", "Riley Chen", "Taylor Grant", "Jordan Price", "Casey Lopez", "Drew Patel"]

    for i, p in enumerate(projects):
        t, rising, falling = p.target, p.trend == "rising", p.trend == "falling"
        # Share of today's issues that already existed ~8 weeks ago (shapes the 8-week trend).
        base = 0.62 if rising else 1.0 if falling else 0.95
        start = d(int(HISTORY_DAYS * (0.4 + p.pct / 100 * 0.6)))
        projects_rows.append(dict(
            project_id=p.id, name=p.name, market_sector=p.sector, region=p.region,
            business_unit=f"{p.region} BU", contract_value=round(p.value_m * 1e6, 2),
            bid_margin_pct=round(rng.uniform(5.5, 8.5), 2), start_date=start,
            substantial_completion_date=start + timedelta(days=int((TODAY - start).days / max(p.pct, 5) * 100)),
            pct_complete=p.pct, project_executive=pe_names[i % len(pe_names)], superintendent=supers[i % len(supers)],
        ))

        # ---- schedule activities (P6) + weekly critical-path float snapshots
        act_ids = []
        for k in range(24):
            a_id = f"A{act_n}"; act_n += 1
            ps = TODAY + timedelta(days=rng.randint(-120, 60))
            crit = k < 6
            acts.append(dict(activity_id=a_id, project_id=p.id, wbs=f"{p.id}.{k // 6 + 1}.{k % 6 + 1}",
                             activity_name=f"Activity {k + 1}", trade=rng.choice(["Concrete", "Steel erection", "Electrical", "Mechanical", "Sitework", "Interiors"]),
                             planned_start=ps, planned_finish=ps + timedelta(days=rng.randint(5, 40)),
                             actual_start=ps if ps < TODAY and rng.random() < 0.8 else None,
                             total_float_days=rng.randint(0, 8) if crit else rng.randint(8, 40), critical_flag=crit))
            act_ids.append(a_id)
        f_now = max(0.0, (100 - t["schedule"]) / 6)
        for w in range(WEEKS_OF_SIGNALS):
            delta = (1 - base) * t["schedule"] / 6 if rising else (-0.25 * t["schedule"] / 6 if falling else 0.3)
            drift = min(w / 8, 1.5) * delta
            floats.append(dict(project_id=p.id, week=d(7 * w), critical_path_float_days=round(max(0.0, f_now + drift + rng.uniform(-0.3, 0.3)), 1)))

        # ---- RFIs (Procore): aging count planted to hit target; rising projects cross 21 days recently
        n_age = round(t["rfi"] / 6.3)
        n_base = round(n_age * base)
        for j in range(n_age):
            age = rng.randint(80, 150) if j < n_base else rng.randint(22, 75)
            disc = rng.choice(DISCIPLINES)
            rfis.append(dict(rfi_id=rid("RFI", rfi_n), project_id=p.id, subject=rng.choice(RFI_SUBJECTS[disc]), discipline=disc, status="Open",
                             created_date=d(age), due_date=d(age - 10), closed_date=None, ball_in_court=rng.choice(["Architect", "Structural engineer", "MEP engineer", "Owner"]),
                             cost_impact_flag=rng.random() < 0.4, schedule_impact_flag=rng.random() < 0.5, activity_id=rng.choice(act_ids)))
            rfi_n += 1
        for _ in range(round(n_age * 0.35) if falling else 0):  # resolved recently → score fell
            disc = rng.choice(DISCIPLINES); created = rng.randint(85, 140)
            rfis.append(dict(rfi_id=rid("RFI", rfi_n), project_id=p.id, subject=rng.choice(RFI_SUBJECTS[disc]), discipline=disc, status="Closed",
                             created_date=d(created), due_date=d(created - 10), closed_date=d(rng.randint(1, 27)), ball_in_court=None,
                             cost_impact_flag=False, schedule_impact_flag=False, activity_id=rng.choice(act_ids)))
            rfi_n += 1
        for _ in range(rng.randint(3, 8)):  # fresh open RFIs
            disc = rng.choice(DISCIPLINES); age = rng.randint(1, 20)
            rfis.append(dict(rfi_id=rid("RFI", rfi_n), project_id=p.id, subject=rng.choice(RFI_SUBJECTS[disc]), discipline=disc, status="Open",
                             created_date=d(age), due_date=d(age - 10), closed_date=None, ball_in_court=rng.choice(["Architect", "Structural engineer", "MEP engineer"]),
                             cost_impact_flag=rng.random() < 0.3, schedule_impact_flag=rng.random() < 0.3, activity_id=rng.choice(act_ids)))
            rfi_n += 1
        for _ in range(rng.randint(40, 120)):  # closed history; falling projects closed a batch of aged RFIs recently
            disc = rng.choice(DISCIPLINES)
            created = rng.randint(30, (TODAY - start).days or 31)
            turnaround = rng.randint(25, 45) if (falling and created < 90) else rng.randint(3, 18)
            closed = max(0, created - turnaround)
            rfis.append(dict(rfi_id=rid("RFI", rfi_n), project_id=p.id, subject=rng.choice(RFI_SUBJECTS[disc]), discipline=disc, status="Closed",
                             created_date=d(created), due_date=d(created - 10), closed_date=d(closed), ball_in_court=None,
                             cost_impact_flag=rng.random() < 0.2, schedule_impact_flag=rng.random() < 0.2, activity_id=rng.choice(act_ids)))
            rfi_n += 1

        # ---- Change orders (Clearstory): pending $ planted to hit target
        pending_m = t["co"] / 50 * (p.value_m / 1000)
        n_pend = rng.randint(3, 6)
        shares = [rng.random() for _ in range(n_pend)]
        sector_subs = SUBS[p.sector]
        acc = 0.0
        for k, s in enumerate(shares):
            amt = round(pending_m * 1e6 * s / sum(shares), -2)
            sub, code = sector_subs[k % len(sector_subs)]
            old = acc < base * pending_m * 1e6
            acc += amt
            age = rng.randint(60, 120) if old else rng.randint(5, 55)
            cos.append(dict(co_id=rid("CO", co_n), project_id=p.id, subcontractor=sub, cost_code=code,
                            description=f"Additional scope — {code}", status=rng.choice(["Pending", "Pending", "Disputed"]),
                            amount_requested=amt, amount_approved=None, submitted_date=d(age), decision_date=None, source_system="Clearstory"))
            co_n += 1
        for _ in range(rng.randint(10, 30)):
            sub, code = rng.choice(sector_subs); age = rng.randint(60, max(61, (TODAY - start).days))
            req = round(p.value_m * 1e6 * rng.uniform(0.00008, 0.0006), -2)  # sized to the job
            cos.append(dict(co_id=rid("CO", co_n), project_id=p.id, subcontractor=sub, cost_code=code, description=f"Change — {code}",
                            status=rng.choice(["Approved", "Approved", "Approved", "Rejected"]), amount_requested=req,
                            amount_approved=round(req * rng.uniform(0.7, 1.0), -2), submitted_date=d(age), decision_date=d(age - rng.randint(5, 15)), source_system="Clearstory"))
            co_n += 1
        if falling:  # COs that were pending 8 weeks ago and got approved in the last month
            for _ in range(2):
                sub, code = rng.choice(sector_subs); req = round(pending_m * 1e6 * 0.15, -2)
                cos.append(dict(co_id=rid("CO", co_n), project_id=p.id, subcontractor=sub, cost_code=code, description=f"Change — {code}",
                                status="Approved", amount_requested=req, amount_approved=round(req * 0.9, -2), submitted_date=d(rng.randint(70, 110)),
                                decision_date=d(rng.randint(3, 28)), source_system="Clearstory"))
                co_n += 1

        # ---- Submittals (Procore)
        n_over = round(t["submittal"] / 10)
        for j in range(n_over):
            req = d(rng.randint(45, 90)) if j < round(n_over * base) else TODAY + timedelta(days=rng.randint(-10, 13))
            subs.append(dict(submittal_id=rid("SUB", sub_n), project_id=p.id, spec_section=rng.choice(SPEC), status=rng.choice(["Submitted", "Revise & Resubmit"]),
                             required_on_site_date=req, returned_date=None)); sub_n += 1
        for _ in range(rng.randint(20, 60)):
            req = d(rng.randint(-60, 300))
            subs.append(dict(submittal_id=rid("SUB", sub_n), project_id=p.id, spec_section=rng.choice(SPEC), status="Approved",
                             required_on_site_date=req, returned_date=req - timedelta(days=rng.randint(10, 40)))); sub_n += 1

        # ---- Job cost (SAP), monthly: EAC overrun ramps to target
        over_now = t["cost"] / 1000
        codes = rng.sample(COST_CODES, 8)
        budgets = [p.value_m * 1e6 * w for w in _split(8)]
        for m in range(18):
            period = date(TODAY.year, TODAY.month, 1) - timedelta(days=30 * m)
            period = date(period.year, period.month, 1)
            ramp = over_now * (1 - (1 - base) * min(m, 2) / 2 - 0.05 * max(0, m - 2)) if rising else over_now * (1 + 0.15 * min(m, 2)) if falling else over_now * (1 - 0.02 * m)
            ramp = max(0.0, ramp)
            frac_done = max(0.02, p.pct / 100 - m * 0.03)
            for c, b in zip(codes, budgets):
                eac = b * (1 + ramp * rng.uniform(0.8, 1.2))
                cost.append(dict(project_id=p.id, cost_code=c, period=period, budget=round(b, 2),
                                 committed=round(eac * min(1, frac_done + 0.25), 2), actual=round(eac * frac_done, 2), eac=round(eac, 2)))

        # ---- Safety observations (Procore / Origami): trailing-14-day mix planted to hit target
        nm = round(t["safety"] / 28)
        rest = max(0, t["safety"] - 25 * nm)
        hi = rest // 12
        lo = (rest - 12 * hi) // 3
        for kind, cnt in (("near", nm), ("high", hi), ("low", lo)):
            for _ in range(cnt):
                obs.append(dict(obs_id=rid("OBS", obs_n), project_id=p.id, date=d(rng.randint(0, 13)), category=rng.choice(OBS_CATS),
                                severity="High" if kind != "low" else rng.choice(["Low", "Medium"]), near_miss_flag=kind == "near",
                                description=f"{'Near miss' if kind == 'near' else 'Observation'} — synthetic")); obs_n += 1
        hist_scale = base if rising else 1.3 if falling else 0.95
        for blk in range(1, 14):  # each earlier 14-day window gets a similar mix → realistic trailing-14-day history
            for kind, cnt in (("near", round(nm * hist_scale)), ("high", round(hi * hist_scale)), ("low", round(lo * hist_scale))):
                for _ in range(cnt):
                    obs.append(dict(obs_id=rid("OBS", obs_n), project_id=p.id, date=d(14 * blk + rng.randint(0, 13)), category=rng.choice(OBS_CATS),
                                    severity="High" if kind != "low" else rng.choice(["Low", "Medium"]), near_miss_flag=kind == "near",
                                    description=f"{'Near miss' if kind == 'near' else 'Observation'} — synthetic")); obs_n += 1
        for _ in range(rng.randint(0, 0)):  # (old random history replaced by windowed history above)
            obs.append(dict(obs_id=rid("OBS", obs_n), project_id=p.id, date=d(rng.randint(14, 400)), category=rng.choice(OBS_CATS),
                            severity=rng.choice(["Low", "Low", "Medium", "High"]), near_miss_flag=rng.random() < 0.1, description="Observation — synthetic")); obs_n += 1

    plant_atlas(rfis, cos)
    return dict(projects=projects_rows, rfis=rfis, change_orders=cos, submittals=subs, schedule_activities=acts,
                schedule_float_weekly=floats, job_cost=cost, safety_observations=obs)


def _split(n: int) -> list[float]:
    xs = [rng.random() + 0.3 for _ in range(n)]
    return [x / sum(xs) for x in xs]


def plant_atlas(rfis: list[dict], cos: list[dict]) -> None:
    """Make the named Atlas items in the UI exist verbatim (Resolve + Jobsite storyboards)."""
    a_rfis = [r for r in rfis if r["project_id"] == "P-1001" and r["status"] == "Open" and (TODAY - r["created_date"]).days > 21]
    named = [("RFI-0387", "Embed plate conflict at L2 beam", "Structural", 26), ("RFI-0391", "Duct bank routing vs. footing F-12", "Electrical", 23), ("RFI-0352", "Rock at pile caps PC-14–22", "Civil", 41)]
    for r, (rid_, subj, disc, age) in zip(a_rfis, named):
        r.update(rfi_id=rid_, subject=subj, discipline=disc, created_date=d(age), due_date=d(age - 10), schedule_impact_flag=True)
    # Replace the NEWEST pending COs so the older (baseline) ones keep shaping the 8-week trend.
    a_cos = sorted([c for c in cos if c["project_id"] == "P-1001" and c["status"] in ("Pending", "Disputed")], key=lambda c: c["submitted_date"], reverse=True)
    planted = [("CO-0142", "Keystone Concrete LLC", "03-3000", "Additional foundation work — subsurface rock", 486000, 12),
               ("CO-0139", "Ironline Steel Erectors", "05-1200", "Revised embed plates, Level 2 (ASI-031)", 122400, 7)]
    for c, (cid, sub, code, desc, amt, age) in zip(a_cos, planted):
        c.update(co_id=cid, subcontractor=sub, cost_code=code, description=desc, amount_requested=amt, status="Pending", submitted_date=d(age))
    # Planted IDs must be unique: renumber any generated row that collides with a planted ID.
    for rows, key, prefix, planted_ids in ((rfis, "rfi_id", "RFI", {"RFI-0387", "RFI-0391", "RFI-0352"}), (cos, "co_id", "CO", {"CO-0142", "CO-0139"})):
        nxt = max(int(r[key].split("-")[1]) for r in rows) + 1
        for r in rows:
            if r[key] in planted_ids and r["project_id"] != "P-1001":
                r[key] = rid(prefix, nxt); nxt += 1
    # Keep Atlas pending total at ~$2.1M: rescale the other pending COs.
    rest = [c for c in a_cos if c["co_id"] not in ("CO-0142", "CO-0139")]
    remaining = 2_080_000 - 486_000 - 122_400
    tot = sum(c["amount_requested"] for c in rest) or 1
    for c in rest:
        c["amount_requested"] = round(c["amount_requested"] / tot * remaining, -2)


# --------------------------------------------------------------------------- weekly signals (computed from raw)


def weekly_signals(t: dict) -> list[dict]:
    projects = {p["project_id"]: p for p in t["projects"]}
    by = lambda rows: _group(rows)  # noqa: E731
    rfis, cos, subs, obs, cost, flt = by(t["rfis"]), by(t["change_orders"]), by(t["submittals"]), by(t["safety_observations"]), by(t["job_cost"]), by(t["schedule_float_weekly"])
    out = []
    for pid, p in projects.items():
        for w in range(WEEKS_OF_SIGNALS):
            asof = d(7 * w)
            aging = sum(1 for r in rfis.get(pid, []) if r["created_date"] <= asof - timedelta(days=21) and (r["closed_date"] is None or r["closed_date"] > asof))
            pend = sum(c["amount_requested"] for c in cos.get(pid, []) if c["submitted_date"] <= asof and (c["decision_date"] is None or c["decision_date"] > asof))
            over = sum(1 for s in subs.get(pid, []) if s["returned_date"] is None and s["required_on_site_date"] <= asof + timedelta(days=14))
            fl = next((f["critical_path_float_days"] for f in flt.get(pid, []) if f["week"] == asof), 10.0)
            month = max((c["period"] for c in cost.get(pid, []) if c["period"] <= asof), default=None)
            rows = [c for c in cost.get(pid, []) if c["period"] == month]
            b, e = sum(c["budget"] for c in rows) or 1, sum(c["eac"] for c in rows)
            win = [o for o in obs.get(pid, []) if asof - timedelta(days=13) <= o["date"] <= asof]
            nm = sum(1 for o in win if o["near_miss_flag"]); hi = sum(1 for o in win if not o["near_miss_flag"] and o["severity"] == "High")
            lo = len(win) - nm - hi
            scores = dict(
                rfi=min(100, 6.3 * aging),
                co=min(100, 50 * (pend / 1e6) / (p["contract_value"] / 1e9)),
                submittal=min(100, 10 * over),
                schedule=max(0, min(100, 100 - 6 * fl)),
                cost=max(0, min(100, 1000 * (e - b) / b)),
                safety=min(100, 25 * nm + 12 * hi + 3 * lo),
            )
            raw = dict(rfi=aging, co=pend, submittal=over, schedule=fl, cost=(e - b) / b, safety=len(win))
            for k, v in scores.items():
                out.append(dict(project_id=pid, week=asof, signal=k, sub_score=round(v, 1), raw_value=round(float(raw[k]), 4), weight=WEIGHTS[k]))
    return out


def _group(rows: list[dict]) -> dict:
    g: dict = {}
    for r in rows:
        g.setdefault(r["project_id"], []).append(r)
    return g


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tables = gen_all(make_projects())
    tables["project_signal_weekly"] = weekly_signals(tables)
    for name, rows in tables.items():
        pl.DataFrame(rows, infer_schema_length=None).write_parquet(OUT / f"{name}.parquet")
        print(f"{name:24s} {len(rows):>7,} rows")
    # Quick check vs. UI targets for the storyline projects
    sig = pl.DataFrame(tables["project_signal_weekly"])
    now = sig.filter(pl.col("week") == TODAY).with_columns((pl.col("sub_score") * pl.col("weight")).alias("pts"))
    then = sig.filter(pl.col("week") == d(56)).with_columns((pl.col("sub_score") * pl.col("weight")).alias("pts"))
    s_now = now.group_by("project_id").agg(pl.col("pts").sum().round(0).alias("score_now"))
    s_then = then.group_by("project_id").agg(pl.col("pts").sum().round(0).alias("score_8w_ago"))
    print(s_now.join(s_then, on="project_id").sort("score_now", descending=True).head(14))


if __name__ == "__main__":
    main()
