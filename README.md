# HCP CRM - Log Interaction Module

This project is my implementation of the **Log Interaction Screen** for an AI-first Healthcare CRM.

The application allows a medical representative to record interactions with Healthcare Professionals (HCPs). Users can either fill a normal form or simply chat with the AI assistant. Both methods create the same interaction record.

---

## Project Structure

```
hcp-crm/
├── backend/
│   ├── requirements.txt
│   ├── .env.example
│   └── app/
│       ├── main.py              # FastAPI app entrypoint, CORS, router setup
│       ├── config.py            # Loads settings from .env
│       ├── database.py          # SQLAlchemy engine/session (MySQL)
│       ├── models.py            # HCP, Interaction, Material, Sample tables
│       ├── schemas.py           # Pydantic request/response models
│       ├── agent/
│       │   ├── llm.py           # Groq model setup
│       │   ├── tools.py         # The 5 LangGraph tools
│       │   └── graph.py         # The LangGraph state graph
│       └── routers/
│           ├── interactions.py  # CRUD endpoints for the structured form
│           ├── chat.py          # Chat endpoint that drives the agent
│           └── hcps.py          # HCP search endpoint
├── frontend/
│   ├── package.json
│   ├── .env.example
│   └── src/
│       ├── App.jsx
│       ├── api/client.js        # Talks to the FastAPI backend
│       ├── store/                # Redux Toolkit slice (form + chat state)
│       └── components/
│           ├── LogInteractionScreen.jsx
│           ├── StructuredForm.jsx
│           └── AIChatPanel.jsx
└── README.md
```

---

# Project Overview

The purpose of this project is to make interaction logging easier.

Instead of filling every field manually, the representative can simply describe the meeting. The AI understands the conversation, extracts important details, and automatically fills the interaction form.

The user can always review and edit the information before saving it.

There are two ways to log an interaction, and **both write to the exact same interaction record** — a rep can start with one method and finish with the other.

### 1. Form Based Logging

The user manually fills information like:

- HCP Name
- Interaction Type
- Date & Time
- Attendees
- Topics Discussed
- Materials Shared
- Samples Distributed
- Sentiment
- Outcomes
- Follow-up Actions

### 2. AI Chat Logging

Instead of filling the form, the user can simply type something like:

```text
Met Dr. Sharma today, discussed Product X efficacy data, she was positive about it, I left a brochure and 2 samples, she wants a follow-up in 2 weeks.
```

The AI automatically extracts the important information and fills the form.

---

# Role of the LangGraph Agent

The agent sits behind the chat panel and is responsible for turning a rep's free-text description into a structured, saved record.

It is built as a **LangGraph state graph** rather than a single LLM call, because logging an interaction is rarely a one-step job. A single message might need the agent to look up an HCP's past visits, extract and save the new interaction, and then propose follow-up actions — three separate actions, each needing a different tool, before the agent is ready to reply.

The graph has two nodes:

- **Agent node** — reads the conversation and decides whether it has enough information to reply, or needs to call a tool.
- **Tools node** — actually executes whichever tool the agent asked for (the tool is what touches the database, not the agent itself), and passes the result back.

These two nodes loop together: agent → tool → agent → tool, for as many steps as needed, until the agent has nothing left to do and produces a final plain-language reply. This loop is what lets one chat message like *"log this meeting and tell me what to do next"* result in multiple tools firing in sequence, automatically.

## Workflow summary

1. User sends a message.
2. The agent node decides what needs to happen.
3. Required tools are executed (these are the only part that reads/writes the database).
4. Database is updated.
5. The agent loops back and either calls another tool or sends a final response.
6. The interaction form on the frontend updates automatically to match what was saved.

![LangGraph agent flow](1A.png)

---

# LangGraph Tools

The project uses five tools.

## 1. Log Interaction

Creates a new interaction record.

### Example

```text
Met Dr. Sharma today, discussed Product X efficacy data, she was positive about it, I left a brochure and 2 samples, she wants a follow-up in 2 weeks.
```

The AI extracts:

- HCP Name
- Topics Discussed
- Sentiment
- Materials Shared
- Samples Distributed
- Follow-up Actions

and saves everything into the database. If the date isn't mentioned, it defaults to today automatically rather than being guessed.

---

## 2. Edit Interaction

Updates an existing interaction.

### Example

```text
Actually, change the sentiment to Negative instead.
```

The AI finds the correct interaction — either from context earlier in the conversation, or by matching the HCP's most recently logged visit if no specific record was mentioned — and updates only the requested field.

---

## 3. Search HCP History

Searches previous meetings with an HCP.

### Example

```text
I'm heading to see Dr. Sharma again — what did we cover last time?
```

The AI returns previous interaction details to help prepare for the next visit.

---

## 4. Search Materials and Samples

Searches available brochures and samples.

### Example

```text
What materials do we have for Product X?
```

The AI returns matching materials directly from the approved catalog in the database, so only real, compliant items ever get recorded as shared.

---

## 5. Suggest Follow Ups

Generates follow-up recommendations.

### Example

```text
Based on today's meeting with Dr. Sharma, what should my next steps be?
```

Example suggestions:

- Schedule another meeting
- Share additional product information
- Send clinical documents

---

# AI Models Used

This project uses two Groq models.

### gemma2-9b-it

Used as the main model for:

- Understanding user messages
- Calling LangGraph tools
- Extracting structured data
- Generating responses

### llama-3.3-70b-versatile

Used for:

- Generating follow-up suggestions, since it benefits from a bit more reasoning than the fast tool-calling model

---

# Tech Stack

### Frontend

- React
- Redux Toolkit
- Vite

### Backend

- FastAPI
- Python

### AI

- LangGraph
- Groq API

### Database

- MySQL

---

# Running the Project

## Backend

```bash
cd backend

python -m venv .venv

# Activate the virtual environment before installing anything
source .venv/bin/activate      # Windows: .venv\Scripts\activate

pip install -r requirements.txt

# Copy the example env file and fill in your own values
cp .env.example .env
```

Then edit `.env` and set:

```
GROQ_API_KEY=your_groq_api_key_here
DATABASE_URL=mysql+pymysql://hcp_user:hcp_pass@localhost:3306/hcp_crm
```

Start the server:

```bash
uvicorn app.main:app --reload
```

Database tables are created automatically on first run.

---

## Frontend

```bash
cd frontend

npm install

cp .env.example .env
```

The frontend `.env` should point at the backend:

```
VITE_API_BASE_URL=http://localhost:8000
```

Start the dev server:

```bash
npm run dev
```

Open:

```
http://localhost:5173
```

---

# API Endpoints

| Method | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/interactions` | Create interaction |
| GET | `/api/interactions` | Get all interactions |
| PATCH | `/api/interactions/{id}` | Update interaction |
| DELETE | `/api/interactions/{id}` | Delete interaction |
| GET | `/api/hcps` | Search HCP |
| POST | `/api/chat` | Chat with AI |

---

# Conclusion

This project demonstrates how an AI agent can simplify interaction logging in a Healthcare CRM. Instead of manually filling every field, the representative can simply describe the meeting, and the AI organizes the information into structured data while still allowing manual edits before saving.
