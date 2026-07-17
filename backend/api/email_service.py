"""
TechMart AI Support — Email Service

Sends transactional emails (escalation confirmations, ticket-created
notices, feedback thank-yous) over SMTP. All sending is best-effort:
if SMTP isn't configured or a send fails, functions log the problem
and return False/failure info rather than raising, so email issues
never break the main chat flow.
"""

import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from ..config import settings

logger = logging.getLogger(__name__)


def is_email_configured() -> bool:
    
    """
    Check whether SMTP credentials have been set. 
    Used to skip sending attempts entirely when email isn't set up.
    """

    return bool(settings.SMTP_USER and settings.SMTP_PASSWORD)


def send_email(to_email: str, subject: str, body: str) -> bool:
    
    """
    Send a single plain-text email over SMTP. 
    Returns True on success, False if email isn't configured or the send fails for any reason.
    """

    if not is_email_configured():

        logger.warning("Email not configured — skipping email send")

        return False
    
    print(f"DEBUG EMAIL | Attempting to send to: {to_email}")
    
    print(f"DEBUG EMAIL | SMTP: {settings.SMTP_HOST}:{settings.SMTP_PORT}")
    
    print(f"DEBUG EMAIL | User: {settings.SMTP_USER}")
    
    print(f"DEBUG EMAIL | Password set: {bool(settings.SMTP_PASSWORD)}")
    
    print(f"DEBUG EMAIL | to = {to_email} host = {settings.SMTP_HOST} user = {settings.SMTP_USER} pass_len = {len(settings.SMTP_PASSWORD or '')}")

    try:

        msg = MIMEMultipart()

        msg["From"] = f"TechMart Support <{settings.SMTP_USER}>"

        msg["To"] = to_email

        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain"))

        # starttls() upgrades the plain connection to an encrypted one before login
        with smtplib.SMTP(settings.SMTP_HOST, int(settings.SMTP_PORT)) as server:
            
            server.ehlo()
            
            server.starttls()
            
            server.ehlo()
            
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            
            server.send_message(msg)
            
            print(f"DEBUG EMAIL SUCCESS | Sent to {to_email}")

        logger.info(f"Email sent to {to_email}: {subject}")

        return True

    except smtplib.SMTPAuthenticationError:

        # Specifically catch bad credentials so the log message is clear about the cause
        logger.error("SMTP authentication failed — check SMTP_USER and SMTP_PASSWORD")

        return False

    except Exception as e:

        # Catch-all for network errors, timeouts, etc. — never let email failures crash the caller
        logger.error(f"Email send failed: {e}")

        return False


def send_escalation_emails(customer_name: str, customer_email: str, session_id: str, session_title: str = "Support Query") -> dict:
    
    """
    Send two emails when a customer escalates to a human agent:
    1. A confirmation email to the customer
    2. An alert email to the support team

    Returns a dict summarizing whether each send succeeded.
    """

    # Short, human-readable reference code built from the session ID
    reference = f"ESC-{session_id[:8].upper()}"

    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    # ------------------------------------------------------------------
    # Email 1: Customer Confirmation
    # ------------------------------------------------------------------
    customer_subject = f"[TechMart] Your Case {reference} — Human Agent Requested"

    customer_body = f"""

    Dear {customer_name},

    Thank you for contacting TechMart Electronics.

    Your support request has been successfully escalated to a human agent.

    ----------------------------------------
    CASE DETAILS
    ----------------------------------------
    Reference Number : {reference}

    Case Topic : {session_title}

    Submitted At : {timestamp}
    ----------------------------------------

    WHAT HAPPENS NEXT:
    A TechMart support specialist will contact you at
    {customer_email} within 2 business hours.

    NEED IMMEDIATE HELP?
    📞 Phone : 1-800-TECHMART (1-800-832-4627)
    💬 Chat  : www.techmartelectronics.com/chat
    📧 Email : support@techmartelectronics.com

    Business Hours: Mon-Fri 8AM-9PM EST | Sat-Sun 9AM-6PM EST

    Please keep your reference number {reference} handy
    when contacting us.

    Thank you for your patience.

    Best regards,
    TechMart Electronics Support Team
    www.techmartelectronics.com
    """

    customer_sent = send_email(customer_email, customer_subject, customer_body)

    # ------------------------------------------------------------------
    # Email 2: Support Team Alert
    # ------------------------------------------------------------------
    # Falls back to SMTP_USER if a dedicated support inbox isn't configured
    support_email = settings.SUPPORT_EMAIL or settings.SMTP_USER

    support_subject = f"🚨 ESCALATION ALERT — {customer_name} [{reference}]"

    support_body = f"""
    ----------------------------------------
    ⚠️  HUMAN AGENT ESCALATION REQUEST
    ----------------------------------------

    CUSTOMER DETAILS:
    Name : {customer_name}
    Email : {customer_email}
    Reference : {reference}

    CASE DETAILS:
    Topic : {session_title}
    Time : {timestamp}
    Session : {session_id}

    ----------------------------------------
    ACTION REQUIRED:
    Contact this customer within 2 business hours.
    Reply directly to: {customer_email}
    ----------------------------------------

    TechMart AI Support System — Automated Alert
    """

    support_sent = send_email(support_email, support_subject, support_body)

    return {

        "customer_email_sent": customer_sent,

        "support_email_sent": support_sent,

        "reference": reference,

        "customer_email": customer_email,

        "support_email": support_email

    }


def send_ticket_created_email(customer_name: str, customer_email: str, ticket_number: str, subject: str, priority: str) -> bool:
    
    "Send a notification email when a support ticket is auto-created."

    email_subject = (f"[TechMart] Ticket {ticket_number} Created — {priority.upper()} Priority")

    body = f"""
    
    Dear {customer_name},

    A support ticket has been automatically created for your inquiry.

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    TICKET DETAILS
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    Ticket Number : {ticket_number}
    Subject       : {subject[:80]}
    Priority      : {priority.upper()}
    Status        : OPEN
    Created At    : {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    Our team will review your case and respond based on priority:
    🔴 HIGH → Within 2 business hours
    🟡 MEDIUM → Within 4 business hours
    🟢 LOW → Within 8 business hours

    CONTACT US: 📞 1-800-TECHMART | 📧 support@techmartelectronics.com

    Best regards,
    TechMart Electronics Support Team
    """

    return send_email(customer_email, email_subject, body)


def send_feedback_thank_you(customer_name: str, customer_email: str, rating: int) -> bool:
    
    "Send a thank-you email after a customer submits feedback, with a slightly different tone depending on whether the rating was high or low."

    stars = "⭐" * rating

    subject = f"[TechMart] Thank You for Your Feedback! {stars}"

    body = f"""
    Dear {customer_name},

    Thank you for taking the time to rate your experience with
    TechMart Electronics AI Support!

    Your Rating: {stars} ({rating}/5)

    {'We are thrilled to hear you had a great experience!' if rating >= 4 else 'We appreciate your honest feedback and will use it to improve.'}

    Your feedback helps us provide better support to all
    TechMart customers.

    NEED MORE HELP?
    📞 1-800-TECHMART | 📧 support@techmartelectronics.com
    💬 Chat: www.techmartelectronics.com/chat

    Best regards,
    TechMart Electronics Support Team
    """

    return send_email(customer_email, subject, body)
