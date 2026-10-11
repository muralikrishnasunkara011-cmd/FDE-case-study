"""One real pretrained encoder shared by index and query paths."""

import os

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL = "sentence-transformers/all-MiniLM-L6-v2"
REVISION = "c9745ed1d9f207416be6d2e6f8de32d1f16199bf"
DIMENSIONS = 384


class Encoder:
    def __init__(self):
        self.model = SentenceTransformer(
            MODEL,
            revision=REVISION,
            device="cpu",
            local_files_only=os.getenv("HF_HUB_OFFLINE", "0") == "1",
        )

    def encode(self, texts: list[str]) -> np.ndarray:
        # Never silently truncate source text at the model's token limit.
        lengths = [len(self.model.tokenizer.encode(t, add_special_tokens=True)) for t in texts]
        if any(n > self.model.max_seq_length for n in lengths):
            raise ValueError("embedding input exceeds model token limit; reduce window/query")
        return np.asarray(
            self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False),
            dtype=np.float32,
        )
