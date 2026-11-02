"""Slim the openFDA 510(k) bulk file into one JSON line per clearance."""
import json, sys, zipfile, collections
from pathlib import Path
src = Path(sys.argv[1]); out = Path(sys.argv[2])
with zipfile.ZipFile(src) as z:
    name = z.namelist()[0]
    with z.open(name) as f:
        data = json.load(f)
rows = data["results"]
keep = ["k_number","device_name","applicant","decision_date","date_received","product_code",
        "statement_or_summary","decision_code","decision_description","clearance_type",
        "advisory_committee","country_code","third_party_flag"]
years = collections.Counter(); sos = collections.Counter()
with out.open("w", encoding="utf-8") as w:
    for r in rows:
        d = {k: r.get(k, "") for k in keep}
        o = r.get("openfda", {}) or {}
        d["generic_name"] = o.get("device_name", "")
        d["regulation_number"] = o.get("regulation_number", "")
        d["device_class"] = o.get("device_class", "")
        w.write(json.dumps(d, ensure_ascii=False) + "\n")
        y = (d["decision_date"] or "")[:4]
        years[y] += 1
        if y >= "2020": sos[(y, d["statement_or_summary"] or "")] += 1
print("records", len(rows))
print("by year (2015+):", sorted((y, c) for y, c in years.items() if y >= "2015"))
print("statement_or_summary 2020+:", sorted(sos.items()))
