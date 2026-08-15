from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: str
    name: str | None = None
    email: str


class AuthResponse(BaseModel):
    user: UserResponse


class ConversationCreateRequest(BaseModel):
    title: str = Field(default="New conversation", max_length=120)


class ConversationRenameRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
