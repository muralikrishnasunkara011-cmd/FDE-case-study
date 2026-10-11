"""Validated full-snapshot ingestion with atomic publication and model provenance."""

import hashlib
import json
import os
import tempfile
from pathlib import Path

import numpy as np

from .embeddings import DIMENSIONS, MODEL, REVISION, Encoder
from .models import Recording, Segment
from .segmentation import SegmentConfig, segment_recording


def read_corpus(path: Path) -> list[Recording]:
    records = [Recording.model_validate(r) for r in json.loads(path.read_text())]
    if not records:
        raise ValueError("empty corpus")
    versions = [r.recording_version_id for r in records]
    if len(versions) != len(set(versions)):
        raise ValueError("one active transcript per recording version; duplicate version")
    revisions = [r.transcript_revision_id for r in records]
    if len(revisions) != len(set(revisions)):
        raise ValueError("transcript revision identifiers must be globally unique")
    return records


def index_input_hash(records: list[Recording], config: SegmentConfig) -> str:
    payload = {
        "records": [r.model_dump() for r in records],
        "config": config.model_dump(),
        "model": MODEL,
        "revision": REVISION,
        "pipeline": "index-v1",
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def build_index(
    corpus: Path, destination: Path, encoder: Encoder, config: SegmentConfig | None = None
) -> dict:
    config = config or SegmentConfig()
    records = read_corpus(corpus)
    digest = index_input_hash(records, config)
    if destination.exists():
        previous = load_index(destination)
        old_records = {r["recording_version_id"]: r for r in previous["records"]}
        for record in records:
            old = old_records.get(record.recording_version_id)
            if old:
                if any(
                    old[field] != getattr(record, field)
                    for field in ("asset_id", "event_id", "duration_ms")
                ):
                    raise ValueError("recording identity/timeline changed; use a new version")
                if old["transcript_revision_id"] == record.transcript_revision_id and (
                    old["words"] != [w.model_dump() for w in record.words]
                    or old["coverage"] != [c.model_dump() for c in record.coverage]
                    or old["untimed_text"] != record.untimed_text
                ):
                    raise ValueError("changed transcript evidence requires a new revision")
        if previous["input_sha256"] == digest:
            return {
                "status": "unchanged",
                "segments": len(previous["segments"]),
                "input_sha256": digest,
            }
    segments = [s for r in records for s in segment_recording(r, config)]
    if not segments:
        raise ValueError("no timed segments available; untimed evidence requires alignment")
    # Encode passage text only, so semantic evidence is not supplied by catalogue titles.
    vectors = encoder.encode([s.text for s in segments])
    snapshot = {
        "schema_version": "1",
        "model": MODEL,
        "model_revision": REVISION,
        "dimensions": DIMENSIONS,
        "input_sha256": digest,
        "config": config.model_dump(),
        "records": [r.model_dump() for r in records],
        "segments": [s.model_dump() for s in segments],
        "vectors": vectors.tolist(),
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, staged = tempfile.mkstemp(dir=destination.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(snapshot, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        load_index(Path(staged))  # verify before replacing the active generation
        os.replace(staged, destination)
    finally:
        Path(staged).unlink(missing_ok=True)
    return {
        "status": "published",
        "recordings": len(records),
        "segments": len(segments),
        "input_sha256": digest,
    }


def load_index(path: Path) -> dict:
    data = json.loads(path.read_text())
    if (data["schema_version"], data["model"], data["model_revision"], data["dimensions"]) != (
        "1",
        MODEL,
        REVISION,
        DIMENSIONS,
    ):
        raise ValueError("incompatible index or embedding model; rebuild")
    records = [Recording.model_validate(r) for r in data["records"]]
    config = SegmentConfig.model_validate(data["config"])
    if data["input_sha256"] != index_input_hash(records, config):
        raise ValueError("source snapshot integrity mismatch")
    expected = [s.model_dump() for r in records for s in segment_recording(r, config)]
    if expected != [Segment.model_validate(s).model_dump() for s in data["segments"]]:
        raise ValueError("segment evidence mismatch")
    vectors = np.asarray(data["vectors"], dtype=np.float32)
    if vectors.shape != (len(expected), DIMENSIONS) or not np.isfinite(vectors).all():
        raise ValueError("invalid embedding matrix")
    if not np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=0.001):
        raise ValueError("embedding vectors must be normalised")
    return data
