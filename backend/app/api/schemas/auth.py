from pydantic import BaseModel


class LoginRequest(BaseModel):
    # Plain str, not EmailStr -- avoids pulling in the email-validator
    # dependency for a login field where a malformed value just fails to
    # match a user and returns 401. Reconsider if a signup form is built.
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    organization_id: int
    email: str
    is_active: bool

    model_config = {"from_attributes": True}
