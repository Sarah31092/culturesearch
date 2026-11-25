import hashlib
import re
from pathlib import Path

import chromadb

from .database import SessionLocal
from .models import Event


CHROMA_DIR = Path(__file__).resolve().parent.parent / "chroma"
DIMENSIONS = 384


def _embed(text):
    vector = [0.0] * DIMENSIONS
    words = re.findall(r"[가-힣A-Za-z0-9]+", text.lower())
    features = list(words)
    for word in words:
        if len(word) >= 3:
            features.extend(word[index:index + 2] for index in range(len(word) - 1))
    for feature in features:
        digest = hashlib.sha256(feature.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % DIMENSIONS
        sign = 1.0 if digest[4] % 2 else -1.0
        vector[index] += sign
    norm = sum(value * value for value in vector) ** 0.5
    if norm:
        vector = [value / norm for value in vector]
    return vector


def get_collection():
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name="culture_events",
        metadata={"hnsw:space": "cosine"},
    )


def event_text(event):
    return "\n".join(filter(None, [
        event.title,
        event.event_type,
        event.region,
        event.district,
        event.venue,
        event.category,
        event.description,
        event.address,
        event.target,
    ]))


def build_embeddings():
    db = SessionLocal()
    try:
        events = db.query(Event).all()
        collection = get_collection()
        existing = collection.get(include=[])
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
    finally:
        db.close()

    ids = []
    documents = []
    embeddings = []
    metadatas = []
    for event in events:
        ids.append(str(event.id))
        text = event_text(event)
        documents.append(text)
        embeddings.append(_embed(text))
        metadatas.append({
            "title": event.title,
            "event_type": event.event_type or "미분류",
            "region": event.region or "",
            "district": event.district or "",
            "source": event.source,
        })
    if ids:
        batch_size = 4000
        for start in range(0, len(ids), batch_size):
            end = start + batch_size
            collection.add(
                ids=ids[start:end],
                documents=documents[start:end],
                embeddings=embeddings[start:end],
                metadatas=metadatas[start:end],
            )
    return len(ids)


def search_similar(query, limit=10):
    limit = max(1, min(int(limit), 100))
    collection = get_collection()
    if collection.count() == 0:
        return []
    result = collection.query(
        query_embeddings=[_embed(query)],
        n_results=min(limit, collection.count()),
        include=["documents", "metadatas", "distances"],
    )
    output = []
    result_ids = result.get("ids") or []
    result_documents = result.get("documents") or []
    result_metadatas = result.get("metadatas") or []
    result_distances = result.get("distances") or []
    for ids, docs, metas, distances in zip(
        result_ids, result_documents, result_metadatas, result_distances
    ):
        for event_id, document, metadata, distance in zip(ids, docs, metas, distances):
            output.append({
                "id": int(event_id),
                "document": document,
                "metadata": metadata,
                "distance": distance,
            })
    return output
