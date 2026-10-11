"""Command-line entry point for the complete local vertical slice."""

import argparse
import json
import sys
from pathlib import Path

from .embeddings import Encoder
from .indexing import build_index
from .retrieval import PRINCIPALS, SearchEngine
from .segmentation import SegmentConfig


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    ingest = sub.add_parser("ingest")
    ingest.add_argument("--corpus", type=Path, default=Path("data/sample/recordings.json"))
    ingest.add_argument("--index", type=Path, default=Path("indexes/demo.json"))
    ingest.add_argument("--config", type=Path, default=Path("configs/segmentation.json"))
    query = sub.add_parser("search")
    query.add_argument("query")
    query.add_argument("--index", type=Path, default=Path("indexes/demo.json"))
    query.add_argument("--principal", choices=list(PRINCIPALS), default="producer")
    query.add_argument("--mode", choices=["hybrid", "lexical", "semantic"], default="hybrid")
    query.add_argument("--version", default=None)
    query.add_argument("--limit", type=int, default=5)
    sub.add_parser("download-model")
    args = parser.parse_args()
    try:
        encoder = Encoder()
        if args.command == "download-model":
            output = {"status": "model_ready"}
        elif args.command == "ingest":
            config = SegmentConfig.model_validate_json(args.config.read_text())
            output = build_index(args.corpus, args.index, encoder, config)
        else:
            output = (
                SearchEngine(args.index, encoder)
                .search(
                    args.query,
                    principal=args.principal,
                    mode=args.mode,
                    recording_version_id=args.version,
                    limit=args.limit,
                )
                .model_dump()
            )
        print(json.dumps(output, ensure_ascii=False, indent=2))
    except (ValueError, OSError, PermissionError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
