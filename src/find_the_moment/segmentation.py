"""Deterministic windows whose boundaries always come from supplied words."""

import hashlib
import json

from pydantic import Field, model_validator

from .models import Contract, Recording, Segment


class SegmentConfig(Contract):
    target_ms: int = Field(default=30000, ge=1000)
    max_ms: int = Field(default=60000, ge=1000)
    overlap_ms: int = Field(default=5000, ge=0)
    gap_ms: int = Field(default=2500, ge=0)

    @model_validator(mode="after")
    def valid(self):
        if not self.overlap_ms < self.target_ms <= self.max_ms:
            raise ValueError("require overlap < target <= maximum")
        return self


def segment_recording(record: Recording, config: SegmentConfig) -> list[Segment]:
    words = record.words
    if any(w.end_ms - w.start_ms > config.max_ms for w in words):
        raise ValueError("source word exceeds maximum segment duration")
    revision = "segment-v1-" + hashlib.sha256(config.model_dump_json().encode()).hexdigest()[:12]
    output: list[Segment] = []
    i = 0
    while i < len(words):
        j = i
        while j + 1 < len(words):
            current, nxt = words[j], words[j + 1]
            # Never bridge a declared evidence gap, a large pause or a language switch.
            same_coverage = any(
                c.start_ms <= words[i].start_ms and nxt.end_ms <= c.end_ms for c in record.coverage
            )
            if (
                not same_coverage
                or nxt.start_ms - current.end_ms > config.gap_ms
                or nxt.language != current.language
                or nxt.end_ms - words[i].start_ms > config.max_ms
            ):
                break
            if current.end_ms - words[i].start_ms >= config.target_ms and current.text.endswith(
                (".", "!", "?")
            ):
                break
            j += 1
        chunk = words[i : j + 1]
        identity = [
            record.asset_id,
            record.recording_version_id,
            record.transcript_revision_id,
            revision,
            [w.model_dump() for w in chunk],
        ]
        sid = (
            "seg-" + hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:24]
        )
        output.append(
            Segment(
                asset_id=record.asset_id,
                recording_version_id=record.recording_version_id,
                transcript_revision_id=record.transcript_revision_id,
                segment_id=sid,
                start_ms=chunk[0].start_ms,
                end_ms=chunk[-1].end_ms,
                start_word_id=chunk[0].word_id,
                end_word_id=chunk[-1].word_id,
                word_ids=[w.word_id for w in chunk],
                text=" ".join(w.text for w in chunk),
                language=chunk[0].language,
                rights_class=record.rights_class,
                availability_state=record.availability_state,
                processing_version=revision,
            )
        )
        if j == len(words) - 1:
            break
        # Overlap only if continuing the same uninterrupted evidence region.
        can_overlap = (
            words[j + 1].language == words[j].language
            and words[j + 1].start_ms - words[j].end_ms <= config.gap_ms
            and any(
                c.start_ms <= words[i].start_ms and words[j + 1].end_ms <= c.end_ms
                for c in record.coverage
            )
        )
        next_i = j + 1
        if can_overlap and config.overlap_ms:
            next_i = next(
                (
                    k
                    for k in range(i + 1, j + 1)
                    if words[k].start_ms >= words[j].end_ms - config.overlap_ms
                ),
                j + 1,
            )
        i = next_i
    return output
