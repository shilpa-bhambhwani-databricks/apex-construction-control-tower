"""Stage 2 (Resolve) synthetic content — SHARED, brand-neutral.

Outputs (data_gen/out_docs/):
  pdf/*.pdf                      contracts, subcontracts, spec sections, daily log, notice letter, geotech memo (Project Atlas)
  change_order_lines.parquet     line items for Atlas pending COs (CO-0142, CO-0139 …)
  historical_unit_costs.parquet  24 months of awarded unit rates by cost code / region (~5K rows)
  historical_rfis.parquet        ~300 closed RFIs with resolutions across projects (incl. 3 planted precedents for RFI-0387)

Planted storyline (Resolve demo, CO-0142):
  * Prime §4.3 Differing Site Conditions covers concealed subsurface rock.
  * Keystone subcontract §11.2: written notice within 7 calendar days of discovery.
  * Daily log 2026-10-11 first records rock at PC-14..22; Keystone's first written notice is dated 2026-10-23 (12 days).
  * CO-0142 rock-removal unit rate $142/CY vs. Northeast 24-month median ~$120/CY (n = 37) → ~18% above.
Run: .venv/bin/python -I data_gen/documents.py
"""
from __future__ import annotations

import random
import statistics
from datetime import date, timedelta
from pathlib import Path

import polars as pl
from fpdf import FPDF

rng = random.Random(1118)
OUT = Path(__file__).parent / "out_docs"
PDF = OUT / "pdf"
TODAY = date(2026, 11, 9)
REGIONS = ["Northeast", "Midwest", "Southeast", "West", "Southwest"]

# --------------------------------------------------------------------------- PDFs


class Doc(FPDF):
    def __init__(self, title: str, subtitle: str):
        super().__init__(format="Letter")
        self.t, self.s = title, subtitle
        self.set_auto_page_break(True, margin=18)
        self.set_margins(20, 18, 20)
        self.add_page()

    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.cell(0, 5, self.t, align="L")
        self.set_font("Helvetica", "", 8)
        self.cell(0, 5, "SYNTHETIC DEMO DOCUMENT", align="R", new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "", 8)
        self.cell(0, 8, f"{self.s}  |  Page {self.page_no()}", align="C")

    def hd(self, text: str):
        self.ln(2)
        self.set_font("Helvetica", "B", 11)
        self.multi_cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")

    def para(self, text: str):
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 5.2, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(1.5)

    def title_block(self, lines: list[str]):
        self.set_font("Helvetica", "B", 15)
        self.multi_cell(0, 8, lines[0], new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 10)
        for ln in lines[1:]:
            self.multi_cell(0, 5.2, ln, new_x="LMARGIN", new_y="NEXT")
        self.ln(3)


FILLER = ("The parties shall cooperate in good faith to coordinate the Work with other trades and with the Owner's operations. "
          "Submittals shall be provided in accordance with the Contract Documents and the approved submittal schedule. ")


def prime_contract():
    d = Doc("Prime Contract - Project Atlas, Data Center Campus Bldg 3", "Owner-GC Agreement AT-PC-001")
    d.title_block(["Agreement Between Owner and Contractor", "Project: Project Atlas - Data Center Campus, Building 3 (P-1001)",
                   "Owner: Atlas Digital Infrastructure LLC  |  Contractor: General Contractor (GC)", "Contract Sum: $1,240,000,000  |  Date: 2025-04-02"])
    d.hd("Article 1 - Definitions"); d.para("1.1 Contract Documents include this Agreement, the General Conditions, Drawings, Specifications, and Addenda. " + FILLER * 2)
    d.hd("Article 3 - Contract Time"); d.para("3.1 Substantial Completion of Building 3 shall be achieved by 2027-09-30, subject to adjustments under Article 4. " + FILLER * 2)
    d.hd("Article 4 - Changes in the Work and Site Conditions")
    d.para("4.1 The Owner may order changes in the Work by Change Order or Construction Change Directive. Pricing of changes shall follow Section 4.5.")
    d.para("4.3 Differing Site Conditions. If the Contractor encounters (a) subsurface or otherwise concealed physical conditions at the site that differ "
        "materially from those indicated in the Contract Documents, including the geotechnical report, or (b) unknown physical conditions of an unusual nature, "
        "the Contractor shall be entitled to an equitable adjustment in the Contract Sum and Contract Time. Unforeseen rock within the limits of excavation "
        "shown on the Drawings is a concealed subsurface condition under this Section 4.3. The Contractor shall give the Owner written notice promptly and "
        "in no event later than 14 calendar days after first observance of the condition, and before the condition is disturbed.")
    d.para("4.4 Concealed conditions identified by subcontractors shall be reported to the Contractor in accordance with the applicable subcontract so that the "
        "Contractor can meet the notice requirements of Section 4.3.")
    d.para("4.5 Pricing of Changes. Changes shall be priced at the reasonable cost of labor, materials, and equipment, plus 10% overhead and 5% profit. "
        "Unit rates shall be consistent with prevailing rates for comparable work in the project region.")
    d.add_page()
    d.hd("Article 7 - Material Price Escalation")
    d.para("7.1 If the published mill price index for structural steel increases by more than 5% between the bid date and the date of purchase order, the Contract Sum "
        "shall be adjusted for the increase above 5% for steel not yet purchased, upon written request within 10 days of the purchase order.")
    d.hd("Article 9 - Claims"); d.para("9.1 Claims must be initiated by written notice within 21 days after the event giving rise to the Claim. " + FILLER * 3)
    return d, "Prime_Contract_Atlas_Bldg3.pdf"


def sub_concrete():
    d = Doc("Subcontract - Keystone Concrete LLC (Concrete & Foundations)", "Subcontract AT-SC-0330")
    d.title_block(["Subcontract Agreement", "Project: Project Atlas - Building 3 (P-1001)", "Subcontractor: Keystone Concrete LLC  |  Scope: cost codes 03-3000, 31-2316",
                   "Subcontract Sum: $48,600,000  |  Date: 2025-06-10"])
    d.hd("Section 2 - Scope"); d.para("2.1 Cast-in-place concrete, pile caps PC-1 through PC-60, grade beams, and associated excavation and backfill per Exhibit A. " + FILLER)
    d.hd("Section 11 - Changes and Concealed Conditions")
    d.para("11.1 Changes shall be priced per Exhibit B unit rates where applicable, otherwise per Section 11.4.")
    d.para("11.2 Notice of Concealed or Differing Conditions. The Subcontractor shall give the Contractor WRITTEN NOTICE within 7 calendar days after first "
        "discovery of any concealed or differing site condition, including rock, and before disturbing the condition. Failure to provide timely written notice "
        "may result in waiver of the Subcontractor's right to an adjustment for costs incurred before notice was given.")
    d.para("11.3 Daily logs and photographs documenting the condition shall accompany the notice.")
    d.para("11.4 Pricing. Adjustments not covered by Exhibit B shall be priced at reasonable cost consistent with prevailing regional unit rates for comparable work, "
        "with 10% overhead and 5% profit, and shall be supported by backup documentation.")
    d.add_page()
    d.hd("Exhibit B - Unit Rates (excerpt)")
    d.para("Rock removal and over-excavation at pile caps (03-3000): $118.00 per cubic yard.\nLean concrete backfill (03-3000): $172.00 per cubic yard.\n"
        "Dewatering: time and materials, not to exceed $30,000 per occurrence.")
    return d, "Subcontract_Keystone_Concrete.pdf"


def sub_steel():
    d = Doc("Subcontract - Ironline Steel Erectors (Structural Steel)", "Subcontract AT-SC-0512")
    d.title_block(["Subcontract Agreement", "Project: Project Atlas - Building 3 (P-1001)", "Subcontractor: Ironline Steel Erectors  |  Scope: cost code 05-1200",
                   "Subcontract Sum: $96,400,000  |  Date: 2025-07-01"])
    d.hd("Section 12 - Material Escalation")
    d.para("12.1 Steel price adjustments apply only per Prime Contract Article 7 and require written request with mill quotes within 10 days of the purchase order.")
    d.hd("Section 14 - Design Changes")
    d.para("14.1 Revisions issued by ASI shall be priced per Section 14.2. Embed plates furnished under this subcontract include plates shown on S-201; "
        "revised plates issued after award are a change to the Work.")
    return d, "Subcontract_Ironline_Steel.pdf"


def spec_excavation():
    d = Doc("Specification 31 23 16 - Excavation", "Project Atlas Specifications - Division 31")
    d.title_block(["Section 31 23 16 - Excavation", "Project Atlas - Building 3"])
    d.hd("1.4 Definitions")
    d.para("Rock: material that cannot be removed with a 1.5 cubic-yard hydraulic excavator bucket without drilling, blasting, or ripping, and boulders exceeding "
        "1 cubic yard. Rock excavation is unclassified only where so indicated; otherwise rock is a differing condition under the Contract.")
    d.hd("3.2 Rock Removal"); d.para("Notify the Contractor immediately upon encountering rock. Do not proceed with rock removal until quantities are measured and documented jointly.")
    return d, "Spec_31_23_16_Excavation.pdf"


def spec_concrete():
    d = Doc("Specification 03 30 00 - Cast-in-Place Concrete", "Project Atlas Specifications - Division 03")
    d.title_block(["Section 03 30 00 - Cast-in-Place Concrete", "Project Atlas - Building 3"])
    d.hd("3.6 Lean Concrete Backfill"); d.para("Where over-excavation is required, backfill to bearing elevation with lean concrete, 1,500 psi minimum. " + FILLER)
    return d, "Spec_03_30_00_Concrete.pdf"


def spec_steel():
    d = Doc("Specification 05 12 00 - Structural Steel Framing", "Project Atlas Specifications - Division 05")
    d.title_block(["Section 05 12 00 - Structural Steel Framing", "Project Atlas - Building 3"])
    d.hd("2.4 Embedded Items"); d.para("Embed plates shall be sized and located per S-201. Coordinate beam pocket locations shown on S-305 prior to fabrication. " + FILLER)
    return d, "Spec_05_12_00_Structural_Steel.pdf"


def daily_log():
    d = Doc("Daily Log - 2026-10-11", "Project Atlas Daily Log (Procore export)")
    d.title_block(["Daily Log - Saturday 2026-10-11", "Project Atlas - Building 3 | Superintendent: Dana Morales | Weather: 58F, clear"])
    d.hd("Work Performed"); d.para("Keystone Concrete excavating pile caps PC-14 through PC-22 at grid lines C-F.")
    d.hd("Issues / Observations")
    d.para("Keystone foreman reports ROCK encountered at PC-14 and PC-16 at approx. elevation -6 ft, excavator refusal. Photos taken. Work continuing at PC-18 to PC-22. "
        "Superintendent requested Keystone to document quantities.")
    d.hd("Manpower"); d.para("Keystone Concrete 18 | Ironline Steel 8 | Brightway Electric 13 | Northgate Mechanical 9")
    return d, "Daily_Log_2026-10-11.pdf"


def notice_letter():
    d = Doc("Keystone Concrete - Notice of Differing Site Condition", "Keystone Concrete letter KC-AT-0147")
    d.title_block(["Notice of Differing Site Condition", "Date: 2026-10-23", "To: General Contractor, Project Atlas  |  From: Keystone Concrete LLC"])
    d.para("This letter serves as written notice under Subcontract Section 11.2 of a differing subsurface condition: rock encountered at pile caps PC-14 through PC-22, "
        "grid lines C-F. Keystone will submit a change order request for rock removal, over-excavation, lean concrete backfill, and dewatering.")
    return d, "Notice_Letter_Keystone_2026-10-23.pdf"


def geotech():
    d = Doc("Geotechnical Memo GM-07", "Project Atlas Geotechnical Engineer of Record")
    d.title_block(["Geotechnical Memorandum GM-07", "Date: 2026-10-15", "Subject: Rock at pile caps PC-14 to PC-22"])
    d.para("Borings B-6 and B-7 in the original report (2025-02) indicated weathered shale below elevation -12 ft. Competent rock was encountered at approx. -6 ft at grid "
        "lines C-F, which differs materially from the report. Recommend over-excavation to sound rock and lean concrete backfill to bearing elevation.")
    return d, "Geotech_Memo_GM-07.pdf"


# --------------------------------------------------------------------------- tables


def unit_costs() -> list[dict]:
    """Awarded unit rates, 24 months. Planted: 03-3000 'Rock removal' Northeast — exactly 37 rows, median ~120."""
    rows, n = [], 0
    items = [("03-3000", "Rock removal and over-excavation", "CY", 120), ("03-3000", "Lean concrete backfill", "CY", 165), ("03-3000", "Pile cap concrete", "CY", 310),
             ("05-1200", "Structural steel erected", "TON", 4200), ("05-1200", "Embed plates furnished and installed", "EA", 420),
             ("26-0500", "Duct bank", "LF", 285), ("23-0500", "Ductwork installed", "LB", 14), ("31-2000", "Mass excavation", "CY", 18)]
    region_factor = {"Northeast": 1.0, "Midwest": 0.88, "Southeast": 0.84, "West": 1.08, "Southwest": 0.9}
    for code, desc, unit, base in items:
        for region in REGIONS:
            k = 37 if (desc.startswith("Rock removal") and region == "Northeast") else rng.randint(60, 160)
            vals = []
            for _ in range(k):
                v = base * region_factor[region] * rng.lognormvariate(0, 0.11)
                vals.append(v)
            if desc.startswith("Rock removal") and region == "Northeast":  # pin median to ~120
                shift = 120 - statistics.median(vals); vals = [v + shift for v in vals]
            for v in vals:
                n += 1
                rows.append(dict(line_id=f"UC-{n:05d}", project_id=f"P-{rng.randint(1001, 1040)}", cost_code=code, item_desc=desc, region=region, unit=unit,
                                 unit_rate=round(v, 2), quantity=round(rng.uniform(50, 3000), 0), award_date=TODAY - timedelta(days=rng.randint(5, 720))))
    return rows


def co_lines() -> list[dict]:
    return [
        dict(project_id="P-1001", co_id="CO-0142", line=1, cost_code="03-3000", item_desc="Rock removal and over-excavation", unit="CY", quantity=2400, unit_rate=142.00, amount=340800.00),
        dict(project_id="P-1001", co_id="CO-0142", line=2, cost_code="03-3000", item_desc="Lean concrete backfill", unit="CY", quantity=650, unit_rate=185.00, amount=120250.00),
        dict(project_id="P-1001", co_id="CO-0142", line=3, cost_code="03-3000", item_desc="Dewatering (T&M)", unit="LS", quantity=1, unit_rate=24950.00, amount=24950.00),
        dict(project_id="P-1001", co_id="CO-0139", line=1, cost_code="05-1200", item_desc="Embed plates furnished and installed", unit="EA", quantity=240, unit_rate=455.00, amount=109200.00),
        dict(project_id="P-1001", co_id="CO-0139", line=2, cost_code="05-1200", item_desc="Field welding and touch-up", unit="LS", quantity=1, unit_rate=13200.00, amount=13200.00),
    ]


def historical_rfis() -> list[dict]:
    planted = [
        dict(rfi_id="RFI-0212", project_id="P-1006", project_name="Project Orion", discipline="Structural", subject="Embed plate conflict with beam pocket at L2",
             question="Embed plates on S-201 conflict with beam pockets on S-305 at level 2, grid B. Confirm plate size and location.",
             resolution="Resolved by ASI-019 in 6 days: plates shifted 4 in. east and upsized to 3/4 in. Steel sub priced as CO ($38K).", cost_impact_usd=38000, schedule_impact_days=0, turnaround_days=6),
        dict(rfi_id="RFI-0098", project_id="P-1009", project_name="Project Nova", discipline="Structural", subject="Embed plate size mismatch at beam seat",
             question="Embed plate size on S-201 does not match beam seat connection detail 7/S-501.", resolution="Field fix approved by EOR (added shim plate); no cost.",
             cost_impact_usd=0, schedule_impact_days=0, turnaround_days=4),
        dict(rfi_id="PL-4471", project_id="LEGACY-DC17", project_name="Legacy DC-17 (Prolog)", discipline="Structural", subject="Embed plate / beam pocket conflict, level 2",
             question="Embed plate locations conflict with beam pockets at level 2. Request revised embed layout.",
             resolution="Open 19 days awaiting EOR; caused a 5-day steel erection delay. Resolved by revised S-201 with relocated plates.", cost_impact_usd=52000, schedule_impact_days=5, turnaround_days=19),
    ]
    topics = [("Mechanical", "Duct routing vs. structure", "Duct conflicts with beam at grid {g}.", "Duct rerouted below beam; no cost."),
              ("Electrical", "Duct bank routing vs. footing", "Duct bank conflicts with footing F-{n}.", "Duct bank lowered 18 in.; minor cost."),
              ("Architectural", "Door hardware schedule conflict", "Hardware set {n} conflicts with frame type.", "Revised hardware set issued."),
              ("Civil", "Utility crossing depth", "Storm line crossing conflicts with water main.", "Storm line lowered per C-{n}."),
              ("Plumbing", "Floor drain location", "Floor drain conflicts with slab joint.", "Drain shifted 12 in."),
              ("Structural", "Slab edge dimension mismatch", "Slab edge on S-1{n} differs from A-2{n}.", "Architectural governs; S-sheet revised."),
              ("Fire Protection", "Sprinkler head layout vs. ceiling", "Heads conflict with light fixtures.", "Heads relocated per RCP.")]
    rows = list(planted)
    for i in range(297):
        disc, subj, q, res = rng.choice(topics)
        rows.append(dict(rfi_id=f"HR-{i + 1:04d}", project_id=f"P-{rng.randint(1001, 1040)}", project_name=None, discipline=disc, subject=subj,
                         question=q.format(g=rng.choice("ABCDEFG"), n=rng.randint(1, 40)), resolution=res,
                         cost_impact_usd=rng.choice([0, 0, 0, 5000, 12000, 25000]), schedule_impact_days=rng.choice([0, 0, 1, 2]), turnaround_days=rng.randint(3, 21)))
    return rows


def main():
    PDF.mkdir(parents=True, exist_ok=True)
    for make in (prime_contract, sub_concrete, sub_steel, spec_excavation, spec_concrete, spec_steel, daily_log, notice_letter, geotech):
        d, name = make()
        d.output(str(PDF / name)); print("pdf ", name)
    for name, rows in (("historical_unit_costs", unit_costs()), ("change_order_lines", co_lines()), ("historical_rfis", historical_rfis())):
        pl.DataFrame(rows, infer_schema_length=None).write_parquet(OUT / f"{name}.parquet"); print(f"{name:24s} {len(rows):>6,} rows")
    uc = pl.read_parquet(OUT / "historical_unit_costs.parquet").filter((pl.col("item_desc").str.starts_with("Rock removal")) & (pl.col("region") == "Northeast"))
    med = uc["unit_rate"].median()
    print(f"check: NE rock removal n={uc.height} median=${med:.2f} → CO-0142 $142 is {142 / med - 1:+.0%}")


if __name__ == "__main__":
    main()
