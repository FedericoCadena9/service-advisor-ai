"""Quote drafting, review, approval, and audit endpoints."""

from typing import Annotated, NamedTuple

from fastapi import APIRouter, Depends, Header, HTTPException, status

from service_advisor_api import state
from service_advisor_api.approvals import (
    AlreadyDecidedError,
    QuoteCitations,
    QuoteDecision,
    QuoteFacts,
    QuoteReview,
    StaleQuoteError,
)
from service_advisor_api.auth import SessionClaims
from service_advisor_api.escalation import (
    EscalationAssessment,
    EscalationReasonRequiredError,
    EscalationRequiredError,
    EvidenceInsufficientError,
    assess_escalation,
)
from service_advisor_api.quotes import (
    InformationalServiceError,
    QuoteDraft,
    UnknownServiceError,
    draft_quote,
    fingerprint,
    required_part_numbers,
)
from service_advisor_api.recommendations import evaluate_maintenance
from service_advisor_api.routers.dependencies import _require_manager, current_session
from service_advisor_api.routers.schemas import (
    QuoteCitationsResponse,
    QuoteDecisionRequest,
    QuoteDecisionResponse,
    QuoteDraftRequest,
    QuoteDraftResponse,
    QuoteFactsResponse,
    QuoteLineResponse,
    QuoteReviewResponse,
)

router = APIRouter()


def _build_quote_draft(shop_id: str, engine: str, service_codes: list[str]) -> QuoteDraft:
    parts = {
        part_number: state.operations_store.part(shop_id, part_number)
        for part_number in required_part_numbers(service_codes)
    }
    return draft_quote(
        service_codes,
        engine=engine,
        parts=parts,
        slots=state.operations_store.slots(shop_id),
    )


@router.post(
    "/vehicles/{vehicle_id}/quote-drafts",
    response_model=QuoteDraftResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_quote_draft(
    vehicle_id: str,
    request: QuoteDraftRequest,
    claims: Annotated[SessionClaims, Depends(current_session)],
) -> QuoteDraftResponse:
    vehicle = state.vehicle_store.get(shop_id=claims.shop_id, vehicle_id=vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    checkin = state.checkin_store.get(
        shop_id=claims.shop_id, demo_session_id=claims.demo_session_id, vehicle_id=vehicle_id
    )
    if checkin is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Confirm a check-in before drafting a quote",
        )
    try:
        draft = _build_quote_draft(claims.shop_id, vehicle.engine, request.service_codes)
    except (UnknownServiceError, InformationalServiceError) as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    return QuoteDraftResponse(
        lines=[QuoteLineResponse(**line.__dict__) for line in draft.lines],
        subtotal_mxn=draft.subtotal_mxn,
        iva_mxn=draft.iva_mxn,
        total_mxn=draft.total_mxn,
        duration_minutes=draft.duration_minutes,
        bay_slot_id=draft.bay_slot_id,
        warnings=list(draft.warnings),
    )


class QuoteContext(NamedTuple):
    facts: QuoteFacts
    citations: QuoteCitations
    fingerprint: str
    unavailable_service_codes: tuple[str, ...]
    declines_per_service: tuple[int, ...]


def _quote_context(claims: SessionClaims, vehicle_id: str, service_codes: list[str]) -> QuoteContext:
    vehicle = state.vehicle_store.get(shop_id=claims.shop_id, vehicle_id=vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    checkin = state.checkin_store.get(
        shop_id=claims.shop_id, demo_session_id=claims.demo_session_id, vehicle_id=vehicle_id
    )
    if checkin is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Confirm a check-in before reviewing a quote",
        )
    try:
        draft = _build_quote_draft(claims.shop_id, vehicle.engine, service_codes)
    except (UnknownServiceError, InformationalServiceError) as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    recommendation = evaluate_maintenance(
        checkin.current_mileage_km,
        checkin.checked_in_on,
        make=vehicle.make,
        model=vehicle.model,
        engine=vehicle.engine,
        drivetrain=vehicle.drivetrain,
        market=vehicle.market,
        completed_services=state.service_history_store.completed(claims.shop_id, vehicle.id),
        declined_services=state.service_history_store.declined(claims.shop_id, vehicle.id),
    )
    facts = QuoteFacts(
        service_codes=tuple(service_codes),
        subtotal_mxn=draft.subtotal_mxn,
        iva_mxn=draft.iva_mxn,
        total_mxn=draft.total_mxn,
        duration_minutes=draft.duration_minutes,
        bay_slot_id=draft.bay_slot_id,
    )
    citations = QuoteCitations(
        rule_version=recommendation.rule_version,
        citation_page=recommendation.citation_page,
        citation_section=recommendation.citation_section,
    )
    declined = state.service_history_store.declined(claims.shop_id, vehicle_id)
    return QuoteContext(
        facts=facts,
        citations=citations,
        fingerprint=fingerprint(draft),
        unavailable_service_codes=tuple(line.service_code for line in draft.lines if not line.available),
        declines_per_service=tuple(
            sum(1 for record in declined if record.service_code == service_code)
            for service_code in service_codes
        ),
    )


def _assess_escalation(
    context: QuoteContext, invalidation_reason: str | None
) -> EscalationAssessment:
    return assess_escalation(
        total_mxn=context.facts.total_mxn,
        rule_version=context.citations.rule_version,
        citation_page=context.citations.citation_page,
        declines_per_service=context.declines_per_service,
        invalidation_reason=invalidation_reason,
        unavailable_service_codes=context.unavailable_service_codes,
    )


def _facts_response(facts: QuoteFacts) -> QuoteFactsResponse:
    return QuoteFactsResponse(
        service_codes=list(facts.service_codes),
        subtotal_mxn=facts.subtotal_mxn,
        iva_mxn=facts.iva_mxn,
        total_mxn=facts.total_mxn,
        duration_minutes=facts.duration_minutes,
        bay_slot_id=facts.bay_slot_id,
    )


def _review_response(
    review: QuoteReview, claims: SessionClaims, escalation: EscalationAssessment
) -> QuoteReviewResponse:
    return QuoteReviewResponse(
        id=review.id,
        vehicle_id=review.vehicle_id,
        approver_role=claims.role,
        approver_session_id=claims.demo_session_id,
        facts=_facts_response(review.facts),
        citations=QuoteCitationsResponse(**review.citations.__dict__),
        status=review.status,
        expires_at=review.expires_at,
        invalidation_reason=review.invalidation_reason,
        escalation_required=escalation.required,
        escalation_reasons=list(escalation.reasons),
        evidence_blocked=escalation.evidence_blocked,
        blocking_reason=escalation.blocking_reason,
    )


def _decision_response(decision: QuoteDecision) -> QuoteDecisionResponse:
    return QuoteDecisionResponse(
        id=decision.id,
        review_id=decision.review_id,
        quote_id=decision.quote_id,
        decision=decision.decision,
        approver_role=decision.approver_role,
        approver_session_id=decision.approver_session_id,
        reason=decision.reason,
        facts=_facts_response(decision.facts),
        citations=QuoteCitationsResponse(**decision.citations.__dict__),
        escalation_reasons=list(decision.escalation_reasons),
    )


def _load_review(review_id: str, claims: SessionClaims) -> QuoteReview:
    try:
        return state.quote_command_store.get(
            review_id, shop_id=claims.shop_id, demo_session_id=claims.demo_session_id
        )
    except (KeyError, PermissionError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote review not found") from error


@router.post(
    "/vehicles/{vehicle_id}/quote-reviews",
    response_model=QuoteReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
def open_quote_review(
    vehicle_id: str,
    request: QuoteDraftRequest,
    claims: Annotated[SessionClaims, Depends(current_session)],
) -> QuoteReviewResponse:
    context = _quote_context(claims, vehicle_id, request.service_codes)
    review = state.quote_command_store.open_review(
        shop_id=claims.shop_id,
        demo_session_id=claims.demo_session_id,
        vehicle_id=vehicle_id,
        facts=context.facts,
        citations=context.citations,
        fingerprint=context.fingerprint,
    )
    return _review_response(review, claims, _assess_escalation(context, review.invalidation_reason))


@router.get("/quote-reviews/{review_id}", response_model=QuoteReviewResponse)
def get_quote_review(
    review_id: str, claims: Annotated[SessionClaims, Depends(current_session)]
) -> QuoteReviewResponse:
    review = _load_review(review_id, claims)
    context = _quote_context(claims, review.vehicle_id, list(review.facts.service_codes))
    revalidated = state.quote_command_store.revalidate(review.id, context.facts, context.fingerprint)
    return _review_response(revalidated, claims, _assess_escalation(context, revalidated.invalidation_reason))


@router.get("/quote-audit", response_model=list[QuoteDecisionResponse])
def list_quote_audit(
    claims: Annotated[SessionClaims, Depends(current_session)],
) -> list[QuoteDecisionResponse]:
    _require_manager(claims)
    return [
        _decision_response(decision)
        for decision in state.quote_command_store.audit_trail(claims.shop_id)
    ]


@router.post("/quote-reviews/{review_id}/decision", response_model=QuoteDecisionResponse)
def decide_quote_review(
    review_id: str,
    request: QuoteDecisionRequest,
    claims: Annotated[SessionClaims, Depends(current_session)],
    x_trace_id: Annotated[str | None, Header()] = None,
) -> QuoteDecisionResponse:
    review = _load_review(review_id, claims)
    context = _quote_context(claims, review.vehicle_id, list(review.facts.service_codes))
    escalation = _assess_escalation(context, review.invalidation_reason)
    if request.decision == "reject":
        if not (request.reason or "").strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="A rejection reason is required",
            )
        try:
            return _decision_response(
                state.quote_command_store.reject(
                    review.id,
                    shop_id=claims.shop_id,
                    demo_session_id=claims.demo_session_id,
                    approver_role=claims.role,
                    approver_session_id=claims.demo_session_id,
                    reason=request.reason or "",
                    escalation_reasons=escalation.reasons,
                )
            )
        except AlreadyDecidedError as error:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    try:
        decision = state.quote_command_store.approve(
            review.id,
            shop_id=claims.shop_id,
            demo_session_id=claims.demo_session_id,
            approver_role=claims.role,
            approver_session_id=claims.demo_session_id,
            idempotency_key=request.idempotency_key,
            current_facts=context.facts,
            current_fingerprint=context.fingerprint,
            escalation=escalation,
            reason=request.reason,
        )
    except EvidenceInsufficientError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    except EscalationRequiredError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    except EscalationReasonRequiredError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    except StaleQuoteError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    state.record_span(
        x_trace_id,
        name="approve_quote",
        kind="command",
        attributes={
            "decision": decision.decision,
            "approver_role": decision.approver_role,
            "escalation_reasons": len(decision.escalation_reasons),
            "total_mxn": str(decision.facts.total_mxn),
            "citation_page": decision.citations.citation_page,
        },
    )
    return _decision_response(decision)
