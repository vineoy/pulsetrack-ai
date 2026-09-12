from pydantic import BaseModel


class ErrorOut(BaseModel):
    code: str
    message: str


class ApiResponse[T](BaseModel):
    """Uniform envelope for every endpoint: {data, error} — exactly one is set."""

    data: T | None = None
    error: ErrorOut | None = None
