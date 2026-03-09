# Getting Started with Complyra

Welcome to Complyra -- a production-ready enterprise AI assistant with private knowledge retrieval, human approval workflows, RBAC, and full audit trails.

This guide walks you through going from a fresh clone to a fully working local environment in about 10 minutes.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Quick Start (Docker Compose)](#2-quick-start-docker-compose)
3. [First Login](#3-first-login)
4. [Upload Your First Document](#4-upload-your-first-document)
5. [Ask a Question](#5-ask-a-question)
6. [Review an Approval](#6-review-an-approval)
7. [Check Audit Logs](#7-check-audit-logs)
8. [Manage Documents](#8-manage-documents)
9. [Configure Tenant Policy](#9-configure-tenant-policy)
10. [Try Streaming Mode](#10-try-streaming-mode)
11. [Local Development Setup](#11-local-development-setup)
12. [Running Tests](#12-running-tests)
13. [Next Steps](#13-next-steps)

---

## 1. Prerequisites

Make sure you have the following installed on your machine:

| Tool             | Minimum Version | Check Command          |
|------------------|-----------------|------------------------|
| Docker           | 24+             | `docker --version`     |
| Docker Compose   | v2+             | `docker compose version` |
| Node.js          | 18+             | `node --version`       |
| Python           | 3.11+           | `python3 --version`    |

> **Note:** Docker and Docker Compose are the only hard requirements for the Quick Start path. Node.js and Python are needed only if you plan to do local development without Docker.

You will also need **Ollama** running locally (or accessible on the network) for LLM inference. Install it from [ollama.com](https://ollama.com) and pull a model:

```bash
ollama pull qwen2.5:3b-instruct
```

---

## 2. Quick Start (Docker Compose)

### Clone the repository

```bash
git clone https://github.com/your-org/complyra.git
cd complyra
```

### Copy the environment file

```bash
cp .env.example .env
```

The defaults work out of the box for local development. The demo user (`demo` / `demo123`) is pre-configured.

### Build and start all services

```bash
docker compose up --build -d
```

This spins up eight services. Wait about 60 seconds for everything to become healthy, then verify:

```bash
docker compose ps
```

### Service URLs

Once running, you can access:

| Service      | URL                          | Purpose                        |
|--------------|------------------------------|--------------------------------|
| Web UI       | http://localhost:5173        | React frontend                 |
| API          | http://localhost:8000        | FastAPI backend                |
| API Docs     | http://localhost:8000/docs   | Interactive Swagger UI         |
| PostgreSQL   | localhost:5432               | Relational database            |
| Redis        | localhost:6379               | Job queue                      |
| Qdrant       | http://localhost:6333        | Vector database                |
| Prometheus   | http://localhost:9090        | Metrics collection             |
| Grafana      | http://localhost:3000        | Dashboards (admin / admin)     |

### Health check

```bash
curl http://localhost:8000/api/health/live
# {"status":"ok"}

curl http://localhost:8000/api/health/ready
# {"status":"ok","postgres":true,"qdrant":true,"ollama":true}
```

---

## 3. First Login

1. Open **http://localhost:5173** in your browser.
2. Log in with the demo credentials:
   - **Username:** `demo`
   - **Password:** `demo123`
3. You will land on the main dashboard.

**UI Layout:**
- **Chat** -- the main conversation panel where you ask questions against ingested documents.
- **Knowledge Base (KB)** -- upload, browse, and manage documents.
- **Approvals** -- review pending AI-generated answers (visible to admin/auditor roles).
- **Audit Logs** -- full trail of every action taken in the system.

You can also log in via the API:

```bash
curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "demo", "password": "demo123"}' | python3 -m json.tool
```

Save the `access_token` from the response -- you will need it for subsequent API calls:

```bash
export TOKEN="<paste your access_token here>"
```

---

## 4. Upload Your First Document

### Via the Web UI

1. Navigate to the **Knowledge Base** tab.
2. Click **Upload** and select a PDF, TXT, or Markdown file.
3. The upload triggers an async ingest job. You will see a progress indicator as the system:
   - Parses the document (PDF text extraction via PyMuPDF, or raw text for TXT/MD)
   - Splits it into chunks (800 tokens with 120-token overlap by default)
   - Generates embeddings (BGE-small-en-v1.5 by default)
   - Upserts the vectors into Qdrant

### Via curl

```bash
curl -X POST http://localhost:8000/api/ingest/file \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: default" \
  -F "file=@/path/to/your/document.pdf"
```

Response:

```json
{
  "job_id": "a1b2c3d4-...",
  "status": "queued"
}
```

### Check job status

```bash
curl -s http://localhost:8000/api/ingest/jobs/a1b2c3d4-... \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: default" | python3 -m json.tool
```

The `status` field transitions through: `queued` -> `processing` -> `completed` (or `failed`).

---

## 5. Ask a Question

### Via the Web UI

1. Go to the **Chat** tab.
2. Type a question related to your uploaded document, for example: *"What is the company's data retention policy?"*
3. The system performs tenant-scoped retrieval from Qdrant, builds a prompt, and generates an answer via the LLM.
4. You will see:
   - **Retrieved chunks** -- the relevant passages found, with relevance scores and source filenames.
   - **Draft answer** -- the LLM-generated response grounded in retrieved context.
   - **Status** -- either `completed` (answer delivered) or `pending_approval` (if approval is enabled).

### Via curl

```bash
curl -s -X POST http://localhost:8000/api/chat/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: default" \
  -d '{"question": "What is the data retention policy?"}' | python3 -m json.tool
```

Response:

```json
{
  "status": "pending_approval",
  "answer": "Your request is pending human approval.",
  "retrieved": [
    {
      "text": "Data is retained for 7 years...",
      "score": 0.92,
      "source": "policy.pdf",
      "page_numbers": [3]
    }
  ],
  "approval_id": "e5f6g7h8-..."
}
```

> **Understanding the approval flow:** When `APP_REQUIRE_APPROVAL=true` (the default), every chat response goes through a human review step. The answer is drafted but not released until an admin or auditor approves it. If approval is disabled, you get the answer immediately with `"status": "completed"`.

---

## 6. Review an Approval

If approval is enabled (default), the chat response will be held until an authorized user reviews it.

### Via the Web UI

1. Navigate to the **Approvals** tab.
2. Find the pending approval entry -- it shows the original question and the draft answer.
3. Click **Approve** to release the answer, or **Reject** to block it. You can add a note explaining your decision.

### Via curl

**List pending approvals:**

```bash
curl -s "http://localhost:8000/api/approvals/?status=pending" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: default" | python3 -m json.tool
```

**Approve a request:**

```bash
curl -s -X POST http://localhost:8000/api/approvals/e5f6g7h8-.../decision \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: default" \
  -d '{"approved": true, "note": "Looks good, factually correct."}' | python3 -m json.tool
```

**Reject a request:**

```bash
curl -s -X POST http://localhost:8000/api/approvals/e5f6g7h8-.../decision \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: default" \
  -d '{"approved": false, "note": "Contains inaccurate information."}' | python3 -m json.tool
```

**Check the result of an approval (as the requesting user):**

```bash
curl -s http://localhost:8000/api/approvals/e5f6g7h8-.../result \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: default" | python3 -m json.tool
```

---

## 7. Check Audit Logs

Every significant action -- logins, chat queries, document uploads, approval decisions -- is recorded in the audit trail.

### Via the Web UI

1. Navigate to the **Audit Logs** tab.
2. Browse the full history of actions. Each entry includes: timestamp, user, action type, input/output text, and metadata.

### Via curl

**List recent audit entries:**

```bash
curl -s "http://localhost:8000/api/audit/?limit=20" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: default" | python3 -m json.tool
```

**Search with filters:**

```bash
curl -s "http://localhost:8000/api/audit/search?user=demo&action=chat_completed&limit=10" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: default" | python3 -m json.tool
```

**Export as CSV:**

```bash
curl -s "http://localhost:8000/api/audit/export?start_time=2025-01-01T00:00:00Z" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: default" \
  -o audit_export.csv
```

The CSV export includes formula injection protection for compliance safety.

---

## 8. Manage Documents

Once documents are ingested, you can manage them through the documents API.

### List documents

```bash
curl -s "http://localhost:8000/api/documents/?status=active" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: default" | python3 -m json.tool
```

### Change sensitivity level

Documents can be marked as `normal`, `sensitive`, or `restricted`. This affects how the approval policy treats them.

```bash
curl -s -X PATCH http://localhost:8000/api/documents/<document_id> \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: default" \
  -d '{"sensitivity": "sensitive"}' | python3 -m json.tool
```

### Set approval override

You can override the tenant-level approval policy on a per-document basis. Set it to `"always"` to force approval for a specific document, or `null` to clear the override and fall back to the tenant policy.

```bash
curl -s -X PATCH http://localhost:8000/api/documents/<document_id> \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: default" \
  -d '{"approval_override": "always"}' | python3 -m json.tool
```

### Bulk operations

Delete multiple documents at once:

```bash
curl -s -X POST http://localhost:8000/api/documents/bulk \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: default" \
  -d '{
    "action": "delete",
    "document_ids": ["doc-id-1", "doc-id-2"]
  }' | python3 -m json.tool
```

Bulk update sensitivity:

```bash
curl -s -X POST http://localhost:8000/api/documents/bulk \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: default" \
  -d '{
    "action": "update_sensitivity",
    "document_ids": ["doc-id-1", "doc-id-2"],
    "sensitivity": "restricted"
  }' | python3 -m json.tool
```

---

## 9. Configure Tenant Policy

Complyra supports per-tenant approval policies. The approval mode controls when human review is required.

| Mode        | Behavior                                                  |
|-------------|-----------------------------------------------------------|
| `all`       | Every chat response requires approval before release      |
| `sensitive` | Only responses citing sensitive/restricted documents need approval |
| `none`      | No approval required -- answers are returned immediately  |

### View current policy

```bash
curl -s http://localhost:8000/api/tenants/default/policy \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

### Update approval mode

```bash
curl -s -X PUT http://localhost:8000/api/tenants/default/policy \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"approval_mode": "sensitive"}' | python3 -m json.tool
```

Try setting it to `none` and asking a question again -- you will get an immediate answer without the approval step.

---

## 10. Try Streaming Mode

Complyra supports Server-Sent Events (SSE) for token-by-token streaming output.

### Via the Web UI

Toggle the **Streaming** switch in the chat interface. When enabled, you will see tokens appear one at a time as the LLM generates the response, along with real-time status events for retrieval, policy checks, and approval routing.

### Via curl

```bash
curl -N -X POST http://localhost:8000/api/chat/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: default" \
  -d '{"question": "Summarize the key compliance requirements."}'
```

You will see a stream of SSE events:

```
event: retrieve_start
data: {"attempt": 1}

event: retrieve_done
data: {"attempt": 1, "retrieved": [...]}

event: generate_start
data: {}

event: token
data: {"text": "According"}

event: token
data: {"text": " to"}

...

event: policy_passed
data: {}

event: done
data: {"answer": "According to the policy..."}
```

The event flow is: `retrieve_start` -> `retrieve_done` -> `generate_start` -> `token*` -> `policy_passed`/`policy_blocked` -> `done`/`approval_required`.

If query rewriting is enabled, you will also see `rewrite_start` and `rewrite_done` events before retrieval. If ReAct multi-step retrieval is enabled, you may see multiple retrieval attempts with `judge_start`/`judge_done` events.

---

## 11. Local Development Setup

For active development, you can run the backend and frontend outside of Docker while keeping infrastructure services (PostgreSQL, Redis, Qdrant) in containers.

### Start infrastructure only

```bash
docker compose up -d postgres redis qdrant
```

### Backend

```bash
# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Update the database URL for local access
export APP_DATABASE_URL="postgresql+psycopg://app:app_password@localhost:5432/complyra"
export APP_REDIS_URL="redis://localhost:6379/0"
export APP_QDRANT_URL="http://localhost:6333"
export APP_OLLAMA_BASE_URL="http://localhost:11434"

# Run database migrations
alembic upgrade head

# Start the API server with hot reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Worker

In a separate terminal (with the same virtual environment activated and environment variables set):

```bash
source .venv/bin/activate
export APP_DATABASE_URL="postgresql+psycopg://app:app_password@localhost:5432/complyra"
export APP_REDIS_URL="redis://localhost:6379/0"
export APP_QDRANT_URL="http://localhost:6333"

rq worker ingest --url redis://localhost:6379/0
```

### Frontend

```bash
cd web
npm install
npm run dev
```

The dev server starts at http://localhost:5173 with hot module replacement.

---

## 12. Running Tests

The test suite uses pytest with async support:

```bash
# Activate the virtual environment
source .venv/bin/activate

# Run all tests with coverage
pytest --cov=app --cov-report=term-missing

# Run a specific test file
pytest tests/test_auth.py -v

# Run tests matching a keyword
pytest -k "approval" -v
```

The test configuration is defined in `pyproject.toml`:
- Test directory: `tests/`
- Async mode: `auto` (via pytest-asyncio)

### Linting and formatting

```bash
# Format code
black .
isort .

# Lint
ruff check .

# Type checking
mypy app/
```

---

## 13. Next Steps

Now that you have Complyra running locally, here are some directions to explore:

- **[Architecture](architecture.md)** -- Understand the full system topology, layered backend design, workflow engine, and security model.
- **[Streaming API Reference](streaming-api.md)** -- Deep dive into the SSE streaming protocol, event types, and client integration patterns.
- **[AWS Deployment](aws-deployment.md)** -- Deploy Complyra to AWS with ECS, RDS, ElastiCache, and managed Qdrant.
- **[Operations Runbook](operations-runbook.md)** -- Monitoring, alerting, backup, and incident response procedures.
- **[Frontend Contributing Guide](frontend-contributing.md)** -- UI component conventions, design tokens, and testing practices.
- **[API Docs](http://localhost:8000/docs)** -- Interactive Swagger UI with all available endpoints.

### Key environment variables to explore

| Variable                    | Purpose                                      |
|-----------------------------|----------------------------------------------|
| `APP_REQUIRE_APPROVAL`      | Enable/disable global approval workflow      |
| `APP_EMBEDDING_PROVIDER`    | `sentence-transformers` (local) or `openai`  |
| `APP_OLLAMA_MODEL`          | Which LLM model to use for generation        |
| `APP_CHUNK_SIZE`            | Token size for document chunking              |
| `APP_TOP_K`                 | Number of chunks to retrieve per query        |
| `APP_OUTPUT_POLICY_ENABLED` | Enable output policy (secret detection, etc.) |
| `APP_INGEST_ALLOWED_EXTENSIONS` | Allowed file types for upload            |

Happy building!
