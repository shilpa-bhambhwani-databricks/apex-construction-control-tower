SELECT project_name, market_sector, region, ROUND(MEASURE(risk_score)) AS risk_score
FROM project_risk_mv WHERE weeks_ago = 0 GROUP BY ALL ORDER BY risk_score DESC LIMIT 8
;;
SELECT signal, ROUND(MEASURE(risk_score), 1) AS pts_now
FROM project_risk_mv WHERE project_name LIKE 'Project Atlas%' AND weeks_ago = 0 GROUP BY ALL ORDER BY pts_now DESC
;;
SELECT weeks_ago, ROUND(MEASURE(risk_score)) AS atlas_score
FROM project_risk_mv WHERE project_name LIKE 'Project Atlas%' AND weeks_ago <= 8 GROUP BY ALL ORDER BY weeks_ago DESC
;;
SELECT market_sector, MEASURE(project_count) AS projects, ROUND(MEASURE(risk_score)) AS avg_risk
FROM project_risk_mv WHERE weeks_ago = 0 GROUP BY ALL ORDER BY avg_risk DESC
