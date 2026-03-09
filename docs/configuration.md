# Configuration Reference

All settings are managed via environment variables with the `APP_` prefix. A `.env` file is automatically loaded if present. Configuration is powered by [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/).

## General

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_APP_NAME` | `Complyra` | Application name (shown in API docs) |
| `APP_ENV` | `dev` | Environment: `dev`, `staging`, `production` |
| `APP_API_PREFIX` | `/api` | URL prefix for all API routes |
| `APP_LOG_LEVEL` | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `APP_LOG_FORMAT` | `json` | Log format: `json` (structured) or `text` (human-readable) |

## Authentication

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_JWT_SECRET_KEY` | `change-me` | Secret key for JWT signing. **Must change in production** |
| `APP_JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `APP_ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | JWT token expiration time in minutes |
| `APP_DEMO_USERNAME` | `demo` | Built-in demo user username |
| `APP_DEMO_PASSWORD` | *(empty)* | Demo user password (plain text, for dev only) |
| `APP_DEMO_PASSWORD_HASH` | *(empty)* | Demo user password hash (PBKDF2+SHA256, for production) |

## CORS & Security

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_CORS_ORIGINS` | `http://localhost:5173` | Comma-separated list of allowed CORS origins |
| `APP_TRUSTED_HOSTS` | `localhost,127.0.0.1` | Comma-separated list of trusted hosts |

## Session / Cookies

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_SESSION_COOKIE_NAME` | `complyra_token` | Cookie name for session token |
| `APP_COOKIE_SECURE` | `false` | Require HTTPS for cookies (set `true` in production) |
| `APP_COOKIE_SAMESITE` | `lax` | Cookie SameSite policy: `lax`, `strict`, `none` |
| `APP_COOKIE_DOMAIN` | *(empty)* | Cookie domain (e.g., `.complyra.app` for subdomains) |

## Vector Database (Qdrant)

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_QDRANT_URL` | `http://localhost:6333` | Qdrant server URL |
| `APP_QDRANT_COLLECTION` | `complyra_private_kb` | Qdrant collection name |

## Embeddings

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_EMBEDDING_PROVIDER` | `sentence-transformers` | Provider: `sentence-transformers`, `openai`, `gemini` |
| `APP_EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | SentenceTransformer model name |
| `APP_EMBEDDING_DIMENSION` | `384` | Vector dimension. Must match provider: 384 (BGE-small), 1536 (OpenAI), 768 (Gemini) |
| `APP_OPENAI_API_KEY` | *(empty)* | OpenAI API key (required when `embedding_provider=openai`) |
| `APP_OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embedding model |
| `APP_GEMINI_API_KEY` | *(empty)* | Google Gemini API key (required when `embedding_provider=gemini`) |
| `APP_GEMINI_EMBEDDING_MODEL` | `text-embedding-004` | Gemini embedding model |

> **Warning**: When switching embedding providers, the Qdrant collection must be recreated because vector dimensions differ. Delete the old collection or use a different collection name.

## LLM

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_LLM_PROVIDER` | `ollama` | LLM provider: `ollama`, `openai`, `gemini` |
| `APP_OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `APP_OLLAMA_MODEL` | `qwen2.5:3b-instruct` | Ollama model name |
| `APP_OLLAMA_PREPULL` | `true` | Auto-pull Ollama model on startup |
| `APP_OLLAMA_TIMEOUT_SECONDS` | `60` | Ollama request timeout |
| `APP_OPENAI_CHAT_MODEL` | `gpt-4o-mini` | OpenAI chat model |
| `APP_GEMINI_CHAT_MODEL` | `gemini-2.5-flash` | Gemini chat model |

## RAG Parameters

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_CHUNK_SIZE` | `800` | Document chunk size in characters |
| `APP_CHUNK_OVERLAP` | `120` | Overlap between adjacent chunks |
| `APP_TOP_K` | `4` | Number of top chunks to retrieve per query |
| `APP_QUERY_REWRITE_ENABLED` | `true` | Enable LLM-based query rewriting for better retrieval |
| `APP_REACT_RETRIEVAL_ENABLED` | `true` | Enable ReAct loop (judge → sub-question → re-retrieve) |
| `APP_MAX_RETRIEVAL_ATTEMPTS` | `3` | Maximum ReAct retrieval iterations |
| `APP_HYBRID_SEARCH_ENABLED` | `true` | Enable hybrid search (dense + sparse vectors) |

## Approval & Output Policy

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_REQUIRE_APPROVAL` | `true` | Global default: require human approval for answers |
| `APP_DEFAULT_TENANT_ID` | `default` | Default tenant ID for new users |
| `APP_OUTPUT_POLICY_ENABLED` | `true` | Enable output policy checks |
| `APP_OUTPUT_POLICY_BLOCK_MESSAGE` | *(see below)* | Message shown when answer is blocked |
| `APP_OUTPUT_POLICY_BLOCK_PATTERNS` | *(see below)* | Regex patterns for secret detection |

Default block message:
> The generated response was withheld due to policy checks. Please contact an administrator.

Default block patterns detect:
- AWS access keys (`AKIA...`, `ASIA...`)
- API secret keys (`sk-...`, `rk-...`)
- Private keys (RSA, SSH, EC, DSA)
- Inline passwords (`password=...`, `pwd:...`)

## Database

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_DATABASE_URL` | `sqlite:///./data/app.db` | SQLAlchemy connection string. Use PostgreSQL in production |

Production example:
```
APP_DATABASE_URL=postgresql://complyra:password@db.example.com:5432/complyra
```

## Queue & Ingestion

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `APP_INGEST_QUEUE_NAME` | `ingest` | RQ queue name for ingestion jobs |
| `APP_INGEST_ASYNC_ENABLED` | `true` | Enable async ingestion (disable for synchronous processing) |
| `APP_INGEST_MAX_FILE_SIZE_MB` | `20` | Maximum upload file size in MB |
| `APP_INGEST_STORAGE_PATH` | `./data/uploads` | Temporary storage for uploaded files |
| `APP_DOCUMENT_PREVIEW_STORAGE_PATH` | `./data/previews` | Storage for document preview files |
| `APP_INGEST_ALLOWED_EXTENSIONS` | `pdf,txt,md,png,jpg,jpeg` | Comma-separated list of allowed file extensions |

## OCR

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_OCR_ENABLED` | `true` | Enable OCR for scanned documents and images |
| `APP_OCR_LANGUAGE` | `eng+chi_sim` | Tesseract language codes |
| `APP_OCR_MIN_TEXT_THRESHOLD` | `50` | Minimum characters for PDF text extraction before OCR fallback |
| `APP_CHUNKING_STRATEGY` | `smart` | Chunking strategy: `smart` (semantic boundaries) or `fixed` |

## Observability

### LangSmith

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_LANGSMITH_TRACING` | `false` | Enable LangSmith tracing |
| `APP_LANGSMITH_API_KEY` | *(empty)* | LangSmith API key |
| `APP_LANGSMITH_PROJECT` | `complyra` | LangSmith project name |

### Sentry

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_SENTRY_DSN` | *(empty)* | Sentry DSN for error tracking |
| `APP_SENTRY_ENVIRONMENT` | `dev` | Sentry environment tag |

### Prometheus

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_METRICS_ENABLED` | `true` | Enable Prometheus metrics endpoint |
| `APP_METRICS_PATH` | `/metrics` | Metrics endpoint path |
| `APP_METRICS_TOKEN` | *(empty)* | Bearer token for metrics endpoint access |

## Multimodal

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_MULTIMODAL_ENABLED` | `false` | Enable multimodal (image understanding) features |

## Approval Policy Resolution

The approval decision follows a priority chain:

```
Document Override (always/never)
        ↓ (if inherit or not set)
  Tenant Policy (all/sensitive/none)
        ↓ (if no tenant policy)
   Global Setting (APP_REQUIRE_APPROVAL)
```

| Level | Setting | Effect |
|-------|---------|--------|
| Document | `approval_override = always` | Always require approval for this document |
| Document | `approval_override = never` | Never require approval for this document |
| Document | `approval_override = null` | Inherit from tenant policy |
| Tenant | `approval_mode = all` | Require approval for all answers |
| Tenant | `approval_mode = sensitive` | Only require approval when source docs are `sensitive` or `restricted` |
| Tenant | `approval_mode = none` | No approval required |
| Global | `APP_REQUIRE_APPROVAL = true` | Default when no tenant policy exists |
