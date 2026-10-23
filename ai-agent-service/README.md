# AI Agent Service

An agentic RAG customer-support agent for an e-commerce store, built with **LangGraph**.

A basic RAG searches once and trusts whatever it finds. This agent decides whether it needs to search at all, picks the right tool, checks whether the results actually answer the question, rewrites the query and retries when they don't, and hands off to the support team instead of making up an answer.

```
User question
     │
     ▼
ai-agent-service (this service)
     ├── Pinecone ─────────────► store policies (vector search)
     ├── core-backend-service ─► orders and refunds (port 8000)
     └── Tavily ───────────────► web search (fallback only)
```

## How the graph works

```
START ──► agent ──(tool needed?)──┬── no ──► END
            ▲                     └── yes ─► tools ──► grade_documents
            │                                               │
            │◄──────── relevant / skip / exhausted ─────────┤
            │                                               │
            └──── rewrite_query ◄─────── irrelevant ────────┘
```

1. **agent**: the LLM (`gpt-4o-mini`) decides whether to answer directly or call a tool.
2. **tools**: runs the chosen tool: policy search, order lookup or refund.
3. **grade_documents**: checks whether the policy search results answer the question. Order and refund results skip grading.
4. **rewrite_query**: if the results are irrelevant, writes a better search query and sends it back to the agent. Up to 2 retries.
5. **Fallback**: when retries run out, a classifier decides whether the question is general (the agent may use web search) or store-specific (the agent tells the user to contact support, with its tools disabled).

This grade → rewrite → retry loop is a **Corrective RAG (CRAG)** pattern.

## Tech stack

- **LangGraph**: the agent graph
- **LangChain + OpenAI**: `gpt-4o-mini` for reasoning, `text-embedding-3-small` for embeddings
- **Pinecone**: vector database for store policies
- **Tavily**: web search fallback
- **FastAPI**: chat API
- **httpx**: calls to the core backend

## Prerequisites

- Python 3.12 or newer
- API keys for **OpenAI** (with billing credits), **Pinecone**, and optionally **Tavily**
- **core-backend-service** set up and running on port `8000` (see its README)

## Setup

All commands below are for **Windows PowerShell**. On macOS/Linux, activate the virtual environment with `source .venv/bin/activate` instead.

### 1. Create a virtual environment and install packages

```powershell
cd ai-agent-service
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

### 2. Create the `.env` file

Create a file named `.env` in the `ai-agent-service` folder:

```env
OPENAI_API_KEY=sk-...
PINECONE_API_KEY=pcsk_...
PINECONE_INDEX_NAME=ecommerce-policies
TAVILY_API_KEY=tvly-...
CORE_BACKEND_URL=http://127.0.0.1:8000/api/v1
```

- Fill in **every** line. An empty line such as `PINECONE_INDEX_NAME=` overrides the default value in the code with an empty string, and the agent fails.
- `TAVILY_API_KEY` is optional. Without it, the web search fallback replies that web search is unavailable.
- Never commit this file.

### 3. Load the store policies into Pinecone

```powershell
python -m app.rag.ingest
```

This creates the `ecommerce-policies` index (1536 dimensions, cosine) if it doesn't exist, embeds the 4 policy documents (returns, cancellations, shipping, warranty) and uploads them. You only need to run it once.

> Run it with `python -m`, not `python app/rag/ingest.py`, or the `app` imports will fail.

### 4. Start the core backend

In a **separate terminal**, start core-backend-service on port 8000 and keep it running. The order and refund tools need it.

## Run the agent

### Option A: from the terminal (best for testing)

```powershell
python test_agent.py "What is your return policy?"
```

Without a question, it runs four sample questions one after another:

```powershell
python test_agent.py
```

The terminal prints every step of the graph (`--- [NODE: AGENT] ---`, `--- [NODE: GRADE DOCUMENTS] ---` and so on), so you can follow the agent's decisions.

`test_agent.py` calls the graph directly, so you don't need to start this service as a server for it.

### Option B: as an API

```powershell
uvicorn app.main:app --reload --port 8001
```

Then open **http://127.0.0.1:8001/docs**, or call it directly:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8001/api/v1/chat `
  -ContentType "application/json" `
  -Body '{"message": "What is the status of order ORD-1001?"}'
```

| Method | Endpoint | What it does |
|---|---|---|
| `POST` | `/api/v1/chat` | Send a message, get the agent's answer as `{"response": "..."}` |
| `GET` | `/health` | Health check |

## Try these questions

| Question | What happens |
|---|---|
| `Hi` | Answers directly, no tool |
| `What is your return policy?` | Searches Pinecone → graded relevant → answers from the policy |
| `What is the status of order ORD-1001?` | Calls the core backend → answers with the order status |
| `Refund 89.99 dollars for order ORD-1002, the item arrived damaged.` | Creates a refund through the core backend |
| `Do you accept gift cards?` | Searches → graded irrelevant → rewrites and retries twice → hands off to support |
| `What is a gift card?` | General question → after retries, uses web search (needs Tavily) |

Notes:
- Always include the **amount** in a refund request. Without it, the refund is sent with an amount of 0 and the backend rejects it.
- Each refund request creates a new refund. To reset the data, see the core-backend-service README.

## Project structure

```
ai-agent-service/
├── app/
│   ├── main.py               # FastAPI app: POST /api/v1/chat
│   ├── core/config.py        # settings, read from .env
│   ├── graph/
│   │   ├── state.py          # AgentState: what travels through the graph
│   │   ├── nodes.py          # what each step does: agent, grading, rewrite, routing
│   │   └── workflow.py       # how the steps connect: nodes and edges
│   ├── rag/
│   │   ├── ingest.py         # one-time: load policies into Pinecone
│   │   └── retriever.py      # search_store_policies tool
│   └── tools/
│       ├── sql_tool.py       # query_database: order lookup via core backend
│       ├── stripe_tool.py    # process_order_refund: refund via core backend
│       └── web_search_tool.py # web_search: Tavily
├── test_agent.py             # run the agent from the terminal
└── requirements.txt
```

`sql_tool.py` doesn't run SQL and `stripe_tool.py` doesn't call Stripe yet. Both call the core backend's REST API.

## Troubleshooting

| Problem | Fix |
|---|---|
| `401 invalid_api_key` | The OpenAI key in `.env` is wrong or revoked. Also check that no `OPENAI_API_KEY` is set as a system environment variable, because it takes priority over `.env`. |
| `429 insufficient_quota` / `credit_balance_exhausted` | Add credits in your OpenAI billing settings. |
| "Backend Service Communication Error" | core-backend-service isn't running on port 8000, or `CORE_BACKEND_URL` in `.env` is empty or wrong. |
| `Order 'ORD-…' not found in backend` | The backend is running but has no data. Run its seed script. |
| `ModuleNotFoundError: No module named 'app'` when ingesting | Run `python -m app.rag.ingest` from the `ai-agent-service` folder. |
| Every policy search returns "NO_INTERNAL_POLICY_FOUND" | Run the ingest step, and check `PINECONE_INDEX_NAME` in `.env`. |
