from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_chat_unauthorized(async_client: AsyncClient):
    response = await async_client.post(
        "/api/chat/",
        json={
            "message": "halo",
            "session_id": "dummy",
        },
    )
    assert response.status_code == 401

@pytest.mark.asyncio
@patch("app.api.v1.chat.gemini_service")
async def test_chat_authorized_record_spending(
    mock_gemini_service, async_client: AsyncClient
):
    # Log in to get token
    login_res = await async_client.post(
        "/api/auth/login",
        json={"email": "test@aturmodal.com", "password": "password123"},
    )
    token = login_res.json()["access_token"]
    
    # Create a session to get session_id
    session_res = await async_client.get(
        "/api/sessions/today",
        headers={"Authorization": f"Bearer {token}"},
    )
    session_id = session_res.json()["id"]

    # Setup mock service response for extraction
    mock_gemini_service.extract_entities = AsyncMock(
        return_value={
            "intent": "RECORD_SPENDING",
            "needs_clarification": False,
            "items_extracted": [{"name": "ayam", "price": 50000, "qty": 1, "unit": "ekor"}],
            "servings": 10,
            "response_text": "Oke!"
        }
    )

    response = await async_client.post(
        "/api/chat/",
        json={
            "message": "beli ayam 50rb jadi 10 porsi",
            "session_id": session_id,
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
async def test_chat_authorized_need_clarification(
    mock_gemini_service, async_client: AsyncClient
):
    # Setup mock for missing data
    mock_gemini_service.extract_entities = AsyncMock(
        return_value={
            "intent": "ASK_CLARIFICATION",
            "needs_clarification": True,
            "response_text": "Jadinya berapa porsi Bu?",
        }
    )

    # Log in
    login_res = await async_client.post(
        "/api/auth/login",
        json={"email": "test@aturmodal.com", "password": "password123"},
    )
    token = login_res.json()["access_token"]

    session_res = await async_client.get(
        "/api/sessions/today",
        headers={"Authorization": f"Bearer {token}"},
    )
    session_id = session_res.json()["id"]

    response = await async_client.post(
        "/api/chat/",
        json={
            "message": "beli telur 20rb",
            "session_id": session_id,
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["response"] == "Jadinya berapa porsi Bu?"
    # Should not advance phase
    assert data["current_phase"] == "MORNING_COSTING"
