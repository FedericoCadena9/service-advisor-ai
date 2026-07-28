from datetime import UTC, datetime, timedelta

import pytest

from service_advisor_api.auth import (
    ExpiredDemoSessionError,
    create_demo_session,
    verify_demo_session,
)


def test_signed_session_contains_authorization_and_tenant_context() -> None:
    now = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)

    token = create_demo_session("advisor", now=now)

    claims = verify_demo_session(token, now=now + timedelta(minutes=1))

    assert claims.role == "advisor"
    assert claims.shop_id == "demo-shop"
    assert claims.demo_session_id
    assert claims.expires_at == now + timedelta(minutes=30)


def test_expired_signed_session_is_rejected() -> None:
    now = datetime(2026, 7, 27, 12, 0, tzinfo=UTC)
    token = create_demo_session("manager", now=now)

    with pytest.raises(ExpiredDemoSessionError):
        verify_demo_session(token, now=now + timedelta(minutes=31))
