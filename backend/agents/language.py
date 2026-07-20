"""
TechMart AI Support — Shared Language Detection

Single lightweight heuristic used everywhere a piece of code needs to
guess the language of a customer's message (unicode-range checks plus
common keyword matches). Not a full NLP language detector — just good
enough to steer the LLM's reply language and to build the classification
prompt in the router.

Previously this logic was implemented twice, independently, in
agents/base.py and agents/router.py — the two copies had drifted apart.
This module is now the single source of truth; both callers import
detect_language() from here instead.

COVERAGE:
    English, Hindi, Marathi, Nepali, Bengali, Tamil, Telugu, Kannada,
    Malayalam, Gujarati, Punjabi, Odia, Urdu, Spanish, French, German,
    Japanese, Arabic, Chinese.

KNOWN LIMITATION — Devanagari-script languages:
    Hindi, Marathi, Nepali, Sanskrit, Konkani, and Maithili all use the
    same Devanagari unicode block, so a character-range check alone
    cannot distinguish between them — "मला मदत हवी आहे" (Marathi) and
    "मुझे मदद चाहिए" (Hindi) both fall in the same unicode range. This
    module first checks the range, then breaks the tie using a small
    keyword list biased toward Marathi/Nepali function words that don't
    appear in Hindi; anything in the Devanagari range that doesn't match
    those keywords defaults to Hindi, since it's the most common case for
    this app's customer base. This is a heuristic, not a guarantee — for
    short or ambiguous messages it can still misclassify.
"""

from typing import List

# ------------------------------------------------------------------
# Unicode script ranges
# ------------------------------------------------------------------
_DEVANAGARI_RANGE = ("\u0900", "\u097f")   # Hindi, Marathi, Nepali, Sanskrit, Konkani, Maithili

_BENGALI_RANGE = ("\u0980", "\u09ff")      # Bengali, Assamese

_GURMUKHI_RANGE = ("\u0a00", "\u0a7f")     # Punjabi

_GUJARATI_RANGE = ("\u0a80", "\u0aff")

_ODIA_RANGE = ("\u0b00", "\u0b7f")

_TAMIL_RANGE = ("\u0b80", "\u0bff")

_TELUGU_RANGE = ("\u0c00", "\u0c7f")

_KANNADA_RANGE = ("\u0c80", "\u0cff")

_MALAYALAM_RANGE = ("\u0d00", "\u0d7f")

_ARABIC_RANGE = ("\u0600", "\u06ff")       # also covers Urdu, which is written in a Perso-Arabic script

_JAPANESE_RANGE = ("\u3040", "\u30ff")     # Hiragana/Katakana

_CHINESE_RANGE = ("\u4e00", "\u9fff")      # CJK


# ------------------------------------------------------------------
# Devanagari tie-breaker: words distinctive to Marathi vs Nepali
# (deliberately excludes words like "धन्यवाद" that both languages share,
# since a shared word can't be used to tell them apart)
# ------------------------------------------------------------------
_MARATHI_KEYWORDS: List[str] = [
    
    "आहे", "मला", "तुम्ही", "काय", "कसे", "पाहिजे", "मदत हवी"
    
]

_NEPALI_KEYWORDS: List[str] = [

    "छ", "तपाईं", "हजुर", "मलाई", "सहयोग", "चाहियो"

]


# ------------------------------------------------------------------
# Keyword lists for scripts shared across multiple languages, or for
# languages written in the Latin alphabet
# ------------------------------------------------------------------
_URDU_KEYWORDS: List[str] = [
    
    "شکریہ", "براہ کرم", "مدد", "مسئلہ", "قیمت",
    
]

_SPANISH_KEYWORDS: List[str] = [
    
    "hola", "como", "gracias", "problema", "ayuda", "quiero",
    
    "necesito", "tengo", "precio", "reembolso", "factura", "por favor"
    
]

_FRENCH_KEYWORDS: List[str] = [

    "bonjour", "merci", "problème", "aide", "comment", "voulez",

    "remboursement", "facture", "prix", "produit", "s'il vous plaît"

]

_GERMAN_KEYWORDS: List[str] = [

    "danke", "bitte", "hilfe", "problem", "hallo", "ich",

    "rückerstattung", "rechnung", "preis", "produkt"

]


def detect_language(text: str) -> str:
    
    """
    Detect the likely language of a customer message using unicode-range
    checks (for distinct scripts) and common keyword matches (for
    languages sharing a script, or written in the Latin alphabet).
    Defaults to "English" if nothing else matches.
    """

    text_lower = text.lower()

    # Devanagari script — Hindi, Marathi, and Nepali all share this range,
    # so use keyword hints to break the tie (see module docstring).
    if any(_DEVANAGARI_RANGE[0] <= c <= _DEVANAGARI_RANGE[1] for c in text):

        if any(word in text for word in _NEPALI_KEYWORDS):

            return "Nepali"

        if any(word in text for word in _MARATHI_KEYWORDS):

            return "Marathi"

        return "Hindi"

    if any(_BENGALI_RANGE[0] <= c <= _BENGALI_RANGE[1] for c in text):

        return "Bengali"

    if any(_GURMUKHI_RANGE[0] <= c <= _GURMUKHI_RANGE[1] for c in text):

        return "Punjabi"

    if any(_GUJARATI_RANGE[0] <= c <= _GUJARATI_RANGE[1] for c in text):

        return "Gujarati"

    if any(_ODIA_RANGE[0] <= c <= _ODIA_RANGE[1] for c in text):

        return "Odia"

    if any(_TAMIL_RANGE[0] <= c <= _TAMIL_RANGE[1] for c in text):

        return "Tamil"

    if any(_TELUGU_RANGE[0] <= c <= _TELUGU_RANGE[1] for c in text):

        return "Telugu"

    if any(_KANNADA_RANGE[0] <= c <= _KANNADA_RANGE[1] for c in text):

        return "Kannada"

    if any(_MALAYALAM_RANGE[0] <= c <= _MALAYALAM_RANGE[1] for c in text):

        return "Malayalam"

    # Arabic script also covers Urdu — check Urdu-specific keywords first,
    # since Urdu borrows heavily from Arabic script but is a distinct language
    if any(_ARABIC_RANGE[0] <= c <= _ARABIC_RANGE[1] for c in text):

        if any(word in text for word in _URDU_KEYWORDS):

            return "Urdu"

        return "Arabic"

    if any(_JAPANESE_RANGE[0] <= c <= _JAPANESE_RANGE[1] for c in text):

        return "Japanese"

    if any(_CHINESE_RANGE[0] <= c <= _CHINESE_RANGE[1] for c in text):

        return "Chinese"

    # Latin-alphabet languages — keyword matching only, since the script
    # itself doesn't distinguish them from English
    if any(word in text_lower for word in _SPANISH_KEYWORDS):

        return "Spanish"

    if any(word in text_lower for word in _FRENCH_KEYWORDS):

        return "French"

    if any(word in text_lower for word in _GERMAN_KEYWORDS):

        return "German"

    return "English"