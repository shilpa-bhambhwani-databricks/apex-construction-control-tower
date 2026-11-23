-- Step 1 (alert): which jobs breach the margin-fade threshold, vs. the portfolio
SELECT project_name, region, bid_margin_pct, projected_margin_pct, margin_fade_pts, ROUND(margin_fade_usd/1e6, 1) AS fade_usd_m, cushion_used_pct
FROM (SELECT project_name, region, MEASURE(bid_margin_pct) bid_margin_pct, MEASURE(projected_margin_pct) projected_margin_pct, MEASURE(margin_fade_pts) margin_fade_pts,
             MEASURE(margin_fade_usd) margin_fade_usd, MEASURE(cushion_used_pct) cushion_used_pct
      FROM project_margin_mv WHERE months_ago = 0 GROUP BY ALL) ORDER BY margin_fade_pts DESC LIMIT 6
;;
SELECT MEASURE(bid_margin_pct) AS portfolio_bid, MEASURE(projected_margin_pct) AS portfolio_projected, MEASURE(projects_breaching) AS breaching, MEASURE(project_count) AS projects
FROM project_margin_mv WHERE months_ago = 0
;;
-- Atlas trend (when did it start to fade?)
SELECT period, MEASURE(projected_margin_pct) AS projected, MEASURE(cushion_used_pct) AS cushion_used, ROUND(MEASURE(cost_growth_usd)/1e6,1) AS growth_m
FROM project_margin_mv WHERE project_name ILIKE '%Atlas%' AND months_ago <= 5 GROUP BY ALL ORDER BY period
;;
-- Step 2 (why): Atlas cost growth by cause, now vs. August
SELECT cause, ROUND(SUM(amount) FILTER (WHERE period = DATE'2026-11-01')/1e6, 1) AS now_m, ROUND(SUM(amount) FILTER (WHERE period = DATE'2026-08-01')/1e6, 1) AS aug_m
FROM cost_variance_log WHERE project_id = 'P-1001' AND period IN (DATE'2026-11-01', DATE'2026-08-01') GROUP BY cause ORDER BY now_m DESC
;;
SELECT v.cost_code, c.description, v.cause, ROUND(SUM(v.amount)/1e6, 1) AS usd_m
FROM cost_variance_log v JOIN cost_codes c USING (cost_code) WHERE v.project_id = 'P-1001' AND v.period = DATE'2026-11-01' GROUP BY ALL ORDER BY usd_m DESC LIMIT 5
;;
-- Step 3 (evidence): steel POs vs Art. 7 window
SELECT po_id, po_date, ROUND(base_amount/1e6, 2) AS base_m, index_change_since_bid_pct AS idx_chg, escalation_request_due AS due, escalation_request_filed_date AS filed,
       ROUND(GREATEST(index_change_since_bid_pct - 5, 0)/100 * base_amount/1e6, 2) AS recoverable_m,
       CASE WHEN escalation_request_due >= DATE'2026-11-09' THEN 'OPEN — file now' ELSE 'window missed' END AS status
FROM purchase_orders WHERE project_id = 'P-1001' AND cost_code = '05-1200' AND index_change_since_bid_pct > 5 ORDER BY po_date DESC
;;
SELECT invoice_id, invoice_date, ROUND(base_amount) base, ROUND(price_escalation) esc, ROUND(tariff_surcharge) tariff, ROUND(freight) freight, source_document
FROM vendor_invoice_lines WHERE source_document IS NOT NULL ORDER BY project_id, invoice_id
;;
SELECT doc_name, doc_type, project_id, page, left(text, 80) AS excerpt FROM finance_doc_chunks ORDER BY doc_name LIMIT 12
;;
-- Step 5 (scale): +15% steel on open (uncommitted + committed-not-invoiced) steel across all active jobs
SELECT p.name, ROUND(SUM(po.committed_amount - po.invoiced_amount)/1e6, 1) AS open_steel_m, ROUND(0.15 * SUM(po.base_amount * (1 - po.invoiced_amount / po.committed_amount))/1e6, 2) AS exposure_15pct_m
FROM purchase_orders po JOIN projects p USING (project_id) WHERE po.cost_code = '05-1200' GROUP BY ALL HAVING open_steel_m > 0 ORDER BY exposure_15pct_m DESC LIMIT 8
