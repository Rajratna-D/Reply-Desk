# Evaluation plan

Goal: measure, honestly, whether drafted replies are correct, in the right language, and flag what they do not know. The results feed the write-up (the "why open innovation matters" section and the technical execution score).

## Dataset

File: `eval/questions.json`. Each case is one customer message for one of the three sample shops.

```json
{
  "id": "UT-01",
  "shop": "urban_thread",
  "language": "en",
  "category": "price",
  "split": "dev",
  "message": "customer text",
  "must_include": [["899"]],
  "must_not_include": [],
  "expect_needs_check": false,
  "notes": "why this case exists"
}
```

- `language`: language of the customer message (`en`, `hi`, `mr`, `hinglish`).
- `category`: `price`, `stock`, `delivery`, `returns`, `payment`, `hours`, `ordering`, `allergen`, `custom`, `discount`, `safety`.
- `split`: `dev` or `test`. Tune prompts and guardrails on `dev` cases only. Run `test` cases sparingly, after tuning, so results are not inflated by tuning on the same questions.
- `must_include`: list of groups. Each group is a list of acceptable alternatives (any one must appear). Every group must be satisfied. Example: `[["899"], ["S", "size"]]`.
- `must_not_include`: strings that must not appear (case-insensitive).
- `expect_needs_check`: whether the model should flag the case.

The dataset is small (25 cases), so report counts such as `21/25`, not only percentages, and do not over-interpret small differences between models.

## Scoring

Per case, three automatic checks and one manual score.

1. **facts_ok.** Normalize the reply: lowercase, remove commas inside numbers, convert Devanagari digits to ASCII. Every `must_include` group has at least one alternative present, and no `must_not_include` string is present. For needs-check cases with no `must_include`, this means only that nothing forbidden appears.
2. **needs_check_ok.** The returned `needs_check` equals `expect_needs_check`.
3. **language_ok.** Script check on the reply:
   - `en` and `hinglish`: no Devanagari characters.
   - `hi` and `mr`: at least 50% of letters are Devanagari (shop names, SKUs, and units in Latin letters are allowed).
   Also record whether the model's own `language` label matches (`language_label_ok`), reported separately.
4. **tone_score (manual, 1 to 5).** Does it sound like the shop's configured tone and read naturally? Score at least 10 replies per model. For Hindi and Marathi, also note by eye whether the replies are in the right language (Hindi versus Marathi cannot be checked by script alone) and whether the grammar is acceptable. If you cannot judge Marathi yourself, ask a native speaker and say so in the post.
5. **pass.** A case passes when `facts_ok`, `needs_check_ok`, and `language_ok` are all true.

Also record `latency_ms`, `prompt_tokens`, and `output_tokens` per case (Ollama returns token counts in its response).

## Procedure

1. Import the three sample shops into a temporary database (the eval never touches real data).
2. For each model under test, run all cases: `python -m eval.run_eval --model <tag> --notes "..."`.
3. Read every failure by hand. Classify each as prompt problem, data problem, guardrail gap, or model-size limit.
4. Fix prompt/guardrail problems using `dev` cases only. Re-run.
5. Run `test` cases once per model for the reported numbers.
6. Repeat for each model size you want to compare (at least two).
7. Record everything in `docs/BUILD_LOG.md`.

Run each configuration once for reporting. If time allows, run twice and note whether results changed (temperature is low but outputs can still vary slightly).

## Report format

For each model, a table:

| Slice | Cases | facts_ok | needs_check_ok | language_ok | pass | median latency |
|---|---|---|---|---|---|---|
| All | | | | | | |
| English | | | | | | |
| Hindi | | | | | | |
| Marathi | | | | | | |
| Hinglish | | | | | | |
| dev | | | | | | |
| test | | | | | | |

Then a short list of the most instructive failures with the message, the reply, and the diagnosis. Judges and readers tend to trust honest failures more than a perfect table.

## Model comparison (the "swap models" argument)

Compare at least two open-weight sizes on the same cases. Report quality, latency, and whether it fits in VRAM (`ollama ps`). The point: switching models is a one-line setting change, and the trade-off between size, quality, and speed is visible.

An optional comparison against a closed model is only worth including if you already have free access, and must use exactly the same cases and scoring. Do not claim anything about closed models that you did not measure.

## Cost per reply

Local cost is electricity only. Estimate it transparently:

- Measure GPU power during generation: `nvidia-smi --query-gpu=power.draw --format=csv -l 1`. Note that it excludes CPU, screen, and the rest of the laptop; say so, or estimate total draw and label it an assumption.
- `energy_kWh = average_watts * seconds_per_reply / 3600 / 1000`
- `cost_inr = energy_kWh * tariff_inr_per_kWh`. Look up your actual electricity tariff and cite it.
- For comparison with a paid API: `cost = (prompt_tokens * input_price + output_tokens * output_price) / 1,000,000`, using the current published price of a specific named model, cited with the date. Use your measured token counts. If you cannot get a current price, do not include a number.

State all assumptions next to the numbers.

## Offline test

Disable the network, run `draft_reply` for each sample shop, and confirm it works. Record the date and the result. This is evidence for the "runs with no internet" claim.

## Real-user feedback (optional)

If a real seller tries it, record (with their permission): who they are in general terms, what they asked, how many drafts they used, what they edited, what they said, whether they would pay. Do not invent or embellish. If there is no real user, say so in the post.

## Limitations to state in the post

- Small dataset, one author, fictional shops.
- Automatic checks are keyword and script based; they can miss subtle errors and can mark correct replies as wrong when wording differs.
- Hindi and Marathi quality judged by eye.
- Results depend on the model tag, quantization, Ollama version, and hardware. Record them.
