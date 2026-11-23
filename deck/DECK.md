# Protect project margin before it fades

**Construction Control Tower for a commercial general contractor**

Business presentation · "Apex Construction" is a fictional contractor · every project, dollar and document in the prototype is synthetic · built on Databricks

---

## 1. The outcome: see margin and schedule risk weeks earlier — and act on it in the same place

A general contractor wins or loses the year on a handful of projects. The Control Tower gives operations and finance leaders one place to see which jobs are drifting, why, and what to do next.

| Outcome | What the working prototype showed (synthetic data) |
|---|---|
| **Risk seen early, not at the monthly cost report** | Project Atlas's risk score climbed from 50 to 73 over 8 weeks; the drivers were visible each week: cost forecast, $2.08M of pending change orders, schedule float, aging RFIs |
| **Margin fade explained by cause, per project** | 3 projects breaching the fade threshold — Atlas 5.53% → 3.11% ($29.9M), Meridian 7.25% → 4.63% ($14.1M), Vega 6.09% → 3.86% ($16.8M) |
| **Change orders reviewed against the contract in seconds, with citations** | One $486,000 change order: agent found the notice was 5 days late and pricing 18–20% over contract and benchmark rates; repricing at contract rates = $419,950, which is $66,050 (13.6%) lower. Review took 23 seconds |
| **Each person sees only their projects** | Same question, three identities: operations leadership sees 40 projects, a regional PM sees 11, a superintendent sees 1 |

---

## 2. Why this matters: the industry's numbers

- Large projects typically take **20% longer** than scheduled and run **up to 80% over budget** (McKinsey, 2016)
- Construction professionals spend **35% of their time** — more than 14 hours a week — on non-productive work such as hunting for project information, resolving conflicts and rework (FMI / PlanGrid, 2018)
- **48% of rework** in the US is caused by poor project data and miscommunication — more than **$31.3 billion a year** (FMI / PlanGrid, 2018)
- An average project generates **796 RFIs**, with a median reply time of **9.7 days** (Navigant Construction Forum, 2013; 1,362 projects)
- The average North American construction dispute is worth **$43.0 million** and takes **14.4 months** to resolve (Arcadis, 2024 report)
- **1,075** construction workers died on the job in the US in 2023 — the most of any industry sector (US Bureau of Labor Statistics)

General contractors work on thin margins, so a 2-point fade on one large job can erase the profit of several good ones.

---

## 3. The customer problem: the signals exist, but nobody sees them together in time

A project executive at a general contractor running data center, healthcare and aviation work has the facts spread across five systems:

- RFIs and submittals in the project management system
- Budget, commitments and forecast in the ERP
- Critical-path float in the scheduling tool
- Change orders in the change-management system
- Near-misses and observations in the safety system
- And the rules that decide who pays — notice periods, unit rates, escalation clauses — locked in contract PDFs

Each system is accurate on its own. The problem is the gap between them:

- Risk shows up as a combination — aging RFIs on critical-path work, plus pending change orders, plus float burning — and no single system shows the combination
- Margin fade is found at the monthly cost review, after contingency is already spent
- Contract notice windows (7 and 14 days in the prototype's contracts) pass before anyone connects the daily log to the contract clause
- Superintendents plan the next two weeks without knowing which activities are blocked by an open RFI or an unapproved submittal

---

## 4. The solution: one Control Tower, three views, one governed set of numbers

**Portfolio Risk Radar — for operations leadership**
One risk score (0–100) per project, built from six signals: aging RFIs, pending change-order exposure, overdue submittals, schedule float consumed, cost forecast vs. budget, and safety observations. Ask questions in plain English; assign a follow-up to an owner in one click.

**Project Resolve — for project controls and project managers**
An AI agent reviews a change order or RFI against the prime contract, the subcontract, the specs, the daily logs and 24 months of awarded unit rates — then returns a recommendation with page-level citations. A person makes the decision; the decision and its evidence are recorded.

**Jobsite Intelligence — for superintendents and safety**
"Ready to work?" for the next two weeks: which activities are blocked, by what, and who owns the blocker. Safety standards answered for this project, this week. Photo hazard check as an aid.

**Margin Watch — for the office of the CFO**
Bid margin vs. projected margin by project, with fade explained by cause (price escalation, missed notice, unbought scope) in plain-English Q&A.

The Control Tower reads from the systems of record. It never writes to them.

---

## 5. What the executive sponsor gets (COO / CFO)

**The KPIs you already run the business on — earlier, and with the cause attached**

| KPI | Today | With the Control Tower |
|---|---|---|
| Projected margin vs. bid margin (points) | Monthly, after the cost report | Continuously, by project, with the cause of fade |
| Margin fade ($) and projects breaching threshold | Found after contingency is spent | Flagged while contingency remains |
| Portfolio risk trend | Assembled by hand for the ops review | One score, same definition everywhere, 8-week trend |
| Pending change-order exposure ($) | In a separate log | Part of the risk score and the margin view |
| Time to answer "which jobs need me this week?" | Calls and spreadsheets | A question in plain English, answered in about 20–30 seconds |

**The arithmetic of margin protection (your figures replace ours):**
every 0.1 point of margin fade avoided is worth $1 million of gross profit per $1 billion of annual volume.

In the prototype's synthetic portfolio, three projects carry $60.8M of projected fade. The Control Tower does not make that go away. It shows it while there is still time to act — recover through change orders, enforce notice, re-buy scope.

---

## 6. What the domain owner gets (VP Operations / Project Controls / Project Executive)

**The working KPIs of project delivery — in one place, with the next action**

| KPI | What changes |
|---|---|
| RFIs aging more than 21 days | Ranked by whether they block critical-path work, with the owner |
| Change-order review cycle time | Contract, notice and pricing checks done in seconds; reviewer starts from a cited draft, not a blank page |
| Notice compliance | Daily log date vs. notice letter date vs. contract clause, checked automatically |
| Unit-rate variance vs. benchmark | Every line compared to the contract rate and the 24-month regional median |
| Overdue submittals and float consumed | Visible per project and tied to the lookahead |
| Lookahead readiness | Blocked activities, the blocker, the owner, the needed-by date |
| Near-misses, trailing 14 days | By category, next to the high-risk work planned this week |

**What your teams keep:** their systems, their process, their judgment. The agent drafts and cites. People decide. Every decision is stored with the evidence it was based on.

---

## 7. Proof: what the working prototype measured

All figures below are from the running prototype on synthetic data. The run output is in the project repository as text.

| What ran | Result |
|---|---|
| Source feeds ingested | 9 feeds, 21,352 rows, loaded incrementally |
| Data quality rules on the risk inputs | 10 rules, all passing, 0 rows dropped |
| Projects scored | 40 projects, 6 signals, 26 weekly snapshots |
| Risk score consistency | Identical results before and after moving the score onto the automated pipeline |
| Access control | 40 / 11 / 1 projects visible to leadership / regional PM / superintendent — in the data, in the app and in Q&A |
| Change-order agent | 23 seconds, 12 steps: 1 change-order lookup, 5 document searches, 2 benchmark lookups, cited answer |
| Plain-English questions | 7 of 7 answered in 18–28 seconds, each with the query behind it |
| Actions recorded | 3 follow-ups, 6 notifications, 1 change-order decision stored with its evidence trail |

---

## 8. How it works: one platform from raw data to decision

1. **Ingest** — project, cost, schedule, change-order and safety extracts land and are loaded automatically, with quality checks (Lakeflow)
2. **Govern** — one catalog for tables, documents and AI tools; one rule decides who sees which projects; one definition of the risk score (Unity Catalog)
3. **Serve operations** — follow-ups, notifications and decisions are stored in a transactional database built into the platform (Lakebase)
4. **Add intelligence** — contracts and specs are parsed and searchable; agents check change orders and jobsite readiness and cite their sources (Gen AI)
5. **Ask in plain English** — leaders and project teams ask questions; answers come with the numbers and the query behind them (Genie)
6. **Put it in people's hands** — one application for the office and the field (Databricks Apps)

One platform means one security model, one set of definitions and one audit trail — not six integrations to maintain.

---

## 9. Built for trust

- **Your systems of record stay the systems of record.** The Control Tower reads from them and never writes back.
- **People decide.** Agents never approve a change order, submit a log or declare an area safe.
- **Every answer shows its work.** Document, page and section for contract answers; the query for every number.
- **Each person sees only their projects** — the same rule applies in dashboards, in Q&A and in the agents.
- **Every agent run is recorded** step by step, so a decision can be traced back to the evidence behind it.

---

## 10. A 6-week path to value

| Weeks | What happens | What you get |
|---|---|---|
| 1–2 | Pick 3–5 active projects. Connect extracts from project management, ERP and scheduling. Agree the risk signals and weights. | Baseline for RFI aging, pending change-order exposure, projected vs. bid margin |
| 3–4 | Risk Radar and Margin Watch live on your data. Load contracts and specs for one project. | Weekly risk review run from the Control Tower |
| 5–6 | Project Resolve on live change orders. Jobsite lookahead with one superintendent. | Measured change in review cycle time and notice compliance |

**Success measures to agree up front:** days of earlier warning on margin fade · change-order review cycle time · share of change orders checked against notice and contract rates · RFIs aging more than 21 days on critical-path work.

**What we need from you:** an executive sponsor, a project-controls lead, read access to three source extracts, and one project's contract documents.

---

## Sources

Industry figures
- McKinsey & Company, "Imagining construction's digital future", June 2016 — https://www.mckinsey.com/capabilities/operations/our-insights/imagining-constructions-digital-future
- FMI and PlanGrid, "Construction Disconnected", 2018 — https://pg.plangrid.com/rs/572-JSV-775/images/Construction_Disconnected.pdf
- Navigant Construction Forum, "Impact & Control of RFIs on Construction Projects", April 2013 — https://www.cmaanet.org/sites/default/files/2018-04/NCF%20IMPACT%20%26%20CONTROL%20OF%20RFIs%20ON%20CONSTRUCTION%20PROJECTS.pdf
- Arcadis, "14th Annual Construction Disputes Report", 2024 — https://media.arcadis.com/-/media/project/arcadiscom/com/expertise/global/contract-solutions/14th-annual-construction-disputes-report-2024.pdf
- US Bureau of Labor Statistics, "National Census of Fatal Occupational Injuries in 2023", December 2024 — https://www.bls.gov/news.release/archives/cfoi_12192024.htm

Prototype figures
- All project, cost, schedule, change-order, safety and document data is synthetic. Measured results come from the run evidence in the project repository (`evidence/`).

Platform
- Lakeflow Spark Declarative Pipelines — https://docs.databricks.com/aws/en/ldp/
- Unity Catalog row filters — https://docs.databricks.com/aws/en/data-governance/unity-catalog/filters-and-masks/
- Unity Catalog metric views — https://docs.databricks.com/aws/en/metric-views/
- Lakebase — https://docs.databricks.com/aws/en/oltp/
- Databricks Apps — https://docs.databricks.com/aws/en/dev-tools/databricks-apps/
