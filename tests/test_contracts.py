import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from find_the_moment.indexing import read_corpus
from find_the_moment.models import Recording
from find_the_moment.segmentation import SegmentConfig, segment_recording


@pytest.mark.parametrize(
    "field",
    [
        "asset_id",
        "recording_version_id",
        "transcript_revision_id",
        "rights_class",
        "custody_reference",
        "duration_ms",
    ],
)
def test_required_fields(records, field):
    data = records[0].model_dump()
    del data[field]
    with pytest.raises(ValidationError):
        Recording.model_validate(data)


@pytest.mark.parametrize(
    "mutation",
    [
        "negative",
        "reversed",
        "overlap",
        "duration",
        "duplicate",
        "coverage",
        "string_time",
        "bad_id",
        "bad_rights",
    ],
)
def test_invalid_evidence(records, mutation):
    data = records[0].model_dump()
    if mutation == "negative":
        data["words"][0]["start_ms"] = -1
    elif mutation == "reversed":
        data["words"][0]["end_ms"] = data["words"][0]["start_ms"]
    elif mutation == "overlap":
        data["words"][1]["start_ms"] = data["words"][0]["start_ms"]
    elif mutation == "duration":
        data["duration_ms"] = 1
    elif mutation == "duplicate":
        data["words"][1]["word_id"] = data["words"][0]["word_id"]
    elif mutation == "coverage":
        data["coverage"] = []
    elif mutation == "string_time":
        data["words"][0]["start_ms"] = "5000"
    elif mutation == "bad_id":
        data["asset_id"] = "../../escape"
    else:
        data["rights_class"] = "public-by-default"
    with pytest.raises(ValidationError):
        Recording.model_validate(data)


def test_duplicate_version_rejected(tmp_path, records):
    path = tmp_path / "records.json"
    path.write_text(json.dumps([records[0].model_dump()] * 2))
    with pytest.raises(ValueError, match="duplicate version"):
        read_corpus(path)


def test_source_bounds_and_stable_ids(records):
    for record in records:
        a = segment_recording(record, SegmentConfig())
        assert a == segment_recording(record, SegmentConfig())
        source = {w.word_id: w for w in record.words}
        for s in a:
            assert 0 <= s.start_ms < s.end_ms <= record.duration_ms
            assert s.start_ms == source[s.start_word_id].start_ms
            assert s.end_ms == source[s.end_word_id].end_ms
            assert s.text == " ".join(source[w].text for w in s.word_ids)
            assert any(c.start_ms <= s.start_ms < s.end_ms <= c.end_ms for c in record.coverage)


def test_overlap_and_progress(records):
    config = SegmentConfig(target_ms=6000, max_ms=10000, overlap_ms=2000)
    segments = segment_recording(records[2], config)
    assert len(segments) > 1
    assert any(a.end_ms > b.start_ms for a, b in zip(segments, segments[1:]))
    assert all(a.start_ms < b.start_ms for a, b in zip(segments, segments[1:]))
    assert all(s.end_ms - s.start_ms <= config.max_ms for s in segments)


def test_version_separation(records):
    a = segment_recording(records[0], SegmentConfig())
    b = segment_recording(records[1], SegmentConfig())
    matching = next(s for s in a if "never surrender" in s.text)
    assert matching.start_ms == 120000
    assert b[0].start_ms == 18000
    assert matching.segment_id != b[0].segment_id


def test_config_validation():
    with pytest.raises(ValidationError):
        SegmentConfig(overlap_ms=30000)


def test_untimed_text_is_not_indexed(records):
    assert not segment_recording(records[-1], SegmentConfig())
    flood = segment_recording(records[3], SegmentConfig())
    assert all("radio appeal" not in s.text for s in flood)


def test_metadata_and_language_preserved(records):
    assert [f.value for f in records[3].source_metadata] == ["1952", "1953"]
    mixed = segment_recording(records[7], SegmentConfig())
    assert {s.language for s in mixed} == {"en", "fr"}


def test_fixture_generator_matches_committed_data():
    import runpy

    generated = runpy.run_path("scripts/make_fixtures.py")["records"]
    assert generated == json.loads(Path("data/sample/recordings.json").read_text())
