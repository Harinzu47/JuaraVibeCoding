import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_auth_login_success(async_client: AsyncClient):
    response = await async_client.post(
        "/api/auth/login",
        json={"email": "testuser@dapurprofit.com", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_auth_login_wrong_password(async_client: AsyncClient):
    response = await async_client.post(
        "/api/auth/login",
        json={"email": "testuser@dapurprofit.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password."


@pytest.mark.asyncio
async def test_auth_login_missing_fields(async_client: AsyncClient):
    response = await async_client.post(
        "/api/auth/login", json={"email": "testuser@dapurprofit.com"}
    )
    assert response.status_code == 422
