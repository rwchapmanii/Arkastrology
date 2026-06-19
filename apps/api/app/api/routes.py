from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Header, Query, Request
from pydantic import BaseModel

from app.models.auth import (
    AccountProfileResponse,
    AccountProfileUpdateRequest,
    AuthRequest,
    AuthSessionResponse,
    EmailRequest,
    LogoutResponse,
    PasswordResetConfirmRequest,
    PasswordResetConfirmResponse,
    PreferencesResponse,
    PreferencesUpdateRequest,
    SessionStatusResponse,
    TokenConfirmRequest,
    TokenDeliveryResponse,
    VerificationConfirmResponse,
)
from app.models.chat import GroundedChatRequest, GroundedChatResponse
from app.models.chart import (
    NatalReadingRequest,
    NatalReadingResponse,
    PlaceResolveRequest,
    PlaceResolveResponse,
    SynastryReadingRequest,
    SynastryReadingResponse,
)
from app.models.history import ReadingHistoryDetailResponse, ReadingHistoryListResponse, ReadingHistoryUpdateRequest
from app.models.social import (
    AddRelationshipRequest,
    DirectoryProfileListResponse,
    PublicChartProfileRequest,
    PublicChartProfileResponse,
    RelationshipListResponse,
)
from app.services.auth_service import AuthService
from app.services.citation_service import CitationService
from app.services.content_loader import load_ontology
from app.services.natal_service import NatalReadingService
from app.services.place_service import PlaceResolutionService
from app.services.rate_limit_service import RateLimitService
from app.services.reading_history_service import ReadingHistoryService
from app.services.relationship_service import RelationshipService
from app.services.source_chat_service import SourceChatService
from app.services.synastry_service import SynastryReadingService

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: str


class OntologyStatusResponse(BaseModel):
    planet_ontology: str
    signs_ontology: str
    houses_ontology: str
    aspects_ontology: str
    jungian_mappings: str
    citation_structure: str
    counts: dict[str, int]


def _client_ip(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host.strip().lower()
    return "unknown"


def _email_key(email: str) -> str:
    return email.strip().lower() or "unknown"


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="the-ark-api",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/healthz", response_model=HealthResponse)
def healthz() -> HealthResponse:
    return health()


@router.get("/v1/ontology/status", response_model=OntologyStatusResponse)
def ontology_status() -> OntologyStatusResponse:
    ontology = load_ontology()
    counts = {key: len(value) for key, value in ontology.items()}
    return OntologyStatusResponse(
        planet_ontology="ingested",
        signs_ontology="ingested",
        houses_ontology="ingested",
        aspects_ontology="ingested",
        jungian_mappings="ingested",
        citation_structure="ingested",
        counts=counts,
    )


@router.post("/v1/auth/register", response_model=AuthSessionResponse)
def register_auth(request: AuthRequest, http_request: Request) -> AuthSessionResponse:
    client_ip = _client_ip(http_request)
    email = _email_key(request.email)
    RateLimitService.enforce("auth-register-ip", client_ip, limit=8, window_seconds=3600, detail="Too many registration attempts from this network. Try again later.")
    RateLimitService.enforce("auth-register-email", email, limit=4, window_seconds=3600, detail="Too many registration attempts for that email. Try again later.")
    return AuthService.register(request)


@router.post("/v1/auth/login", response_model=AuthSessionResponse)
def login_auth(request: AuthRequest, http_request: Request) -> AuthSessionResponse:
    client_ip = _client_ip(http_request)
    email = _email_key(request.email)
    RateLimitService.enforce("auth-login-ip", client_ip, limit=20, window_seconds=900, detail="Too many sign-in attempts from this network. Try again in a bit.")
    RateLimitService.enforce("auth-login-email", email, limit=10, window_seconds=900, detail="Too many sign-in attempts for that email. Try again in a bit.")
    return AuthService.login(request)


@router.get("/v1/auth/session", response_model=SessionStatusResponse)
def get_auth_session(authorization: Annotated[Optional[str], Header()] = None) -> SessionStatusResponse:
    return AuthService.get_session(authorization)


@router.post("/v1/auth/logout", response_model=LogoutResponse)
def logout_auth(authorization: Annotated[Optional[str], Header()] = None) -> LogoutResponse:
    return AuthService.logout(authorization)


@router.post("/v1/auth/verify-email/request", response_model=TokenDeliveryResponse)
def request_email_verification(request: EmailRequest, http_request: Request) -> TokenDeliveryResponse:
    client_ip = _client_ip(http_request)
    email = _email_key(request.email)
    RateLimitService.enforce("auth-verify-request-ip", client_ip, limit=10, window_seconds=3600, detail="Too many verification-email requests from this network. Try again later.")
    RateLimitService.enforce("auth-verify-request-email", email, limit=4, window_seconds=3600, detail="Too many verification-email requests for that address. Try again later.")
    return AuthService.request_email_verification(request)


@router.post("/v1/auth/verify-email/confirm", response_model=VerificationConfirmResponse)
def confirm_email_verification(request: TokenConfirmRequest, http_request: Request) -> VerificationConfirmResponse:
    client_ip = _client_ip(http_request)
    email = _email_key(request.email)
    RateLimitService.enforce("auth-verify-confirm-ip", client_ip, limit=20, window_seconds=3600, detail="Too many verification attempts from this network. Try again later.")
    RateLimitService.enforce("auth-verify-confirm-email", email, limit=10, window_seconds=3600, detail="Too many verification attempts for that address. Try again later.")
    return AuthService.confirm_email_verification(request)


@router.post("/v1/auth/password-reset/request", response_model=TokenDeliveryResponse)
def request_password_reset(request: EmailRequest, http_request: Request) -> TokenDeliveryResponse:
    client_ip = _client_ip(http_request)
    email = _email_key(request.email)
    RateLimitService.enforce("auth-reset-request-ip", client_ip, limit=10, window_seconds=3600, detail="Too many password-reset requests from this network. Try again later.")
    RateLimitService.enforce("auth-reset-request-email", email, limit=4, window_seconds=3600, detail="Too many password-reset requests for that address. Try again later.")
    return AuthService.request_password_reset(request)


@router.post("/v1/auth/password-reset/confirm", response_model=PasswordResetConfirmResponse)
def confirm_password_reset(request: PasswordResetConfirmRequest, http_request: Request) -> PasswordResetConfirmResponse:
    client_ip = _client_ip(http_request)
    email = _email_key(request.email)
    RateLimitService.enforce("auth-reset-confirm-ip", client_ip, limit=20, window_seconds=3600, detail="Too many password-reset attempts from this network. Try again later.")
    RateLimitService.enforce("auth-reset-confirm-email", email, limit=10, window_seconds=3600, detail="Too many password-reset attempts for that address. Try again later.")
    return AuthService.confirm_password_reset(request)


@router.get("/v1/account/preferences", response_model=PreferencesResponse)
def get_account_preferences(authorization: Annotated[Optional[str], Header()] = None) -> PreferencesResponse:
    return AuthService.get_preferences(authorization)


@router.patch("/v1/account/preferences", response_model=PreferencesResponse)
def update_account_preferences(
    request: PreferencesUpdateRequest,
    authorization: Annotated[Optional[str], Header()] = None,
) -> PreferencesResponse:
    return AuthService.update_preferences(request, authorization)


@router.get("/v1/account/profile", response_model=AccountProfileResponse)
def get_account_profile(authorization: Annotated[Optional[str], Header()] = None) -> AccountProfileResponse:
    return AuthService.get_profile(authorization)


@router.patch("/v1/account/profile", response_model=AccountProfileResponse)
def update_account_profile(
    request: AccountProfileUpdateRequest,
    authorization: Annotated[Optional[str], Header()] = None,
) -> AccountProfileResponse:
    return AuthService.update_profile(request, authorization)


@router.get("/v1/account/readings", response_model=ReadingHistoryListResponse)
def list_account_readings(
    authorization: Annotated[Optional[str], Header()] = None,
    query: Optional[str] = Query(default=None),
    favorite_only: bool = Query(default=False),
    chart_type: Optional[str] = Query(default=None),
    tag: Optional[str] = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=50),
) -> ReadingHistoryListResponse:
    user_id = AuthService.get_user_id_for_session(authorization)
    return ReadingHistoryService.list_readings(
        user_id,
        query=query,
        favorite_only=favorite_only,
        chart_type=chart_type,
        tag=tag,
        offset=offset,
        limit=limit,
    )


@router.get("/v1/account/readings/{reading_id}", response_model=ReadingHistoryDetailResponse)
def get_account_reading(reading_id: str, authorization: Annotated[Optional[str], Header()] = None) -> ReadingHistoryDetailResponse:
    user_id = AuthService.get_user_id_for_session(authorization)
    return ReadingHistoryService.get_reading(user_id, reading_id)


@router.patch("/v1/account/readings/{reading_id}", response_model=ReadingHistoryDetailResponse)
def update_account_reading(
    reading_id: str,
    request: ReadingHistoryUpdateRequest,
    authorization: Annotated[Optional[str], Header()] = None,
) -> ReadingHistoryDetailResponse:
    user_id = AuthService.get_user_id_for_session(authorization)
    return ReadingHistoryService.update_reading(user_id, reading_id, request)


@router.get("/v1/account/public-chart", response_model=PublicChartProfileResponse)
def get_public_chart(authorization: Annotated[Optional[str], Header()] = None) -> PublicChartProfileResponse:
    user_id = AuthService.get_user_id_for_session(authorization)
    return RelationshipService.get_public_chart_profile(user_id)


@router.put("/v1/account/public-chart", response_model=PublicChartProfileResponse)
def set_public_chart(
    request: PublicChartProfileRequest,
    authorization: Annotated[Optional[str], Header()] = None,
) -> PublicChartProfileResponse:
    user_id = AuthService.get_user_id_for_session(authorization)
    return RelationshipService.set_public_chart_profile(user_id, request)


@router.get("/v1/account/relationships", response_model=RelationshipListResponse)
def list_relationships(authorization: Annotated[Optional[str], Header()] = None) -> RelationshipListResponse:
    user_id = AuthService.get_user_id_for_session(authorization)
    return RelationshipService.list_relationships(user_id)


@router.post("/v1/account/relationships", response_model=RelationshipListResponse)
def add_relationship(
    request: AddRelationshipRequest,
    authorization: Annotated[Optional[str], Header()] = None,
) -> RelationshipListResponse:
    user_id = AuthService.get_user_id_for_session(authorization)
    return RelationshipService.add_relationship(user_id, request)


@router.delete("/v1/account/relationships/{profile_id}", response_model=RelationshipListResponse)
def remove_relationship(
    profile_id: str,
    authorization: Annotated[Optional[str], Header()] = None,
) -> RelationshipListResponse:
    user_id = AuthService.get_user_id_for_session(authorization)
    return RelationshipService.remove_relationship(user_id, profile_id)


@router.get("/v1/directory/profiles", response_model=DirectoryProfileListResponse)
def directory_profiles(
    query: str = Query(default="", max_length=120),
    limit: int = Query(default=20, ge=1, le=50),
    authorization: Annotated[Optional[str], Header()] = None,
) -> DirectoryProfileListResponse:
    user_id = AuthService.get_user_id_for_session(authorization)
    return RelationshipService.search_directory(user_id=user_id, query=query, limit=limit)


@router.post("/v1/places/resolve", response_model=PlaceResolveResponse)
def resolve_place(request: PlaceResolveRequest) -> PlaceResolveResponse:
    return PlaceResolutionService.resolve(request)


@router.post("/v1/readings/natal", response_model=NatalReadingResponse)
def create_natal_reading(
    request: NatalReadingRequest,
    authorization: Annotated[Optional[str], Header()] = None,
) -> NatalReadingResponse:
    response = NatalReadingService.build_response(request)
    user_id = AuthService.get_optional_user_id_for_session(authorization)
    if user_id:
        ReadingHistoryService.record_reading(user_id, response.model_dump())
    return response


@router.post("/v1/readings/synastry", response_model=SynastryReadingResponse)
def create_synastry_reading(
    request: SynastryReadingRequest,
    authorization: Annotated[Optional[str], Header()] = None,
) -> SynastryReadingResponse:
    response = SynastryReadingService.build_response(request)
    user_id = AuthService.get_optional_user_id_for_session(authorization)
    if user_id:
        ReadingHistoryService.record_reading(user_id, response.model_dump())
    return response


@router.post("/v1/chat/grounded", response_model=GroundedChatResponse)
def grounded_chat(
    request: GroundedChatRequest,
    authorization: Annotated[Optional[str], Header()] = None,
) -> GroundedChatResponse:
    if authorization:
        AuthService.get_optional_user_id_for_session(authorization)
    return SourceChatService.answer_question(request)


@router.get("/v1/citations")
def list_citations():
    return {"citations": CitationService.get_all()}
