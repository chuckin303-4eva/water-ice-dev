from pydantic import BaseModel, Field, field_validator

from app.core.validators import validate_email_format


class LoginRequest(BaseModel):
    # Plain str, not EmailStr -- avoids pulling in the email-validator
    # dependency for a login field where a malformed value just fails to
    # match a user and returns 401.
    email: str
    password: str


class RegisterRequest(BaseModel):
    """Self-serve signup: creates a brand-new Organization plus its first
    user, who becomes that org's admin (ADR-0012). No email verification
    or CAPTCHA -- both real hardening gaps, not silently faked; noted as
    deferred, not solved, in ADR-0012.
    """

    organization_name: str = Field(min_length=1, max_length=255)
    email: str
    password: str = Field(min_length=8)

    _validate_email = field_validator("email")(validate_email_format)


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
    role: str
