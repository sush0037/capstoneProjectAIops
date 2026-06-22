"""Ingest policy documents into ChromaDB for RAG retrieval."""

import os
import logging
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

COLLECTION_NAME = "insurance_policies"


def _get_chroma_client(persist_dir: str):
    import chromadb
    return chromadb.PersistentClient(path=persist_dir)


def _get_embeddings():
    from langchain_openai import OpenAIEmbeddings
    from src.config import OPENAI_API_KEY
    return OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY, model="text-embedding-3-small")


def _load_pdf_text(pdf_path: str) -> str:
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except Exception as e:
        logger.error(f"Failed to read {pdf_path}: {e}")
        return ""


def _chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    """Simple fixed-size text chunker."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end].strip())
        start += chunk_size - overlap
    return [c for c in chunks if len(c) > 50]


def ingest_policy_documents(policy_dir: str, persist_dir: str, force_reingest: bool = False) -> int:
    """
    Load all PDFs from policy_dir, chunk them, embed, and store in ChromaDB.
    Returns the number of chunks stored.
    """
    Path(persist_dir).mkdir(parents=True, exist_ok=True)
    client = _get_chroma_client(persist_dir)
    embeddings = _get_embeddings()

    # Check if already ingested
    existing = client.list_collections()
    if any(c.name == COLLECTION_NAME for c in existing) and not force_reingest:
        collection = client.get_collection(COLLECTION_NAME)
        count = collection.count()
        if count > 0:
            logger.info(f"Collection '{COLLECTION_NAME}' already has {count} chunks — skipping ingest")
            return count

    # Drop and recreate collection
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(COLLECTION_NAME)

    pdf_files = list(Path(policy_dir).glob("*.pdf"))
    if not pdf_files:
        logger.warning(f"No PDF files found in {policy_dir}")
        return 0

    all_ids, all_docs, all_metas = [], [], []

    for pdf_path in pdf_files:
        text = _load_pdf_text(str(pdf_path))
        if not text:
            continue
        chunks = _chunk_text(text)
        for i, chunk in enumerate(chunks):
            doc_id = f"{pdf_path.stem}_chunk_{i}"
            all_ids.append(doc_id)
            all_docs.append(chunk)
            all_metas.append({"source": pdf_path.name, "chunk_index": i})

    if not all_docs:
        return 0

    # Embed in batches of 100
    batch_size = 100
    for i in range(0, len(all_docs), batch_size):
        batch_docs = all_docs[i:i + batch_size]
        batch_ids = all_ids[i:i + batch_size]
        batch_metas = all_metas[i:i + batch_size]
        batch_embeddings = embeddings.embed_documents(batch_docs)
        collection.add(
            ids=batch_ids,
            documents=batch_docs,
            metadatas=batch_metas,
            embeddings=batch_embeddings,
        )

    logger.info(f"Ingested {len(all_docs)} chunks from {len(pdf_files)} policy documents")
    return len(all_docs)


def get_collection_stats(persist_dir: str) -> dict:
    try:
        client = _get_chroma_client(persist_dir)
        collections = client.list_collections()
        for c in collections:
            if c.name == COLLECTION_NAME:
                col = client.get_collection(COLLECTION_NAME)
                return {"exists": True, "chunk_count": col.count(), "collection": COLLECTION_NAME}
        return {"exists": False, "chunk_count": 0, "collection": COLLECTION_NAME}
    except Exception as e:
        return {"exists": False, "chunk_count": 0, "error": str(e)}
