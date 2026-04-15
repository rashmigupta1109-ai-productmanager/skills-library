"""
rag_engine.py — Core RAG (Retrieval-Augmented Generation) logic.

Responsibilities:
  - Ingest documents (PDF / plain-text) into a ChromaDB vector store
  - Run similarity search over stored chunks
  - Build a conversational RAG chain with memory
"""

import os
import uuid
import logging
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferWindowMemory
from langchain_community.document_loaders import PyPDFLoader, TextLoader

load_dotenv()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration (pulled from .env)
# ---------------------------------------------------------------------------
OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL          = os.getenv("LLM_MODEL", "gpt-4o-mini")
EMBEDDING_MODEL    = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
RETRIEVAL_TOP_K    = int(os.getenv("RETRIEVAL_TOP_K", "4"))
CHUNK_SIZE         = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP      = int(os.getenv("CHUNK_OVERLAP", "200"))
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")


class RAGEngine:
    """Manages document ingestion, retrieval, and answer generation."""

    def __init__(self) -> None:
        if not OPENAI_API_KEY or OPENAI_API_KEY == "your_openai_api_key_here":
            raise EnvironmentError(
                "OPENAI_API_KEY is not set. "
                "Please edit backend/.env and add your OpenAI API key."
            )

        self.embeddings = OpenAIEmbeddings(
            model=EMBEDDING_MODEL,
            openai_api_key=OPENAI_API_KEY,
        )

        self.vectorstore = Chroma(
            collection_name="rag_docs",
            embedding_function=self.embeddings,
            persist_directory=CHROMA_PERSIST_DIR,
        )

        self.llm = ChatOpenAI(
            model=LLM_MODEL,
            temperature=0.2,
            openai_api_key=OPENAI_API_KEY,
        )

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

        # Per-session memory kept in RAM (keyed by session_id)
        self._memories: dict[str, ConversationBufferWindowMemory] = {}

    # ------------------------------------------------------------------
    # Document ingestion
    # ------------------------------------------------------------------

    def ingest_file(self, file_path: str, filename: str) -> dict:
        """
        Load, split, and embed a document.

        Returns a summary dict with doc_id, filename, and chunk count.
        """
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix == ".pdf":
            loader = PyPDFLoader(str(path))
        elif suffix in (".txt", ".md"):
            loader = TextLoader(str(path), encoding="utf-8")
        else:
            raise ValueError(f"Unsupported file type: {suffix}. Upload PDF or TXT.")

        raw_docs = loader.load()
        chunks   = self.text_splitter.split_documents(raw_docs)

        doc_id = str(uuid.uuid4())
        for chunk in chunks:
            chunk.metadata["doc_id"]   = doc_id
            chunk.metadata["filename"] = filename

        self.vectorstore.add_documents(chunks)

        logger.info("Ingested '%s' → %d chunks (doc_id=%s)", filename, len(chunks), doc_id)
        return {"doc_id": doc_id, "filename": filename, "chunks": len(chunks)}

    def ingest_text(self, text: str, source_name: str = "pasted-text") -> dict:
        """Ingest raw text directly (no file needed)."""
        doc    = Document(page_content=text, metadata={"source": source_name})
        chunks = self.text_splitter.split_documents([doc])

        doc_id = str(uuid.uuid4())
        for chunk in chunks:
            chunk.metadata["doc_id"]   = doc_id
            chunk.metadata["filename"] = source_name

        self.vectorstore.add_documents(chunks)
        return {"doc_id": doc_id, "filename": source_name, "chunks": len(chunks)}

    # ------------------------------------------------------------------
    # Chat / querying
    # ------------------------------------------------------------------

    def _get_memory(self, session_id: str) -> ConversationBufferWindowMemory:
        if session_id not in self._memories:
            self._memories[session_id] = ConversationBufferWindowMemory(
                k=10,
                memory_key="chat_history",
                return_messages=True,
                output_key="answer",
            )
        return self._memories[session_id]

    def chat(self, question: str, session_id: str) -> dict:
        """
        Answer a question using retrieved context + conversation history.

        Returns: {answer, sources, session_id}
        """
        has_docs = self.vectorstore._collection.count() > 0

        if has_docs:
            retriever = self.vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": RETRIEVAL_TOP_K},
            )
            memory = self._get_memory(session_id)
            chain  = ConversationalRetrievalChain.from_llm(
                llm=self.llm,
                retriever=retriever,
                memory=memory,
                return_source_documents=True,
                output_key="answer",
            )
            result = chain.invoke({"question": question})
            answer = result["answer"]
            source_docs = result.get("source_documents", [])
            sources = self._dedupe_sources(source_docs)
        else:
            # No documents yet — fall back to plain LLM chat
            from langchain.schema import HumanMessage, SystemMessage
            messages = [
                SystemMessage(
                    content=(
                        "You are a helpful AI assistant. "
                        "No documents have been uploaded yet. "
                        "Answer the user's question using your general knowledge, "
                        "and remind them they can upload documents for grounded answers."
                    )
                ),
                HumanMessage(content=question),
            ]
            response = self.llm.invoke(messages)
            answer   = response.content
            sources  = []

        return {"answer": answer, "sources": sources, "session_id": session_id}

    def _dedupe_sources(self, docs: list) -> list[dict]:
        seen = set()
        sources = []
        for doc in docs:
            fname = doc.metadata.get("filename", "unknown")
            page  = doc.metadata.get("page", "")
            key   = f"{fname}:{page}"
            if key not in seen:
                seen.add(key)
                sources.append({"filename": fname, "page": page})
        return sources

    # ------------------------------------------------------------------
    # Document management
    # ------------------------------------------------------------------

    def list_documents(self) -> list[dict]:
        """Return unique documents stored in the vector store."""
        try:
            data = self.vectorstore._collection.get(include=["metadatas"])
            seen, docs = set(), []
            for meta in data["metadatas"]:
                doc_id = meta.get("doc_id")
                if doc_id and doc_id not in seen:
                    seen.add(doc_id)
                    docs.append({
                        "doc_id":   doc_id,
                        "filename": meta.get("filename", "unknown"),
                    })
            return docs
        except Exception as exc:
            logger.warning("Could not list documents: %s", exc)
            return []

    def delete_document(self, doc_id: str) -> bool:
        """Remove all chunks belonging to a document."""
        try:
            self.vectorstore._collection.delete(where={"doc_id": doc_id})
            return True
        except Exception as exc:
            logger.error("Delete failed for doc_id=%s: %s", doc_id, exc)
            return False

    def clear_session(self, session_id: str) -> None:
        """Wipe conversation history for a session."""
        self._memories.pop(session_id, None)

    def clear_all_documents(self) -> int:
        """Delete every document chunk from the vector store. Returns chunk count removed."""
        try:
            data  = self.vectorstore._collection.get()
            ids   = data.get("ids", [])
            count = len(ids)
            if count:
                self.vectorstore._collection.delete(ids=ids)
            logger.info("Cleared all documents (%d chunks removed).", count)
            return count
        except Exception as exc:
            logger.error("Failed to clear all documents: %s", exc)
            raise
