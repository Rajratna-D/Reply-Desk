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
        "ignore your instructions", "ignore previous instructions",
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
        r"\b(?:phone\s+number|mobile\s+number|contact\s+number|cost\s+price|margin|personal\s+number|address|call\s+me|ignore\s+(?:all\s+|previous\s+|your\s+)?instructions|system\s+prompt|developer\s+instructions)\b",
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


# Precompiled regex patterns for indirect prompt injection defense
PROMPT_INJECTION_PATTERNS = [
    r"\b(?:ignore|disregard|override|bypass|forget)\s+(?:all\s+|previous\s+|your\s+|the\s+|seller\s+)?(?:instructions|rules|guidelines|system|prompt|guardrails|policies)\b",
    r"\bact\s+as\s+(?:a\s+|an\s+|my\s+)?(?:system|developer|unrestricted|jailbroken|evil|new|different|admin\w*|bot|ai)\b",
    r"system\s+prompt",
    r"you\s+are\s+now\s+(?:a\s+|an\s+)?(?:developer|unrestricted|jailbroken|admin\w*)",
    r"<\|im_start\|>",
    r"\[inst\]",
]
PROMPT_INJECTION_REGEX = re.compile("|".join(PROMPT_INJECTION_PATTERNS), re.IGNORECASE)


def detect_prompt_injection(text: str) -> tuple[bool, str]:
    """Check incoming messages for adversarial system override and jailbreak patterns."""
    if not text:
        return False, ""
    match = PROMPT_INJECTION_REGEX.search(text)
    if match:
        return True, "Prompt injection attempt blocked"
    return False, ""


# Precompiled regex patterns for local PII scrubber
CARD_REGEX = re.compile(r"\b(?:\d[ -]*?){13,19}\b")
AADHAAR_REGEX = re.compile(r"\b\d{4}[\s-]??\d{4}[\s-]??\d{4}\b")
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_REGEX = re.compile(r"(?:\+91[\s-]?)?[6-9]\d{9}\b")

# Protect order IDs, AWB courier tracking, UPI UTRs, and invoice numbers from accidental redaction
ORDER_TRACKING_REGEX = re.compile(
    r"(?i)(?:#|\b(?:order|awb|utr|tracking|ref|invoice|id))\s*[:#-]?\s*([0-9A-Za-z_-]{4,30})\b"
)


def redact_pii(text: str) -> tuple[str, list[str]]:
    """Mask credit cards, Aadhaar IDs, emails, and phone numbers before storage and prompting.

    Preserves order IDs, courier tracking numbers, and UPI UTR references.
    """
    if not text:
        return "", []

    detected: list[str] = []

    # Preserve order/tracking identifiers with placeholders
    preserved_tokens: list[str] = []

    def _preserve_match(match: re.Match[str]) -> str:
        preserved_tokens.append(match.group(0))
        return f"__RD_PRESERVED_TOKEN_{len(preserved_tokens) - 1}__"

    protected_text = ORDER_TRACKING_REGEX.sub(_preserve_match, text)
    redacted = protected_text

    if CARD_REGEX.search(redacted):
        detected.append("card")
        redacted = CARD_REGEX.sub("[REDACTED_CARD]", redacted)

    if AADHAAR_REGEX.search(redacted):
        detected.append("id")
        redacted = AADHAAR_REGEX.sub("[REDACTED_ID]", redacted)

    if EMAIL_REGEX.search(redacted):
        detected.append("contact_email")
        redacted = EMAIL_REGEX.sub("[REDACTED_CONTACT]", redacted)

    if PHONE_REGEX.search(redacted):
        detected.append("contact_phone")
        redacted = PHONE_REGEX.sub("[REDACTED_CONTACT]", redacted)

    # Restore preserved order/tracking tokens
    for idx, token in enumerate(preserved_tokens):
        redacted = redacted.replace(f"__RD_PRESERVED_TOKEN_{idx}__", token)

    return redacted, detected


# Patterns for numeric claims in drafts
PERCENT_REGEX = re.compile(r"\b\d+\s*%", re.IGNORECASE)
TIME_WINDOW_REGEX = re.compile(
    r"\b\d+\s*(?:hours?|days?|weeks?|months?|घंटे?|दिन|दिवस)\b",
    re.IGNORECASE,
)


def verify_numeric_grounding(
    draft_reply: str,
    source_context: str,
    customer_query: str = "",
) -> dict[str, Any]:
    """Verify whether numeric claims (currencies, discounts, time windows) exist in source data.

    Whitelists numbers and time windows present in customer_query, and allows small integer
    multiples (2x to 10x) of base product prices for quantity inquiries.

    Returns:
        dict with 'is_grounded': bool, 'unverified_numbers': list[str]
    """
    if not draft_reply:
        return {"is_grounded": True, "unverified_numbers": []}

    unverified: list[str] = []
    norm_context = normalize_digits(source_context).lower()
    norm_query = normalize_digits(customer_query).lower() if customer_query else ""

    # 1. Currency amounts and raw digits in context
    context_amounts = set(extract_amounts(source_context))
    raw_context_numbers = set(re.findall(r"\b\d+\b", norm_context))

    # Whitelist small integer multiples (2x through 10x) of base prices
    whitelisted_multiples: set[int] = set()
    for base_price in context_amounts:
        for mult in range(2, 11):
            whitelisted_multiples.add(base_price * mult)

    # Whitelist numbers and amounts echoed from customer's query
    query_amounts = set(extract_amounts(customer_query)) if customer_query else set()
    raw_query_numbers = set(re.findall(r"\b\d+\b", norm_query)) if customer_query else set()

    reply_amounts = extract_amounts(draft_reply)
    for amt in reply_amounts:
        is_known = (
            amt in context_amounts
            or amt in whitelisted_multiples
            or str(amt) in raw_context_numbers
            or amt in query_amounts
            or str(amt) in raw_query_numbers
        )
        if not is_known:
            unverified.append(f"₹{amt}")

    # 2. Percentages
    for pct in PERCENT_REGEX.findall(draft_reply):
        pct_norm = normalize_digits(pct).lower().replace(" ", "")
        in_ctx = pct_norm in norm_context.replace(" ", "")
        in_query = pct_norm in norm_query.replace(" ", "") if norm_query else False
        if not in_ctx and not in_query:
            unverified.append(pct)

    # 3. Time windows
    for tw in TIME_WINDOW_REGEX.findall(draft_reply):
        digits = re.search(r"\d+", normalize_digits(tw))
        if digits:
            d_str = digits.group(0)
            if d_str not in raw_context_numbers and d_str not in raw_query_numbers:
                unverified.append(tw)

    return {
        "is_grounded": len(unverified) == 0,
        "unverified_numbers": unverified,
    }
