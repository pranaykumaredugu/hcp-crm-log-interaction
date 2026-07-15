import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, DateTime, Text, Enum, ForeignKey, JSON
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class SentimentEnum(str, enum.Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"


class InteractionTypeEnum(str, enum.Enum):
    meeting = "Meeting"
    call = "Call"
    email = "Email"
    conference = "Conference"


class HCP(Base):
    __tablename__ = "hcps"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String, nullable=False, index=True)
    specialty = Column(String, nullable=True)
    hospital = Column(String, nullable=True)

    interactions = relationship("Interaction", back_populates="hcp")


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(String, primary_key=True, default=gen_uuid)
    hcp_id = Column(String, ForeignKey("hcps.id"), nullable=False)
    interaction_type = Column(
    Enum(InteractionTypeEnum, values_callable=lambda obj: [e.value for e in obj]),
    default=InteractionTypeEnum.meeting,
)
    interaction_datetime = Column(DateTime, default=datetime.utcnow)
    attendees = Column(JSON, default=list)          # list[str]
    topics_discussed = Column(Text, nullable=True)
    materials_shared = Column(JSON, default=list)    # list[str]
    samples_distributed = Column(JSON, default=list) # list[str]
    sentiment = Column(
    Enum(SentimentEnum, values_callable=lambda obj: [e.value for e in obj]),
    default=SentimentEnum.neutral,
)
    outcomes = Column(Text, nullable=True)
    follow_up_actions = Column(Text, nullable=True)
    ai_suggested_followups = Column(JSON, default=list)  # list[str]
    raw_source_text = Column(Text, nullable=True)    # original chat/voice text, for audit
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    hcp = relationship("HCP", back_populates="interactions")
