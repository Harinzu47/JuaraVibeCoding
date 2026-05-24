from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_chat_unauthorized(async_client: AsyncClient):
    response = await async_client.post(
        "/api/chat/",
        json={
            "message": "halo",
            "chat_history": [],
            "current_phase": "MORNING_COSTING",
            "total_spending": 0,
            "cogs_per_unit": 0,
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
@patch("app.api.v1.chat.gemini_service")
async def test_chat_authorized_record_spending(
    mock_gemini_service, async_client: AsyncClient
):
    # Setup mock service response
    mock_gemini_service.generate_content = AsyncMock(
        return_value={
            "response": "Oke!",
            "intent": "RECORD_SPENDING",
            "total_spending": 50000,
            "used_capital": 50000,
            "cogs_per_unit": 5000,
        }
    )

    # Log in to get token
    login_res = await async_client.post(
        "/api/auth/login",
        json={"email": "test@dapurprofit.com", "password": "password123"},
    )
    token = login_res.json()["access_token"]

    response = await async_client.post(
        "/api/chat/",
        json={
            "message": "beli ayam 50rb",
            "chat_history": [],
            "current_phase": "MORNING_COSTING",
            "total_spending": 0,
            "cogs_per_unit": 0,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_spending"] == 50000
    assert data["cogs_per_unit"] == 5000
    assert data["current_phase"] == "EVENING_SALES"


@pytest.mark.asyncio
@patch("app.api.v1.chat.gemini_service")
async def test_chat_authorized_correct_spending(
    mock_gemini_service, async_client: AsyncClient
):
    # Setup mock response for correction
    mock_gemini_service.generate_content = AsyncMock(
        return_value={
            "response": "Siap dikoreksi",
            "intent": "CORRECT_SPENDING",
            "correction_item": "ayam",
            "correction_old_price": 50000,
            "correction_new_price": 40000,
        }
    )

    # Log in to get token
    login_res = await async_client.post(
        "/api/auth/login",
        json={"email": "test@dapurprofit.com", "password": "password123"},
    )
    token = login_res.json()["access_token"]

    # Assume total spending was 100k, COGS was 10k
    response = await async_client.post(
        "/api/chat/",
        json={
            "message": "eh salah ayamnya 40rb bukan 50rb",
            "chat_history": [],
            "current_phase": "MORNING_COSTING",
            "total_spending": 100000,
            "cogs_per_unit": 10000,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_correction"] is True
    assert data["total_spending"] == 90000
    assert data["correction_summary"] is not None
