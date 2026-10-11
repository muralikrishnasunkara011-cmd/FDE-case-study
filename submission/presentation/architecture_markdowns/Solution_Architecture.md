# Find the Moment: NHA solution architecture

## Customer outcome and custody boundary

A broadcaster producer, government user or approved third party describes a remembered moment and receives a passage tied to one recording version and its source words. Discovery must save manual listening time while preserving the archivist's authority over identity, rights and official delivery. The case study states that all media is digitised but authoritative storage remains on physical media. S3 therefore stores approved processing/access copies and derived artefacts, not an assumed replacement preservation master.

The supplied case study identifies *We Shall Fight on the Beaches*, 4 June 1940. That historical identification does not prove that a particular recording captures the original performance. Our sample versions are explicitly synthetic, with separate 120-second and 18-second quotation offsets. No authentic audio or NHA integration is claimed.

## Scope and deployment map

| Capability | Running implementation | Proposed production replacement |
|---|---|---|
| Intake | Validated JSON recording/transcript snapshot | Catalogue registration, S3 checksum validation, SQS intake |
| Processing | Deterministic synchronous Python pipeline | Dispatcher plus Step Functions Standard workflow |
| Media and ASR | Synthetic timed word fixtures | Fargate/FFmpeg derivatives, Transcribe batch jobs |
| Segmentation | Word-boundary windows, configurable overlap, gap/language boundaries | Same pure segmentation logic in worker |
| Semantic representation | Pinned local MiniLM, CPU, 384 dimensions | Approved Bedrock embedding model after relevance/residency evaluation |
| Search | BM25 plus exact cosine on permitted local documents, RRF | Atlas Search and Atlas Vector Search on AWS, equivalent filters |
| Publication | Validated full snapshot with atomic replace | Staged revision, search visibility validation, active revision switch |
| Query | CLI, local FastAPI, fixed producer identity | API Gateway, Lambda, Cognito/NHA IdP and current policy service |
| Delivery | Transcript result and labelled possible simulated offline action | Reauthorised preview, asynchronous export, archive ticket integration |
| Security/operations | Fail-closed demo rights, validation and reproducible tests | IAM, KMS, Secrets Manager, private connectivity, CloudWatch, CloudTrail |

## Processing flow

1. NHA approves processing eligibility and validates stable custody, asset and recording IDs. Unknown rights enter reconciliation, not public access.
2. Register a source checksum and immutable version. Place references on SQS. A dispatcher starts a Step Functions workflow using a version/checksum/pipeline idempotency key.
3. Fargate inspects audio/video, retains originals, and records any timebase transformations. A constant offset is valid only when playback rate and continuity are unchanged. Edits and speed changes require explicit reviewed mapping.
4. Transcribe produces timed hypotheses. Preserve raw response and job settings. Existing text remains untimed until validated alignment. Review damaged audio and unsupported languages.
5. Normalise words, validate order and coverage, and generate deterministic segments. Current local windows target 30 seconds, cap at 60 and overlap by about 5 seconds. Short evidence regions remain short rather than acquiring fabricated context. Single-stream overlapping words are rejected; diarised overlapping speech requires a future multi-track contract.
6. Generate embeddings from original passage text. Optional enrichment stays in a separate derived collection with evidence and reviewer state. It cannot overwrite catalogue facts or timing.
7. Stage records/vectors under a revision, validate counts, dimensions, evidence and search visibility, then publish. Preserve the prior generation for recovery.

## Interactive retrieval

Identity resolution yields current permitted collections, snippet permissions and action permissions. Apply mandatory policy and publication filters to each lexical and vector branch. In the local engine even BM25 statistics are computed only over permitted records. Neither title nor generated summary participates in local semantic embeddings.

Retrieve up to 50 candidates per branch. BM25 uses k1=1.5, b=.75. Cosine candidates require similarity ≥0.28, a development heuristic rather than calibrated confidence. RRF sums `1 / (60 + rank)` for each branch containing the candidate. Deterministic segment IDs break ties. Greedy grouping suppresses overlapping windows only within the same recording version. It retains the best original interval, rather than constructing unsupported unions. Return up to five passages by default.

An explicit quotation, or a whole-query contiguous phrase, resolves through source tokens to first/last word offsets. Vague semantic descriptions return the source window. The local resolver deliberately does not narrow an imprecise query based on a short incidental substring. Every result reports resolution, source kind, transcript revision, word IDs and quality flags. Result scores are not probabilities.

The semantic threshold can suppress useful weak matches, and any lexical match may admit an irrelevant result. This is a known precision/no-answer tradeoff, not reliable universal abstention. The small judged fixture set exercises negative queries but cannot calibrate a production threshold.

## Data contracts and publication

`models.py` defines strict identifiers, integer millisecond timing, valid rights/availability enums and explicit source provenance. Distinguish `event_id`, `asset_id`, `recording_version_id`, `transcript_revision_id` and `segment_id`. Each word belongs to one declared coverage interval. Coverage intervals are ordered and non-overlapping and cannot exceed recording duration. Untimed notes survive ingestion but do not participate in passage retrieval.

One active transcript per version is allowed in a snapshot. Re-ingesting identical evidence/config/model returns unchanged without recomputing embeddings. Changing a transcript uses a new transcript revision. Source words, segmentation config, model ID/revision and full catalogue snapshot contribute to the input hash. Segments include a content/config-derived deterministic ID. New vectors must be finite, normalised and dimension-compatible. Publication validates source-derived segments before atomic rename. Files are trusted local operator artefacts; hashing is an integrity check, not a signed security boundary.

Local full-snapshot ingestion removes records omitted from the new input. It is not an incremental append API. Single-writer operation is assumed. An already-running API holds its loaded snapshot until restart; local policy and corpus changes require restart. Production must use live entitlements, policy-versioned caches and controlled active generations.

## Security and sovereignty

The API serves a fixed producer demo identity, cannot accept arbitrary role claims, and must bind to loopback. The CLI's archivist role is a test harness, not authentication. Unknown rights are denied to every identity. Approved and restricted rights are a deliberately simplified policy, not NHA's actual permissions model. Searchable excerpts themselves require protection.

Production must distinguish discover, metadata, transcript, preview, request, export and curate permissions. Recheck policy at response and delivery time. Do not expose internal S3 paths. Generate short-lived permitted links only after confirming version/timing, revocation behaviour and export rights. Sensitive collections may require separate indexes/accounts instead of shared filtering. Test caches, snippets, exported files and expired/reused links as release gates.

NHA must approve the Region, model endpoints, Atlas hosting/backups/support arrangements, logs and transfer paths. Regional hosting alone is not proof of sovereignty. Disable unapproved cross-region inference/replication. Use least-privilege task roles, customer-approved key policy, secret rotation and private networking where supported. No compliance certification is claimed.

## Ownership and operations

| Owner | Responsibility | Signals / recovery |
|---|---|---|
| Archive lead | Identity, source corrections, provenance | Reconcile conflicts; signed review decision with revision |
| Rights/security owner | Processing eligibility, entitlements, residency | Any leak blocks rollout; revoke and investigate |
| Archive operations | Physical custody and delivery SLA | Queue age and retrieval status, timeline verification of retrieved master |
| NHA application owner | Search configuration and release decisions | Recall by cohort, negative errors, p95, deploy/rollback |
| Platform/service team | Queues, compute, secrets, backup | Failed jobs, throttling, restore drills, cost ceilings |

Local runbook: preserve source fixtures and config; rebuild into a different index path; run tests/evaluation; verify versions and counts; archive the previous JSON; replace the configured index and restart the API. Roll back by selecting the previous JSON and restarting. Never repair an index by manually editing vectors or offsets. Invalid records need source correction and a new revision. There is no automatic backup or multi-writer coordination in the PoC.

Production failures: retry only transient service errors with bounded backoff; quarantine invalid media/rights; send terminal intake failures to a DLQ. Optional enrichment failure need not block timed transcript retrieval. Model change requires a new compatible index and side-by-side evaluation. Budget/quota exhaustion pauses low-priority backfill. Alert on queue age, incomplete coverage, publication mismatch, model errors, policy failures and operational latency. Logs should favour IDs and decisions over raw transcript/query text.

## Rollout and economics

Phase 0: validate custody identifiers, rights, regional processing and success measures with NHA. Phase 1: rights-cleared English pilot, proposed 100 recordings/50 hours, with real degraded audio and independent source timing judgements. These are blueprint planning assumptions, not supplied inventory. Phase 2: integrate identity, Atlas and physical retrieval with restore and revocation drills. Phase 3: broaden languages and collections only after per-cohort quality and cost acceptance.

Measure one-time backfill separately from steady state. Backfill cost = media hours × preparation/ASR rate + embedding/enrichment usage + storage/search provisioning + review effort. Recurring cost includes new ingestion, storage, Atlas/search capacity, API/inference, exports/egress, monitoring and staff. No price estimate is defensible without workload, Region, retention, concurrency and procurement details. Cost per indexed hour and per 1,000 searches support NHA budget cycles. Archivist handling time and producer time-to-usable-excerpt are customer outcome measures.

## References

The three supplied documents are the requirements baseline; external sources validate service capabilities only. [Transcribe timed output](https://docs.aws.amazon.com/transcribe/latest/dg/how-input.html), [MongoDB hybrid search](https://www.mongodb.com/docs/vector-search/hybrid-search/hybrid-search-overview/), [MongoDB vector prefilters](https://www.mongodb.com/docs/vector-search/), [SentenceTransformer encoding API](https://sbert.net/docs/package_reference/sentence_transformer/model.html). Accessed 11 October 2026. Final model/Region availability requires deployment-time verification.
