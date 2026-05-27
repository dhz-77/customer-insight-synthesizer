"""
Stage 1 — Per-review structured extraction.

Reads reviews_raw.csv, sends batches of 20 reviews to Claude, and writes
reviews_enriched.csv with the original columns plus:
  is_about_app, primary_theme, sentiment,
  specific_complaint, feature_request, severity
"""

import json
import time
from pathlib import Path

import os

import anthropic
import pandas as pd


def _load_env(env_path: Path) -> None:
    """Minimal .env loader — handles files with no trailing newline."""
    try:
        text = env_path.read_text().strip()
    except FileNotFoundError:
        return
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            # Overwrite if the current value is empty (e.g. shell exported a blank var)
            key, val = k.strip(), v.strip()
            if not os.environ.get(key):
                os.environ[key] = val


_load_env(Path(__file__).parent.parent / ".env")

# ── Config ────────────────────────────────────────────────────────────────────

DATA_DIR   = Path(__file__).parent.parent / "data"
MODEL      = "claude-opus-4-7"
BATCH_SIZE = 20
INPUT_CSV  = DATA_DIR / "reviews_raw.csv"
OUTPUT_CSV = DATA_DIR / "reviews_enriched.csv"

THEMES = [
    "Authentication & login",
    "Coupons & discounts",
    "Search & navigation",
    "Performance & stability",
    "Payment & checkout",
    "Store finder & maps",
    "In-store experience",
    "Privacy & data concerns",
    "Loyalty program mechanics",
    "Push notifications",
    "Onboarding & registration",
    "Other / unclear",
]

# ── System prompt (cached — identical across every batch) ─────────────────────

SYSTEM_PROMPT = """\
You are a product analyst extracting structured insights from app store reviews
for German grocery / retail apps (Lidl Plus and REWE).

For each review you receive, return exactly one JSON object inside the
top-level "results" array. The fields are:

is_about_app (boolean)
  true  → the review is about the app experience (UI, features, bugs,
          performance, login, notifications, checkout, etc.)
  false → the review is purely about the physical store, product prices,
          or brand — nothing that can be fixed in the app

primary_theme (string — pick EXACTLY ONE)
  Authentication & login
  Coupons & discounts
  Search & navigation
  Performance & stability
  Payment & checkout
  Store finder & maps
  In-store experience
  Privacy & data concerns
  Loyalty program mechanics
  Push notifications
  Onboarding & registration
  Other / unclear

  Pick the theme the reviewer spends the most words on. When uncertain,
  prefer the more specific category over "Other / unclear".

sentiment (string)
  "positive" | "neutral" | "negative"

specific_complaint (string | null)
  One concise sentence in German capturing the core issue.
  null → review is positive or contains no identifiable complaint.
  Write in German regardless of the review's original language.

feature_request (string | null)
  One concise sentence in German describing what the user wants added or
  changed. null if no feature request is present.

severity (string)
  "high"   → blocks core functionality (cannot log in, app crashes,
              payment fails, data lost)
  "medium" → significantly degrades the experience but app still works
  "low"    → minor annoyance, cosmetic issue, or review is not about the app

Guidelines
- If is_about_app is false, set severity to "low".
- Positive reviews with no complaint → specific_complaint: null.
- Keep specific_complaint / feature_request under ~20 words each.
- Return results in the SAME ORDER as the input reviews.
"""

# ── JSON schema for structured output ────────────────────────────────────────

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "is_about_app": {
                        "type": "boolean",
                    },
                    "primary_theme": {
                        "type": "string",
                        "enum": THEMES,
                    },
                    "sentiment": {
                        "type": "string",
                        "enum": ["positive", "neutral", "negative"],
                    },
                    "specific_complaint": {
                        "anyOf": [{"type": "string"}, {"type": "null"}],
                    },
                    "feature_request": {
                        "anyOf": [{"type": "string"}, {"type": "null"}],
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                    },
                },
                "required": [
                    "is_about_app",
                    "primary_theme",
                    "sentiment",
                    "specific_complaint",
                    "feature_request",
                    "severity",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["results"],
    "additionalProperties": False,
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def build_user_message(batch: pd.DataFrame) -> str:
    lines = [f"Extract insights for the following {len(batch)} reviews.\n"]
    for i, (_, row) in enumerate(batch.iterrows(), 1):
        review_text = str(row["review"]).strip() if pd.notna(row["review"]) else "(no text)"
        lines.append(
            f"Review {i} (app: {row['app']}, rating: {row['rating']}/5):\n"
            f"{review_text}\n"
        )
    return "\n".join(lines)


def extract_batch(
    client: anthropic.Anthropic,
    batch: pd.DataFrame,
    batch_num: int,
    total_batches: int,
) -> list[dict]:
    """Send one batch to Claude and return a list of extracted dicts."""
    print(f"  [{batch_num:02d}/{total_batches:02d}] {len(batch)} reviews … ", end="", flush=True)

    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                # Cache the system prompt — it's identical across all batches.
                # First batch pays the write premium (~1.25×); every subsequent
                # batch reads at ~0.1× the base input price.
                "cache_control": {"type": "ephemeral"},
            }
        ],
        output_config={
            "format": {
                "type": "json_schema",
                "schema": OUTPUT_SCHEMA,
            }
        },
        messages=[
            {"role": "user", "content": build_user_message(batch)},
        ],
    )

    # With output_config.format the first (and only) content block is always text.
    text = next(b.text for b in response.content if b.type == "text")
    results = json.loads(text)["results"]

    usage = response.usage
    print(
        f"✓  "
        f"cache_read={usage.cache_read_input_tokens} "
        f"cache_write={usage.cache_creation_input_tokens} "
        f"uncached={usage.input_tokens} "
        f"out={usage.output_tokens}"
    )

    if len(results) != len(batch):
        raise ValueError(
            f"Batch {batch_num}: expected {len(batch)} results, got {len(results)}"
        )

    return results


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    df = pd.read_csv(INPUT_CSV)
    print(f"Loaded {len(df)} reviews from {INPUT_CSV}\n")

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    batches = [df.iloc[i : i + BATCH_SIZE] for i in range(0, len(df), BATCH_SIZE)]
    total   = len(batches)
    print(f"Processing {total} batches of up to {BATCH_SIZE} reviews each…")

    all_results: list[dict] = []

    for i, batch in enumerate(batches, 1):
        for attempt in range(3):
            try:
                results = extract_batch(client, batch, i, total)
                all_results.extend(results)
                break
            except anthropic.RateLimitError:
                wait = 60 * (attempt + 1)
                print(f"\n  Rate limited — waiting {wait}s…", flush=True)
                time.sleep(wait)
            except anthropic.APIStatusError as exc:
                if exc.status_code >= 500 and attempt < 2:
                    time.sleep(10)
                else:
                    raise
        else:
            raise RuntimeError(f"Batch {i} failed after 3 attempts.")

        # Polite pause between batches (skip after the last one)
        if i < total:
            time.sleep(0.5)

    # ── Merge & save ──────────────────────────────────────────────────────────
    enriched_cols = pd.DataFrame(all_results)
    output = pd.concat([df.reset_index(drop=True), enriched_cols], axis=1)
    output.to_csv(OUTPUT_CSV, index=False)

    print(f"\n✓  Saved {len(output)} enriched reviews to {OUTPUT_CSV}")
    print(f"   Columns: {output.columns.tolist()}\n")

    print("Theme distribution:")
    print(
        output.groupby(["app", "primary_theme"])
        .size()
        .unstack(fill_value=0)
        .to_string()
    )

    print("\nSentiment distribution:")
    print(output.groupby(["app", "sentiment"]).size().unstack(fill_value=0).to_string())

    print("\nSeverity distribution:")
    print(output.groupby(["app", "severity"]).size().unstack(fill_value=0).to_string())

    not_about_app = (output["is_about_app"] == False).sum()
    print(f"\nReviews flagged as NOT about the app: {not_about_app} ({not_about_app/len(output)*100:.1f}%)")


if __name__ == "__main__":
    main()
