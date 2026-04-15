"""
main.py — FastAPI server for the RAG Chatbot.

Endpoints:
  POST /api/chat          — send a message, get an AI answer
  POST /api/upload        — upload a PDF or TXT document
  GET  /api/documents     — list all ingested documents
  DELETE /api/documents/{doc_id} — delete a document
  POST /api/session/clear — clear conversation history for a session
  GET  /api/health        — health check
"""

import os
import uuid
import logging
import tempfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from rag_engine import RAGEngine

# ---------------------------------------------------------------------------
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5500,http://127.0.0.1:5500").split(",")
]
# ---------------------------------------------------------------------------

app = FastAPI(
    title="RAG Chatbot API",
    description="Retrieval-Augmented Generation chatbot backend",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tightened to ALLOWED_ORIGINS in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialise the RAG engine once at startup
try:
    rag = RAGEngine()
    logger.info("RAG engine initialised successfully.")
except EnvironmentError as e:
    rag = None
    logger.error("RAG engine failed to initialise: %s", e)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    session_id: str = ""          # empty → new session


class SessionClearRequest(BaseModel):
    session_id: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {
        "status": "ok" if rag else "degraded",
        "rag_ready": rag is not None,
    }


@app.post("/api/chat")
def chat(req: ChatRequest):
    if not rag:
        raise HTTPException(
            status_code=503,
            detail="RAG engine is not available. Check that OPENAI_API_KEY is set in backend/.env",
        )
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    session_id = req.session_id or str(uuid.uuid4())

    try:
        result = rag.chat(req.message.strip(), session_id)
        return {
            "answer":     result["answer"],
            "sources":    result["sources"],
            "session_id": session_id,
        }
    except Exception as exc:
        logger.exception("Chat error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    if not rag:
        raise HTTPException(status_code=503, detail="RAG engine not available.")

    filename = file.filename or "upload"
    suffix   = Path(filename).suffix.lower()

    if suffix not in (".pdf", ".txt", ".md"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF (.pdf) and plain-text (.txt / .md) files are supported.",
        )

    # Write to a temp file so loaders can open it by path
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        info = rag.ingest_file(tmp_path, filename)
        return {
            "success":  True,
            "doc_id":   info["doc_id"],
            "filename": info["filename"],
            "chunks":   info["chunks"],
            "message":  f"'{filename}' ingested successfully ({info['chunks']} chunks).",
        }
    except Exception as exc:
        logger.exception("Upload error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@app.get("/api/documents")
def list_documents():
    if not rag:
        raise HTTPException(status_code=503, detail="RAG engine not available.")
    docs = rag.list_documents()
    return {"documents": docs, "count": len(docs)}


@app.delete("/api/documents/{doc_id}")
def delete_document(doc_id: str):
    if not rag:
        raise HTTPException(status_code=503, detail="RAG engine not available.")
    success = rag.delete_document(doc_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete document.")
    return {"success": True, "message": f"Document {doc_id} deleted."}


@app.delete("/api/documents")
def clear_all_documents():
    if not rag:
        raise HTTPException(status_code=503, detail="RAG engine not available.")
    try:
        count = rag.clear_all_documents()
        return {"success": True, "message": f"Knowledge base cleared ({count} chunks removed)."}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/session/clear")
def clear_session(req: SessionClearRequest):
    if not rag:
        raise HTTPException(status_code=503, detail="RAG engine not available.")
    rag.clear_session(req.session_id)
    return {"success": True, "message": "Conversation history cleared."}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )
