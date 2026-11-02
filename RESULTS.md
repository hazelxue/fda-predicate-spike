# Predicate retrieval spike on openFDA 510(k) data

Date: 2026-11-02. One evening, public data only. Goal: check whether a predicate-retrieval
benchmark can be built from FDA clearance history with the cited predicate as ground truth.

## Data

- openFDA bulk export `device/510k` (export date 2026-10-30): 176,466 clearances, 1976 to 2026.
- Fields per clearance: K number, device name, applicant, decision date, product code,
  regulation number, generic name, and whether a 510(k) Summary or a Statement was filed.
- The predicate is **not** a field. It lives in the 510(k) Summary PDF
  (`accessdata.fda.gov/cdrh_docs/pdfYY/KYYxxxx.pdf`).
- 2020 to 2026: about 94% of clearances filed a Summary (Statements have no public summary).

## Sample

400 random clearances with a Summary, decision dates 2022 to 2025. PDFs downloaded and parsed
with pypdf; K/P/DEN numbers extracted by regex; a number counts as a predicate candidate if the
word "predicate" occurs within 400 characters before it.

| step | result |
|---|---|
| PDF available | 394 / 400 (98.5%); 6 returned 404 |
| text extractable (no OCR needed) | 394 / 394; none looked scanned |
| cites at least one other K/P/DEN number | 374 / 400 (93.5%) |
| has a K number in "predicate" context | 371 / 400 (92.8%) |
| predicate K numbers that exist in the openFDA index | 778 / 785 (99.1%) |
| ...cleared before the citing device | 777 / 778 |
| ...same product code as the citing device | 601 / 778 (77.2%) |
| ...same applicant (company cites its own earlier device) | 284 / 778 (36.5%) |

Number of predicate-context K numbers per summary: 1 (193), 2 (97), 3 (34), 4 (16), 5+ (31).

## Baseline retrieval

Query = device name + generic name + applicant + product code of the new device.
Corpus = every clearance decided before the query device. TF-IDF (1-2 grams), cosine.
A query is a hit if any of its cited predicates is in the top k. 369 queries.

| candidate pool | median pool size | hit@1 | hit@5 | hit@10 | hit@50 |
|---|---|---|---|---|---|
| all earlier clearances | 166,927 | 40.7% | 60.4% | 66.4% | 78.9% |
| same product code only | 192 | 37.4% | 57.7% | 65.0% | 76.7% |

Ceiling for the product-code filter: the true predicate is inside the same-product-code pool for
94.6% of queries, so the filter is a cheap, nearly lossless first stage.

## What this says

1. Ground truth is cheap: roughly 9 in 10 recent clearances yield at least one cited predicate
   from the public summary with regex alone, and almost every cited number resolves to a record.
2. A metadata-only lexical baseline already gets the predicate into the top 10 two thirds of the
   time. The remaining third is where embeddings over the summary text, hybrid retrieval and
   reranking should earn their keep, and where the evaluation has to be careful.
3. The benchmark needs a few design decisions before it is trustworthy:
   - predicate vs. reference device: the regex context heuristic does not separate them; the
     summary's "Predicate Device(s)" table does, and should be parsed properly;
   - multi-predicate submissions (about half): decide whether the metric is any-hit, all-hit,
     or recall over the predicate set;
   - self-predicates (36%): applicant name alone is a strong shortcut, so report results with
     and without the applicant field, or hold out by applicant;
   - temporal split: only clearances before the query's decision date are candidates
     (already enforced here), and the test split should be by year to avoid leakage.

## Reproduce

```
python scripts/build_index.py <bulk.zip> index.jsonl
python scripts/fetch_parse.py index.jsonl <pdf_dir> sample.jsonl 400
python scripts/evaluate.py index.jsonl sample.jsonl
```
Bulk file, PDFs and intermediate files are kept outside the repository.
