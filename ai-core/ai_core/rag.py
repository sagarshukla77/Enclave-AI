"""RAG knowledge base: embeddings via Ollama, storage/search via ChromaDB (Week 3)."""
import chromadb
from chromadb.config import Settings

from . import config, llm

# anonymized_telemetry=False -> Chroma never phones home (important for the "sovereign" claim)
_client = chromadb.PersistentClient(
    path=str(config.CHROMA_DIR), settings=Settings(anonymized_telemetry=False)
)
_collection = _client.get_or_create_collection("documents", metadata={"hnsw:space": "cosine"})

EMBED_BATCH = 16


def index_chunks(source: str, chunks: list[dict]) -> int:
    """(Re)index one document. Existing chunks for the same filename are replaced."""
    delete_document(source)
    if not chunks:
        return 0
    for start in range(0, len(chunks), EMBED_BATCH):
        batch = chunks[start:start + EMBED_BATCH]
        vectors = llm.embed([c["text"] for c in batch])
        _collection.add(
            ids=[c["id"] for c in batch],
            documents=[c["text"] for c in batch],
            embeddings=vectors,
            metadatas=[{"source": c["source"], "page": c["page"], "chunk_index": c["chunk_index"]}
                       for c in batch],
        )
    return len(chunks)


def retrieve(question: str, k: int | None = None, sources: list[str] | None = None) -> list[dict]:
    """Top-k most similar chunks with their citation info (filename + page)."""
    if _collection.count() == 0:
        return []
    k = k or config.TOP_K
    query_vec = llm.embed([question])[0]
    kwargs = {"query_embeddings": [query_vec], "n_results": min(k, _collection.count())}
    if sources:
        kwargs["where"] = {"source": {"$in": sources}}
    res = _collection.query(**kwargs)
    results = []
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        results.append({
            "text": doc,
            "source": meta["source"],
            "page": meta["page"],
            "score": round(1 - dist, 4),   # cosine similarity: higher = more relevant
        })
    return results


def delete_document(source: str) -> None:
    _collection.delete(where={"source": source})


def list_documents() -> list[dict]:
    data = _collection.get(include=["metadatas"])
    docs: dict[str, dict] = {}
    for meta in data["metadatas"]:
        d = docs.setdefault(meta["source"], {"filename": meta["source"], "chunks": 0, "pages": set()})
        d["chunks"] += 1
        d["pages"].add(meta["page"])
    return [{"filename": d["filename"], "chunks": d["chunks"], "pages": len(d["pages"])}
            for d in sorted(docs.values(), key=lambda x: x["filename"].lower())]
