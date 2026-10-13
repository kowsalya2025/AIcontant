# 🎓 EduAI — Personalized AI Learning Content Generator

An AI-powered learning platform that generates **customized educational content** based on a student's learning profile, subject, skill level, and performance.

Generates personalized notes, explanations, examples, quizzes, and learning recommendations.  
RAG retrieves relevant context from learning materials; quiz performance adapts future content.

---

## 🚀 Tech Stack

| Technology | Purpose |
|---|---|
| **Python 3.12** | Core language |
| **Django 4.2 + DRF** | Web framework & REST API |
| **FastAPI 0.115** | Modern async API (runs on port 8001) |
| **Google Gemini 1.5 Flash** | LLM — content, quiz, feedback generation |
| **HuggingFace Transformers** | Local zero-shot classification & summarisation fallback |
| **LangChain** | PromptTemplate, RecursiveCharacterTextSplitter, LLM chains |
| **Sentence Transformers** | Local text embeddings (`all-MiniLM-L6-v2`) |
| **FAISS** | Fast in-memory vector similarity search |
| **ChromaDB** | Persistent on-disk vector store with metadata filtering |
| **PostgreSQL** | Production database (SQLite for local dev, zero config) |
| **Docker + Compose** | Containerised deployment |

---

## 🏗️ Architecture

```
EduAI/
├── config/                  # Django settings & URLs
├── apps/
│   ├── accounts/            # Student auth & learning profiles
│   ├── content/             # AI content generation (DRF)
│   ├── quiz/                # Quiz generation & grading (DRF)
│   ├── recommendations/     # Adaptive recommendations (DRF)
│   └── knowledge/           # RAG document upload (DRF)
├── fastapi_app/             # ← NEW: FastAPI application
│   ├── main.py              #   ASGI app, all routes
│   ├── schemas.py           #   Pydantic v2 request/response models
│   ├── auth.py              #   Token auth (reuses Django DRF tokens)
│   ├── dependencies.py      #   DI: shared LLM/RAG service singletons
│   └── services/
│       ├── content_service.py       # RAG → LangChain → Gemini → ORM
│       ├── quiz_service.py          # LangChain PromptTemplate → Gemini
│       ├── recommendation_service.py
│       └── rag_upload_service.py
├── ai_services/
│   ├── llm_service.py       # Gemini 1.5 Flash client + fallback
│   ├── rag_service.py       # FAISS + ChromaDB dual-store RAG pipeline
│   ├── embedding_service.py # Sentence Transformers (all-MiniLM-L6-v2)
│   ├── hf_service.py        # ← NEW: HuggingFace Transformers pipelines
│   └── chroma_service.py    # ← NEW: ChromaDB persistent vector store
├── knowledge_base/          # Pre-loaded learning materials
├── frontend/
│   ├── templates/           # Django HTML templates
│   └── static/              # CSS, JS assets
├── Dockerfile               # ← NEW
├── docker-compose.yml       # ← NEW (includes PostgreSQL service)
└── run_fastapi.py           # ← NEW: uvicorn launcher for FastAPI
```

---

## 🚀 Quick Start

### Option A — Local Development (SQLite, no Docker)

```bash
# 1. Activate virtual environment
.\venv312\Scripts\activate        # Windows
# source venv312/bin/activate     # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure API key
cp .env.example .env
# Edit .env and set GEMINI_API_KEY=your_key_here

# 4. Run migrations (uses SQLite by default)
python manage.py migrate

# 5. Start Django server (port 8000)
python manage.py runserver

# 6. (Optional) Start FastAPI server (port 8001)
python run_fastapi.py
```

Open **http://localhost:8000** — Django UI  
Open **http://localhost:8001/docs** — FastAPI interactive docs

---

### Option B — Docker with PostgreSQL

```bash
# 1. Copy and configure .env
cp .env.example .env
# Set GEMINI_API_KEY, and optionally change POSTGRES_PASSWORD

# 2. Start all services (PostgreSQL + Django web server)
docker-compose up --build

# 3. (First time) Run migrations inside the container
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
```

Open **http://localhost:8000**

---

## 📡 API Reference

### Django REST Framework (port 8000)

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register/` | Register new student |
| POST | `/api/auth/login/` | Login → returns DRF token |
| POST | `/api/auth/logout/` | Revoke token |
| GET/PUT | `/api/auth/profile/` | Get / update learning profile |
| GET | `/api/auth/dashboard-stats/` | Dashboard statistics |
| POST | `/api/content/generate/` | Generate AI content (RAG + Gemini) |
| GET | `/api/content/history/` | Content history |
| POST | `/api/quiz/generate/` | Generate MCQ quiz |
| POST | `/api/quiz/submit/` | Submit answers → score + feedback |
| GET | `/api/quiz/history/` | Quiz history |
| GET | `/api/recommendations/` | Personalized recommendations |
| POST | `/api/knowledge/upload/` | Upload PDF/TXT for RAG indexing |
| GET | `/api/knowledge/documents/` | List uploaded documents |

### FastAPI (port 8001) — interactive docs at `/docs`

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/generate/content` | Generate content (LangChain + Gemini + FAISS) |
| POST | `/generate/quiz` | Generate quiz (LangChain PromptTemplate) |
| GET | `/recommendations` | Adaptive recommendations |
| POST | `/rag/upload` | Upload & index document (FAISS + Chroma) |
| POST | `/rag/query` | Query RAG index directly |

---

## 🤖 AI Services

| Service | File | Description |
|---|---|---|
| **LLMService** | `ai_services/llm_service.py` | Gemini 1.5 Flash + demo fallback |
| **EmbeddingService** | `ai_services/embedding_service.py` | Sentence Transformers (`all-MiniLM-L6-v2`) |
| **RAGService** | `ai_services/rag_service.py` | FAISS + Chroma dual-store pipeline |
| **HFService** | `ai_services/hf_service.py` | HuggingFace Transformers (zero-shot, summarisation) |
| **ChromaService** | `ai_services/chroma_service.py` | Persistent ChromaDB with metadata filtering |

---

## ⚙️ Environment Variables

| Variable | Description | Default |
|---|---|---|
| `GEMINI_API_KEY` | Google Gemini API key (free) | Required for AI |
| `SECRET_KEY` | Django secret key | Set in .env |
| `DEBUG` | Debug mode | `True` |
| `ALLOWED_HOSTS` | Allowed hosts | `localhost,127.0.0.1` |
| `DB_ENGINE` | `django.db.backends.postgresql` to use PG | SQLite (blank) |
| `DB_NAME` | PostgreSQL database name | `eduai` |
| `DB_USER` | PostgreSQL user | `eduai_user` |
| `DB_PASSWORD` | PostgreSQL password | `eduai_pass` |
| `DB_HOST` | PostgreSQL host | `localhost` |
| `DB_PORT` | PostgreSQL port | `5432` |
| `POSTGRES_DB/USER/PASSWORD` | Docker Compose PostgreSQL env | same as above |

---

## 🎯 Features

- ✅ **Personalized Content** — Notes, explanations, examples, summaries, deep dives
- ✅ **RAG-Enhanced** — FAISS semantic retrieval from your knowledge base
- ✅ **Dual Vector Store** — FAISS (fast) + ChromaDB (persistent, metadata-filtered)
- ✅ **HuggingFace Transformers** — Local zero-shot classification, summarisation fallback
- ✅ **LangChain** — PromptTemplate, text chunking, chain orchestration
- ✅ **AI Quiz Generator** — MCQ quizzes with grading and AI feedback
- ✅ **Adaptive Recommendations** — Based on quiz scores, weak/strong topics
- ✅ **FastAPI** — Modern async API with Pydantic v2 validation + auto docs
- ✅ **PostgreSQL** — Production-grade DB (SQLite fallback for local dev)
- ✅ **Docker** — One-command containerised deployment
- ✅ **Document Upload** — Index your own PDFs for RAG
- ✅ **Progress Tracking** — Points, streaks, quiz scores, weak areas
- ✅ **Premium Dark UI** — Glassmorphism design

> **Get a free Gemini API key**: https://aistudio.google.com/app/apikey
