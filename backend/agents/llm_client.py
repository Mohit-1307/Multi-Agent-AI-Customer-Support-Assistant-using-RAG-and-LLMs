"""
TechMart AI Support — Unified LLM Client

Supports Groq, OpenAI, and Ollama (all through the OpenAI-compatible SDK).
Falls back to simple template responses when no API key is configured,
so the app still works in a "demo mode" without any external API access.
"""

import asyncio
import logging
from typing import List, Optional
from ..config import settings

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Intent -> template fallback responses, used only when no LLM API key is set
# -----------------------------------------------------------------------------
FALLBACK_RESPONSES = {

    "billing": (

        """
        I can see you have a billing-related question. 
        
        Based on our records, TechMart offers flexible payment options including Visa, Mastercard, PayPal, and Affirm financing. 
        
        For detailed billing inquiries, please contact us at billing@techmartelectronics.com or call 1-800-TECHMART.

        Our billing team is available Mon–Fri 8AM–9PM EST.
        """

    ),

    "technical": (

        """
        Thank you for reaching out about a technical issue. 
        
        Our technical support team is here to help! For immediate assistance, please try restarting your device (hold Power for 10 seconds). 
        
        If the issue persists, contact us at support@techmartelectronics.com or call 1-800-TECHMART.

        We're available Mon–Fri 8AM–9PM EST.
        """

    ),

    "product": (

        """
        Great question about our products! 
        
        TechMart Electronics offers a wide range of premium devices including UltraBooks, SmartPhones, TabPros, SmartWatches, and more. 
        
        Visit www.techmartelectronics.com/products to explore our full

        catalog with detailed specifications and pricing.
        """

    ),

    "complaint": (

        """
        I sincerely apologize for the experience you've had. 
        
        At TechMart, customer satisfaction is our top priority.

        I'm escalating your concern to our senior support team who will contact you within 2 business hours.

        You can also reach us directly at complaints@techmartelectronics.com or 1-800-TECHMART.
        """

    ),

    "refund": (

        """
        I understand you'd like information about a refund. 
        
        TechMart has a 30-day return policy for most items in their original condition. To initiate a return, log into your account, go to Orders, and click 'Start Return.

        Refunds are processed within 5–7 business days to your original payment method.
        """

    ),

    "faq": (

        """
        Thank you for your question! 
        
        TechMart Electronics is here to help. 
        
        For comprehensive answers, visit our FAQ page at www.techmartelectronics.com/faq.

        You can also reach our support team at support@techmartelectronics.com or call 1-800-TECHMART.
        """

    ),

    "general": (

        """
        Thank you for contacting TechMart Electronics support! 
        
        How can I assist you today? 
        
        I can help with product information, billing, technical issues, returns, warranties, and more.

        Please provide more details about your inquiry.
        """

    ),

}


class LLMClient:
    
    "Wrapper around OpenAI-compatible APIs (Groq, OpenAI, Ollama). All methods are async."

    def __init__(self):

        # The actual SDK client — created lazily, not here (see _get_client below)
        self._client = None

        # Loaded once from settings: api_key, base_url, model for the active provider
        self._config = settings.get_llm_config()

        self._provider = settings.LLM_PROVIDER

    def _get_client(self):
        
        """
        Lazily initialise the OpenAI SDK client, only when it's first needed.
        Returns None if no API key is configured or the SDK isn't installed —
        callers treat None as "fall back to template responses".
        """

        # Already created on a previous call — reuse it
        if self._client is not None:

            return self._client

        config = self._config

        # No real API key configured (or it's the placeholder "mock" value)
        if not config.get("api_key") or config["api_key"] == "mock":

            return None

        try:

            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(api_key = config["api_key"], base_url = config["base_url"])

            logger.info(

                f"LLM client initialized: provider = {self._provider},"

                f"model = {config['model']}"

            )

        except ImportError:

            # openai package isn't installed — fall back gracefully instead of crashing
            logger.warning("openai package not installed. Using fallback mode.")

            return None

        return self._client

    async def chat(

        self,

        messages: List[dict],

        system: Optional[str] = None,

        max_tokens: int = None,

        temperature: float = None,

    ) -> str:
        
        """Send a chat completion request and return the assistant's reply text.

        Args:
            messages: list of {"role": "user"|"assistant", "content": "..."}
            system: optional system prompt prepended to messages
            max_tokens: max tokens to generate
            temperature: sampling temperature

        Returns:
            Assistant reply string"""

        client = self._get_client()

        # No LLM configured — use the intent-based fallback templates instead
        if client is None:

            last_user_msg = ""

            # Walk backwards through messages to find the most recent user message
            for m in reversed(messages):

                if m["role"] == "user":

                    last_user_msg = m["content"].lower()

                    break

            return self._fallback_response(last_user_msg)

        full_messages = []

        # System prompt goes first, if one was provided
        if system:

            full_messages.append({"role": "system", "content": system})

        full_messages.extend(messages)

        # ----------------------------------------------------------------------------
        # Retry up to 3 times on failure, with increasing wait time between attempts
        # ----------------------------------------------------------------------------
        last_error = None

        for attempt in range(3):

            try:

                response = await client.chat.completions.create(

                    model = self._config["model"],

                    messages = full_messages,

                    max_tokens = max_tokens or settings.MAX_TOKENS,

                    temperature = temperature or settings.TEMPERATURE,

                    timeout = 30.0

                )

                return response.choices[0].message.content.strip()

            except Exception as e:

                last_error = e

                logger.warning(f"LLM attempt {attempt + 1}/3 failed ({self._provider}): {e}")

                # Don't sleep after the final attempt, just fall through to the fallback
                if attempt < 2:

                    import asyncio

                    wait = (attempt + 1) * 2  # 2s, then 4s

                    logger.info(f"Retrying in {wait}s...")

                    await asyncio.sleep(wait)

                continue

        logger.error(f"LLM API failed after 3 attempts: {last_error}")

        # All retries failed — use the smart fallback based on the last user message
        last_msg = ""

        for m in reversed(messages):

            if m.get("role") == "user":

                last_msg = m.get("content", "")

                break

        return self._fallback_response(last_msg)

    async def complete(self, prompt: str, max_tokens: int = 300) -> str:
        
        "Single-turn completion — a convenience wrapper around chat() for when you just have one prompt and no conversation history."

        return await self.chat([{"role": "user", "content": prompt}], max_tokens = max_tokens)

    def _fallback_response(self, message: str) -> str:
        
        """
        Keyword-based fallback response, used only when no LLM is configured.
        Looks for keywords in the user's message to guess which template fits best.
        """

        msg = message.lower()

        # Billing-related keywords
        if any(w in msg for w in ["bill", "invoice", "payment", "charge", "subscription", "renew"]):

            return FALLBACK_RESPONSES["billing"]

        # Refund/return-related keywords
        if any(w in msg for w in ["refund", "return", "money back", "cancel order"]):

            return FALLBACK_RESPONSES["refund"]

        # Technical-issue keywords
        if any(w in msg for w in ["broken", "not work", "error", "bug", "crash", "install", "password", "login"]):

            return FALLBACK_RESPONSES["technical"]

        # Product-related keywords
        if any(w in msg for w in ["product", "price", "spec", "model", "laptop", "phone", "tablet", "buy"]):

            return FALLBACK_RESPONSES["product"]

        # Complaint-related keywords
        if any( w in msg for w in ["complaint", "angry", "terrible", "awful", "worst", "disappointed"]):

            return FALLBACK_RESPONSES["complaint"]

        # Nothing matched — use the generic greeting/fallback
        return FALLBACK_RESPONSES["general"]


# ------------------------------------------------------------------
# Module-level singleton — reused across the app instead of creating
# a new LLMClient (and a new SDK connection) on every request
# ------------------------------------------------------------------
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    
    "Return the shared LLMClient instance, creating it on first call."

    global _llm_client

    if _llm_client is None:

        _llm_client = LLMClient()

    return _llm_client
