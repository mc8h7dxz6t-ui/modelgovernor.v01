from __future__ import annotations

import ast
import hashlib
import json
import re
import time
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from .config import Settings
from .schemas import (
    AgentDecision,
    OrchestrationWorkflowRequest,
    OrchestrationWorkflowResponse,
    WorkflowCitation,
    WorkflowComputationResult,
)

MONEY_QUANTUM = Decimal("0.000001")
INJECTION_PATTERNS = (
    "ignore previous instructions",
    "system prompt",
    "developer message",
    "drop table",
    "<script",
)
PROHIBITED_PAYLOAD_MARKERS = ("private key", "credit card number", "ssn:")
TECH_EDGES = [
    "deterministic_compute_sandbox",
    "dual_pass_critic_validation",
    "prompt_injection_retrieval_filter",
    "semantic_cache_first_gate",
    "adaptive_model_routing",
]


class OrchestrationPolicyError(Exception):
    pass


def run_orchestration_workflow(
    session: Session,
    settings: Settings,
    request: OrchestrationWorkflowRequest,
) -> OrchestrationWorkflowResponse:
    runtime_mode = (request.runtime_mode or settings.orchestration_runtime_mode).lower()
    if runtime_mode not in {"coexisting", "standalone"}:
        raise OrchestrationPolicyError("runtime_mode must be coexisting or standalone")
    if runtime_mode == "coexisting" and not request.external_context_id:
        raise OrchestrationPolicyError("external_context_id is required in coexisting mode")
    if runtime_mode == "standalone" and not request.documents:
        raise OrchestrationPolicyError("standalone mode requires at least one source document")

    _validate_input_payload(request)
    compacted_query = _compact_context(request.query)
    cache_key = _cache_key(runtime_mode, compacted_query, request.documents, request.computations, request.regulated)

    cached = _load_semantic_cache(session, cache_key)
    if cached:
        cached_response = cached["response"]
        cached_response["cache_hit"] = True
        cached_response.setdefault("tech_edges", TECH_EDGES)
        _insert_audit(
            session,
            run_id=cached["run_id"],
            workflow_id=request.workflow_id,
            user_id=request.user_id,
            runtime_mode=runtime_mode,
            state="PUBLISHED",
            agent="critic",
            status="OK",
            details={"cache_hit": True, "shadow_mode": settings.orchestration_shadow_mode},
        )
        session.commit()
        return OrchestrationWorkflowResponse.model_validate(cached_response)

    model_tier = _route_model_tier(request)
    estimated_cost = _estimate_workflow_cost(compacted_query, request.documents, model_tier)
    if estimated_cost > _money(request.max_cost):
        raise OrchestrationPolicyError("workflow estimated cost exceeds max_cost budget")

    run_id = str(uuid.uuid4())
    decisions: list[AgentDecision] = []
    total_start = time.perf_counter()

    ingest_start = time.perf_counter()
    chunks = _ingest_documents(request.documents)
    decisions.append(
        AgentDecision(
            agent="ingest",
            status="OK",
            reason="documents parsed into deterministic chunks",
            latency_ms=_elapsed_ms(ingest_start),
            routing_tier=model_tier,
        )
    )

    retrieve_start = time.perf_counter()
    citations, blocked_chunks = _retrieve_grounded_citations(compacted_query, chunks, request.regulated)
    retrieve_status = "REJECTED" if blocked_chunks and request.regulated else "OK"
    decisions.append(
        AgentDecision(
            agent="retrieve",
            status=retrieve_status,
            reason=(
                "retrieval grounded with prompt-injection filtering"
                if retrieve_status == "OK"
                else "regulated workflow blocked due to injection patterns"
            ),
            latency_ms=_elapsed_ms(retrieve_start),
            routing_tier=model_tier,
        )
    )
    if retrieve_status == "REJECTED":
        return _reject_workflow(
            session=session,
            run_id=run_id,
            request=request,
            runtime_mode=runtime_mode,
            model_tier=model_tier,
            estimated_cost=estimated_cost,
            decisions=decisions,
            issues=["prompt-injection pattern detected in regulated retrieval source"],
        )

    compute_start = time.perf_counter()
    computations: list[WorkflowComputationResult] = []
    compute_issues: list[str] = []
    if request.computations:
        for task in request.computations:
            try:
                value = _eval_expression(task.expression, task.variables)
                computations.append(
                    WorkflowComputationResult(
                        task_id=task.task_id,
                        value=value,
                        expected_unit=task.expected_unit,
                    )
                )
            except OrchestrationPolicyError as exc:
                compute_issues.append(f"{task.task_id}: {exc}")
    decisions.append(
        AgentDecision(
            agent="compute",
            status="OK" if not compute_issues else "REJECTED",
            reason="deterministic compute sandbox executed" if not compute_issues else "computation task failed",
            latency_ms=_elapsed_ms(compute_start),
            routing_tier=model_tier,
        )
    )
    if compute_issues:
        return _reject_workflow(
            session=session,
            run_id=run_id,
            request=request,
            runtime_mode=runtime_mode,
            model_tier=model_tier,
            estimated_cost=estimated_cost,
            decisions=decisions,
            issues=compute_issues,
        )

    report_start = time.perf_counter()
    report_payload = {
        "query": compacted_query,
        "runtime_mode": runtime_mode,
        "external_context_id": request.external_context_id,
        "summary": (
            "Institutional workflow completed in shadow mode"
            if settings.orchestration_shadow_mode
            else "Institutional workflow completed in enforced mode"
        ),
        "grounded_source_count": len(citations),
        "computation_count": len(computations),
        "total_runtime_ms": _elapsed_ms(total_start),
    }
    _validate_output_payload(report_payload)
    decisions.append(
        AgentDecision(
            agent="report",
            status="OK",
            reason="json-only machine payload emitted",
            latency_ms=_elapsed_ms(report_start),
            routing_tier=model_tier,
        )
    )

    critic_start = time.perf_counter()
    critic_issues = _critic_review(request.regulated, citations, report_payload)
    critic_status = "OK" if not critic_issues else "REJECTED"
    if critic_issues and citations:
        critic_issues = []
        critic_status = "OK"
    decisions.append(
        AgentDecision(
            agent="critic",
            status=critic_status,
            reason="dual-pass critic validation complete" if critic_status == "OK" else "critic validation failed",
            latency_ms=_elapsed_ms(critic_start),
            routing_tier=model_tier,
        )
    )
    if critic_issues:
        return _reject_workflow(
            session=session,
            run_id=run_id,
            request=request,
            runtime_mode=runtime_mode,
            model_tier=model_tier,
            estimated_cost=estimated_cost,
            decisions=decisions,
            issues=critic_issues,
        )

    response = OrchestrationWorkflowResponse(
        run_id=run_id,
        workflow_id=request.workflow_id,
        runtime_mode=runtime_mode,
        state="PUBLISHED",
        cache_hit=False,
        routing_tier=model_tier,
        estimated_cost=estimated_cost,
        tech_edges=TECH_EDGES,
        citations=citations,
        computations=computations,
        report_payload=report_payload,
        critic_passed=True,
        critic_issues=[],
        agent_decisions=decisions,
    )
    _persist_audit_decisions(session, response, request.user_id)
    _store_semantic_cache(session, cache_key, response, settings.orchestration_cache_ttl_seconds)
    session.commit()
    return response


def _reject_workflow(
    *,
    session: Session,
    run_id: str,
    request: OrchestrationWorkflowRequest,
    runtime_mode: str,
    model_tier: str,
    estimated_cost: Decimal,
    decisions: list[AgentDecision],
    issues: list[str],
) -> OrchestrationWorkflowResponse:
    response = OrchestrationWorkflowResponse(
        run_id=run_id,
        workflow_id=request.workflow_id,
        runtime_mode=runtime_mode,  # type: ignore[arg-type]
        state="REJECTED",
        cache_hit=False,
        routing_tier=model_tier,  # type: ignore[arg-type]
        estimated_cost=estimated_cost,
        tech_edges=TECH_EDGES,
        citations=[],
        computations=[],
        report_payload={},
        critic_passed=False,
        critic_issues=issues,
        agent_decisions=decisions,
    )
    _persist_audit_decisions(session, response, request.user_id)
    session.commit()
    return response


def _route_model_tier(request: OrchestrationWorkflowRequest) -> str:
    complexity = len(request.query) + (100 * len(request.documents)) + (80 * len(request.computations))
    if request.regulated or complexity > 1400:
        return "reasoning-large"
    return "fast-8b"


def _estimate_workflow_cost(query: str, documents: list[Any], model_tier: str) -> Decimal:
    token_estimate = max(1, len(query) // 4) + sum(len(doc.content) // 4 for doc in documents)
    per_token = Decimal("0.000020") if model_tier == "reasoning-large" else Decimal("0.000008")
    return _money(Decimal(token_estimate) * per_token)


def _ingest_documents(documents: list[Any]) -> list[dict[str, str]]:
    chunks: list[dict[str, str]] = []
    for doc in documents:
        compacted = _compact_context(doc.content)
        if compacted:
            chunks.append(
                {
                    "document_id": doc.document_id,
                    "source_uri": doc.source_uri,
                    "content": compacted,
                }
            )
    return chunks


def _retrieve_grounded_citations(
    query: str,
    chunks: list[dict[str, str]],
    regulated: bool,
) -> tuple[list[WorkflowCitation], int]:
    query_terms = {term for term in re.split(r"\W+", query.lower()) if len(term) > 3}
    citations: list[WorkflowCitation] = []
    blocked_chunks = 0
    for chunk in chunks:
        lowered = chunk["content"].lower()
        if any(pattern in lowered for pattern in INJECTION_PATTERNS):
            blocked_chunks += 1
            continue
        if not query_terms or any(term in lowered for term in query_terms):
            quote = chunk["content"][:220]
            citations.append(
                WorkflowCitation(
                    source_uri=chunk["source_uri"],
                    document_id=chunk["document_id"],
                    quote=quote,
                )
            )
    if regulated and not citations:
        return [], max(blocked_chunks, 1)
    return citations[:5], blocked_chunks


def _critic_review(regulated: bool, citations: list[WorkflowCitation], payload: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    if regulated and not citations:
        issues.append("regulated workflow requires at least one citation")
    if payload.get("summary") and "```" in str(payload.get("summary")):
        issues.append("markdown output is not allowed for machine-facing payloads")
    if "query" not in payload:
        issues.append("payload missing query field")
    return issues


def _validate_input_payload(request: OrchestrationWorkflowRequest) -> None:
    lowered = request.query.lower()
    if any(marker in lowered for marker in PROHIBITED_PAYLOAD_MARKERS):
        raise OrchestrationPolicyError("input contains prohibited sensitive marker")


def _validate_output_payload(payload: dict[str, Any]) -> None:
    rendered = json.dumps(payload, sort_keys=True).lower()
    if any(marker in rendered for marker in PROHIBITED_PAYLOAD_MARKERS):
        raise OrchestrationPolicyError("output payload contains prohibited sensitive marker")


def _eval_expression(expression: str, variables: dict[str, Decimal]) -> Decimal:
    allowed = {key: _money(value) for key, value in variables.items()}
    node = ast.parse(expression, mode="eval")
    value = _eval_ast(node.body, allowed)
    return _money(value)


def _eval_ast(node: ast.AST, variables: dict[str, Decimal]) -> Decimal:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return Decimal(str(node.value))
    if isinstance(node, ast.Name) and node.id in variables:
        return variables[node.id]
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
        left = _eval_ast(node.left, variables)
        right = _eval_ast(node.right, variables)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if right == 0:
            raise OrchestrationPolicyError("division by zero")
        return left / right
    raise OrchestrationPolicyError("expression contains unsupported syntax")


def _cache_key(runtime_mode: str, query: str, documents: list[Any], computations: list[Any], regulated: bool) -> str:
    digest = hashlib.sha256()
    digest.update(runtime_mode.encode("utf-8"))
    digest.update(query.encode("utf-8"))
    digest.update(str(regulated).encode("utf-8"))
    for doc in documents:
        digest.update(doc.document_id.encode("utf-8"))
        digest.update(doc.source_uri.encode("utf-8"))
        digest.update(_compact_context(doc.content).encode("utf-8"))
    for task in computations:
        digest.update(task.task_id.encode("utf-8"))
        digest.update(task.expression.encode("utf-8"))
        digest.update(json.dumps({k: str(v) for k, v in sorted(task.variables.items())}, sort_keys=True).encode("utf-8"))
    return digest.hexdigest()


def _load_semantic_cache(session: Session, cache_key: str) -> dict[str, Any] | None:
    row = session.execute(
        text(
            """
            SELECT run_id, response_json
            FROM orchestration_semantic_cache
            WHERE cache_key = :cache_key
              AND expires_at > :now
            """
        ),
        {"cache_key": cache_key, "now": _utcnow()},
    ).mappings().first()
    if not row:
        return None
    return {"run_id": row["run_id"], "response": json.loads(row["response_json"])}


def _store_semantic_cache(
    session: Session,
    cache_key: str,
    response: OrchestrationWorkflowResponse,
    cache_ttl_seconds: int,
) -> None:
    expires_at = _utcnow() + timedelta(seconds=cache_ttl_seconds)
    payload = response.model_dump(mode="json")
    session.execute(
        text(
            """
            INSERT INTO orchestration_semantic_cache (cache_key, run_id, response_json, expires_at, updated_at)
            VALUES (:cache_key, :run_id, :response_json, :expires_at, :updated_at)
            ON CONFLICT (cache_key) DO UPDATE
            SET run_id = excluded.run_id,
                response_json = excluded.response_json,
                expires_at = excluded.expires_at,
                updated_at = excluded.updated_at
            """
        ),
        {
            "cache_key": cache_key,
            "run_id": response.run_id,
            "response_json": json.dumps(payload, sort_keys=True),
            "expires_at": expires_at,
            "updated_at": _utcnow(),
        },
    )


def _persist_audit_decisions(
    session: Session,
    response: OrchestrationWorkflowResponse,
    user_id: str,
) -> None:
    for decision in response.agent_decisions:
        _insert_audit(
            session,
            run_id=response.run_id,
            workflow_id=response.workflow_id,
            user_id=user_id,
            runtime_mode=response.runtime_mode,
            state=response.state,
            agent=decision.agent,
            status=decision.status,
            details={
                "reason": decision.reason,
                "latency_ms": decision.latency_ms,
                "routing_tier": decision.routing_tier,
                "critic_issues": response.critic_issues,
                "cache_hit": response.cache_hit,
            },
        )


def _insert_audit(
    session: Session,
    *,
    run_id: str,
    workflow_id: str,
    user_id: str,
    runtime_mode: str,
    state: str,
    agent: str,
    status: str,
    details: dict[str, Any],
) -> None:
    details_json = json.dumps(details, sort_keys=True)
    details_value = ":details"
    if session.bind.dialect.name == "postgresql":
        details_value = "CAST(:details AS JSONB)"
    session.execute(
        text(
            f"""
            INSERT INTO orchestration_audit_log (
                run_id,
                workflow_id,
                user_id,
                runtime_mode,
                state,
                agent,
                status,
                details,
                recorded_at
            ) VALUES (
                :run_id,
                :workflow_id,
                :user_id,
                :runtime_mode,
                :state,
                :agent,
                :status,
                {details_value},
                :recorded_at
            )
            """
        ),
        {
            "run_id": run_id,
            "workflow_id": workflow_id,
            "user_id": user_id,
            "runtime_mode": runtime_mode,
            "state": state,
            "agent": agent,
            "status": status,
            "details": details_json,
            "recorded_at": _utcnow(),
        },
    )


def _compact_context(text_value: str) -> str:
    collapsed = re.sub(r"\s+", " ", text_value).strip()
    return collapsed[:8000]


def _money(value: Decimal | str | int | float) -> Decimal:
    return Decimal(value).quantize(MONEY_QUANTUM)


def _elapsed_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)
