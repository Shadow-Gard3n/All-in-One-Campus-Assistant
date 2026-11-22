from pydantic import BaseModel, Field


class DepartmentCreate(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=100
    )


class DepartmentSource(BaseModel):

    document: str

    page: int | None = None

    score: float | None = None


class DepartmentResponse(BaseModel):

    department_id: str

    department_name: str

    answer: str

    confidence: float = Field(
        ge=0,
        le=1
    )

    needs_human: bool = False

    reason: str | None = None

    sources: list[DepartmentSource] = Field(
        default_factory=list
    )