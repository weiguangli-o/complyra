# Complyra API Reference

Base URL: `/api`

All endpoints are served over HTTPS in production. Request and response bodies use JSON (`application/json`) unless otherwise noted.

---

## Table of Contents

- [Authentication](#authentication)
- [Common Headers](#common-headers)
- [Error Responses](#error-responses)
- [RBAC Roles & Permissions](#rbac-roles--permissions)
- [Pagination](#pagination)
- [Rate Limiting](#rate-limiting)
- [Endpoints](#endpoints)
  - [Auth](#auth)
  - [Chat](#chat)
  - [Documents](#documents)
  - [Ingest](#ingest)
  - [Approvals](#approvals)
  - [Audit](#audit)
  - [Tenants](#tenants)
  - [Users](#users)
  - [Health](#health)
  - [Monitoring](#monitoring)

---

## Authentication

Complyra uses **JWT Bearer tokens** for authentication. Tokens are obtained via the login endpoint and must be included in subsequent requests.

### Obtaining a Token

Call `POST /api/auth/login` with valid credentials. The response includes an `access_token` field. The server also sets an `HttpOnly` cookie containing the token for browser-based clients.

### Using the Token

Provide the token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

Browser clients can rely on the `HttpOnly` cookie instead; it is sent automatically with each request.

### Token Lifetime

Tokens expire after the configured TTL (default: 60 minutes). After expiry, the client must re-authenticate.

---

## Common Headers

| Header         | Required | Description                                                                 |
|----------------|----------|-----------------------------------------------------------------------------|
| `Authorization`| Yes*     | `Bearer <access_token>`. Required for all endpoints except `/auth/login`, `/health/*`. |
| `Content-Type` | Yes**    | `application/json` for JSON bodies; `multipart/form-data` for file uploads. |
| `X-Tenant-ID`  | Conditional | UUID of the target tenant. Required for tenant-scoped operations such as `/chat`. If omitted, the user's `default_tenant_id` is used. |

\* Not required when the `HttpOnly` cookie is present.

\** Not required for GET/DELETE requests without a body.

---

## Error Responses

All error responses follow a consistent shape:

```json
{
  "detail": "Human-readable error message"
}
```

For validation errors (422), FastAPI returns:

```json
{
  "detail": [
    {
      "loc": ["body", "username"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### Standard HTTP Status Codes

| Code | Meaning               | When                                                        |
|------|-----------------------|-------------------------------------------------------------|
| 400  | Bad Request           | Malformed request or business-logic violation.              |
| 401  | Unauthorized          | Missing, expired, or invalid token.                         |
| 403  | Forbidden             | Authenticated but insufficient role for the resource.       |
| 404  | Not Found             | Resource does not exist or has been soft-deleted.            |
| 409  | Conflict              | Duplicate resource (e.g., username already exists).         |
| 422  | Unprocessable Entity  | Request body fails schema validation.                       |
| 500  | Internal Server Error | Unexpected server-side failure.                             |

#### Example: 401 Unauthorized

```http
HTTP/1.1 401 Unauthorized
Content-Type: application/json

{
  "detail": "Could not validate credentials"
}
```

#### Example: 403 Forbidden

```http
HTTP/1.1 403 Forbidden
Content-Type: application/json

{
  "detail": "Admin role required"
}
```

#### Example: 404 Not Found

```http
HTTP/1.1 404 Not Found
Content-Type: application/json

{
  "detail": "Document not found"
}
```

#### Example: 422 Validation Error

```http
HTTP/1.1 422 Unprocessable Entity
Content-Type: application/json

{
  "detail": [
    {
      "loc": ["body", "password"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

## RBAC Roles & Permissions

Complyra enforces role-based access control at the endpoint level. Each user is assigned exactly one role.

| Capability                        | `admin` | `auditor` | `user` |
|-----------------------------------|:-------:|:---------:|:------:|
| Login / Logout                    |    Y    |     Y     |   Y    |
| Chat (ask questions)              |    Y    |     Y     |   Y    |
| List / view documents             |    Y    |     Y     |   --   |
| Update document sensitivity       |    Y    |    --     |   --   |
| Delete documents                  |    Y    |    --     |   --   |
| Bulk document operations          |    Y    |    --     |   --   |
| Preview document file             |    Y    |     Y     |   Y    |
| Ingest files                      |    Y    |     Y     |   Y    |
| List pending approvals            |    Y    |     Y     |   --   |
| Approve / reject approvals        |    Y    |     Y     |   --   |
| View approval results             |    Y    |     Y     |   Y    |
| Query audit logs                  |    Y    |     Y     |   --   |
| Export audit logs (CSV)           |    Y    |     Y     |   --   |
| Manage tenants                    |    Y    |    --     |   --   |
| View / update tenant policy       |    Y    |     Y     |   --   |
| Manage users                      |    Y    |    --     |   --   |
| View health checks                |    Y    |     Y     |   Y    |
| View Prometheus metrics           |  token  |   token   | token  |

---

## Pagination

List endpoints that return collections support **offset-based pagination** using two query parameters:

| Parameter | Type | Default | Constraints      | Description                    |
|-----------|------|---------|------------------|--------------------------------|
| `limit`   | int  | 50      | 1 -- 500         | Maximum number of items to return. |
| `offset`  | int  | 0       | >= 0             | Number of items to skip.       |

Paginated responses include a `total` field with the full count:

```json
{
  "items": [ ... ],
  "total": 142
}
```

**Example:** Fetch the second page of 20 items:

```
GET /api/documents/?limit=20&offset=20
```

---

## Rate Limiting

Complyra does **not** implement application-level rate limiting. It is designed to sit behind a reverse proxy (e.g., Nginx, AWS ALB, Cloudflare) that enforces rate limits. Consult your infrastructure documentation for configuration details.

---

## Endpoints

### Auth

#### POST `/api/auth/login`

Authenticate a user and obtain a JWT token.

**Authentication:** None

**Request Body:**

```json
{
  "username": "alice",
  "password": "s3cret!"
}
```

| Field      | Type   | Required | Description        |
|------------|--------|----------|--------------------|
| `username` | string | Yes      | The user's login name. |
| `password` | string | Yes      | The user's password.   |

**Response: 200 OK**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "role": "admin",
  "user_id": "b2f7c8a1-3e4d-4f5a-9b1c-6d7e8f9a0b1c",
  "default_tenant_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

The response also sets an `HttpOnly` cookie named `access_token`.

**Errors:** 401 (invalid credentials)

---

#### POST `/api/auth/logout`

Clear the authentication cookie.

**Authentication:** Bearer token or cookie

**Request Body:** None

**Response: 200 OK**

```json
{
  "message": "Logged out"
}
```

---

### Chat

#### POST `/api/chat/`

Submit a compliance question. The system retrieves relevant document chunks, checks approval policy, and generates an answer.

**Authentication:** Required

**Headers:** `X-Tenant-ID` (optional; falls back to user's default tenant)

**Request Body:**

```json
{
  "question": "What is our data retention policy for customer PII?"
}
```

| Field      | Type   | Required | Description                |
|------------|--------|----------|----------------------------|
| `question` | string | Yes      | The compliance question.   |

**Response: 200 OK** (policy passed)

```json
{
  "status": "completed",
  "answer": "According to the Data Retention Policy (DRP-2024-003), customer PII must be deleted within 90 days of account closure...",
  "retrieved": [
    {
      "text": "Section 4.2: Personal data retention periods...",
      "score": 0.92,
      "source": "data-retention-policy-v3.pdf",
      "page_numbers": [12, 13]
    },
    {
      "text": "GDPR Article 17 compliance requirements...",
      "score": 0.87,
      "source": "gdpr-handbook.pdf",
      "page_numbers": [45]
    }
  ]
}
```

**Response: 200 OK** (approval required)

```json
{
  "status": "pending_approval",
  "answer": null,
  "retrieved": [ ... ],
  "approval_id": "d4e5f6a7-b8c9-0d1e-2f3a-4b5c6d7e8f9a"
}
```

When `status` is `"pending_approval"`, the answer is withheld until an admin or auditor approves the request via the Approvals endpoint. The client should poll `GET /api/approvals/{approval_id}/result` or display a waiting state.

**Errors:** 401, 403, 422

---

#### POST `/api/chat/stream`

Same as `POST /api/chat/` but returns a **Server-Sent Events (SSE)** stream, enabling real-time UI updates as the pipeline progresses.

**Authentication:** Required

**Headers:** `X-Tenant-ID` (optional)

**Request Body:** Same as `POST /api/chat/`

**Response:** `text/event-stream`

Each SSE message has an `event` field and a JSON `data` payload. Events are emitted in pipeline order:

| Event               | Data                              | Description                                    |
|---------------------|-----------------------------------|------------------------------------------------|
| `rewrite_start`     | `{}`                              | Query rewriting has begun.                     |
| `rewrite_done`      | `{"rewritten": "..."}`            | Rewritten query text.                          |
| `retrieve_start`    | `{}`                              | Document retrieval has begun.                  |
| `retrieve_done`     | `{"retrieved": [...]}`            | Retrieved chunks (same schema as non-streaming).|
| `judge_start`       | `{}`                              | Approval policy evaluation has begun.          |
| `judge_done`        | `{"policy": "passed"|"blocked"|"approval_required"}` | Policy decision.            |
| `generate_start`    | `{}`                              | LLM answer generation has begun.               |
| `token`             | `{"t": "word "}`                  | Incremental token from the LLM.                |
| `policy_passed`     | `{"answer": "..."}`              | Final answer (policy passed).                  |
| `policy_blocked`    | `{"reason": "..."}`              | Answer blocked by policy.                      |
| `approval_required` | `{"approval_id": "..."}`         | Answer held pending approval.                  |
| `done`              | `{}`                              | Stream complete.                               |

**Example SSE stream:**

```
event: rewrite_start
data: {}

event: rewrite_done
data: {"rewritten": "What is the data retention policy for customer personally identifiable information (PII)?"}

event: retrieve_start
data: {}

event: retrieve_done
data: {"retrieved": [{"text": "...", "score": 0.92, "source": "policy.pdf", "page_numbers": [12]}]}

event: judge_start
data: {}

event: judge_done
data: {"policy": "passed"}

event: generate_start
data: {}

event: token
data: {"t": "According "}

event: token
data: {"t": "to "}

event: token
data: {"t": "the "}

event: policy_passed
data: {"answer": "According to the Data Retention Policy..."}

event: done
data: {}
```

---

### Documents

#### GET `/api/documents/`

List documents with optional filters.

**Authentication:** Required (admin, auditor)

**Query Parameters:**

| Parameter     | Type   | Default  | Description                                      |
|---------------|--------|----------|--------------------------------------------------|
| `status`      | string | `active` | Filter by status: `active`, `archived`, `deleted`, `all`. |
| `sensitivity` | string | --       | Filter by sensitivity: `normal`, `sensitive`, `restricted`. |
| `limit`       | int    | 50       | Page size (1--500).                               |
| `offset`      | int    | 0        | Items to skip.                                    |

**Response: 200 OK**

```json
{
  "items": [
    {
      "id": "c3d4e5f6-a7b8-9c0d-1e2f-3a4b5c6d7e8f",
      "filename": "data-retention-policy-v3.pdf",
      "status": "active",
      "sensitivity": "sensitive",
      "approval_override": false,
      "chunk_count": 24,
      "created_at": "2025-11-15T08:30:00Z",
      "updated_at": "2025-11-15T08:30:00Z"
    }
  ],
  "total": 87
}
```

**Errors:** 401, 403

---

#### GET `/api/documents/{document_id}`

Get full details of a single document.

**Authentication:** Required (admin, auditor)

**Path Parameters:**

| Parameter     | Type | Description          |
|---------------|------|----------------------|
| `document_id` | UUID | The document's ID.   |

**Response: 200 OK**

Returns the full document object including metadata and chunk information.

**Errors:** 401, 403, 404

---

#### PATCH `/api/documents/{document_id}`

Update a document's sensitivity level or approval override flag.

**Authentication:** Required (admin)

**Path Parameters:**

| Parameter     | Type | Description          |
|---------------|------|----------------------|
| `document_id` | UUID | The document's ID.   |

**Request Body:**

```json
{
  "sensitivity": "restricted",
  "approval_override": true
}
```

| Field               | Type    | Required | Description                                              |
|---------------------|---------|----------|----------------------------------------------------------|
| `sensitivity`       | string  | No       | New sensitivity level: `normal`, `sensitive`, `restricted`. |
| `approval_override` | boolean | No       | If `true`, answers citing this document always require approval. |

At least one field must be provided.

**Response: 200 OK**

Returns the updated document object.

**Errors:** 401, 403, 404, 422

---

#### DELETE `/api/documents/{document_id}`

Soft-delete a document. The document record is marked as `deleted` and its vectors are removed from the Qdrant collection.

**Authentication:** Required (admin)

**Path Parameters:**

| Parameter     | Type | Description          |
|---------------|------|----------------------|
| `document_id` | UUID | The document's ID.   |

**Response: 200 OK**

```json
{
  "message": "Document deleted",
  "document_id": "c3d4e5f6-a7b8-9c0d-1e2f-3a4b5c6d7e8f"
}
```

**Errors:** 401, 403, 404

---

#### POST `/api/documents/bulk`

Perform a bulk action on multiple documents.

**Authentication:** Required (admin)

**Request Body:**

```json
{
  "document_ids": [
    "c3d4e5f6-a7b8-9c0d-1e2f-3a4b5c6d7e8f",
    "d4e5f6a7-b8c9-0d1e-2f3a-4b5c6d7e8f9a"
  ],
  "action": "update_sensitivity",
  "sensitivity": "restricted"
}
```

| Field          | Type     | Required    | Description                                               |
|----------------|----------|-------------|-----------------------------------------------------------|
| `document_ids` | string[] | Yes         | List of document UUIDs.                                   |
| `action`       | string   | Yes         | `"delete"` or `"update_sensitivity"`.                     |
| `sensitivity`  | string   | Conditional | Required when `action` is `"update_sensitivity"`.         |

**Response: 200 OK**

```json
{
  "processed": 2,
  "failed": 0,
  "errors": []
}
```

**Errors:** 401, 403, 422

---

#### GET `/api/documents/{document_id}/preview`

Serve the original uploaded file for preview or download.

**Authentication:** Required (admin, auditor, user)

**Path Parameters:**

| Parameter     | Type | Description          |
|---------------|------|----------------------|
| `document_id` | UUID | The document's ID.   |

**Response: 200 OK**

Returns the binary file content with appropriate `Content-Type` and `Content-Disposition` headers.

> **Security:** Path traversal protection is enforced. Requests attempting to escape the storage directory are rejected with 400.

**Errors:** 400, 401, 403, 404

---

#### GET `/api/documents/legacy`

Legacy endpoint that lists documents directly from the Qdrant vector store. Provided for backward compatibility.

**Authentication:** Required

**Response: 200 OK**

Returns a list of document entries as stored in Qdrant.

---

### Ingest

#### POST `/api/ingest/file`

Upload a file for ingestion into the document pipeline. The file is parsed, chunked, embedded, and stored in Qdrant asynchronously.

**Authentication:** Required

**Content-Type:** `multipart/form-data`

**Form Fields:**

| Field  | Type | Required | Constraints                                        |
|--------|------|----------|----------------------------------------------------|
| `file` | file | Yes      | Max 20 MB. Allowed types: `pdf`, `txt`, `md`, `png`, `jpg`, `jpeg`. |

**Example (cURL):**

```bash
curl -X POST /api/ingest/file \
  -H "Authorization: Bearer <token>" \
  -F "file=@compliance-policy.pdf"
```

**Response: 202 Accepted**

```json
{
  "job_id": "e5f6a7b8-c9d0-1e2f-3a4b-5c6d7e8f9a0b",
  "status": "queued"
}
```

**Errors:** 400 (unsupported file type, file too large), 401, 422

---

#### GET `/api/ingest/jobs/{job_id}`

Check the status of an ingestion job.

**Authentication:** Required

**Path Parameters:**

| Parameter | Type | Description      |
|-----------|------|------------------|
| `job_id`  | UUID | The job's ID.    |

**Response: 200 OK**

```json
{
  "job_id": "e5f6a7b8-c9d0-1e2f-3a4b-5c6d7e8f9a0b",
  "status": "completed",
  "filename": "compliance-policy.pdf",
  "document_id": "c3d4e5f6-a7b8-9c0d-1e2f-3a4b5c6d7e8f",
  "chunk_count": 24,
  "created_at": "2025-11-15T08:30:00Z",
  "completed_at": "2025-11-15T08:30:45Z",
  "error": null
}
```

Possible `status` values: `queued`, `processing`, `completed`, `failed`.

When `status` is `"failed"`, the `error` field contains a description of the failure.

**Errors:** 401, 404

---

### Approvals

#### GET `/api/approvals/`

List pending approval requests.

**Authentication:** Required (admin, auditor)

**Query Parameters:**

| Parameter | Type | Default | Description        |
|-----------|------|---------|--------------------|
| `limit`   | int  | 50      | Page size (1--500). |
| `offset`  | int  | 0       | Items to skip.     |

**Response: 200 OK**

```json
{
  "items": [
    {
      "id": "d4e5f6a7-b8c9-0d1e-2f3a-4b5c6d7e8f9a",
      "user_id": "b2f7c8a1-3e4d-4f5a-9b1c-6d7e8f9a0b1c",
      "question": "What is our data retention policy for customer PII?",
      "status": "pending",
      "created_at": "2025-11-15T09:00:00Z"
    }
  ],
  "total": 3
}
```

**Errors:** 401, 403

---

#### POST `/api/approvals/{approval_id}/decision`

Approve or reject a pending approval request.

**Authentication:** Required (admin, auditor)

**Path Parameters:**

| Parameter     | Type | Description         |
|---------------|------|---------------------|
| `approval_id` | UUID | The approval's ID.  |

**Request Body:**

```json
{
  "approved": true,
  "note": "Verified — answer is appropriate for the requesting user."
}
```

| Field      | Type    | Required | Description                        |
|------------|---------|----------|------------------------------------|
| `approved` | boolean | Yes      | `true` to approve, `false` to reject. |
| `note`     | string  | No       | Optional reviewer note.            |

**Response: 200 OK**

```json
{
  "approval_id": "d4e5f6a7-b8c9-0d1e-2f3a-4b5c6d7e8f9a",
  "status": "approved",
  "decided_by": "b2f7c8a1-3e4d-4f5a-9b1c-6d7e8f9a0b1c",
  "decided_at": "2025-11-15T09:05:00Z"
}
```

**Errors:** 401, 403, 404 (approval not found or already decided)

---

#### GET `/api/approvals/{approval_id}/result`

Retrieve the outcome of an approval decision, including the released answer if approved.

**Authentication:** Required

**Path Parameters:**

| Parameter     | Type | Description         |
|---------------|------|---------------------|
| `approval_id` | UUID | The approval's ID.  |

**Response: 200 OK** (approved)

```json
{
  "approval_id": "d4e5f6a7-b8c9-0d1e-2f3a-4b5c6d7e8f9a",
  "status": "approved",
  "answer": "According to the Data Retention Policy...",
  "note": "Verified — answer is appropriate.",
  "decided_at": "2025-11-15T09:05:00Z"
}
```

**Response: 200 OK** (pending)

```json
{
  "approval_id": "d4e5f6a7-b8c9-0d1e-2f3a-4b5c6d7e8f9a",
  "status": "pending",
  "answer": null,
  "note": null,
  "decided_at": null
}
```

**Errors:** 401, 404

---

### Audit

#### GET `/api/audit/`

Query the audit log. All state-changing operations are recorded automatically.

**Authentication:** Required (admin, auditor)

**Query Parameters:**

| Parameter    | Type   | Default | Description                                |
|--------------|--------|---------|--------------------------------------------|
| `action`     | string | --      | Filter by action type (e.g., `login`, `chat`, `ingest`, `approve`, `delete_document`). |
| `user`       | string | --      | Filter by user ID.                         |
| `start_date` | string | --      | ISO 8601 datetime. Records on or after.    |
| `end_date`   | string | --      | ISO 8601 datetime. Records on or before.   |
| `limit`      | int    | 50      | Page size.                                  |
| `offset`     | int    | 0       | Items to skip.                              |

**Response: 200 OK**

```json
[
  {
    "id": "f6a7b8c9-d0e1-2f3a-4b5c-6d7e8f9a0b1c",
    "action": "chat",
    "user_id": "b2f7c8a1-3e4d-4f5a-9b1c-6d7e8f9a0b1c",
    "tenant_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "details": {
      "question": "What is our data retention policy?",
      "status": "completed"
    },
    "created_at": "2025-11-15T09:00:00Z"
  }
]
```

**Errors:** 401, 403

---

#### GET `/api/audit/export`

Export audit logs as a CSV file. Accepts the same filter parameters as `GET /api/audit/`.

**Authentication:** Required (admin, auditor)

**Query Parameters:** Same as `GET /api/audit/` (excluding `limit` and `offset` — all matching records are exported).

**Response: 200 OK**

```
Content-Type: text/csv
Content-Disposition: attachment; filename="audit-export-2025-11-15.csv"
```

**Errors:** 401, 403

---

### Tenants

#### GET `/api/tenants/`

List all tenants.

**Authentication:** Required (admin)

**Response: 200 OK**

```json
[
  {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "name": "Acme Corp",
    "created_at": "2025-10-01T00:00:00Z"
  }
]
```

**Errors:** 401, 403

---

#### POST `/api/tenants/`

Create a new tenant.

**Authentication:** Required (admin)

**Request Body:**

```json
{
  "name": "Acme Corp"
}
```

**Response: 201 Created**

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "name": "Acme Corp",
  "created_at": "2025-11-15T10:00:00Z"
}
```

**Errors:** 401, 403, 409 (duplicate name), 422

---

#### GET `/api/tenants/{tenant_id}/policy`

Get a tenant's approval policy configuration.

**Authentication:** Required (admin, auditor)

**Path Parameters:**

| Parameter   | Type | Description        |
|-------------|------|--------------------|
| `tenant_id` | UUID | The tenant's ID.   |

**Response: 200 OK**

```json
{
  "tenant_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "approval_mode": "sensitive"
}
```

| `approval_mode` | Behavior                                                        |
|------------------|-----------------------------------------------------------------|
| `all`            | All chat answers require approval before being shown to users.  |
| `sensitive`      | Only answers referencing sensitive/restricted documents require approval. |
| `none`           | No approval required; answers are returned immediately.         |

**Errors:** 401, 403, 404

---

#### PUT `/api/tenants/{tenant_id}/policy`

Update a tenant's approval policy.

**Authentication:** Required (admin)

**Path Parameters:**

| Parameter   | Type | Description        |
|-------------|------|--------------------|
| `tenant_id` | UUID | The tenant's ID.   |

**Request Body:**

```json
{
  "approval_mode": "all"
}
```

| Field           | Type   | Required | Description                                    |
|-----------------|--------|----------|------------------------------------------------|
| `approval_mode` | string | Yes      | One of `"all"`, `"sensitive"`, or `"none"`.    |

**Response: 200 OK**

Returns the updated policy object.

**Errors:** 401, 403, 404, 422

---

### Users

#### GET `/api/users/`

List all users.

**Authentication:** Required (admin)

**Response: 200 OK**

```json
[
  {
    "id": "b2f7c8a1-3e4d-4f5a-9b1c-6d7e8f9a0b1c",
    "username": "alice",
    "role": "admin",
    "default_tenant_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "created_at": "2025-10-01T00:00:00Z"
  }
]
```

**Errors:** 401, 403

---

#### POST `/api/users/`

Create a new user.

**Authentication:** Required (admin)

**Request Body:**

```json
{
  "username": "bob",
  "password": "str0ng_p@ssw0rd",
  "role": "auditor",
  "default_tenant_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

| Field               | Type   | Required | Description                                    |
|---------------------|--------|----------|------------------------------------------------|
| `username`          | string | Yes      | Unique login name.                             |
| `password`          | string | Yes      | Password (hashed before storage).              |
| `role`              | string | Yes      | One of `"admin"`, `"auditor"`, or `"user"`.    |
| `default_tenant_id` | string | No       | UUID of the user's default tenant.             |

**Response: 201 Created**

Returns the created user object (password excluded).

**Errors:** 401, 403, 409 (duplicate username), 422

---

#### POST `/api/users/{user_id}/tenants`

Assign a tenant to a user, granting access to that tenant's documents and chat scope.

**Authentication:** Required (admin)

**Path Parameters:**

| Parameter | Type | Description      |
|-----------|------|------------------|
| `user_id` | UUID | The user's ID.   |

**Request Body:**

```json
{
  "tenant_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

| Field       | Type   | Required | Description                |
|-------------|--------|----------|----------------------------|
| `tenant_id` | string | Yes      | UUID of the tenant to assign. |

**Response: 200 OK**

```json
{
  "message": "Tenant assigned",
  "user_id": "b2f7c8a1-3e4d-4f5a-9b1c-6d7e8f9a0b1c",
  "tenant_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**Errors:** 401, 403, 404 (user or tenant not found), 409 (already assigned)

---

### Health

Health check endpoints do **not** require authentication.

#### GET `/api/health/live`

Liveness probe. Returns 200 if the application process is running.

**Response: 200 OK**

```json
{
  "status": "ok"
}
```

---

#### GET `/api/health/ready`

Readiness probe. Returns 200 only if all downstream dependencies are reachable.

**Response: 200 OK**

```json
{
  "status": "ready",
  "checks": {
    "database": "ok",
    "qdrant": "ok",
    "ollama": "ok"
  }
}
```

**Response: 503 Service Unavailable**

```json
{
  "status": "not_ready",
  "checks": {
    "database": "ok",
    "qdrant": "error",
    "ollama": "ok"
  }
}
```

---

### Monitoring

#### GET `/api/monitoring/metrics`

Expose Prometheus-format metrics for scraping.

**Authentication:** Requires a `metrics_token` query parameter or header matching the server's configured metrics secret. This is **not** a JWT token — it is a separate static secret.

**Example:**

```
GET /api/monitoring/metrics?metrics_token=<secret>
```

**Response: 200 OK**

```
Content-Type: text/plain; version=0.0.4; charset=utf-8

# HELP complyra_requests_total Total HTTP requests
# TYPE complyra_requests_total counter
complyra_requests_total{method="POST",endpoint="/api/chat/",status="200"} 1452
...
```

**Errors:** 401 (invalid or missing metrics token)
