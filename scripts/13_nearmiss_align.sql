MERGE INTO safety_observations o USING (SELECT project_id, market_sector FROM projects) p
ON o.project_id = p.project_id AND o.near_miss_flag AND o.date >= DATE'2026-11-09' - INTERVAL 13 DAYS
WHEN MATCHED THEN UPDATE SET
  category = CASE p.market_sector WHEN 'Data Center' THEN 'Fall protection' WHEN 'Healthcare' THEN 'Ladders' WHEN 'Aviation' THEN 'Struck-by'
                                  WHEN 'Education' THEN 'Housekeeping' ELSE 'Struck-by' END,
  description = CASE p.market_sector
    WHEN 'Data Center' THEN 'Near miss — worker at leading edge without tie-off (synthetic)' WHEN 'Healthcare' THEN 'Near miss — ladder used on unstable footing in corridor (synthetic)'
    WHEN 'Aviation' THEN 'Near miss — vehicle backing at airside gate (synthetic)' WHEN 'Education' THEN 'Near miss — student entered work zone via unblocked route (synthetic)'
    ELSE 'Near miss — tool dropped from upper level (synthetic)' END
;;
MERGE INTO jobsite_day d USING (
  SELECT project_id, SUM(CASE WHEN near_miss_flag THEN 1 ELSE 0 END) AS n FROM safety_observations
  WHERE date >= DATE'2026-11-09' - INTERVAL 13 DAYS GROUP BY project_id
) o ON d.project_id = o.project_id
WHEN MATCHED THEN UPDATE SET near_miss_count_14d = o.n
;;
SELECT d.project_id, d.near_miss_count_14d, d.near_miss_theme, collect_set(o.category) AS nm_categories
FROM jobsite_day d LEFT JOIN safety_observations o ON o.project_id = d.project_id AND o.near_miss_flag AND o.date >= DATE'2026-11-09' - INTERVAL 13 DAYS
WHERE d.project_id IN ('P-1001', 'P-1004', 'P-1011') GROUP BY ALL
