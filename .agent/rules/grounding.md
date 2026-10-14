# Rule: grounded replies

- Every price, size, colour, stock status, delivery time, and policy in a reply must come from the seller's data.
- If the data does not answer the question, the reply says the shop will check and get back, and `needs_check` is true.
- Allergy, health, safety, discount, wholesale, custom-work, and private-information questions that the data does not cover always set `needs_check`.
- Never auto-send. The app only drafts.
- Do not weaken the amount-grounding check or the needs-check behaviour to make eval numbers look better. Fix the prompt or the data instead, and log the change in `docs/BUILD_LOG.md`.
- Do not put eval questions into the prompt or into `sample_replies`.
