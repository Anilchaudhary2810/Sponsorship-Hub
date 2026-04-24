from __future__ import annotations
import datetime
from pydantic import BaseModel, EmailStr, validator, ConfigDict, Field
from typing import Optional, List, Literal, Any
from decimal import Decimal

# Literal Types
RoleType = Literal["sponsor", "organizer", "influencer"]
PaymentByType = Literal["organizer", "sponsor", "influencer"]
DealType = Literal["sponsorship", "promotion"]

# ------------------------------------------------
# LOGIN / AUTH
# ------------------------------------------------
class LoginRequest(BaseModel):
    email: str
    password: str

# ------------------------------------------------
# USER SCHEMAS
# ------------------------------------------------
class UserBase(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    role: RoleType
    state: Optional[str] = None
    city: Optional[str] = None
    company_name: Optional[str] = None
    organization_name: Optional[str] = None
    focus: Optional[str] = None
    preferred_budget: Optional[Decimal] = None
    
    # Influencer-specific
    instagram_handle: Optional[str] = None
    youtube_channel: Optional[str] = None
    twitter_handle: Optional[str] = None
    audience_size: Optional[int] = 0
    platforms: Optional[str] = None
    niche: Optional[str] = None
    
    website: Optional[str] = None
    about: Optional[str] = None

class UserCreate(UserBase):
    password: str

    @validator("password")
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        return v

class PublicUserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    company_name: Optional[str] = None
    organization_name: Optional[str] = None
    focus: Optional[str] = None
    preferred_budget: Optional[Decimal] = None
    
    instagram_handle: Optional[str] = None
    youtube_channel: Optional[str] = None
    twitter_handle: Optional[str] = None
    audience_size: Optional[int] = None
    platforms: Optional[str] = None
    niche: Optional[str] = None
    
    website: Optional[str] = None
    about: Optional[str] = None

class AdminUserUpdate(PublicUserUpdate):
    is_verified: Optional[bool] = None
    role: Optional[RoleType] = None
    trust_score: Optional[Decimal] = None
    verification_badge: Optional[bool] = None

# Internal schema for system updates (not for API input)
class SystemUserUpdate(AdminUserUpdate):
    refresh_token: Optional[str] = None
    verification_token: Optional[str] = None
    verification_token_expires_at: Optional[datetime.datetime] = None
    reset_password_token: Optional[str] = None
    reset_password_expires_at: Optional[datetime.datetime] = None

class UserResponse(UserBase):
    id: int
    is_verified: bool
    verification_badge: bool
    trust_score: Decimal
    plan_tier: str
    plan_status: str
    plan_renewal_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)

class PublicUserResponse(BaseModel):
    id: int
    full_name: str
    role: RoleType
    city: Optional[str] = None
    state: Optional[str] = None
    company_name: Optional[str] = None
    organization_name: Optional[str] = None
    niche: Optional[str] = None
    audience_size: Optional[int] = None
    verification_badge: bool
    trust_score: Decimal

    model_config = ConfigDict(from_attributes=True)

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    user: UserResponse

    model_config = ConfigDict(from_attributes=True)


class AuthSessionResponse(BaseModel):
    token_type: str = "bearer"
    user: UserResponse
    message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RegisterResponse(BaseModel):
    message: str
    user: UserResponse
    requires_verification: bool = True
    verification_token_preview: Optional[str] = None
    verification_email_sent: bool = False

    model_config = ConfigDict(from_attributes=True)

class TokenRefreshRequest(BaseModel):
    refresh_token: Optional[str] = None


class VerificationResendRequest(BaseModel):
    email: EmailStr


class VerificationResendResponse(BaseModel):
    message: str
    verification_token_preview: Optional[str] = None

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str

# ------------------------------------------------
# CAMPAIGN SCHEMAS (New)
# ------------------------------------------------
class CampaignBase(BaseModel):
    title: str
    description: Optional[str] = None
    budget: Optional[Decimal] = None
    platform_required: Optional[str] = None
    deliverables: Optional[str] = None
    status: str = "open"
    event_id: Optional[int] = None

class CampaignCreate(CampaignBase):
    creator_id: int

class CampaignUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    budget: Optional[Decimal] = None
    platform_required: Optional[str] = None
    deliverables: Optional[str] = None
    status: Optional[str] = None

class CampaignResponse(CampaignBase):
    id: int
    creator_id: int
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)

# ------------------------------------------------
# EVENT SCHEMAS
# ------------------------------------------------
class EventBase(BaseModel):
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    expected_audience: Optional[str] = None
    about: Optional[str] = None
    date: Optional[datetime.date] = None
    location: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    raw_budget: Optional[Decimal] = None
    currency: Optional[str] = "INR"

class EventCreate(EventBase):
    organizer_id: int

class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    expected_audience: Optional[str] = None
    about: Optional[str] = None
    date: Optional[datetime.date] = None
    location: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    raw_budget: Optional[Decimal] = None
    currency: Optional[str] = None
    media_items: Optional[List[dict]] = None

class EventResponse(EventBase):
    id: int
    organizer_id: int
    media_items: Optional[List[dict]] = []
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)

# ------------------------------------------------
# REVIEW SCHEMAS
# ------------------------------------------------
class ReviewBase(BaseModel):
    deal_id: int
    reviewer_id: int
    reviewer_role: RoleType
    target_role: RoleType
    rating: int
    comment: Optional[str] = None

class ReviewCreate(ReviewBase):
    pass

class ReviewResponse(ReviewBase):
    id: int
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)

# ------------------------------------------------
# DEAL SCHEMAS
# ------------------------------------------------
class DealBase(BaseModel):
    sponsor_id: Optional[int] = None
    organizer_id: Optional[int] = None
    influencer_id: Optional[int] = None
    event_id: Optional[int] = None
    campaign_id: Optional[int] = None
    deal_type: DealType

class DealCreate(DealBase):
    pass

class DealUpdate(BaseModel):
    # Only non-critical fields can be updated directly via generic PUT
    proof_of_work: Optional[str] = None

# Internal schema for system updates (not for API input)
class SystemDealUpdate(BaseModel):
    sponsor_accepted: Optional[bool] = None
    organizer_accepted: Optional[bool] = None
    influencer_accepted: Optional[bool] = None
    payment_done: Optional[bool] = None
    payment_amount: Optional[Decimal] = None
    currency: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    payment_status: Optional[str] = None
    payment_timestamp: Optional[datetime.datetime] = None
    organizer_signed: Optional[bool] = None
    sponsor_signed: Optional[bool] = None
    influencer_signed: Optional[bool] = None
    status: Optional[str] = None

class DealResponse(DealBase):
    id: int
    event: Optional[EventResponse] = None
    campaign: Optional[CampaignResponse] = None
    sponsor_accepted: bool
    organizer_accepted: bool
    influencer_accepted: bool
    sponsor_signed: bool
    organizer_signed: bool
    influencer_signed: bool
    payment_done: bool
    proof_of_work: Optional[str] = None
    payment_amount: Decimal
    currency: str
    razorpay_payment_id: Optional[str] = None
    payment_status: Optional[str] = None
    status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    reviews: List[ReviewResponse] = []
    
    # Nested objects for frontend mapping
    sponsor: Optional[UserResponse] = None
    organizer: Optional[UserResponse] = None
    influencer: Optional[UserResponse] = None

    model_config = ConfigDict(from_attributes=True)

class DealAccept(BaseModel):
    role: RoleType
    accept: bool

class DealPayment(BaseModel):
    amount: Decimal
    currency: Optional[str] = "INR"
    payment_by: PaymentByType
    method: Optional[str] = None
    details: Optional[dict] = None

class PaymentCheckoutConfigResponse(BaseModel):
    provider: str = "razorpay"
    key_id: Optional[str] = None

class DealSign(BaseModel):
    role: RoleType
    signature: str


# ------------------------------------------------
# CHAT SCHEMAS
# ------------------------------------------------
class ChatMessageBase(BaseModel):
    deal_id: int
    content: str

class ChatMessageCreate(ChatMessageBase):
    sender_id: int
    sender_role: str

class ChatMessageResponse(ChatMessageBase):
    id: int
    sender_id: int
    sender_role: str
    sender_name: Optional[str] = None
    timestamp: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class AIContextRequest(BaseModel):
    path: str = "/"
    page_title: Optional[str] = None
    page_data: dict[str, Any] = Field(default_factory=dict)


class AIMessageRequest(AIContextRequest):
    message: str
    history_limit: int = 12


class AIChatHistoryItem(BaseModel):
    id: int
    role: Literal["user", "assistant"]
    content: str
    route_path: Optional[str] = None
    page_title: Optional[str] = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class AIContextResponse(BaseModel):
    path: str
    title: str
    role: str
    capabilities: list[str] = Field(default_factory=list)
    user_stats: dict[str, Any] = Field(default_factory=dict)
    global_stats: dict[str, Any] = Field(default_factory=dict)
    recent_items: list[dict[str, Any]] = Field(default_factory=list)
    page_data: dict[str, Any] = Field(default_factory=dict)
    confidentiality_note: str


class AIMessageResponse(BaseModel):
    reply: str
    context: AIContextResponse
    history: list[AIChatHistoryItem] = Field(default_factory=list)


# ------------------------------------------------
# NOTIFICATION SCHEMAS
# ------------------------------------------------
class NotificationBase(BaseModel):
    title: str
    message: str
    type: str

class NotificationResponse(NotificationBase):
    id: int
    user_id: int
    is_read: bool
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class BillingPlanResponse(BaseModel):
    code: str
    name: str
    monthly_price_inr: int
    limits: dict[str, int]
    features: list[str]


class BillingUsageResponse(BaseModel):
    month_start: str
    events_created: int
    campaigns_created: int
    deals_created: int
    chat_messages_sent: int
    notifications_received: int


class BillingOverviewResponse(BaseModel):
    plan_tier: str
    plan_status: str
    plan_renewal_at: Optional[datetime.datetime] = None
    limits: dict[str, int]
    usage: BillingUsageResponse


class ChangePlanRequest(BaseModel):
    target_plan: Literal["free", "starter", "growth", "enterprise"]
    note: Optional[str] = None


class BillingEventResponse(BaseModel):
    id: int
    from_plan: Optional[str] = None
    to_plan: str
    amount: Decimal
    currency: str
    status: str
    note: Optional[str] = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class KYCSubmissionCreate(BaseModel):
    document_type: Literal["aadhaar", "pan", "passport", "gst", "other"]
    document_number_masked: str
    document_url: Optional[str] = None


class KYCSubmissionResponse(BaseModel):
    id: int
    user_id: int
    reviewer_id: Optional[int] = None
    document_type: str
    document_number_masked: str
    document_url: Optional[str] = None
    status: str
    risk_score: int
    risk_flags: list[str]
    review_note: Optional[str] = None
    submitted_at: datetime.datetime
    reviewed_at: Optional[datetime.datetime] = None

    model_config = ConfigDict(from_attributes=True)


class KYCReviewRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    review_note: Optional[str] = None
    risk_score: Optional[int] = None
    risk_flags: Optional[list[str]] = None


class TrustProfileResponse(BaseModel):
    verification_badge: bool
    trust_score: Decimal
    kyc_status: str
    latest_submission: Optional[KYCSubmissionResponse] = None
    risk_flags: list[str]
    risk_level: Literal["low", "medium", "high"]


WorkspaceRole = Literal["owner", "manager", "finance", "viewer"]
ApprovalStatus = Literal["pending", "approved", "rejected"]
MilestoneStatus = Literal["planned", "funded", "released", "disputed"]
DisputeStatus = Literal["open", "under_review", "resolved", "rejected"]
NudgeState = Literal["pending", "sent", "dismissed", "done"]
IntegrationProvider = Literal["hubspot", "sheets", "slack", "email", "calendar"]


class DealTemplateBase(BaseModel):
    name: str
    description: Optional[str] = None
    deal_type: DealType
    terms_json: dict[str, Any] = {}
    is_default: bool = False


class DealTemplateCreate(DealTemplateBase):
    pass


class DealTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    terms_json: Optional[dict[str, Any]] = None
    is_default: Optional[bool] = None


class DealTemplateResponse(DealTemplateBase):
    id: int
    owner_user_id: int
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class DealApprovalCreate(BaseModel):
    approver_role: WorkspaceRole
    approver_user_id: Optional[int] = None
    note: Optional[str] = None


class DealApprovalDecision(BaseModel):
    decision: Literal["approved", "rejected"]
    note: Optional[str] = None


class DealApprovalResponse(BaseModel):
    id: int
    deal_id: int
    requested_by_user_id: Optional[int] = None
    approver_user_id: Optional[int] = None
    approver_role: WorkspaceRole
    status: ApprovalStatus
    note: Optional[str] = None
    decided_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class NegotiationEntryCreate(BaseModel):
    change_type: Literal["comment", "counter_offer", "term_update"] = "comment"
    message: Optional[str] = None
    payload: dict[str, Any] = {}


class NegotiationEntryResponse(BaseModel):
    id: int
    deal_id: int
    actor_user_id: Optional[int] = None
    change_type: str
    message: Optional[str] = None
    payload: dict[str, Any] = {}
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class DealMilestoneCreate(BaseModel):
    sequence_no: Optional[int] = None
    title: str
    description: Optional[str] = None
    amount: Decimal
    due_date: Optional[datetime.date] = None


class DealMilestoneAction(BaseModel):
    action: Literal["fund", "release", "mark_disputed"]


class DealMilestoneResponse(BaseModel):
    id: int
    deal_id: int
    sequence_no: int
    title: str
    description: Optional[str] = None
    amount: Decimal
    due_date: Optional[datetime.date] = None
    status: MilestoneStatus
    funded_at: Optional[datetime.datetime] = None
    released_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class DealDisputeCreate(BaseModel):
    reason: str
    details: Optional[str] = None


class DealDisputeResolve(BaseModel):
    decision: Literal["under_review", "resolved", "rejected"]
    resolution_note: Optional[str] = None
    settlement_amount: Optional[Decimal] = None


class DealDisputeResponse(BaseModel):
    id: int
    deal_id: int
    opened_by_user_id: Optional[int] = None
    reason: str
    details: Optional[str] = None
    status: DisputeStatus
    resolution_note: Optional[str] = None
    settlement_amount: Optional[Decimal] = None
    opened_at: datetime.datetime
    resolved_at: Optional[datetime.datetime] = None

    model_config = ConfigDict(from_attributes=True)


class WorkspaceCreate(BaseModel):
    name: str


class WorkspaceMemberInvite(BaseModel):
    user_id: int
    role: WorkspaceRole = "viewer"


class WorkspaceMemberUpdate(BaseModel):
    role: Optional[WorkspaceRole] = None
    status: Optional[Literal["invited", "active", "removed"]] = None


class WorkspaceMemberResponse(BaseModel):
    id: int
    workspace_id: int
    user_id: int
    role: WorkspaceRole
    status: str
    invited_by_user_id: Optional[int] = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class WorkspaceResponse(BaseModel):
    id: int
    name: str
    owner_user_id: int
    is_active: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime
    members: list[WorkspaceMemberResponse] = []

    model_config = ConfigDict(from_attributes=True)


class WorkspaceResourceAdd(BaseModel):
    resource_type: Literal["event", "campaign", "deal", "template", "report"]
    resource_id: int


class WorkspaceResourceResponse(BaseModel):
    id: int
    workspace_id: int
    resource_type: str
    resource_id: int
    added_by_user_id: Optional[int] = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class LifecycleNudgeResponse(BaseModel):
    id: int
    user_id: int
    nudge_type: str
    title: str
    message: str
    state: NudgeState
    due_at: Optional[datetime.datetime] = None
    payload: dict[str, Any] = {}
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class NudgeStateUpdate(BaseModel):
    state: Literal["dismissed", "done"]


class ROIReportResponse(BaseModel):
    role: str
    total_deals: int
    closed_deals: int
    active_deals: int
    conversion_rate: float
    total_value: Decimal
    paid_value: Decimal
    avg_deal_value: Decimal
    period_days: int


class CampaignOutcomeRow(BaseModel):
    id: int
    title: str
    status: str
    budget: Decimal
    linked_deals: int
    closed_deals: int
    conversion_rate: float


class MonthlyExecutiveReportResponse(BaseModel):
    month: str
    role: str
    kpis: dict[str, Any]
    highlights: list[str]
    risks: list[str]


class IntegrationConnectRequest(BaseModel):
    provider: IntegrationProvider
    config_json: Optional[dict[str, Any]] = None


class IntegrationConnectionResponse(BaseModel):
    id: int
    user_id: int
    provider: IntegrationProvider
    status: str
    config_json: dict[str, Any]
    last_sync_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class IntegrationSyncRequest(BaseModel):
    event_type: str
    payload: dict[str, Any] = {}


class IntegrationEventResponse(BaseModel):
    id: int
    connection_id: int
    event_type: str
    status: str
    request_payload: dict[str, Any]
    response_payload: dict[str, Any]
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)
