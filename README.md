<div align="center">

# TechMart AI Support

### Multi-Agent AI Customer Support Assistant powered by RAG and LLMs

A FastAPI + Next.js customer support platform that routes customer messages to specialized AI agents, grounds every answer in a FAISS-indexed knowledge base, and tracks the full conversation lifecycle — sessions, sentiment, tickets, and escalation.

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14-000000?logo=nextdotjs&logoColor=white)](https://nextjs.org/)
[![FAISS](https://img.shields.io/badge/FAISS-Vector%20Search-4B8BBE)](https://github.com/facebookresearch/faiss)
[![Sentence Transformers](https://img.shields.io/badge/Sentence--Transformers-MiniLM--L6--v2-FFB000)](https://www.sbert.net/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00)](https://www.sqlalchemy.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](#license)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](#contributing)

**[Live Demo →](https://techmart-ai-support.vercel.app/)**

</div>

---

## Table of Contents

- [Overview](#overview)
- [Live Demo](#live-demo)
- [Features](#features)
- [System Architecture](#system-architecture)
- [High-Level Request Flow](#high-level-request-flow)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [Multi-Agent System](#multi-agent-system)
- [Retrieval-Augmented Generation (RAG)](#retrieval-augmented-generation-rag)
- [Database Schema](#database-schema)
- [Authentication](#authentication)
- [API Reference](#api-reference)
- [Sample Requests](#sample-requests)
- [Notifications (Email & WhatsApp)](#notifications-email--whatsapp)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgements](#acknowledgements)
- [FAQ](#faq)
- [Troubleshooting](#troubleshooting)

---

## Overview

TechMart AI Support is a customer support system built for a fictional electronics retailer, **TechMart Electronics**. Rather than a single monolithic chatbot prompt, it splits support work across five specialized agents (Billing, Technical, Product, Complaint, FAQ), each with its own system prompt, domain rules, and preferred knowledge-base sources.

Every agent answers using context retrieved from a local **FAISS** vector index built over eight `.txt` knowledge-base documents (FAQ, pricing, refund policy, shipping policy, warranty, user manual, installation guide, and product catalog). If no LLM API key is configured, the system falls back to static templated responses so the app remains functional in a "demo mode."

**Core capabilities:**
- Keyword-first, LLM-refined intent and sentiment classification
- Per-intent agent routing with an empathy blend for frustrated customers
- Source-cited RAG answers grounded in the knowledge base
- JWT-based auth with per-user session history
- Auto-created support tickets for complaints/frustrated sentiment, with email and WhatsApp notifications
- Usage analytics (agent distribution, intent distribution, sentiment trends, response time)
- Admin-only knowledge-base upload and index rebuild endpoints

---

## Live Demo

The frontend is deployed at **[techmart-ai-support.vercel.app](https://techmart-ai-support.vercel.app/)**, backed by the FastAPI service on Render.

---

## Features

- ✅ Multi-Agent architecture (Billing, Technical, Product, Complaint, FAQ)
- ✅ Two-stage intent detection — fast keyword classifier, LLM fallback for ambiguous messages
- ✅ Sentiment detection (positive / neutral / negative / frustrated) with keyword-priority override over the LLM
- ✅ Retrieval-Augmented Generation via FAISS (`IndexFlatL2`) + Sentence-Transformers embeddings
- ✅ Multi-language response matching (detects the language of the current message and instructs the LLM to reply in kind)
- ✅ FastAPI REST backend with JWT authentication (bcrypt password hashing)
- ✅ Next.js (Pages Router) frontend with Tailwind CSS
- ✅ Persistent chat sessions with soft-delete, archive, and restore
- ✅ Automatic support ticket creation for complaints/frustrated sentiment
- ✅ Email notifications (SendGrid API, with SMTP fallback)
- ✅ WhatsApp notifications via Twilio
- ✅ Usage analytics dashboard endpoint (agent/intent/sentiment breakdowns, daily trend)
- ✅ Admin endpoints for knowledge-base document upload and FAISS index rebuild
- ✅ Configurable LLM provider — Groq, OpenAI, or local Ollama (OpenAI-compatible client)
- ✅ Graceful "mock mode" fallback with templated responses when no LLM key is set
- ✅ SQLite by default, swappable to PostgreSQL via `DATABASE_URL`
- ✅ Deployable to Render via `render.yaml`

---

## System Architecture

```mermaid
flowchart TD
    A[Customer Message] --> B[FastAPI /api/chat]
    B --> C[AgentRouter.detect_intent]
    C --> D{Keyword confidence >= 0.7?}
    D -->|Yes| E[Use keyword result]
    D -->|No| F[LLM classification call]
    F --> E
    E --> G[AgentRouter.route]
    G --> H{Primary Intent}
    H --> I1[BillingAgent]
    H --> I2[TechnicalAgent]
    H --> I3[ProductAgent]
    H --> I4[ComplaintAgent]
    H --> I5[FAQAgent]
    I1 --> J[FAISSRetriever.retrieve]
    I2 --> J
    I3 --> J
    I4 --> J
    I5 --> J
    J --> K[FAISS IndexFlatL2]
    K --> L[Top-K Knowledge Base Chunks]
    L --> M[LLMClient.chat]
    M --> N{LLM configured?}
    N -->|Yes| O[Groq / OpenAI / Ollama]
    N -->|No| P[Static Fallback Templates]
    O --> Q[Response Text]
    P --> Q
    Q --> R[Persist Message to SQLite/Postgres]
    R --> S{Complaint or Frustrated?}
    S -->|Yes| T[Create SupportTicket]
    T --> U[Email via SendGrid/SMTP]
    T --> V[WhatsApp via Twilio]
    S -->|No| W[Return ChatResponse]
    U --> W
    V --> W
```

**Supporting services shown above:**

| Component | Role |
|---|---|
| JWT Auth (`api/auth.py`) | Issues/validates bearer tokens, protects all non-auth routes |
| SQLAlchemy ORM (`database/db.py`) | Users, sessions, messages, feedback, tickets, KB doc registry |
| Rate Limiter (`api/routes.py`) | In-memory, 20 messages/minute per user |
| Email Service (`api/email_service.py`) | SendGrid API primary, SMTP fallback, best-effort (never raises) |
| WhatsApp Service (`api/whatsapp_service.py`) | Twilio WhatsApp API, best-effort |

---

## High-Level Request Flow

```mermaid
sequenceDiagram
    participant U as User (Browser)
    participant F as Next.js Frontend
    participant A as FastAPI /api
    participant R as AgentRouter
    participant V as FAISS Retriever
    participant L as LLM Provider
    participant D as Database

    U->>F: Type message, click send
    F->>A: POST /api/chat (Bearer token)
    A->>A: check_rate_limit(user_id)
    A->>R: detect_intent(message)
    R-->>A: intent, sentiment, confidence
    A->>D: Save user Message row
    A->>R: route(message, history)
    R->>V: retrieve(query, top_k)
    V-->>R: Ranked knowledge chunks
    R->>L: chat(messages, system+context)
    L-->>R: Generated response
    R-->>A: response, agent, sources
    A->>D: Save assistant Message row
    alt Complaint or frustrated sentiment
        A->>D: Create SupportTicket
        A->>A: send_ticket_created_email()
        A->>A: send_ticket_whatsapp() (if phone on file)
    end
    A-->>F: ChatResponse JSON
    F-->>U: Render assistant reply
```

---

## Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| Language | Python 3.11+, JavaScript (ES6+) | Backend and frontend implementation |
| Backend Framework | FastAPI 0.115, Uvicorn (standard) | Async REST API server |
| Frontend Framework | Next.js 14 (Pages Router), React 18 | Chat UI, auth pages |
| Styling | Tailwind CSS 3.4 | Frontend styling |
| LLM Providers | Groq (`llama-3.1-8b-instant` default), OpenAI, Ollama | Response generation, via `AsyncOpenAI`-compatible client |
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2`) | Text-to-vector embedding for RAG |
| Vector Store | FAISS (`faiss-cpu`, `IndexFlatL2`) | Exact nearest-neighbor semantic search |
| Database ORM | SQLAlchemy 2.0 | Users, sessions, messages, tickets, feedback |
| Database Engine | SQLite (default) / PostgreSQL (`psycopg2-binary`) | Persistence, selected via `DATABASE_URL` |
| Auth | `python-jose` (JWT), `passlib[bcrypt]` | Token issuance/validation, password hashing |
| Email | SendGrid HTTP API (primary), SMTP (fallback) | Ticket & escalation notifications |
| Messaging | Twilio (`twilio` SDK) | WhatsApp notifications |
| Language Detection | `langdetect`, Unicode range heuristics | Multi-language response matching |
| Deployment (backend) | Render (`render.yaml`), Uvicorn | Backend hosting |
| Deployment (frontend) | Vercel (Next.js) | Frontend hosting — [live demo](https://techmart-ai-support.vercel.app/) |

---

## Project Structure

```text
Multi-Agent-AI-Customer-Support-Assistant-using-RAG-and-LLMs/
├── backend/
│   ├── main.py                    # FastAPI app, lifespan startup, CORS, static frontend mount
│   ├── config.py                  # Settings — env-driven, LLM provider selection
│   ├── agents/
│   │   ├── base.py                # BaseAgent — shared prompt building, language detection, RAG call
│   │   ├── agents.py               # BillingAgent, TechnicalAgent, ProductAgent, ComplaintAgent, FAQAgent
│   │   ├── router.py               # AgentRouter — intent/sentiment detection, agent dispatch
│   │   └── llm_client.py           # LLMClient — Groq/OpenAI/Ollama wrapper + fallback templates
│   ├── rag/
│   │   ├── document_processor.py   # .txt loading, chunking (600 chars, 80 overlap by default)
│   │   ├── embeddings.py           # EmbeddingManager — sentence-transformers wrapper
│   │   └── retriever.py            # FAISSRetriever — index build/reload/search
│   ├── vectorstore/
│   │   └── faiss_index/            # Persisted FAISS index (faiss.index, chunks.pkl)
│   ├── api/
│   │   ├── routes.py               # All HTTP endpoints (auth, chat, sessions, analytics, admin, tickets)
│   │   ├── auth.py                 # JWT + bcrypt auth dependencies
│   │   ├── email_service.py        # SendGrid/SMTP notifications
│   │   └── whatsapp_service.py     # Twilio WhatsApp notifications
│   ├── database/
│   │   └── db.py                   # SQLAlchemy models + session factory
│   └── models/
│       └── schemas.py              # Pydantic request/response models
├── frontend/
│   ├── pages/
│   │   ├── index.js                 # Landing page
│   │   ├── login.js                 # Login page
│   │   ├── register.js              # Registration page
│   │   └── chat.js                  # Main chat interface
│   ├── services/
│   │   └── api.js                   # Central fetch wrapper, JWT storage, timeout handling
│   ├── tailwind.config.js
│   └── package.json
├── knowledge_base/                  # Source .txt (+ generated .pdf) documents for RAG
│   ├── faq.txt
│   ├── installation_guide.txt
│   ├── pricing.txt
│   ├── products.txt
│   ├── refund_policy.txt
│   ├── shipping_policy.txt
│   ├── user_manual.txt
│   └── warranty.txt
├── datasets/                        # Evaluation/sample data (banking77, sample queries/users)
├── setup.py                          # One-time setup: .env check, DB tables, admin user, FAISS build
├── requirements.txt                  # Python dependencies (pinned)
├── render.yaml                       # Render.com deployment config
└── README.md
```

<details>
<summary><strong>What each backend folder is responsible for</strong></summary>

- **`agents/`** — All AI reasoning logic. `base.py` defines the shared retrieval → prompt → LLM call pipeline; `agents.py` defines five domain subclasses that each override `role_description` and append domain-specific rules to the system prompt; `router.py` decides *which* agent handles a message.
- **`rag/`** — Everything related to grounding responses in the knowledge base: chunking raw text, embedding it, indexing it in FAISS, and retrieving relevant chunks at query time.
- **`api/`** — HTTP surface area: route handlers, JWT auth dependencies, and best-effort outbound notification services (email, WhatsApp).
- **`database/`** — SQLAlchemy ORM models and the engine/session setup (SQLite by default, Postgres-ready).
- **`models/`** — Pydantic schemas used for FastAPI request validation and response serialization.

</details>

---

## Installation

### Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- A Groq, OpenAI, or local Ollama endpoint (optional — the app runs in fallback/template mode without one)

### 1. Clone the repository

```bash
git clone https://github.com/Mohit-1307/Multi-Agent-AI-Customer-Support-Assistant-using-RAG-and-LLMs.git
cd Multi-Agent-AI-Customer-Support-Assistant-using-RAG-and-LLMs
```

### 2. Backend setup

```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the project root (see [Environment Variables](#environment-variables) for the full list):

```bash
SECRET_KEY=replace-with-a-long-random-string
GROQ_API_KEY=your-groq-api-key
LLM_PROVIDER=groq
```

`SECRET_KEY` is required — `backend/config.py` raises `ValueError` at import time if it isn't set.

### 4. Run the setup script

This creates database tables, an admin user, and builds the FAISS index from `knowledge_base/`:

```bash
python setup.py
```

This prints the generated admin credentials and confirms the FAISS index was built.

### 5. Start the backend

```bash
uvicorn backend.main:app --reload
# API available at http://localhost:8000
# Interactive docs at http://localhost:8000/docs
```

### 6. Start the frontend

```bash
cd frontend
npm install
npm run dev
# App available at http://localhost:3000
```

### 7. Verify installation

```bash
curl http://localhost:8000/api/health
```

Expected response:

```json
{
  "status": "ok",
  "app": "TechMart AI Support",
  "version": "1.0.0",
  "rag_ready": true,
  "knowledge_chunks": 128,
  "llm_provider": "groq"
}
```

---

## Environment Variables

| Variable | Description | Required | Example |
|---|---|---|---|
| `SECRET_KEY` | JWT signing secret | **Yes** | `openssl rand -hex 32` output |
| `DATABASE_URL` | DB connection string | No (defaults to local SQLite) | `postgresql://user:pass@host/db` |
| `LLM_PROVIDER` | `groq` \| `openai` \| `ollama` \| unset (mock) | No | `groq` |
| `GROQ_API_KEY` | Groq API key | If using Groq | `gsk_...` |
| `GROQ_MODEL` | Groq model name | No (defaults `llama-3.1-8b-instant`) | `llama-3.1-8b-instant` |
| `OPENAI_API_KEY` | OpenAI API key | If using OpenAI | `sk-...` |
| `OPENAI_MODEL` | OpenAI model name | No (defaults `gpt-3.5-turbo`) | `gpt-4o-mini` |
| `OLLAMA_BASE_URL` | Local Ollama endpoint | If using Ollama | `http://localhost:11434/v1` |
| `OLLAMA_MODEL` | Ollama model name | No (defaults `llama3.1`) | `llama3.1` |
| `EMBEDDING_MODEL` | Sentence-transformers model | No (defaults `all-MiniLM-L6-v2`) | `all-MiniLM-L6-v2` |
| `CHUNK_SIZE` | RAG chunk size, characters | No (default `600`) | `600` |
| `CHUNK_OVERLAP` | RAG chunk overlap, characters | No (default `80`) | `80` |
| `TOP_K_RESULTS` | Chunks retrieved per query | No (default `4`) | `4` |
| `MAX_TOKENS` | Max LLM completion tokens | No (default `600`) | `600` |
| `TEMPERATURE` | LLM sampling temperature | No (default `0.7`) | `0.7` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT lifetime, minutes | No (default `1440`) | `1440` |
| `SMTP_HOST` / `SMTP_PORT` | SMTP fallback server | No (default Gmail SMTP) | `smtp.gmail.com` / `587` |
| `SMTP_USER` / `SMTP_PASSWORD` | SMTP credentials | For email notifications | — |
| `SENDGRID_API_KEY` | SendGrid API key (primary email path) | For email notifications | `SG....` |
| `SUPPORT_EMAIL` | Displayed support contact address | No | `support@techmartelectronics.com` |
| `TWILIO_ACCOUNT_SID` | Twilio account SID (must start `AC`) | For WhatsApp notifications | `AC...` |
| `TWILIO_AUTH_TOKEN` | Twilio auth token | For WhatsApp notifications | — |
| `TWILIO_WHATSAPP_FROM` | Twilio WhatsApp sender number | No (default sandbox number) | `whatsapp:+14155238886` |
| `DEBUG` | Enables debug mode | No (default `false`) | `true` |

---

## Multi-Agent System

Every agent is a subclass of `BaseAgent` (`backend/agents/base.py`), which handles the shared pipeline: retrieve context → build system prompt → detect reply language → call the LLM. Each subclass supplies its own `role_description` and appends domain-specific rules to the prompt.

| Agent | Domain Key | Handles | Primary KB Sources |
|---|---|---|---|
| **Billing Support** | `billing` | Payments, subscriptions (TechMart Care), invoices, financing, refunds¹ | `pricing`, `refund_policy`, `faq` |
| **Technical Support** | `technical` | Setup, troubleshooting, errors, password resets, connectivity | `installation_guide`, `user_manual`, `warranty` |
| **Product Specialist** | `product` | Specs, comparisons, availability, recommendations | `products`, `pricing`, `faq` |
| **Customer Relations** | `complaint` | Escalations, dissatisfaction, de-escalation | `refund_policy`, `warranty`, `faq` |
| **Support Assistant** | `faq` | General questions, shipping, account help, policies | `faq`, `shipping_policy`, `warranty` |

¹ The `refund` intent is routed to the same `BillingAgent` instance rather than a dedicated class — `router.py` maps `"refund": BillingAgent()`.

**Routing logic (`AgentRouter.route`):**

1. **Stage 1 — Keyword detection** (`_keyword_detect`): scores the message against per-intent keyword lists (including Hindi/Spanish/French/German refund-related terms) and a separate sentiment keyword set (positive / negative / frustrated). If confidence ≥ 0.7, this result is used directly — no LLM call.
2. **Stage 2 — LLM refinement** (`_llm_detect`): only triggered when keyword confidence is low. Sends a structured classification prompt (with detected message language and recent history) asking for JSON output. If the LLM's sentiment is less severe than the keyword-detected sentiment, the keyword sentiment wins.
3. **Frustration override**: if sentiment is `frustrated`, the `complaint` agent is always added to `suggested_agents`, even if it wasn't the primary intent — its opening empathy line gets prepended to the primary agent's response (deduplicated if already present).

### Language Matching

`BaseAgent._detect_language()` uses Unicode block checks (Devanagari, Hiragana/Katakana, Arabic, CJK) plus common-word heuristics for Spanish/French/German to determine the language of the current message only (conversation history is ignored for this purpose, so a reply always matches what the customer just typed). The detected language is injected into both the system prompt and appended to the user message as an explicit instruction.

---

## Retrieval-Augmented Generation (RAG)

```mermaid
flowchart LR
    A[knowledge_base/*.txt] --> B[document_processor.load_knowledge_base]
    B --> C[split_text: 600 chars, 80 overlap, sentence-boundary aware]
    C --> D[TextChunk objects w/ source + chunk_id]
    D --> E[EmbeddingManager.embed_texts]
    E --> F[all-MiniLM-L6-v2 SentenceTransformer]
    F --> G[Normalized float32 embeddings]
    G --> H[faiss.IndexFlatL2]
    H --> I[Persisted: faiss.index + chunks.pkl]
    I --> J[FAISSRetriever.retrieve at query time]
    J --> K[Top-K chunks + L2 distance scores]
    K --> L[format_context: labeled, source-tagged text block]
    L --> M[Injected into agent system prompt]
```

**Key implementation details:**

- **Chunking** (`document_processor.split_text`): fixed character window (`CHUNK_SIZE=600`, `CHUNK_OVERLAP=80` by default) that tries to break on the last `". "` within the final 150 characters, avoiding mid-sentence cuts where possible.
- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2`, batch-encoded with `normalize_embeddings=True` so cosine similarity is well-approximated by the L2 index.
- **Index**: `faiss.IndexFlatL2` — exact (not approximate) nearest-neighbor search, appropriate given the knowledge base's small size.
- **Persistence**: the index (`faiss.index`) and chunk metadata (`chunks.pkl`) are saved under `backend/vectorstore/faiss_index/`. On startup, `main.py`'s lifespan hook reloads this from disk rather than rebuilding — rebuilding requires loading the embedding model, which the code avoids at startup to keep memory usage low. The index builds lazily on first use if no saved index is found.
- **Admin rebuild**: `POST /api/admin/knowledge-base/rebuild` forces a full re-embed and re-index from the current `.txt` files.

---

## Database Schema

```mermaid
erDiagram
    USER ||--o{ CHAT_SESSION : owns
    USER ||--o{ FEEDBACK : submits
    CHAT_SESSION ||--o{ MESSAGE : contains
    CHAT_SESSION ||--o{ FEEDBACK : receives
    USER {
        string id PK
        string email UK
        string name
        string password_hash
        string phone
        boolean is_admin
        datetime created_at
    }
    CHAT_SESSION {
        string id PK
        string user_id FK
        string title
        text summary
        datetime created_at
        datetime updated_at
        boolean is_active
        boolean is_deleted
    }
    MESSAGE {
        string id PK
        string session_id FK
        string role
        text content
        string agent
        string intent
        string sentiment
        float sentiment_score
        float response_time_ms
        boolean context_used
        datetime timestamp
    }
    FEEDBACK {
        string id PK
        string session_id FK
        string user_id FK
        string message_id FK
        int rating
        text comment
        datetime created_at
    }
    KNOWLEDGE_BASE_DOC {
        string id PK
        string filename UK
        int chunk_count
        int file_size_bytes
        datetime indexed_at
    }
    SUPPORT_TICKET {
        string id PK
        string user_id FK
        string session_id FK
        string ticket_number UK
        string subject
        string status
        string priority
        string agent
        datetime created_at
    }
```

All primary keys are UUID4 strings generated at insert time. SQLite is the default engine (`connect_args={"check_same_thread": False}`); switching `DATABASE_URL` to a PostgreSQL DSN automatically enables `pool_pre_ping=True` instead.

---

## Authentication

```mermaid
sequenceDiagram
    participant C as Client
    participant A as /api/auth/*
    participant D as Database

    C->>A: POST /auth/register {name, email, password, phone}
    A->>D: Check email uniqueness
    A->>D: Insert User (bcrypt password_hash)
    A-->>C: {access_token, user}

    C->>A: POST /auth/login {email, password}
    A->>D: Fetch User by email
    A->>A: verify_password (bcrypt)
    A-->>C: {access_token, user}

    C->>A: GET /auth/me (Authorization: Bearer <token>)
    A->>A: decode_token (jose JWT, HS256)
    A->>D: Fetch User by sub claim
    A-->>C: User profile
```

- Passwords are hashed with `passlib`'s bcrypt scheme.
- JWTs are signed with `HS256` using `SECRET_KEY`, with a default 24-hour (`1440` minute) expiry.
- `get_current_user` and `get_admin_user` are FastAPI dependencies applied via `Depends(...)` on nearly every route.

---

## API Reference

All endpoints are mounted under the `/api` prefix. Interactive Swagger docs are available at `/docs` and ReDoc at `/redoc`.

### Auth

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/register` | Create a new user account |
| `POST` | `/api/auth/login` | Log in, returns JWT |
| `GET` | `/api/auth/me` | Get current user profile |
| `DELETE` | `/api/auth/account` | Permanently delete account + all data |
| `POST` | `/api/auth/reset-history` | Wipe chat/analytics data, keep the account |

### Chat & Sessions

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/chat` | Send a message; routes through the agent system |
| `GET` | `/api/sessions` | List active sessions |
| `POST` | `/api/sessions` | Create an empty session |
| `DELETE` | `/api/sessions/{id}` | Soft-delete a session |
| `GET` | `/api/sessions/{id}/history` | Full message history for a session |
| `GET` | `/api/sessions/{id}/summary` | AI-generated (cached) conversation summary |
| `POST` | `/api/sessions/{id}/archive` | Archive a session |
| `POST` | `/api/sessions/archive-all` | Archive all active sessions |
| `GET` | `/api/sessions/archived` | List archived sessions |
| `GET` | `/api/sessions/deleted` | List soft-deleted sessions |
| `POST` | `/api/sessions/{id}/restore` | Restore an archived/deleted session |
| `POST` | `/api/sessions/unarchive-all` | Restore all archived sessions |
| `POST` | `/api/sessions/restore-all` | Restore all deleted sessions |
| `DELETE` | `/api/sessions/{id}/permanent` | Permanently delete a session |
| `DELETE` | `/api/sessions` | Soft-delete all active sessions |

### Feedback & Analytics

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/feedback` | Submit a 1–5 star rating + comment |
| `GET` | `/api/analytics?days=30` | Usage analytics (self-scoped, or all-user for admins) |

### Admin

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/admin/knowledge-base` | List indexed KB documents (admin only) |
| `POST` | `/api/admin/knowledge-base/rebuild` | Force-rebuild the FAISS index (admin only) |
| `POST` | `/api/admin/knowledge-base/upload` | Upload a new `.txt` KB document (admin only) |

### Tickets & Escalation

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/tickets/create` | Manually create a support ticket |
| `GET` | `/api/tickets` | List the current user's tickets |
| `POST` | `/api/escalate` | Escalate a session to a human agent |

### Notifications & System

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/email/status` | Check if email notifications are configured |
| `GET` | `/api/whatsapp/status` | Check if WhatsApp notifications are configured |
| `GET`/`HEAD` | `/api/health` | Health check + RAG index status |

---

## Sample Requests

<details>
<summary><strong>curl</strong></summary>

```bash
# Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Jane Doe","email":"jane@example.com","password":"SecurePass123","phone":"+15551234567"}'

# Send a chat message
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -d '{"message":"My SmartWatch Series 3 won'\''t turn on, what should I do?"}'
```

</details>

<details>
<summary><strong>Python</strong></summary>

```python
import requests

BASE = "http://localhost:8000/api"

login = requests.post(f"{BASE}/auth/login", json={
    "email": "jane@example.com",
    "password": "SecurePass123"
})
token = login.json()["access_token"]

chat = requests.post(
    f"{BASE}/chat",
    headers={"Authorization": f"Bearer {token}"},
    json={"message": "What's your refund policy on the UltraBook Pro 15?"}
)
print(chat.json()["response"])
```

</details>

<details>
<summary><strong>JavaScript (fetch)</strong></summary>

```javascript
const BASE = "http://localhost:8000/api";

const login = await fetch(`${BASE}/auth/login`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email: "jane@example.com", password: "SecurePass123" }),
}).then((r) => r.json());

const chat = await fetch(`${BASE}/chat`, {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    Authorization: `Bearer ${login.access_token}`,
  },
  body: JSON.stringify({ message: "Do you ship to Canada?" }),
}).then((r) => r.json());

console.log(chat.response);
```

</details>

---

## Example Usage

| Customer Message | Detected Intent | Sentiment | Routed Agent |
|---|---|---|---|
| "How much does the Care Pro plan cost per month?" | `billing` | neutral | Billing Support |
| "My TabPro 11 won't connect to WiFi" | `technical` | negative | Technical Support |
| "What's the difference between the X14 and X14 Pro?" | `product` | neutral | Product Specialist |
| "This is ridiculous, I've asked twice and still no refund!" | `refund` | frustrated | Billing Support + empathy line from Customer Relations |
| "What are your business hours?" | `faq` | neutral | Support Assistant |

---

## Notifications (Email & WhatsApp)

- **Email**: `send_email()` first attempts the SendGrid HTTP API (`SENDGRID_API_KEY`); if that key isn't set, it falls back to SMTP using `SMTP_HOST`/`SMTP_USER`/`SMTP_PASSWORD`. All send calls are best-effort — failures are logged, not raised, so a notification failure never breaks the chat response.
- **WhatsApp**: `send_whatsapp()` uses the Twilio SDK. `is_whatsapp_configured()` additionally checks that `TWILIO_ACCOUNT_SID` starts with `"AC"` as a basic sanity check. WhatsApp notifications are only attempted if the user has a `phone` on file.
- Both are triggered automatically when a message's intent is `complaint` or sentiment is `frustrated`/`negative` (auto-ticket creation), and again on manual `/api/escalate` calls.

---

## Deployment

**Live app:** [https://techmart-ai-support.vercel.app/](https://techmart-ai-support.vercel.app/)

### Backend — Render

The included `render.yaml` defines a `python` web service:

```yaml
buildCommand: pip install -r requirements.txt
startCommand: uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

Set the marked `sync: false` environment variables (`DATABASE_URL`, `SECRET_KEY`, `GROQ_API_KEY`, SMTP/Twilio credentials, etc.) in the Render dashboard rather than committing them.

### Frontend — Vercel

The Next.js frontend (`frontend/`) is deployed on Vercel at [techmart-ai-support.vercel.app](https://techmart-ai-support.vercel.app/), pointing `NEXT_PUBLIC_API_URL` at the Render backend's `/api` base URL. `backend/main.py`'s CORS configuration allowlists this Vercel origin alongside the Render backend URL.

Alternatively, `backend/main.py` will serve a static Next.js export from `frontend/out/` if that directory exists (`app.mount("/", StaticFiles(...))`), allowing a single-service deployment.

---

## Contributing

Contributions are welcome.

1. Fork the repository and create a feature branch: `git checkout -b feature/my-feature`
2. Make your changes, keeping to the existing code style (agents subclass `BaseAgent`; new endpoints go in `routes.py` with a matching Pydantic schema in `schemas.py`)
3. Test locally against a running backend + frontend
4. Commit with a clear message and open a pull request describing the change and motivation

Please open an issue first for significant architectural changes (e.g. new agent types, storage backends) so the approach can be discussed before implementation.

---

## Acknowledgements

- [FastAPI](https://fastapi.tiangolo.com/) — backend web framework
- [Next.js](https://nextjs.org/) — frontend framework
- [FAISS](https://github.com/facebookresearch/faiss) (Meta AI) — vector similarity search
- [Sentence-Transformers](https://www.sbert.net/) — embedding models
- [Groq](https://groq.com/) / [OpenAI](https://openai.com/) — LLM inference providers
- [SQLAlchemy](https://www.sqlalchemy.org/) — ORM
- [Twilio](https://www.twilio.com/) — WhatsApp messaging
- [SendGrid](https://sendgrid.com/) — transactional email

---

## FAQ

<details>
<summary><strong>Do I need an LLM API key to run this?</strong></summary>

No. If `LLM_PROVIDER` is unset or the corresponding API key is missing, `LLMClient._get_client()` returns `None` and the app falls back to static, intent-keyed template responses defined in `llm_client.py`. This lets you run and demo the full app (auth, sessions, routing, tickets) without any external API cost.
</details>

<details>
<summary><strong>Which LLM providers are supported?</strong></summary>

Groq (default), OpenAI, and local Ollama — all accessed through the same `AsyncOpenAI`-compatible client, since all three expose OpenAI-compatible chat completion endpoints. Set `LLM_PROVIDER` accordingly in `.env`.
</details>

<details>
<summary><strong>How do I add a new knowledge-base document?</strong></summary>

Either drop a `.txt` file into `knowledge_base/` and re-run `python setup.py` (rebuilds the index locally), or, on a running server, use `POST /api/admin/knowledge-base/upload` followed by `POST /api/admin/knowledge-base/rebuild` (both admin-only).
</details>

<details>
<summary><strong>Why SQLite by default instead of PostgreSQL?</strong></summary>

SQLite requires no external setup, which keeps local development and demos frictionless. Setting `DATABASE_URL` to a PostgreSQL connection string switches the engine automatically — see `backend/database/db.py`.
</details>

<details>
<summary><strong>Why does the FAISS index not rebuild automatically on server startup?</strong></summary>

`backend/main.py`'s lifespan hook only reloads a previously-built index from disk to keep startup memory usage low. The index builds lazily on first use if no saved index is found, or via the admin rebuild endpoint.
</details>

<details>
<summary><strong>How does the app decide which language to reply in?</strong></summary>

`BaseAgent._detect_language()` checks Unicode character ranges (Devanagari, CJK, Hiragana/Katakana, Arabic) and common-word heuristics for Spanish/French/German, based only on the current message — not the conversation history — so replies always track what the customer just typed.
</details>

<details>
<summary><strong>Is there rate limiting?</strong></summary>

Yes — 20 messages per minute per user, enforced in `routes.py`.
</details>

<details>
<summary><strong>How are support tickets created?</strong></summary>

Automatically, whenever a chat message's detected intent is `complaint` or its sentiment is `frustrated`/`negative` (see the ticket-creation block in `POST /api/chat`). Tickets can also be created manually via `POST /api/tickets/create`.
</details>

<details>
<summary><strong>Can I deploy the backend and frontend as a single service?</strong></summary>

Yes. `backend/main.py` mounts a static file server at `/` if `frontend/out/` exists (a Next.js static export), so `next build && next export` followed by copying `out/` alongside the backend allows single-service hosting.
</details>

<details>
<summary><strong>What happens if the LLM call fails mid-request?</strong></summary>

`LLMClient.chat()` retries up to 3 times with increasing backoff (2s, then 4s). If all attempts fail, it falls back to the same static template responses used in mock mode, keyed off the last user message's keywords.
</details>

---

## Troubleshooting

| Issue | Possible Cause | Solution |
|---|---|---|
| `ValueError: SECRET_KEY environment variable is required` on startup | `.env` missing or `SECRET_KEY` not set | Add `SECRET_KEY=<random string>` to `.env` |
| `rag_ready: false` in `/api/health` | FAISS index not yet built | Run `python setup.py`, or call `POST /api/admin/knowledge-base/rebuild` as an admin |
| Chat responses are generic/templated regardless of question | No LLM provider configured, or API key invalid | Check `LLM_PROVIDER` and the matching `*_API_KEY` in `.env`; check backend logs for `LLM attempt` warnings |
| `401 Unauthorized` on every request | Missing or expired JWT | Re-authenticate via `/api/auth/login`; confirm the frontend is sending `Authorization: Bearer <token>` |
| `429 Too Many Requests` | Rate limit hit (20 msgs/min) | Wait ~1 minute, or raise `max_messages` in `check_rate_limit` for local testing |
| WhatsApp notifications never send | Twilio not configured, or user has no phone on file | Check `GET /api/whatsapp/status`; ensure `TWILIO_ACCOUNT_SID` starts with `AC` |
| Emails never send | Neither `SENDGRID_API_KEY` nor SMTP credentials set | Check `GET /api/email/status`; set `SENDGRID_API_KEY` or `SMTP_USER`/`SMTP_PASSWORD` |
| `ImportError` around `openai`, `faiss`, or `sentence_transformers` | Dependencies not installed / wrong virtualenv active | Re-run `pip install -r requirements.txt` inside the activated venv |
| Frontend can't reach backend (CORS error) | Frontend origin not in `allow_origins` | Add your frontend URL to the CORS list in `backend/main.py` |
| Slow first response after a cold start | Embedding model loading lazily on first RAG query | Expected behavior — subsequent requests reuse the loaded model |

---

<div align="center">

Built with FastAPI, Next.js, FAISS, and Sentence-Transformers.

**[Live Demo](https://techmart-ai-support.vercel.app/)**

</div>

---

# Author

**MOHIT SINGH RAJPUT — AI/ML Engineer**

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=flat-square&logo=linkedin&logoColor=white)](https://linkedin.com/in/mohitsingh1307)
[![GitHub](https://img.shields.io/badge/GitHub-121011?style=flat-square&logo=github&logoColor=white)](https://github.com/Mohit-1307)
[![Kaggle](https://img.shields.io/badge/Kaggle-20BEFF?style=flat-square&logo=kaggle&logoColor=white)](https://www.kaggle.com/mohitsinghrajput1307)
[![Email](https://img.shields.io/badge/Email-D14836?style=flat-square&logo=gmail&logoColor=white)](mailto:mohitsinghdausa@gmail.com)

---

<div align="center">

_If this project was useful, a ⭐ on the repository is appreciated._

</div>
