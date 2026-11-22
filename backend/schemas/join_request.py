from pydantic import BaseModel

from models.user import UserRole


class CreateJoinRequest(BaseModel):

    organisation_id: str

    role: UserRole

    department_id: str | None = None


class JoinRequestResponse(BaseModel):

    id: str

    user_id: str

    user_name: str

    user_email: str

    organisation_id: str

    requested_role: UserRole

    department_id: str | None = None

    status: str

    created_at: str