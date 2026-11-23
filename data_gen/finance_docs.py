"""Demo 2 evidence PDFs — every figure is read from data_gen/out_finance/*.parquet so documents and tables agree.

Writes data_gen/out_finance/pdf/ (uploaded to volume documents/finance/). Does not touch the Demo 1 PDFs.
Run after finance.py:  .venv/bin/python -I data_gen/finance_docs.py
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).parent))
from documents import Doc  # noqa: E402  (same look as the Demo 1 documents)

OUT = Path(__file__).parent / "out_finance"
PDF = OUT / "pdf"
po = pl.read_parquet(OUT / "purchase_orders.parquet")
inv = pl.read_parquet(OUT / "vendor_invoice_lines.parquet")
ci = pl.read_parquet(OUT / "commodity_index.parquet")
cvl = pl.read_parquet(OUT / "cost_variance_log.parquet")
LAST = cvl["period"].max()
usd = lambda x: f"${x:,.2f}"  # noqa: E731
STEEL = "Structural steel (mill, incl. tariff pass-through)"


def index_at(commodity: str, d: date) -> float:
    return ci.filter((pl.col("commodity") == commodity) & (pl.col("month") == date(d.year, d.month, 1)))["index_value"][0]


def invoice_pdf(row: dict, project: str, extra: list[str]):
    d = Doc(f"{row['vendor']} - Invoice {row['invoice_id']}", f"{row['vendor']}  |  Remit-to on file")
    d.title_block([f"INVOICE {row['invoice_id']}", f"Invoice date: {row['invoice_date']}  |  Customer PO: {row['po_id']}",
                   f"Bill to: General Contractor (GC)  |  Project: {project}", f"Cost code: {row['cost_code']}"])
    d.hd("Line items")
    if row["base_amount"]:
        d.para(f"1. {row['description']} - {row['quantity']:,.1f} {row['uom']} @ bid unit price {usd(row['bid_unit_price'])} = {usd(row['base_amount'])}")
        d.para(f"2. Mill price adjustment (index-based, per supplier price notice) = {usd(row['price_escalation'])}")
        d.para(f"3. Tariff surcharge (Section 232 steel duty pass-through) = {usd(row['tariff_surcharge'])}")
        d.para(f"4. Freight and delivery = {usd(row['freight'])}")
    else:
        d.para(f"1. {row['description']} = {usd(row['storage_fee'])}")
    d.hd(f"Invoice total: {usd(row['line_total'])}")
    for e in extra:
        d.para(e)
    d.para("Payment terms: Net 30. Questions regarding surcharges should reference the supplier price notice on file.")
    return d


def atlas_docs():
    steel = po.filter((pl.col("project_id") == "P-1001") & (pl.col("cost_code") == "05-1200")).sort("po_date")
    out = []
    # supplier escalation notice (2026-09-15) — index values come from commodity_index
    i_aug, i_oct = index_at(STEEL, date(2026, 8, 1)), index_at(STEEL, date(2026, 10, 1))
    d = Doc("Northbridge Steel Supply - Price Notice", "Northbridge Steel Supply  |  Customer notice NSS-2026-09")
    d.title_block(["Customer Price Notice: Structural Steel", "Date: 2026-09-15  |  To: General Contractor (GC) - Purchasing / Project Atlas (P-1001)",
                   "Re: Mill base price increase and tariff surcharge, effective 2026-10-01"])
    d.para(f"Domestic mill base prices for wide-flange sections will increase effective October 1, 2026, and the Section 232 tariff surcharge on imported "
           f"semi-finished steel will be passed through as a separate invoice line. The published structural steel mill price index moved from {i_aug:.1f} "
           f"(August 2026) to an expected {i_oct:.1f} (October 2026).")
    d.para("All purchase orders released on or after October 1, 2026 will be priced at the new mill base plus surcharge. Quotes are valid for 7 calendar days.")
    d.para("Enclosed are mill quotes for your remaining Project Atlas tonnage. Many owner agreements allow price adjustment for steel escalation only "
           "if requested promptly with supporting mill quotes; we recommend you submit these with each release.")
    d.para(f"Open Project Atlas releases on file: {steel.height} purchase orders to date, {usd(steel['committed_amount'].sum())} committed.")
    out.append((d, "Northbridge_Steel_Price_Notice_2026-09-15.pdf"))
    for r in inv.filter(pl.col("source_document").is_not_null() & (pl.col("project_id") == "P-1001")).iter_rows(named=True):
        out.append((invoice_pdf(r, "Project Atlas - Data Center Campus, Bldg 3 (P-1001)", []), r["source_document"]))
    return out


def meridian_docs():
    out = []
    d = Doc("Transmar Freight Forwarding - Arrival Notice", "Transmar Freight Forwarding  |  Shipment TMF-88213")
    d.title_block(["Arrival Notice and Storage Notice", "Date: 2026-07-20  |  To: General Contractor (GC) - Project Meridian (P-1004)",
                   "Shipment: 4 medium-voltage switchgear lineups (SG-1..SG-4), Corvane Electrical Equipment, ocean freight ex-Europe"])
    d.para("The shipment cleared customs and is available for delivery on 2026-07-20. Per the project delivery schedule, the required-on-site date is "
           "2026-09-08 (7 weeks later). The site has advised that the main electrical rooms are not ready to receive equipment.")
    d.para("At the GC's instruction the lineups will be transferred to Midwest Crating & Storage (bonded, climate-controlled) at $8,600 per week, "
           "plus a one-time receiving and rehandling charge of $1,450. Storage continues until the GC releases the equipment for delivery.")
    d.para("Note: import duties on the switchgear were assessed at the increased tariff rate effective 2026-06-01.")
    out.append((d, "Meridian_Switchgear_Arrival_Notice_2026-07-20.pdf"))
    d = Doc("Corvane Electrical Equipment - Tariff Surcharge Notice", "Corvane Electrical Equipment  |  Notice CEE-T-0612")
    d.title_block(["Tariff Surcharge Notice", "Date: 2026-06-12  |  To: General Contractor (GC) - Purchasing", "Re: Imported switchgear and distribution equipment"])
    d.para("Following the tariff increase effective June 1, 2026 on imported electrical equipment, Corvane will apply a tariff surcharge line to all "
           "invoices for equipment shipped after that date, including Project Meridian lineups SG-1..SG-4.")
    out.append((d, "Corvane_Tariff_Surcharge_Notice_2026-06-12.pdf"))
    d = Doc("Prime Contract (excerpt) - Project Meridian Regional Medical Center", "Owner-GC Agreement MR-PC-001 (excerpt)")
    d.title_block(["Agreement Between Owner and Contractor (excerpt)", "Project: Project Meridian - Regional Medical Center (P-1004)", "Contract Sum: $540,000,000"])
    d.hd("Article 8 - Tariffs and Duties")
    d.para("8.1 If a new or increased tariff or duty on materials or equipment incorporated into the Work becomes effective after the bid date, the Contract "
           "Sum shall be adjusted by the documented increase, provided the Contractor gives written notice within 21 days after the Contractor becomes aware "
           "of the increase, with supplier documentation.")
    d.hd("Article 9 - Owner-Directed Delivery and Storage")
    d.para("9.2 Storage of owner-procured or long-lead equipment delivered before the required-on-site date is at the Contractor's cost unless the early "
           "delivery was directed by the Owner in writing.")
    out.append((d, "Meridian_Prime_Contract_Excerpt.pdf"))
    for r in inv.filter(pl.col("source_document").is_not_null() & (pl.col("project_id") == "P-1004")).iter_rows(named=True):
        tot = inv.filter(pl.col("po_id") == "PO-MER-STOR")["line_total"].sum()
        out.append((invoice_pdf(r, "Project Meridian - Regional Medical Center (P-1004)", [f"Storage billed to date (since 2026-07-20): {usd(tot)}."]), r["source_document"]))
    return out


def vega_docs():
    c = cvl.filter((pl.col("project_id") == "P-1003") & (pl.col("period") == LAST))
    conc = c.filter(pl.col("cost_code") == "03-3000")
    q = conc.filter(pl.col("cause").str.starts_with("Quantity"))["amount"].sum()
    pr = conc.filter(pl.col("cause").str.starts_with("Labor"))["amount"].sum()
    total = c["amount"].sum()
    d = Doc("Project Vega - Monthly Cost Report Narrative (October 2026)", "Project Vega - AI Data Hall (P-1003)  |  Project Controls")
    d.title_block(["Monthly Cost Report - Narrative", "Project: Project Vega - AI Data Hall (P-1003)  |  Period: October 2026  |  Issued: 2026-11-02",
                   "Prepared by: Project Controls"])
    d.hd("1. Forecast summary")
    d.para(f"Cost-code forecast growth to date is {usd(total)} over the control budget. Contingency and buyout savings are now fully committed; further "
           "growth flows directly to margin.")
    d.hd("2. Concrete (03-3000)")
    d.para(f"Installed concrete quantities are running about 6% above the estimate takeoff (slab thickening at data hall equipment pads, over-pour at "
           f"pile caps). Quantity growth on 03-3000: {usd(q)}. Crew productivity on elevated decks is running at a productivity factor of 1.18 "
           f"(18% more crew hours per cubic yard than estimated). Productivity growth on 03-3000: {usd(pr)}.")
    d.hd("3. Actions under consideration")
    d.para("Re-sequence deck pours to reduce re-mobilization; verify pad thickening against IFC drawings to determine if an owner change applies; "
           "update the remaining-quantity forecast with the concrete subcontractor.")
    return [(d, "Vega_Monthly_Cost_Report_2026-10.pdf")]


def main():
    PDF.mkdir(parents=True, exist_ok=True)
    for d, name in atlas_docs() + meridian_docs() + vega_docs():
        d.output(str(PDF / name))
        print("pdf ", name)


if __name__ == "__main__":
    main()
