"""Versioned evidence contracts. Invalid rights or timings fail closed."""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

Identifier = Annotated[str, Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,119}$")]
Millis = Annotated[int, Field(strict=True, ge=0)]
Rights = Literal["approved", "restricted", "unknown"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Word(Contract):
    word_id: Identifier
    text: Annotated[str, Field(min_length=1, pattern=r"\S")]
    start_ms: Millis
    end_ms: Millis
    language: Annotated[str, Field(min_length=2)]
    confidence: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def interval(self) -> Self:
        if self.start_ms >= self.end_ms:
            raise ValueError("word must have positive duration")
        return self


class Coverage(Contract):
    start_ms: Millis
    end_ms: Millis

    @model_validator(mode="after")
    def interval(self) -> Self:
        if self.start_ms >= self.end_ms:
            raise ValueError("coverage interval must have positive duration")
        return self


class Fact(Contract):
    field: str
    value: str
    source: str


class Recording(Contract):
    schema_version: Literal["1"] = "1"
    event_id: Identifier
    asset_id: Identifier
    recording_version_id: Identifier
    transcript_revision_id: Identifier
    title: Annotated[str, Field(min_length=1)]
    event_date: str | None = None
    recording_date: str | None = None
    custody_reference: Annotated[str, Field(min_length=1)]
    duration_ms: Annotated[int, Field(strict=True, gt=0)]
    rights_class: Rights
    availability_state: Literal["online", "offline", "unavailable"]
    source_kind: Literal["synthetic_fixture", "validated_transcript"]
    source_reference: Annotated[str, Field(min_length=1)]
    coverage: list[Coverage]
    words: list[Word]
    untimed_text: str = ""
    source_metadata: list[Fact] = Field(default_factory=list)
    quality_flags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def evidence(self) -> Self:
        if not self.words and not self.untimed_text:
            raise ValueError("transcript evidence is required")
        ids = [w.word_id for w in self.words]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate word identifiers")
        for i, region in enumerate(self.coverage):
            if region.end_ms > self.duration_ms:
                raise ValueError("coverage outside recording")
            if i and region.start_ms < self.coverage[i - 1].end_ms:
                raise ValueError("coverage must be sorted and disjoint")
        for i, word in enumerate(self.words):
            if word.end_ms > self.duration_ms:
                raise ValueError("word outside recording")
            if i and word.start_ms < self.words[i - 1].end_ms:
                raise ValueError("word order/overlap invalid for single-stream transcript")
            if not any(
                c.start_ms <= word.start_ms < word.end_ms <= c.end_ms for c in self.coverage
            ):
                raise ValueError("word must belong to declared timed coverage")
        return self


class Segment(Contract):
    asset_id: Identifier
    recording_version_id: Identifier
    transcript_revision_id: Identifier
    segment_id: Identifier
    start_ms: Millis
    end_ms: Millis
    text: str
    start_word_id: Identifier
    end_word_id: Identifier
    language: str
    rights_class: Rights
    availability_state: Literal["online", "offline", "unavailable"]
    processing_version: str
    word_ids: list[str]


class SearchResult(Contract):
    title: str
    event_id: str
    event_date: str | None
    asset_id: str
    recording_version_id: str
    transcript_revision_id: str
    segment_id: str
    matched_excerpt: str
    start_ms: int
    end_ms: int
    start_word_id: str
    end_word_id: str
    language: str
    evidence_status: str
    resolution: Literal["exact_phrase", "source_window"]
    quality_flags: list[str]
    coverage_fraction: float
    availability_state: str
    permitted_actions: list[str]
    source_reference: str
    score: float


class SearchResponse(Contract):
    query: str
    status: Literal["matches", "no_match"]
    results: list[SearchResult]
    notice: str = (
        "Search covers indexed timed evidence only. Scores are ranking signals, "
        "not probabilities. Demo identities are not production authentication."
    )
