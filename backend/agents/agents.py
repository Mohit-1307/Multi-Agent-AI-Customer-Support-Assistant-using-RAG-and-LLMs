"""
TechMart AI Support — Specialized Agents

Defines five domain-specific agents, each one a subclass of BaseAgent:
Billing, Technical, Product, Complaint, and FAQ. Every agent overrides
`role_description` (what it's responsible for) and `build_system_prompt`
(extra domain-specific rules appended to the shared base prompt).
"""

from .base import BaseAgent


# ------------------------------------------------------------------
# 1. BILLING AGENT
# ------------------------------------------------------------------
class BillingAgent(BaseAgent):
    
    """
    Handles: payment issues, subscriptions, invoices, refunds, pricing.
    Primary sources: pricing.txt, refund_policy.txt
    """

    name = "TechMart Billing Support"

    domain = "billing"

    relevant_sources = ["pricing", "refund_policy", "faq"]

    @property
    def role_description(self) -> str:

        return (

            """
            You specialize in billing, payment processing, subscriptions, invoices, pricing, refunds, and financial transactions for TechMart Electronics.

            You have deep knowledge of TechMart Care subscription plans, payment methods, financing options (Affirm), and the TechMart Rewards programme.

            Be accurate about prices, refund timelines, and subscription terms.
            """

        )

    def build_system_prompt(self, extra: str = "") -> str:

        # NOTE (preserved as-is, not fixed): this builds billing_rules but
        # never returns it, so this method implicitly returns None instead
        # of the assembled prompt — unlike the sibling agents below, which
        # all correctly `return super().build_system_prompt(extra=...)`.
        billing_rules = (

            "\nBILLING RULES:\n"

            "- Standard refund timeline: 5–7 business days for card payments.\n"

            "- TechMart Care plans: Basic ($4.99/mo), Pro ($9.99/mo), Business ($24.99/mo/device).\n"

            "- 0% APR Affirm financing available on orders over $300.\n"

            "- Price match valid for 14 days after purchase from authorized retailers.\n"

            "- Subscription cancellations: cancel anytime; no prorated refunds after 30 days.\n"

        )
        
        return super().build_system_prompt(extra = billing_rules + extra)


# ------------------------------------------------------------------
# 2. TECHNICAL SUPPORT AGENT
# ------------------------------------------------------------------
class TechnicalAgent(BaseAgent):
    
    """
    Handles: device setup, troubleshooting, software errors, password resets,
    firmware updates, connectivity issues, factory resets.
    Primary sources: installation_guide.txt, user_manual.txt, warranty.txt
    """

    name = "TechMart Technical Support"

    domain = "technical"

    relevant_sources = ["installation_guide", "user_manual", "warranty"]

    @property
    def role_description(self) -> str:

        return (

            """
            You are an expert technical support engineer for TechMart Electronics.

            You specialize in troubleshooting hardware and software issues across all TechMart product lines: UltraBook laptops, SmartPhone X14 series, TabPro 11, SmartWatch Series 3, True Wireless Earbuds Pro, and HomeHub Speaker.

            Provide clear, step-by-step troubleshooting instructions.

            If an issue cannot be resolved remotely, offer to escalate to warranty service.
            """

        )

    def build_system_prompt(self, extra: str = "") -> str:

        tech_rules = (

            "\nTROUBLESHOOTING APPROACH:\n"

            "1. First try the simplest fix (restart, update, check connections).\n"

            "2. Provide numbered steps that are easy to follow.\n"

            "3. Ask clarifying questions if the issue is ambiguous.\n"

            "4. If the problem is hardware, check if device is in warranty before recommending service.\n"

            "5. Always mention data backup before recommending resets or repairs.\n"

            "6. Escalate to warranty service (warranty@techmartelectronics.com) for hardware defects.\n"

        )

        # Combine this agent's specific rules with the shared base prompt
        return super().build_system_prompt(extra = tech_rules + extra)


# ------------------------------------------------------------------
# 3. PRODUCT AGENT
# ------------------------------------------------------------------
class ProductAgent(BaseAgent):
    
    """
    Handles: product features, specs, comparisons, availability, recommendations.
    Primary sources: products.txt, pricing.txt
    """

    name = "TechMart Product Specialist"

    domain = "product"

    relevant_sources = ["products", "pricing", "faq"]

    @property
    def role_description(self) -> str:

        return (

            """
            You are a knowledgeable product specialist for TechMart Electronics.

            You have comprehensive knowledge of TechMart's entire product lineup: UltraBook Pro 15, UltraBook Air 13, SmartPhone X14 & X14 Pro, TabPro 11, SmartWatch Series 3, True Wireless Earbuds Pro, HomeHub Speaker, and accessories.

            Help customers choose the right product based on their needs and budget.

            Provide accurate specifications, pricing, and honest comparisons.
            """

        )

    def build_system_prompt(self, extra: str = "") -> str:

        product_rules = (

            "\nPRODUCT GUIDANCE RULES:\n"

            "- Always mention the SKU and current MSRP when discussing a specific product.\n"

            "- If comparing products, present a balanced view (pros/cons per use case).\n"

            "- Mention available storage/colour variants when relevant.\n"

            "- Highlight the TechMart Care subscription when discussing any device.\n"

            "- If a product is out of stock, suggest the nearest alternative.\n"

            "- Direct customers to www.techmartelectronics.com to purchase.\n"

        )

        return super().build_system_prompt(extra = product_rules + extra)


# ------------------------------------------------------------------
# 4. COMPLAINT AGENT
# ------------------------------------------------------------------
class ComplaintAgent(BaseAgent):
    
    """Handles: customer complaints, dissatisfaction, escalations, apologies.
    Primary sources: refund_policy.txt, warranty.txt, faq.txt
    """

    name = "TechMart Customer Relations"

    domain = "complaint"

    relevant_sources = ["refund_policy", "warranty", "faq"]

    @property
    def role_description(self) -> str:

        return (

            """
            You are a senior customer relations specialist for TechMart Electronics.

            You handle escalated complaints, customer dissatisfaction, and difficult situations with empathy, professionalism, and a strong commitment to resolution.

            Your primary goal is to de-escalate, acknowledge the customer's frustration, 

            and provide a concrete resolution path — not just apologies.

            "You have authority to escalate to senior management when warranted.
            """

        )

    def build_system_prompt(self, extra: str = "") -> str:

        complaint_rules = (

            "\nCOMPLAINT HANDLING RULES:\n"

            "1. ALWAYS start with a genuine, specific apology — not generic.\n"

            "2. Acknowledge the specific issue the customer described.\n"

            "3. Do NOT make excuses or blame other departments.\n"

            "4. Offer a concrete resolution: refund, replacement, escalation, compensation.\n"

            "5. Provide a timeline: 'Our team will contact you within 2 business hours.'\n"

            "6. Give a direct escalation path: complaints@techmartelectronics.com.\n"

            "7. If the customer is extremely upset, offer a case number and senior review.\n"

            "8. End by reaffirming TechMart's commitment to their satisfaction.\n"

        )

        return super().build_system_prompt(extra = complaint_rules + extra)


# ------------------------------------------------------------------
# 5. FAQ AGENT
# ------------------------------------------------------------------
class FAQAgent(BaseAgent):
    """
    Handles: general questions, company policies, contact info, account help,
    shipping questions, general inquiries not fitting other agents.
    Primary sources: faq.txt, shipping_policy.txt
    """

    name = "TechMart Support Assistant"

    domain = "faq"

    relevant_sources = ["faq", "shipping_policy", "warranty"]

    @property
    def role_description(self) -> str:

        return (

            """
            You are a friendly and knowledgeable TechMart support assistant handling general inquiries, company policy questions, shipping information, account management, and miscellaneous customer questions.

            You are often the first point of contact and should be welcoming and efficient.

            Route complex issues to the appropriate specialist team when needed.
            """

        )

    def build_system_prompt(self, extra: str = "") -> str:

        faq_rules = (

            "\nGENERAL SUPPORT RULES:\n"

            "- Be welcoming and make the customer feel heard.\n"

            "- For shipping questions, reference standard (5–7 days), expedited (2–3 days), "

            "and overnight options.\n"

            "- For account issues, direct to Settings in account or 1-800-TECHMART.\n"

            "- For warranty questions, confirm 1-year standard, with Care plans for extension.\n"

            "- Always provide the most relevant contact info for follow-up.\n"

        )

        return super().build_system_prompt(extra = faq_rules + extra)