"""
TechMart AI Support — Pydantic Schemas (request/response models)

These classes define the shape of every JSON payload the API sends
and receives. FastAPI uses them to validate incoming requests and
to automatically generate the /docs API documentation.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field

# ------------------------------------------------------------------
# Auth
# ------------------------------------------------------------------
class RegisterRequest(BaseModel):
    
    "Payload sent when a new user signs up."

    name: str = Field(..., min_length = 2, max_length = 80)

    email: EmailStr

    password: str = Field(..., min_length = 6)

    phone: Optional[str] = Field(

        None, description = "Phone with country code e.g. +919876543210"

    )


class LoginRequest(BaseModel):
    
    "Payload sent when a user logs in."

    email: EmailStr

    password: str


class TokenResponse(BaseModel):
    
    "Returned after a successful login/registration — contains the JWT token."

    access_token: str

    token_type: str = "bearer"

    user: "UserOut"


class UserOut(BaseModel):
    
    "Public-facing representation of a user (never includes the password hash)."

    id: str

    name: str

    email: str

    phone: Optional[str] = None

    is_admin: bool

    created_at: datetime

    class Config:

        # Allows this schema to be built directly from a SQLAlchemy ORM object
        from_attributes = True


# ------------------------------------------------------------------
# Chat
# ------------------------------------------------------------------
class ChatRequest(BaseModel):
    
    "Payload sent when the user sends a chat message."

    message: str = Field(..., min_length = 1, max_length = 2000)

    session_id: Optional[str] = None  # None means: create a new session


class AgentInfo(BaseModel):
    
    "Small summary of which agent handled a message and how."

    name: str

    intent: str

    confidence: float

    sentiment: str


class ChatResponse(BaseModel):
    
    "Returned after the assistant generates a reply to a chat message."

    session_id: str

    message_id: str

    response: str

    agent: str

    intent: str

    sentiment: str

    sentiment_score: float

    response_time_ms: float

    context_retrieved: bool

    timestamp: datetime


# ------------------------------------------------------------------
# Session / History
# ------------------------------------------------------------------
class MessageOut(BaseModel):
    
    "A single message as returned to the frontend (part of session history)."

    id: str

    role: str

    content: str

    agent: str

    intent: str

    sentiment: str

    timestamp: datetime

    class Config:

        from_attributes = True


class SessionOut(BaseModel):
    
    "Summary view of a chat session, used in the sidebar session list."

    id: str

    title: str

    summary: Optional[str]

    created_at: datetime

    updated_at: datetime

    message_count: int = 0

    class Config:

        from_attributes = True


class SessionDetailOut(BaseModel):
    
    "Full view of a chat session, including all its messages."

    id: str

    title: str

    summary: Optional[str]

    created_at: datetime

    messages: List[MessageOut]

    class Config:

        from_attributes = True


class SummaryResponse(BaseModel):
    
    "Returned when requesting an AI-generated summary of a session."

    session_id: str

    summary: str


# ------------------------------------------------------------------
# Feedback
# ------------------------------------------------------------------
class FeedbackRequest(BaseModel):
    
    "Payload sent when a user rates a response."

    session_id: str

    message_id: Optional[str] = None

    rating: int = Field(..., ge = 1, le = 5)

    comment: Optional[str] = Field(None, max_length = 500)


class FeedbackOut(BaseModel):
    
    "Feedback record as returned to the frontend."

    id: str

    rating: int

    comment: Optional[str]

    created_at: datetime

    class Config:

        from_attributes = True


# ------------------------------------------------------------------
# Analytics
# ------------------------------------------------------------------
class AgentStat(BaseModel):
    
    "How many messages a given agent handled, and what share of the total."

    agent: str

    count: int

    percentage: float


class IntentStat(BaseModel):
    
    "Count of messages classified under a given intent."

    intent: str

    count: int


class SentimentStat(BaseModel):
    
    "Count of messages classified under a given sentiment."

    sentiment: str

    count: int


class AnalyticsResponse(BaseModel):
    
    "Full analytics dashboard payload."

    total_conversations: int

    total_messages: int

    average_rating: float

    avg_response_time_ms: float

    agent_distribution: List[AgentStat]

    intent_distribution: List[IntentStat]

    sentiment_distribution: List[SentimentStat]

    # Each dict here represents one day's conversation count, e.g. {"date": ..., "count": ...}
    daily_conversations: List[dict]


# ------------------------------------------------------------------
# Knowledge Base (admin)
# ------------------------------------------------------------------
class KBDocOut(BaseModel):
    
    "A single knowledge-base document as tracked in the database."

    id: str

    filename: str

    chunk_count: int

    file_size_bytes: int

    indexed_at: datetime

    class Config:

        from_attributes = True


class KBRebuildResponse(BaseModel):
    
    "Returned after triggering a knowledge-base index rebuild."

    message: str

    documents_indexed: int

    total_chunks: int


# ------------------------------------------------------------------
# Generic
# ------------------------------------------------------------------
class SuccessResponse(BaseModel):
    
    "Generic success message, used for simple confirmation endpoints."

    message: str

    detail: Optional[str] = None
