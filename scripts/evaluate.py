"""Ground-truth coverage of the parsed sample, plus a TF-IDF retrieval baseline."""
import json, sys, collections, statistics
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

index_path, sample_path = Path(sys.argv[1]), Path(sys.argv[2])
rows = [json.loads(l) for l in index_path.open(encoding="utf-8")]
idx = {r["k_number"]: r for r in rows}
S = [json.loads(l) for l in sample_path.open(encoding="utf-8")]
n = len(S)
def pct(x, d=None): d = d or n; return f"{x}/{d} = {100*x/d:.1f}%"

st = collections.Counter(d["status"] for d in S)
print("sample", n, "status", dict(st))
ok = [d for d in S if d["status"] == "ok"]
scanned = [d for d in ok if d["n_chars"] < 1500]
print("text extractable:", pct(len(ok)), "| of those near-empty (scanned?):", len(scanned))
any_cited = [d for d in ok if d["cited"]]
print("cites >=1 other K/P/DEN number:", pct(len(any_cited)))
pred = [d for d in ok if d["predicate_ctx"]]
print("has >=1 K number near the word 'predicate':", pct(len(pred)))
print("count of predicate-context K numbers:", collections.Counter(min(len(d["predicate_ctx"]), 5) for d in pred))
# ground-truth quality
gt_pairs = [(d, c) for d in pred for c in d["predicate_ctx"] if c.startswith("K")]
in_index = [(d, c) for d, c in gt_pairs if c in idx]
print("predicate K numbers found in openFDA index:", pct(len(in_index), len(gt_pairs)))
earlier = [(d, c) for d, c in in_index if idx[c]["decision_date"] < d["decision_date"]]
print("  ...and cleared before the citing device:", pct(len(earlier), len(in_index)))
same_pc = [(d, c) for d, c in in_index if idx[c]["product_code"] == d["product_code"]]
print("  ...same product code as citing device:", pct(len(same_pc), len(in_index)))
same_app = [(d, c) for d, c in in_index if idx[c]["applicant"].lower() == d["applicant"].lower()]
print("  ...same applicant (self-predicate):", pct(len(same_app), len(in_index)))

# retrieval baseline: candidates = everything cleared before the query device
def doc(r): return f"{r['device_name']} {r['generic_name']} {r['applicant']} {r['product_code']}"
queries = [d for d in pred if any(c in idx and idx[c]["decision_date"] < d["decision_date"] for c in d["predicate_ctx"])]
print("\nqueries with >=1 usable ground truth:", len(queries))
corpus_rows = [r for r in rows if r["decision_date"] < "2026-01-01"]
vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
X = vec.fit_transform(doc(r) for r in corpus_rows)
knums = [r["k_number"] for r in corpus_rows]
dates = [r["decision_date"] for r in corpus_rows]
pcs = [r["product_code"] for r in corpus_rows]
import numpy as np
dates = np.array(dates); pcs = np.array(pcs); knums = np.array(knums)
def run(filter_pc):
    hits = {1: 0, 5: 0, 10: 0, 50: 0}; pool_sizes = []
    for d in queries:
        truth = {c for c in d["predicate_ctx"] if c in idx and idx[c]["decision_date"] < d["decision_date"]}
        q = vec.transform([doc(d)])
        mask = (dates < d["decision_date"]) & (knums != d["k_number"])
        if filter_pc: mask &= pcs == d["product_code"]
        pool_sizes.append(int(mask.sum()))
        sims = linear_kernel(q, X).ravel(); sims[~mask] = -1
        order = np.argsort(-sims)[:50]; ranked = knums[order]
        for k in hits:
            if truth & set(ranked[:k]): hits[k] += 1
    print(f"  filter_by_product_code={filter_pc}: median candidate pool {int(statistics.median(pool_sizes))}; " +
          ", ".join(f"hit@{k} {100*v/len(queries):.1f}%" for k, v in hits.items()))
print("TF-IDF baseline over device_name+generic_name+applicant (any cited predicate in top-k):")
run(False); run(True)
# oracle check: is the true predicate even in the same-product-code pool?
inpool = sum(1 for d in queries if any(c in idx and idx[c]["product_code"] == d["product_code"] and idx[c]["decision_date"] < d["decision_date"] for c in d["predicate_ctx"]))
print("  ceiling for product-code filter (truth inside pool):", pct(inpool, len(queries)))
print("\nexamples:")
for d in pred[:6]:
    print(f"- {d['k_number']} {d['device_name'][:50]!r} pc={d['product_code']} pred={d['predicate_ctx']} ref={d['reference_ctx']} | {d['predicate_snippet'][:140]!r}")
