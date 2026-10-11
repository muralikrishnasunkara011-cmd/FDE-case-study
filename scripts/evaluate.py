"""Development fixture evaluation with explicit version-and-interval relevance."""

import argparse
import json
import platform
import statistics
import time
from pathlib import Path

from find_the_moment.embeddings import MODEL, REVISION, Encoder
from find_the_moment.retrieval import SearchEngine


def evaluate(engine, cases, mode):
    rows = []
    for case in cases:
        started = time.perf_counter()
        response = engine.search(
            case["query"],
            mode=mode,
            principal=case.get("principal", "producer"),
            recording_version_id=case.get("version"),
        )
        elapsed = (time.perf_counter() - started) * 1000
        expected = case["relevant"]

        def recording_ok(result):
            return any(result.recording_version_id == e["version"] for e in expected)

        def segment_ok(result):
            return any(
                result.recording_version_id == e["version"]
                and result.start_ms <= e["start_ms"]
                and result.end_ms >= e["end_ms"]
                for e in expected
            )

        ranks = [i + 1 for i, r in enumerate(response.results) if segment_ok(r)]
        errors = []
        if case.get("exact_boundaries"):
            for r in response.results:
                match = next((e for e in expected if e["version"] == r.recording_version_id), None)
                if match:
                    errors.append(
                        {
                            "version": r.recording_version_id,
                            "start_error_ms": abs(r.start_ms - match["start_ms"]),
                            "end_error_ms": abs(r.end_ms - match["end_ms"]),
                        }
                    )
        rows.append(
            {
                "id": case["id"],
                "query": case["query"],
                "positive": bool(expected),
                "recording_hit_at_5": any(recording_ok(r) for r in response.results),
                "segment_hit_at_5": bool(ranks),
                "reciprocal_rank": 1 / ranks[0] if ranks else 0,
                "negative_correct": not response.results if not expected else None,
                "latency_ms": elapsed,
                "boundary_errors": errors,
                "results": [r.model_dump() for r in response.results],
            }
        )
    positives = [r for r in rows if r["positive"]]
    negatives = [r for r in rows if not r["positive"]]
    errors = [e for r in rows for e in r["boundary_errors"]]
    latencies = sorted(r["latency_ms"] for r in rows)
    metrics = {
        "mode": mode,
        "positive_queries": len(positives),
        "negative_queries": len(negatives),
        "recording_recall_at_5": statistics.mean(r["recording_hit_at_5"] for r in positives),
        "segment_recall_at_5": statistics.mean(r["segment_hit_at_5"] for r in positives),
        "mrr_at_5": statistics.mean(r["reciprocal_rank"] for r in positives),
        "negative_accuracy": statistics.mean(r["negative_correct"] for r in negatives),
        "boundary_intervals_measured": len(errors),
        "start_mae_ms": statistics.mean(e["start_error_ms"] for e in errors) if errors else None,
        "end_mae_ms": statistics.mean(e["end_error_ms"] for e in errors) if errors else None,
        "boundary_fraction_within_2s": statistics.mean(
            error <= 2000 for e in errors for error in [e["start_error_ms"], e["end_error_ms"]]
        )
        if errors
        else None,
        "warm_sequential_p95_ms": latencies[
            max(0, __import__("math").ceil(0.95 * len(latencies)) - 1)
        ],
    }
    return {"metrics": metrics, "queries": rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, default=Path("indexes/demo.json"))
    parser.add_argument("--judgements", type=Path, default=Path("data/sample/judgements.json"))
    parser.add_argument("--output", type=Path, default=Path("submission/evaluation/results.json"))
    args = parser.parse_args()
    started = time.perf_counter()
    engine = SearchEngine(args.index, Encoder())
    engine.search("model warmup")
    cold = (time.perf_counter() - started) * 1000
    cases = json.loads(args.judgements.read_text())
    result = {
        "model": MODEL,
        "model_revision": REVISION,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "load_and_warmup_ms": cold,
        "dataset": "synthetic development fixtures; no held-out claims",
        "concurrency": 1,
        "runs": [evaluate(engine, cases, m) for m in ["lexical", "semantic", "hybrid"]],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps([r["metrics"] for r in result["runs"]], indent=2))


if __name__ == "__main__":
    main()
