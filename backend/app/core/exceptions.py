from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    """Business error carrying a machine-readable code + HTTP status.

    Every error response in the API has the same envelope:
    {"data": null, "error": {"code": "...", "message": "..."}}
    """

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.headers = headers
        super().__init__(message)


def _error_response(
    status_code: int, code: str, message: str, headers: dict[str, str] | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        headers=headers,
        content={"data": None, "error": {"code": code, "message": message}},
    )


_HTTP_CODE_NAMES = {
    400: "BAD_REQUEST",
    401: "NOT_AUTHENTICATED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    429: "RATE_LIMITED",
}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return _error_response(exc.status_code, exc.code, exc.message, exc.headers)

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _HTTP_CODE_NAMES.get(exc.status_code, f"HTTP_{exc.status_code}")
        return _error_response(exc.status_code, code, str(exc.detail), exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        field = ".".join(str(part) for part in list(first.get("loc", []))[1:])
        message = f"{field or 'body'}: {first.get('msg', 'invalid input')}"
        return _error_response(422, "VALIDATION_ERROR", message)
