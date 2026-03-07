# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Pluggable embedding layer with SentenceTransformer and OpenAI provider support
- SSE streaming endpoint (`POST /chat/stream`) for real-time token-by-token output
- LangSmith tracing integration for LLM observability
- `@traceable` decorators on core service functions
- Streaming mode toggle in the web UI
- Developer tooling: `pyproject.toml`, `requirements-dev.txt`, `.pre-commit-config.yaml`
- Test fixtures (`conftest.py`) and embedding provider tests
- Google-style docstrings across all `app/` modules
- Inline comments explaining the LangGraph workflow
- `CONTRIBUTING.md`, `SECURITY.md`, `CHANGELOG.md`
- GitHub issue templates and pull request template
- SSE streaming API documentation (`docs/streaming-api.md`)
- `.dockerignore` for optimized Docker builds

### Changed
- Dockerfile now runs as non-root user with `HEALTHCHECK`
- `docker-compose.yml` now includes resource limits and healthchecks for all services
- CI workflow updated with linting (black, isort, ruff) and coverage reporting
- `retrieval.py` logs a warning when Qdrant collection dimension mismatches the embedding provider
- README.md rewritten with Mermaid architecture diagram and comprehensive documentation

### Fixed
- Embedding dimension mismatch detection when switching providers
