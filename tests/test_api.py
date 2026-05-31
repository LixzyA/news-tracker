"""Integration tests for the FastAPI subscription API (api.py)."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health_returns_200(self):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_body(self):
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "ok"
        assert "message" in data


# ---------------------------------------------------------------------------
# POST /subscribe
# ---------------------------------------------------------------------------

class TestSubscribe:
    def test_subscribe_new_email(self):
        mock_result = {"status": "success", "message": "Subscribed successfully.", "token": "abc-token"}
        with patch("api.add_subscriber", return_value=mock_result) as mock_add:
            response = client.post("/subscribe", json={"email": "user@example.com"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        mock_add.assert_called_once_with("user@example.com")

    def test_subscribe_duplicate_email_returns_400(self):
        mock_result = {"status": "error", "message": "Email is already subscribed."}
        with patch("api.add_subscriber", return_value=mock_result):
            response = client.post("/subscribe", json={"email": "dup@example.com"})
        assert response.status_code == 400
        assert response.json()["status"] == "error"
        assert "already subscribed" in response.json()["message"].lower()

    def test_subscribe_invalid_email_returns_422(self):
        """Pydantic EmailStr validation should reject malformed addresses."""
        response = client.post("/subscribe", json={"email": "not-an-email"})
        assert response.status_code == 422

    def test_subscribe_missing_email_field_returns_422(self):
        response = client.post("/subscribe", json={})
        assert response.status_code == 422

    def test_subscribe_reactivation_returns_200(self):
        mock_result = {"status": "success", "message": "Subscription re-activated."}
        with patch("api.add_subscriber", return_value=mock_result):
            response = client.post("/subscribe", json={"email": "old@example.com"})
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# GET /unsubscribe
# ---------------------------------------------------------------------------

class TestUnsubscribe:
    def test_unsubscribe_valid_token_returns_200(self):
        mock_result = {"status": "success", "message": "Unsubscribed successfully.", "email": "user@example.com"}
        with patch("api.remove_subscriber", return_value=mock_result):
            response = client.get("/unsubscribe", params={"token": "valid-token-123"})
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_unsubscribe_valid_token_html_content(self):
        mock_result = {"status": "success", "message": "Unsubscribed successfully.", "email": "user@example.com"}
        with patch("api.remove_subscriber", return_value=mock_result):
            response = client.get("/unsubscribe", params={"token": "valid-token-123"})
        assert "unsubscribed" in response.text.lower()
        assert "user@example.com" in response.text

    def test_unsubscribe_invalid_token_returns_400(self):
        mock_result = {"status": "error", "message": "Invalid or unknown unsubscribe token."}
        with patch("api.remove_subscriber", return_value=mock_result):
            response = client.get("/unsubscribe", params={"token": "bad-token"})
        assert response.status_code == 400
        assert "text/html" in response.headers["content-type"]

    def test_unsubscribe_invalid_token_html_content(self):
        mock_result = {"status": "error", "message": "Invalid or unknown unsubscribe token."}
        with patch("api.remove_subscriber", return_value=mock_result):
            response = client.get("/unsubscribe", params={"token": "bad-token"})
        assert "something went wrong" in response.text.lower() or "failed" in response.text.lower()

    def test_unsubscribe_missing_token_returns_422(self):
        """token is a required query param."""
        response = client.get("/unsubscribe")
        assert response.status_code == 422

    def test_unsubscribe_already_inactive_returns_200(self):
        mock_result = {"status": "success", "message": "Already unsubscribed."}
        with patch("api.remove_subscriber", return_value=mock_result):
            response = client.get("/unsubscribe", params={"token": "old-token"})
        assert response.status_code == 200
