"""
Tests for authentication endpoints.

Covers:
- Login with valid credentials
- Login with invalid credentials
- Token validation
- Protected route access
- Token expiration
- Error handling
"""
import pytest
from httpx import AsyncClient
from fastapi import status


class TestAuthEndpoints:
    """Test authentication endpoints."""

    @pytest.mark.asyncio
    async def test_login_success_with_admin(self, client: AsyncClient):
        """Test successful login with admin credentials."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "admin",
                "password": "admin123"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["username"] == "admin"
        assert data["user"]["role"] == "admin"

    @pytest.mark.asyncio
    async def test_login_success_with_viewer(self, client: AsyncClient):
        """Test successful login with viewer credentials."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "viewer",
                "password": "viewer123"
            }
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["user"]["username"] == "viewer"
        assert data["user"]["role"] == "viewer"

    @pytest.mark.asyncio
    async def test_login_invalid_username(self, client: AsyncClient):
        """Test login with non-existent username."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent",
                "password": "password123"
            }
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "detail" in data
        assert "Incorrect username or password" in data["detail"]

    @pytest.mark.asyncio
    async def test_login_invalid_password(self, client: AsyncClient):
        """Test login with wrong password."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "admin",
                "password": "wrongpassword"
            }
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_login_missing_username(self, client: AsyncClient):
        """Test login without username."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "password": "admin123"
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_login_missing_password(self, client: AsyncClient):
        """Test login without password."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "admin"
            }
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_login_empty_credentials(self, client: AsyncClient):
        """Test login with empty username and password."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "",
                "password": ""
            }
        )

        # OAuth2PasswordRequestForm validates empty strings result in 422
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_token_validation_success(self, client: AsyncClient, auth_token: str):
        """Test accessing protected endpoint with valid token."""
        response = await client.get(
            "/api/v1/data-sources",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        # Should not return 401 unauthorized
        assert response.status_code != status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_protected_route_without_token(self, client: AsyncClient):
        """Test accessing protected endpoint without token."""
        response = await client.get("/api/v1/data-sources")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_protected_route_invalid_token(self, client: AsyncClient):
        """Test accessing protected endpoint with invalid token."""
        response = await client.get(
            "/api/v1/data-sources",
            headers={"Authorization": "Bearer invalid_token_here"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_protected_route_malformed_header(self, client: AsyncClient):
        """Test accessing protected endpoint with malformed auth header."""
        response = await client.get(
            "/api/v1/data-sources",
            headers={"Authorization": "InvalidFormat token"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_token_contains_user_info(self, client: AsyncClient):
        """Test that token contains correct user information."""
        from jose import jwt
        from app.presentation.api.v1.auth import SECRET_KEY, ALGORITHM

        # Login to get token
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin", "password": "admin123"}
        )

        token = response.json()["access_token"]

        # Decode token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        assert "sub" in payload
        assert payload["sub"] == "admin"
        assert "exp" in payload

    @pytest.mark.asyncio
    async def test_token_expiration_format(self, client: AsyncClient):
        """Test that token has proper expiration time."""
        from jose import jwt
        from app.presentation.api.v1.auth import SECRET_KEY, ALGORITHM
        from datetime import datetime, timezone

        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin", "password": "admin123"}
        )

        token = response.json()["access_token"]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Check expiration is in the future
        exp_timestamp = payload["exp"]
        exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
        now = datetime.now(timezone.utc)

        assert exp_datetime > now, "Token should not be expired"

    @pytest.mark.asyncio
    async def test_multiple_logins_generate_different_tokens(self, client: AsyncClient):
        """Test that multiple logins generate different tokens."""
        import asyncio

        response1 = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin", "password": "admin123"}
        )
        token1 = response1.json()["access_token"]

        # Wait 1 second to ensure different expiration timestamp
        await asyncio.sleep(1)

        response2 = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin", "password": "admin123"}
        )
        token2 = response2.json()["access_token"]

        # Tokens should be different due to different timestamps
        assert token1 != token2

    @pytest.mark.asyncio
    async def test_login_response_structure(self, client: AsyncClient):
        """Test that login response has correct structure."""
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": "admin", "password": "admin123"}
        )

        data = response.json()

        # Check all required fields exist
        assert "access_token" in data
        assert "token_type" in data
        assert "user" in data

        # Check user object structure
        user = data["user"]
        assert "username" in user
        assert "role" in user
        assert "full_name" in user

        # Password should not be in response
        assert "password" not in user
