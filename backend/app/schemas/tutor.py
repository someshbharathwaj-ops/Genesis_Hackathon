"""Pydantic schemas for Grounded Tutor queries and responses."""

from pydantic import BaseModel, Field


class TutorQueryRequest(BaseModel):
    """Student concept inquiry request for the Grounded AI Tutor."""

    student_id: str = Field(..., description="UUID of the student making the query")
    query: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="The course concept or curriculum inquiry",
    )
    objective_id: str | None = Field(
        default=None,
        description="Optional specific learning objective UUID or code to bias retrieval",
    )


class TutorQueryResponse(BaseModel):
    """Syllabus-grounded pedagogical explanation with verified citations."""

    answer: str = Field(description="The grounded tutoring explanation or abstention notice")
    citations: list[str] = Field(
        default_factory=list,
        description="List of verifiable source citations, e.g., [Lecture: notes.pdf, Page 2]",
    )
    abstention_recommended: bool = Field(
        description="True if system abstained due to missing or low-confidence course evidence",
    )
    course_id: str = Field(description="Course scope identifier")
    student_id: str = Field(description="Student identifier")
    model_used: str = Field(description="Name of the SLM provider/model utilized")
    retrieved_chunks_count: int = Field(description="Number of candidate excerpts retrieved")
    is_mock: bool = Field(default=False, description="Whether a mock provider was utilized")
    prompt_tokens: int | None = Field(default=None, description="Estimated/measured prompt tokens")
    completion_tokens: int | None = Field(
        default=None,
        description="Estimated/measured completion tokens",
    )
    warning: str | None = Field(
        default=None,
        description="Warning or explanatory notice if prompt was truncated or evidence was sparse",
    )
