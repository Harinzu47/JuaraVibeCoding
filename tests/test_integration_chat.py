import pytest
from httpx import AsyncClient
from unittest.mock import patch, MagicMock

@pytest.mark.asyncio
async def test_chat_unauthorized(async_client: AsyncClient):
    response = await async_client.post("/api/chat", json={
        "message": "halo",
        "chat_history": [],
        "fase_saat_ini": "PAGI_COSTING",
        "total_belanja": 0,
        "hpp_unit": 0
    })
    assert response.status_code == 401

@pytest.mark.asyncio
@patch("main.genai.Client")
async def test_chat_authorized_catat_belanja(mock_genai_client, async_client: AsyncClient):
    # Setup mock response from Gemini
    mock_response = MagicMock()
    mock_response.text = '{"response": "Oke!", "intent": "CATAT_BELANJA", "total_belanja": 50000, "modal_terpakai": 50000, "hpp_unit": 5000}'
    
    mock_client_instance = MagicMock()
    mock_client_instance.models.generate_content.return_value = mock_response
    mock_genai_client.return_value = mock_client_instance

    # Login to get token
    login_res = await async_client.post("/api/auth/login", json={
        "email": "test@dapurprofit.com",
        "password": "password123"
    })
    token = login_res.json()["access_token"]

    response = await async_client.post("/api/chat", json={
        "message": "beli ayam 50rb",
        "chat_history": [],
        "fase_saat_ini": "PAGI_COSTING",
        "total_belanja": 0,
        "hpp_unit": 0
    }, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    assert data["total_belanja"] == 50000
    assert data["hpp_unit"] == 5000
    assert data["fase_saat_ini"] == "SORE_REVENUE"

@pytest.mark.asyncio
@patch("main.genai.Client")
async def test_chat_authorized_koreksi_belanja(mock_genai_client, async_client: AsyncClient):
    # Setup mock response for koreksi
    mock_response = MagicMock()
    mock_response.text = '{"response": "Siap dikoreksi", "intent": "KOREKSI_BELANJA", "koreksi_item": "ayam", "koreksi_harga_lama": 50000, "koreksi_harga_baru": 40000}'
    
    mock_client_instance = MagicMock()
    mock_client_instance.models.generate_content.return_value = mock_response
    mock_genai_client.return_value = mock_client_instance

    # Login to get token
    login_res = await async_client.post("/api/auth/login", json={
        "email": "test@dapurprofit.com",
        "password": "password123"
    })
    token = login_res.json()["access_token"]

    # Asumsikan sebelumnya total belanja 100k, hpp 10k, dan porsi dibuat = 10
    response = await async_client.post("/api/chat", json={
        "message": "eh salah ayamnya 40rb bukan 50rb",
        "chat_history": [],
        "fase_saat_ini": "PAGI_COSTING",
        "total_belanja": 100000,
        "hpp_unit": 10000
    }, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    assert data["is_koreksi"] is True
    assert data["total_belanja"] == 90000
    assert data["koreksi_summary"] is not None
