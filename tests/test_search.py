import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from find_the_moment.api import create_app
from find_the_moment.indexing import build_index, load_index
from find_the_moment.models import SearchResponse
from find_the_moment.retrieval import bm25, rrf

pytestmark = pytest.mark.integration


def test_bm25_exact_term():
    values = bm25("marigold", ["operation marigold", "apple orchard"])
    assert values[0] > 0 and values[1] == 0


def test_rrf_explicit_ranks():
    scores = rrf([[2, 1], [1, 3]])
    assert scores[1] == 1 / 62 + 1 / 61
    assert scores[1] > scores[2] == scores[3] + (1 / 61 - 1 / 62)


def test_semantic_without_lexical_overlap(engine):
    query = "Refusing to capitulate despite an invasion across every part of our homeland"
    response = engine.search(query, mode="semantic")
    assert response.results
    assert response.results[0].event_id == "churchill-1940-06-04"
    assert response.results[0].resolution == "source_window"


def test_churchill_imprecise_query(engine):
    query = (
        "I'm looking for that Churchill speech where he talks about fighting everywhere… "
        "I think it's during the war, maybe after a retreat? "
        "He says something like they'll never surrender."
    )
    response = engine.search(query)
    assert response.results[0].event_id == "churchill-1940-06-04"
    assert "never surrender" in response.results[0].matched_excerpt


def test_phrase_boundaries_differ_by_version(engine):
    response = engine.search("we shall never surrender", mode="lexical")
    found = {r.recording_version_id: r for r in response.results}
    a, b = found["churchill-full"], found["churchill-edit"]
    assert a.start_ms - b.start_ms == 102000
    assert a.resolution == b.resolution == "exact_phrase"
    assert a.matched_excerpt == "we shall never surrender."
    assert a.end_ms - a.start_ms == 2500


def test_permissions_all_modes(engine):
    for mode in ["lexical", "semantic", "hybrid"]:
        response = engine.search("Operation Marigold confidential shelter locations", mode=mode)
        assert all(r.recording_version_id != "restricted" for r in response.results)
    response = engine.search("Marigold", principal="archivist")
    assert response.results[0].recording_version_id == "restricted"
    response = engine.search("Azurestone", principal="archivist", mode="lexical")
    assert not response.results


def test_unknown_principal_denied(engine):
    with pytest.raises(PermissionError):
        engine.search("Marigold", principal="administrator")


def test_offline_availability(engine):
    response = engine.search("steam locomotive")
    result = response.results[0]
    assert result.availability_state == "offline"
    assert "simulate_retrieval_request" in result.permitted_actions
    assert "preview" not in result.permitted_actions


def test_no_match(engine):
    assert engine.search("quantum superconducting qubits").status == "no_match"


def test_serialization(engine):
    result = engine.search("steam locomotive")
    assert SearchResponse.model_validate_json(result.model_dump_json()) == result


def test_partial_quality(engine):
    result = engine.search("Rising water entered the houses").results[0]
    assert result.coverage_fraction < 1
    assert "metadata_conflict" in result.quality_flags
    assert "low_transcript_confidence_review" in result.quality_flags
    assert "partial_timed_coverage" in result.quality_flags


def test_french_lexical_preserves_original(engine):
    result = engine.search("bibliothèque municipale", mode="lexical").results[0]
    assert result.language == "fr"
    assert "semantic_language_not_validated" in result.quality_flags


def test_idempotency_no_embedding_regeneration(built_index):
    class MustNotEncode:
        def encode(self, texts):
            raise AssertionError("unchanged ingestion must reuse vectors")

    before = built_index.read_bytes()
    result = build_index(Path("data/sample/recordings.json"), built_index, MustNotEncode())
    assert result["status"] == "unchanged"
    assert built_index.read_bytes() == before


def test_failed_build_retains_previous_index(built_index, tmp_path):
    class FailingEncoder:
        def encode(self, texts):
            raise RuntimeError("simulated embedding outage")

    data = json.loads(Path("data/sample/recordings.json").read_text())
    data[0]["title"] += " revised"
    corpus = tmp_path / "changed.json"
    corpus.write_text(json.dumps(data))
    before = built_index.read_bytes()
    with pytest.raises(RuntimeError):
        build_index(corpus, built_index, FailingEncoder())
    assert built_index.read_bytes() == before


@pytest.mark.parametrize("field,value", [("model_revision", "wrong"), ("dimensions", 42)])
def test_model_mismatch_rejected(built_index, tmp_path, field, value):
    data = json.loads(built_index.read_text())
    data[field] = value
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        load_index(path)


def test_corrupt_evidence_rejected(built_index, tmp_path):
    data = json.loads(built_index.read_text())
    data["segments"][0]["start_ms"] += 1
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="segment evidence"):
        load_index(path)


def test_api_contract_and_role_injection(engine):
    with TestClient(create_app(engine)) as client:
        result = client.post("/search", json={"query": "steam locomotive"})
        assert result.status_code == 200
        assert result.json()["results"][0]["recording_version_id"] == "railway"
        assert (
            client.post("/search", json={"query": "Marigold", "principal": "archivist"}).status_code
            == 422
        )
        response = client.post(
            "/search", json={"query": "Marigold"}, headers={"X-Role": "archivist"}
        )
        assert response.json()["results"] == []
        assert client.post("/search", json={"query": "   "}).status_code == 422
        assert client.get("/health").json()["authentication"] == "fixed_demo_producer"


def test_version_filter(engine):
    response = engine.search("we shall never surrender", recording_version_id="churchill-edit")
    assert len(response.results) == 1
    assert response.results[0].recording_version_id == "churchill-edit"


def test_transcript_mutation_requires_new_revision(built_index, encoder, tmp_path):
    data = json.loads(Path("data/sample/recordings.json").read_text())
    data[0]["words"][0]["text"] = "Changed"
    path = tmp_path / "mutated.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="new revision"):
        build_index(path, built_index, encoder)


def test_query_does_not_reembed_corpus(engine):
    class QueryOnly:
        def encode(self, texts):
            assert len(texts) == 1
            return original.encode(texts)

    original = engine.encoder
    engine.encoder = QueryOnly()
    try:
        assert engine.search("steam locomotive").results
    finally:
        engine.encoder = original


def test_overlapping_results_suppressed(engine):
    response = engine.search("we shall never surrender")
    for i, a in enumerate(response.results):
        for b in response.results[i + 1 :]:
            if a.recording_version_id == b.recording_version_id:
                assert min(a.end_ms, b.end_ms) <= max(a.start_ms, b.start_ms)


def test_revocation_between_requests(engine):
    from find_the_moment.retrieval import PRINCIPALS

    assert engine.search("Marigold", principal="archivist").results
    previous = PRINCIPALS["archivist"]
    PRINCIPALS["archivist"] = {"approved"}
    try:
        assert not engine.search("Marigold", principal="archivist").results
    finally:
        PRINCIPALS["archivist"] = previous
