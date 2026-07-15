# AI-First CRM — HCP Module: Log Interaction Screen

A prototype of the "Log Interaction Screen" for a Healthcare Professional (HCP)
CRM module, built for field sales reps. Users can log an interaction either
via a **structured form** or a **conversational chat interface**, both backed
by the same LangGraph agent + database.

## Tech stack

| Layer      | Choice |
|------------|--------|
| Frontend   | React + Redux Toolkit |
| Backend    | Python, FastAPI |
| AI agent   | LangGraph |
| LLMs       | Groq — `gemma2-9b-it` (chat/extraction), `llama-3.3-70b-versatile` (follow-up suggestions) |
| Database   | PostgreSQL (MySQL also supported via SQLAlchemy) |
| Font       | Google Inter |

## Project structure

```
hcp-crm/
├── backend/
│   ├── app/
│   │   ├── agent/
│   │   │   ├── llm.py        # Groq LLM clients
│   │   │   ├── tools.py      # the 5 LangGraph tools
│   │   │   └── graph.py      # the LangGraph agent graph itself
│   │   ├── routers/
│   │   │   ├── chat.py           # POST /api/chat  (conversational path)
│   │   │   └── interactions.py   # REST CRUD (structured-form path)
│   │   ├── database.py
│   │   ├── models.py         # SQLAlchemy models: HCP, Interaction
│   │   ├── schemas.py        # Pydantic request/response models
│   │   └── main.py           # FastAPI app entrypoint
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── LogInteractionForm.jsx   # structured form
    │   │   └── ChatPanel.jsx            # conversational panel
    │   ├── store/
    │   │   ├── interactionSlice.js      # Redux slice + thunks
    │   │   └── store.js
    │   ├── App.jsx
    │   └── index.css
    ├── index.html
    ├── package.json
    └── vite.config.js
```

## How to run

### 1. Database
Create a Postgres DB (or MySQL, adjust the URL):
```bash
createdb hcp_crm
```

### 2. Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then add your GROQ_API_KEY from console.groq.com/keys
uvicorn app.main:app --reload --port 8000
```
Tables are auto-created on first run via `Base.metadata.create_all`.

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
```
Visit `http://localhost:5173`. Vite proxies `/api/*` to the backend on `:8000`.

---

## LangGraph AI Agent & Tools — write-up

### Role of the LangGraph agent
The agent is the reasoning layer sitting behind the chat side of the Log
Interaction Screen. A field rep types (or dictates, transcribed to text) an
unstructured note about a visit or call. The agent's job is to:

1. **Interpret intent** — decide whether the rep wants to *log* a new
   interaction, *edit* one just logged, *look up* an HCP's history, or get
   *follow-up suggestions*.
2. **Route to the right tool** rather than trying to do extraction itself in
   one shot — each tool encapsulates a specific CRM operation and its own
   LLM sub-call for structured-data extraction.
3. **Turn tool output back into natural language** — the rep never sees raw
   JSON; they see a one-line confirmation ("Logged your meeting with Dr.
   Sharma — sentiment: positive. Two follow-ups suggested.").
4. **Keep state consistent** — both the structured form and the chat write to
   the same `Interaction` row in the DB, so switching between the two input
   modes never creates duplicate or conflicting records.

Graph shape (see `backend/app/agent/graph.py`): a minimal ReAct-style loop —
`agent` node (Groq LLM decides whether to call a tool) → `tools` node (LangGraph's
`ToolNode` executes it) → back to `agent` to summarize → `END`.

### The 5 tools

1. **`log_interaction`** *(required)* — Takes the rep's raw free text, sends
   it to the LLM with a strict JSON-extraction prompt to pull out HCP name,
   interaction type, attendees, topics, materials/samples, sentiment,
   outcomes, and follow-ups. Creates (or reuses) the `HCP` row, then inserts
   a new `Interaction` row with the extracted fields plus the original raw
   text (kept for audit/traceability).

2. **`edit_interaction`** *(required)* — Takes an `interaction_id` plus a
   natural-language instruction ("change sentiment to positive", "add that a
   brochure was shared"). The LLM diffs the instruction against the
   interaction's current JSON state and returns only the changed fields,
   which are merged into the existing row (`updated_at` bumped).

3. **`search_hcp`** — Partial-name lookup against the `HCP` table, powering
   the "Search or select HCP..." autocomplete field in both the form and chat.

4. **`get_interaction_history`** — Returns the last 5 interactions for a
   given HCP, so the agent (or rep) has context — e.g. "what did we discuss
   with Dr. Sharma last time" — before logging a new note or suggesting
   follow-ups.

5. **`suggest_followups`** — Given a logged interaction's topics/outcomes/
   sentiment, asks the LLM (llama-3.3-70b-versatile, for stronger reasoning)
   for 2-4 concrete next steps, and writes them to
   `ai_suggested_followups` — shown in the UI as the "AI Suggested
   Follow-ups" list under the form, matching the mockup.

### Why two models
`gemma2-9b-it` is fast/cheap and used for the interactive chat loop and
short structured-extraction calls where latency matters. The optional
`llama-3.3-70b-versatile` is used only for the follow-up-suggestion tool,
where slightly deeper reasoning over multiple past interactions produces
better-quality suggestions.

---

## What's intentionally simplified (given the 2-hour scope)
- Chat session history is kept in-memory per HCP name (`_SESSION_HISTORY` in
  `chat.py`) rather than in a real session store — noted in-code, easy swap
  for Redis in production.
- No auth layer — CRM would sit behind SSO in production.
- Voice-note transcription ("Summarize from Voice Note") is stubbed as a UI
  affordance; wiring an actual speech-to-text provider is a follow-up.
- Materials/Samples are free-text tags rather than a linked catalog table.
