"""Local demo API. No user-provided claims or role headers are trusted."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import Field

from .embeddings import Encoder
from .models import Contract, SearchResponse
from .retrieval import SearchEngine


class Query(Contract):
    query: str = Field(min_length=1, max_length=1000)
    limit: int = Field(default=5, ge=1, le=20)
    recording_version_id: str | None = None


def create_app(engine: SearchEngine | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app):
        app.state.engine = engine or SearchEngine(
            Path(os.getenv("FTM_INDEX", "indexes/demo.json")), Encoder()
        )
        yield

    app = FastAPI(title="Find the Moment: local demo", lifespan=lifespan)

    @app.get("/health")
    def health():
        return {"status": "ok", "authentication": "fixed_demo_producer", "media": "not_included"}

    @app.post("/search", response_model=SearchResponse)
    def search(request: Query):
        try:
            return app.state.engine.search(**request.model_dump(), principal="producer")
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return app


app = create_app()
