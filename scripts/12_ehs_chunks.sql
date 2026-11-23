INSERT INTO parsed_documents
SELECT path, regexp_extract(path, '([^/]+)$', 1), ai_parse_document(content)
FROM read_files('/Volumes/bhambs/construction_control_tower/documents/ehs/', format => 'binaryFile')
;;
INSERT INTO doc_chunks
WITH el AS (
  SELECT doc_name, pos, e:type::string AS type, e:content::string AS content, e:bbox[0].page_id::int + 1 AS page
  FROM parsed_documents LATERAL VIEW posexplode(variant_get(parsed, '$.document.elements', 'ARRAY<VARIANT>')) t AS pos, e
  WHERE doc_name = 'EHS_Field_Standards.pdf'
), labeled AS (
  SELECT *, last_value(CASE WHEN type IN ('section_header', 'title') THEN content END, true) OVER (PARTITION BY doc_name ORDER BY pos) AS section FROM el WHERE type IN ('text', 'section_header', 'title')
)
SELECT concat(doc_name, '#', pos), doc_name, 'ehs', 'ALL', page, section, concat_ws('\n', section, content) FROM labeled WHERE type = 'text'
;;
SELECT section, left(text, 90) FROM doc_chunks WHERE doc_type = 'ehs' ORDER BY chunk_id
