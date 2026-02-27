from __future__ import annotations
import datetime
from pydantic import BaseModel, EmailStr, validator, ConfigDict
from typing import Optional, List, Literal
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
    reset_password_token: Optional[str] = None
    reset_password_expires_at: Optional[datetime.datetime] = None

class UserResponse(UserBase):
    id: int
    is_verified: bool
    verification_badge: bool
    trust_score: Decimal
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

class TokenRefreshRequest(BaseModel):
    refresh_token: str

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
