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
    reset_password_token = Column(String(255), nullable=True)
    reset_password_expires_at = Column(DateTime, nullable=True)
    refresh_token = Column(String(255), nullable=True, index=True)

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

