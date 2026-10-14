"""Guardrails for numeric grounding, risk topic alerts, and script detection."""

import re
import unicodedata
from typing import Any

# Map Devanagari numerals to ASCII digits
DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

# Regex to detect rupee/currency patterns
# Matches:
# ₹ 1,200 | ₹1200 | Rs. 899 | Rs 899 | 899 rupees | 899 rs | 1200/- | INR 899 | 899 inr
AMOUNT_REGEX = re.compile(
    r"""
    (?:(?:₹|rs\.?|inr)\s*([0-9०-९]+(?:,[0-9०-९]+)*)(?:\s*/-)?)|
    (?:([0-9०-९]+(?:,[0-9०-९]+)*)\s*(?:/-|rupees?|rs\.?|inr|रुपये|रुपया))
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Risk topic keywords reference (English, Hindi, Marathi, and Hinglish)
RISK_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "allergy_and_health": [
        "allerg", "gluten", "nut", "walnut", "peanut", "vegan", "diabetic",
        "sugar-free", "sugar free", "pregnan", "health", "safe to eat",
        "एलर्जी", "ॲलर्जी", "अलर्जी",
    ],
    "discount_and_bargain": [
        "discount", "bargain", "cheaper", "sasta", "kam karo", "kam kijiye",
        "off", "छूट", "डिस्काउंट", "सूट", "कमी करा",
    ],
    "wholesale_and_bulk": [
        "wholesale", "bulk", "thok", "resell", "reseller",
        "थोक", "घाऊक",
    ],
    "custom_work": [
        "custom", "stitch", "tailor", "customize", "customise", "measure",
        "कस्टम", "शिलाई", "माप",
    ],
    "private_and_sensitive": [
        "phone number", "mobile number", "contact number", "cost price", "margin",
        "personal number", "address", "call me", "ignore instructions",
        "system prompt", "developer instructions",
    ],
}

# Precompiled word-boundary patterns for high-performance and false-positive prevention
RISK_TOPIC_PATTERNS: dict[str, re.Pattern[str]] = {
    "allergy_and_health": re.compile(
        r"\b(?:allerg\w*|gluten|nuts?|walnuts?|peanuts?|vegan|diabetic|sugar[-\s]free|pregnan\w*|health\w*|safe\s+to\s+eat)\b"
        r"|एलर्जी|ॲलर्जी|अलर्जी",
        re.IGNORECASE,
    ),
    "discount_and_bargain": re.compile(
        r"\b(?:discounts?|bargain\w*|cheaper|sast[aei]|kam\s+(?:karo|kijiye|kardo|karein)|off)\b"
        r"|छूट|डिस्काउंट|सूट|कमी\s+करा",
        re.IGNORECASE,
    ),
    "wholesale_and_bulk": re.compile(
        r"\b(?:wholesale|bulk|thok|resell\w*)\b"
        r"|थोक|घाऊक",
        re.IGNORECASE,
    ),
    "custom_work": re.compile(
        r"\b(?:custom(?:ize|ise|ized|ised|ization|isation|s)?|stitch\w*|tailor\w*|measure\w*)\b"
        r"|कस्टम|शिलाई|माप",
        re.IGNORECASE,
    ),
    "private_and_sensitive": re.compile(
        r"\b(?:phone\s+number|mobile\s+number|contact\s+number|cost\s+price|margin|personal\s+number|address|call\s+me|ignore\s+(?:previous\s+)?instructions|system\s+prompt|developer\s+instructions)\b",
        re.IGNORECASE,
    ),
}


def normalize_digits(text: str) -> str:
    """Translate Devanagari digits to ASCII digits."""
    return text.translate(DEVANAGARI_DIGITS)


def extract_amounts(text: str) -> list[int]:
    """Extract currency amounts from text.

    Recognizes formats like:
    - ₹1,200, ₹ 899, ₹1200/-, 1200/-
    - Rs 899, Rs. 899, 899 rupees, 899 rs, INR 500, 500 inr
    - Devanagari numerals: ₹१,२००, ४०० रुपये
    """
    normalized = normalize_digits(text)
    amounts: list[int] = []

    for match in AMOUNT_REGEX.finditer(normalized):
        amt_str = match.group(1) or match.group(2)
        if amt_str:
            clean_str = amt_str.replace(",", "")
            try:
                amt = int(clean_str)
                amounts.append(amt)
            except ValueError:
                continue

    return amounts


def ungrounded_amounts(reply: str, known: set[int]) -> list[int]:
    """Return all currency amounts mentioned in the reply that do not appear in the known set."""
    found = extract_amounts(reply)
    return [amt for amt in found if amt not in known]


def risk_topics(message: str) -> list[str]:
    """Identify risk topics mentioned in a customer message with word-boundary awareness."""
    matched: list[str] = []
    for topic, pattern in RISK_TOPIC_PATTERNS.items():
        if pattern.search(message):
            matched.append(topic)
    return matched


def script_of(text: str) -> str:
    """Determine the primary script of the text: 'devanagari', 'latin', or 'mixed'."""
    devanagari_count = 0
    latin_count = 0

    for char in text:
        # Check Devanagari Unicode block U+0900 to U+097F
        code = ord(char)
        if 0x0900 <= code <= 0x097F:
            devanagari_count += 1
        elif char.isascii() and char.isalpha():
            latin_count += 1

    if devanagari_count > 0 and latin_count == 0:
        return "devanagari"
    if latin_count > 0 and devanagari_count == 0:
        return "latin"
    if devanagari_count > 0 and latin_count > 0:
        # If one heavily dominates (>80%) we can still classify or return mixed
        total = devanagari_count + latin_count
        if devanagari_count / total >= 0.8:
            return "devanagari"
        if latin_count / total >= 0.8:
            return "latin"
        return "mixed"

    return "latin"
