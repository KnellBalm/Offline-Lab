import os
import sys
import pytest
from unittest.mock import patch
import importlib
from fastapi.testclient import TestClient

@pytest.fixture(scope="module")
def client():
    """
    Fixture to set ENV to production and reload backend.main
    to apply production CORS settings.
    Restores the original environment and reloads backend.main afterwards.
    """
    # Temporarily set ENV to production
    with patch.dict(os.environ, {"ENV": "production"}):
        import backend.main
        importlib.reload(backend.main)
        from backend.main import app
        yield TestClient(app)

    # Reload backend.main to restore original (development) state
    # This is crucial so other tests (like test_integration.py)
    # don't see the production app instance or stale env settings.
    import backend.main
    importlib.reload(backend.main)

class TestCORSConfig:
    """Test CORS configuration for the backend."""

    def test_cors_specific_origin_allowed(self, client):
        """
        Verify that the specific frontend origin reported in the issue is allowed.
        Origin: https://query-craft-frontend-758178119666.us-central1.run.app
        """
        origin = "https://query-craft-frontend-758178119666.us-central1.run.app"

        # 1. Test Preflight (OPTIONS)
        response = client.options(
            "/auth/me",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "content-type",
            }
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == origin
        assert response.headers.get("access-control-allow-credentials") == "true"

        # 2. Test GET request
        response = client.get(
            "/auth/me",
            headers={"Origin": origin}
        )
        assert response.headers.get("access-control-allow-origin") == origin
        assert response.headers.get("access-control-allow-credentials") == "true"

    def test_cors_cloud_run_domain_regex(self, client):
        """Verify that other Cloud Run domains matching the regex are also allowed."""
        origin = "https://query-craft-frontend-random-hash.a.run.app"

        response = client.options(
            "/auth/me",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            }
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == origin

    def test_cors_disallowed_origin(self, client):
        """Verify that a random origin is NOT allowed."""
        origin = "https://evil-site.com"

        response = client.options(
            "/auth/me",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            }
        )
        assert "access-control-allow-origin" not in response.headers

    def test_path_rewrite_does_not_break_cors(self, client):
        """
        Verify that PathRewriteMiddleware (which rewrites /auth/me to /api/auth/me)
        does not interfere with CORS headers.
        """
        origin = "https://query-craft-frontend-758178119666.us-central1.run.app"

        # Send request to /auth/me (rewritten to /api/auth/me)
        response = client.get(
            "/auth/me",
            headers={"Origin": origin}
        )
        assert response.headers.get("access-control-allow-origin") == origin

        # Send request directly to /api/auth/me (no rewrite needed)
        response = client.get(
            "/api/auth/me",
            headers={"Origin": origin}
        )
        assert response.headers.get("access-control-allow-origin") == origin
