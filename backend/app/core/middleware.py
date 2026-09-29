import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response
from fastapi import Request, status
from .security_settings import security_settings
from .security import check_rate_limit
from .config import settings

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Enforce payload size limit (OWASP Unrestricted Uploads / DoS)
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > security_settings.MAX_FILE_SIZE_BYTES:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"detail": "Payload too large. Maximum permitted request body is 10 MB."}
            )

        # 2. Rate limiting enforcement
        client_ip = request.client.host if request.client else "127.0.0.1"
        is_login_route = "/api/auth/login" in request.url.path or "/api/auth/verify-otp" in request.url.path
        
        rate_key = f"{'login' if is_login_route else 'api'}:{client_ip}"
        limit = security_settings.LOGIN_RATE_LIMIT if is_login_route else security_settings.GENERAL_RATE_LIMIT

        if not check_rate_limit(rate_key, max_requests=limit, window_seconds=60):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded. Too many requests. Please wait 60 seconds before retrying.",
                    "client_ip": client_ip,
                    "retry_after_seconds": 60
                },
                headers={"Retry-After": "60"}
            )

        # 3. Process the request
        try:
            response: Response = await call_next(request)
        except Exception as exc:
            # Prevent leaking stack traces, database schema, or internal exceptions in production
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "An internal system error occurred. Incident reference logged for security review."}
            )

        # 4. Attach all mandatory Security Headers
        for header_name, header_value in security_settings.SECURITY_HEADERS.items():
            response.headers[header_name] = header_value

        # Session inactivity indicator headers for the client
        response.headers["X-Session-Timeout-Minutes"] = str(security_settings.SESSION_INACTIVITY_MAX_SECONDS // 60)
        response.headers["X-Data-Residency"] = settings.PRIMARY_DATA_RESIDENCY

        return response
