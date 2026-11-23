"""Turn the (single-source) jobsite generator output into UC tables. Input: JSON from the TS generator
(frontend/src/modules/jobsite/data.ts run under Node for all projects). Run: python -I data_gen/jobsite_tables.py <jobsite.json>"""
import json, sys
from datetime import date
from pathlib import Path
import polars as pl

WHEN = {"Today": date(2026, 11, 9), "Tomorrow": date(2026, 11, 10), "Thu": date(2026, 11, 12), "Next Mon": date(2026, 11, 16)}
days = json.load(open(sys.argv[1]))
out = Path(__file__).parent / "out_jobsite"; out.mkdir(exist_ok=True)
day_rows, look, crews, events = [], [], [], []
for d in days:
    pid = d["project_id"]
    day_rows.append(dict(project_id=pid, superintendent=d["superintendent"], weather=d["weather"], phase=d["phase"],
                         near_miss_count_14d=d["nearMisses"]["count"], near_miss_theme=d["nearMisses"]["theme"], as_of=date(2026, 11, 9)))
    for i, a in enumerate(d["activities"]):
        row = dict(project_id=pid, seq=i + 1, lookahead_id=a["id"], activity=a["name"], trade=a["trade"], area=a["area"], when_label=a["when"],
                   planned_date=WHEN[a["when"]], hazard=a["hazard"], standard=a["standard"], permit=a.get("permit"), risk_level=a["level"],
                   ready=all(c["ok"] for c in a["checks"]))
        for c in a["checks"]:
            k = c["label"].lower()
            row.update({f"{k}_ok": c["ok"], f"{k}_detail": c["detail"], f"{k}_owner": c.get("owner"), f"{k}_needed_by": c.get("neededBy")})
        look.append(row)
    for c in d["crews"]:
        crews.append(dict(project_id=pid, trade=c["trade"], company=c["company"], planned=c["planned"], actual_yesterday=c["yesterday"], short_by=c["planned"] - c["yesterday"]))
    for e in d["events"]:
        events.append(dict(project_id=pid, event_date=date(2026, 11, 9), time=e["time"], kind=e["kind"], description=e["what"]))
for name, rows in (("jobsite_day", day_rows), ("jobsite_lookahead", look), ("jobsite_crews", crews), ("jobsite_events", events)):
    pl.DataFrame(rows, infer_schema_length=None).write_parquet(out / f"{name}.parquet"); print(f"{name:18s} {len(rows):>4} rows")
