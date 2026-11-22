from pydantic import BaseModel, EmailStr, Field
from typing import Literal


# ============================================================
# INITIAL DEPARTMENT
# ============================================================

class InitialDepartment(BaseModel):

    name: str = Field(
        min_length=2,
        max_length=100
    )

    bot_enabled: bool = True

    human_support_enabled: bool = True


# ============================================================
# REGISTER / JOIN ORGANISATION
# ============================================================
class RegisterRequest(BaseModel):

    name: str = Field(
        min_length=2,
        max_length=100
    )

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128
    )

    # Organisation the user wants to join
    organisation_id: str

    # Requested role
    role: Literal[
        "user",
        "support_agent"
    ]

    # Required only for support_agent
    department_id: str | None = None

# class RegisterRequest(BaseModel):

#     name: str = Field(
#         min_length=2,
#         max_length=100
#     )

#     email: EmailStr

#     password: str = Field(
#         min_length=8,
#         max_length=128
#     )

#     # Organisation the user wants to join
#     organisation_id: str

#     # Users can only request these roles
#     role: Literal[
#         "user",
#         "support_agent"
#     ]

#     # Required only for support_agent
#     department_id: str | None = None


# ============================================================
# CREATE ORGANISATION
# ============================================================

class CreateOrganisationRequest(BaseModel):

    organisation_name: str = Field(
        min_length=2,
        max_length=150
    )

    name: str = Field(
        min_length=2,
        max_length=100
    )

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128
    )

    departments: list[InitialDepartment] = Field(
        default_factory=list
    )


# ============================================================
# LOGIN
# ============================================================

class LoginRequest(BaseModel):

    email: EmailStr

    password: str


# ============================================================
# JOIN ORGANISATION
# ============================================================
#
# Optional endpoint for an already-created account.
#
# Your current registration page doesn't need this because
# registration itself creates the join request.
#
# Keep this schema if you want to support:
#
# Existing account -> request to join organisation
#
# ============================================================

class JoinOrganisationRequest(BaseModel):

    organisation_id: str

    role: Literal[
        "user",
        "support_agent"
    ]

    department_id: str | None = None


# ============================================================
# TOKEN
# ============================================================

class TokenResponse(BaseModel):

    access_token: str

    token_type: str = "bearer"

# from pydantic import BaseModel, EmailStr, Field
# from typing import Literal

# from models.user import UserRole


# class InitialDepartment(BaseModel):
#     name: str = Field(
#         min_length=2,
#         max_length=100
#     )

#     bot_enabled: bool = True
#     human_support_enabled: bool = True


# # ============================================================
# # NORMAL USER REGISTRATION
# # ============================================================


# class RegisterRequest(BaseModel):

#     name: str = Field(
#         min_length=2,
#         max_length=100
#     )

#     email: EmailStr

#     password: str = Field(
#         min_length=8,
#         max_length=128
#     )

#     organisation_id: str

#     role: Literal[
#         "user",
#         "support_agent"
#     ]

#     department_id: str | None = None


# # ============================================================
# # CREATE ORGANISATION
# # ============================================================

# class CreateOrganisationRequest(BaseModel):
#     organisation_name: str = Field(
#         min_length=2,
#         max_length=150
#     )

#     name: str = Field(
#         min_length=2,
#         max_length=100
#     )

#     email: EmailStr

#     password: str = Field(
#         min_length=8,
#         max_length=128
#     )

#     departments: list[InitialDepartment] = Field(
#         default_factory=list
#     )


# # ============================================================
# # LOGIN
# # ============================================================

# class LoginRequest(BaseModel):
#     email: EmailStr
#     password: str


# # ============================================================
# # JOIN ORGANISATION
# # ============================================================

# class JoinOrganisationRequest(BaseModel):
#     organisation_id: str

#     role: UserRole

#     department_id: str | None = None


# # ============================================================
# # TOKEN
# # ============================================================

# class TokenResponse(BaseModel):
#     access_token: str
#     token_type: str = "bearer"

# # from pydantic import BaseModel, EmailStr, Field

# # from models.user import UserRole


# # class InitialDepartment(BaseModel):
# #     name: str = Field(
# #         min_length=2,
# #         max_length=100
# #     )

# #     bot_enabled: bool = True
# #     human_support_enabled: bool = True


# # class CreateOrganisationRequest(BaseModel):
# #     organisation_name: str = Field(
# #         min_length=2,
# #         max_length=150
# #     )

# #     name: str = Field(
# #         min_length=2,
# #         max_length=100
# #     )

# #     email: EmailStr

# #     password: str = Field(
# #         min_length=8,
# #         max_length=128
# #     )

# #     departments: list[InitialDepartment] = Field(default_factory=list)


# # class LoginRequest(BaseModel):
# #     email: EmailStr
# #     password: str


# # class JoinOrganisationRequest(BaseModel):
# #     organisation_id: str

# #     role: UserRole

# #     department_id: str | None = None


# # class TokenResponse(BaseModel):
# #     access_token: str
# #     token_type: str = "bearer"

# # class RegisterRequest(BaseModel):
# #     name: str = Field(
# #         min_length=2,
# #         max_length=100
# #     )

# #     email: EmailStr

# #     password: str = Field(
# #         min_length=8,
# #         max_length=128
# #     )