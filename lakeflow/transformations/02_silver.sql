-- SILVER — cleaned, de-duplicated, quality-checked tables that feed the governed risk metric view
-- (project_risk_mv), which in turn feeds the Risk Radar page of the app and the Portfolio Risk Genie Agent.
--
-- Expectations (data quality rules) are recorded in the pipeline event log on every update:
--   ON VIOLATION DROP ROW  -> bad rows are kept out of the score
--   (no ON VIOLATION)      -> rows are kept, violations are counted and reported
-- De-duplication keeps the latest landed version of each business key, so re-landing a corrected extract is safe.
-- Docs: https://docs.databricks.com/aws/en/ldp/developer/ldp-sql-ref-create-materialized-view
--       https://docs.databricks.com/aws/en/ldp/expectations

CREATE OR REFRESH MATERIALIZED VIEW silver_projects (
  CONSTRAINT valid_project_id        EXPECT (project_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT valid_region            EXPECT (region IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT pct_complete_in_range   EXPECT (pct_complete BETWEEN 0 AND 100),
  CONSTRAINT positive_contract_value EXPECT (contract_value > 0)
)
COMMENT 'Silver: one row per project (latest landed version). Source for project_risk_mv dimensions. Synthetic.'
TBLPROPERTIES ('quality' = 'silver')
WITH ROW FILTER bhambs.construction_control_tower.ct_row_scope ON (project_id)
AS SELECT project_id, name, market_sector, region, business_unit, contract_value, bid_margin_pct,
          start_date, substantial_completion_date, pct_complete, project_executive, superintendent
FROM bronze_projects
QUALIFY ROW_NUMBER() OVER (PARTITION BY project_id ORDER BY _source_modified_at DESC, _ingested_at DESC) = 1;

CREATE OR REFRESH MATERIALIZED VIEW silver_project_signal_weekly (
  CONSTRAINT valid_project_id   EXPECT (project_id IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT valid_week         EXPECT (week IS NOT NULL) ON VIOLATION DROP ROW,
  CONSTRAINT known_signal       EXPECT (signal IN ('rfi', 'co', 'submittal', 'schedule', 'cost', 'safety')) ON VIOLATION DROP ROW,
  CONSTRAINT sub_score_in_range EXPECT (sub_score BETWEEN 0 AND 100) ON VIOLATION DROP ROW,
  CONSTRAINT weight_in_range    EXPECT (weight > 0 AND weight <= 1) ON VIOLATION DROP ROW,
  CONSTRAINT raw_value_present  EXPECT (raw_value IS NOT NULL)
)
COMMENT 'Silver: one row per project / week / signal (latest landed version). Source for project_risk_mv measures. Synthetic.'
TBLPROPERTIES ('quality' = 'silver')
WITH ROW FILTER bhambs.construction_control_tower.ct_row_scope ON (project_id)
AS SELECT project_id, week, signal, sub_score, raw_value, weight
FROM bronze_project_signal_weekly
QUALIFY ROW_NUMBER() OVER (PARTITION BY project_id, week, signal ORDER BY _source_modified_at DESC, _ingested_at DESC) = 1;
