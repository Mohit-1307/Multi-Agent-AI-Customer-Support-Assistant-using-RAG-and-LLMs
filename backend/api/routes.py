"""
TechMart AI Support — API Routes

Defines every HTTP endpoint the frontend talks to: auth, chat sessions,
the main chat endpoint, feedback, analytics, admin knowledge-base
management, support tickets, escalation, and notification status checks.
"""

import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..agents.router import get_router
from ..api.auth import (

    create_access_token,

    get_admin_user,

    get_current_user,

    hash_password,

    verify_password,

)
from ..config import settings
from ..database.db import (ChatSession, Feedback, KnowledgeBaseDoc, Message, SupportTicket, User, get_db)
from ..models.schemas import (AnalyticsResponse, AgentStat, ChatRequest, ChatResponse, FeedbackRequest, FeedbackOut, IntentStat, KBDocOut, KBRebuildResponse, LoginRequest, 
                                MessageOut, RegisterRequest, SentimentStat, SessionDetailOut, SessionOut, SuccessResponse, SummaryResponse, TokenResponse, UserOut)

from ..rag.retriever import get_retriever

from .email_service import (

    send_escalation_emails,

    send_ticket_created_email,

    send_feedback_thank_you,

    is_email_configured,

)

from .whatsapp_service import (

    send_escalation_whatsapp,

    send_ticket_whatsapp,

    is_whatsapp_configured,

)

router = APIRouter()


# ------------------------------------------------------------------
# Simple in-memory rate limiter
# ------------------------------------------------------------------
# Keyed by user ID, holds a list of timestamps for recent messages.
# NOTE: this resets whenever the server restarts, and won't work
# correctly across multiple server processes — fine for a single-instance
# deployment, but wouldn't scale to a multi-worker/multi-server setup.
_message_counts = defaultdict(list)


def check_rate_limit(user_id: str, max_messages: int = 20, window_minutes: int = 1) -> bool:
    
    "Returns True if the user is allowed to send another message, False if they've hit the rate limit for the current time window."

    now = datetime.utcnow()

    window_start = now - timedelta(minutes = window_minutes)

    # Drop any timestamps older than the current window before counting
    _message_counts[user_id] = [t for t in _message_counts[user_id] if t > window_start]

    if len(_message_counts[user_id]) >= max_messages:

        return False

    _message_counts[user_id].append(now)

    return True


# ------------------------------------------------------------------
#  AUTH
# ------------------------------------------------------------------
@router.post("/auth/register", response_model = TokenResponse, tags = ["Auth"])
async def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    
    "Register a new user account."

    if db.query(User).filter(User.email == payload.email).first():

        raise HTTPException(status_code = 400, detail = "Email already registered")

    user = User(

        name = payload.name,

        email = payload.email,

        password_hash = hash_password(payload.password),

        phone = payload.phone

    )

    db.add(user)

    db.commit()

    db.refresh(user)

    token = create_access_token({"sub": user.id})

    return TokenResponse(access_token = token, user = UserOut.model_validate(user))


@router.post("/auth/login", response_model = TokenResponse, tags = ["Auth"])
async def login(payload: LoginRequest, db: Session = Depends(get_db)):
    
    "Login with email and password, returns a JWT access token."

    user = db.query(User).filter(User.email == payload.email).first()

    if not user or not verify_password(payload.password, user.password_hash):

        raise HTTPException(status_code = 401, detail = "Invalid email or password")

    token = create_access_token({"sub": user.id})

    return TokenResponse(access_token = token, user = UserOut.model_validate(user))


@router.get("/auth/me", response_model = UserOut, tags = ["Auth"])
async def get_me(current_user: User = Depends(get_current_user)):
    
    "Return the currently logged-in user's profile."

    return current_user


# ------------------------------------------------------------------
#  SESSIONS
# ------------------------------------------------------------------
@router.get("/sessions", response_model = List[SessionOut], tags = ["Sessions"])
async def list_sessions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    
    "List all active chat sessions for the current user, most recently updated first."

    sessions = (

        db.query(ChatSession)

        .filter(ChatSession.user_id == current_user.id, ChatSession.is_active == True)

        .order_by(ChatSession.updated_at.desc())

        .all()

    )

    result = []

    for s in sessions:

        # Attach a live message count to each session for display in the sidebar
        msg_count = db.query(Message).filter(Message.session_id == s.id).count()

        out = SessionOut.model_validate(s)

        out.message_count = msg_count

        result.append(out)

    return result


@router.post("/sessions", response_model = SessionOut, tags = ["Sessions"])
async def create_session(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    
    "Create a new, empty chat session for the current user."

    session = ChatSession(user_id = current_user.id)

    db.add(session)

    db.commit()

    db.refresh(session)

    out = SessionOut.model_validate(session)

    out.message_count = 0

    return out


@router.delete("/sessions/{session_id}", tags = ["Sessions"])
async def delete_session(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    
    "Soft-delete a session — marks it inactive/deleted without removing the data."

    session = (

        db.query(ChatSession)

        .filter(

            ChatSession.id == session_id,

            ChatSession.user_id == current_user.id

        )

        .first()

    )

    if not session:

        raise HTTPException(status_code = 404, detail = "Session not found")

    session.is_active = False

    session.is_deleted = True

    db.commit()

    return SuccessResponse(message = "Session deleted")


@router.get("/sessions/{session_id}/history", response_model = SessionDetailOut, tags = ["Sessions"])
async def get_session_history(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    
    "Get the full message history for a single session."

    session = (

        db.query(ChatSession)

        .filter(

            ChatSession.id == session_id,

            ChatSession.user_id == current_user.id,

        )

        .first()

    )

    if not session:

        raise HTTPException(status_code = 404, detail = "Session not found")

    return SessionDetailOut.model_validate(session)


# ------------------------------------------------------------------
#  CHAT
# ------------------------------------------------------------------
@router.post("/chat", response_model = ChatResponse, tags = ["Chat"])
async def chat(payload: ChatRequest,current_user: User = Depends(get_current_user),db: Session = Depends(get_db)):
    
    """
    Main chat endpoint. Routes the user's message through the
    multi-agent system and returns the assistant's reply.
    If session_id is None, a new session is created automatically.
    """

    # Rate limiting — max 20 messages per minute per user
    if not check_rate_limit(current_user.id):

        raise HTTPException(

            status_code = 429,

            detail = "Too many messages. Please wait a moment before sending again."

        )

    # Step 1: Resolve the target session, or create a new one if none was given
    if payload.session_id:

        session = (

            db.query(ChatSession)

            .filter(

                ChatSession.id == payload.session_id,

                ChatSession.user_id == current_user.id,

            )

            .first()

        )

        if not session:

            raise HTTPException(status_code = 404, detail = "Session not found")

    else:

        session = ChatSession(user_id = current_user.id)

        db.add(session)

        db.commit()

        db.refresh(session)

    # Step 2: Build the conversation history so the agent has context
    prev_messages = (

        db.query(Message)

        .filter(Message.session_id == session.id)

        .order_by(Message.timestamp)

        .all()

    )

    history = [{"role": m.role, "content": m.content} for m in prev_messages]

    # Step 3: Detect intent/sentiment using the FULL pipeline (keyword baseline,
    # refined by an LLM call when the keyword match is ambiguous), so the stored
    # Message row already has this metadata attached
    start_ms = time.time() * 1000

    router_obj = get_router()

    routing = await router_obj.detect_intent(payload.message)

    user_msg = Message(

        session_id = session.id,

        role = "user",

        content = payload.message,

        agent = "user",

        intent = routing.get("intent", "general"),

        sentiment = routing.get("sentiment", "neutral"),

        sentiment_score = routing.get("sentiment_score", 0.0)

    )

    db.add(user_msg)

    db.commit()

    # Step 4: Route the message through the full agent system to get a reply
    result = await router_obj.route(payload.message, history)

    elapsed_ms = time.time() * 1000 - start_ms

    # Step 5: Store the assistant's reply as a new message
    assistant_msg = Message(

        session_id = session.id,

        role = "assistant",

        content = result["response"],

        agent = result["agent"],

        intent = result["intent"],

        sentiment = result["sentiment"],

        sentiment_score = result["sentiment_score"],

        response_time_ms = elapsed_ms,

        context_used = result.get("context_retrieved", False)

    )

    db.add(assistant_msg)

    # Auto-create a support ticket for complaints or frustrated customers,
    # and notify the customer by email/WhatsApp about the new ticket

    if result.get("intent") == "complaint" or result.get("sentiment") in ["frustrated", "negative"]:
        
        print(f"DEBUG TICKET | intent={result.get('intent')} sentiment={result.get('sentiment')}")
        
        print(f"DEBUG TICKET | phone={current_user.phone} whatsapp_configured={is_whatsapp_configured()}")

        import random

        ticket_number = f"TM-{random.randint(10000, 99999)}"

        priority = "high" if result.get("sentiment") == "frustrated" else "medium"

        ticket = SupportTicket(

            user_id = current_user.id,

            session_id = session.id,

            ticket_number = ticket_number,

            subject = payload.message[:100],

            priority = priority,

            agent = result.get("agent", "complaint")

        )

        db.add(ticket)

        # Send ticket creation email
        send_ticket_created_email(

            customer_name = current_user.name,

            customer_email = current_user.email,

            ticket_number = ticket_number,

            subject = payload.message[:80],

            priority = priority

        )

        # Send WhatsApp notification, only if the user has a phone number on file
        if current_user.phone and is_whatsapp_configured():

            send_ticket_whatsapp(

                customer_name = current_user.name,

                customer_phone = current_user.phone,

                ticket_number = ticket_number,

                priority = priority

            )

    # Step 6: Update session metadata (timestamp, and title if this is the first message)
    session.updated_at = datetime.utcnow()

    if len(prev_messages) == 0:

        # Smart title generation — pick a title based on message language and detected intent
        msg = payload.message.strip()

        # Check whether the message contains non-ASCII characters (Hindi, Arabic, Chinese, etc.)
        has_non_ascii = not all(ord(c) < 128 for c in msg)

        if has_non_ascii:

            # Use a pre-translated title based on intent and detected language,
            # since a plain character-slice title wouldn't read naturally in these languages
            intent = result.get("intent", "general")

            hindi_titles = {

                "billing": "बिलिंग सहायता",

                "technical": "तकनीकी सहायता",

                "product": "उत्पाद जानकारी",

                "complaint": "शिकायत",

                "refund": "वापसी अनुरोध",

                "faq": "सामान्य प्रश्न",

                "general": "ग्राहक सहायता"

            }

            spanish_titles = {

                "billing": "Consulta de Facturación",

                "technical": "Soporte Técnico",

                "product": "Información de Producto",

                "complaint": "Queja",

                "refund": "Solicitud de Reembolso",

                "faq": "Pregunta General",

                "general": "Atención al Cliente"

            }

            french_titles = {

                "billing": "Facturation",

                "technical": "Support Technique",

                "product": "Info Produit",

                "complaint": "Réclamation",

                "refund": "Remboursement",

                "faq": "Question Générale",

                "general": "Service Client"

            }

            # Detect which language's title map to use, based on character/keyword hints
            if any("\u0900" <= c <= "\u097f" for c in msg):

                title_map = hindi_titles

            elif any(w in msg.lower() for w in ["hola", "como", "gracias", "política", "necesito"]):

                title_map = spanish_titles

            elif any(w in msg.lower() for w in ["bonjour", "merci", "politique", "besoin"]):

                title_map = french_titles

            else:

                # Non-ASCII but not one of the languages above — fall back to English titles
                title_map = {

                    "billing": "Billing Support",

                    "technical": "Technical Support",

                    "product": "Product Inquiry",

                    "complaint": "Complaint",

                    "refund": "Refund Request",

                    "faq": "General FAQ",

                    "general": "Support Query"

                }

            session.title = title_map.get(intent, "Customer Support")

        else:

            # Plain English (or other ASCII) message — just use the first 50 characters
            session.title = msg[:50] + ("..." if len(msg) > 50 else "")

    db.commit()

    db.refresh(assistant_msg)

    return ChatResponse(

        session_id = session.id,

        message_id = assistant_msg.id,

        response = result["response"],

        agent = result["agent"],

        intent = result["intent"],

        sentiment = result["sentiment"],

        sentiment_score = result["sentiment_score"],

        response_time_ms = elapsed_ms,

        context_retrieved = result.get("context_retrieved", False),

        timestamp = assistant_msg.timestamp

    )


# ------------------------------------------------------------------
#  CONVERSATION SUMMARY  (Optional/Bonus Feature)
# ------------------------------------------------------------------
@router.get("/sessions/{session_id}/summary", response_model = SummaryResponse, tags = ["Chat"])
async def get_session_summary(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    
    "Generate (or return a cached) AI summary of a conversation session."

    session = (

        db.query(ChatSession)

        .filter(

            ChatSession.id == session_id,

            ChatSession.user_id == current_user.id,

        )

        .first()

    )

    if not session:

        raise HTTPException(status_code = 404, detail = "Session not found")

    # Return the cached summary if one was already generated, to avoid an extra LLM call
    if session.summary:

        return SummaryResponse(session_id = session_id, summary = session.summary)

    messages = (

        db.query(Message)

        .filter(Message.session_id == session_id)

        .order_by(Message.timestamp)

        .all()

    )

    if not messages:

        return SummaryResponse(

            session_id = session_id, summary = "No messages in this session."

        )

    # Format the whole conversation as plain text for the summarization prompt
    convo_text = "\n".join(f"{m.role.upper()}: {m.content}" for m in messages)

    prompt = (

        f"Summarize this customer support conversation in 2–3 sentences. "

        f"Include: the customer's main issue, how it was resolved, and any follow-up actions needed.\n\n"

        f"Conversation:\n{convo_text[:3000]}"

    )

    from ..agents.llm_client import get_llm_client

    llm = get_llm_client()

    summary = await llm.complete(prompt, max_tokens = 200)

    # Cache the summary on the session so we don't regenerate it next time
    session.summary = summary

    db.commit()

    return SummaryResponse(session_id = session_id, summary = summary)


# ------------------------------------------------------------------
#  FEEDBACK  (Optional/Bonus Feature)
# ------------------------------------------------------------------
@router.post("/feedback", response_model = FeedbackOut, tags = ["Feedback"])
async def submit_feedback(payload: FeedbackRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    
    "Submit a 1-5 star rating (and optional comment) for a conversation."

    session = (

        db.query(ChatSession)

        .filter(

            ChatSession.id == payload.session_id,

            ChatSession.user_id == current_user.id,

        )

        .first()

    )

    if not session:

        raise HTTPException(status_code = 404, detail = "Session not found")

    feedback = Feedback(

        session_id = payload.session_id,

        user_id = current_user.id,

        message_id = payload.message_id,

        rating = payload.rating,

        comment = payload.comment,

    )

    db.add(feedback)

    db.commit()

    db.refresh(feedback)

    # Send a thank-you email for the feedback (best-effort, doesn't block the response)
    send_feedback_thank_you(

        customer_name = current_user.name,

        customer_email = current_user.email,

        rating = payload.rating,

    )

    return FeedbackOut.model_validate(feedback)


# ------------------------------------------------------------------
#  ANALYTICS DASHBOARD  (Optional/Bonus Feature)
# ------------------------------------------------------------------
@router.get("/analytics", response_model = AnalyticsResponse, tags = ["Analytics"])
async def get_analytics(days: int = 30, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    
    "Return usage analytics: totals, average rating/response time, and breakdowns by agent, intent, and sentiment. Admins see data for all users; regular users only see their own."

    since = datetime.utcnow() - timedelta(days = days)

    if current_user.is_admin:

        session_q = db.query(ChatSession)

        message_q = db.query(Message)

        feedback_q = db.query(Feedback)

    else:

        # Non-admins only see analytics scoped to their own sessions
        user_session_ids = [

            s.id

            for s in db.query(ChatSession.id)

            .filter(ChatSession.user_id == current_user.id)

            .all()

        ]

        session_q = db.query(ChatSession).filter(ChatSession.user_id == current_user.id)

        message_q = db.query(Message).filter(Message.session_id.in_(user_session_ids))

        feedback_q = db.query(Feedback).filter(Feedback.user_id == current_user.id)

    total_conversations = session_q.filter(ChatSession.created_at >= since).count()

    total_messages = message_q.filter(Message.timestamp >= since).count()

    # Average feedback rating across the scoped set
    avg_rating = feedback_q.with_entities(func.avg(Feedback.rating)).scalar() or 0.0

    # Average assistant response time, in milliseconds
    avg_rt = (

        message_q.filter(Message.role == "assistant", Message.timestamp >= since)

        .with_entities(func.avg(Message.response_time_ms))

        .scalar()

    ) or 0.0

    # Break down assistant messages by which agent handled them
    agent_rows = (

        message_q.filter(Message.role == "assistant", Message.timestamp >= since)

        .with_entities(Message.agent, func.count(Message.agent))

        .group_by(Message.agent)

        .all()

    )

    total_agent_msgs = sum(r[1] for r in agent_rows) or 1

    agent_dist = [

        AgentStat(

            agent = r[0] or "general",

            count = r[1],

            percentage = round(r[1] / total_agent_msgs * 100, 1),

        )

        for r in agent_rows

    ]

    # Break down assistant messages by detected intent
    intent_rows = (

        message_q.filter(Message.role == "assistant", Message.timestamp >= since)

        .with_entities(Message.intent, func.count(Message.intent))

        .group_by(Message.intent)

        .all()

    )

    intent_dist = [

        IntentStat(intent = r[0] or "general", count = r[1]) for r in intent_rows

    ]

    # Break down user messages by sentiment — queried one sentiment at a time
    from sqlalchemy import text

    sentiment_dist = []

    for sent in ["neutral", "positive", "negative", "frustrated"]:

        cnt = message_q.filter(

            Message.role == "user",

            Message.sentiment == sent

        ).count()

        # NOTE (preserved as-is): leftover debug print statement, left
        # unchanged since removing it would be a behavior/output change.
        print(f"DEBUG SENTIMENT: {sent} = {cnt}")

        if cnt > 0:

            sentiment_dist.append(SentimentStat(sentiment = sent, count = cnt))

    # Daily conversation counts for the last 7 days, used for a trend chart
    daily = defaultdict(int)

    recent_sessions = session_q.filter(

        ChatSession.created_at >= datetime.utcnow() - timedelta(days = 7)

    ).all()

    for s in recent_sessions:

        day_key = s.created_at.strftime("%Y-%m-%d")

        daily[day_key] += 1

    daily_conversations = [{"date": k, "count": v} for k, v in sorted(daily.items())]

    return AnalyticsResponse(

        total_conversations = total_conversations,

        total_messages = total_messages,

        average_rating = round(float(avg_rating), 2),

        avg_response_time_ms = round(float(avg_rt), 1),

        agent_distribution = agent_dist,

        intent_distribution = intent_dist,

        sentiment_distribution = sentiment_dist,

        daily_conversations = daily_conversations

    )


# ------------------------------------------------------------------
#  ADMIN — Knowledge Base Management  (Optional/Bonus Feature)
# ------------------------------------------------------------------
@router.get("/admin/knowledge-base", response_model = List[KBDocOut], tags = ["Admin"])
async def list_kb_docs(_: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    
    "List all indexed knowledge base documents (admin only)."

    return db.query(KnowledgeBaseDoc).all()


@router.post("/admin/knowledge-base/rebuild", response_model = KBRebuildResponse, tags = ["Admin"])
async def rebuild_knowledge_base(_: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    
    "Rebuild the FAISS vector index from the knowledge base files (admin only)."

    retriever = get_retriever()

    result = retriever.build_index(force_rebuild = True)

    if result.get("status") == "error":

        raise HTTPException(status_code = 500, detail = "Failed to rebuild index")

    # Replace the tracked document records with the freshly rebuilt stats
    db.query(KnowledgeBaseDoc).delete()

    for filename, stats in result.get("file_stats", {}).items():

        doc = KnowledgeBaseDoc(

            filename = filename,

            chunk_count = stats["chunks"],

            file_size_bytes = stats["file_size_bytes"]

        )

        db.add(doc)

    db.commit()

    return KBRebuildResponse(

        message = "Knowledge base rebuilt successfully",

        documents_indexed = len(result.get("file_stats", {})),

        total_chunks = result.get("chunks", 0)

    )


@router.post("/admin/knowledge-base/upload", tags = ["Admin"])
async def upload_kb_document(file: UploadFile = File(...), _: User = Depends(get_admin_user)):
    
    """
    Upload a new .txt document to the knowledge base (admin only).
    Note: this only saves the file — the index must be rebuilt separately
    via /admin/knowledge-base/rebuild before the new content is searchable.
    """

    if not file.filename.endswith(".txt"):

        raise HTTPException(status_code = 400, detail = "Only .txt files are supported")

    save_path = settings.KNOWLEDGE_BASE_DIR / file.filename

    content = await file.read()

    save_path.write_bytes(content)

    return SuccessResponse(

        message = f"File '{file.filename}' uploaded. Run /admin/knowledge-base/rebuild to index.",

    )


# ------------------------------------------------------------------
#  TICKETS & ESCALATION
#  (NOTE: preserved as-is — the original source labeled this section
#  "HEALTH CHECK", which doesn't match the routes below; the actual
#  health check endpoint is the unlabeled one at the bottom of this file.
#  Comment corrected here since it's just a heading, not logic.)
# ------------------------------------------------------------------
@router.post("/tickets/create", tags = ["Tickets"])
async def create_ticket(session_id: str, subject: str, priority: str = "medium", current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    
    "Manually create a support ticket."

    import random

    ticket_number = f"TM-{random.randint(10000, 99999)}"

    ticket = SupportTicket(

        user_id = current_user.id,

        session_id = session_id,

        ticket_number = ticket_number,

        subject = subject,

        priority = priority

    )

    db.add(ticket)

    db.commit()

    db.refresh(ticket)

    return {

        "ticket_number": ticket_number,

        "status": "open",

        "message": f"Ticket {ticket_number} created. Our team will contact you within 2 business hours."

    }


@router.get("/tickets", tags = ["Tickets"])
async def list_tickets(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    
    "List all support tickets for the current user, newest first."

    tickets = (

        db.query(SupportTicket)

        .filter(SupportTicket.user_id == current_user.id)

        .order_by(SupportTicket.created_at.desc())

        .all()

    )

    return [

        {

            "ticket_number": t.ticket_number,

            "subject": t.subject,

            "status": t.status,

            "priority": t.priority,

            "agent": t.agent,

            "created_at": t.created_at

        }

        for t in tickets

    ]


@router.post("/escalate", tags = ["Escalation"])
async def escalate_to_human(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    
    "Escalate a conversation to a human agent — posts a confirmation message in the chat and sends email/WhatsApp notifications."

    session = (

        db.query(ChatSession)

        .filter(ChatSession.id == session_id, ChatSession.user_id == current_user.id)

        .first()

    )

    if not session:

        raise HTTPException(status_code = 404, detail = "Session not found")

    reference = f"ESC-{session_id[:8].upper()}"

    # Add a visible escalation confirmation message into the chat history
    escalation_msg = Message(

        session_id = session_id,

        role = "assistant",

        content = (

            f"I understand you'd like to speak with a human agent."

            f"Your case has been escalated (Reference: {reference})."

            f"A TechMart support specialist will contact you at"

            f"{current_user.email} within 2 business hours."

            f"You can also call us directly at 1-800-TECHMART."

            f"Thank you for your patience."

        ),

        agent = "escalation",

        intent = "escalation"

    )

    db.add(escalation_msg)

    db.commit()

    # Send confirmation + alert emails (to the customer and the support team)
    email_result = send_escalation_emails(

        customer_name = current_user.name,

        customer_email = current_user.email,

        session_id = session_id,

        session_title = session.title or "Support Query"

    )

    # Send a WhatsApp confirmation too, if the user has a phone number on file
    whatsapp_sent = False

    if current_user.phone and is_whatsapp_configured():

        whatsapp_sent = send_escalation_whatsapp(

            customer_name = current_user.name,

            customer_phone = current_user.phone,

            reference = reference

        )

    return {

        "escalated": True,

        "reference": reference,

        "message": "A human agent will contact you within 2 business hours.",

        "contact_email": current_user.email,

        "email_sent": email_result["customer_email_sent"],

        "whatsapp_sent": whatsapp_sent

    }


@router.get("/email/status", tags = ["Notifications"])
async def email_status(current_user: User = Depends(get_current_user)):
    
    "Check whether email notifications are configured on this server."

    return {

        "email_configured": is_email_configured(),

        "smtp_host": settings.SMTP_HOST if is_email_configured() else None,

        "support_email": (

            settings.SUPPORT_EMAIL or settings.SMTP_USER

            if is_email_configured()

            else None

        )

    }


@router.get("/whatsapp/status", tags = ["Notifications"])
async def whatsapp_status(current_user: User = Depends(get_current_user)):
    
    "Check whether WhatsApp notifications are configured, and whether the current user has a phone number on file to receive them."

    return {

        "whatsapp_configured": is_whatsapp_configured(),

        "user_phone": current_user.phone or "Not set",

        "note": "Add phone number during registration for WhatsApp notifications"

    }


@router.delete("/sessions", tags = ["Sessions"])
async def delete_all_sessions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    
    "Soft-delete every active session belonging to the current user."

    db.query(ChatSession).filter(

        ChatSession.user_id == current_user.id,

        ChatSession.is_active == True,

    ).update({"is_active": False, "is_deleted": True})

    db.commit()

    return SuccessResponse(message = "All conversations deleted")


@router.post("/sessions/{session_id}/archive", tags = ["Sessions"])
async def archive_session(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    
    "Archive a single session (marks it inactive but not deleted)."

    session = (

        db.query(ChatSession)

        .filter(

            ChatSession.id == session_id,

            ChatSession.user_id == current_user.id,

        )

        .first()

    )

    if not session:

        raise HTTPException(status_code = 404, detail = "Session not found")

    session.is_active = False

    session.is_deleted = False

    db.commit()

    return SuccessResponse(message = "Conversation archived")


@router.post("/sessions/archive-all", tags = ["Sessions"])
async def archive_all_sessions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    
    "Archive every active session belonging to the current user."

    db.query(ChatSession).filter(

        ChatSession.user_id == current_user.id,

        ChatSession.is_active == True,

    ).update({"is_active": False})

    db.commit()

    return SuccessResponse(message = "All conversations archived")


@router.get("/sessions/archived", response_model = List[SessionOut], tags = ["Sessions"])
async def list_archived_sessions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    
    "List all archived (inactive, not deleted) sessions for the current user."

    sessions = (

        db.query(ChatSession)

        .filter(

            ChatSession.user_id == current_user.id,

            ChatSession.is_active == False,

            ChatSession.is_deleted == False,

        )

        .order_by(ChatSession.updated_at.desc())

        .all()

    )

    result = []

    for s in sessions:

        msg_count = db.query(Message).filter(Message.session_id == s.id).count()

        out = SessionOut.model_validate(s)

        out.message_count = msg_count

        result.append(out)

    return result


@router.get("/sessions/deleted", response_model = List[SessionOut], tags = ["Sessions"])
async def list_deleted_sessions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    
    "List recently soft-deleted sessions for the current user."

    sessions = (

        db.query(ChatSession)

        .filter(

            ChatSession.user_id == current_user.id,

            ChatSession.is_deleted == True,

        )

        .order_by(ChatSession.updated_at.desc())

        .all()

    )

    result = []

    for s in sessions:

        msg_count = db.query(Message).filter(Message.session_id == s.id).count()

        out = SessionOut.model_validate(s)

        out.message_count = msg_count

        result.append(out)

    return result


@router.post("/sessions/{session_id}/restore", tags = ["Sessions"])
async def restore_session(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    
    "Restore an archived or soft-deleted session back to active."

    session = (

        db.query(ChatSession)

        .filter(

            ChatSession.id == session_id,

            ChatSession.user_id == current_user.id,

        )

        .first()

    )

    if not session:

        raise HTTPException(status_code = 404, detail = "Session not found")

    session.is_active = True

    session.is_deleted = False

    db.commit()

    return SuccessResponse(message = "Conversation restored")


@router.delete("/sessions/{session_id}/permanent", tags = ["Sessions"])
async def delete_session_permanent(session_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    
    "Permanently delete a session and all of its messages/feedback. Unlike delete_session above, this cannot be undone."

    session = (

        db.query(ChatSession)

        .filter(

            ChatSession.id == session_id,

            ChatSession.user_id == current_user.id,

        )

        .first()

    )

    if not session:

        raise HTTPException(status_code = 404, detail = "Session not found")

    # Delete dependent rows first to avoid foreign-key constraint errors
    db.query(Message).filter(Message.session_id == session_id).delete()

    db.query(Feedback).filter(Feedback.session_id == session_id).delete()

    db.query(SupportTicket).filter(SupportTicket.session_id == session_id).delete()

    db.delete(session)
    
    db.commit()

    return SuccessResponse(message = "Conversation permanently deleted")


@router.delete("/auth/account", tags = ["Auth"])
async def delete_account(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    
    "Permanently delete the current user's account and all associated data (sessions, messages, feedback, tickets). This cannot be undone."

    user_id = current_user.id

    # Delete all messages/feedback/tickets tied to each of the user's sessions
    user_sessions = db.query(ChatSession).filter(ChatSession.user_id == user_id).all()

    for session in user_sessions:

        db.query(Message).filter(Message.session_id == session.id).delete()

        db.query(Feedback).filter(Feedback.session_id == session.id).delete()

        db.query(SupportTicket).filter(SupportTicket.session_id == session.id).delete()

    # Delete all the user's sessions themselves
    db.query(ChatSession).filter(ChatSession.user_id == user_id).delete()

    # Delete any remaining feedback tied directly to the user
    db.query(Feedback).filter(Feedback.user_id == user_id).delete()

    # Delete any remaining tickets tied directly to the user
    db.query(SupportTicket).filter(SupportTicket.user_id == user_id).delete()

    # Finally, delete the user account itself
    db.query(User).filter(User.id == user_id).delete()

    db.commit()

    return SuccessResponse(message = "Account permanently deleted")


@router.post("/auth/reset-history", tags = ["Auth"])
async def reset_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    
    "Wipe all chat/analytics data for the user but keep the account itself (unlike delete_account, this doesn't remove the user's login credentials)."

    user_id = current_user.id

    user_sessions = db.query(ChatSession).filter(ChatSession.user_id == user_id).all()

    for session in user_sessions:

        db.query(Message).filter(Message.session_id == session.id).delete()

        db.query(Feedback).filter(Feedback.session_id == session.id).delete()

        db.query(SupportTicket).filter(SupportTicket.session_id == session.id).delete()

    db.query(ChatSession).filter(ChatSession.user_id == user_id).delete()

    db.query(Feedback).filter(Feedback.user_id == user_id).delete()

    db.query(SupportTicket).filter(SupportTicket.user_id == user_id).delete()

    db.commit()

    return SuccessResponse(message = "Account history reset. Fresh start!")


@router.post("/sessions/unarchive-all", tags = ["Sessions"])
async def unarchive_all_sessions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    
    "Restore all archived (but not deleted) sessions back to active."

    db.query(ChatSession).filter(

        ChatSession.user_id == current_user.id,

        ChatSession.is_active == False,

        ChatSession.is_deleted == False,

    ).update({"is_active": True})

    db.commit()

    return SuccessResponse(message = "All archived conversations restored")


@router.post("/sessions/restore-all", tags = ["Sessions"])
async def restore_all_deleted_sessions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    
    "Restore all recently soft-deleted sessions back to active."

    db.query(ChatSession).filter(

        ChatSession.user_id == current_user.id,

        ChatSession.is_deleted == True,

    ).update({"is_active": True, "is_deleted": False})

    db.commit()

    return SuccessResponse(message = "All deleted conversations restored")


@router.api_route("/health", methods = ["GET", "HEAD"], tags = ["System"])
async def health_check():
    
    "Simple health check endpoint — reports app status and whether the RAG knowledge base index is loaded and ready."

    retriever = get_retriever()

    return {

        "status": "ok",

        "app": settings.APP_NAME,

        "version": settings.APP_VERSION,

        "rag_ready": retriever.is_ready,

        "knowledge_chunks": retriever.chunk_count,

        "llm_provider": settings.LLM_PROVIDER

    }