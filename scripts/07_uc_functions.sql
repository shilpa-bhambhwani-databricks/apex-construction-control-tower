CREATE OR REPLACE FUNCTION get_unit_cost_baseline(cost_code STRING, region STRING, item_keyword STRING)
RETURNS TABLE (item_desc STRING, unit STRING, n BIGINT, p25 DOUBLE, median DOUBLE, p75 DOUBLE, window_start DATE, window_end DATE)
COMMENT 'Resolve tool: trailing-24-month awarded unit-rate benchmark for a cost code + region + item keyword (P25 / median / P75 and sample size).'
RETURN
  SELECT item_desc, first(unit), COUNT(*), ROUND(percentile(unit_rate, 0.25), 2), ROUND(percentile(unit_rate, 0.5), 2), ROUND(percentile(unit_rate, 0.75), 2),
         MIN(award_date), MAX(award_date)
  FROM bhambs.construction_control_tower.historical_unit_costs h
  WHERE h.cost_code = get_unit_cost_baseline.cost_code AND h.region = get_unit_cost_baseline.region
    AND h.item_desc ILIKE concat('%', get_unit_cost_baseline.item_keyword, '%')
    AND h.award_date >= DATE'2026-11-09' - INTERVAL 24 MONTHS
  GROUP BY item_desc
;;
CREATE OR REPLACE FUNCTION get_change_order(co_id STRING)
RETURNS TABLE (co_id STRING, project_id STRING, project_name STRING, region STRING, subcontractor STRING, cost_code STRING, description STRING, status STRING,
               amount_requested DOUBLE, submitted_date DATE, line INT, item_desc STRING, unit STRING, quantity DOUBLE, unit_rate DOUBLE, line_amount DOUBLE)
COMMENT 'Resolve tool: change order header + line items (Clearstory). Row-filtered: only COs on projects the caller can see.'
RETURN
  SELECT c.co_id, c.project_id, p.name, p.region, c.subcontractor, c.cost_code, c.description, c.status, c.amount_requested, c.submitted_date,
         l.line, l.item_desc, l.unit, l.quantity, l.unit_rate, l.amount
  FROM bhambs.construction_control_tower.change_orders c
  JOIN bhambs.construction_control_tower.projects p ON p.project_id = c.project_id
  LEFT JOIN bhambs.construction_control_tower.change_order_lines l ON l.co_id = c.co_id
  WHERE c.co_id = get_change_order.co_id
;;
SELECT * FROM get_unit_cost_baseline('03-3000', 'Northeast', 'rock removal')
;;
SELECT co_id, project_name, region, subcontractor, amount_requested, submitted_date, line, item_desc, quantity, unit_rate FROM get_change_order('CO-0142')
