CREATE OR REPLACE FUNCTION get_unit_cost_baseline(cost_code STRING, region STRING, item_keyword STRING)
RETURNS TABLE (item_desc STRING, unit STRING, n BIGINT, p25 DOUBLE, median DOUBLE, p75 DOUBLE, window_start DATE, window_end DATE)
COMMENT 'Resolve tool: trailing-24-month awarded unit-rate benchmark for a cost code + region + item keywords (every word must match; P25 / median / P75 and sample size).'
RETURN
  SELECT item_desc, first(unit), COUNT(*), ROUND(percentile(unit_rate, 0.25), 2), ROUND(percentile(unit_rate, 0.5), 2), ROUND(percentile(unit_rate, 0.75), 2),
         MIN(award_date), MAX(award_date)
  FROM bhambs.construction_control_tower.historical_unit_costs h
  WHERE h.cost_code = get_unit_cost_baseline.cost_code AND h.region = get_unit_cost_baseline.region
    AND aggregate(filter(split(lower(regexp_replace(get_unit_cost_baseline.item_keyword, '[^A-Za-z ]', ' ')), ' '), x -> length(x) > 2 AND x NOT IN ('and', 'the')),
                  true, (acc, x) -> acc AND lower(h.item_desc) LIKE concat('%', x, '%'))
    AND h.award_date >= DATE'2026-11-09' - INTERVAL 24 MONTHS
  GROUP BY item_desc
;;
SELECT item_desc, n, median FROM get_unit_cost_baseline('03-3000', 'Northeast', 'rock removal over-excavation')
