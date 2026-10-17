"""Script to verify draft_reply across all three sample shops."""

import sys
from pathlib import Path

# Force UTF-8 encoding for console output on Windows
if sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
from engine.service import draft_reply


def main():
    parser = argparse.ArgumentParser(description="Verify draft_reply across sample shops.")
    parser.add_argument("--model", type=str, default=None, help="Model name to evaluate (e.g. gemma4:e2b)")
    args = parser.parse_args()

    test_cases = [
        ("urban_thread", "Hi, how much is the cotton kurti?"),
        ("sweet_crumbs", "How much is a 1 kg chocolate truffle cake?"),
        ("kalakruti_jewels", "What is the price of the jhumka?"),
    ]

    target_desc = args.model or "default config model"
    print(f"Verifying draft_reply on all three sample shops (Model: {target_desc}):\n" + "=" * 50)
    for slug, message in test_cases:
        print(f"\n[Shop: {slug}]")
        print(f"Customer Message: {message}")
        try:
            draft = draft_reply(slug, message, model=args.model)
            print(f"Drafted Reply:   {draft.reply}")
            print(f"Detected Lang:   {draft.language}")
            print(f"Needs Check:     {draft.needs_check}")
            if draft.reason:
                print(f"Reason:          {draft.reason}")
            print(f"Latency:         {draft.latency_ms} ms")
        except Exception as e:
            print(f"ERROR: {e}")
            sys.exit(1)

    print("\n" + "=" * 50)
    print("All three sample shops drafted replies successfully!")


if __name__ == "__main__":
    main()
