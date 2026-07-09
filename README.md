# AI-First HCP CRM — Log Interaction Module

A conceptual + working implementation of the **Log HCP Interaction** screen for an
AI-first CRM, built for field reps to log visits with healthcare professionals
(HCPs) either through a **structured form** or a **conversational AI chat**
panel, backed by a **LangGraph** agent running on **Groq**.

```
hcp-crm/
├── backend/     FastAPI + LangGraph + SQLAlchemy (Postgres/MySQL)
├── frontend/    React + Redux Toolkit
└── README.md
```

---

## 1. Product concept

A rep can log an interaction two ways, and both write to the *same* record:

- **Structured form** — explicit fields (HCP, type, date, attendees, topics,
  materials/samples, sentiment, outcomes, follow-ups).
- **Chat with the AI Assistant** — the rep just types (or pastes a voice-note
  transcript of) what happened, e.g.:
  > "Met Dr. Sharma today, discussed Product X efficacy data, she was
  > positive, left a brochure and 2 samples, wants a follow-up in 2 weeks."

  The agent extracts every structured field itself, logs the interaction, and
  the form on the left updates live — fields the AI just filled are
  highlighted with a teal "AI" tag so the rep can see and correct what was
  captured before saving.

---

## 2. LangGraph AI Agent — role & design

**Role.** The agent is the reasoning layer behind the chat panel. It is not a
single LLM call — it's a small graph that can decide to look things up, take
an action, and loop back to itself before replying, so it behaves like an
assistant rather than a form-autofill script:

```
        START
          │
          ▼
      [ agent ]  <───────────┐
          │                   │
     tool_calls?              │
      /        \              │
    yes         no             │
     │           │             │
     ▼           ▼             │
  [ tools ] ─────'──────────────┘
      (results are appended to the
       message state, looped back
       into the agent node)
          │
          ▼
         END
```

- **`agent` node** — `gemma2-9b-it` (Groq) with the 6 tools below bound to it.
  It reads the running conversation, decides whether it has enough
  information to act, and either calls a tool or replies in natural language.
- **`tools` node** — a LangGraph `ToolNode` that executes whichever tool(s)
  the model requested, writes the result back into the message list, and
  routes back to `agent` so it can use that result (e.g. call
  `search_hcp_history` first, then `log_interaction`).
- The loop lets the agent chain actions in one turn: *look up context →
  extract & log → suggest follow-ups → reply* — all before the rep sees a
  response.

This is implemented directly with `langgraph.graph.StateGraph` (see
`backend/app/agent/graph.py`) rather than only a prebuilt helper, so the
state, routing, and system prompt are explicit and easy to extend.

### The 6 tools

| # | Tool | Purpose |
|---|------|---------|
| 1 | **`log_interaction`** *(required)* | Persists a new interaction. The LLM extracts HCP name, interaction type, date, attendees, topics, sentiment, materials/samples, outcomes and follow-ups from free text, then calls this tool with structured arguments. The tool creates the HCP record if new, writes the `Interaction` row plus child `InteractionMaterial`/`InteractionSample` rows, and returns the new `interaction_id` so the frontend can sync the structured form. |
| 2 | **`edit_interaction`** *(required)* | Lets the rep correct a just-logged (or older) record conversationally — "actually make that Negative sentiment" — by passing `interaction_id`, the `field` to change, and the `new_value`. Restricted to a whitelist of editable fields. |
| 3 | **`search_hcp_history`** | Looks up an HCP's recent past interactions so the agent can avoid repeating stale talking points, or notice something worth flagging (e.g. "last visit was also about pricing"). |
| 4 | **`search_materials_and_samples`** | Searches the approved materials/sample catalog by keyword, so only compliant, cataloged items get recorded as shared/distributed. |
| 5 | **`suggest_follow_ups`** | Uses the larger `llama-3.3-70b-versatile` model to propose 2–4 concrete next-step actions from the topics/sentiment/outcomes — rendered in the UI as "AI Suggested Follow-ups". |
| 6 | **`summarize_voice_note`** | Condenses a raw dictated transcript (behind the "Summarize from Voice Note — Requires Consent" control) into a clean `topics_discussed` summary before logging. |

`log_interaction` and `search_follow_ups`/`suggest_follow_ups` intentionally
use two different Groq models: **`gemma2-9b-it`** is the fast, tool-calling
driver for the whole agent loop (cheap, low-latency, good enough for
structured extraction), while **`llama-3.3-70b-versatile`** is reserved for
the two tasks that benefit from more reasoning/context (summarizing a long
voice note, drafting nuanced follow-up suggestions).

---

## 3. Tech stack (per spec)

| Layer | Choice |
|---|---|
| Frontend | React + Redux Toolkit (Vite) |
| Backend | Python, FastAPI |
| AI agent framework | LangGraph |
| LLMs | Groq — `gemma2-9b-it` (primary/tool-calling), `llama-3.3-70b-versatile` (context tasks) |
| Database | SQLAlchemy ORM, Postgres or MySQL via `DATABASE_URL` (SQLite fallback for local dev — see below) |
| Font | Google **Inter** |

> **DB note:** `DATABASE_URL` is the only thing that changes between
> Postgres/MySQL/SQLite because everything is behind SQLAlchemy's engine —
> see `backend/.env.example` for both connection string formats. SQLite is
> the zero-setup default so the app runs immediately for local testing; swap
> in a real Postgres/MySQL URL for grading/deployment.

---

## 4. Running it locally

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # add your GROQ_API_KEY, set DATABASE_URL
uvicorn app.main:app --reload --port 8000
```

Tables are auto-created on first run via `Base.metadata.create_all`. API docs
at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env        # points VITE_API_BASE_URL at the backend
npm run dev
```

Open `http://localhost:5173`.

---

## 5. API surface

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/interactions` | Create an interaction from the structured form |
| `GET` | `/api/interactions?hcp_name=` | List interactions, optionally filtered by HCP |
| `PATCH` | `/api/interactions/{id}` | Edit a field on an existing interaction |
| `DELETE` | `/api/interactions/{id}` | Delete an interaction |
| `GET` | `/api/hcps?q=` | Search/autocomplete HCPs |
| `POST` | `/api/chat` | Send a chat message to the LangGraph agent; returns the reply, which tools fired, the synced interaction record, and any follow-up suggestions |

---

## 6. What I understood the task to be

Design and build the "Log Interaction" screen of an AI-first CRM's HCP
module: a dual-mode (form + chat) logger, backed by a real LangGraph agent —
not just a single LLM prompt — with distinct tools for writing, editing, and
enriching interaction records, wired to Groq-hosted models, on a
React/Redux frontend and a FastAPI/SQL backend. The emphasis throughout was
on the agent actually *doing the CRM's data-entry and compliance work*
(cataloged materials/samples, editable structured fields, HCP history
context) rather than just chatting about it.
