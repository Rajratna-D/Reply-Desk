"""Tests for numeric grounding, amount extraction, risk topics, and script detection."""

from engine.guardrails import (
    extract_amounts,
    risk_topics,
    script_of,
    ungrounded_amounts,
)


def test_extract_amounts():
    text1 = "The kurti is ₹899 and shipping is ₹ 60."
    assert extract_amounts(text1) == [899, 60]

    text2 = "Total price is Rs. 1,499 (or 1499/-) plus 50 rs delivery."
    assert extract_amounts(text2) == [1499, 1499, 50]

    # Devanagari numerals
    text3 = "किंमत ₹१,२०० आहे आणि डिलिव्हरी ₹५०."
    assert extract_amounts(text3) == [1200, 50]

    # Free text without amounts
    text4 = "No prices mentioned here."
    assert extract_amounts(text4) == []


def test_ungrounded_amounts():
    known = {899, 1499, 60}
    reply_valid = "Yes, the kurti is ₹899 and delivery is ₹60."
    assert ungrounded_amounts(reply_valid, known) == []

    reply_hallucinated = "The kurti is ₹750 and special packing is ₹120."
    assert ungrounded_amounts(reply_hallucinated, known) == [750, 120]


def test_risk_topics():
    # Allergy
    assert "allergy_and_health" in risk_topics("Does the brownie have walnuts or nuts?")
    assert "allergy_and_health" in risk_topics("Is this gluten free?")
    assert "allergy_and_health" in risk_topics("मला शेंगदाण्याची ॲलर्जी आहे.")

    # Discount / bargaining
    assert "discount_and_bargain" in risk_topics("Can I get a discount or 20% off?")
    assert "discount_and_bargain" in risk_topics("kuch sasta rate milega kya?")

    # Wholesale
    assert "wholesale_and_bulk" in risk_topics("Do you sell wholesale / bulk?")
    assert "wholesale_and_bulk" in risk_topics("thok me kitna padega?")

    # Custom work
    assert "custom_work" in risk_topics("Can you stitch a custom size?")
    assert "custom_work" in risk_topics("कस्टम डिझाईन मिळेल का?")

    # Sensitive
    assert "private_and_sensitive" in risk_topics("What is the owner's phone number?")

    # False positive prevention (word boundary checks)
    assert risk_topics("Can you deliver to our office in 10 minutes?") == []
    assert risk_topics("Do you have coffee cake or donuts?") == []
    assert risk_topics("I am a happy customer looking for sarees.") == []


def test_script_of():
    assert script_of("Hello, how much is this kurti?") == "latin"
    assert script_of("कुर्ती की कीमत क्या है?") == "devanagari"
    assert script_of("हे उत्पादन उपलब्ध आहे का?") == "devanagari"
    assert script_of("kurti ka price kitna hai ji?") == "latin"
