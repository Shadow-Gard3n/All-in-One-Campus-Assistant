from pydantic import BaseModel, Field


class RouteTask(BaseModel):

    department_id: str

    department_name: str

    question: str

    confidence: float = Field(
        ge=0,
        le=1
    )


class RouterResponse(BaseModel):

    routes: list[RouteTask] = Field(
        default_factory=list
    )

    overall_confidence: float = Field(
        ge=0,
        le=1
    )

    needs_clarification: bool = False