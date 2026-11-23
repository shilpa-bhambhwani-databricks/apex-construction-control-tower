-- Demo 2 (Office of the CFO — margin fade) finance layer. ADDITIVE ONLY: creates new objects, never alters Demo 1 tables.
-- Source: data_gen/finance.py → /Volumes/bhambs/construction_control_tower/raw/v3/ ; PDFs → volume finance_documents.
CREATE OR REPLACE TABLE cost_codes COMMENT 'CSI-style cost code names for job_cost / cost_variance_log.' AS SELECT * FROM read_files('/Volumes/bhambs/construction_control_tower/raw/v3/cost_codes.parquet')
;;
CREATE OR REPLACE TABLE commodity_index COMMENT 'Monthly commodity price indices (Jan 2024 = 100): structural steel incl. tariff pass-through, rebar, ready-mix, copper, switchgear PPI, aluminum.' AS SELECT * FROM read_files('/Volumes/bhambs/construction_control_tower/raw/v3/commodity_index.parquet')
;;
CREATE OR REPLACE TABLE project_financials COMMENT 'Per-project WIP inputs (SAP / estimating): bid gross profit, contingency budget, buyout savings, margin-fade alert threshold (points below bid).' AS SELECT * FROM read_files('/Volumes/bhambs/construction_control_tower/raw/v3/project_financials.parquet')
;;
CREATE OR REPLACE TABLE cost_variance_log COMMENT 'Project controls variance log: why each cost code is over budget, by cause and month. SUM(amount) per project/cost_code/period equals job_cost eac - budget.' AS SELECT * FROM read_files('/Volumes/bhambs/construction_control_tower/raw/v3/cost_variance_log.parquet')
;;
CREATE OR REPLACE TABLE purchase_orders COMMENT 'Material purchase orders (SAP MM): bid-price basis, price escalation, tariff surcharge, freight/storage, committed and invoiced. escalation_request_due = PO date + 10 days (Atlas prime contract Art. 7 steel escalation).' AS SELECT * FROM read_files('/Volumes/bhambs/construction_control_tower/raw/v3/purchase_orders.parquet')
;;
CREATE OR REPLACE TABLE vendor_invoice_lines COMMENT 'Vendor invoice lines (AP): base amount at bid unit price, price escalation, tariff surcharge, freight, storage fee. source_document = invoice PDF in volume finance_documents.' AS SELECT * FROM read_files('/Volumes/bhambs/construction_control_tower/raw/v3/vendor_invoice_lines.parquet')
;;
ALTER TABLE project_financials SET ROW FILTER ct_row_scope ON (project_id)
;;
ALTER TABLE cost_variance_log SET ROW FILTER ct_row_scope ON (project_id)
;;
ALTER TABLE purchase_orders SET ROW FILTER ct_row_scope ON (project_id)
;;
ALTER TABLE vendor_invoice_lines SET ROW FILTER ct_row_scope ON (project_id)
;;
CREATE OR REPLACE TABLE finance_parsed_documents COMMENT 'ai_parse_document output for the Demo 2 evidence PDFs (volume finance_documents).' AS
SELECT path, regexp_extract(path, '([^/]+)$', 1) AS doc_name, ai_parse_document(content) AS parsed
FROM read_files('/Volumes/bhambs/construction_control_tower/finance_documents/', format => 'binaryFile')
;;
CREATE OR REPLACE TABLE finance_doc_chunks COMMENT 'Searchable paragraphs of the Demo 2 evidence PDFs with page + section for citations. Kept separate from doc_chunks (Resolve/Jobsite AI Search index).' AS
WITH el AS (
  SELECT doc_name, pos, e:type::string AS type, e:content::string AS content, e:bbox[0].page_id::int + 1 AS page
  FROM finance_parsed_documents LATERAL VIEW posexplode(variant_get(parsed, '$.document.elements', 'ARRAY<VARIANT>')) t AS pos, e
), labeled AS (
  SELECT *, last_value(CASE WHEN type IN ('section_header', 'title') THEN content END, true) OVER (PARTITION BY doc_name ORDER BY pos) AS section
  FROM el WHERE type IN ('text', 'section_header', 'title')
)
SELECT concat(doc_name, '#', pos) AS chunk_id, doc_name,
  CASE WHEN doc_name LIKE 'Invoice%' THEN 'invoice' WHEN doc_name LIKE '%Notice%' THEN 'supplier_notice' WHEN doc_name LIKE '%Contract%' THEN 'prime_contract'
       ELSE 'cost_report' END AS doc_type,
  CASE WHEN doc_name RLIKE 'Northbridge' THEN 'P-1001' WHEN doc_name RLIKE 'Meridian|Corvane|Midwest' THEN 'P-1004' WHEN doc_name RLIKE 'Vega' THEN 'P-1003' END AS project_id,
  page, section, concat_ws('\n', section, content) AS text
FROM labeled WHERE type IN ('text', 'title')
;;
ALTER TABLE finance_doc_chunks SET ROW FILTER ct_row_scope ON (project_id)
;;
CREATE OR REPLACE VIEW project_margin_monthly
COMMENT 'WIP projected margin by project and month. Cost growth (job_cost EAC - budget) net of approved change-order revenue is absorbed by contingency + buyout savings first; only the remainder fades margin.'
AS
WITH g AS (
  SELECT project_id, period, SUM(eac - budget) AS cost_growth FROM bhambs.construction_control_tower.job_cost GROUP BY ALL
), a AS (
  SELECT g.project_id, g.period, COALESCE(SUM(c.amount_approved), 0) AS approved_co_revenue
  FROM g LEFT JOIN bhambs.construction_control_tower.change_orders c
    ON c.project_id = g.project_id AND c.status = 'Approved' AND c.decision_date < add_months(g.period, 1) AND c.decision_date <= DATE'2026-11-09'
  GROUP BY ALL
), x AS (
  SELECT f.project_id, g.period, f.contract_value, f.bid_margin_pct, f.bid_gross_profit, f.contingency_budget, f.buyout_savings,
         f.contingency_budget + f.buyout_savings AS cushion, f.fade_alert_threshold_pts, f.project_controls_manager,
         a.approved_co_revenue, g.cost_growth, GREATEST(g.cost_growth - a.approved_co_revenue, 0) AS net_cost_growth
  FROM bhambs.construction_control_tower.project_financials f
  JOIN g ON g.project_id = f.project_id JOIN a ON a.project_id = g.project_id AND a.period = g.period
)
SELECT *, LEAST(net_cost_growth, cushion) AS cushion_used, GREATEST(net_cost_growth - cushion, 0) AS margin_fade,
       contract_value + approved_co_revenue AS contract_revenue,
       bid_gross_profit - GREATEST(net_cost_growth - cushion, 0) AS projected_gross_profit,
       ROUND(100 * (bid_gross_profit - GREATEST(net_cost_growth - cushion, 0)) / (contract_value + approved_co_revenue), 2) AS projected_margin_pct,
       ROUND(bid_margin_pct - 100 * (bid_gross_profit - GREATEST(net_cost_growth - cushion, 0)) / (contract_value + approved_co_revenue), 2) AS fade_pts
FROM x
;;
CREATE OR REPLACE VIEW project_margin_mv
WITH METRICS
LANGUAGE YAML
COMMENT 'Single definition of projected margin (WIP) and margin fade for the Office of the CFO. Used by SQL alerts, Genie, and dashboards. Synthetic data as of 2026-11-09; latest period = 2026-11-01.'
AS $$
version: 1.1
source: bhambs.construction_control_tower.project_margin_monthly
joins:
  - name: p
    source: bhambs.construction_control_tower.projects
    on: source.project_id = p.project_id
dimensions:
  - name: project_id
    expr: source.project_id
  - name: project_name
    expr: p.name
    comment: "e.g. Project Atlas — Data Center Campus, Bldg 3"
  - name: market_sector
    expr: p.market_sector
  - name: region
    expr: p.region
  - name: business_unit
    expr: p.business_unit
  - name: project_executive
    expr: p.project_executive
  - name: project_controls_manager
    expr: source.project_controls_manager
  - name: pct_complete
    expr: p.pct_complete
  - name: period
    expr: source.period
    comment: "Monthly WIP period (first of month). Latest = 2026-11-01."
  - name: months_ago
    expr: CAST(months_between(DATE'2026-11-01', source.period) AS INT)
    comment: "0 = current WIP period (Nov 2026), 3 = August 2026. ALWAYS filter to one period, e.g. months_ago = 0."
  - name: breaching_threshold
    expr: source.fade_pts > source.fade_alert_threshold_pts
    comment: "TRUE when projected margin is more than the alert threshold (1.5 pts) below bid margin."
measures:
  - name: contract_revenue
    expr: SUM(source.contract_revenue)
    comment: "Contract value + approved change-order revenue (USD)."
  - name: bid_margin_pct
    expr: ROUND(100 * SUM(source.bid_gross_profit) / SUM(source.contract_value), 2)
    comment: "Margin at bid (%)."
  - name: projected_margin_pct
    expr: ROUND(100 * SUM(source.projected_gross_profit) / SUM(source.contract_revenue), 2)
    comment: "Projected (WIP) margin at completion (%), revenue-weighted when grouped."
  - name: margin_fade_pts
    expr: ROUND(100 * SUM(source.bid_gross_profit) / SUM(source.contract_value) - 100 * SUM(source.projected_gross_profit) / SUM(source.contract_revenue), 2)
    comment: "Bid margin minus projected margin, in percentage points. Positive = fade."
  - name: margin_fade_usd
    expr: SUM(source.margin_fade)
    comment: "Gross profit lost vs. bid (USD) = cost growth not covered by contingency + buyout savings."
  - name: bid_gross_profit
    expr: SUM(source.bid_gross_profit)
  - name: projected_gross_profit
    expr: SUM(source.projected_gross_profit)
  - name: cost_growth_usd
    expr: SUM(source.cost_growth)
    comment: "Cost-code forecast growth: SUM(EAC - budget) from SAP job cost."
  - name: approved_co_revenue
    expr: SUM(source.approved_co_revenue)
  - name: cushion_usd
    expr: SUM(source.cushion)
    comment: "Contingency + buyout savings available to absorb cost growth."
  - name: cushion_remaining_usd
    expr: SUM(source.cushion - source.cushion_used)
  - name: cushion_used_pct
    expr: ROUND(100 * SUM(source.cushion_used) / SUM(source.cushion), 1)
    comment: "Share of contingency + buyout savings already consumed (%). Early-warning signal: > 90% means the next overrun hits margin."
  - name: projects_breaching
    expr: COUNT(DISTINCT CASE WHEN source.fade_pts > source.fade_alert_threshold_pts THEN source.project_id END)
  - name: project_count
    expr: COUNT(DISTINCT source.project_id)
$$
;;
SELECT table_name FROM information_schema.tables WHERE table_schema = 'construction_control_tower'
  AND table_name IN ('cost_codes','commodity_index','project_financials','cost_variance_log','purchase_orders','vendor_invoice_lines','finance_parsed_documents','finance_doc_chunks','project_margin_monthly','project_margin_mv') ORDER BY 1
