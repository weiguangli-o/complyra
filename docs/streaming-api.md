# Streaming Chat API (SSE)

## Endpoint

```
POST /api/chat/stream
```

## Request

```json
{
  "question": "What is the company's data retention policy?"
}
```

**Headers:**
- `Authorization: Bearer <token>` (required)
- `X-Tenant-ID: <tenant_id>` (optional, defaults to user's default tenant)

## Response

The response is a stream of [Server-Sent Events (SSE)](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events). Each event has an `event` type and a JSON `data` payload.

### Event Types

| Event | Data | Description |
|-------|------|-------------|
| `retrieve_start` | `{}` | Retrieval phase started |
| `retrieve_done` | `{"retrieved": [...]}` | Retrieval complete with matched chunks |
| `generate_start` | `{}` | LLM generation started |
| `token` | `{"text": "..."}` | Single token from the LLM |
| `policy_passed` | `{}` | Output policy check passed |
| `policy_blocked` | `{"violations": [...]}` | Answer blocked by policy |
| `approval_required` | `{"approval_id": "..."}` | Answer pending human approval |
| `done` | `{"answer": "..."}` | Final answer (when no approval needed) |

### Event Flow

```
retrieve_start -> retrieve_done -> generate_start -> token* -> policy_passed -> done
                                                             -> policy_blocked
                                                             -> approval_required
```

### Example SSE Stream

```
event: retrieve_start
data: {}

event: retrieve_done
data: {"retrieved": [{"text": "Data is retained for 7 years...", "score": 0.92, "source": "policy.pdf"}]}

event: generate_start
data: {}

event: token
data: {"text": "According"}

event: token
data: {"text": " to"}

event: token
data: {"text": " the"}

event: token
data: {"text": " policy"}

event: token
data: {"text": ","}

event: token
data: {"text": " data"}

event: token
data: {"text": " is"}

event: token
data: {"text": " retained"}

event: token
data: {"text": " for"}

event: token
data: {"text": " 7"}

event: token
data: {"text": " years."}

event: policy_passed
data: {}

event: done
data: {"answer": "According to the policy, data is retained for 7 years."}

```

## Client Example (JavaScript)

```javascript
function chatStream(question, onEvent) {
  const controller = new AbortController();
  fetch("/api/chat/stream", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`,
    },
    body: JSON.stringify({ question }),
    signal: controller.signal,
  }).then(async (res) => {
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split("\n\n");
      buffer = blocks.pop();
      for (const block of blocks) {
        const eventMatch = block.match(/^event: (.+)$/m);
        const dataMatch = block.match(/^data: (.+)$/m);
        if (eventMatch && dataMatch) {
          onEvent(eventMatch[1], JSON.parse(dataMatch[1]));
        }
      }
    }
  });
  return controller; // call controller.abort() to cancel
}
```

## Backwards Compatibility

The synchronous `POST /api/chat/` endpoint remains unchanged and returns a complete JSON response. The streaming endpoint is opt-in.
