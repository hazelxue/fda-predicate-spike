# fda-predicate-spike

A one-evening check of whether a **predicate retrieval benchmark** can be built from public
FDA 510(k) data, with the predicate a device actually cited as ground truth.

Short answer: yes. In a random sample of 400 recent clearances, 93% yield a cited predicate
from the public summary PDF with regex alone, 99% of those K numbers resolve to an openFDA
record, and a metadata-only TF-IDF baseline puts a cited predicate in the top 10 for 66% of
queries. Numbers, caveats and the benchmark decisions that come next are in [RESULTS.md](RESULTS.md).

## Run it

```
pip install -r requirements.txt
curl -L -o device-510k.json.zip https://download.open.fda.gov/device/510k/device-510k-0001-of-0001.json.zip
python scripts/build_index.py device-510k.json.zip index.jsonl
python scripts/fetch_parse.py index.jsonl pdfs sample.jsonl 400
python scripts/evaluate.py index.jsonl sample.jsonl
```

`fetch_parse.py` downloads one summary PDF per sampled clearance from accessdata.fda.gov
(about 400 files, a few minutes with 6 threads). The sample is seeded, so the numbers reproduce.

## Layout

- `scripts/build_index.py`: slims the 238 MB openFDA bulk export into one JSON line per clearance.
- `scripts/fetch_parse.py`: samples clearances with a 510(k) Summary, downloads the PDFs, extracts cited K/P/DEN numbers and the ones in "predicate" context.
- `scripts/evaluate.py`: ground-truth coverage statistics and a TF-IDF retrieval baseline with a temporal cutoff.

Data source: [openFDA device/510k](https://open.fda.gov/apis/device/510k/) and FDA 510(k) summary documents. MIT license.
