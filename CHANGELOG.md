# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-03-09

### Added

#### Core RAG System
- Multi-tenant RAG pipeline with tenant-scoped document ingestion and vector retrieval
- LangGraph workflow with 6-node state machine: rewrite → retrieve → judge → draft → approval → final
- ReAct retrieval loop: judge relevance → generate sub-questions → re-retrieve (configurable max attempts)
- Query rewriting via LLM for improved retrieval accuracy
- Hybrid search: dense (BGE/OpenAI/Gemini) + sparse vector search
- SSE streaming endpoint (`POST /chat/stream`) with token-by-token output and real-time status events

#### Knowledge Base Management
- Document CRUD with paginated listing, filtering by status and sensitivity
- Three sensitivity levels: `normal`, `sensitive`, `restricted`
- Per-document approval override: `always` / `never` / `inherit`
- Tenant-level approval policy: `all` / `sensitive` / `none`
- Approval policy resolution chain: document override → tenant policy → global setting
- Bulk operations: delete and update sensitivity for multiple documents
- Document preview with path traversal protection
- Async ingestion via Redis + RQ worker with job status tracking
- OCR support for scanned documents and images (Tesseract)

#### Pluggable Providers
- Pluggable embedding layer with ABC + 3 implementations (SentenceTransformer, OpenAI, Gemini)
- Multi-LLM support: Ollama (local), OpenAI API, Gemini API
- Provider switching via environment variables without code changes

#### Security & Compliance
- JWT authentication with configurable expiration and HttpOnly cookie support
- RBAC with three roles: `admin`, `auditor`, `user`
- Multi-tenant data isolation at API, database, and vector DB layers
- Output policy guard: regex-based detection of secrets, API keys, and credentials
- Human-in-the-loop approval workflow for generated answers
- Trusted host middleware and security response headers
- Input filename sanitization and file extension allowlist
- CSV export formula injection mitigation in audit export

#### Observability
- Prometheus metrics: query latency, embedding throughput, queue depth
- Grafana dashboards for system monitoring
- LangSmith tracing integration with `@traceable` decorators
- Sentry error tracking and alerting
- Structured JSON logging with request ID propagation

#### Frontend
- React + TypeScript SPA with Vite
- Chat interface with streaming mode toggle
- Knowledge base management panel with stats, filters, pagination
- Approval queue management
- Audit log viewer with search and export
- Tenant and user management
- i18n support (English and Chinese)
- Responsive design with accessibility support

#### Infrastructure
- Docker Compose for local development (9 services)
- Multi-stage Dockerfile with non-root user and HEALTHCHECK
- ARM64 container builds for AWS ECS Fargate
- Terraform IaC with OPA/Conftest policy gate
- GitHub Actions CI pipeline: lint (black, isort, ruff) → test (500+ tests) → build → deploy
- Automated deployment scripts for AWS

#### Documentation
- Comprehensive README with architecture diagrams
- Getting started tutorial
- Complete API reference with request/response schemas
- Database ER diagrams
- LangGraph workflow design documentation
- Deployment architecture documentation
- AWS deployment runbook (13-step guide)
- Operations runbook (health checks, SLOs, incident response)
- Release and rollback procedures
- Frontend contributing guide
- UI design tokens specification
- Security policy
- Contributing guide with PR checklist

#### Developer Tooling
- `pyproject.toml` with black, isort, ruff, mypy, pytest configuration
- `requirements-dev.txt` with development dependencies
- `.pre-commit-config.yaml` for automated code quality checks
- `conftest.py` with shared test fixtures
- `.dockerignore` for optimized Docker builds
- GitHub issue templates (bug report, feature request)
- Pull request template with checklist
