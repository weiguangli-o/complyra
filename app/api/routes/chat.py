"""Chat API endpoints.

Provides both synchronous (``POST /chat/``) and streaming
(``POST /chat/stream``) question-answering endpoints with
tenant-scoped retrieval, policy checks, and approval workflow.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user, get_tenant_id
from app.core.config import settings
from app.models.schemas import ChatRequest, ChatResponse, RetrievedChunk
from app.services.approvals import create_approval_request
from app.services.audit import log_event
from app.services.llm import generate_answer_stream
from app.services.policy import evaluate_output_policy
from app.services.retrieval import search_chunks
from app.services.workflow import run_workflow

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user),
) -> ChatResponse:
    """Synchronous chat endpoint — returns a complete JSON response."""
    state = run_workflow(payload.question, tenant_id, user["user_id"])
    matches = state.get("retrieved", [])
    approval_required = state.get("approval_required", False)
    approval_id = state.get("approval_id")
    policy_blocked = state.get("policy_blocked", False)
    policy_violations = state.get("policy_violations", [])

    retrieved = [
        RetrievedChunk(text=text, score=score, source=source)
        for text, score, source in matches
    ]

    if approval_required:
        answer = "Your request is pending human approval."
        status = "pending_approval"
    else:
        answer = state.get("draft_answer", "")
        status = "completed"

    if policy_blocked:
        action = "chat_blocked_by_policy"
    elif approval_required:
        action = "chat_pending"
    else:
        action = "chat_completed"

    log_event(
        tenant_id=tenant_id,
        user=user["username"],
        action=action,
        input_text=payload.question,
        output_text=answer,
        metadata=json.dumps(
            {
                "approval_id": approval_id or "",
                "policy_blocked": policy_blocked,
                "policy_violations": policy_violations,
            }
        ),
    )

    return ChatResponse(
        status=status, answer=answer, retrieved=retrieved, approval_id=approval_id
    )


def _sse_event(event: str, data: dict) -> str:
    """Format a Server-Sent Events message."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/stream")
async def chat_stream(
    payload: ChatRequest,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user),
):
    """Streaming chat endpoint — returns Server-Sent Events with
    retrieval results, token-by-token LLM output, policy check,
    and approval status.
    """

    async def event_generator():
        # Step 1: Retrieve relevant documents
        yield _sse_event("retrieve_start", {})
        matches = search_chunks(payload.question, settings.top_k, tenant_id)
        retrieved = [
            {"text": t, "score": s, "source": src} for t, s, src in matches
        ]
        yield _sse_event("retrieve_done", {"retrieved": retrieved})

        # Step 2: Stream LLM generation token by token
        yield _sse_event("generate_start", {})
        contexts = [t for t, _, _ in matches]
        sources = [src for _, _, src in matches]
        full_answer: list[str] = []
        async for token in generate_answer_stream(payload.question, contexts, sources):
            full_answer.append(token)
            yield _sse_event("token", {"text": token})

        # Step 3: Output policy check
        answer_text = "".join(full_answer)
        policy_result = evaluate_output_policy(answer_text)
        if policy_result.blocked:
            yield _sse_event(
                "policy_blocked", {"violations": policy_result.matched_rules}
            )
            answer_text = settings.output_policy_block_message
        else:
            yield _sse_event("policy_passed", {})

        # Step 4: Approval workflow
        approval_id = None
        if not policy_result.blocked and settings.require_approval:
            approval_id = create_approval_request(
                user_id=user["user_id"],
                tenant_id=tenant_id,
                question=payload.question,
                draft_answer=answer_text,
            )
            yield _sse_event(
                "approval_required", {"approval_id": approval_id}
            )
        else:
            yield _sse_event("done", {"answer": answer_text})

        # Audit log
        if policy_result.blocked:
            action = "chat_stream_blocked_by_policy"
        elif approval_id:
            action = "chat_stream_pending"
        else:
            action = "chat_stream_completed"

        log_event(
            tenant_id=tenant_id,
            user=user["username"],
            action=action,
            input_text=payload.question,
            output_text=answer_text,
            metadata=json.dumps(
                {
                    "approval_id": approval_id or "",
                    "policy_blocked": policy_result.blocked,
                    "policy_violations": policy_result.matched_rules,
                    "streaming": True,
                }
            ),
        )

    return StreamingResponse(event_generator(), media_type="text/event-stream")
