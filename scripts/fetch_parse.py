"""Sample recent 510(k) summaries, download the PDFs, extract cited K numbers."""
import json, random, re, sys, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import requests
from pypdf import PdfReader

index_path, pdf_dir, out_path, n = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), int(sys.argv[4])
rows = [json.loads(l) for l in index_path.open(encoding="utf-8")]
pool = [r for r in rows if "2022-01-01" <= r["decision_date"] <= "2025-12-31" and r["statement_or_summary"] == "Summary"]
random.seed(7)
sample = random.sample(pool, n)
KNUM = re.compile(r"\b(?:K|P|DEN|N)\d{6}\b")

def pdf_url(k):
    yy = int(k[1:3])
    return f"https://www.accessdata.fda.gov/cdrh_docs/pdf{yy or ''}/{k}.pdf"

def fetch(r):
    k = r["k_number"]; p = pdf_dir / f"{k}.pdf"
    d = dict(r); d["status"] = ""
    if not p.exists():
        for attempt in range(3):
            try:
                resp = requests.get(pdf_url(k), headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
                if resp.status_code == 200 and resp.content[:4] == b"%PDF":
                    p.write_bytes(resp.content); break
                d["status"] = f"http{resp.status_code}"
            except Exception as e:
                d["status"] = type(e).__name__
            time.sleep(2)
        else:
            return d
    try:
        reader = PdfReader(str(p))
        text = "\n".join((pg.extract_text() or "") for pg in reader.pages)
    except Exception as e:
        d["status"] = "pdf_error:" + type(e).__name__; return d
    d["n_pages"] = len(reader.pages); d["n_chars"] = len(text)
    cited = [m for m in dict.fromkeys(KNUM.findall(text)) if m != k]
    d["cited"] = cited
    low = text.lower()
    pred, ref = [], []
    for c in cited:
        for m in re.finditer(re.escape(c), text):
            ctx = low[max(0, m.start() - 400): m.end() + 150]
            if "predicate" in ctx: pred.append(c)
            if "reference device" in ctx or "reference(s)" in ctx: ref.append(c)
    d["predicate_ctx"] = list(dict.fromkeys(pred)); d["reference_ctx"] = list(dict.fromkeys(ref))
    i = low.find("predicate device")
    d["predicate_snippet"] = text[i: i + 300].replace("\n", " ") if i >= 0 else ""
    d["status"] = "ok" if text.strip() else "no_text"
    return d

with ThreadPoolExecutor(6) as ex, out_path.open("w", encoding="utf-8") as w:
    for i, d in enumerate(ex.map(fetch, sample), 1):
        w.write(json.dumps(d, ensure_ascii=False) + "\n")
        if i % 50 == 0: print(i, flush=True)
print("done", n)
