"""RAG retriever — fetch relevant policy context for a claim query."""

import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

COLLECTION_NAME = "insurance_policies"

# Fallback policy rules used when ChromaDB is unavailable
FALLBACK_POLICY_CONTEXT = """
KEY INSURANCE POLICY RULES (Built-in Reference):

COVERAGE:
- Medical services (office visits, surgery, hospitalization, lab tests) are covered when medically necessary.
- Emergency services are always covered regardless of network status.
- Mental health services are covered at parity with medical benefits (Mental Health Parity Act).
- Pre-existing conditions cannot be used to deny coverage under ACA rules.

EXCLUSIONS:
- Dental services are excluded from medical-only plans.
- Cosmetic/elective procedures without medical necessity are excluded.
- Experimental/investigational treatments (Phase I-III clinical trials) are excluded unless otherwise approved.
- Duplicate claims (same member, provider, date, procedure within 90 days) are denied.

CLAIM REQUIREMENTS:
- Required fields: Patient name, DOB, policy number, provider NPI, ICD-10 code, CPT code, date of service, billed amount.
- Missing required fields result in rejection or manual review.
- Claims over $25,000 require manual senior reviewer approval.
- Out-of-network claims are subject to higher cost-sharing and manual review.

AUTO-APPROVAL: Claims under $5,000 with all required fields, in-network provider, valid codes, no duplicates.
AUTO-DENIAL: Dental on medical plan, experimental treatments, duplicates, missing mandatory fields.
MANUAL REVIEW: Claims >$25,000, out-of-network, missing some fields, code mismatches.
"""


def _get_chroma_client(persist_dir: str):
    import chromadb
    return chromadb.PersistentClient(path=persist_dir)


def _get_embeddings():
    from langchain_openai import OpenAIEmbeddings
    from src.config import OPENAI_API_KEY
    return OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY, model="text-embedding-3-small")


def retrieve_policy_context(query: str, persist_dir: str, top_k: int = 5) -> Tuple[str, List[str]]:
    """
    Query ChromaDB for relevant policy chunks.
    Returns (context_string, list_of_sources).
    Falls back to built-in rules if ChromaDB is unavailable.
    """
    try:
        client = _get_chroma_client(persist_dir)
        collections = [c.name for c in client.list_collections()]
        if COLLECTION_NAME not in collections:
            logger.info("ChromaDB collection not found — using fallback policy context")
            return FALLBACK_POLICY_CONTEXT, ["built-in policy rules"]

        collection = client.get_collection(COLLECTION_NAME)
        if collection.count() == 0:
            return FALLBACK_POLICY_CONTEXT, ["built-in policy rules"]

        embeddings = _get_embeddings()
        query_embedding = embeddings.embed_query(query)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, collection.count()),
            include=["documents", "metadatas"],
        )

        docs = results["documents"][0] if results["documents"] else []
        metas = results["metadatas"][0] if results["metadatas"] else []
        sources = list({m.get("source", "unknown") for m in metas})

        if not docs:
            return FALLBACK_POLICY_CONTEXT, ["built-in policy rules"]

        context = "\n\n---\n\n".join(docs)
        logger.info(f"Retrieved {len(docs)} policy chunks from {sources}")
        return context, sources

    except Exception as e:
        logger.warning(f"RAG retrieval failed ({e}) — using fallback policy context")
        return FALLBACK_POLICY_CONTEXT, ["built-in policy rules"]
