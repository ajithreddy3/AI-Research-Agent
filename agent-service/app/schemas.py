from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)
    domain: str = Field(..., description="AI | Security | Other")
    source_language: str | None = Field(default=None, description="Optional; auto-detect if missing")


class RecommendedPaper(BaseModel):
    paper_title: str
    score: float


class AskResponse(BaseModel):
    answer: str
    language: str
    recommended_papers: list[RecommendedPaper]
    references: list[str]


class IngestResponse(BaseModel):
    paper_title: str
    domain: str
    language: str
    inserted_chunks: int
