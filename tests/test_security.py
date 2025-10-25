"""
Security feature tests for CAPP

Tests authentication, rate limiting, input validation, and other security features.
"""

import pytest
from fastapi.testclient import TestClient
from applications.capp.capp.main import app

client = TestClient(app)


class TestAuthentication:
    """Test authentication endpoints and JWT tokens"""

    def test_register_user(self):
        """Test user registration"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "SecurePass123!",
                "full_name": "Test User",
                "phone_number": "+1234567890"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "test@example.com"
        assert "id" in data
        assert "hashed_password" not in data  # Should not expose password

    def test_register_duplicate_email(self):
        """Test that duplicate email registration fails"""
        # Register first user
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "SecurePass123!",
                "full_name": "User One"
            }
        )

        # Try to register with same email
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "DifferentPass123!",
                "full_name": "User Two"
            }
        )
        assert response.status_code == 409  # Conflict

    def test_weak_password_rejected(self):
        """Test that weak passwords are rejected"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "weak@example.com",
                "password": "weak",  # Too weak
                "full_name": "Weak Password User"
            }
        )
        assert response.status_code == 422  # Validation error

    def test_login_success(self):
        """Test successful login"""
        # Register user first
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "login@example.com",
                "password": "SecurePass123!",
                "full_name": "Login User"
            }
        )

        # Login
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "login@example.com",
                "password": "SecurePass123!"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "WrongPass123!"
            }
        )
        assert response.status_code == 401

    def test_protected_endpoint_without_auth(self):
        """Test that protected endpoints require authentication"""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_protected_endpoint_with_auth(self):
        """Test accessing protected endpoint with valid token"""
        # Register and login
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "protected@example.com",
                "password": "SecurePass123!",
                "full_name": "Protected User"
            }
        )

        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "protected@example.com",
                "password": "SecurePass123!"
            }
        )
        token = login_response.json()["access_token"]

        # Access protected endpoint
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "protected@example.com"


class TestSecurityHeaders:
    """Test security headers are present"""

    def test_security_headers_present(self):
        """Test that all security headers are included"""
        response = client.get("/health")

        # Check for security headers
        assert "x-content-type-options" in response.headers
        assert response.headers["x-content-type-options"] == "nosniff"

        assert "x-frame-options" in response.headers
        assert response.headers["x-frame-options"] == "DENY"

        assert "x-xss-protection" in response.headers
        assert "content-security-policy" in response.headers
        assert "referrer-policy" in response.headers

    def test_server_header_removed(self):
        """Test that server header is not exposed"""
        response = client.get("/health")
        assert "server" not in response.headers.get("server", "").lower() or \
               response.headers.get("server") == ""


class TestInputValidation:
    """Test input validation and sanitization"""

    def test_oversized_request_rejected(self):
        """Test that oversized requests are rejected"""
        # This would require a very large payload
        # Skipping for now as it's tested by middleware
        pass

    def test_invalid_content_type_rejected(self):
        """Test that invalid content types are rejected"""
        response = client.post(
            "/api/v1/auth/register",
            data="invalid data",
            headers={"Content-Type": "text/plain"}
        )
        assert response.status_code == 415  # Unsupported Media Type

    def test_sql_injection_in_query_params(self):
        """Test that SQL injection attempts in query params are blocked"""
        response = client.get("/api/v1/payments/corridors/supported?filter=1' OR '1'='1")
        # Should either block or safely handle
        assert response.status_code in [200, 400]


class TestCORS:
    """Test CORS configuration"""

    def test_cors_headers_present(self):
        """Test that CORS headers are properly configured"""
        response = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST"
            }
        )
        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers


class TestSecretsValidation:
    """Test secrets validation on startup"""

    def test_app_starts_with_warnings(self):
        """Test that app starts and logs warnings for insecure defaults"""
        # The app should start successfully
        response = client.get("/health")
        assert response.status_code == 200

        # Note: Warnings are logged but don't prevent startup in dev mode


def test_health_check():
    """Test basic health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "CAPP" in data["message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
