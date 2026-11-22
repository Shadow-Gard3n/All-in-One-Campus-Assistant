from datetime import datetime

from pydantic import BaseModel


class KnowledgeDocumentResponse(BaseModel):
    id: str
    organisation_id: str
    department_id: str
    filename: str
    file_type: str
    file_size: int
    status: str
    created_at: datetime