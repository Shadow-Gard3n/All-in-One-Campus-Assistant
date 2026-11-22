from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from schemas.conversation import (
    ConversationMessage,
    ConversationStatus
)


# ============================================================
# SUPPORT QUEUE ITEM
# ============================================================

class SupportQuestionResponse(BaseModel):

    conversation_id: str

    user_id: str

    user_name: str

    user_email: str

    organisation_id: str

    department_id: Optional[str] = None

    question: str

    answer: Optional[str] = None

    status: ConversationStatus

    assigned_agent_id: Optional[str] = None

    created_at: datetime

    updated_at: datetime


# ============================================================
# SUPPORT CONVERSATION
# ============================================================

class SupportConversationResponse(BaseModel):

    conversation_id: str

    user_id: str

    user_name: str

    user_email: str

    organisation_id: str

    department_id: Optional[str] = None

    status: ConversationStatus

    assigned_agent_id: Optional[str] = None

    messages: list[ConversationMessage]

    created_at: datetime

    updated_at: datetime


# ============================================================
# SUPPORT AGENT REPLY
# ============================================================

class SupportReplyRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=5000
    )


# ============================================================
# TAKE SUPPORT REQUEST
# ============================================================

class TakeConversationResponse(BaseModel):

    conversation_id: str

    assigned_agent_id: str

    status: ConversationStatus


# ============================================================
# RESOLVE SUPPORT REQUEST
# ============================================================

class ResolveConversationResponse(BaseModel):

    conversation_id: str

    status: ConversationStatus