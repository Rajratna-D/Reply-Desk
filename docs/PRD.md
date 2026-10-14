# Product requirements - ReplyDesk

## Problem

Small sellers who run shops on Instagram and WhatsApp answer the same customer questions all day: price, sizes, stock, delivery, returns, payment. Slow replies lose sales. Many customers write in Hindi, Marathi, or Hinglish, and sellers often reply in a rush with inconsistent details. Generic AI chat tools need the seller to paste in their whole catalogue every time, send customer data to a third party, and tend to make up prices and policies.

## User

Primary: the owner of a small shop (clothing, home bakery, handmade jewellery, and similar) who handles customer chats personally, on a phone or laptop, and is not technical.

Secondary: the developer-user of this repo during the challenge, who needs to demonstrate the tool with several different shops.

## Product in one sentence

Set up your shop once, paste in a customer message, get a ready-to-send reply in the customer's language that only uses your real prices and policies, and runs entirely on your own computer.

## Goals

1. Drafts are correct: facts come only from the seller's data.
2. Drafts match the customer's language and the seller's tone.
3. Setup for a new seller takes about five minutes with no code.
4. Everything runs locally and offline, with a model that can be swapped from a setting.
5. We can measure quality and show the results (see `docs/EVAL_PLAN.md`).

## Non-goals (out of scope)

- Login, accounts, multi-user or cloud hosting of seller data
- WhatsApp or Instagram integration, auto-sending, or reading chats automatically (the customer chat page is a local simulation for demo purposes only)
- Payments, orders, inventory sync, analytics dashboards
- Image understanding (product photos)
- Fine-tuning (possible later as an extra, not part of the core)

## User stories and acceptance criteria

**US1. Set up a shop.**
As a seller, I fill in my shop details, tone, languages, products with prices, and policies.
- A setup page collects shop name, description, tone, default language, supported languages.
- Products can be added by form or by uploading a CSV (columns documented in `docs/CONFIG_SCHEMA.md`) or by importing a config JSON.
- Policies are free-text entries grouped by topic (delivery, returns, payment, hours, ordering, other).
- Saved data persists in the local SQLite database and can be exported as the config JSON.

**US2. Get a drafted reply.**
As a seller, I paste a customer message and get a reply.
- The reply is in the customer's language and script.
- Every number and fact in the reply appears in the seller's data.
- If the data does not cover the question, the reply says the shop will check and get back, and the UI shows a clear "needs your check" flag with the reason.
- Response time is acceptable on the target laptop (target to be measured, see `docs/SETUP.md`). Show a progress indicator while generating.

**US3. Review before sending.**
As a seller, I can edit the draft, copy it, and mark what I did.
- The draft is editable in a text box with a copy button.
- The seller can mark the draft as sent as is, edited, or discarded; this is logged.
- The UI never sends anything.

**US4. Switch shops.**
As a seller (or demo user), I can hold more than one shop and switch between them.
- A shop selector switches the active seller.
- Replies for one shop never use another shop's data.

**US5. See history.**
As a seller, I can see past drafts and what I did with them.
- A history page lists past messages and replies for the selected shop, newest first.

**US6. Swap the model.**
As a developer or seller, I can change the model name in settings and compare.
- Changing `MODEL_NAME` changes the model used, with no code change.
- The app shows which model produced each draft (also stored in the log).

**US7. Evaluate.**
As the developer, I can run a fixed set of test messages and get a results table.
- `python -m eval.run_eval` runs all cases in `eval/questions.json` against a chosen model and writes results to the database and a markdown/CSV report.
- Report includes facts-correct, language-correct, needs-check-correct rates and latency (see `docs/EVAL_PLAN.md`).

**US8. Customer chat simulator and owner inbox (demo-only).**
As a presenter or evaluator, I can demo both the customer experience and shop owner experience side by side in two browser windows on localhost without third-party messaging integrations.
- Customer Chat page: Allows selecting a shop, typing a customer message in English, Hindi, Marathi, or Hinglish, and viewing sent messages and received replies.
- Sending immediately generates a draft with `draft_reply()` and stores it in `reply_log` with `seller_action = NULL` (pending). Customer sees "The shop will reply shortly."
- Customer session remembers its messages in `st.session_state` without creating user accounts or session tables in the database.
- Customer never sees drafts, needs-check flags, or internal shop facts.
- A prominent disclaimer states: "Simulated chat for demo. Not connected to WhatsApp or Instagram."
- Owner Inbox page: Lists pending (`seller_action IS NULL`) drafts for the active shop, newest first, showing customer message, editable draft, needs-check banner with reason, and warnings.
- Owner actions: "Send as is" (marks `sent_as_is`), "Send edited" (marks `edited`, stores `final_reply`), or "Discard" (marks `discarded`).
- When the owner sends, the customer chat shows the reply (`final_reply` if present, else `drafted_reply`). If discarded, the customer sees nothing new.
- Switching shops in the sidebar changes which seller's data is used. Replies for one shop never use another shop's catalogue or policies.

## Quality requirements

- Privacy: the seller's data and customer messages never leave the machine. The app works with the network disabled once the model is downloaded.
- Safety: allergy, health, and legal questions not covered by the data must trigger `needs_check`.
- Reliability: if Ollama is not running or the model is missing, the UI shows a clear message with the fix, and does not crash.
- Simplicity: a first-time user can install and run it from the README in under 15 minutes.

## Success metrics (to be measured, not assumed)

- Facts-correct rate on the eval set
- Needs-check correctness (flags unknown questions, does not flag known ones)
- Language-match rate by language (Hindi and Marathi will likely be weaker; report honestly)
- Median latency per reply on the target laptop
- Cost per reply (electricity estimate) versus a typical paid API price per reply, with the assumptions stated
- Optional: one or more real sellers tried it, with their feedback

## Risks

| Risk | Mitigation |
|---|---|
| Small model writes poor Marathi/Hindi | Compare model sizes in the eval; report results honestly; keep replies short and template-friendly |
| Model invents prices | Strict prompt, structured output, numeric grounding check, `needs_check` fallback, seller always reviews |
| Slow on a 6 GB GPU | Use the smallest model that passes the eval; short prompts; limit context size |
| No real first user | Use clearly labelled fictional sample shops; say so in the post; do not fabricate feedback |
| Scope creep | Follow Non-goals; one milestone at a time |
