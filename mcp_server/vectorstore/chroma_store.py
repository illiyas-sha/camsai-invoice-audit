"""Embedded Chroma PersistentClient: seeding helpers and the similarity query used by API2."""

from __future__ import annotations

from pathlib import Path

import chromadb

from mcp_server.vectorstore.seed_contracts import CONTRACTS

CHROMA_DIR = Path(__file__).resolve().parent.parent.parent / "chroma_data"
COLLECTION_NAME = "vendor_contracts"

_client: chromadb.ClientAPI | None = None


def get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return _client


def get_collection():
    collection = get_client().get_or_create_collection(COLLECTION_NAME)
    if collection.count() == 0:
        collection.add(
            ids=[c["id"] for c in CONTRACTS],
            documents=[c["document"] for c in CONTRACTS],
            metadatas=[c["metadata"] for c in CONTRACTS],
        )
    return collection


def query_contract(vendor_id: str, vendor_name: str) -> dict | None:
    """Return the best-matching historical contract snippet for this vendor, via real embedding similarity."""
    result = get_collection().query(
        query_texts=[f"{vendor_name} ({vendor_id}) contract rate ceiling"],
        n_results=1,
    )
    if not result["ids"] or not result["ids"][0]:
        return None
    metadata = result["metadatas"][0][0]
    return {
        "rate_ceiling": metadata["rate_ceiling"],
        "total_billing_cap": metadata["total_billing_cap"],
        "matched_document": result["documents"][0][0],
        "similarity_distance": result["distances"][0][0],
    }
