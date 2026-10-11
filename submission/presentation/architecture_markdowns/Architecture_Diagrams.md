# Architecture diagrams

These diagrams describe the proposed production architecture unless labelled local. All AWS and Atlas services are proposed, not deployed.

```mermaid
flowchart TB
  C[Authoritative physical custody / NHA catalogue] --> A[Approve processing copy and manifest]
  A --> S[S3 versioned source and evidence]
  S --> Q[SQS intake]
  Q --> L[Lambda dispatcher]
  L --> W[Step Functions Standard]
  W --> F[Fargate / FFmpeg preparation]
  F --> T[Transcribe timed words]
  T --> V[Validate coverage and segment]
  V --> B[Bedrock embeddings]
  B --> M[Atlas staged text / vectors / catalogue]
  M --> P[Validate then activate publication revision]
  T --> S
  C -. custody reference .-> M
  O[IAM / KMS / Secrets / monitoring / audit] -. approved regional boundary .-> W
```

```mermaid
sequenceDiagram
  actor U as Authorised producer
  participant API as API Gateway / Lambda
  participant ID as NHA IdP / current policy
  participant AT as Atlas Search + Vector Search
  participant R as RRF + word resolver
  participant AR as Archive operations
  U->>API: Imprecise description
  API->>ID: Authenticate and resolve current entitlements
  ID-->>API: Permitted discovery, snippets and actions
  API->>AT: Lexical + vector query with policy / publication filters
  AT-->>R: Permitted version-specific passages
  R->>R: Fuse ranks; suppress overlaps within each version
  R->>R: Exact words or broader validated interval
  R-->>API: Evidence and source interval
  API->>ID: Recheck permitted response/actions
  API-->>U: Excerpt, timing, version, quality, availability
  U->>API: Request authorised offline recording
  API->>AR: Reauthorised custody request (future integration)
```

```mermaid
flowchart LR
  E[Historical event] --> A[Archive asset]
  A --> V1[Recording version A]
  A --> V2[Edited version B]
  V1 --> T1[Transcript revision A]
  V2 --> T2[Transcript revision B]
  T1 --> W1[Words at 120 seconds: synthetic]
  T2 --> W2[Words at 18 seconds: synthetic]
  W1 --> S1[Version A segment]
  W2 --> S2[Version B segment]
```

```mermaid
flowchart LR
  J[Local JSON timed evidence] --> V[Validate]
  V --> S[Segment]
  S --> I[MiniLM + persisted JSON vectors]
  I --> Q[CLI / local FastAPI]
  Q --> H[Permitted BM25 + cosine + RRF]
  H --> R[Source-word result]
```
