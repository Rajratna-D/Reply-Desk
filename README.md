# ReplyDesk

A local-first assistant that drafts customer replies for small sellers, in English, Hindi, Marathi, and Hinglish. Set up your shop once; paste a customer message; get a draft that only uses your real prices and policies. Everything runs on your own computer with an open-weight model.

Built for the DEV / MLH Hacktoberfest 2026 Open-Source AI Challenge, Week 2 ("Side Hustle").

> Status: documentation and design pack. Code is built milestone by milestone following `docs/TASKS.md`.

## Docs

Start with `AGENTS.md`, then `docs/`:

- `CHALLENGE.md`: what the challenge asks for
- `PRD.md`: product requirements
- `SYSTEM_DESIGN.md`: system design
- `ARCHITECTURE.md`: modules and interfaces
- `DBMS.md`: database design
- `CONFIG_SCHEMA.md`: seller config format
- `PROMPTS.md`: prompts and output format
- `EVAL_PLAN.md`: how quality is measured
- `TASKS.md`: milestones and dates
- `SETUP.md`: hardware and model setup
- `BUILD_LOG.md`: running log used for the write-up

## Sample data

`config/` holds three fictional sample shops (clothing, home bakery, handmade jewellery). They are invented for testing. `eval/questions.json` holds the test messages.

## Limitations (keep this section honest)

- Drafts are suggestions. A person must review every reply before it is sent.
- Small local models can make mistakes, especially in Marathi and Hindi. Results are reported in `docs/BUILD_LOG.md`.
- No real customer data is included.

## Commits after the challenge deadline

None yet. If any are made after 18 Oct 2026 11:59 PM PDT they must be listed here.

## License

To be decided by the author. Gemma models are used under Google's Gemma license terms; check them before distributing the model.
