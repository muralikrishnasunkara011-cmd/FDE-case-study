"""Access-filtered BM25 and cosine candidates, deterministic RRF, source resolution."""

import math
import re
from collections import Counter
from pathlib import Path
from typing import Literal

import numpy as np

from .embeddings import Encoder
from .indexing import load_index
from .models import Recording, SearchResponse, SearchResult, Segment

Mode = Literal["hybrid", "lexical", "semantic"]
STOP = set(
    "a an the is are was were be been to of in on at for and or it its i im he she "
    "they we you that this with about where what how some something maybe think "
    "looking during says like them their from by as our will shall".split()
)
# Demo policy is resolved server-side. Unknown principals fail closed.
PRINCIPALS = {"producer": {"approved"}, "archivist": {"approved", "restricted"}}


def tokens(text: str) -> list[str]:
    return re.findall(r"[^\W_]+(?:['’][^\W_]+)?", text.casefold(), flags=re.UNICODE)


def lexical_tokens(text: str) -> list[str]:
    return [t for t in tokens(text) if t not in STOP]


def bm25(query: str, documents: list[str]) -> list[float]:
    """Okapi BM25, k1=1.5 b=.75, statistics computed only over permitted corpus."""
    bags = [Counter(lexical_tokens(d)) for d in documents]
    lengths = [sum(b.values()) for b in bags]
    average = sum(lengths) / max(len(bags), 1) or 1
    scores = [0.0] * len(bags)
    for term in set(lexical_tokens(query)):
        df = sum(term in bag for bag in bags)
        idf = math.log(1 + (len(bags) - df + 0.5) / (df + 0.5))
        for i, bag in enumerate(bags):
            freq = bag[term]
            scores[i] += idf * freq * 2.5 / (freq + 1.5 * (0.25 + 0.75 * lengths[i] / average))
    return scores


def rrf(branches: list[list[int]], k: int = 60) -> dict[int, float]:
    if k < 1:
        raise ValueError("RRF k must be positive")
    scores: dict[int, float] = {}
    for branch in branches:
        for rank, item in enumerate(branch, 1):
            scores[item] = scores.get(item, 0) + 1 / (k + rank)
    return scores


def phrase_words(query: str, segment: Segment, record: Recording):
    words_by_id = {w.word_id: w for w in record.words}
    words = [words_by_id[i] for i in segment.word_ids]
    # Explicitly quoted phrase, or entire query if it is a contiguous source quotation.
    quoted = re.findall(r'["“]([^"”]+)["”]', query)
    phrases = sorted(quoted or [query], key=lambda x: -len(tokens(x)))
    flattened = [(token, word) for word in words for token in tokens(word.text)]
    source = [t for t, _ in flattened]
    for phrase in phrases:
        match = tokens(phrase)
        if len(match) < 2:
            continue
        for i in range(len(source) - len(match) + 1):
            if source[i : i + len(match)] == match:
                first, last = flattened[i][1], flattened[i + len(match) - 1][1]
                return [w for w in words if first.start_ms <= w.start_ms <= last.start_ms]
    return None


class SearchEngine:
    def __init__(self, index: Path, encoder: Encoder):
        snapshot = load_index(index)
        self.encoder = encoder
        self.records = {
            r["recording_version_id"]: Recording.model_validate(r) for r in snapshot["records"]
        }
        self.segments = [Segment.model_validate(s) for s in snapshot["segments"]]
        self.vectors = np.asarray(snapshot["vectors"], dtype=np.float32)

    def search(
        self,
        query: str,
        principal: str = "producer",
        limit: int = 5,
        mode: Mode = "hybrid",
        recording_version_id: str | None = None,
        min_similarity: float = 0.28,
    ) -> SearchResponse:
        query = query.strip()
        if not query or len(query) > 1000 or not 1 <= limit <= 20:
            raise ValueError("query must be 1–1000 characters and limit 1–20")
        if principal not in PRINCIPALS:
            raise PermissionError("unknown demo principal")
        if mode not in ("hybrid", "semantic", "lexical"):
            raise ValueError("unknown retrieval mode")
        allowed = [
            i
            for i, s in enumerate(self.segments)
            if s.rights_class in PRINCIPALS[principal]
            and (recording_version_id is None or s.recording_version_id == recording_version_id)
        ]
        if not allowed:
            return SearchResponse(query=query, status="no_match", results=[])
        # Both branches receive permitted records only, before scoring/candidate truncation.
        docs = [self.segments[i].text for i in allowed]
        lex = bm25(query, docs)
        sem = (
            self.vectors[allowed] @ self.encoder.encode([query])[0]
            if mode != "lexical"
            else np.zeros(len(allowed))
        )
        branches = []
        if mode != "semantic":
            branches.append(
                [
                    allowed[i]
                    for i in sorted(
                        range(len(allowed)),
                        key=lambda i: (-lex[i], self.segments[allowed[i]].segment_id),
                    )
                    if lex[i] > 0
                ][:50]
            )
        if mode != "lexical":
            branches.append(
                [
                    allowed[i]
                    for i in sorted(
                        range(len(allowed)),
                        key=lambda i: (-sem[i], self.segments[allowed[i]].segment_id),
                    )
                    if sem[i] >= min_similarity
                ][:50]
            )
        scores = rrf(branches)
        results: list[SearchResult] = []
        selected: list[Segment] = []
        for idx in sorted(scores, key=lambda i: (-scores[i], self.segments[i].segment_id)):
            segment = self.segments[idx]
            record = self.records[segment.recording_version_id]
            if record.rights_class not in PRINCIPALS[principal]:
                continue
            # Greedy suppression retains the best original interval, never creates a union.
            if any(
                s.recording_version_id == segment.recording_version_id
                and min(s.end_ms, segment.end_ms) > max(s.start_ms, segment.start_ms)
                for s in selected
            ):
                continue
            selected.append(segment)
            matched = phrase_words(query, segment, record)
            words_by_id = {w.word_id: w for w in record.words}
            evidence = matched or [words_by_id[w] for w in segment.word_ids]
            flags = list(record.quality_flags)
            coverage = sum(c.end_ms - c.start_ms for c in record.coverage) / record.duration_ms
            if coverage < 1:
                flags.append("partial_timed_coverage")
            if segment.language != "en":
                flags.append("semantic_language_not_validated")
            if any(w.confidence is not None and w.confidence < 0.7 for w in evidence):
                flags.append("low_transcript_confidence_review")
            actions = ["read_transcript"]
            if record.availability_state == "offline":
                actions.append("simulate_retrieval_request")
            elif record.availability_state == "online":
                actions.append("media_not_in_demo")
            results.append(
                SearchResult(
                    title=record.title,
                    event_id=record.event_id,
                    event_date=record.event_date,
                    asset_id=record.asset_id,
                    recording_version_id=record.recording_version_id,
                    transcript_revision_id=record.transcript_revision_id,
                    segment_id=segment.segment_id,
                    matched_excerpt=" ".join(w.text for w in evidence),
                    start_ms=evidence[0].start_ms,
                    end_ms=evidence[-1].end_ms,
                    start_word_id=evidence[0].word_id,
                    end_word_id=evidence[-1].word_id,
                    language=segment.language,
                    evidence_status=record.source_kind,
                    resolution="exact_phrase" if matched else "source_window",
                    quality_flags=sorted(set(flags)),
                    coverage_fraction=round(coverage, 4),
                    availability_state=record.availability_state,
                    permitted_actions=actions,
                    source_reference=record.source_reference,
                    score=round(scores[idx], 8),
                )
            )
            if len(results) == limit:
                break
        return SearchResponse(
            query=query, status="matches" if results else "no_match", results=results
        )
