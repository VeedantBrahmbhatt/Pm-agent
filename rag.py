import os
import chromadb
from sentence_transformers import SentenceTransformer
from confluence_client import get_confluence_pages
from dotenv import load_dotenv

load_dotenv()

chroma_client = chromadb.PersistentClient(path="./chroma_db")
embedder = SentenceTransformer("all-MiniLM-L6-v2")


def _get_collection(user_id: int | None):
    """Each user gets their own isolated ChromaDB collection."""
    name = f"confluence_user_{user_id}" if user_id else "confluence_docs"
    return chroma_client.get_or_create_collection(name)


def chunk_text(text, chunk_size=500):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - 50):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks


def index_confluence_pages(space_keys=None, creds: dict | None = None, user_id: int | None = None):
    collection = _get_collection(user_id)
    pages = get_confluence_pages(space_keys=space_keys, creds=creds)

    if not pages:
        print("No pages found.")
        return 0

    docs, ids, metadatas = [], [], []
    for page in pages:
        chunks = chunk_text(page["content"])
        for i, chunk in enumerate(chunks):
            chunk_id = f"{page['id']}_chunk_{i}"
            docs.append(chunk)
            ids.append(chunk_id)
            metadatas.append({
                "title": page["title"],
                "space_key": page["space_key"],
                "space_name": page["space_name"],
                "url": page["url"],
                "page_id": page["id"]
            })

    print(f"Indexing {len(docs)} chunks from {len(pages)} pages...")
    embeddings = embedder.encode(docs).tolist()
    collection.upsert(documents=docs, embeddings=embeddings, ids=ids, metadatas=metadatas)
    print(f"✅ Indexed {len(pages)} pages.")
    return len(pages)


def query_rag(query, space_keys=None, n_results=3, user_id: int | None = None):
    try:
        collection = _get_collection(user_id)
        query_embedding = embedder.encode([query]).tolist()
        where_filter = {"space_key": {"$in": space_keys}} if space_keys else None

        results = collection.query(
            query_embeddings=query_embedding,
            n_results=n_results,
            where=where_filter
        )

        if not results["documents"][0]:
            return ""

        context_parts = []
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            context_parts.append(f"[{meta['space_name']} — {meta['title']}]\n{doc}")
        return "\n\n---\n\n".join(context_parts)

    except Exception as e:
        print(f"RAG query failed: {e}")
        return ""
