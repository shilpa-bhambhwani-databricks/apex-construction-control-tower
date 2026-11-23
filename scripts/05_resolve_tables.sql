CREATE OR REPLACE TABLE historical_unit_costs COMMENT 'Awarded unit rates, trailing 24 months, by cost code / item / region. Portfolio-wide benchmark (used via get_unit_cost_baseline).' AS SELECT * FROM read_files('/Volumes/bhambs/construction_control_tower/raw/v2/historical_unit_costs.parquet')
;;
CREATE OR REPLACE TABLE change_order_lines COMMENT 'Line items for change orders (Clearstory COR detail).' AS SELECT * FROM read_files('/Volumes/bhambs/construction_control_tower/raw/v2/change_order_lines.parquet')
;;
ALTER TABLE change_order_lines SET ROW FILTER ct_row_scope ON (project_id)
;;
CREATE OR REPLACE TABLE historical_rfis COMMENT 'Closed RFIs with resolutions across projects (Procore + legacy Prolog). Institutional knowledge base for similar-RFI search.' AS SELECT * FROM read_files('/Volumes/bhambs/construction_control_tower/raw/v2/historical_rfis.parquet')
;;
CREATE OR REPLACE TABLE parsed_documents COMMENT 'ai_parse_document output for files in the documents volume.' AS
SELECT path, regexp_extract(path, '([^/]+)$', 1) AS doc_name, ai_parse_document(content) AS parsed
FROM read_files('/Volumes/bhambs/construction_control_tower/documents/', format => 'binaryFile', recursiveFileLookup => true)
;;
SELECT doc_name, schema_of_variant(parsed) AS shape FROM parsed_documents WHERE doc_name = 'Subcontract_Keystone_Concrete.pdf'
