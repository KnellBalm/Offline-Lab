
import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import logging

# Set ENV to production
os.environ["ENV"] = "production"

# Mock dependencies
with patch("backend.services.db_init.init_database", return_value=(True, None)):
    # We need to mock postgres_connection because it's used in health check
    mock_pg = MagicMock()
    mock_pg.__enter__.return_value.execute.return_value = None

    with patch("backend.services.database.postgres_connection", return_value=mock_pg):
        from backend.main import app

client = TestClient(app)

def test_cors_origin_allowed(caplog):
    caplog.set_level(logging.INFO)

    origin = "https://query-craft-frontend-758178119666.us-central1.run.app"
    headers = {"Origin": origin}

    response = client.get("/health", headers=headers)

    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == origin

    # Check logs
    # Note: backend uses its own logger setup, but caplog should capture root logger logs if propagated
    # backend.common.logging.get_logger returns logging.getLogger(name)

    log_messages = [r.message for r in caplog.records]
    found = False
    for msg in log_messages:
        if "CORS Success" in msg and origin in msg:
            found = True
            break

    if not found:
        print("Captured Logs:", log_messages)

    assert found, "CORS Success log not found"

def test_cors_origin_disallowed(caplog):
    caplog.set_level(logging.WARNING)

    origin = "https://evil-site.com"
    headers = {"Origin": origin}

    response = client.get("/health", headers=headers)

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers

    log_messages = [r.message for r in caplog.records]
    found = False
    for msg in log_messages:
        if "CORS Failed" in msg and origin in msg:
            found = True
            break

    if not found:
        print("Captured Logs:", log_messages)

    assert found, "CORS Failed log not found"
