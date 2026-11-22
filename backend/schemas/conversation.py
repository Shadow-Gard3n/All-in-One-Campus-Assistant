from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, Field


ConversationStatus = Literal[
    "open",
    "processing",
    "waiting_for_agent",
    "assigned",
    "resolved"
]



class SendMessageRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=5000
    )


class ConversationTask(BaseModel):

    task_id: str

    department_id: str

    department_name: str

    question: str

    status: Literal[
        "pending",
        "processing",
        "answered",
        "waiting_for_agent",
        "resolved"
    ] = "pending"

    confidence: float = 0.0

    answer: Optional[str] = None

    needs_human: bool = False

    assigned_agent_id: Optional[str] = None

    sources: list[dict] = Field(
        default_factory=list
    )

class ConversationMessage(BaseModel):

    sender: Literal[
        "user",
        "ai",
        "agent"
    ]

    message: str = Field(
        min_length=1,
        max_length=5000
    )

    created_at: datetime

    agent_id: Optional[str] = None

    confidence: Optional[float] = None

    needs_human: bool = False


class ConversationBase(BaseModel):

    user_id: str

    organisation_id: str

    department_id: Optional[str] = None

    title: Optional[str] = None

    status: ConversationStatus = "open"

    assigned_agent_id: Optional[str] = None

    messages: list[ConversationMessage] = Field(
        default_factory=list
    )

    created_at: datetime

    updated_at: datetime


class ChatHistoryItem(BaseModel):

    id: str

    title: str

    status: ConversationStatus

    created_at: datetime

    updated_at: datetime


class ConversationResponse(BaseModel):

    id: str

    title: str

    status: ConversationStatus

    messages: list[ConversationMessage]

    created_at: datetime

    updated_at: datetime


class AIResponse(BaseModel):

    answer: str

    confidence: float

    needs_clarification: bool = False

    needs_human: bool = False

    status: ConversationStatus

    sources: list[dict] = Field(
        default_factory=list
    )


class PendingQuestionResponse(BaseModel):

    conversation_id: str

    question: str

    answer: Optional[str] = None

    status: ConversationStatus

    assigned_agent_id: Optional[str] = None

    created_at: datetime

    updated_at: datetime