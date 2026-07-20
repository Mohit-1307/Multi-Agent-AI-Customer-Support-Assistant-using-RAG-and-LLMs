import logging
from datetime import datetime
from ..config import settings

logger = logging.getLogger(__name__)


def is_email_configured() -> bool:

    return bool(settings.SMTP_USER and settings.SMTP_PASSWORD)


def send_email(to_email: str, subject: str, body: str) -> bool:

    try:

        import urllib.request
        import json as _json
        import os

        api_key = os.getenv("SENDGRID_API_KEY", "")
        
        if not api_key:
            
            # Fallback to SMTP if no SendGrid key
            return _send_smtp(to_email, subject, body)

        payload = _json.dumps({
            
            "personalizations": [{"to": [{"email": to_email}]}],
            
            "from": {"email": settings.SMTP_USER, "name": "TechMart Support"},
            
            "subject": subject,
            
            "content": [{"type": "text/plain", "value": body}]
            
        }).encode()

        req = urllib.request.Request(
            
            "https://api.sendgrid.com/v3/mail/send",
            data = payload,

            headers = {

                "Authorization": f"Bearer {api_key}",

                "Content-Type": "application/json"

            },

            method = "POST"

        )

        with urllib.request.urlopen(req, timeout = 10) as resp:

            logger.info(f"Email sent via SendGrid to {to_email}")

            return True

    except Exception as e:

        logger.error(f"Email send failed: {e}")

        return False


def _send_smtp(to_email: str, subject: str, body: str) -> bool:

    import smtplib

    from email.mime.multipart import MIMEMultipart

    from email.mime.text import MIMEText

    try:

        msg = MIMEMultipart()

        msg["From"] = f"TechMart Support <{settings.SMTP_USER}>"

        msg["To"] = to_email

        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(settings.SMTP_HOST, int(settings.SMTP_PORT)) as server:

            server.ehlo()

            server.starttls()

            server.ehlo()

            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)

            server.send_message(msg)

        logger.info(f"Email sent via SMTP to {to_email}")

        return True

    except Exception as e:

        logger.error(f"SMTP failed: {e}")

        return False


def send_escalation_emails(customer_name, customer_email, session_id, session_title = "Support Query"):

    reference = f"ESC-{session_id[:8].upper()}"

    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    customer_body = f"""Dear {customer_name},

    Your support request has been escalated to a human agent.

    Reference: {reference}

    Topic: {session_title}

    Time: {timestamp}

    A TechMart specialist will contact you at {customer_email} within 2 business hours.

    Phone: 1-800-TECHMART

    Email: support@techmartelectronics.com

    Thank you for your patience.

    TechMart Electronics Support Team"""

    support_email = settings.SUPPORT_EMAIL or settings.SMTP_USER
            
    support_body = f"""ESCALATION ALERT

    Customer: {customer_name}

    Email: {customer_email}

    Reference: {reference}

    Topic: {session_title}

    Time: {timestamp}

    Contact this customer within 2 business hours.
    """

    customer_sent = send_email(customer_email, f"[TechMart] Your Case {reference} — Human Agent Requested", customer_body)
    
    support_sent = send_email(support_email, f"ESCALATION — {customer_name} [{reference}]", support_body)

    return {"customer_email_sent": customer_sent, "support_email_sent": support_sent, "reference": reference}


def send_ticket_created_email(customer_name, customer_email, ticket_number, subject, priority):
    
    body = f"""Dear {customer_name},

    A support ticket has been created for your inquiry.

    Ticket: {ticket_number}

    Subject: {subject[:80]}

    Priority: {priority.upper()}

    Status: OPEN

    Our team will respond based on priority:

    HIGH → Within 2 hours

    MEDIUM → Within 4 hours

    Phone: 1-800-TECHMART

    Email: support@techmartelectronics.com

    TechMart Electronics Support Team
    """

    return send_email(customer_email, f"[TechMart] Ticket {ticket_number} Created — {priority.upper()} Priority", body)


def send_feedback_thank_you(customer_name, customer_email, rating):

    stars = "⭐" * rating

    body = f"""Dear {customer_name},
    
Thank you for rating your experience! {stars} ({rating}/5)

{'We are thrilled to hear you had a great experience!' if rating >= 4 else 'We appreciate your honest feedback.'}

TechMart Electronics Support Team"""

    return send_email(customer_email, f"[TechMart] Thank You for Your Feedback! {stars}", body)