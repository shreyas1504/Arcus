"""BGE query embeddings with onnxruntime, so the API server does not need torch.

Matches sentence-transformers for BAAI/bge-small-en-v1.5: CLS pooling, L2
normalization, 512-token truncation.
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np

DEFAULT_MODEL_DIR = Path(
    os.getenv(
        "RESEARCH_EMBEDDER_DIR",
        str(Path(os.getenv("RESEARCH_DATA_DIR", "research/data")) / "bge-small-en-v1.5-onnx"),
    )
)
MAX_TOKENS = 512


class OnnxEmbedder:
    def __init__(self, model_dir: Path = DEFAULT_MODEL_DIR, *, threads: int = 1):
        import onnxruntime as ort
        from tokenizers import Tokenizer

        self.tokenizer = Tokenizer.from_file(str(model_dir / "tokenizer.json"))
        self.tokenizer.enable_truncation(MAX_TOKENS)
        self.tokenizer.no_padding()
        options = ort.SessionOptions()
        options.intra_op_num_threads = threads
        options.inter_op_num_threads = 1
        options.enable_cpu_mem_arena = False
        self.session = ort.InferenceSession(
            str(model_dir / "model.onnx"), options, providers=["CPUExecutionProvider"]
        )
        self.input_names = {item.name for item in self.session.get_inputs()}

    def encode(self, texts: list[str], **_) -> np.ndarray:
        vectors = []
        for text in texts:
            encoding = self.tokenizer.encode(text)
            feeds = {
                "input_ids": np.array([encoding.ids], dtype=np.int64),
                "attention_mask": np.array([encoding.attention_mask], dtype=np.int64),
                "token_type_ids": np.array([encoding.type_ids], dtype=np.int64),
            }
            hidden = self.session.run(None, {k: v for k, v in feeds.items() if k in self.input_names})[0]
            cls = hidden[0, 0]
            vectors.append(cls / max(np.linalg.norm(cls), 1e-12))
        return np.asarray(vectors, dtype=np.float32)
