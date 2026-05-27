"""
Stage 2B — Per-theme synthesis via Claude API.

Reads stage2a_input.json, batches 3-4 themes per call, and asks Claude to
produce structured PM-level insights for each theme.

Skips themes with fewer than 5 total substantive reviews.
Output: themes_report.json
"""

import json
import time
from pathlib import Path
import os

import anthropic

def _load_env(env_path: Path) -> None:
    try:
        text = env_path.read_text().strip()
    except FileNotFoundError:
        return
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            key, val = k.strip(), v.strip()
            if not os.environ.get(key):
                os.environ[key] = val

_load_env(Path(__file__).parent.parent / ".env")

# ── Config ────────────────────────────────────────────────────────────────────

DATA_DIR     = Path(__file__).parent.parent / "data"
MODEL        = "claude-opus-4-7"
BATCH_SIZE   = 4          # themes per API call
MIN_REVIEWS  = 5          # skip themes below this total
INPUT_JSON   = DATA_DIR / "stage2a_input.json"
OUTPUT_JSON  = DATA_DIR / "themes_report.json"

APPS = ["lidl-plus", "rewe"]

PM_ACTIONS = [
    "fix-stability-bug",
    "redesign-flow",
    "build-new-feature",
    "clarify-comms",
    "research-deeper",
]

# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are a senior product manager synthesizing app store review data for two
German grocery apps: Lidl Plus and REWE.

You receive batches of themes. For each theme you have:
- Per-app review counts, average ratings, and severity distributions
- Up to 5 representative reviews per app (in German — authenticity preserved)

Your output must be in English (quotes may remain in German).

For each theme return exactly one object in the "results" array with these fields:

theme (string) — echo back the theme name exactly as given

theme_description (string)
  One sentence in PM language describing what this theme covers.
  Example: "Users cannot complete the login flow, blocking access to all
  personalised features."

lidl_summary (string)
  One sentence summarising the Lidl Plus user experience for this theme.
  If there are zero Lidl Plus reviews, write "No Lidl Plus feedback in dataset."

rewe_summary (string)
  One sentence summarising the REWE user experience for this theme.
  If there are zero REWE reviews, write "No REWE feedback in dataset."

pm_action (string — pick EXACTLY ONE)
  fix-stability-bug   → crashes, hangs, data loss, payment failures
  redesign-flow       → confusing UX, multi-step friction, unclear navigation
  build-new-feature   → users want something that doesn't exist yet
  clarify-comms       → users confused by messaging, labels, or policy
  research-deeper     → mixed signals or unclear root cause

ab_test_idea (string)
  One concrete, testable hypothesis a PM could run next sprint.
  Format: "Test whether [intervention] [reduces/increases] [metric] by [target]."
  Keep it specific and actionable.

strategic_note (string | null)
  For ASYMMETRIC themes only: one sentence on what the imbalance means
  strategically — is this a competitive gap, a platform-specific bug, a
  feature the competitor hasn't built yet?
  Set to null for symmetric themes.

Guidelines
- Be precise and opinionated — avoid vague hedge language ("may", "could potentially")
- Base everything on the data given; do not invent complaints not in the reviews
- Keep each field to one sentence (ab_test_idea may be two if needed for clarity)
- Return results in the SAME ORDER as the themes are presented in the input
"""

# ── JSON schema ───────────────────────────────────────────────────────────────

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "theme":             {"type": "string"},
                    "theme_description": {"type": "string"},
                    "lidl_summary":      {"type": "string"},
                    "rewe_summary":      {"type": "string"},
                    "pm_action":         {"type": "string", "enum": PM_ACTIONS},
                    "ab_test_idea":      {"type": "string"},
                    "strategic_note":    {"anyOf": [{"type": "string"}, {"type": "null"}]},
                },
                "required": [
                    "theme", "theme_description", "lidl_summary", "rewe_summary",
                    "pm_action", "ab_test_idea", "strategic_note",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["results"],
    "additionalProperties": False,
}

# ── Prompt builder ────────────────────────────────────────────────────────────

def build_user_message(batch: list[dict]) -> str:
    parts = [f"Synthesise the following {len(batch)} theme(s).\n"]

    for t in batch:
        signal = t["comparative_signal"]
        dominant = t.get("dominant_app")
        signal_line = (
            f"asymmetric — {dominant} dominates"
            if signal == "asymmetric" and dominant
            else "symmetric"
        )

        parts.append(f"## Theme: {t['theme']}")
        parts.append(f"Signal: {signal_line}\n")

        for app in APPS:
            stats = t["stats"][app]
            reviews = t["representative_reviews"].get(app, [])
            count = stats["count"]
            avg = stats["avg_rating"]
            sev = stats["severity_pct"]

            parts.append(f"### {app} ({count} reviews, avg rating: {avg})")
            if count > 0:
                parts.append(
                    f"Severity: {sev['high']}% high, "
                    f"{sev['medium']}% medium, "
                    f"{sev['low']}% low"
                )
            if not reviews:
                parts.append("(no reviews available)\n")
                continue

            parts.append("")
            for i, r in enumerate(reviews, 1):
                stars = f"★{r['rating']}"
                sev_tag = r["severity"]
                review_text = str(r["review"]).strip()
                line = f'Review {i} [{sev_tag}, {stars}]: "{review_text}"'
                if r.get("feature_request"):
                    line += f'\n  → Feature request: "{r["feature_request"]}"'
                parts.append(line)
            parts.append("")

    return "\n".join(parts)


# ── API call ──────────────────────────────────────────────────────────────────

def synthesise_batch(
    client: anthropic.Anthropic,
    batch: list[dict],
    batch_num: int,
    total_batches: int,
) -> list[dict]:
    themes_str = ", ".join(t["theme"] for t in batch)
    print(f"  [{batch_num:02d}/{total_batches:02d}] {themes_str}")
    print(f"           ", end="", flush=True)

    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
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

    text = next(b.text for b in response.content if b.type == "text")
    results = json.loads(text)["results"]

    usage = response.usage
    print(
        f"✓  cache_read={usage.cache_read_input_tokens} "
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
    raw = json.loads(INPUT_JSON.read_text())

    themes = [
        t for t in raw
        if sum(t["stats"][a]["count"] for a in APPS) >= MIN_REVIEWS
    ]
    dropped = len(raw) - len(themes)
    print(f"Loaded {len(raw)} themes from {INPUT_JSON}")
    print(f"Dropped {dropped} themes with < {MIN_REVIEWS} total reviews")
    print(f"Processing {len(themes)} themes in batches of {BATCH_SIZE}\n")

    client = anthropic.Anthropic()

    batches = [themes[i : i + BATCH_SIZE] for i in range(0, len(themes), BATCH_SIZE)]
    total   = len(batches)
    all_results: list[dict] = []

    for i, batch in enumerate(batches, 1):
        for attempt in range(3):
            try:
                results = synthesise_batch(client, batch, i, total)
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

        if i < total:
            time.sleep(0.5)

    OUTPUT_JSON.write_text(json.dumps(all_results, ensure_ascii=False, indent=2))
    print(f"\n✓  Saved {len(all_results)} theme reports to {OUTPUT_JSON}")

    # ── Quick preview ─────────────────────────────────────────────────────────
    print("\n── Preview ──────────────────────────────────────────────────────────")
    for r in all_results:
        print(f"\n▸ {r['theme']}  [{r['pm_action']}]")
        print(f"  {r['theme_description']}")
        print(f"  Lidl: {r['lidl_summary']}")
        print(f"  REWE: {r['rewe_summary']}")
        print(f"  A/B:  {r['ab_test_idea']}")
        if r.get("strategic_note"):
            print(f"  ★    {r['strategic_note']}")


if __name__ == "__main__":
    main()
