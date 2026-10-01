"""Chroma vector store + embedding and LLM factories."""
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document

COLLECTION = "news"


def get_embeddings(model_name: str):
    # Local sentence-transformers model: free, no API key, ~90 MB download on first use.
    from langchain_huggingface import HuggingFaceEmbeddings
    return HuggingFaceEmbeddings(model_name=model_name, encode_kwargs={"normalize_embeddings": True})


def get_llm(model: str, api_key: str, temperature: float = 0.0):
    if not api_key:
        raise SystemExit("GEMINI_API_KEY is not set. Get a free key at aistudio.google.com and add it to .env")
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(model=model, google_api_key=api_key, temperature=temperature, max_retries=2)


def get_store(persist_dir: Path, embeddings) -> Chroma:
    return Chroma(collection_name=COLLECTION, embedding_function=embeddings,
                  persist_directory=str(persist_dir), collection_metadata={"hnsw:space": "cosine"})


def index(store: Chroma, docs: list[Document], batch: int = 256) -> int:
    """Add only documents whose id is not in the store yet. Returns how many were added."""
    existing = set(store.get(include=[])["ids"])
    new = [d for d in docs if d.id not in existing]
    for i in range(0, len(new), batch):
        chunk = new[i:i + batch]
        store.add_documents(chunk, ids=[d.id for d in chunk])
    return len(new)
