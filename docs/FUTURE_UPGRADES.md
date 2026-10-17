# Future Upgrade Plan: ReplyDesk

This document outlines the architectural blueprints, technical requirements, and phased roadmaps for post-hackathon enhancements to ReplyDesk.

---

## 1. Feature: Confidence-Gated Auto-Dispatch (Auto-Pilot Mode)

### Problem Statement
Currently, ReplyDesk operates strictly in a **Review-First** model where every generated draft queues in the Owner Inbox for manual approval. While this ensures 100% human oversight, small merchants who receive 50 to 100 repetitive queries daily (e.g., standard price checks, business hours, delivery timelines) want verified standard replies sent instantly, while escalating ambiguous, policy-sensitive, or bargaining queries to the seller.

### Architecture Overview

```
                                [ Customer Message ]
                                         │
                                         ▼
                             [ engine.service.draft_reply ]
                                         │
                                         ▼
                            [ Confidence & Safety Gate ]
                            ├── Numeric Grounding Verified?
                            ├── Needs Check == False?
                            ├── Zero Risk / Bargain Topics?
                            └── Zero Injection Signatures?
                                         │
                        ┌────────────────┴────────────────┐
                        ▼                                 ▼
               [ HIGH CONFIDENCE ]              [ COMPLEX / ESCALATE ]
                        │                                 │
           ┌────────────┴────────────┐                    ▼
           │ Auto-Pilot Enabled?     │          [ Immediate Holding Msg ]
           ▼                         ▼          "Shop owner will review
       [ YES ]                    [ NO ]         and contact shortly"
          │                          │                    │
          ▼                          ▼                    ▼
   [ Auto-Dispatch ]          [ Queue Draft ]     [ Owner Inbox Queue ]
   Reply sent to buyer        Pending review      Flagged "NEEDS HUMAN"
   Logged as "auto_sent"      in Owner Inbox      High priority alert
```

### Safety & Gating Criteria
A reply may ONLY be auto-dispatched if it satisfies **all four** conditions:
1. **100% Numeric Grounding:** Every currency amount in the draft strictly matches the shop's active catalogue in SQLite.
2. **Model Certainty:** The model returned `needs_check: false` and cited verified facts from the injected context.
3. **Zero Risk Topics:** None of the precompiled risk topic patterns trigger (no discount bargaining, no allergen queries, no custom tailoring, no bulk/reseller requests).
4. **Security & PII Clearance:** No prompt injection signatures, no card/Aadhaar/phone numbers in untrusted customer text, and valid script classification.

If any single condition fails, the system automatically routes the query to **Escalation Mode**:
- **Customer sees:** *"Thank you for your message! Our shop owner will review your request and get back to you shortly."*
- **Owner sees:** High-contrast amber badge `⚠️ NEEDS HUMAN REVIEW` with the AI suggested draft and the specific escalation reason.

### Planned Database Schema Updates
```sql
-- In db/schema.sql (migration to user_version = 2)
ALTER TABLE sellers ADD COLUMN auto_pilot_enabled INTEGER NOT NULL DEFAULT 0;
ALTER TABLE sellers ADD COLUMN custom_holding_message TEXT DEFAULT 'Thank you for reaching out! Our shop owner will review your inquiry and get back to you shortly.';

-- Supported values for reply_log.seller_action:
-- 'sent_as_is', 'sent_edited', 'discarded', 'auto_sent'
```

---

## 2. Feature: Dynamic Bargaining & Negotiation Engine

### Problem Statement
In Indian social commerce, buyers frequently negotiate (*"Bhai 700 me doge kya?"*, *"Can I get 20% off?"*). Currently, ReplyDesk either holds a strict fixed-price line or escalates. Merchants want the ability to define flexible, pre-approved discounting boundaries so the AI can negotiate within safe parameters.

### Technical Specification
1. **Merchant-Defined Negotiation Rules:**
   - **Floor Price (`min_price`):** The absolute minimum price an item can be sold for.
   - **Bundle Discounts:** Pre-approved thresholds (e.g. *"Buy 2, get ₹100 off"* or *"5% off on prepaid UPI orders"*).
   - **Discount Authority Limit:** Maximum permissible discount the model can grant without owner sign-off (e.g. max 5%).
2. **Two-Stage Grounding Verification:**
   - Any counter-offer made by the model must be mathematically verified against `product.min_price`.
   - If a buyer's offer is below `min_price`, the model politely explains the handcrafted quality and offers free shipping or a smaller token discount rather than rejecting the customer outright.

---

## 3. Feature: Sentiment & Emotion-Aware Triage

### Problem Statement
Customer inquiries range from enthusiastic purchase intent to extreme frustration (damaged delivery, lost parcel, urgent deadline). Prioritizing inbox queues chronologically can cause angry or high-value inquiries to sit unattended.

### Technical Specification
1. **Multilingual Emotion Classifier:**
   - Classify customer intent into 4 actionable states:
     - `URGENT_COMPLAINT` (Damaged, missing item, delivery dispute) -> Escalates to Top of Inbox with Red Alert.
     - `BUYING_INTENT` (Ready to pay, asking for UPI/account details) -> Highlighted in Green to close the sale immediately.
     - `BARGAIN_INQUIRY` (Price negotiation) -> Yellow Badge with suggested counter-offer.
     - `STANDARD_FAQ` (Size, stock, delivery time) -> Blue Badge / Auto-Pilot eligible.
2. **De-escalation Empathy Anchors:**
   - Enforce customer de-escalation guidelines in prompts for angry buyers: immediate acknowledgment of inconvenience, clear instructions on return unboxing videos, and personal owner follow-up commitments.

---

## 4. Feature: Direct Messaging Webhooks (WhatsApp & Instagram)

### Problem Statement
ReplyDesk currently runs an interactive split-screen simulation for demo and hackathon evaluation. Production deployment requires live connectivity to messaging channels.

### Technical Specification
1. **WhatsApp Business Cloud API Connector:**
   - FastAPI webhook receiver (`/api/webhooks/whatsapp`) to receive inbound message payloads.
   - Verification handshake handling (`hub.verify_token`, `hub.challenge`).
   - Outbound dispatch via official Cloud API `POST /v18.0/{phone_number_id}/messages`.
2. **Instagram Messaging Graph API Connector:**
   - Inbound webhook processing for Direct Messages (DMs) and Story mentions.
3. **Local Encryption & Privacy Guard:**
   - Messages arriving from webhooks are scrubbed of PII (`engine/guardrails.py`) before persistence in the local SQLite database.

---

## 5. Feature: Multimodal & Voice-to-Text Support

### Problem Statement
Many Indian buyers prefer sending WhatsApp voice notes or photos of garments rather than typing long inquiries.

### Technical Specification
1. **Local Audio Transcription via Whisper (quantized GGUF / tiny.en / tiny.indic):**
   - Inbound voice notes are transcribed 100% locally on-device without cloud speech APIs.
   - Script detection and language normalization into text for `engine.service.draft_reply()`.
2. **Visual Product Grounding:**
   - Buyer sends a photo of a dress asking *"Do you have this in green?"*.
   - Local vision model (e.g. Gemma 3 / 4 Vision) matches image features against product catalogue photos in `data/images/`.

---

## Phased Implementation Roadmap

| Phase | Milestone | Primary Modules Affected | Target Timeline |
|---|---|---|---|
| **Phase A** | Confidence-Gated Auto-Dispatch & Settings Toggle | `engine/service.py`, `ui/customer_chat_page.py`, `ui/settings_page.py` | Week 1 Post-Hackathon |
| **Phase B** | Negotiation Rules & Floor Price Grounding | `config/seller.schema.json`, `engine/guardrails.py`, `engine/prompt.py` | Week 2 Post-Hackathon |
| **Phase C** | Sentiment-Prioritized Owner Inbox Queue | `engine/service.py`, `ui/inbox_page.py` | Week 3 Post-Hackathon |
| **Phase D** | WhatsApp Cloud API Webhook Integration | `connectors/whatsapp.py`, `app.py` | Week 4 Post-Hackathon |
| **Phase E** | Local Voice Note Transcription (Whisper) | `engine/audio.py`, `ui/customer_chat_page.py` | Month 2 Post-Hackathon |
