# Find the Moment

A local, runnable proof of concept for NHA: describe a vaguely remembered spoken moment and retrieve a source-grounded passage in a **specific recording version**, with word-derived timestamps and access/availability information.

**All sample recordings, custody references and clocks are synthetic. No audio is included.** The short Churchill quotation and historical identification come from the supplied assessment. This repository does not claim an authentic recording, AWS deployment, NHA integration or production authentication. See [dataset provenance](data/PROVENANCE.md).

## Quick start

Use Python **3.12** (the tested version is 3.12.2). Allow roughly 1 GB for Python dependencies and model/cache space. Initial dependency/model installation needs internet access. No cloud account or API key is required.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock.txt
python -m pip install --no-deps -e .
ftm download-model
ftm ingest
ftm search "we shall never surrender"
```

`requirements.lock.txt` pins the full dependency set exercised on macOS ARM64/Python 3.12. CPU execution is selected explicitly. Other supported platforms need their own clean-install verification. For normal dependency resolution instead of the exact tested set, use `python -m pip install -e '.[dev]'`.

After the model download, the complete demo runs without external APIs:

```bash
export HF_HUB_OFFLINE=1
export TOKENIZERS_PARALLELISM=false
ftm ingest  # unchanged input reuses the index without recomputing vectors
ftm search "I'm looking for that Churchill speech where he talks about fighting everywhere… I think it's during the war, maybe after a retreat? He says something like they'll never surrender."
ftm search "Refusing to capitulate despite an invasion across every part of our homeland" --mode semantic
ftm search "we shall never surrender" --version churchill-edit
ftm search "steam locomotive"
ftm search "Marigold"
ftm search "Marigold" --principal archivist
ftm search "quantum superconducting qubits"
```

The `archivist` CLI flag is a **test entitlement context**, not authentication. Unknown rights are denied to both demo principals. The API serves only a fixed producer identity and rejects role fields.

## What the demo returns

The first captured result for the supplied Churchill query is abridged below. [Full output](submission/evaluation/demo-churchill.json) includes transcript/word IDs, source reference and quality flags.

```json
{
  "title": "We Shall Fight on the Beaches — synthetic edited fixture",
  "event_date": "1940-06-04",
  "asset_id": "asset-churchill",
  "recording_version_id": "churchill-edit",
  "start_ms": 18000,
  "end_ms": 39350,
  "evidence_status": "synthetic_fixture",
  "resolution": "source_window",
  "availability_state": "offline",
  "permitted_actions": ["read_transcript", "simulate_retrieval_request"]
}
```

The imprecise request returns the source passage ending in “we shall never surrender.” Exact phrase search narrows that phrase to **36.850–39.350 s** in the edited fixture and **138.850–141.350 s** in the full fixture. These offsets come from each fixture's words and cannot be used with real media. Broader semantic matches do not promise exact clip boundaries. Offline action text does not submit a ticket.

## Architecture and scope

The local vertical slice is JSON intake → Pydantic validation → deterministic word windows → persisted MiniLM vectors → access-filtered BM25/cosine → Reciprocal Rank Fusion → source-word result. Windows target 30 seconds, cap at 60 seconds and overlap by about 5 seconds where evidence permits. Gaps and language changes split windows. Short evidence regions remain short.

| Implemented | Demonstrated using fixtures | Proposed only |
|---|---|---|
| Versioned contracts, timing validation and deterministic IDs | Timed transcripts and poor-quality flags | Audio preparation, ASR and acoustic alignment |
| BM25, real pretrained semantic embeddings, RRF | Fixed producer/archivist policy | Federated identity and full NHA rights model |
| Phrase resolution and labelled source windows | Separate edited clocks and offline availability | Playback, export and physical retrieval integration |
| Atomic full-snapshot publication, idempotency, tests | Mixed-language preservation and French lexical lookup | General multilingual retrieval, enrichment, AWS/Atlas deployment |

Production remains AWS-first with S3, SQS, Step Functions, Fargate/FFmpeg, Transcribe, Bedrock, API Gateway/Lambda and NHA identity integration. **MongoDB Atlas on AWS remains the preferred proposed search platform.** The local backend serves reproducibility, not evidence of Atlas performance. See [architecture](submission/architecture/Solution_Architecture.md), [diagrams](submission/architecture/Architecture_Diagrams.md) and [tradeoffs / all six messy-data conditions](submission/architecture/Technical_Decisions.md).

## Configuration and input contracts

`configs/segmentation.json` contains target, maximum, overlap and gap milliseconds. The CLI accepts `--corpus`, `--index` and `--config` for ingestion, and `--mode`, `--principal`, `--version` and `--limit` for search. `.env.example` documents optional environment variables; it is not automatically loaded.

`data/sample/recordings.json` contains nine recording records. Required fields include event, asset, version and transcript IDs, title, custody reference, rights, availability, duration, source kind and word evidence. Source metadata can retain conflicting values with provenance. Every timed word must fit a declared ordered coverage interval. Untimed text survives intake but is excluded from timed search. Single-stream overlapping word timings are rejected. No real media timing is manufactured by the application. `scripts/make_fixtures.py` is explicitly a synthetic test-data generator.

Ingestion is a **complete snapshot replacement**, not append. Omitted recordings disappear on a successful replacement. Duplicate version IDs are rejected. Transcript changes require a new revision; changing an existing recording identity/duration requires a new recording version. Identical inputs/config/model are reused. A staged JSON snapshot is validated before atomic replacement; failed processing leaves the previous index intact. Only one writer is supported. Treat index files as trusted local operator artefacts. Preserve a prior file separately for rollback.

Model: `sentence-transformers/all-MiniLM-L6-v2`, immutable revision `c9745ed1d9f207416be6d2e6f8de32d1f16199bf`, normalised 384-dimensional vectors. The encoder refuses silent token truncation. Model changes need re-embedding. Passage text alone enters local embeddings; catalogue titles and generated summaries do not supply semantic hints.

BM25 uses k1=1.5 and b=.75. Cosine candidates use a 0.28 development cutoff. RRF sums `1 / (60 + rank)` over up to 50 candidates per branch. Results suppress overlapping windows within the same recording version. Scores are not probabilities. Stopwords and thresholds are English-oriented heuristics. Weak lexical overlap can produce false positives, and the cosine threshold can miss real passages.

## API

```bash
export FTM_INDEX=indexes/demo.json
uvicorn find_the_moment.api:app --host 127.0.0.1 --port 8000
# In another terminal:
curl -s http://127.0.0.1:8000/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"we shall never surrender","limit":5}'
```

Open `http://127.0.0.1:8000/docs` for the local API explorer. `GET /health` states the demo identity and missing media. Keep it on loopback. It is not safe to expose as a production authenticated service. The API loads an index at startup; restart after corpus/policy changes. There are no search-response caches or media URLs.

## Tests and evaluation

```bash
pytest -q
ruff check src tests scripts
ruff format --check src tests scripts
mypy --no-incremental --cache-dir=/dev/null src/find_the_moment
python scripts/evaluate.py
```

The tests exercise the **real encoder**, so download/cache the pinned model first. Evaluation writes per-query outputs, timing and ablations to `submission/evaluation/results.json`. It compares lexical-only, semantic-only and hybrid search on 10 positive and 4 negative/access queries. Relevance requires a judged version and source interval. This is a small development fixture suite, not held-out customer data. [Measured results and definitions](submission/evaluation/Evaluation_Results.md) and [test evidence](submission/evaluation/Test_Evidence.md) report actual execution.

The supplied blueprint's 90% recording recall, 80% passage recall, 90% of boundaries within ±2 s and p95 ≤5 s at ten users are **proposed pilot targets**. Synthetic fixture results cannot establish acoustic accuracy, multilingual quality, archive scale or production security. Hybrid ranking does not outperform semantic-only MRR on this fixture set.

## Repository map

- `src/find_the_moment/`: contracts, segmentation, embedding wrapper, publication, retrieval, API and CLI.
- `data/`, `configs/`: reproducible fixtures, judgements, provenance and segmentation settings.
- `tests/`, `scripts/`: contract/integration tests, fixture generator and evaluation.
- `docs/Requirements_Traceability.md`: source precedence, assumptions and requirement mapping.
- `submission/`: editable presentation, presenter notes, architecture and measured evidence.

## Limitations and next build

No authentic audio, ASR, alignment, playback, clip export, live archive request, cloud deployment, production authentication or full rights policy. French lexical lookup works in one synthetic example; general multilingual semantic search is unvalidated. Full snapshots keep sources/vectors in memory and are unsuitable for archive scale. Metadata conflicts are retained, but there is no curation UI. A source interval is only as reliable as the supplied alignment. An untimed-only record is retained but is not searchable through this passage API.

Next: obtain approved real media and catalogue/custody mappings; create archivist-judged recording-family-separated holdout queries; benchmark ASR and embeddings by cohort; validate region/provider policy; integrate Atlas and identity; add reauthorised media delivery and archive requests; exercise recovery, revocation and concurrent-load gates. NHA must agree operating ownership and backfill/steady-state budgets before expansion.

## Submission

[Submission summary](submission/SUBMISSION_SUMMARY.md), [readiness checklist](submission/SUBMISSION_CHECKLIST.md), and [GitHub publication instructions](docs/GitHub_Submission.md). Input assignment documents, environments, downloaded model weights and generated local indexes are excluded from Git. No repository has been published from this environment.
