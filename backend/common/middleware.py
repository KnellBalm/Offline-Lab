from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from fastapi import Request
from backend.common.logging import get_logger

class PathRewriteMiddleware(BaseHTTPMiddleware):
    """
    Rewrite paths for backward compatibility or convenience.
    Prepends /api to specific paths if missing.
    """
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not path.startswith("/api"):
            for prefix in ["/auth", "/problems", "/sql", "/stats", "/admin", "/practice", "/daily"]:
                if path.startswith(prefix):
                    request.scope["path"] = "/api" + path
                    break

        response = await call_next(request)
        return response

class ExceptionHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to catch unhandled exceptions and return a JSON response with 500 status code.
    This ensures that CORS middleware can still add headers to the response.
    """
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as e:
            logger = get_logger("backend.middleware.exception")
            logger.error(f"Unhandled exception: {str(e)}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal Server Error"}
            )

class CORSLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log potential CORS issues.
    This should be added outside CORSMiddleware so it can see the final response headers.
    """
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        origin = request.headers.get("origin")
        if origin:
            allow_origin = response.headers.get("access-control-allow-origin")
            if not allow_origin:
                # If it's a 404/500, sometimes headers are missing if not handled correctly.
                # But generally CORSMiddleware adds them even for errors.
                logger = get_logger("backend.middleware.cors")
                logger.warning(f"CORS Warning: Origin '{origin}' requested but no 'Access-Control-Allow-Origin' header in response. Status: {response.status_code}")

        return response
