# Find the Moment submission

The working local implementation retrieves source-grounded archival transcript passages using genuine pretrained semantic embeddings, BM25 and Reciprocal Rank Fusion. It preserves recording and transcript identity, validates timing/coverage, enforces test entitlements and distinguishes exact phrase resolution from a broader source window.

## Main deliverables

- [Editable customer presentation](presentation/Find_the_Moment_FDE_Presentation.pptx) and [presenter notes](presentation/Presenter_Notes.md).
- [Runnable repository guide](../README.md), Python application in `src/find_the_moment`, tests, fixtures and pinned dependencies.
- [Architecture](architecture/Solution_Architecture.md), [diagrams](architecture/Architecture_Diagrams.md), [decisions and messy-data matrix](architecture/Technical_Decisions.md).
- [Measured evaluation](evaluation/Evaluation_Results.md), [test evidence](evaluation/Test_Evidence.md), raw outputs and [requirements traceability](../docs/Requirements_Traceability.md).

## Verified outcomes

46 tests passed with zero failures in both the working environment and a separate clean source/environment. The 24-slide editable deck includes notes and a 41-minute agenda. The nine-record, 12-segment synthetic corpus supports 10 positive and four negative/access development queries. Hybrid recording and passage Recall@5 are 100%, MRR@5 is 0.90 and all four judged negative/access cases return no match. Lexical passage recall is 80%; semantic MRR is 0.95, better than hybrid here. These are development fixture measurements, not production targets achieved.

The boundary measure across every returned interval in judged versions is 85.7% within ±2 seconds over 14 synthetic boundaries. An extra English window for a French query causes errors. No acoustic accuracy is measured. Exact quotation results preserve independent edited/full offsets.

## Scope and submission status

All recordings, custody references and clocks are synthetic. No audio, ASR, playback/export, real archive request, cloud deployment or production authentication is claimed. The local API uses a fixed producer identity; CLI roles are test contexts. AWS and MongoDB Atlas remain the proposed production architecture. Multilingual semantics require separate evaluation.

The repository is initialised locally but **not published**. GitHub has no authenticated session, and the supplied HR contact is a placeholder. See [publication steps](../docs/GitHub_Submission.md) and the [checklist](SUBMISSION_CHECKLIST.md). The local code and presentation are ready for review; external access and presenter rehearsal remain.
