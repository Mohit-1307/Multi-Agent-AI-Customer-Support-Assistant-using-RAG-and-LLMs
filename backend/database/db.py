"""
TechMart AI Support — Database Models (SQLAlchemy + SQLite)

This file defines every database table used by the app, as
SQLAlchemy ORM classes, plus small helper functions to create
the tables and hand out database sessions.
"""

import uuid
from datetime import datetime
from sqlalchemy import (Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, create_engine)
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import Session, relationship, sessionmaker
from ..config import settings


# ------------------------------------------------------------------
# Engine & Session setup
# ------------------------------------------------------------------
if settings.DATABASE_URL.startswith("sqlite"):

    # SQLite needs this extra flag so the same connection can be used
    # across different threads (FastAPI handles requests concurrently)
    engine = create_engine(settings.DATABASE_URL, connect_args = {"check_same_thread": False})

else:

    # Any other database (Postgres, MySQL, etc.) — pool_pre_ping checks
    # that a connection is still alive before using it, avoiding stale-connection errors
    engine = create_engine(settings.DATABASE_URL, pool_pre_ping = True)

# Factory that creates new database session objects on demand
SessionLocal = sessionmaker(autocommit = False, autoflush = False, bind = engine)

# Base class that all ORM model classes below inherit from
Base = declarative_base()


# ------------------------------------------------------------------
# ORM Models — each class below maps to one database table
# ------------------------------------------------------------------
class User(Base):
    
    "A registered user account."

    __tablename__ = "users"

    # Primary key, auto-generated as a random UUID string
    id = Column(String, primary_key = True, default = lambda: str(uuid.uuid4()))

    # Email must be unique and is indexed for fast lookups on login
    email = Column(String, unique = True, index = True, nullable = False)

    name = Column(String, nullable = False)

    # Stores a hashed password, never the plain-text password
    password_hash = Column(String, nullable = False)

    phone = Column(String, nullable = True)  # for WhatsApp notifications

    is_admin = Column(Boolean, default = False)

    created_at = Column(DateTime, default = datetime.utcnow)

    # One user can have many chat sessions; deleting a user deletes their sessions too
    sessions = relationship("ChatSession", back_populates = "user", cascade = "all, delete-orphan")

    feedback = relationship("Feedback", back_populates = "user")


class ChatSession(Base):
    
    "A single conversation thread between a user and the assistant."

    __tablename__ = "chat_sessions"

    id = Column(String, primary_key = True, default = lambda: str(uuid.uuid4()))

    user_id = Column(String, ForeignKey("users.id"), nullable = False)

    title = Column(String, default = "New Conversation")

    # Optional short summary of the conversation, useful for the sidebar list
    summary = Column(Text, nullable = True)

    created_at = Column(DateTime, default = datetime.utcnow)

    updated_at = Column(DateTime, default = datetime.utcnow)

    is_active = Column(Boolean, default = True)

    # Soft-delete flag — the row stays in the DB but is hidden from the user
    is_deleted = Column(Boolean, default = False)

    user = relationship("User", back_populates = "sessions")

    # Messages are always returned ordered by timestamp (oldest first)
    messages = relationship(

        "Message",

        back_populates = "session",

        order_by = "Message.timestamp",

        cascade = "all, delete-orphan"

    )

    feedback = relationship("Feedback", back_populates = "session")


class Message(Base):
    
    "A single message inside a chat session — either from the user or the assistant."

    __tablename__ = "messages"

    id = Column(String, primary_key = True, default = lambda: str(uuid.uuid4()))

    session_id = Column(String, ForeignKey("chat_sessions.id"), nullable = False)

    role = Column(String, nullable = False)  # "user" | "assistant"

    content = Column(Text, nullable = False)

    agent = Column(String, default = "general")  # which agent responded

    intent = Column(String, default = "general")  # detected intent

    # Overall sentiment label assigned to this message
    sentiment = Column(String, default = "neutral")  # positive|neutral|negative|frustrated

    sentiment_score = Column(Float, default = 0.0)  # -1.0 to 1.0

    response_time_ms = Column(Float, default = 0.0)

    context_used = Column(Boolean, default = False)  # whether RAG context was retrieved

    timestamp = Column(DateTime, default = datetime.utcnow)

    session = relationship("ChatSession", back_populates = "messages")


class Feedback(Base):
    
    "User-submitted rating/comment for a chat session or specific message."

    __tablename__ = "feedback"

    id = Column(String, primary_key = True, default = lambda: str(uuid.uuid4()))

    session_id = Column(String, ForeignKey("chat_sessions.id"), nullable = False)

    user_id = Column(String, ForeignKey("users.id"), nullable = False)

    # Optional — feedback can be tied to one specific message, or the session as a whole
    message_id = Column(String, ForeignKey("messages.id"), nullable = True)

    rating = Column(Integer, nullable = False)  # 1–5

    comment = Column(Text, nullable = True)

    created_at = Column(DateTime, default = datetime.utcnow)

    session = relationship("ChatSession", back_populates = "feedback")

    user = relationship("User", back_populates = "feedback")


class KnowledgeBaseDoc(Base):
    
    "Tracks which documents are loaded into the vector store."

    __tablename__ = "kb_documents"

    id = Column(String, primary_key = True, default = lambda: str(uuid.uuid4()))

    filename = Column(String, nullable = False, unique = True)

    # How many text chunks this document was split into for embedding
    chunk_count = Column(Integer, default = 0)

    indexed_at = Column(DateTime, default = datetime.utcnow)

    file_size_bytes = Column(Integer, default = 0)


class SupportTicket(Base):
    
    "An escalated support ticket, created when an issue needs human follow-up."

    __tablename__ = "support_tickets"

    id = Column(String, primary_key = True, default = lambda: str(uuid.uuid4()))

    user_id = Column(String, ForeignKey("users.id"), nullable = False)

    session_id = Column(String, ForeignKey("chat_sessions.id"), nullable = False)

    # Human-friendly ticket number shown to the customer (e.g. "TM-2024-0001")
    ticket_number = Column(String, unique = True)

    subject = Column(String, nullable = False)

    status = Column(String, default = "open")

    priority = Column(String, default = "medium")

    agent = Column(String, default = "general")

    created_at = Column(DateTime, default = datetime.utcnow)

    updated_at = Column(DateTime, default = datetime.utcnow)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def create_tables() -> None:
    
    """
    Create every table defined above, if it doesn't already exist.
    Safe to call every time the app starts — existing tables are left untouched.
    """

    Base.metadata.create_all(bind = engine)


def get_db():
    
    "FastAPI dependency — yields a DB session and ensures it's closed afterwards, even if the request raises an error."

    db: Session = SessionLocal()

    try:

        yield db

    finally:

        # Always close the session to release the connection back to the pool
        db.close()