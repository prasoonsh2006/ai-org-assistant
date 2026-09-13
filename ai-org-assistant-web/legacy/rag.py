"""
Retrieval-Augmented Generation core.

- Embeddings: sentence-transformers (runs locally, free, no API needed).
- Vector store: ChromaDB, persisted to disk.
- Multi-tenancy: every chunk is tagged with org_id in its metadata, and every
  query filters `where={"org_id": ...}` so one organization can NEVER see
  another organization's data, even though they share the same collection.
"""

import os
import chromadb
from sentence_transformers import SentenceTransformer

from config import EMBEDDING_MODEL_NAME, TOP_K_RESULTS

CHROMA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_store")

_model = None
_client = None


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model


def get_client():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=CHROMA_DIR)
    return _client


def get_collection():
    return get_client().get_or_create_collection(name="org_documents")


def add_chunks(org_id: int, doc_id: int, filename: str, chunks: list[str]):
    """Embed and store a document's chunks, tagged with org_id + doc_id."""
    if not chunks:
        return
    model = get_model()
    collection = get_collection()

    embeddings = model.encode(chunks, show_progress_bar=False).tolist()
    ids = [f"org{org_id}_doc{doc_id}_chunk{i}" for i in range(len(chunks))]
    metadatas = [
        {"org_id": str(org_id), "doc_id": str(doc_id), "filename": filename, "chunk_index": i}
        for i in range(len(chunks))
    ]
    collection.add(documents=chunks, embeddings=embeddings, metadatas=metadatas, ids=ids)


def query_chunks(org_id: int, question: str, top_k: int = TOP_K_RESULTS):
    """Returns a list of (chunk_text, metadata) for the most relevant chunks
    belonging ONLY to this org."""
    model = get_model()
    collection = get_collection()

    q_embedding = model.encode([question]).tolist()
    results = collection.query(
        query_embeddings=q_embedding,
        n_results=top_k,
        where={"org_id": str(org_id)},
    )

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    return list(zip(docs, metas))


def delete_org_data(org_id: int):
    """Utility: wipe all vector data for an organization (e.g. for testing)."""
    collection = get_collection()
    collection.delete(where={"org_id": str(org_id)})
