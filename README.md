# 🎙️ VoiceActions AI

> **Speak messy. Get clarity.**  
> *Because one model being wrong is worse than no model at all.*

---

## 🎯 Problem & Person (15%)

**Ankit**, a startup founder, sends 20 voice notes a day to his 8-person team. Half of them contradict each other — *"send the report"* in one breath, *"hold off on sending"* in the next. His team wastes 2 hours/day resolving conflicts he doesn't know he created.

**One-liner:** *"Startup founders who give contradicting verbal instructions and don't realize it until the team is already confused."*

---

## 💡 What It Does

Record a voice note **or** upload a document → we run it through a **two-model pipeline** that:

1. ✅ **Extracts structured action items** — owner, deadline, priority, source quote
2. ⚠️ **Detects conflicts** — catches contradicting instructions side by side
3. ❓ **Flags ambiguity** — refuses to guess when something is unclear
4. 🔍 **Cross-verifies with a second model** — Gemini analyzes, Llama audits
5. 📊 **Full observability** — tokens, cost, latency, decision trace per step

---

## 🔥 Why This Couldn't Exist in 2023 (Originality — 25%)

- **Groq Whisper** didn't exist — instant voice transcription wasn't possible
- **Gemini 2.0 Flash** didn't exist — cheap structured extraction at this quality
- **Two-model verification** as a pattern (Model A extracts, Model B audits) is a 2024+ paradigm
- Llama 3.3 70B on Groq = sub-second verification — not possible before

---

## 🏗️ Technical Depth (25%) — All 8 Hackathon Layers

| # | Layer | Technology | What We Built |
|---|-------|-----------|--------------|
| 1 | **Models** | Groq Whisper + Gemini Flash + Llama 3.3 70B | Two models that cross-verify each other's work |
| 2 | **Agent** | Hand-rolled orchestration | 5-step pipeline with retries, fallbacks, decision trace — NOT langchain |
| 3 | **Retrieval** | Supabase pgvector | Semantic search over past action items with Gemini embeddings |
| 4 | **Frontend** | Next.js 16 (TypeScript) | Streaming pipeline UI, 3 input modes (voice/doc/text) |
| 5 | **Backend** | FastAPI (Python) | NDJSON streaming, async pipeline, CORS-ready |
| 6 | **Data & Infra** | Supabase PostgreSQL + Storage | Persistent storage with embeddings, audio bucket |
| 7 | **On-device** | Web Speech API | Live transcription preview before server processing |
| 8 | **Observability** | Eval harness + cost tracker | 20-test eval suite, per-step token/cost/latency tracking |

---

## 🚀 Quick Start

### Backend
```bash
cd backend
pip install -r requirements.txt
# Create .env with: GROQ_API_KEY, GEMINI_API_KEY, SUPABASE_URL, SUPABASE_KEY
python main.py
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Database (Supabase)
1. Create project at https://supabase.com
2. Run `supabase/migrations/001_init.sql` in SQL Editor
3. Create Storage bucket named `audio` (public)
4. Copy URL + anon key to `backend/.env`

### Demo Mode
The frontend works **without the backend** — it simulates a realistic pipeline response with mock data. Just run `npm run dev` and click "Analyze Text →".

---

## 📐 Hackathon Constraints

- ✅ **Two models, not one** — Gemini Flash extracts, Llama 3.3 70B audits
- ✅ **Handle being wrong** — Confidence scores, refusal on ambiguity, verification audit, fallback chains
- ✅ **All 8 layers** — Models, Agent, Retrieval, Frontend, Backend, Data, On-device, Observability

---

## 📊 Eval Harness
```bash
cd eval
python run_eval.py --all
```
20 test cases: clean notes, conflicts, Hindi-English code-mixed, ambiguities, edge cases, adversarial inputs.

---

## ⚠️ Failure Awareness (15%)

See [`FAILURE_LOG.md`](FAILURE_LOG.md) for an honest account of what's broken, what we'd fix with more time, and what it would cost.

---

Built with ❤️ for the VocaLabs AI 24-Hour Hackathon
