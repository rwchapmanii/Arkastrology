from typing import List, Optional

from pydantic import BaseModel, Field


class AccountPreferences(BaseModel):
    include_jungian_default: bool = False
    include_red_book_prompts_default: bool = False


class AccountProfile(BaseModel):
    display_name: Optional[str] = None
    timezone_name: Optional[str] = None
    bio: Optional[str] = None
    email_verified: bool = False


class AuthRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=8)
    display_name: Optional[str] = None


class EmailRequest(BaseModel):
    email: str


class TokenConfirmRequest(BaseModel):
    email: str
    token: str = Field(..., min_length=6)


class PasswordResetConfirmRequest(BaseModel):
    email: str
    token: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=8)


class AccountProfileUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    timezone_name: Optional[str] = None
    bio: Optional[str] = None


class AccountSummary(BaseModel):
    user_id: str
    email: str
    display_name: Optional[str] = None
    plan: str = "prototype"
    preferences: AccountPreferences
    email_verified: bool = False
    timezone_name: Optional[str] = None
    bio: Optional[str] = None


class AuthSessionResponse(BaseModel):
    status: str = "authenticated"
    session_token: str
    session_expires_at: str
    account: AccountSummary
    notes: List[str] = Field(default_factory=list)


class SessionStatusResponse(BaseModel):
    status: str = "authenticated"
    session_expires_at: str
    account: AccountSummary


class PreferencesResponse(BaseModel):
    status: str = "ok"
    preferences: AccountPreferences


class PreferencesUpdateRequest(BaseModel):
    include_jungian_default: Optional[bool] = None
    include_red_book_prompts_default: Optional[bool] = None


class AccountProfileResponse(BaseModel):
    status: str = "ok"
    profile: AccountProfile


class TokenDeliveryResponse(BaseModel):
    status: str
    token_expires_at: str
    delivery_mode: str
    delivery_target: str
    prototype_token: Optional[str] = None
    notes: List[str] = Field(default_factory=list)


class VerificationConfirmResponse(BaseModel):
    status: str
    email_verified: bool
    notes: List[str] = Field(default_factory=list)


class PasswordResetConfirmResponse(BaseModel):
    status: str
    notes: List[str] = Field(default_factory=list)


class LogoutResponse(BaseModel):
    status: str = "signed_out"
