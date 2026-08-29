<p align="center">
  <h1 align="center">🎙️ VoiceActions AI</h1>
  <p align="center"><strong>Speak messy. Get clarity.</strong></p>
  <p align="center"><em>A multi-model AI pipeline that turns chaotic voice notes into structured action items — and catches your contradictions before your team does.</em></p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Next.js-16-black?logo=next.js" alt="Next.js 16" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Gemini-Flash_Lite-4285F4?logo=google" alt="Gemini" />
  <img src="https://img.shields.io/badge/Groq-Whisper_+_Qwen_27B-F55036?logo=groq" alt="Groq" />
  <img src="https://img.shields.io/badge/Supabase-pgvector-3ECF8E?logo=supabase" alt="Supabase" />
</p>

  Live link - https://voice-actions-fjvg3zmgo-hanshraj317-4511s-projects.vercel.app/

---

## 📋 Table of Contents

- [The Problem](#-the-problem)
- [Our Solution](#-our-solution)
- [How It Works — The Pipeline](#-how-it-works--the-pipeline)
- [Tech Stack — 8 Layers Deep](#-tech-stack--8-layers-deep)
- [Project Structure](#-project-structure)
- [Quick Start](#-quick-start)
- [API Endpoints](#-api-endpoints)
- [Why Two Models? (Trust & Safety)](#-why-two-models-trust--safety)
- [What Makes This Original](#-what-makes-this-original)
- [Eval Harness](#-eval-harness)
- [Deployment](#-deployment)
- [Failure Awareness](#-failure-awareness)
- [Future Roadmap](#-future-roadmap)

---
<img width="1917" height="873" alt="image" src="https://github.com/user-attachments/assets/fea4258b-7920-472e-a8f2-eaa34430d481" />


## 🎯 The Problem

**Meet Ankit.** He's a startup founder who sends **20 voice notes a day** to his 8-person team. Half of them contradict each other:

> *"Send the client report today"* → 10 minutes later → *"Actually, hold off on the report until Friday"*

His team wastes **2+ hours daily** figuring out which instruction to follow. They build the wrong thing, miss deadlines, and nobody knows who's responsible for what.

**This isn't just Ankit.** This is every team lead, project manager, and founder who thinks out loud.

### The Core Insight

> Existing tools (Otter.ai, Notion AI, Fireflies) **transcribe** meetings — but they don't **catch contradictions**. They turn your messy voice into messy text. We turn it into **structured, verified, conflict-checked action items**.

---

## 💡 Our Solution

VoiceActions AI is a **voice-to-action pipeline** that does 3 things no other tool does simultaneously:

| Feature | What It Does | Why It Matters |
|---------|-------------|---------------|
| **🎯 Action Extraction** | Pulls structured tasks with owner, deadline, priority | No more "what did he say?" |
| **⚠️ Conflict Detection** | Catches contradicting instructions side-by-side | No more "which one do I follow?" |
| **🔍 Two-Model Verification** | A second AI audits the first AI's work | No more blindly trusting one model |

### 3 Input Modes

| Mode | Use Case |
|------|---------|
| 🎤 **Voice** | Record directly in browser (with live preview) |
| 📄 **Document** | Upload meeting notes as text files |
| ⌨️ **Text** | Paste or type raw notes directly |

---

## ⚙️ How It Works — The Pipeline

```
Voice Note / Text Input
        │
        ▼
┌──────────────────────┐
│  STEP 1: TRANSCRIBE  │ ← Groq Whisper (whisper-large-v3)
│  Audio → Text        │   Handles English, Hindi, code-mixed
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  STEP 2: ANALYZE     │ ← Google Gemini Flash Lite
│  Text → Structured   │   Extracts: actions, conflicts,
│  JSON Output         │   ambiguities, confidence score
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  STEP 3: VERIFY      │ ← Groq Qwen 27B (independent audit)
│  Cross-check output  │   Finds: missed actions, false conflicts,
│  of Step 2           │   adjusts confidence score up/down
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  STEP 4: STORE       │ ← Supabase PostgreSQL + pgvector
│  Persist + embed     │   Stores results + 768-dim vectors
│  for semantic search │   for future semantic search
└──────────────────────┘
```

### Real Example

**Input (voice note):**
> *"Tell Riya to send the client report by Thursday. Also tell Amit to hold off on sending any client docs until we review them internally."*

**Output:**

| # | Action | Owner | Deadline | Priority |
|---|--------|-------|----------|----------|
| 1 | Send the client report | Riya | Thursday | High |
| 2 | Hold off on sending client docs until internal review | Amit | Not specified | Medium |

**⚠️ Conflict Detected:**
> Action 1 says **send** client docs. Action 2 says **hold off** on client docs. These instructions contradict each other. Affected: Riya, Amit.

**🔍 Verification Audit (Qwen 27B):**
> Confirmed conflict. Confidence adjusted from 92% → 74% due to contradicting instructions.

---

## 🏗️ Tech Stack — 8 Layers Deep

| # | Layer | Technology | What It Does |
|---|-------|-----------|-------------|
| 1 | **AI Models** | Groq Whisper + Gemini Flash Lite + Qwen 27B | Three models: transcribe → analyze → verify |
| 2 | **Agent Orchestration** | Hand-built async pipeline (NOT LangChain) | Retries, fallbacks, decision trace — zero framework overhead |
| 3 | **Retrieval (RAG)** | Supabase pgvector + Gemini Embeddings | Semantic search over past action items using cosine similarity |
| 4 | **Frontend** | Next.js 16 + TypeScript | Real-time streaming UI, 3 input modes, glassmorphism design |
| 5 | **Backend** | FastAPI (Python) | NDJSON streaming, async pipeline, CORS-ready REST API |
| 6 | **Database** | Supabase PostgreSQL + Storage | Persistent storage for notes, actions, conflicts, audio files |
| 7 | **On-Device** | Web Speech API | Live transcription preview in browser before server processes |
| 8 | **Observability** | Custom eval harness + cost tracker | Per-step token count, latency, cost tracking, 20-test eval suite |

### Why NOT LangChain?

We built the orchestrator from scratch because:
- **No abstraction tax** — we control every retry, fallback, and timeout
- **Transparent decision trace** — every model call is logged with tokens, cost, latency
- **Curveball-ready** — swapping a model = changing one line in `config.py`

---

## 📁 Project Structure

```
VoiceActions-AI/
├── backend/                    # FastAPI server
│   ├── main.py                 # API endpoints (streaming + sync)
│   ├── config.py               # All model configs, feature flags, pricing
│   ├── prompts.py              # System prompts for Gemini & Qwen
│   ├── pipeline/
│   │   └── orchestrator.py     # The 4-step async pipeline engine
│   ├── services/
│   │   ├── groq_service.py     # Whisper transcription + Qwen verification
│   │   ├── gemini_service.py   # Action extraction + conflict detection
│   │   ├── embedding_service.py# Gemini gemini-embedding-001 (768-dim)
│   │   └── supabase_service.py # Database CRUD + audio storage
│   ├── models/
│   │   └── schemas.py          # Pydantic models for type-safe data flow
│   ├── .env.example            # Environment variable template
│   ├── requirements.txt        # Python dependencies
│   └── render.yaml             # One-click Render deployment config
│
├── frontend/                   # Next.js 16 app
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx        # Main page — pipeline UI + smart demo mode
│   │   │   ├── history/        # Past voice notes & semantic search
│   │   │   └── layout.tsx      # Root layout with fonts + metadata
│   │   ├── components/
│   │   │   ├── AudioRecorder.tsx   # Mic recording + file upload + Web Speech
│   │   │   ├── StatusStepper.tsx   # Live pipeline progress indicator
│   │   │   ├── ActionCards.tsx     # Structured action item display
│   │   │   ├── ConflictAlerts.tsx  # Conflict detection cards
│   │   │   ├── AmbiguityFlags.tsx  # Ambiguity flag display
│   │   │   ├── ConfidenceBar.tsx   # Dual-model confidence gauge
│   │   │   ├── CostTracker.tsx     # Token + cost + latency breakdown
│   │   │   └── DecisionTrace.tsx   # Full pipeline decision log
│   │   └── lib/
│   │       └── api.ts          # Type-safe API client with streaming support
│   └── vercel.json             # One-click Vercel deployment config
│
├── eval/                       # Evaluation harness
│   ├── run_eval.py             # Automated 20-test evaluation runner
│   └── test_cases.json         # Test cases: clean, conflicts, Hindi, edge cases
│
├── supabase/
│   └── migrations/
│       └── 001_init.sql        # Database schema (pgvector + tables)
│
├── package.json                # Root — runs backend + frontend together
├── ARCHITECTURE.md             # System architecture with Mermaid diagram
├── FAILURE_LOG.md              # Honest failure documentation
└── HACKATHON_PITCH_GUIDE.md    # Pitch preparation & defense guide
```

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.10+** and **Node.js 18+**
- API keys for: [Groq](https://console.groq.com), [Google AI Studio](https://aistudio.google.com), [Supabase](https://supabase.com)

### 1. Clone & Install

```bash
git clone https://github.com/Hansh07/VoiceActions-AI.git
cd VoiceActions-AI
```

### 2. Backend Setup

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys:
#   GROQ_API_KEY=gsk_...
#   GEMINI_API_KEY=AI...
#   SUPABASE_URL=https://xxx.supabase.co
#   SUPABASE_KEY=eyJ...
```

### 3. Database Setup (Supabase)

1. Create a free project at [supabase.com](https://supabase.com)
2. Go to **SQL Editor** → paste and run `supabase/migrations/001_init.sql`
3. Go to **Storage** → create a bucket named `audio` (set to public)
4. Copy your **Project URL** and **anon key** into `backend/.env`

### 4. Frontend Setup

```bash
cd frontend
npm install
```

### 5. Run Everything (One Command)

```bash
# From the root directory:
npm run dev
```

This starts **both** the FastAPI backend (port 8000) and Next.js frontend (port 3000) simultaneously.

### 🎮 Demo Mode (No API Keys Needed)

The frontend works **without the backend running**. It includes a built-in smart demo that:
- Parses your text input into realistic action items
- Detects conflicts using rule-based matching
- Simulates the full pipeline with step-by-step progress

Just run `cd frontend && npm run dev` and try the **Text** input mode.

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check — returns app status |
| `GET` | `/health` | Feature flags and config status |
| `POST` | `/api/process` | **Main endpoint** — streams NDJSON pipeline events |
| `POST` | `/api/process-sync` | Synchronous version — returns complete result |
| `POST` | `/api/process-text` | Process raw text (skip transcription) |
| `POST` | `/api/process-batch` | **Multi-file upload** — transcribe + cross-analyze multiple audio files |
| `POST` | `/api/search` | Semantic search over past action items (pgvector) |
| `GET` | `/api/history` | Retrieve past voice notes with actions and conflicts |
| `GET` | `/api/config` | Feature flags and model config for frontend |

### Example: Process Text

```bash
curl -X POST http://localhost:8000/api/process-text \
  -H "Content-Type: application/json" \
  -d '{"text": "Tell Riya to send the report. Tell Amit to hold off on sending anything."}'
```

---

## 🛡️ Why Two Models? (Trust & Safety)

> *"One model being wrong is worse than no model at all."*

Most AI tools use a single model and present its output as truth. We don't.

### Our Verification Architecture

```
Gemini Flash Lite (Analyzer)          Qwen 27B (Auditor)
─────────────────────────         ─────────────────────────
Extracts actions, conflicts,      Reviews Gemini's output and:
ambiguities from transcript  →    ✓ Finds missed action items
                                  ✓ Flags false conflicts
                                  ✓ Discovers missed conflicts
                                  ✓ Adjusts confidence score
```

### Why This Matters

| Scenario | Single-Model Approach | Our Two-Model Approach |
|----------|----------------------|----------------------|
| Model hallucinates a conflict | User sees fake conflict, takes wrong action | Auditor catches it: *"This is not actually a conflict"* |
| Model misses a real conflict | User never knows about contradiction | Auditor flags it: *"These two instructions conflict"* |
| Model is uncertain | Presents 90% confidence anyway | Confidence drops to reflect real uncertainty |

### Confidence Score System

- **> 85%** — High confidence, both models agree
- **70-85%** — Partial agreement, review recommended
- **< 70%** — Significant disagreement, manual review needed

---

## 🔥 What Makes This Original

| Claim | Evidence |
|-------|---------|
| **Couldn't exist in 2023** | Groq Whisper, Gemini Flash Lite, and Qwen 27B on Groq are all 2024+ releases |
| **Not a wrapper** | Hand-built orchestrator with retries, fallbacks, decision trace — zero LangChain |
| **Two-model verification** | Model A extracts → Model B audits → confidence score adjusts — a 2024+ pattern |
| **Conflict detection** | No existing tool detects contradictions within a single speaker's voice notes |
| **Full observability** | Every step logs: model used, tokens in/out, latency, cost, retry count |

---

## 📊 Eval Harness

We built a 20-test automated evaluation suite:

```bash
cd eval
python run_eval.py --all
```

### Test Categories

| Category | # Tests | What It Validates |
|----------|---------|------------------|
| Clean notes | 5 | Basic action extraction accuracy |
| Conflicting instructions | 5 | Conflict detection precision |
| Hindi-English mixed | 3 | Multilingual handling |
| Ambiguous input | 3 | Ambiguity flagging |
| Edge cases | 2 | Empty input, single word, etc. |
| Adversarial | 2 | Prompt injection resistance |

---

## 🌐 Deployment

### Frontend → Vercel

```bash
# vercel.json is pre-configured
cd frontend
npx vercel --prod
```

Set environment variable:
- `NEXT_PUBLIC_API_URL` = your Render backend URL

### Backend → Render

```bash
# render.yaml is pre-configured
# Push to GitHub → connect repo in Render dashboard
```

Set environment variables in Render:
- `GROQ_API_KEY`
- `GEMINI_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_KEY`

---

## ⚠️ Failure Awareness

> We document what's broken because trust requires honesty. Full details in [`FAILURE_LOG.md`](FAILURE_LOG.md).

| Issue | Impact | Fix Cost |
|-------|--------|----------|
| Mic needs HTTPS | Voice mode fails on HTTP | 30 min (deploy to Vercel) |
| No authentication | No user isolation | 3 hours (Supabase Auth) |
| Prompt injection | Adversarial input can manipulate output | 2 hours (input sanitization) |
| Hinglish WER ~15-20% higher | Some code-mixed words garbled | 1 day (normalization layer) |
| Gemini rate limits (15 RPM free) | Breaks with 3+ concurrent users | $0.01/query (pay-as-you-go) |
| Verifier sometimes disagrees incorrectly | ~10% of edge-case conflicts misclassified | 1 day (few-shot prompting) |

---

## 🗺️ Future Roadmap

| Feature | Effort | Impact |
|---------|--------|--------|
| Real-time WebSocket streaming | 4 hours | Smoother live progress |
| PDF / DOCX parsing | 2 hours | More document types |
| Supabase Auth + multi-user | 3 hours | Production-ready |
| Slack / WhatsApp integration | 1 day | Action items → team chat |
| Mobile PWA | 2 hours | Record from phone |
| Fine-tuned conflict classifier | 3 days | Higher edge-case accuracy |

---

## 🧑‍💻 Built By

**Hansh Raj** & **Utkarsh** — Built with ❤️ for the VocaLabs AI 24-Hour Hackathon

---

<p align="center">
  <strong>🎙️ Stop sending confusing voice notes. Start sending clarity.</strong>
</p>
