# Stage 4 — Gen AI: make it intelligent

Contracts, subcontracts, specs, daily logs and safety standards are parsed with `ai_parse_document`, chunked with page and section, and indexed in AI Search. Two tool-calling agents (Project Resolve and Jobsite Intelligence) run on a Databricks-hosted foundation model, retrieve from that index, call governed Unity Catalog functions, and log every step with MLflow Tracing. The outputs below are real.

Captured 2026-11-23 19:42 UTC by `scripts/capture_evidence.py` against the live workspace. All data is synthetic.

### ai_parse_document output — contracts, specs, logs and standards parsed from PDFs in a volume

```sql
SELECT doc_name, size(variant_get(parsed, '$.document.elements', 'ARRAY<VARIANT>')) AS parsed_elements,
       size(variant_get(parsed, '$.document.pages', 'ARRAY<VARIANT>')) AS pages
FROM parsed_documents ORDER BY doc_name
```

Result — 10 row(s):

```text
doc_name                              | parsed_elements | pages
--------------------------------------+-----------------+------
Daily_Log_2026-10-11.pdf              | 12              | 1
EHS_Field_Standards.pdf               | 24              | 2
Geotech_Memo_GM-07.pdf                | 6               | 1
Notice_Letter_Keystone_2026-10-23.pdf | 6               | 1
Prime_Contract_Atlas_Bldg3.pdf        | 20              | 2
Spec_03_30_00_Concrete.pdf            | 8               | 1
Spec_05_12_00_Structural_Steel.pdf    | 8               | 1
Spec_31_23_16_Excavation.pdf          | 10              | 1
Subcontract_Ironline_Steel.pdf        | 10              | 1
Subcontract_Keystone_Concrete.pdf     | 16              | 2
```

### Parsed elements for one document (real ai_parse_document output)

```sql
SELECT pos AS element, e:type::string AS type, e:bbox[0].page_id::int + 1 AS page, left(e:content::string, 110) AS content
FROM parsed_documents LATERAL VIEW posexplode(variant_get(parsed, '$.document.elements', 'ARRAY<VARIANT>')) t AS pos, e
WHERE doc_name = 'Subcontract_Keystone_Concrete.pdf' ORDER BY pos LIMIT 14
```

Result — 14 row(s):

```text
element | type           | page | content
--------+----------------+------+-----------------------------------------------------------------------------------------------------------------
0       | page_header    | 1    | Subcontract - Keystone Concrete LLC (Concrete & Foundations)
1       | page_header    | 1    | SYNTHETIC DEMO DOCUMENT
2       | section_header | 1    | Subcontract Agreement
3       | text           | 1    | Project: Project Atlas - Building 3 (P-1001) ⏎ Subcontractor: Keystone Concrete LLC | Scope: cost codes 03-3000,
4       | section_header | 1    | Section 2 - Scope
5       | text           | 1    | 2.1 Cast-in-place concrete, pile caps PC-1 through PC-60, grade beams, and associated excavation and ⏎ backfill
6       | section_header | 1    | Section 11 - Changes and Concealed Conditions
7       | text           | 1    | 11.1 Changes shall be priced per Exhibit B unit rates where applicable, otherwise per Section 11.4. ⏎ 11.2 Notic
8       | page_footer    | 1    | Subcontract AT-SC-0330
9       | page_number    | 1    | Page 1
10      | page_header    | 2    | Subcontract - Keystone Concrete LLC (Concrete & Foundations)
11      | page_header    | 2    | SYNTHETIC DEMO DOCUMENT
12      | section_header | 2    | Exhibit B - Unit Rates (excerpt)
13      | text           | 2    | Rock removal and over-excavation at pile caps (03-3000): $118.00 per cubic yard. ⏎ Lean concrete backfill (03-30
```

### Retrieval chunks behind the AI Search index

```sql
SELECT doc_type, COUNT(*) AS chunks, COUNT(DISTINCT doc_name) AS documents FROM doc_chunks GROUP BY 1 ORDER BY 2 DESC
```

Result — 8 row(s):

```text
doc_type       | chunks | documents
---------------+--------+----------
rfi            | 300    | 300
ehs            | 8      | 1
subcontract    | 7      | 2
spec           | 7      | 3
prime_contract | 6      | 1
daily_log      | 4      | 1
memo           | 1      | 1
letter         | 1      | 1
```

### AI Search (vector) index status

```text
index          : bhambs.construction_control_tower.doc_chunks_index
type           : DELTA_SYNC
endpoint       : ct-vector-search
ready          : True
indexed rows   : 334
embedding model: databricks-gte-large-en
```

### Semantic retrieval over the index — the question a project manager would ask

```sql
SELECT doc_name, page, section, left(text, 170) AS passage
FROM vector_search(index => 'bhambs.construction_control_tower.doc_chunks_index', query_text => 'How many days does the subcontractor have to give notice of a differing site condition?', num_results => 5)
```

Result — 5 row(s):

```text
doc_name                              | page | section                                             | passage
--------------------------------------+------+-----------------------------------------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
Subcontract_Keystone_Concrete.pdf     | 1    | Section 11 - Changes and Concealed Conditions       | Section 11 - Changes and Concealed Conditions ⏎ 11.1 Changes shall be priced per Exhibit B unit rates where applicable, otherwise per Section 11.4. ⏎ 11.2 Notice of Concealed
Notice_Letter_Keystone_2026-10-23.pdf | 1    | Notice of Differing Site Condition                  | Notice of Differing Site Condition ⏎ Date: 2026-10-23 ⏎ To: General Contractor, Project Atlas | From: Keystone Concrete LLC ⏎  ⏎ This letter serves as written notice under Sub
Prime_Contract_Atlas_Bldg3.pdf        | 1    | Article 4 - Changes in the Work and Site Conditions | Article 4 - Changes in the Work and Site Conditions ⏎ 4.1 The Owner may order changes in the Work by Change Order or Construction Change Directive. Pricing of ⏎ changes shall
Prime_Contract_Atlas_Bldg3.pdf        | 2    | Article 9 - Claims                                  | Article 9 - Claims ⏎ 9.1 Claims must be initiated by written notice within 21 days after the event giving rise to the Claim. The parties ⏎ shall cooperate in good faith to co
Subcontract_Keystone_Concrete.pdf     | 1    | Subcontract Agreement                               | Subcontract Agreement ⏎ Project: Project Atlas - Building 3 (P-1001) ⏎ Subcontractor: Keystone Concrete LLC | Scope: cost codes 03-3000, 31-2316 ⏎ Subcontract Sum: $48,600,000
```

### Agent tool: historical unit-cost benchmark (Unity Catalog function)

```sql
SELECT * FROM get_unit_cost_baseline('03-3000', 'Northeast', 'rock removal')
```

Result — 1 row(s):

```text
item_desc                        | unit | n  | p25    | median | p75    | window_start | window_end
---------------------------------+------+----+--------+--------+--------+--------------+-----------
Rock removal and over-excavation | CY   | 37 | 115.64 | 120.0  | 135.59 | 2024-11-26   | 2026-11-03
```

### Agent tool: change order with line items (Unity Catalog function, row-filtered)

```sql
SELECT co_id, project_name, subcontractor, amount_requested, submitted_date, line, item_desc, quantity, unit, unit_rate, line_amount
FROM get_change_order('CO-0142')
```

Result — 3 row(s):

```text
co_id   | project_name                               | subcontractor         | amount_requested | submitted_date | line | item_desc                        | quantity | unit | unit_rate | line_amount
--------+--------------------------------------------+-----------------------+------------------+----------------+------+----------------------------------+----------+------+-----------+------------
CO-0142 | Project Atlas — Data Center Campus, Bldg 3 | Keystone Concrete LLC | 486000.0         | 2026-10-28     | 1    | Rock removal and over-excavation | 2400.0   | CY   | 142.0     | 340800.0
CO-0142 | Project Atlas — Data Center Campus, Bldg 3 | Keystone Concrete LLC | 486000.0         | 2026-10-28     | 3    | Dewatering (T&M)                 | 1.0      | LS   | 24950.0   | 24950.0
CO-0142 | Project Atlas — Data Center Campus, Bldg 3 | Keystone Concrete LLC | 486000.0         | 2026-10-28     | 2    | Lean concrete backfill           | 650.0    | CY   | 185.0     | 120250.0
```

### MLflow traces logged by the agents from the app (experiment 3807042541599144, newest first) — 28 runs

```text
trace_id                            | started (UTC)    | state | duration | agent         | request
------------------------------------+------------------+-------+----------+---------------+---------------------------------------------------------------------------------
tr-0b82a67899ff378f0907e325a03bd617 | 2026-11-18 14:16 | OK    | 26.6s    | resolve_agent | {"item": {"id": "CO-0142", "kind": "CO", "project": {"project_id": "P-1001", "na
tr-29b982165ac10149fb99d8159417f1ae | 2026-11-18 03:41 | OK    | 19.6s    | jobsite_agent | {"project": {"project_id": "P-1001", "name": "Project Atlas — Data Center Campus
tr-6acb3cc263d4a0844fa1688358f39cf4 | 2026-11-18 03:36 | OK    | 11.9s    | jobsite_agent | {"project": {"project_id": "P-1001", "name": "Project Atlas — Data Center Campus
tr-d5360455694b532d11d61203c3a95819 | 2026-11-18 03:34 | OK    | 22.0s    | jobsite_agent | {"project": {"project_id": "P-1001", "name": "Project Atlas — Data Center Campus
tr-73813160d29171e921e6a5e6aada5ecf | 2026-11-18 03:29 | OK    | 28.6s    | resolve_agent | {"item": {"id": "CO-0142", "kind": "CO", "project": {"project_id": "P-1001", "na
tr-aeccc0c6a24c6a3e02371cb2264c2eed | 2026-11-18 03:22 | OK    | 25.2s    | resolve_agent | {"item": {"id": "CO-0142", "kind": "CO", "project": {"project_id": "P-1001", "na
tr-1357cd27bf8262365f75264e48b874b5 | 2026-11-16 21:07 | OK    | 19.8s    | jobsite_agent | {"project": {"project_id": "P-1001", "name": "Project Atlas — Data Center Campus
tr-5cda97b9f9558fd45ba0e0bbaad7b792 | 2026-11-16 20:51 | OK    | 22.6s    | resolve_agent | {"item": {"id": "CO-0142", "kind": "CO", "project_id": "P-1001", "region": "Nort
tr-b5b0163ce4b1b9a9bf4a09799b22a2ea | 2026-11-16 20:50 | OK    | 21.3s    | jobsite_agent | {"project": {"project_id": "P-1001", "name": "Project Atlas — Data Center Campus
tr-40aedaaa64a4b1f54ad8e324b496aaa0 | 2026-11-16 20:07 | OK    | 23.1s    | resolve_agent | {"item": {"id": "CO-0142", "kind": "CO", "project": {"project_id": "P-1001", "na
tr-7c37996997c796f00440d5baed939c41 | 2026-11-16 20:06 | OK    | 19.2s    | resolve_agent | {"item": {"id": "CO-0102", "kind": "CO", "project": {"project_id": "P-1001", "na
tr-0e4f2f6055af7c87b3136c836312694c | 2026-11-12 15:21 | OK    | 18.3s    | jobsite_agent | {"project": {"project_id": "P-1001", "name": "Project Atlas — Data Center Campus
tr-85ac01e88b65cd7c563d690f015e1b34 | 2026-11-10 21:47 | OK    | 12.8s    | jobsite_agent | {"project": {"project_id": "P-1001", "name": "Project Atlas — Data Center Campus
tr-40c2e3294186cb21cc6c2cfd13824bd4 | 2026-11-10 21:46 | OK    | 23.4s    | resolve_agent | {"item": {"id": "CO-0142", "kind": "CO", "project": {"project_id": "P-1001", "na
tr-f91ae02661cecf795504bfcd9c039dce | 2026-11-10 21:46 | OK    | 9.6s     | jobsite_agent | {"project": {"project_id": "P-1001", "name": "Project Atlas — Data Center Campus
tr-c65e274f96805969d53acee56d58bc2a | 2026-11-10 21:45 | OK    | 28.2s    | resolve_agent | {"item": {"id": "CO-0142", "kind": "CO", "project": {"project_id": "P-1001", "na
tr-0d84fcf12c46a943e1d23aec6900a15b | 2026-11-10 03:11 | OK    | 6.4s     | resolve_agent | {"item": {"id": "RFI-0108", "kind": "RFI", "project": {"project_id": "P-1001", "
tr-9de592a0bd9582632b6c8616a5452609 | 2026-11-10 02:51 | OK    | 13.9s    | jobsite_agent | {"project": {"project_id": "P-1001", "name": "Project Atlas — Data Center Campus
tr-b15c7223be0c308a59f4a266cf5340d0 | 2026-11-10 02:50 | OK    | 19.1s    | jobsite_agent | {"project": {"project_id": "P-1001", "name": "Project Atlas — Data Center Campus
tr-75bd0e3d4406d4d05e03424e0a9bc84b | 2026-11-10 02:47 | OK    | 17.4s    | jobsite_agent | {"project": {"project_id": "P-1001", "name": "Project Atlas", "market_sector": "
tr-17b5460a4444f103d24cf9141eb2d9ca | 2026-11-10 02:41 | OK    | 23.0s    | jobsite_agent | {"project": {"project_id": "P-1001", "name": "Project Atlas"}, "question": "What
tr-b6bf291f37ec714812e093254cf6c15e | 2026-11-10 02:26 | OK    | 7.0s     |               | {"item": {"id": "RFI-0387", "kind": "RFI", "project": {"project_id": "P-1001", "
tr-d6193fa513850f8fb32f7466d280b1a2 | 2026-11-10 02:25 | OK    | 20.8s    |               | {"item": {"id": "CO-0142", "kind": "CO", "project": {"project_id": "P-1001", "na
tr-3992bd495de2ce68f33a1afd790e208a | 2026-11-10 01:11 | OK    | 21.8s    |               | {"item": {"id": "CO-0142", "kind": "CO", "project": {"project_id": "P-1001", "na
tr-f469571e545818efccab5877702e14a4 | 2026-11-10 01:01 | OK    | 25.9s    |               | {"item": {"id": "CO-0142", "kind": "CO", "project": {"project_id": "P-1001", "na
tr-c54d0ac635701bebc0e546a54a5e31e6 | 2026-11-10 00:51 | OK    | 42.9s    |               | {"item": {"id": "CO-0142", "kind": "CO", "project": {"project_id": "P-1001", "na
tr-6c089c59cdbe2579379268b4a5766bc5 | 2026-11-10 00:47 | ERROR | 0.5s     |               | {"item": {"id": "CO-0142", "kind": "CO", "project": {"project_id": "P-1001", "na
tr-c541d1b18c0dcbfb282e5c784807bab5 | 2026-11-10 00:35 | ERROR | 1.5s     |               | {"item": {"id": "CO-0142", "kind": "CO", "project": {"project_id": "P-1001", "na
```

### Agent run tr-aeccc0c6a24c6a3e02371cb2264c2eed — the run behind the human decision stored in Lakebase (see 03_lakebase.md)

```text
started  : 2026-11-18 03:22 UTC
state    : OK
duration : 25.2s
agent    : resolve_agent
```

Request (preview kept by MLflow):

```text
{"item": {"id": "CO-0142", "kind": "CO", "project": {"project_id": "P-1001", "name": "Project Atlas — Data Center Campus, Bldg 3", "region": "Northeast"}, "co_id": "CO-0142", "subcontractor": "Keystone Concrete LLC", "cost_code": "03-3000", "description": "Additional foundation work — subsurface rock", "status": "Pending", "amount_requested": "486000.0", "submitted_date": "2026-10-28"}, "question": "Is this change order covered by the prime contract, and is the pricing in line with similar work in this region?", "user": "<presenter>"}
```

Response (preview kept by MLflow):

```text
{"answer": "**Coverage**\n- ✓ Prime §4.3 expressly treats unforeseen rock within the excavation limits as a concealed condition, which gives an equitable adjustment [Prime_Contract_Atlas_Bldg3.pdf p.1 §4.3]. Geotech memo GM-07 says rock at about -6 ft differs materially from the report, which showed shale below -12 ft [Geotech_Memo_GM-07.pdf p.1].\n- ⚠ Prime §4.3 requires written notice to the Owner within 14 days of first observance. That deadline was 25 Oct (11 Oct + 14 days). I found no GC-to-Owner notice in the records, so confirm one was sent [Prime_Contract_Atlas_Bldg3.pdf p.1 §4.3].\n\n**Notice**\n- ⚠ Rock was first logged 11 Oct [Daily_Log_2026-10-11.pdf p.1]. Keystone's written notice is dated 23 Oct [Notice_Letter_Keystone_2026-10-23.pdf p.1]. That is 12 days, against a 7-day requirement, so 5 days late [Subcontract_Keystone_Concrete.pdf p.1 §11.2].\n- ⚠ Excavation continued after the 11 Oct log entry, so the work wasn't left undisturbed [Daily_Log_2026-10-11.pdf p.1]. §11.2 allows waiver of costs incurred before notice. Keystone must also attach logs and photos [Subcontract_Keystone_Concrete.pdf p.1 §11.2–11.3].\n\n**Pricing**\n- ⚠ Rock removal is $142/CY against a contract rate of $118, which is +20.3% (142/118 − 1) [Subcontract_Keystone_Concrete.pdf p.2 Exh. B]. It is also +18.3% over the regional median of $120 and above the P75 of $135.59 (n=37) [get_unit_cost_baseline]. Over 2,400 CY, the excess over contract is $57,600 [get_change_order].\n- ⚠ Backfill is $185/CY against a contract rate of $172, which is +7.6% [Subcontract_Keystone_Concrete.pdf p.2 Exh. B]. It is +13.2% over the median of $163.44 and above the P75 of $176.79 (n=122) [get_unit_cost_baseline]. Over 650 CY, the excess over contract is $8,450.\n- ✓ Dewatering is $24,950 on a T&M basis, under the $30,000 per-occurrence cap [Subcontract_Keystone_Concrete.pdf p.2 Exh. B]. Backup is still required [Subcontract_Keystone_Concrete.pdf p.1 §11.4].\n\n**Recommendation**\n- Entitlement looks supported under prime §4.3. Consider pricing at Exhibit B rates, which comes to $419,950 (283,200 + 111,800 + 24,950). That is $66,050 (13.6%) below the $486,000 requested [get_change_order]. Exhibit B governs where it applies [Subcontract_Keystone_Concrete.pdf p.1 §11.1].\n- Before deciding, confirm the Owner notice was sent. Also review the late-notice waiver exposure for costs incurred between 11 and 23 Oct, and request daily logs, photos and quantity backup. The decision is yours.", "steps": ["get_change_order", "search_documents", "search_documents", "search_documents", "search_documents", "get_unit_cost_baseline", "get_unit_cost_baseline"]}
```

### Agent run tr-d5360455694b532d11d61203c3a95819 — newest `jobsite_agent` run with full span data

```text
started  : 2026-11-18 03:34 UTC
state    : OK
duration : 22.0s
spans    : 8
  AGENT       jobsite_agent                                                22.0s
  CHAT_MODEL  llm_round_1                                                   3.7s
  TOOL        get_lookahead                                                 1.3s
  TOOL        get_jobsite_day                                               2.2s
  TOOL        get_recent_observations                                       1.7s
  RETRIEVER   search_standards                                              0.5s
  RETRIEVER   search_standards                                              0.5s
  CHAT_MODEL  llm_round_2                                                  12.0s
```

Request:

```text
{'project': {'project_id': 'P-1001', 'name': 'Project Atlas — Data Center Campus, Bldg 3', 'market_sector': 'Data Center', 'region': 'Northeast', 'pct_complete': '46'}, 'question': "My steel crew is up on Bldg 1 today. Anything in this photo I should act on before Thursday's pick?", 'photo': True, 'user': 'Dana Morales (simulated)'}
```

Model output (verbatim, first 4,500 characters):

```text
**Photo check (an aid only. It doesn't declare any area safe.)**

**What I can see**
- Two ironworkers are at a beam-to-column connection. Both wear harnesses and hard hats.
- I can't see a lanyard connected to an anchor on either worker. Confirm tie-off in person.
- A hoist line and hook hang right at the connection, close to their hands and bodies. I can't tell whether the hook has a safety latch.
- Wire cable lines run across the frame. I can't tell whether they are a perimeter cable system or something else.
- I can't tell the height from the photo.

**Standards**
- Company: 100% tie-off at 6 ft, unless the EHS manager approves a written exception [EHS-11 §Fall Protection and Leading Edges].
- OSHA: steel erection fall protection applies at 15 ft, with connector provisions [OSHA 1926.760]. The general rule applies at 6 ft [OSHA 1926.501(b)(1)].
- Crane and rigging work falls under [OSHA 1926 Subpart CC]. The company standard adds a pre-lift meeting and an exclusion zone [EHS-14 §Cranes, Rigging, and Critical Lifts].

**Act on before Thursday**
1. **Stand-down and toolbox talk.** You have 2 leading-edge fall near-misses in 14 days, which triggers one [observations][EHS-11]. Today's L2 decking is a leading-edge activity [lookahead].
2. **RFI-0387** (embed plates, L2 grid B) has been open 26 days and was needed today. L2 decking isn't ready [lookahead].
3. **Wind** is 18 mph gusting 28 today [jobsite_day]. That is close to the company stop limits of more than 20 sustained or more than 30 gusts [EHS-14]. Re-check the forecast for Thursday.
4. **Critical lift plan** for the 220-ton roof steel pick. The lookahead shows it as required and the pick as ready. Confirm the plan is actually on file [lookahead].
5. **Crew:** Ironline was 3 short of 8 yesterday [jobsite_day]. Check who is on the leading edge and whether any first-year workers need a monitor [EHS-11].
```

### Agent run tr-5cda97b9f9558fd45ba0e0bbaad7b792 — newest `resolve_agent` run with full span data

```text
started  : 2026-11-16 20:51 UTC
state    : OK
duration : 22.6s
spans    : 12
  AGENT       resolve_agent                                                22.6s
  CHAT_MODEL  llm_round_1                                                   2.7s
  TOOL        get_change_order                                              1.7s
  RETRIEVER   search_documents                                              0.4s
  RETRIEVER   search_documents                                              0.4s
  RETRIEVER   search_documents                                              0.5s
  RETRIEVER   search_documents                                              0.5s
  CHAT_MODEL  llm_round_2                                                   2.7s
  TOOL        get_unit_cost_baseline                                        1.0s
  TOOL        get_unit_cost_baseline                                        0.7s
  RETRIEVER   search_documents                                              0.3s
  CHAT_MODEL  llm_round_3                                                  11.7s
```

Request:

```text
{'item': {'id': 'CO-0142', 'kind': 'CO', 'project_id': 'P-1001', 'region': 'Northeast'}, 'question': 'Is this change order covered by the prime contract, and is the pricing in line with similar work in this region?', 'user': 'dry-run'}
```

Model output (verbatim, first 4,500 characters):

```text
**Coverage**
- ✓ Prime §4.3 treats unforeseen rock within the excavation limits as a concealed subsurface condition, which earns an equitable adjustment [Prime_Contract_Atlas_Bldg3.pdf p.1 §4.3]. Geotech memo GM-07 says rock at about -6 ft differs materially from the report's shale below -12 ft [Geotech_Memo_GM-07.pdf p.1].
- ⚠ Confirm that PC-14 to PC-22 sit inside the drawn excavation limits, because §4.3 depends on that. I found no record of the GC's own written notice to the Owner. That notice is due within 14 days of first observance, which is 25 Oct (11 Oct + 14) [Prime_Contract_Atlas_Bldg3.pdf p.1 §4.3].

**Notice**
- ⚠ Rock was first logged on 11 Oct [Daily_Log_2026-10-11.pdf p.1]. Keystone's written notice is dated 23 Oct [Notice_Letter_Keystone_2026-10-23.pdf p.1]. That is 12 days (23 − 11), against a 7-day requirement, so it is 5 days late [Subcontract_Keystone_Concrete.pdf p.1 §11.2].
- ⚠ Work continued at PC-18 to PC-22 on 11 Oct, so the condition may have been disturbed before notice [Daily_Log_2026-10-11.pdf p.1]. §11.2 allows waiver of costs incurred before notice [Subcontract_Keystone_Concrete.pdf p.1 §11.2]. The CO was submitted 28 Oct, 17 days after discovery [get_change_order].

**Pricing**
- ⚠ Rock removal is $142/CY on 2,400 CY. That is +20.3% over the $118 Exhibit B rate (142/118 − 1) [Subcontract_Keystone_Concrete.pdf p.2 §Exhibit B]. It is +18.3% over the Northeast median of $120 and above the P75 of $135.59 (n=37) [get_unit_cost_baseline].
- ⚠ Lean backfill is $185/CY on 650 CY. That is +7.6% over the $172 contract rate and +13.2% over the $163.44 median. It is above the P75 of $176.79 (n=122) [get_unit_cost_baseline]. Dewatering at $24,950 T&M is within the $30,000 cap, but it needs backup [Subcontract_Keystone_Concrete.pdf p.2 §Exhibit B].

**Recommendation**
- Before the PM decides, consider repricing at Exhibit B rates, since §11.1 makes them govern [Subcontract_Keystone_Concrete.pdf p.1 §11.1]. That gives $419,950 (2,400×118 + 650×172 + 24,950), which is $66,050 (13.6%) below the $486,000 requested [get_change_order].
- Confirm the Owner notice status and the excavation limits. Then decide whether to reserve rights on costs incurred 11–23 Oct under the 7-day notice clause.
```

### Agent run tr-b6bf291f37ec714812e093254cf6c15e — newest `agent` run with full span data

```text
started  : 2026-11-10 02:26 UTC
state    : OK
duration : 7.0s
spans    : 4
  AGENT       resolve_agent                                                 7.0s
  CHAT_MODEL  llm_round_1                                                   1.7s
  RETRIEVER   find_similar_rfis                                             0.5s
  CHAT_MODEL  llm_round_2                                                   4.8s
```

Request:

```text
{'item': {'id': 'RFI-0387', 'kind': 'RFI', 'project': {'project_id': 'P-1001', 'name': 'Project Atlas', 'region': 'Northeast'}, 'rfi_id': 'RFI-0387', 'subject': 'Embed plate conflict at L2 beam', 'discipline': 'Structural', 'ball_in_court': 'Architect'}, 'question': 'Has a similar RFI come up before, and how was it resolved?', 'user': 'presenter (local test)'}
```

Model output (verbatim, first 4,500 characters):

```text
**Precedents**
- ⚠ **PL-4471 (Legacy DC-17) is the closest match and the worst outcome.** It was an embed plate and beam pocket conflict at level 2. The RFI sat 19 days waiting on the EOR. It caused a 5-day steel erection delay and a $52,000 cost. The fix was a revised S-201 with relocated plates [find_similar_rfis].
- ✓ **RFI-0212 (Orion) is a near-identical conflict and was resolved quickly.** Embed plates on S-201 conflicted with beam pockets on S-305 at L2. ASI-019 closed it in 6 days. It shifted the plates 4 in. east and upsized them to 3/4 in. There was no schedule impact. The steel sub priced it as a $38K CO [find_similar_rfis].
- ✓ **RFI-0098 (Nova) was a related but smaller issue.** It was a plate size mismatch at a beam seat. The EOR approved a field fix (added shim plate) in 4 days at $0 and 0 days [find_similar_rfis].

**Recommendation**
- ⚠ **Expect a $38K–$52K cost exposure.** Turnaround on the two closest precedents ranges from 6 to 19 days, a 13-day spread (19 − 6). Ask the Architect and EOR for a response within about 6 days. The 19-day case also cost 5 days of schedule.
- ✓ **Propose a fix with the RFI.** Suggest relocating or upsizing the plates, as in RFI-0212, or a shim plate if the conflict is minor, as in RFI-0098. Check the fabrication and steel erection dates now. The PM decides.
```
