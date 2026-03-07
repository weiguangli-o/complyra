"""LangGraph-based RAG workflow.

Defines a state-machine workflow with the following stages:
  1. **Retrieve** — vector search for relevant document chunks
  2. **Draft** — LLM answer generation with output policy check
  3. **Approval** — optional human-in-the-loop approval
  4. **Final** — pass-through when no approval is required

The graph is compiled once at module level and reused for every request.
"""

from __future__ import annotations

from typing import List, Tuple, TypedDict

from langgraph.graph import END, START, StateGraph

from app.core.config import settings
from app.services.approvals import create_approval_request
from app.services.llm import generate_answer
from app.services.policy import evaluate_output_policy
from app.services.retrieval import search_chunks


class WorkflowState(TypedDict, total=False):
    """Typed dictionary carrying data through the workflow graph."""

    question: str
    tenant_id: str
    user_id: str
    retrieved: List[Tuple[str, float, str]]
    draft_answer: str
    policy_blocked: bool
    policy_violations: List[str]
    approval_required: bool
    approval_id: str


def retrieve_node(state: WorkflowState) -> WorkflowState:
    """Search Qdrant for the top-k chunks matching the user question,
    scoped to the request's tenant."""
    matches = search_chunks(state["question"], settings.top_k, state["tenant_id"])
    return {"retrieved": matches}


def draft_node(state: WorkflowState) -> WorkflowState:
    """Generate an LLM answer from retrieved contexts, then run the
    output policy evaluator to check for sensitive patterns."""
    contexts = [text for text, _, _ in state.get("retrieved", [])]
    sources = [source for _, _, source in state.get("retrieved", [])]
    raw_answer = generate_answer(state["question"], contexts, sources)
    policy_result = evaluate_output_policy(raw_answer)
    return {
        "draft_answer": policy_result.answer,
        "policy_blocked": policy_result.blocked,
        "policy_violations": policy_result.matched_rules,
    }


def approval_node(state: WorkflowState) -> WorkflowState:
    """Create a pending approval request so a human reviewer can
    approve or reject the generated answer before it is released."""
    approval_id = create_approval_request(
        user_id=state["user_id"],
        tenant_id=state["tenant_id"],
        question=state["question"],
        draft_answer=state["draft_answer"],
    )
    return {"approval_required": True, "approval_id": approval_id}


def final_node(_: WorkflowState) -> WorkflowState:
    """Terminal node — marks the answer as not requiring approval."""
    return {"approval_required": False}


def route_after_draft(state: WorkflowState) -> str:
    """Conditional edge: skip approval when the policy blocked the answer
    or when the approval feature is disabled."""
    if state.get("policy_blocked"):
        return "final"
    return "approval" if settings.require_approval else "final"


# ── Build the LangGraph state graph ──────────────────────────────────────────
builder = StateGraph(WorkflowState)

# Register nodes
builder.add_node("retrieve", retrieve_node)
builder.add_node("draft", draft_node)
builder.add_node("approval", approval_node)
builder.add_node("final", final_node)

# Wire edges: START -> retrieve -> draft -> (conditional) -> END
builder.add_edge(START, "retrieve")
builder.add_edge("retrieve", "draft")
builder.add_conditional_edges(
    "draft",
    route_after_draft,
    {"approval": "approval", "final": "final"},
)
builder.add_edge("approval", END)
builder.add_edge("final", END)

# Compile once — the compiled graph is thread-safe and reusable
workflow_graph = builder.compile()


def run_workflow(question: str, tenant_id: str, user_id: str) -> WorkflowState:
    """Execute the full RAG workflow and return the final state."""
    return workflow_graph.invoke(
        {"question": question, "tenant_id": tenant_id, "user_id": user_id}
    )
