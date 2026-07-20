"""
TechMart AI Support — Agent Router & Orchestrator

Responsibilities:
    1. Detect intent from the user message (via LLM or keyword fallback)
    2. Detect sentiment (positive / neutral / negative / frustrated)
    3. Route the message to one or more specialized agents
    4. Aggregate responses from multiple agents when needed
"""

import json
import logging
import re
from typing import Dict, List, Optional, Tuple
from ..config import settings
from .agents import BillingAgent, ComplaintAgent, FAQAgent, ProductAgent, TechnicalAgent
from .base import BaseAgent
from .language import detect_language
from .llm_client import get_llm_client

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Intent & Sentiment keyword definitions
# ------------------------------------------------------------------
# Each intent maps to a list of keywords/phrases that suggest that intent.
# Used by the fast keyword-based classifier before falling back to the LLM.
INTENTS = {

    "billing": [

        "payment",

        "invoice",

        "subscription",

        "charge",

        "bill",

        "refund",

        "pricing",

        "price",

        "cost",

        "fee",

        "money",

        "credit",

        "debit",

        "affirm",

        "financing",

        "plan",

        "renew",

        "cancel subscription",

        "techmart care",

        "rewards points",

        "care plan",

        "care pricing",

        "how much does",

        "what does it cost",

        "care basic",

        "care pro",

        "monthly plan",

        "annual plan",

        "per month",

        "per year",

        "subscription cost",

        "subscription price",

        "plan price",

        "upgrade plan",

        "care subscription"

    ],

    "refund": [

        "refund",

        "return",

        "money back",

        "reimburse",

        "cancel order",

        "exchange",

        "sent back",

        "ship back",

        "return policy",

        "refund policy",

        # Hindi terms
        "वापसी",

        "रिटर्न",

        "रिटर्न पॉलिसी",

        "वापसी नीति",

        "पैसे वापस",

        # Spanish terms
        "política de devoluciones",

        "devoluciones",

        # French terms
        "politique de retour",

        "remboursement",

        # German terms
        "rückgabe",

        "rückerstattung"

    ],

    "technical": [

        "not working",

        "broken",

        "error",

        "bug",

        "crash",

        "install",

        "setup",

        "login",

        "password",

        "reset",

        "update",

        "freeze",

        "slow",

        "wifi",

        "bluetooth",

        "connect",

        "driver",

        "screen",

        "battery drain",

        "overheating",

        "won't turn on",

        "black screen"

    ],

    "product": [

        "product",

        "laptop",

        "phone",

        "tablet",

        "watch",

        "earbuds",

        "speaker",

        "ultrabook",

        "smartphone",

        "tabpro",

        "smartwatch",

        "spec",

        "specification",

        "feature",

        "compare",

        "difference",

        "which is better",

        "available",

        "stock",

        "color",

        "size",

        "recommend",

        "buy",

        "purchase",

        "x14",

        "x14 pro",

        "ultrabook",

        "air 13",

        "pro 15",

        "homehub",

        "earbuds pro",

        "series 3",

        "techmart care",

        "stylus",

        "keyboard",

        "charger",

        "accessory",

        "how much",

        "what does",

        "tell me about",

        "best product",

        "which model",

        "latest",

        "new model",

        "upgrade"

    ],

    "complaint": [

        "complaint",

        "terrible",

        "awful",

        "worst",

        "horrible",

        "angry",

        "furious",

        "disgusted",

        "unacceptable",

        "disappointed",

        "scam",

        "never again",

        "lawsuit",

        "garbage",

        "waste of money",

        "demand",

        "escalate",

        "manager",

        "supervisor"

    ],

    "faq": [

        "hours",

        "contact",

        "where",

        "when",

        "how long",

        "shipping",

        "deliver",

        "track",

        "account",

        "warranty",

        "how do I",

        "can I",

        "do you",

        "business hours",

        "store location",

        "contact number"

    ]

}

# Keyword lists used to guess the customer's emotional tone
SENTIMENT_KEYWORDS = {

    "positive": [

        "thank",

        "thanks",

        "thankyou",

        "thank you",

        "great",

        "awesome",

        "excellent",

        "perfect",

        "wonderful",

        "amazing",

        "fantastic",

        "good",

        "helpful",

        "love",

        "happy",

        "satisfied",

        "pleased",

        "brilliant",

        "superb",

        "outstanding",

        "resolved",

        "fixed",

        "works",

        "working now",

        "appreciate",

        "appreciated"

    ],

    "negative": [

        "bad",

        "poor",

        "terrible",

        "horrible",

        "worst",

        "awful",

        "disappointed",

        "unhappy",

        "not satisfied",

        "not working",

        "broken",

        "failed",

        "error",

        "wrong",

        "issue",

        "problem",

        "doesn't work",

        "not good",

        "very bad",

        "really bad",

        "not happy",

        "not helpful",

        "useless",

        "waste",

        "unable",

        "can't",

        "cannot",

        "stuck",

        "confused"

    ],

    "frustrated": [

        "angry",

        "furious",

        "frustrated",

        "fed up",

        "ridiculous",

        "unacceptable",

        "disgusted",

        "outraged",

        "livid",

        "pathetic",

        "worst ever",

        "never again",

        "demand refund",

        "very angry",

        "so angry",

        "extremely frustrated",

        "hate this",

        "this is ridiculous",

        "still not working",

        "been waiting",

        "no response",

        "ignored",

        "wasting my time",

        "waste of money",

        "regret buying"

    ]

}


class AgentRouter:
    
    "Orchestrates intent detection, sentiment analysis, and agent dispatch."

    def __init__(self):

        # One instance of each specialized agent, keyed by intent name.
        # Note: "refund" and "general" reuse the Billing/FAQ agent instances
        # rather than having their own dedicated agent classes.
        self._agents: Dict[str, BaseAgent] = {

            "billing": BillingAgent(),

            "refund": BillingAgent(),  # refunds handled by billing agent

            "technical": TechnicalAgent(),

            "product": ProductAgent(),

            "complaint": ComplaintAgent(),

            "faq": FAQAgent(),

            "general": FAQAgent()

        }

        self._llm = get_llm_client()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def route(self, user_message: str, conversation_history: Optional[List[dict]] = None) -> dict:
        
        "Main entry point. Detects intent/sentiment, picks the right agent(s), and returns the full routing + agent response payload."

        history = conversation_history or []

        # Step 1: Detect intent and sentiment for this message
        routing = await self._detect_intent_and_sentiment(user_message, history)

        intent: str = routing["intent"]

        sentiment: str = routing["sentiment"]

        sentiment_score: float = routing["sentiment_score"]

        confidence: float = routing["confidence"]

        suggested_agents: List[str] = routing["suggested_agents"]

        # Step 2: Determine the primary agent to handle this message
        primary_intent = suggested_agents[0] if suggested_agents else "general"

        # Safety check — make sure primary_intent is actually a valid agent key,
        # in case the LLM classifier returned something unexpected
        valid_agents = {

            "billing",

            "refund",

            "technical",

            "product",

            "complaint",

            "faq",

            "general"

        }

        if primary_intent not in valid_agents:

            primary_intent = "general"

        # Step 3: If the customer sounds frustrated, always also involve
        # the complaint agent so the tone of the reply reflects that
        if sentiment == "frustrated" and "complaint" not in suggested_agents:

            suggested_agents.append("complaint")

        logger.info(

            f"Routing | intent = {intent} | sentiment = {sentiment}"

            f"| confidence={confidence:.2f} | agents = {suggested_agents}"

        )

        # Step 4: Invoke the primary agent to generate the actual response
        primary_agent = self._agents.get(primary_intent, self._agents["faq"])

        primary_result = await primary_agent.respond(user_message, history)

        # Step 5: If more than one agent applies (rare — usually just the
        # frustrated + complaint case above), blend in an empathy opener
        response_text = primary_result["response"]

        if len(suggested_agents) > 1 and "complaint" in suggested_agents[1:]:

            complaint_agent = self._agents["complaint"]

            complaint_result = await complaint_agent.respond(user_message, history)

            # Prepend an empathy statement from the complaint agent, but only
            # if it isn't already present in the primary response (avoid duplication)
            empathy = self._extract_empathy_line(complaint_result["response"])

            if empathy and empathy not in response_text:

                response_text = empathy + "\n\n" + response_text

        return {

            "response": response_text,

            "agent": primary_agent.domain,

            "agent_name": primary_agent.name,

            "intent": intent,

            "sentiment": sentiment,

            "sentiment_score": sentiment_score,

            "confidence": confidence,

            "suggested_agents": suggested_agents,

            "context_retrieved": primary_result.get("context_retrieved", False),

            "sources": primary_result.get("sources", [])

        }

    async def detect_intent(self, message: str) -> dict:
        
        "Lightweight public method for just getting the intent/sentiment, without actually generating an agent response."

        return await self._detect_intent_and_sentiment(message, [])

    # ------------------------------------------------------------------
    # Intent & Sentiment Detection (internal)
    # ------------------------------------------------------------------
    async def _detect_intent_and_sentiment(self, message: str, history: List[dict]) -> dict:
        
        "Two-stage detection: fast keyword matching first, then an LLM call to refine the result only if the keyword match was ambiguous."

        # Stage 1 — keyword baseline (always fast, no network call)
        keyword_result = self._keyword_detect(message)

        # Skip the LLM call entirely if keyword confidence is already high.
        # This saves 1-2 seconds per request when the message is unambiguous.
        if keyword_result.get("confidence", 0) >= 0.7:

            logger.info("High confidence keyword detection — skipping LLM classification")

            return keyword_result

        # Stage 2 — ask the LLM to refine the classification, but only for
        # messages where the keyword match wasn't confident enough
        try:

            llm_result = await self._llm_detect(message, history)

            if llm_result and llm_result.get("confidence", 0) > 0.5:

                # If keyword already detected frustrated/negative, don't let
                # LLM downgrade it — keyword is more reliable for sentiment
                keyword_sentiment = keyword_result.get("sentiment", "neutral")

                llm_sentiment = llm_result.get("sentiment", "neutral")

                SENTIMENT_PRIORITY = {
                    
                    "frustrated": 3,
                    
                    "negative": 2,
                    
                    "positive": 1,
                    
                    "neutral": 0,
                    
                }

                if SENTIMENT_PRIORITY.get(keyword_sentiment, 0) > SENTIMENT_PRIORITY.get(llm_sentiment, 0):

                    llm_result["sentiment"] = keyword_sentiment

                    llm_result["sentiment_score"] = keyword_result.get("sentiment_score", 0.0)

                return llm_result

        except Exception as e:

            # If the LLM call fails for any reason, just use the keyword result
            logger.warning(f"LLM intent detection failed, using keywords: {e}")

        return keyword_result

    def _keyword_detect(self, message: str) -> dict:
        
        """
        Fast keyword-based intent and sentiment detection.
        No network call — just checks the message text against the
        keyword lists defined above.
        """

        msg_lower = message.lower()

        # Sentiment detection — check frustrated first (most specific),
        # then negative, then positive. Priority order matters because
        # a frustrated message often also contains negative/positive words
        # (e.g. "this is ridiculous, I've been waiting and no response, thanks for nothing").
        sentiment = "neutral"

        sentiment_score = 0.0

        frustrated_count = sum(1 for kw in SENTIMENT_KEYWORDS["frustrated"] if kw in msg_lower)

        negative_count = sum(1 for kw in SENTIMENT_KEYWORDS["negative"] if kw in msg_lower)

        positive_count = sum(1 for kw in SENTIMENT_KEYWORDS["positive"] if kw in msg_lower)

        if frustrated_count > 0:

            sentiment = "frustrated"

            sentiment_score = -1.0

        elif negative_count > 0:

            sentiment = "negative"

            sentiment_score = -0.5

        elif positive_count > 0:

            sentiment = "positive"

            sentiment_score = 0.8

        else:

            sentiment = "neutral"

            sentiment_score = 0.0

        # ------------------------------------------------------------------
        # Intent detection — score each category by counting keyword hits
        # ------------------------------------------------------------------
        scores: Dict[str, int] = {intent: 0 for intent in INTENTS}

        for intent, keywords in INTENTS.items():

            for kw in keywords:

                if kw in msg_lower:

                    scores[intent] += 1

        # Pick whichever intent scored the highest
        best_intent = max(scores, key = lambda k: scores[k])

        best_score = scores[best_intent]

        if best_score == 0:

            # No keywords matched at all — default to "general" with low confidence
            best_intent = "general"

            confidence = 0.4

        else:

            # More keyword hits = higher confidence, capped at 0.9
            confidence = min(0.5 + best_score * 0.1, 0.9)

        # Build the suggested_agents list: sort intents by score (highest
        # first) and take the top 2 that scored above zero
        ranked = sorted(

            [(k, v) for k, v in scores.items() if v > 0],

            key = lambda x: x[1],

            reverse = True)

        suggested = [r[0] for r in ranked[:2]] or ["general"]

        return {

            "intent": best_intent,

            "confidence": confidence,

            "sentiment": sentiment,

            "sentiment_score": sentiment_score,

            "suggested_agents": suggested,

            "method": "keyword"

        }

    async def _llm_detect(self, message: str, history: List[dict]) -> Optional[dict]:
        
        "LLM-based intent and sentiment classification, requesting a structured JSON response from the model."

        # Summarize recent history to give the LLM some conversational context
        history_summary = ""

        if history:

            recent = history[-4:]

            history_summary = "\n".join(f"{m['role'].upper()}: {m['content'][:120]}" for m in recent)

        # Detect the language of the message, using the same shared heuristic
        # the base agent uses (agents/language.py), so intent classification
        # and the eventual reply are never working off two different guesses.
        detected_lang = detect_language(message)

        # Prompt asks the LLM to return a strict JSON object we can parse directly.
        # Sentiment guidance is intentionally detailed here — the model tends to
        # default to "neutral" too often unless explicitly told that any reported
        # problem (even a calmly-worded one) should be negative or frustrated.
        prompt = f"""You are an intent classification system for a customer support chatbot.

                    Customer message language detected: {detected_lang}

                    Classify the customer message below into EXACTLY ONE intent from this list:
                    - billing → payment, invoice, subscription, pricing, TechMart Care plans
                    - refund → return requests, refunds, order cancellations
                    - technical → device issues, setup, errors, troubleshooting, password reset
                    - product → product info, specs, comparisons, availability, recommendations
                    - complaint → complaints, dissatisfaction, escalations
                    - faq → general questions, policies, shipping, hours, account help
                    - general → doesn't fit any category above

                    Also classify the sentiment:
                    - positive → satisfaction, gratitude, praise, confirmation something works
                    - neutral → purely factual/informational questions with no stated problem or emotion
                    - negative → the customer reports a problem, failure, dissatisfaction, or something not working, even if stated calmly (e.g. "the device won't turn on", "I never got my refund", "this is not what I ordered")
                    - frustrated → negative AND expressing anger, urgency, or repeated failure (e.g. "still broken", "I've asked twice", swearing, ALL CAPS, exclamation-heavy)

                    IMPORTANT: If the customer is reporting ANY problem, defect, error, or unmet expectation, sentiment must be "negative" or "frustrated" — never "neutral". Only use "neutral" for messages with no problem and no emotion (e.g. "what are your store hours?").

                    Recent conversation:
                    {history_summary or "(no prior context)"}

                    Customer message: "{message}"

                    Respond ONLY with valid JSON (no markdown, no backticks):
                    {{
                        
                        "intent": "<one of the intent labels>",

                        "confidence": <0.0-1.0>,

                        "sentiment": "<positive|neutral|negative|frustrated>",

                        "sentiment_score": <-1.0 to 1.0>,

                        "suggested_agents": ["<primary agent>", "<optional secondary>"],

                        "detected_language": "{detected_lang}",

                        "reasoning": "<one sentence>"

                    }}
                    """

        raw = await self._llm.complete(prompt, max_tokens = 250)

        raw = raw.strip()

        # Strip markdown code fences if the LLM wrapped its JSON in ```json ... ```
        raw = re.sub(r"^```(?:json)?\s*", "", raw)

        raw = re.sub(r"\s*```$", "", raw)

        try:

            parsed = json.loads(raw)

        except json.JSONDecodeError:

            # LLM didn't return valid JSON — log it and let the caller fall back to keywords
            logger.warning(f"LLM returned invalid JSON: {raw[:100]}")

            raise ValueError("Invalid JSON from LLM")

        # ------------------------------------------------------------------
        # Validate and normalize the LLM's response before trusting it
        # ------------------------------------------------------------------
        valid_intents = {

            "billing",

            "refund",

            "technical",

            "product",

            "complaint",

            "faq",

            "general"

        }

        valid_sentiments = {"positive", "neutral", "negative", "frustrated"}

        intent = parsed.get("intent", "general")

        if intent not in valid_intents:

            intent = "general"

        sentiment = parsed.get("sentiment", "neutral")

        if sentiment not in valid_sentiments:

            # Log the exact raw LLM output when the sentiment field comes back
            # invalid/missing, since this is the case most worth debugging
            logger.warning(

                f"LLM returned invalid/missing sentiment {sentiment!r} for message; "

                f"defaulting to neutral. Raw response: {raw[:200]}"

            )

            sentiment = "neutral"

        # The LLM sometimes returns human-friendly agent names instead of our
        # internal domain keys (e.g. "Tech Support" instead of "technical") —
        # this map translates those variants back to valid domain names
        AGENT_NAME_MAP = {

            "knowledge base": "faq",

            "live chat": "faq",

            "returns": "billing",

            "return policy": "billing",

            "support": "faq",

            "general support": "faq",

            "customer service": "faq",

            "customer relations": "complaint",

            "tech support": "technical",

            "product specialist": "product",

            "technical support": "technical",

            "billing support": "billing",

            "complaint handling": "complaint"

        }

        raw_agents = parsed.get("suggested_agents", [intent])

        normalized_agents = [AGENT_NAME_MAP.get(a.lower(), a.lower()) for a in raw_agents]

        # Filter out anything that still isn't a recognized agent domain
        valid_agents = {

            "billing",

            "refund",

            "technical",

            "product",

            "complaint",

            "faq",

            "general"

        }

        normalized_agents = [a for a in normalized_agents if a in valid_agents] or [intent]

        return {

            "intent": intent,

            "confidence": float(parsed.get("confidence", 0.7)),

            "sentiment": sentiment,

            "sentiment_score": float(parsed.get("sentiment_score", 0.0)),

            "suggested_agents": normalized_agents,

            "method": "llm"

        }

    # ------------------------------------------------------------------
    # Small internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_empathy_line(complaint_response: str) -> str:
        
        "Extract the first sentence of the complaint agent's response used as a short empathy opener prepended to another agent's reply."

        lines = complaint_response.strip().split(".")

        if lines:

            return lines[0].strip() + "."

        return ""


# ------------------------------------------------------------------
# Module-level singleton — reused across the app instead of rebuilding
# every agent instance on every request
# ------------------------------------------------------------------
_router: Optional[AgentRouter] = None


def get_router() -> AgentRouter:
    
    "Return the shared AgentRouter instance, creating it on first call."

    global _router

    if _router is None:

        _router = AgentRouter()

    return _router