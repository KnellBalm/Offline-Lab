import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import os
import sys

# Ensure backend can be imported
sys.path.append(os.getcwd())

# Save original ENV
original_env = os.environ.get("ENV")

# Mock environment to avoid DB connection issues during import if not already imported
if "backend.main" not in sys.modules:
    # Set ENV to production to ensure CORS middleware is added
    os.environ["ENV"] = "production"
    os.environ["POSTGRES_DSN"] = "postgresql://dummy:dummy@localhost:5432/dummy"
    # Also mock db_init to prevent thread creation
    sys.modules["backend.services.db_init"] = MagicMock()
    sys.modules["backend.scheduler"] = MagicMock()

try:
    from backend.main import app
except ImportError:
    # Retry import if it failed? Or just let it fail
    from backend.main import app
finally:
    # Restore original ENV immediately after import
    # The app object is already created with production settings (if we just imported it)
    # If it was already imported, changing ENV here doesn't affect the app instance,
    # but protects other tests.
    if original_env is None:
        if "ENV" in os.environ:
            del os.environ["ENV"]
    else:
        os.environ["ENV"] = original_env

def test_cors_logging_middleware():
    """Test that CORSLoggingMiddleware logs origin and response headers."""

    # We patch the get_logger in backend.common.middleware
    # verify where it is imported.
    # In backend/common/middleware.py: from backend.common.logging import get_logger
    with patch("backend.common.middleware.get_logger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        client = TestClient(app)
        origin = "https://query-craft-frontend-758178119666.us-central1.run.app"

        # Make a request with Origin header to /health (doesn't require DB auth)
        response = client.get("/health", headers={"Origin": origin})

        # Verify logger was called
        # 1. Log request origin
        # 2. Log response headers

        assert mock_logger.info.call_count >= 2

        request_log_found = False
        response_log_found = False

        for call in mock_logger.info.call_args_list:
            msg = call[0][0]
            if "CORS Request Origin" in msg:
                request_log_found = True
                assert origin in msg
            if "CORS Response - Origin" in msg:
                response_log_found = True
                assert origin in msg
                # Should contain allowed origin because it is a valid origin
                assert f"Allow-Origin: {origin}" in msg

        assert request_log_found, "Request log not found"
        assert response_log_found, "Response log not found"

def test_cors_logging_middleware_no_origin():
    """Test that middleware does NOT log if no origin header is present."""
    with patch("backend.common.middleware.get_logger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        client = TestClient(app)

        client.get("/health")

        # Should NOT log CORS info
        for call in mock_logger.info.call_args_list:
            msg = call[0][0]
            assert "CORS Request Origin" not in msg
            assert "CORS Response - Origin" not in msg
