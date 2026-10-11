# Executed test evidence

- Python 3.12.2, macOS ARM64; full dependency versions in `requirements.lock.txt`.
- `HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false .venv/bin/pytest -q --junitxml=submission/evaluation/pytest.xml`: **46 passed**, zero failed, one upstream Starlette/AnyIO deprecation warning. See `test-output.txt` and `pytest.xml`.
- `.venv/bin/ruff check src tests scripts`: all checks passed (`lint-output.txt`).
- `.venv/bin/ruff format --check src tests scripts`: verified separately in final checks.
- `.venv/bin/mypy --no-incremental --cache-dir=/dev/null src/find_the_moment`: success, eight source files (`typecheck-output.txt`). NumPy/SentenceTransformers imports use skipped third-party stubs. The default cache writer exposed an upstream mypy internal serialization error; the documented no-cache invocation avoids it.
- Real model-backed CLI ingestion, exact/semantic/hybrid queries and evaluation executed. Ingestion published nine records and 12 segments. Captured outputs are `ingestion.json`, `demo-*.json` and `results.json`.
- API request/response and role-injection behaviour executed using FastAPI TestClient in integration tests.

The initial suite had one failed semantic retrieval test at a 0.40 cutoff. Development score inspection supported a 0.28 cutoff, followed by a complete passing run. No failed run is represented as passing. See the evaluation report for limitations and poorer boundary results.

Test behaviours: required and malformed fields; word ordering and bounds; disjoint coverage; segment timing/overlap/stability; edited-version separation; untimed exclusion; language/metadata preservation; duplicate versions; unchanged ingestion and vector reuse; failed publication retention; source/model corruption; phrase boundaries; semantic-only paraphrase; fusion math; rights and revocation; offline action; no-match; structured JSON; API validation and role injection. No full line-coverage percentage is claimed.

No AWS, Atlas, acoustic timing, production authentication, real delivery or GitHub CI execution has been tested. The workflow file is supplied for future CI and is not evidence of a hosted run.

## Clean-copy verification

A separate source copy under `/private/tmp/ftm-clean-source` and fresh Python environment `/private/tmp/ftm-clean-verify` installed the pinned requirements from the package cache, then installed the project as editable. It reused the pinned model cache with `HF_HUB_OFFLINE=1`; this is not a fresh network model-download test. Starting with no index, CLI ingestion published nine records/12 segments, CLI phrase search returned independent version offsets, and all 46 tests passed. The separate evaluation reproduced recording/passage recall, MRR and boundary results. Latencies vary as expected. See `clean-test-output.txt`, `clean-ingestion.json` and `clean-results.json`.

The 24-slide presentation contains 24 note parts, three native editable tables and native editable diagrams. All slides were rendered and visually inspected, including corrected arrow directions. Package/layout/import validation passed with no findings. PowerPoint-native rendering was not exercised.
