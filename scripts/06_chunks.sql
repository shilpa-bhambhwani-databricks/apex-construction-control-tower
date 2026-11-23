CREATE OR REPLACE TABLE doc_chunks (
  chunk_id STRING NOT NULL, doc_name STRING, doc_type STRING, project_id STRING, page INT, section STRING, text STRING
) TBLPROPERTIES (delta.enableChangeDataFeed = true)
COMMENT 'Retrieval chunks for AI Search: parsed document paragraphs (with page + section for citations) and historical RFI resolutions.'
;;
INSERT INTO doc_chunks
WITH el AS (
  SELECT doc_name, pos, e:type::string AS type, e:content::string AS content, e:bbox[0].page_id::int + 1 AS page
  FROM parsed_documents LATERAL VIEW posexplode(variant_get(parsed, '$.document.elements', 'ARRAY<VARIANT>')) t AS pos, e
), labeled AS (
  SELECT *, last_value(CASE WHEN type IN ('section_header', 'title') THEN content END, true) OVER (PARTITION BY doc_name ORDER BY pos) AS section
  FROM el WHERE type IN ('text', 'section_header', 'title')
)
SELECT concat(doc_name, '#', pos) AS chunk_id, doc_name,
  CASE WHEN doc_name LIKE 'Prime%' THEN 'prime_contract' WHEN doc_name LIKE 'Subcontract%' THEN 'subcontract' WHEN doc_name LIKE 'Spec%' THEN 'spec'
       WHEN doc_name LIKE 'Daily_Log%' THEN 'daily_log' WHEN doc_name LIKE 'Notice%' THEN 'letter' ELSE 'memo' END AS doc_type,
  'P-1001' AS project_id, page, section, concat_ws('\n', section, content) AS text
FROM labeled WHERE type = 'text'
;;
INSERT INTO doc_chunks
SELECT concat('rfi#', rfi_id), rfi_id, 'rfi', project_id, NULL, subject,
  concat('RFI ', rfi_id, ' (', coalesce(project_name, project_id), ', ', discipline, '): ', subject, '. Question: ', question, ' Resolution: ', resolution,
         ' Cost impact $', CAST(cost_impact_usd AS STRING), ', schedule impact ', CAST(schedule_impact_days AS STRING), ' days, turnaround ', CAST(turnaround_days AS STRING), ' days.')
FROM historical_rfis
;;
SELECT doc_type, COUNT(*) AS chunks FROM doc_chunks GROUP BY 1 ORDER BY 2 DESC
