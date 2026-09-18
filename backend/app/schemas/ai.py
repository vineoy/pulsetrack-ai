from pydantic import BaseModel, Field


class AnalysisOut(BaseModel):
    summary: str | None
    cached: bool


class AskIn(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class AskOut(BaseModel):
    answer: str | None
