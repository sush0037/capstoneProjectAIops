"""Ingest policy documents into ChromaDB for RAG retrieval."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.config import POLICY_DOCS_DIR, CHROMA_PERSIST_DIR
from src.rag.ingestion import ingest_policy_documents, get_collection_stats


def main():
    force = "--force" in sys.argv

    print(f"Ingesting policy documents from: {POLICY_DOCS_DIR}")
    print(f"ChromaDB persistence dir: {CHROMA_PERSIST_DIR}")
    if force:
        print("Force re-ingest requested — dropping existing collection")

    count = ingest_policy_documents(POLICY_DOCS_DIR, CHROMA_PERSIST_DIR, force_reingest=force)
    stats = get_collection_stats(CHROMA_PERSIST_DIR)

    print(f"\nIngested {count} chunks")
    print(f"ChromaDB stats: {stats}")
    print("\nDone. RAG is ready.")


if __name__ == "__main__":
    main()
