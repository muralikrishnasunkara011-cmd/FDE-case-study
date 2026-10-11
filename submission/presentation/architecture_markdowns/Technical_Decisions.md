# Technical decisions and messy-data treatment

## Decision register

| Decision | Choice and reason | Alternative / decision gate |
|---|---|---|
| Local execution | MiniLM + JSON snapshot avoids cloud credentials and recurring demo costs | Atlas remains preferred production search platform |
| Production platform | AWS managed orchestration and pretrained services fit limited ML staffing | Approved local processing if sovereignty prohibits managed inference |
| Search platform | Atlas combines variable catalogue documents, text and vectors | OpenSearch + catalogue store if procurement/benchmarks favour it; pgvector if relational needs dominate |
| Ranking | BM25 + cosine + explicit RRF preserves exact and paraphrase paths | Reranker only after held-out incremental benefit justifies latency/cost |
| Timing | Deterministic source words; broader semantic intervals | No LLM timing, text-length alignment or transferred edit offsets |
| Local model | Pinned English MiniLM CPU encoder, existing cache, no training | Bedrock model needs new embeddings/dimensions and fresh evaluation |
| Multilingual | Preserve French/English words and split language windows | General multilingual retrieval needs a multilingual model and cohort evaluation |
| Delivery | Return honest actions with no fake preview URLs | Real exports need media, FFmpeg timebase verification and reauthorisation |
| Scope | No RDF, visual indexing, enrichment generation or fine-tuning | Introduce only for a measured customer query gap and an assigned owner |

These narrow the implementation without changing the AWS/Atlas proposal. The supplied blueprint has 13 numbered sections, not the 16 described in the master request. Its proposed targets remain acceptance proposals, not PoC achievements. There is no material conflict with the HR or customer requirements: HR permits timed transcript inputs.

## All six messy-data conditions

| Condition | Proposed pipeline | Implemented / simulated locally | Remaining gap and human fallback | Validation |
|---|---|---|---|---|
| Poor audio | Preserve original, compare preprocessing, Transcribe hypotheses, review confidence/timing | Synthetic low-confidence words and review flags | No audio/ASR, WER or actual denoising. Archivist reviews aligned words against source | Low-confidence result test; pilot degraded-audio WER and timing cohorts |
| Partial transcripts | Coverage intervals, gap markers, align untimed text before clip use | Disjoint coverage validated; windows stop at gaps; untimed notes preserved and excluded | No catalogue-only search path or alignment. Request transcription/review for gaps | No gap-spanning segments; untimed text never receives offsets |
| Multilingual/mixed | Language-aware ASR and a validated multilingual encoder | French original text, English/French windows, French lexical query | English semantic baseline only. Translator/archivist handles unsupported language | Language/lexical tests; pilot per-language recall and code-switch ASR |
| Duplicate/edited | File checksum duplicates, fingerprint suggestions, distinct playback timelines | Reject duplicate version IDs, idempotent snapshot, separate offsets and IDs | No audio hashing/fingerprinting or automatic equivalence. Archivist confirms relationships | Re-ingest test, edited version offset and identity tests |
| Metadata gaps/conflicts | Keep source facts and generated suggestions separate; reconcile before publishing authority | Required identity/rights rejection, null recording dates, conflicting facts retained, review flag | No enrichment or review UI. Archivist resolves under new revision | Missing fields, conflict preservation and unknown-rights tests |
| Offline delays | Search independent of availability; queue request into archive system, track SLA | Offline flag and explicitly labelled possible simulated request action | No ticket submission, queue, real media or SLA. User contacts archive operations | Offline result test; future workflow and retrieved-master timeline test |

## Production acceptance and residual risks

- A tiny synthetic corpus can produce misleading retrieval metrics. Freeze family-separated development and holdout sets with real users and archivist judgement before tuning.
- A source interval is only as accurate as its transcript alignment. Local zero error would test arithmetic, not ASR or acoustic accuracy.
- MiniLM's English model and limited context may omit multilingual or long spoken passages. The encoder refuses silent token truncation, so reduce segment windows or choose an evaluated model.
- Shared-index filtering must survive candidate, response, cache and link tests. Any confirmed leak blocks release.
- AWS and Atlas residency/procurement remain unapproved assumptions. NHA security owns the decision.
- No authentic playback/export is delivered. HR explicitly permits transcripts; production usability still requires audio validation.
