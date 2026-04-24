from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Numeric,
    Text,
    Date,
    DateTime,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from .database import Base


# ==========================================
# USERS
# ==========================================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    full_name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    phone = Column(String(20))
    password = Column(String(255), nullable=False)

    role = Column(String(20), nullable=False, index=True) 

    # Auth Hardening
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_token = Column(String(255), nullable=True)
    verification_token_expires_at = Column(DateTime, nullable=True)
    reset_password_token = Column(String(255), nullable=True)
    reset_password_expires_at = Column(DateTime, nullable=True)
    refresh_token = Column(String(255), nullable=True, index=True)
    plan_tier = Column(String(30), default="free", nullable=False, index=True)
    plan_status = Column(String(20), default="active", nullable=False, index=True)
    plan_renewal_at = Column(DateTime, nullable=True)

    # Sponsor/Organizer fields
    company_name = Column(String(200))
    organization_name = Column(String(200))
    focus = Column(String(200))
    preferred_budget = Column(Numeric(12, 2))

    # Influencer Fields
    instagram_handle = Column(String(100))
    youtube_channel = Column(String(200))
    twitter_handle = Column(String(100))
    audience_size = Column(Integer, default=0)
    platforms = Column(String(300))
    niche = Column(String(100))

    # Common
    state = Column(String(50))
    city = Column(String(50))
    website = Column(String(255))
    about = Column(Text)
    verification_badge = Column(Boolean, default=False)
    trust_score = Column(Numeric(3, 2), default=5.00)

    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime, nullable=True)

    events = relationship("Event", back_populates="organizer", cascade="all, delete-orphan")
    campaigns = relationship("Campaign", back_populates="creator", cascade="all, delete-orphan")
    deals_As_sponsor = relationship("Deal", foreign_keys="Deal.sponsor_id", back_populates="sponsor")
    deals_as_organizer = relationship("Deal", foreign_keys="Deal.organizer_id", back_populates="organizer")
    deals_as_influencer = relationship("Deal", foreign_keys="Deal.influencer_id", back_populates="influencer")
    reviews_as_reviewer = relationship("DealReview", foreign_keys="DealReview.reviewer_id", back_populates="reviewer")
    reviews_as_target = relationship("DealReview", foreign_keys="DealReview.target_user_id", back_populates="target_user")
    kyc_submissions = relationship("KYCSubmission", foreign_keys="KYCSubmission.user_id", back_populates="user", cascade="all, delete-orphan")
    ai_chat_messages = relationship("AIChatMessage", back_populates="user", cascade="all, delete-orphan")


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    budget = Column(Numeric(12, 2))
    platform_required = Column(String(100))
    deliverables = Column(Text)
    status = Column(String(20), default="open", index=True)

    creator_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="SET NULL"), nullable=True, index=True)

    created_at = Column(DateTime, server_default=func.now(), index=True)
    
    creator = relationship("User", back_populates="campaigns")
    event = relationship("Event")


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(100))
    expected_audience = Column(String(100))
    about = Column(Text)
    date = Column(Date, index=True)

    location = Column(String(150))
    city = Column(String(100), index=True)
    state = Column(String(50))

    raw_budget = Column(Numeric(12, 2))
    currency = Column(String(10), default="INR")

    organizer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime, nullable=True)
    media_items = Column(JSON, default=list)  # [{url, caption, type}]

    organizer = relationship("User", back_populates="events")


class Deal(Base):
    __tablename__ = "deals"

    id = Column(Integer, primary_key=True, index=True)

    sponsor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    organizer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    influencer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    
    event_id = Column(Integer, ForeignKey("events.id", ondelete="SET NULL"), nullable=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True)

    deal_type = Column(String(50), nullable=False, index=True)

    organizer_accepted = Column(Boolean, default=False, nullable=False)
    sponsor_accepted = Column(Boolean, default=False, nullable=False)
    influencer_accepted = Column(Boolean, default=False, nullable=False)

    # Payment Implementation
    payment_done = Column(Boolean, default=False, nullable=False, index=True)
    payment_amount = Column(Numeric(12, 2), default=0, nullable=False)
    currency = Column(String(10), default="INR")
    razorpay_payment_id = Column(String(255), unique=True, nullable=True, index=True)
    payment_status = Column(String(50), default="pending", index=True)
    payment_timestamp = Column(DateTime, nullable=True)

    proof_of_work = Column(Text)
    
    organizer_signed = Column(Boolean, default=False, nullable=False)
    sponsor_signed = Column(Boolean, default=False, nullable=False)
    influencer_signed = Column(Boolean, default=False, nullable=False)

    status = Column(String(20), default="proposed", nullable=False, index=True)

    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    sponsor = relationship("User", foreign_keys=[sponsor_id], back_populates="deals_As_sponsor")
    organizer = relationship("User", foreign_keys=[organizer_id], back_populates="deals_as_organizer")
    influencer = relationship("User", foreign_keys=[influencer_id], back_populates="deals_as_influencer")
    event = relationship("Event")
    campaign = relationship("Campaign")
    reviews = relationship("DealReview", back_populates="deal", cascade="all, delete-orphan")


class DealReview(Base):
    __tablename__ = "deal_reviews"

    id = Column(Integer, primary_key=True, index=True)

    deal_id = Column(Integer, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    target_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    reviewer_role = Column(String(20), nullable=False)
    target_role = Column(String(20), nullable=False)

    rating = Column(Integer, nullable=False)
    comment = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    deal = relationship("Deal", back_populates="reviews")
    reviewer = relationship("User", foreign_keys=[reviewer_id], back_populates="reviews_as_reviewer")
    target_user = relationship("User", foreign_keys=[target_user_id], back_populates="reviews_as_target")

    __table_args__ = (
        UniqueConstraint('deal_id', 'reviewer_id', name='uix_deal_reviewer'),
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, server_default=func.now(), index=True)

    deal = relationship("Deal")
    sender = relationship("User")


class AIChatMessage(Base):
    __tablename__ = "ai_chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False, index=True)  # user/assistant
    content = Column(Text, nullable=False)
    route_path = Column(String(255), nullable=True, index=True)
    page_title = Column(String(200), nullable=True)
    context_json = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.now(), index=True)

    user = relationship("User", back_populates="ai_chat_messages")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), nullable=False) # e.g., "deal_new", "payment", "sign", "review"
    is_read = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)

    user = relationship("User")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(80), nullable=False, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    target_type = Column(String(80), nullable=True, index=True)
    target_id = Column(Integer, nullable=True, index=True)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(300), nullable=True)
    event_meta = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.now(), index=True)

    actor = relationship("User")


class BillingEvent(Base):
    __tablename__ = "billing_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    from_plan = Column(String(30), nullable=True)
    to_plan = Column(String(30), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False, default=0)
    currency = Column(String(10), nullable=False, default="INR")
    status = Column(String(30), nullable=False, default="simulated")
    note = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)

    user = relationship("User")


class KYCSubmission(Base):
    __tablename__ = "kyc_submissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    document_type = Column(String(50), nullable=False, index=True)
    document_number_masked = Column(String(50), nullable=False)
    document_url = Column(String(500), nullable=True)

    status = Column(String(20), default="pending", nullable=False, index=True)  # pending/approved/rejected
    risk_score = Column(Integer, default=0, nullable=False)
    risk_flags = Column(JSON, default=list)
    review_note = Column(Text, nullable=True)

    submitted_at = Column(DateTime, server_default=func.now(), index=True)
    reviewed_at = Column(DateTime, nullable=True, index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", foreign_keys=[user_id], back_populates="kyc_submissions")
    reviewer = relationship("User", foreign_keys=[reviewer_id])


class DealTemplate(Base):
    __tablename__ = "deal_templates"

    id = Column(Integer, primary_key=True, index=True)
    owner_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    description = Column(Text, nullable=True)
    deal_type = Column(String(50), nullable=False, index=True)
    terms_json = Column(JSON, default=dict)
    is_default = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    owner = relationship("User")


class DealApproval(Base):
    __tablename__ = "deal_approvals"

    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, index=True)
    requested_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    approver_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    approver_role = Column(String(20), nullable=False, index=True)  # owner/manager/finance/viewer
    status = Column(String(20), nullable=False, default="pending", index=True)  # pending/approved/rejected
    note = Column(Text, nullable=True)
    decided_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)

    deal = relationship("Deal")
    requested_by = relationship("User", foreign_keys=[requested_by_user_id])
    approver = relationship("User", foreign_keys=[approver_user_id])


class NegotiationEntry(Base):
    __tablename__ = "negotiation_entries"

    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    change_type = Column(String(40), nullable=False, default="comment", index=True)  # comment/counter_offer/term_update
    message = Column(Text, nullable=True)
    payload = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.now(), index=True)

    deal = relationship("Deal")
    actor = relationship("User")


class DealMilestone(Base):
    __tablename__ = "deal_milestones"

    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, index=True)
    sequence_no = Column(Integer, nullable=False, default=1)
    title = Column(String(160), nullable=False)
    description = Column(Text, nullable=True)
    amount = Column(Numeric(12, 2), nullable=False, default=0)
    due_date = Column(Date, nullable=True, index=True)
    status = Column(String(30), nullable=False, default="planned", index=True)  # planned/funded/released/disputed
    funded_at = Column(DateTime, nullable=True)
    released_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    deal = relationship("Deal")

    __table_args__ = (
        UniqueConstraint("deal_id", "sequence_no", name="uix_milestone_sequence"),
    )


class DealDispute(Base):
    __tablename__ = "deal_disputes"

    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, index=True)
    opened_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    reason = Column(String(200), nullable=False)
    details = Column(Text, nullable=True)
    status = Column(String(30), nullable=False, default="open", index=True)  # open/under_review/resolved/rejected
    resolution_note = Column(Text, nullable=True)
    settlement_amount = Column(Numeric(12, 2), nullable=True)
    opened_at = Column(DateTime, server_default=func.now(), index=True)
    resolved_at = Column(DateTime, nullable=True, index=True)

    deal = relationship("Deal")
    opened_by = relationship("User")


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    owner_user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    owner = relationship("User", foreign_keys=[owner_user_id])
    members = relationship("WorkspaceMember", back_populates="workspace", cascade="all, delete-orphan")


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False, default="viewer", index=True)  # owner/manager/finance/viewer
    status = Column(String(20), nullable=False, default="active", index=True)  # invited/active/removed
    invited_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)

    workspace = relationship("Workspace", back_populates="members")
    user = relationship("User", foreign_keys=[user_id])
    invited_by = relationship("User", foreign_keys=[invited_by_user_id])

    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uix_workspace_member"),
    )


class WorkspaceResource(Base):
    __tablename__ = "workspace_resources"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_type = Column(String(40), nullable=False, index=True)  # event/campaign/deal/template/report
    resource_id = Column(Integer, nullable=False, index=True)
    added_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)

    workspace = relationship("Workspace")
    added_by = relationship("User")

    __table_args__ = (
        UniqueConstraint("workspace_id", "resource_type", "resource_id", name="uix_workspace_resource"),
    )


class LifecycleNudge(Base):
    __tablename__ = "lifecycle_nudges"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    nudge_type = Column(String(60), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    state = Column(String(20), nullable=False, default="pending", index=True)  # pending/sent/dismissed/done
    due_at = Column(DateTime, nullable=True, index=True)
    payload = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User")


class ReportSnapshot(Base):
    __tablename__ = "report_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    report_type = Column(String(40), nullable=False, index=True)  # roi/campaign_outcome/monthly_exec
    period_key = Column(String(40), nullable=False, index=True)
    data_json = Column(JSON, default=dict)
    exported_format = Column(String(20), nullable=True)
    generated_at = Column(DateTime, server_default=func.now(), index=True)

    user = relationship("User")


class IntegrationConnection(Base):
    __tablename__ = "integration_connections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(40), nullable=False, index=True)  # hubspot/sheets/slack/email/calendar
    status = Column(String(20), nullable=False, default="connected", index=True)
    config_json = Column(JSON, default=dict)
    last_sync_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User")

    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uix_user_provider_integration"),
    )


class IntegrationEvent(Base):
    __tablename__ = "integration_events"

    id = Column(Integer, primary_key=True, index=True)
    connection_id = Column(Integer, ForeignKey("integration_connections.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(80), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="success", index=True)
    request_payload = Column(JSON, default=dict)
    response_payload = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.now(), index=True)

    connection = relationship("IntegrationConnection")
