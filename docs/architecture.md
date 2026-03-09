# Architecture

## 1. System Overview

Complyra is a multi-tenant enterprise RAG (Retrieval-Augmented Generation) system designed for compliance-sensitive environments. It combines vector search, LLM generation, human-in-the-loop approval, and full audit logging into a single deployable platform.

```mermaid
graph TB
    subgraph Client["Client Layer"]
        SPA[React SPA]
        API_CLIENT[API Client / curl]
    end

    subgraph Gateway["API Gateway"]
        FASTAPI[FastAPI]
        JWT[JWT Auth]
        RBAC[Role-Based Access Control]
        TENANT[Tenant Isolation]
    end

    subgraph Workflow["LangGraph Workflow Engine"]
        direction LR
        REWRITE[Query Rewrite] --> RETRIEVE[Vector Retrieve]
        RETRIEVE --> JUDGE[Relevance Judge]
        JUDGE -->|sub-questions| RETRIEVE
        JUDGE --> DRAFT[Draft Answer]
        DRAFT --> POLICY[Policy Gate]
        POLICY -->|sensitive| APPROVAL[Human Approval]
        POLICY -->|safe| OUTPUT[Output]
    end

    subgraph Services["Service Layer"]
        LLM_SVC[LLM Service<br/>Ollama / OpenAI / Gemini]
        EMB_SVC[Embedding Service<br/>BGE / OpenAI / Gemini]
        INGEST_SVC[Ingest Service<br/>Parse / Chunk / Embed]
        DOC_SVC[Document Service<br/>KB Management]
        AUDIT_SVC[Audit Service]
        POLICY_SVC[Policy Engine]
    end

    subgraph Data["Data Layer"]
        PG[(PostgreSQL<br/>Users, Approvals,<br/>Audit, Documents)]
        QD[(Qdrant<br/>Vector Embeddings)]
        REDIS[(Redis<br/>Job Queue)]
        FS[File Storage<br/>Uploads / Previews]
    end

    subgraph Worker["Background Worker"]
        RQ[RQ Worker]
    end

    subgraph Observability["Observability"]
        PROM[Prometheus]
        GRAF[Grafana]
        LS[LangSmith]
        SENTRY[Sentry]
    end

    SPA --> FASTAPI
    API_CLIENT --> FASTAPI
    FASTAPI --> JWT --> RBAC --> TENANT
    TENANT --> Workflow
    Workflow --> LLM_SVC
    Workflow --> EMB_SVC
    Workflow --> POLICY_SVC
    FASTAPI --> DOC_SVC
    FASTAPI --> AUDIT_SVC
    FASTAPI --> INGEST_SVC
    INGEST_SVC -->|enqueue| REDIS
    REDIS --> RQ
    RQ --> EMB_SVC
    RQ --> QD
    RQ --> PG
    RQ --> FS
    EMB_SVC --> QD
    DOC_SVC --> PG
    AUDIT_SVC --> PG
    LLM_SVC --> QD
    FASTAPI -.-> PROM --> GRAF
    Workflow -.-> LS
    FASTAPI -.-> SENTRY
```

## 2. Design Principles

| Principle | Implementation |
|-----------|---------------|
| **Multi-tenancy** | Every data access scoped by `tenant_id` at API, SQL, and vector DB layers |
| **Separation of concerns** | Routes → Services → DB layers with clear boundaries |
| **Pluggable providers** | Embedding and LLM providers are interchangeable via config |
| **Human-in-the-loop** | Configurable approval gates at document, tenant, and global levels |
| **Auditability** | Every action logged with user, tenant, timestamp, and full I/O |
| **Observable** | Prometheus metrics, LangSmith traces, Sentry errors |
| **Cloud-native** | Docker containers, ECS Fargate, Terraform IaC |

## 3. Layered Backend Design

```
┌─────────────────────────────────────────────────────────┐
│  app/api/routes/    HTTP handlers and request validation │
├─────────────────────────────────────────────────────────┤
│  app/api/deps.py    Auth, tenant scoping, role guards   │
├─────────────────────────────────────────────────────────┤
│  app/services/      Domain logic and business rules     │
├─────────────────────────────────────────────────────────┤
│  app/db/            Persistence (SQLAlchemy + Qdrant)   │
├─────────────────────────────────────────────────────────┤
│  app/models/        Pydantic schemas (API contracts)    │
├─────────────────────────────────────────────────────────┤
│  app/core/          Config, security, logging, metrics  │
└─────────────────────────────────────────────────────────┘
```

**Why this matters**: Each layer has a single responsibility. Routes handle HTTP concerns, services contain business logic, and DB handles persistence. This makes testing straightforward — services can be tested without HTTP, and DB operations can be tested without business logic.

## 4. Multi-Tenant Data Isolation

```mermaid
sequenceDiagram
    participant C as Client
    participant A as API (FastAPI)
    participant D as Database
    participant Q as Qdrant

    C->>A: Request + JWT + X-Tenant-ID
    A->>A: Verify JWT token
    A->>D: Check user_tenants (user_id, tenant_id)
    D-->>A: Access granted / denied
    A->>D: SELECT ... WHERE tenant_id = ?
    D-->>A: Tenant-scoped results
    A->>Q: Search(filter: tenant_id = ?)
    Q-->>A: Tenant-scoped vectors
    A-->>C: Response
```

Key isolation points:
- **API layer**: `get_tenant_id()` dependency verifies the user has access to the requested tenant
- **Database**: Every query includes `WHERE tenant_id = :tenant_id`
- **Qdrant**: Payload filter `{"must": [{"key": "tenant_id", "match": {"value": tenant_id}}]}`

## 5. Request Processing Pipeline

```mermaid
graph LR
    REQ[HTTP Request] --> MW1[Request ID<br/>Middleware]
    MW1 --> MW2[Security Headers<br/>Middleware]
    MW2 --> MW3[Trusted Host<br/>Middleware]
    MW3 --> MW4[CORS<br/>Middleware]
    MW4 --> AUTH[JWT Auth<br/>Dependency]
    AUTH --> ROLE[Role Check<br/>Dependency]
    ROLE --> TENANT[Tenant Check<br/>Dependency]
    TENANT --> HANDLER[Route Handler]
    HANDLER --> SVC[Service Layer]
    SVC --> DB[Database / Qdrant]
    HANDLER --> AUDIT[Audit Log]
    HANDLER --> RES[HTTP Response]
```

## 6. Document Ingestion Pipeline

```mermaid
sequenceDiagram
    participant U as User
    participant A as API
    participant R as Redis Queue
    participant W as RQ Worker
    participant E as Embedding Service
    participant Q as Qdrant
    participant D as Database
    participant F as File Storage

    U->>A: POST /ingest/file (multipart)
    A->>A: Validate extension, size
    A->>F: Save to upload storage
    A->>D: Create IngestJob (status=queued)
    A->>R: Enqueue job
    A-->>U: {job_id, status: "queued"}

    R->>W: Dequeue job
    W->>D: Update status=processing
    W->>W: Parse document (PDF/TXT/OCR)
    W->>W: Chunk text (smart/fixed)
    W->>E: Embed chunks
    E-->>W: Vectors
    W->>Q: Upsert vectors with metadata
    W->>D: Create Document record
    W->>F: Move to preview storage
    W->>D: Update IngestJob (status=completed)

    U->>A: GET /ingest/jobs/{id}
    A->>D: Query IngestJob
    A-->>U: {status: "completed", chunks_indexed: N}
```

## 7. Approval Policy Resolution

The approval decision follows a priority chain, evaluated from most specific to least:

```mermaid
graph TD
    Q[Should require approval?]
    Q --> D{Document has<br/>approval_override?}
    D -->|always| YES[✓ Require Approval]
    D -->|never| NO[✗ Skip Approval]
    D -->|null/inherit| T{Tenant policy<br/>approval_mode?}
    T -->|all| YES
    T -->|none| NO
    T -->|sensitive| S{Source documents<br/>contain sensitive?}
    S -->|yes| YES
    S -->|no| NO
    T -->|not set| G{Global setting<br/>APP_REQUIRE_APPROVAL?}
    G -->|true| YES
    G -->|false| NO
```

## 8. Scalability Path

| Component | Current | Scale Strategy |
|-----------|---------|---------------|
| API | Single container | Horizontal (ECS auto-scaling behind ALB) |
| Worker | Single container | Horizontal (scale by Redis queue depth) |
| PostgreSQL | Single instance | Managed RDS with read replicas |
| Redis | Single instance | ElastiCache with failover |
| Qdrant | Single instance | Vertical → distributed (sharding) |
| LLM | Ollama (local) | Switch to API providers (OpenAI/Gemini) for elastic scale |
| Embeddings | Local SentenceTransformer | Switch to API providers or GPU instances |

## 9. Non-Goals

This repository intentionally does not include:

- SSO/SAML/OIDC enterprise identity integration
- Full DLP (Data Loss Prevention) pipeline
- Multi-region active-active replication
- Complex ABAC/PBAC policy engine
- Legal document retention lifecycle management

These are expected next-stage enhancements after production adoption.
