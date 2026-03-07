# Contributing to Complyra

Thank you for your interest in contributing! This guide explains how to set up a development environment and submit changes.

## Development Setup

```bash
# Clone and install
git clone https://github.com/complyra/complyra.git
cd complyra
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Start infrastructure
docker compose up postgres redis qdrant ollama -d

# Run the API
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

## Code Style

We use the following tools for consistent code quality:

- **black** — code formatter (line length: 100)
- **isort** — import sorter (black profile)
- **ruff** — fast linter (E, F, W, I rules)
- **mypy** — optional static type checking

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

## Pull Request Process

1. Fork the repository and create a feature branch from `main`
2. Make your changes with tests
3. Ensure all checks pass (`black`, `isort`, `ruff`, `pytest`)
4. Write a clear PR description explaining what and why
5. Request review from a maintainer

### PR Checklist

- [ ] Tests pass locally
- [ ] Code formatted with `black` and `isort`
- [ ] No new linting warnings from `ruff`
- [ ] Docstrings added for new public functions (Google style)
- [ ] `.env.example` updated if new config options added
- [ ] README updated if user-facing behavior changed

## Commit Messages

Use clear, imperative-mood commit messages:

- `Add pluggable embedding provider abstraction`
- `Fix tenant isolation in search_chunks`
- `Update CI to include coverage report`

## Reporting Issues

Please use our [issue templates](.github/ISSUE_TEMPLATE/) for bug reports and feature requests.

## Code of Conduct

Be respectful and constructive. We follow the [Contributor Covenant](https://www.contributor-covenant.org/).
