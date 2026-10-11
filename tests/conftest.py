from pathlib import Path

import pytest

from find_the_moment.embeddings import Encoder
from find_the_moment.indexing import build_index, read_corpus
from find_the_moment.retrieval import SearchEngine


@pytest.fixture
def records():
    return read_corpus(Path("data/sample/recordings.json"))


@pytest.fixture(scope="session")
def encoder():
    return Encoder()


@pytest.fixture(scope="session")
def built_index(tmp_path_factory, encoder):
    path = tmp_path_factory.mktemp("index") / "demo.json"
    build_index(Path("data/sample/recordings.json"), path, encoder)
    return path


@pytest.fixture(scope="session")
def engine(built_index, encoder):
    return SearchEngine(built_index, encoder)
