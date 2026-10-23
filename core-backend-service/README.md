# Core Backend Service

The data service for the Agentic RAG project. It owns the **orders** and **refunds** data in PostgreSQL and exposes it through a small FastAPI REST API.

The AI agent never touches the database directly. When it needs an order's status or has to create a refund, it calls this service over HTTP.

```
ai-agent-service  ──HTTP──►  core-backend-service (port 8000)  ──►  PostgreSQL (ecommerce_db)
```

## Tech stack

- **FastAPI**: REST API
- **SQLAlchemy (async) + asyncpg**: database access
- **Alembic**: database migrations
- **PostgreSQL**: orders and refunds data

## Prerequisites

- Python 3.12 or newer
- PostgreSQL running locally on port `5432`

## Setup

All commands below are for **Windows PowerShell**. On macOS/Linux, activate the virtual environment with `source .venv/bin/activate` instead.

### 1. Create the database

```powershell
psql -U postgres -c "CREATE DATABASE ecommerce_db;"
```

### 2. Create a virtual environment and install packages

```powershell
cd core-backend-service
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

> Use `python -m pip` so the packages go into this virtual environment and not into another Python on your machine.

### 3. Create the `.env` file

Create a file named `.env` in the `core-backend-service` folder:

```env
DATABASE_URL="postgresql+asyncpg://postgres:<your-password>@localhost:5432/ecommerce_db"
```

Replace `<your-password>` with your Postgres password. Never commit this file.

### 4. Create the tables

```powershell
alembic upgrade head
```

This runs the migration that creates the `orders` and `refunds` tables.

### 5. Add sample data

```powershell
python app/db/seed.py
```

If the `orders` table already has data, the script skips seeding, so it's safe to run more than once.

| Order ID | Status | Total |
|---|---|---|
| ORD-1001 | DELIVERED | 120.50 |
| ORD-1002 | DELIVERED | 89.99 |
| ORD-1003 | PROCESSING | 210.00 |
| ORD-1004 | CANCELLED | 45.00 |
| ORD-1005 | REFUNDED | 150.00 |

### 6. Start the server

```powershell
uvicorn app.main:app --reload --port 8000
```

You should see `Application startup complete.` Keep this terminal open while you use the AI agent.

## Try the API

Open the interactive docs at **http://127.0.0.1:8000/docs**, or call the endpoints directly.

| Method | Endpoint | What it does |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/api/v1/orders/{order_id}` | Get one order |
| `POST` | `/api/v1/refunds/` | Create a refund (returns `201`) |

**Get an order:**

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/orders/ORD-1001
```

**Create a refund:**

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/v1/refunds/ `
  -ContentType "application/json" `
  -Body '{"order_id": "ORD-1002", "amount": 89.99, "reason": "Item arrived damaged"}'
```

On macOS/Linux, use `curl` with the same URL and JSON body.

Refund rules:
- `amount` must be greater than 0, otherwise the API returns `422`.
- `amount` can't be more than the order total, otherwise it returns `400`.
- An unknown order ID returns `404`.
- A full refund sets the order status to `refunded`; a smaller amount sets it to `partially_refunded`.

## Reset the data

Every refund call creates a new refund. To start fresh:

```powershell
psql -U postgres -d ecommerce_db -c "TRUNCATE orders, refunds;"
python app/db/seed.py
```

## Project structure

```
core-backend-service/
├── alembic/                  # migrations
│   └── versions/             # initial schema: orders + refunds
├── alembic.ini
├── app/
│   ├── main.py               # FastAPI app, CORS, routes
│   ├── core/config.py        # settings, read from .env
│   ├── api/
│   │   ├── deps.py           # database session dependency
│   │   └── v1/
│   │       ├── router.py     # /orders and /refunds routes
│   │       └── endpoints/    # orders.py, refunds.py
│   ├── services/             # business logic: order_service.py, refund_service.py
│   ├── schemas/              # request/response models (Pydantic)
│   └── db/
│       ├── models.py         # Order and Refund tables
│       ├── session.py        # async engine and session
│       └── seed.py           # sample data
└── requirements.txt
```

The request flow is: `endpoints/` → `services/` → `db/` → PostgreSQL.

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'fastapi'` | The packages aren't in this virtual environment. Activate `.venv` and run `python -m pip install -r requirements.txt` again. |
| `password authentication failed` | Check the password in `DATABASE_URL` in your `.env`. |
| `database "ecommerce_db" does not exist` | Run step 1 to create the database. |
| `relation "orders" does not exist` | Run `alembic upgrade head` before seeding. |
| The agent says "Backend Service Communication Error" | This server isn't running. Start it with step 6 and keep the terminal open. |
| The traceback stops at an import line with `--reload` | Run `python -c "from app.main import app"` to see the full error. |
