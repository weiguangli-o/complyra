# Contributing to Complyra

Thank you for your interest in contributing! This guide explains how to set up a development environment, follow our conventions, and submit changes.

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- Docker and Docker Compose
- Git

### Backend

```bash
# Clone and install
git clone https://github.com/weiguangli-io/complyra.git
cd complyra
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Start infrastructure services
docker compose up postgres redis qdrant ollama -d

# Initialize database
cp .env.example .env
alembic upgrade head

# Run the API server
uvicorn app.main:app --reload
```

### Frontend

```bash
cd web
npm install
npm run dev
```

### Worker

```bash
rq worker ingest --url redis://localhost:6379/0
```

## Code Style

We use the following tools for consistent code quality:

| Tool | Purpose | Config |
|------|---------|--------|
| **black** | Code formatter | `line-length = 100` |
| **isort** | Import sorter | `profile = "black"` |
| **ruff** | Linter | `E, F, W, I` rules |
| **mypy** | Type checker | `python_version = "3.11"` |

Run all checks:

```bash
black --check app/
isort --check app/
ruff check app/
mypy app/
```

Or let pre-commit do it automatically:

```bash
pre-commit run --all-files
```

## Testing

All changes must include tests where applicable.

```bash
PYTHONPATH=. pytest tests/ -v --cov=app --cov-report=term-missing
```

### Test Organization

```
tests/
├── conftest.py              # Shared fixtures
├── test_auth.py             # Authentication tests
├── test_chat.py             # Chat endpoint tests
├── test_documents.py        # Document route tests
├── test_retrieval.py        # Retrieval service tests
├── test_workflow.py         # LangGraph workflow tests
├── test_worker.py           # Ingest worker tests
├── test_approval_policy.py  # Approval policy tests
├── test_document_model.py   # Database model tests
├── test_document_service.py # Document service tests
├── test_kb_routes.py        # KB management route tests
├── test_kb_integration.py   # Integration tests
├── test_kb_smoke.py         # Smoke tests
└── test_functional.py       # End-to-end functional tests
```

### Writing Tests

- Use `pytest` with `unittest.mock` for mocking
- Follow the existing test structure: one test class per feature/function
- Mock external services (Qdrant, Ollama, Redis) — tests should not require running infrastructure
- Use `tmp_path` fixture for file-based tests

## Pull Request Process

1. Fork the repository and create a feature branch from `main`
2. Make your changes with tests
3. Ensure all checks pass (`black`, `isort`, `ruff`, `pytest`)
4. Write a clear PR description explaining what and why
5. Request review from a maintainer

### PR Checklist

- [ ] Tests pass locally (`pytest tests/ -v`)
- [ ] Code formatted with `black` and `isort`
- [ ] No new linting warnings from `ruff`
- [ ] Docstrings added for new public functions (Google style)
- [ ] `.env.example` updated if new config options added
- [ ] `docs/configuration.md` updated if new settings added
- [ ] README updated if user-facing behavior changed
- [ ] CHANGELOG.md updated under `[Unreleased]`

## Commit Messages

Use clear, imperative-mood commit messages:

```
Add pluggable embedding provider abstraction
Fix tenant isolation in search_chunks
Update CI to include coverage report
```

## Architecture Guidelines

### Adding a New API Endpoint

1. Define Pydantic schemas in `app/models/schemas.py`
2. Create or update the route in `app/api/routes/`
3. Implement business logic in `app/services/`
4. Add database operations in `app/db/audit_db.py` if needed
5. Include the router in `app/main.py`
6. Write tests in `tests/`

### Adding a New Provider

Complyra uses a provider abstraction for embeddings and LLMs:

1. Implement the `EmbeddingProvider` ABC (see `app/services/embeddings.py`)
2. Add configuration in `app/core/config.py`
3. Register in the factory function (`get_embedder()`)
4. Update `.env.example` and `docs/configuration.md`
5. Write provider-specific tests

## Reporting Issues

Please use our [issue templates](.github/ISSUE_TEMPLATE/) for bug reports and feature requests.

## Code of Conduct

Be respectful and constructive. We follow the [Contributor Covenant](https://www.contributor-covenant.org/).
