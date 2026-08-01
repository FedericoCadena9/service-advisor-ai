"""Approved-quote appointment and simulated SMS command endpoints."""

from typing import Annotated, NamedTuple

from fastapi import APIRouter, Depends, HTTPException, status

from service_advisor_api import state
from service_advisor_api.appointments import Appointment
from service_advisor_api.approvals import QuoteDecision, QuoteReview, StaleQuoteError
from service_advisor_api.auth import SessionClaims
from service_advisor_api.messaging import (
    InventedContentError,
    MessageAlreadySentError,
    MessageTooLongError,
    SmsDelivery,
    compose_sms,
    validate_sms,
)
from service_advisor_api.routers.dependencies import current_session
from service_advisor_api.routers.schemas import (
    AppointmentResponse,
    SmsDeliveryResponse,
    SmsPreviewResponse,
    SmsRequest,
)

router = APIRouter()


class ApprovedQuoteContext(NamedTuple):
    decision: QuoteDecision
    review: QuoteReview
    customer_label: str
    slot_label: str


def _approved_quote(quote_id: str, claims: SessionClaims) -> ApprovedQuoteContext:
    try:
        decision, review = state.quote_command_store.approved_quote(
            quote_id, shop_id=claims.shop_id, demo_session_id=claims.demo_session_id
        )
    except KeyError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A human approval is required before reserving or messaging",
        ) from error
    except StaleQuoteError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except PermissionError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approved quote not found") from error
    if decision.facts.bay_slot_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="The approved quote has no bay slot"
        )
    slot = next(
        (slot for slot in state.operations_store.slots(claims.shop_id) if slot.id == decision.facts.bay_slot_id),
        None,
    )
    if slot is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The approved bay slot is no longer offered",
        )
    vehicle = state.vehicle_store.get(shop_id=claims.shop_id, vehicle_id=review.vehicle_id)
    if vehicle is None:  # pragma: no cover - protected by the review boundary
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    return ApprovedQuoteContext(decision, review, vehicle.customer_label, slot.starts_at)


def _appointment_response(appointment: Appointment) -> AppointmentResponse:
    return AppointmentResponse(
        id=appointment.id,
        quote_id=appointment.quote_id,
        bay_slot_id=appointment.bay_slot_id,
        starts_at=appointment.starts_at,
        approver_role=appointment.approver_role,
        simulated=appointment.simulated,
    )


def _delivery_response(delivery: SmsDelivery) -> SmsDeliveryResponse:
    return SmsDeliveryResponse(
        id=delivery.id,
        quote_id=delivery.quote_id,
        text=delivery.text,
        segments=delivery.segments,
        state=delivery.state,
        simulated=delivery.simulated,
        approver_role=delivery.approver_role,
        rule_version=delivery.rule_version,
        citation_page=delivery.citation_page,
        citation_section=delivery.citation_section,
    )


@router.post(
    "/quotes/{quote_id}/appointment",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def reserve_appointment(
    quote_id: str, claims: Annotated[SessionClaims, Depends(current_session)]
) -> AppointmentResponse:
    context = _approved_quote(quote_id, claims)
    appointment = state.appointment_store.reserve(
        quote_id=quote_id,
        shop_id=claims.shop_id,
        demo_session_id=claims.demo_session_id,
        bay_slot_id=context.decision.facts.bay_slot_id or "",
        starts_at=context.slot_label,
        approver_role=context.decision.approver_role,
    )
    return _appointment_response(appointment)


@router.post("/quotes/{quote_id}/sms-preview", response_model=SmsPreviewResponse)
def preview_sms(
    quote_id: str, claims: Annotated[SessionClaims, Depends(current_session)]
) -> SmsPreviewResponse:
    context = _approved_quote(quote_id, claims)
    preview = compose_sms(
        customer_label=context.customer_label,
        service_codes=context.decision.facts.service_codes,
        total_mxn=context.decision.facts.total_mxn,
        slot_label=context.slot_label,
    )
    return SmsPreviewResponse(
        text=preview.text, segments=preview.segments, priorities=list(preview.priorities)
    )


@router.post(
    "/quotes/{quote_id}/messages",
    response_model=SmsDeliveryResponse,
    status_code=status.HTTP_201_CREATED,
)
def enqueue_sms(
    quote_id: str,
    request: SmsRequest,
    claims: Annotated[SessionClaims, Depends(current_session)],
) -> SmsDeliveryResponse:
    context = _approved_quote(quote_id, claims)
    if state.appointment_store.for_quote(
        quote_id, shop_id=claims.shop_id, demo_session_id=claims.demo_session_id
    ) is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Reserve the appointment before enqueueing a message",
        )
    try:
        segments = validate_sms(
            request.text,
            customer_label=context.customer_label,
            service_codes=context.decision.facts.service_codes,
            total_mxn=context.decision.facts.total_mxn,
            slot_label=context.slot_label,
        )
    except (InventedContentError, MessageTooLongError) as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    try:
        delivery = state.messaging_store.enqueue(
            quote_id=quote_id,
            shop_id=claims.shop_id,
            demo_session_id=claims.demo_session_id,
            text=request.text,
            segments=segments,
            approver_role=context.decision.approver_role,
            rule_version=context.decision.citations.rule_version,
            citation_page=context.decision.citations.citation_page,
            citation_section=context.decision.citations.citation_section,
        )
    except MessageAlreadySentError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    return _delivery_response(delivery)


@router.get("/messages/{delivery_id}", response_model=SmsDeliveryResponse)
def get_message(
    delivery_id: str, claims: Annotated[SessionClaims, Depends(current_session)]
) -> SmsDeliveryResponse:
    try:
        delivery = state.messaging_store.get(
            delivery_id, shop_id=claims.shop_id, demo_session_id=claims.demo_session_id
        )
    except (KeyError, PermissionError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found") from error
    return _delivery_response(delivery)


@router.post("/messages/{delivery_id}/advance", response_model=SmsDeliveryResponse)
def advance_message(
    delivery_id: str, claims: Annotated[SessionClaims, Depends(current_session)]
) -> SmsDeliveryResponse:
    try:
        delivery = state.messaging_store.advance(
            delivery_id, shop_id=claims.shop_id, demo_session_id=claims.demo_session_id
        )
    except (KeyError, PermissionError) as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found") from error
    return _delivery_response(delivery)
