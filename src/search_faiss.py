from __future__ import annotations

import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

EMB_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
INDEX_PATH = Path("data/index/items.faiss")
META_PATH = Path("data/index/items_meta.jsonl")

def load_meta():
    metas = []
    with META_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            metas.append(json.loads(line))
    return metas

def main():
    q = input("Soru/arama: ").strip()
    if not q:
        print("EMPTY_QUERY")
        return

    index = faiss.read_index(str(INDEX_PATH))
    metas = load_meta()

    model = SentenceTransformer(EMB_MODEL_NAME)
    qv = model.encode([q], normalize_embeddings=True)
    qv = np.asarray(qv, dtype="float32")

    D, I = index.search(qv, 5)

    for rank, (score, idx) in enumerate(zip(D[0], I[0]), start=1):
        m = metas[idx]
        print(f"\n#{rank} score={score:.4f}")
        print(m["doc"])

if __name__ == "__main__":
    main()
