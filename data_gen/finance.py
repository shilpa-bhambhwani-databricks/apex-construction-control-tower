"""Demo 2 (Office of the CFO — margin fade) synthetic finance layer — SHARED, brand-neutral.

READ-ONLY on the Demo 1 data (data_gen/out/*.parquet). Writes only to data_gen/out_finance/. Separate RNG, so Demo 1 rows
never shift. Every new number reconciles to the existing job_cost overruns (EAC - budget):

  cost_variance_log   (project, cost_code, period, cause) — SUM(amount) == job_cost.eac - job_cost.budget, every row
  purchase_orders     material buyout by cost code; price/tariff/freight variance == the matching causes x committed share
  vendor_invoice_lines invoiced share of each PO (base, price escalation, tariff surcharge, freight, storage)
  project_financials  per project: bid gross profit, contingency, buyout savings, alert threshold (fade > 1.5 pts)
  commodity_index     monthly price indices (structural steel incl. tariff pass-through, rebar, ready-mix, copper, switchgear)
  cost_codes          CSI-style cost code names

Projected margin (computed in SQL, scripts/14_finance.sql):
  net cost growth    = SUM(eac - budget) - approved change-order revenue
  cushion            = contingency + buyout savings
  margin fade ($)    = GREATEST(net cost growth - cushion, 0)
  projected margin % = (bid gross profit - margin fade) / (contract value + approved CO revenue)

Planted storylines (one per classic margin-fade pattern):
  * Atlas   (P-1001) HERO  — cushion exhausted in Oct; 5.5% bid → ~3.1%. Biggest single driver: structural steel 05-1200
             price escalation + tariff pass-through. Prime Contract Art. 7 lets the GC recover the steel index increase above 5%
             if requested within 10 days of each PO — no request has been filed on any PO. Two POs are still inside the window.
             Plus scope leakage: $2.08M of field work on pending/disputed COs (existing CO-0101/0102/0139/0142).
  * Meridian (P-1004)      — input cost + logistics: tariffs on imported switchgear/AHUs, switchgear delivered 7 weeks early →
             bonded-warehouse storage + double handling; prime contract tariff clause (21-day notice).
  * Vega    (P-1003)       — cost-at-completion creep: concrete quantity overrun vs takeoff + labor productivity (PF ~1.18).
Run: .venv/bin/python -I data_gen/finance.py
"""
from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

import polars as pl

rng = random.Random(2026_1118)
ROOT = Path(__file__).parent
SRC, OUT = ROOT / "out", ROOT / "out_finance"
TODAY = date(2026, 11, 9)
FADE_ALERT_PTS = 1.5

COST_CODES = {
    "01-5000": ("Temporary facilities & general conditions", "01"), "02-4100": ("Demolition & site clearing", "02"),
    "03-3000": ("Cast-in-place concrete", "03"), "04-2000": ("Unit masonry", "04"), "05-1200": ("Structural steel framing", "05"),
    "07-5000": ("Membrane roofing", "07"), "08-4400": ("Curtain wall & glazed assemblies", "08"), "09-2900": ("Gypsum board", "09"),
    "22-1000": ("Plumbing piping", "22"), "23-0500": ("HVAC — common work & equipment", "23"), "26-0500": ("Electrical — common work & switchgear", "26"),
    "31-2000": ("Earth moving", "31"), "32-1200": ("Flexible paving", "32"),
}
PRICE, QTY, PROD, LOGI, GC = ("Material price escalation / tariff", "Quantity overrun vs. takeoff", "Labor productivity",
                              "Logistics, freight & storage", "Schedule extension (extended general conditions)")
CAUSES = [PRICE, QTY, PROD, LOGI, GC]

# Material buyout: which cost codes are bought on POs, the material share of the code, supplier, index, tariff share of price variance
MATERIAL = {
    "05-1200": (0.55, "Northbridge Steel Supply", "Structural steel (mill, incl. tariff pass-through)", "Wide-flange structural steel", "TON", 0.45),
    "03-3000": (0.45, "Summit Ready-Mix & Rebar", "Ready-mix concrete", "Ready-mix concrete 5,000 psi + rebar", "CY", 0.0),
    "26-0500": (0.50, "Corvane Electrical Equipment", "Electrical switchgear (PPI)", "Medium-voltage switchgear & distribution", "EA", 0.50),
    "23-0500": (0.50, "Aeromark HVAC Equipment", "Copper", "Air handling units & chillers", "EA", 0.40),
    "08-4400": (0.55, "ClearSpan Facade Systems", "Aluminum extrusions", "Unitized curtain wall panels", "SF", 0.30),
}
UNIT_PRICE = {"TON": 4200.0, "CY": 210.0, "EA": 185000.0, "SF": 118.0}

# Cause shares by project and cost code (hero storylines). Shares sum to 1.
HERO = {
    "P-1001": {  # Atlas
        "05-1200": {PRICE: 0.90, LOGI: 0.10}, "23-0500": {PRICE: 0.35, PROD: 0.65}, "04-2000": {PROD: 0.60, QTY: 0.40},
        "02-4100": {QTY: 0.70, PROD: 0.30}, "31-2000": {QTY: 0.80, PROD: 0.20}, "01-5000": {LOGI: 0.35, GC: 0.65},
        "09-2900": {PROD: 0.50, QTY: 0.50}, "22-1000": {PRICE: 0.50, PROD: 0.50},
    },
    "P-1004": {  # Meridian
        "23-0500": {PRICE: 0.60, PROD: 0.40}, "32-1200": {QTY: 0.70, PROD: 0.30}, "09-2900": {PROD: 0.60, QTY: 0.40},
        "01-5000": {LOGI: 0.12, GC: 0.88}, "04-2000": {PROD: 0.50, QTY: 0.50}, "05-1200": {PRICE: 0.85, LOGI: 0.15},
        "31-2000": {QTY: 1.0}, "26-0500": {PRICE: 0.55, LOGI: 0.45},
    },
    "P-1003": {  # Vega
        "03-3000": {QTY: 0.55, PROD: 0.45}, "04-2000": {PROD: 0.70, QTY: 0.30}, "05-1200": {PROD: 0.50, PRICE: 0.35, QTY: 0.15},
        "08-4400": {PROD: 0.60, QTY: 0.40}, "22-1000": {PROD: 0.70, QTY: 0.30}, "26-0500": {PROD: 0.60, PRICE: 0.40},
        "32-1200": {QTY: 0.60, PROD: 0.40}, "23-0500": {PROD: 0.70, PRICE: 0.30},
    },
}
HERO_FADE_PTS = {"P-1001": 2.4, "P-1004": 2.6, "P-1003": 2.2}
WATCH_FADE_PTS = {"P-1002": 1.1}  # Helios: on the edge, below the alert threshold
BID_DATE = {"P-1001": date(2025, 4, 2)}
MER_SW_ARRIVAL, MER_SW_RAS = date(2026, 7, 20), date(2026, 9, 8)  # switchgear arrival vs required-on-site date (7 weeks early)
MER_STORAGE_WK, MER_REHANDLE = 8600.0, 1450.0
MER_STORAGE_WEEKS = 19  # committed: through mid-Dec (electrical rooms ready)
MER_STORAGE_TOTAL = MER_STORAGE_WK * MER_STORAGE_WEEKS + MER_REHANDLE  # matches Prime_Contract_Atlas_Bldg3.pdf


def month_add(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    return date(d.year + y, m + 1, 1)


# --------------------------------------------------------------------------- commodity index
def commodity_index() -> list[dict]:
    """Monthly indices, Jan 2024 = 100. Steel jumps with tariff pass-through from mid-2025 and again in Sep-Oct 2026."""
    rows, start = [], date(2024, 1, 1)
    for i in range(35):  # Jan 2024 .. Nov 2026
        m = month_add(start, i)
        t = i / 34
        steel = 100 + (2 if i < 17 else 2 + 0.95 * (i - 17)) + (4.5 if m >= date(2026, 9, 1) else 0) + (2.0 if m >= date(2026, 10, 1) else 0)
        vals = {"Structural steel (mill, incl. tariff pass-through)": steel, "Rebar": 100 + 9 * t, "Ready-mix concrete": 100 + 6.5 * t,
                "Copper": 100 + 21 * t ** 1.3, "Electrical switchgear (PPI)": 100 + 16 * t ** 1.2, "Aluminum extrusions": 100 + 8 * t}
        rows += [dict(month=m, commodity=k, index_value=round(v + rng.uniform(-0.4, 0.4), 1)) for k, v in vals.items()]
    return rows


def idx(ci: pl.DataFrame, commodity: str, d: date) -> float:
    r = ci.filter((pl.col("commodity") == commodity) & (pl.col("month") == date(d.year, d.month, 1)))
    return r["index_value"][0] if r.height else 100.0


# --------------------------------------------------------------------------- main build
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    projects = pl.read_parquet(SRC / "projects.parquet")
    jc = pl.read_parquet(SRC / "job_cost.parquet")
    co = pl.read_parquet(SRC / "change_orders.parquet")
    ci = pl.DataFrame(commodity_index())
    last = jc["period"].max()

    # ---- cost_variance_log: split every existing (eac - budget) into causes
    shares: dict[tuple[str, str], dict[str, float]] = {}
    for pid, code in jc.select("project_id", "cost_code").unique().iter_rows():
        if pid in HERO and code in HERO[pid]:
            shares[(pid, code)] = HERO[pid][code]
            continue
        w = {PROD: rng.uniform(0.3, 0.6), QTY: rng.uniform(0.2, 0.5), GC: rng.uniform(0.0, 0.15) if code == "01-5000" else 0.0,
             PRICE: rng.uniform(0.15, 0.4) if code in MATERIAL else 0.0, LOGI: rng.uniform(0.0, 0.08) if code in MATERIAL else 0.0}
        s = sum(w.values())
        shares[(pid, code)] = {k: v / s for k, v in w.items() if v > 0}
    NOTE = {PRICE: "Supplier price increase over bid unit price (incl. tariff surcharges) — see purchase_orders / vendor_invoice_lines",
            QTY: "Installed quantities above estimate takeoff", PROD: "Crew hours per unit above estimate (productivity factor > 1.0)",
            LOGI: "Freight, expediting, storage and re-handling not in estimate", GC: "Extended field staff, temp power and site services"}
    cvl = []
    for pid, code, period, budget, eac in jc.select("project_id", "cost_code", "period", "budget", "eac").iter_rows():
        var = eac - budget
        items = list(shares[(pid, code)].items())
        acc = 0.0
        for i, (cause, sh) in enumerate(items):
            amt = round(var - acc, 2) if i == len(items) - 1 else round(var * sh, 2)
            acc += amt
            cvl.append(dict(project_id=pid, cost_code=code, period=period, cause=cause, amount=amt, note=NOTE[cause]))
    cvl_df = pl.DataFrame(cvl)

    # ---- project_financials: tune the cushion so only the planted projects fade past the threshold
    approved = co.filter(pl.col("status") == "Approved")
    growth_now = jc.filter(pl.col("period") == last).group_by("project_id").agg((pl.col("eac") - pl.col("budget")).sum().alias("g"))
    appr_now = approved.filter(pl.col("decision_date") <= TODAY).group_by("project_id").agg(pl.col("amount_approved").sum().alias("a"))
    fin = []
    for p in projects.join(growth_now, on="project_id").join(appr_now, on="project_id", how="left").fill_null(0).iter_rows(named=True):
        cv, bm, pid = p["contract_value"], p["bid_margin_pct"], p["project_id"]
        net, rev = p["g"] - p["a"], cv + p["a"]
        if pid in HERO_FADE_PTS or pid in WATCH_FADE_PTS:
            cushion = net - (HERO_FADE_PTS.get(pid) or WATCH_FADE_PTS[pid]) / 100 * rev
        else:
            cushion = net * rng.uniform(0.95, 1.12)
        cont = cushion * rng.uniform(0.6, 0.72)
        bid_date = BID_DATE.get(pid, p["start_date"] - timedelta(days=rng.randint(120, 220)))
        fin.append(dict(project_id=pid, bid_date=bid_date, contract_value=cv, bid_margin_pct=bm, bid_gross_profit=round(cv * bm / 100, 2),
                        contingency_budget=round(cont, 2), buyout_savings=round(cushion - cont, 2), fade_alert_threshold_pts=FADE_ALERT_PTS,
                        project_controls_manager=rng.choice(["Alex Romero", "Jamie Cho", "Pat Sullivan", "Robin Shah", "Kerry Adams"])))
    fin_df = pl.DataFrame(fin)

    # ---- purchase_orders + vendor_invoice_lines (material buyout), reconciled to the variance causes
    jl = jc.filter(pl.col("period") == last)
    cause_now = cvl_df.filter(pl.col("period") == last)
    pos, inv = [], []
    po_n, inv_n = 5000, 70000
    for r in jl.join(projects.select("project_id", "pct_complete", "start_date"), on="project_id").iter_rows(named=True):
        code, pid = r["cost_code"], r["project_id"]
        if code not in MATERIAL:
            continue
        m_share, vendor, commodity, material, uom, tariff_share = MATERIAL[code]
        c = {k: v for k, v in cause_now.filter((pl.col("project_id") == pid) & (pl.col("cost_code") == code)).select("cause", "amount").iter_rows()}
        price_v, logi_v = c.get(PRICE, 0.0), c.get(LOGI, 0.0)
        if pid == "P-1004" and code == "26-0500":
            logi_v -= MER_STORAGE_TOTAL  # storage is billed on its own PO (PO-MER-STOR) below — keep the cause total reconciled
        mat_eac = m_share * r["eac"]
        com_f, act_f = r["committed"] / r["eac"], r["actual"] / r["eac"]
        base_total = mat_eac - price_v - logi_v  # bid-price basis of all material for this code
        bid_d = fin_df.filter(pl.col("project_id") == pid)["bid_date"][0]
        i_bid = idx(ci, commodity, bid_d)
        # PO dates: from 60 days after start through the as-of date; Atlas steel gets 14 POs, two inside the Art. 7 window
        n = 14 if (pid == "P-1001" and code == "05-1200") else rng.randint(3, 6)
        first = r["start_date"] + timedelta(days=60)
        span = max(30, (TODAY - first).days - 5)
        dates = sorted(first + timedelta(days=int(span * (k + rng.uniform(0.1, 0.9)) / n)) for k in range(n))
        if pid == "P-1001" and code == "05-1200":
            dates[-2], dates[-1] = date(2026, 11, 3), date(2026, 11, 6)
        weights = [rng.uniform(0.7, 1.3) for _ in dates]
        ws = sum(weights)
        # escalation weight grows with the index at PO date → later POs carry more price variance
        esc_w = [w * max(0.002, idx(ci, commodity, d) / i_bid - 1) for w, d in zip(weights, dates)]
        esc_ws = sum(esc_w)
        committed_base = base_total * com_f
        for d, w, ew in zip(dates, weights, esc_w):
            po_base = committed_base * w / ws
            po_price = price_v * com_f * ew / esc_ws
            po_logi = logi_v * com_f * w / ws
            tariff = po_price * tariff_share
            esc = po_price - tariff
            committed = po_base + po_price + po_logi
            # invoiced share: older POs fully invoiced; recent POs not yet
            age = (TODAY - d).days
            pid_code = f"PO-{po_n}"
            ratio_idx = idx(ci, commodity, d) / i_bid - 1
            pos.append(dict(po_id=pid_code, project_id=pid, cost_code=code, vendor=vendor, material=material, commodity=commodity, po_date=d,
                            base_amount=round(po_base, 2), price_escalation=round(esc, 2), tariff_surcharge=round(tariff, 2),
                            freight_and_storage=round(po_logi, 2), committed_amount=round(committed, 2),
                            index_change_since_bid_pct=round(100 * ratio_idx, 1),
                            escalation_request_due=d + timedelta(days=10) if (pid == "P-1001" and code == "05-1200") else None,
                            escalation_request_filed_date=None))
            po_n += 1
            pos[-1]["_age"] = age
        # invoices: allocate the invoiced amount (act_f of material EAC) to the oldest POs first
        to_invoice = mat_eac * act_f
        for po in sorted([p for p in pos if p["project_id"] == pid and p["cost_code"] == code], key=lambda x: x["po_date"]):
            if to_invoice <= 1 or po["_age"] < 25:
                po["invoiced_amount"] = 0.0
                continue
            take = min(po["committed_amount"], to_invoice)
            to_invoice -= take
            po["invoiced_amount"] = round(take, 2)
            f = take / po["committed_amount"]
            k = max(1, min(6, po["_age"] // 30))
            for j in range(k):
                inv_d = po["po_date"] + timedelta(days=30 * (j + 1) - rng.randint(0, 6))
                if inv_d > TODAY:
                    inv_d = TODAY - timedelta(days=rng.randint(1, 5))
                part = f / k
                base, esc, tar, lg = (po["base_amount"] * part, po["price_escalation"] * part, po["tariff_surcharge"] * part, po["freight_and_storage"] * part)
                qty = base / UNIT_PRICE[uom]
                storage = lg * 0.35 if code == "26-0500" else 0.0
                inv.append(dict(invoice_id=f"INV-{inv_n}", line_no=1, po_id=po["po_id"], project_id=pid, cost_code=code, vendor=vendor,
                                invoice_date=inv_d, description=material, quantity=round(qty, 1), uom=uom,
                                bid_unit_price=UNIT_PRICE[uom], invoiced_unit_price=round((base + esc + tar) / qty, 2) if qty else None,
                                base_amount=round(base, 2), price_escalation=round(esc, 2), tariff_surcharge=round(tar, 2),
                                freight=round(lg - storage, 2), storage_fee=round(storage, 2), line_total=round(base + esc + tar + lg, 2),
                                source_document=None))
                inv_n += 1
        for po in pos:
            po.setdefault("invoiced_amount", 0.0)

    # Meridian: switchgear delivered 7 weeks early → bonded warehouse storage (weekly invoices) — part of 26-0500 logistics
    sw = MER_SW_ARRIVAL
    pos.append(dict(po_id="PO-MER-STOR", project_id="P-1004", cost_code="26-0500", vendor="Midwest Crating & Storage",
                    material="Bonded warehouse storage - MV switchgear", commodity=None, po_date=sw, base_amount=0.0, price_escalation=0.0,
                    tariff_surcharge=0.0, freight_and_storage=MER_STORAGE_TOTAL, committed_amount=MER_STORAGE_TOTAL, index_change_since_bid_pct=None,
                    escalation_request_due=None, escalation_request_filed_date=None, invoiced_amount=0.0, _age=0))
    for wk in range(MER_STORAGE_WEEKS):
        d = sw + timedelta(days=7 * (wk + 1))
        if d > TODAY:
            break
        amt = MER_STORAGE_WK + (MER_REHANDLE if wk == 0 else 0.0)
        next(p for p in pos if p["po_id"] == "PO-MER-STOR")["invoiced_amount"] += amt
        inv.append(dict(invoice_id=f"INV-{inv_n}", line_no=1, po_id="PO-MER-STOR", project_id="P-1004", cost_code="26-0500",
                        vendor="Midwest Crating & Storage", invoice_date=d, description="Bonded warehouse storage - MV switchgear lineups SG-1..SG-4 (week)" + (" + receiving/rehandling" if wk == 0 else ""),
                        quantity=1.0, uom="WK", bid_unit_price=0.0, invoiced_unit_price=amt, base_amount=0.0, price_escalation=0.0,
                        tariff_surcharge=0.0, freight=0.0, storage_fee=amt, line_total=amt, source_document=None))
        inv_n += 1

    po_df = pl.DataFrame([{k: v for k, v in p.items() if k != "_age"} for p in pos], infer_schema_length=None)
    inv_df = pl.DataFrame(inv, infer_schema_length=None)

    # attach source PDFs to the most telling invoices (written by finance_docs.py)
    # latest invoice of each of the 3 most recently invoiced Atlas steel POs → shows the surcharge rising PO over PO
    a = inv_df.filter((pl.col("project_id") == "P-1001") & (pl.col("cost_code") == "05-1200")).sort("invoice_date")
    atlas_inv = a.group_by("po_id").agg(pl.all().last()).sort("invoice_date").tail(3).select(a.columns)
    mer_inv = inv_df.filter(pl.col("po_id") == "PO-MER-STOR").sort("invoice_date").tail(1)
    pick = {i: f"Invoice_{i}_{v.split()[0]}.pdf" for i, v in zip(pl.concat([atlas_inv, mer_inv])["invoice_id"], pl.concat([atlas_inv, mer_inv])["vendor"])}
    inv_df = inv_df.with_columns(pl.col("invoice_id").replace_strict(pick, default=None).alias("source_document"))

    cc = pl.DataFrame([dict(cost_code=k, description=v[0], csi_division=v[1]) for k, v in COST_CODES.items()])
    for name, df in (("cost_variance_log", cvl_df), ("project_financials", fin_df), ("purchase_orders", po_df),
                     ("vendor_invoice_lines", inv_df), ("commodity_index", ci), ("cost_codes", cc)):
        df.write_parquet(OUT / f"{name}.parquet")
        print(f"{name:22s} {df.height:>7,} rows")
    check(jc, cvl_df, fin_df, co, po_df)


def check(jc, cvl, fin, co, po):
    """Reconciliation + projected margin preview (same formula as scripts/14_finance.sql)."""
    v = jc.with_columns((pl.col("eac") - pl.col("budget")).alias("v")).group_by("project_id", "cost_code", "period").agg(pl.col("v").sum())
    c = cvl.group_by("project_id", "cost_code", "period").agg(pl.col("amount").sum())
    diff = v.join(c, on=["project_id", "cost_code", "period"]).select((pl.col("v") - pl.col("amount")).abs().max())[0, 0]
    print(f"check: cost_variance_log vs job_cost max abs diff = ${diff:.2f}")
    last = jc["period"].max()
    rows = []
    for per in sorted(jc["period"].unique())[-6:]:
        g = jc.filter(pl.col("period") == per).group_by("project_id").agg((pl.col("eac") - pl.col("budget")).sum().alias("g"))
        a = co.filter((pl.col("status") == "Approved") & (pl.col("decision_date") < month_add(per, 1)) & (pl.col("decision_date") <= TODAY)).group_by("project_id").agg(pl.col("amount_approved").sum().alias("a"))
        x = fin.join(g, on="project_id").join(a, on="project_id", how="left").fill_null(0).with_columns(
            fade=pl.max_horizontal(pl.col("g") - pl.col("a") - pl.col("contingency_budget") - pl.col("buyout_savings"), 0),
            rev=pl.col("contract_value") + pl.col("a")).with_columns(pm=100 * (pl.col("bid_gross_profit") - pl.col("fade")) / pl.col("rev"))
        rows.append(x.select("project_id", pl.lit(per).alias("period"), "bid_margin_pct", pl.col("pm").round(2), (pl.col("fade") / 1e6).round(1).alias("fade_m"), "rev", "bid_gross_profit"))
    allm = pl.concat(rows)
    now = allm.filter(pl.col("period") == last)
    pf = 100 * (now["bid_gross_profit"].sum() - now["fade_m"].sum() * 1e6) / now["rev"].sum()
    print(f"portfolio projected margin now = {pf:.2f}%  (bid {100 * now['bid_gross_profit'].sum() / now['rev'].sum():.2f}%)")
    print("breaching threshold:", now.filter(pl.col("bid_margin_pct") - pl.col("pm") > FADE_ALERT_PTS).select("project_id", "bid_margin_pct", "pm", "fade_m").rows())
    print("top fades:", now.with_columns((pl.col("bid_margin_pct") - pl.col("pm")).round(2).alias("pts")).sort("pts", descending=True).head(6).select("project_id", "pts").rows())
    for pid in ("P-1001", "P-1004", "P-1003"):
        print(pid, "trend:", allm.filter(pl.col("project_id") == pid).sort("period").select("period", "pm").rows())
    s = po.filter((pl.col("project_id") == "P-1001") & (pl.col("cost_code") == "05-1200")).sort("po_date")
    print("Atlas steel POs:", s.height, " committed $%.1fM  price+tariff $%.1fM" % (s["committed_amount"].sum() / 1e6, (s["price_escalation"].sum() + s["tariff_surcharge"].sum()) / 1e6))
    print(s.select("po_id", "po_date", "base_amount", "index_change_since_bid_pct", "escalation_request_due", "invoiced_amount").tail(4).rows())


if __name__ == "__main__":
    main()
