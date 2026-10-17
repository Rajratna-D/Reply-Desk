# Future Upgrade Plan: ReplyDesk

This document outlines the architectural blueprints, technical requirements, and phased roadmaps for post-hackathon enhancements to ReplyDesk, turning it into an end-to-end local commerce operating system for small sellers.

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
                     - Numeric Grounding Verified?
                     - Needs Check == False?
                     - Zero Risk / Bargain Topics?
                     - Zero Injection Signatures?
                                   │
                  ┌────────────────┴────────────────┐
                  ▼                                 ▼
         [ HIGH CONFIDENCE ]              [ COMPLEX / ESCALATE ]
                  │                                 │
         Auto-Pilot Enabled?              [ Immediate Holding Msg ]
             /          \                 "Shop owner will review
         [ YES ]       [ NO ]             and contact shortly"
            │             │                         │
            ▼             ▼                         ▼
   [ Auto-Dispatch ]  [ Queue Draft ]     [ Owner Inbox Queue ]
   Reply sent to buyer  Pending review     Flagged "NEEDS HUMAN"
   Logged as auto_sent  in Owner Inbox     High priority alert
```

### Safety & Gating Criteria
A reply may ONLY be auto-dispatched if it satisfies **all four** conditions:
1. **100% Numeric Grounding:** Every currency amount in the draft strictly matches the shop active catalogue in SQLite.
2. **Model Certainty:** The model returned `needs_check: false` and cited verified facts from the injected context.
3. **Zero Risk Topics:** None of the precompiled risk topic patterns trigger (no discount bargaining, no allergen queries, no custom tailoring, no bulk/reseller requests).
4. **Security & PII Clearance:** No prompt injection signatures, no card/Aadhaar/phone numbers in untrusted customer text, and valid script classification.

If any single condition fails, the system automatically routes the query to **Escalation Mode**:
- **Customer sees:** *"Thank you for your message! Our shop owner will review your request and get back to you shortly."*
- **Owner sees:** High-contrast amber badge `NEEDS HUMAN REVIEW` with the AI suggested draft and the specific escalation reason.

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
   - **Bundle Discounts:** Pre-approved thresholds (e.g. *"Buy 2, get Rs 100 off"* or *"5% off on prepaid UPI orders"*).
   - **Discount Authority Limit:** Maximum permissible discount the model can grant without owner sign-off (e.g. max 5%).
2. **Two-Stage Grounding Verification:**
   - Any counter-offer made by the model must be mathematically verified against `product.min_price`.
   - If a buyer offer is below `min_price`, the model politely explains the handcrafted quality and offers free shipping or a smaller token discount rather than rejecting the customer outright.

---

## 3. Feature: Sentiment & Emotion-Aware Triage

### Problem Statement
Customer inquiries range from enthusiastic purchase intent to extreme frustration (damaged delivery, lost parcel, urgent deadline). Prioritizing inbox queues chronologically can cause angry or high-value inquiries to sit unattended.

### Technical Specification
1. **Multilingual Emotion Classifier:**
   - Classify customer intent into 4 actionable states:
     - `URGENT_COMPLAINT` (Damaged, missing item, delivery dispute): Escalates to Top of Inbox with Red Alert.
     - `BUYING_INTENT` (Ready to pay, asking for UPI/account details): Highlighted in Green to close the sale immediately.
     - `BARGAIN_INQUIRY` (Price negotiation): Yellow Badge with suggested counter-offer.
     - `STANDARD_FAQ` (Size, stock, delivery time): Blue Badge / Auto-Pilot eligible.
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

## 6. Feature: Digital Catalogue Auto-Dispatch (PDF, Lookbooks & Media Cards)

### Problem Statement
Customers frequently ask for the full collection upfront (*"Catalogue bhejo"*, *"Do you have a menu card?"*, *"Send your lookbook"*, *"Share PDF"*). Currently, the assistant summarizes individual items. Merchants want the assistant to instantly attach or link their digital catalogue PDF, brochure link, or product image carousels directly into the chat response.

### Technical Specification
1. **Catalogue Asset Registry in `seller.schema.json`:**
   - Add schema fields for `digital_catalogue_url`, `catalogue_pdf_path`, and `category_lookbooks` (e.g., Cakes, Sourdough, Festive Modaks, Kurtas, Sofas).
2. **Intent Trigger & Media Attachment Dispatch:**
   - Detect broad catalogue requests via regex and semantic classifier (`CATALOGUE_REQUEST`).
   - Automatically inject a clean download link or dispatch the PDF / image document via the messaging connector.
   - Accompany the document with a personalized, friendly note: *"Here is our complete collection for 2026! Feel free to ask if you want custom modifications or custom sizing on any item."*

---

## 7. Feature: Local Customer CRM & Excel Contact Manager with Targeted Promotional Broadcasts

### Problem Statement
Small sellers manually write buyer phone numbers in paper diaries or loose WhatsApp chats. When launching a new festive batch (e.g., Diwali modak gift boxes, seasonal linen kurta drops, or sofa renovation discount weeks), they have no structured way to notify past buyers without getting flagged for spam.

### Technical Specification
1. **Local Customer Registry in SQLite (`customers` table):**
   - Automatically record customer phone numbers, names, preferred language (English / Hindi / Marathi), order history, total spend, and product tags (e.g., `eggless_only`, `sofa_inquiry`, `kurtas`).
   - Two-way export and import with Microsoft Excel (`.xlsx`) and CSV formats for easy merchant editing on desktop.
2. **Targeted Promotional Broadcast Engine:**
   - Merchant selects target customer segments (e.g., *"All buyers who inquired about modaks in the last 6 months"* or *"All customers who purchased over Rs 1,000"*).
   - Generates personalized, warm broadcast messages customized per buyer preferred language using on-device Gemma.
   - **Anti-Spam & Rate-Limiting Guard:** Staggers message dispatches (5 to 10 seconds between contacts) with an automatic opt-out mechanism (*"Reply STOP to unsubscribe"*), protecting the seller phone number from Meta rate-limit bans.

---

## 8. Feature: Merchant Business Analytics & Sales Attribution Dashboard

### Problem Statement
Sellers lack clear visibility into which products drive the most interest, how many inquiries convert to paid sales, and how much total revenue was facilitated by the assistant versus lost to slow follow-ups.

### Technical Specification
1. **Conversation-to-Order Attribution:**
   - Add a one-click *"Mark as Converted"* button in the Owner Inbox with fields for final order value (INR) and payment status.
2. **Interactive Streamlit Business Dashboard:**
   - **Key Financial Metrics:** Total Inquiries Handled, Average Response Latency (seconds), Inquiry-to-Sale Conversion Rate (%), and Total Facilitated Revenue (Rs).
   - **Product Demand Heatmap:** Bar chart of top-inquired catalogue items, frequently requested out-of-stock sizes/flavours, and missed inventory opportunities.
   - **Customer Geography & Peak Hours:** Insights showing peak inquiry hours (e.g., 7 PM to 10 PM) and top customer localities (Baner, Aundh, Kothrud, Viman Nagar).
   - **Guardrail Interceptions:** Audit log of hallucinated prices prevented and suspicious injection attempts blocked.

---

## 9. Feature: Dynamic UPI QR Code Generation & Digital Invoicing

### Problem Statement
When a customer agrees to buy (*"Done, book 1 kg modak"* or *"Finalise the blue 3-seater sofa"*), sellers have to scramble to find their phone, open GPay/PhonePe, screenshot their QR code, and send it. By the time they send it, the buyer gets distracted.

### Technical Specification
1. **Dynamic Bharat UPI Intent Generation:**
   - Automatically generates a dynamic UPI payment string (`upi://pay?pa=shop@upi&pn=ShopName&am=Amount&tn=OrderID`) and on-device QR code image.
   - Embeds the customer order ID and exact total amount into the QR code so incoming payments are auto-reconciled.
2. **Instant Local PDF Receipt / Invoice Generator:**
   - Generates a clean, branded PDF receipt with itemized breakdown, tax/delivery charges, and return policy summary ready to send to the buyer.

---

## 10. Feature: Gentle Cart Recovery & Non-Spam Ghosting Follow-Ups

### Problem Statement
Over 40% of Instagram and WhatsApp shoppers ask for price and shipping details and then stop replying ("ghosting"). Manually following up is awkward and time-consuming.

### Technical Specification
1. **Ghosting Detection:**
   - Detects conversations where the seller provided prices/options but no response was received for 6 to 12 hours.
2. **Soft, Polite Nudge Generation:**
   - Generates a warm, low-pressure follow-up message: *"Hi Priya! Just checking in to see if you would like us to reserve the last eggless blueberry cake for tomorrow batch before pre-orders close?"*
   - Sellers report recovering 15% to 25% of stalled deals with a single well-timed follow-up.

---

## 11. Feature: End-to-End Enterprise API Ecosystem & Webhook Architecture

### Problem Statement
To function as an end-to-end commercial product, ReplyDesk must seamlessly connect with external e-commerce backends, courier dispatch aggregators, and payment gateways through standard, secure REST APIs.

### Technical Specification
1. **Shopify & WooCommerce Inventory Webhook Sync:**
   - Webhook listeners (`/api/webhooks/shopify/inventory`, `/api/webhooks/woocommerce/stock`) that automatically sync inventory changes into SQLite FTS5 in real time.
2. **Automated Courier Dispatch APIs (Shiprocket / Delhivery / Dunzo):**
   - One-click courier booking from the Owner Inbox: creates shipping labels, generates AWB tracking numbers, and automatically dispatches live tracking links to the customer on WhatsApp.
3. **Payment Verification Webhooks (Razorpay / Cashfree / UPI Gateway):**
   - Webhook endpoint (`/api/webhooks/payments/verify`) that confirms successful customer payments and instantly moves orders from "Pending Payment" to "Paid and Processing".
4. **Local Developer REST API:**
   - Standard OpenAPI endpoints allowing third-party tools to interact with ReplyDesk locally:
     - `POST /api/v1/inquire`: Submit inquiry and receive structured draft response.
     - `GET /api/v1/catalogue`: Retrieve active shop products and variants.
     - `POST /api/v1/broadcast`: Enqueue segmented promotional messages.
     - `GET /api/v1/analytics/summary`: Export real-time business telemetry metrics.

---

## Phased Implementation Roadmap

| Phase | Milestone | Primary Modules Affected | Target Timeline |
|---|---|---|---|
| **Phase A** | Confidence-Gated Auto-Dispatch & Settings Toggle | `engine/service.py`, `ui/customer_chat_page.py`, `ui/settings_page.py` | Week 1 Post-Hackathon |
| **Phase B** | Negotiation Rules & Floor Price Grounding | `config/seller.schema.json`, `engine/guardrails.py`, `engine/prompt.py` | Week 2 Post-Hackathon |
| **Phase C** | Sentiment-Prioritized Owner Inbox Queue | `engine/service.py`, `ui/inbox_page.py` | Week 3 Post-Hackathon |
| **Phase D** | WhatsApp Cloud API Webhook Integration | `connectors/whatsapp.py`, `app.py` | Week 4 Post-Hackathon |
| **Phase E** | Local Voice Note Transcription (Whisper) | `engine/audio.py`, `ui/customer_chat_page.py` | Month 2 Post-Hackathon |
| **Phase F** | Digital Catalogue Auto-Dispatch & Lookbook Links | `engine/service.py`, `engine/prompt.py`, `ui/settings_page.py` | Month 2 Post-Hackathon |
| **Phase G** | Customer CRM & Excel Broadcast Engine | `engine/crm.py`, `ui/crm_page.py`, `db/schema.sql` | Month 3 Post-Hackathon |
| **Phase H** | Merchant Business Analytics & Sales Dashboard | `ui/analytics_page.py`, `db/schema.sql` | Month 3 Post-Hackathon |
| **Phase I** | Dynamic UPI QR Generator & Gentle Cart Recovery | `engine/payments.py`, `engine/service.py` | Month 4 Post-Hackathon |
| **Phase J** | Courier Dispatch & Payment Webhooks (Shiprocket/Razorpay) | `connectors/shipping.py`, `connectors/payments.py` | Month 4 Post-Hackathon |
| **Phase K** | Shopify & WooCommerce Inventory Sync Connectors | `connectors/ecommerce.py`, `engine/importer.py` | Month 5 Post-Hackathon |
