
import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import logging

# Set ENV to production temporarily for import
# We use mock.patch.dict to ensure it doesn't leak, but we need it set
# BEFORE importing main.py if main.py reads it at module level.
# However, main.py reads os.getenv("ENV") inside the middleware definition block
# AND at module level for CORSMiddleware.

# Strategy:
# 1. Use patch.dict to set ENV=production
# 2. Import app
# 3. Reload app or ensure the import happens within the patch context?
# Since pytest collects tests before running, module level code runs at collection time.

# Better approach for this specific test file:
# Since we need to test production configuration which happens at module level in main.py,
# we should wrap the import in a fixture or setup that patches os.environ.
# BUT, main.py is likely imported by other tests too.
# If main.py is already imported, reloading it is necessary to pick up the new ENV.

import importlib
import backend.main

@pytest.fixture(scope="module")
def client():
    # Patch environment to production
    with patch.dict(os.environ, {"ENV": "production"}):
        # Reload backend.main to re-evaluate module-level logic (CORS setup)
        importlib.reload(backend.main)

        # We also need to mock dependencies that might be initialized
        with patch("backend.services.db_init.init_database", return_value=(True, None)):
            mock_pg = MagicMock()
            mock_pg.__enter__.return_value.execute.return_value = None

            with patch("backend.services.database.postgres_connection", return_value=mock_pg):
                # Return client
                yield TestClient(backend.main.app)

    # Cleanup: Reload backend.main with original environment (development)
    # This ensures subsequent tests (like test_integration.py) get the clean state
    # assuming they run after this module.
    # Note: If tests run in parallel or random order, this might be tricky,
    # but preventing pollution is key.
    if "ENV" in os.environ and os.environ["ENV"] == "production":
        del os.environ["ENV"]
    importlib.reload(backend.main)

def test_cors_origin_allowed(client, caplog):
    caplog.set_level(logging.INFO)

    origin = "https://query-craft-frontend-758178119666.us-central1.run.app"
    headers = {"Origin": origin}

    response = client.get("/health", headers=headers)

    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == origin

    # Check logs
    log_messages = [r.message for r in caplog.records]
    found = False
    for msg in log_messages:
        if "CORS Success" in msg and origin in msg:
            found = True
            break

    assert found, f"CORS Success log not found. Logs: {log_messages}"

def test_cors_origin_disallowed(client, caplog):
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

    assert found, f"CORS Failed log not found. Logs: {log_messages}"
