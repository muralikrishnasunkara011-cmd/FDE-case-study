# Measured evaluation results

Measured locally on macOS-26.7-arm64-arm-64bit, Python 3.12.2. Model sentence-transformers/all-MiniLM-L6-v2 at revision `c9745ed1d9f207416be6d2e6f8de32d1f16199bf`.

Nine synthetic recording records produce 12 segments. One untimed-only record remains unindexed. Ten positive queries and four negative/access queries form a development fixture suite. The corpus and judgements were authored together. No holdout or independent human assessment is claimed.

| Mode | Recording Recall@5 | Segment Recall@5 | MRR@5 | Negative correct | Warm sequential p95 |
|---|---:|---:|---:|---:|---:|
| lexical | 90% | 80% | 0.75 | 100% (n=4) | 0.84 ms |
| semantic | 100% | 100% | 0.95 | 100% (n=4) | 13.12 ms |
| hybrid | 100% | 100% | 0.90 | 100% (n=4) | 11.85 ms |

## Definitions and limitations

- Recording Recall@5 is a query-level hit rate: at least one judged version appears among five returned passages. Multiple editions may be acceptable. This differs from recall over every possible relevant version.
- Segment Recall@5 requires the correct version and a returned interval containing the manually selected fixture interval. Broad windows can satisfy containment, so this does not establish exact clip precision.
- MRR@5 measures the first relevant passage. Hybrid MRR is lower than semantic-only MRR on this suite; there is no universal superiority claim.
- Negative accuracy is empty output for the four judged negative/access cases. It does not establish a general abstention classifier.
- Latency is nearest-rank p95 over 14 sequential queries after model warmup, within one process and without API/network/production authentication. With n=14, p95 is the maximum. No ten-user load test was performed.
- Model/index load plus warmup took 133.4 ms in this run. CLI process startup can add considerable overhead.

## Boundary evaluation

Hybrid and semantic modes each return seven intervals belonging to versions with exact-boundary judgements (14 boundaries). 85.7% are within ±2 seconds. Mean absolute start error is 3192.9 ms and end error 4121.4 ms. All returned intervals in a judged version count, including a wrong passage from the right recording. An additional English-language window returned for the French quotation accounts for the nonzero errors. The six exactly resolved intervals have zero boundary error against their synthetic words. This is arithmetic evidence, **not acoustic alignment accuracy**.

Lexical-only returns six measured intervals (12 boundaries), all exact. That smaller denominator reflects missed semantic candidates and must not be interpreted as an overall better retrieval system. The all-returned hybrid boundary measure is below the blueprint’s 90% proposal. No real-media timestamp target has been validated.

## Development change and residual errors

An initial cosine threshold of 0.40 rejected the no-lexical-overlap paraphrase (cosine ≈0.297), causing one test failure. Lowering the development threshold to 0.28 retrieved it while retaining the four judged no-match cases. This is tuning on development evidence. A fresh holdout is required before deployment. The vague Churchill query also returns irrelevant introduction/bridge windows below its first correct result; inspect the complete captured output rather than only the headline metric.

## Pilot targets are not achieved claims

| Blueprint proposal | Current evidence boundary |
|---|---|
| Recording Recall@5 ≥90% | Tiny synthetic development hit rate only |
| Segment Recall@5 ≥80% | Broad-window containment, no representative holdout |
| ≥90% of boundaries within ±2 seconds | 85.7% on 14 synthetic returned boundaries; no audio |
| Warm p95 ≤5 seconds at ten users | Single sequential process only |
| No unauthorised exposure | Local simplified policy tests only |

Next: archivist judgements for representative rights-cleared media, recording-family-separated development/holdout split, per-language and quality cohorts, independently validated boundaries, false-positive analysis, production authentication and ten-user load test. Proposed 100 recordings/50 hours and 60 development/40 holdout queries remain blueprint planning assumptions.

Raw evidence: [results.json](results.json), [judgements](../../data/sample/judgements.json), [captured Churchill query](demo-churchill.json). Reproduce with `python scripts/evaluate.py`.
