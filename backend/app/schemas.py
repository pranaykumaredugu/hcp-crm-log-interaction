from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel


class HCPOut(BaseModel):
    id: str
    name: str
    specialty: Optional[str] = None
    hospital: Optional[str] = None

    class Config:
        from_attributes = True


class InteractionCreate(BaseModel):
    hcp_name: str
    interaction_type: str = "Meeting"
    attendees: List[str] = []
    topics_discussed: Optional[str] = None
    materials_shared: List[str] = []
    samples_distributed: List[str] = []
    sentiment: str = "neutral"
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None


class InteractionUpdate(BaseModel):
    interaction_type: Optional[str] = None
    attendees: Optional[List[str]] = None
    topics_discussed: Optional[str] = None
    materials_shared: Optional[List[str]] = None
    samples_distributed: Optional[List[str]] = None
    sentiment: Optional[str] = None
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None


class InteractionOut(BaseModel):
    id: str
    hcp_id: str
    hcp_name: str
    interaction_type: str
    interaction_datetime: datetime
    attendees: List[str]
    topics_discussed: Optional[str]
    materials_shared: List[str]
    samples_distributed: List[str]
    sentiment: str
    outcomes: Optional[str]
    follow_up_actions: Optional[str]
    ai_suggested_followups: List[str]

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    message: str
    hcp_name: Optional[str] = None
    interaction_id: Optional[str] = None  # present -> user is editing, absent -> logging new


class ChatResponse(BaseModel):
    reply: str
    tool_used: Optional[str] = None
    interaction: Optional[InteractionOut] = None
