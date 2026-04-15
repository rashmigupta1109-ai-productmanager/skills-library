# Skills Library

A **Retrieval-Augmented Generation (RAG) chatbot** built for AssetMark, styled with the company's brand colours. Upload documents (PDF or TXT) to a persistent knowledge base and ask questions — the AI retrieves the most relevant passages and generates grounded answers, citing its sources.

---

## What We Built

| Layer | Technology |
|---|---|
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Backend API | Python 3 + FastAPI |
| RAG Pipeline | LangChain |
| Vector Store | ChromaDB (persistent, local) |
| Embeddings | OpenAI `text-embedding-3-small` |
| LLM | OpenAI `gpt-4o-mini` |
| Document Parsing | PyPDF (PDF), LangChain TextLoader (TXT/MD) |

---

## Features

- **Document ingestion** — upload PDF, TXT, or Markdown files via drag-and-drop or file picker
- **RAG answers** — each response is grounded in retrieved document chunks, with source citations (filename + page number)
- **Conversation memory** — the last 10 turns of chat history are kept per session
- **Fallback mode** — works as a general-purpose assistant even before any documents are uploaded
- **Knowledge base management** — view and delete documents from the sidebar
- **AssetMark brand theme** — navy `#164B81`, blue `#046BD2`, cyan `#00AFD7` throughout the UI
- **Environment variables** — all API keys and settings are stored in `backend/.env`, never hardcoded

---

## Project Structure

```
Skills Library/
├── backend/
│   ├── main.py           # FastAPI server — REST API endpoints
│   ├── rag_engine.py     # RAG logic: ingestion, retrieval, chat
│   ├── requirements.txt  # Python dependencies
│   ├── env.txt           # Visible template for environment variables
│   └── .env              # Your actual API keys (git-ignored)
├── frontend/
│   ├── index.html        # Chat UI layout
│   ├── style.css         # AssetMark-themed styles
│   └── app.js            # All frontend logic (chat, upload, doc list)
├── setup.sh              # One-shot install script
├── .gitignore
└── README.md
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Server + RAG engine health check |
| `POST` | `/api/chat` | Send a message, receive a RAG-grounded answer |
| `POST` | `/api/upload` | Upload and ingest a PDF or TXT document |
| `GET` | `/api/documents` | List all documents in the knowledge base |
| `DELETE` | `/api/documents/{doc_id}` | Remove a document from the knowledge base |
| `POST` | `/api/session/clear` | Clear conversation history for a session |

---

## Setup & Running

### Prerequisites
- Python 3.9+
- An [OpenAI API key](https://platform.openai.com/api-keys)

### 1. Install dependencies

```bash
cd "Skills Library"
bash setup.sh
```

This creates a Python virtual environment and installs all packages from `requirements.txt`.

### 2. Configure your API key

Open `backend/env.txt` (or the hidden `backend/.env`) and set:

```
OPENAI_API_KEY=sk-proj-your-key-here
```

> On Mac, press `Cmd + Shift + .` in Finder to reveal hidden files like `.env`.

### 3. Start the backend

```bash
cd backend
source .venv/bin/activate
python main.py
```

The API server starts at `http://localhost:8000`.

### 4. Open the frontend

Open `frontend/index.html` in your browser.
For the best experience use the **Live Server** extension in VS Code (right-click → *Open with Live Server*).

---

## Environment Variables

All variables live in `backend/.env`. Only `OPENAI_API_KEY` is required to get started.

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | *(required)* | Your OpenAI API key |
| `LLM_MODEL` | `gpt-4o-mini` | Model used to generate answers |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Model used to embed document chunks |
| `RETRIEVAL_TOP_K` | `4` | Number of chunks retrieved per query |
| `CHUNK_SIZE` | `1000` | Characters per document chunk |
| `CHUNK_OVERLAP` | `200` | Overlap between consecutive chunks |
| `CHROMA_PERSIST_DIR` | `./chroma_db` | Where ChromaDB saves its index |
| `HOST` | `0.0.0.0` | FastAPI server host |
| `PORT` | `8000` | FastAPI server port |

---

## How RAG Works

```
User question
      │
      ▼
 Embed question  ──►  ChromaDB similarity search
                              │
                              ▼
                    Top-K relevant chunks
                              │
                              ▼
              LLM (GPT-4o-mini) + chat history
                              │
                              ▼
                   Grounded answer + sources
```

1. **Ingestion** — uploaded documents are split into overlapping chunks, embedded with OpenAI, and stored in ChromaDB.
2. **Retrieval** — the user's question is embedded and the closest `RETRIEVAL_TOP_K` chunks are fetched.
3. **Generation** — the LLM receives the retrieved chunks, conversation history, and the question, then produces a cited answer.

---

## Brand & Design

The UI follows the **AssetMark** visual identity:

| Element | Colour |
|---|---|
| Sidebar background | Navy `#164B81` |
| Primary buttons / user bubbles | Blue `#046BD2` |
| Hover / accent | Cyan `#00AFD7` |
| Page background | Light blue-gray `#F0F5FA` |
| Body text | Slate `#1E293B` |
| Font | Roboto / system-ui |
