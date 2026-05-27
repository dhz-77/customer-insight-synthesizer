"""
Stage 3 — PM Briefing.

Single API call: reads themes_report.json, produces a structured comparative
briefing written from the Lidl Plus PM perspective for Schwarz Group leadership.

Output: pm_briefing.json
"""

import json
import time
from datetime import datetime, timezone
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

DATA_DIR         = Path(__file__).parent.parent / "data"
MODEL            = "claude-opus-4-7"
INPUT_REPORT     = DATA_DIR / "themes_report.json"
INPUT_STAGE2A    = DATA_DIR / "stage2a_input.json"
OUTPUT_JSON      = DATA_DIR / "pm_briefing.json"

REPORT_META = {
    "perspective": "Lidl Plus Product Team",
    "competitor": "REWE App",
    "data_basis": "432 substantive app store reviews (216 per app), German market, May 2026",
}

# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are a senior product manager at Lidl Plus writing a competitive briefing
for Schwarz Group product leadership.

Tone requirements — non-negotiable:
- Direct and opinionated. "We have a login crisis." Not "there may be login friction."
- Action-oriented. "Ship the email-fallback in two weeks." Not "consider exploring this."
- First-person plural for Lidl (we/our). Third-person for REWE (they/their).
- No academic hedging: ban "potentially", "could possibly", "may suggest", "it appears".

You will receive a structured summary of 13 app themes, each with:
- Per-app stats (review counts, severity distribution, average rating)
- A theme description, per-app summary, suggested PM action, A/B test idea
- A strategic note for asymmetric themes (where one app dominates the other)

Your output is a single JSON object matching the schema exactly.

Field-level guidance:

executive_summary
  3-4 sentences. Lead with the single most urgent finding (the thing leadership
  must act on this week). Then state the biggest competitive opportunity.
  Close with the recommended first move. Zero hedging.

product_health.overall_verdict
  One sentence. Blunt. Is Lidl Plus healthy, stressed, or in crisis?

product_health.critical_issues
  3-5 items ranked by urgency (1 = most urgent). Only include themes where
  Lidl Plus has a real problem (not REWE's problem). Use severity:
    critical → blocks core functionality for large user segments
    serious  → degrades experience significantly, causes churn
    moderate → real friction but workaround exists

product_health.what_users_value
  1-2 sentences. What do users actively praise? What's worth protecting?

competitive_position.where_we_lead
  Areas where Lidl Plus is ahead of REWE. Be honest — if the lead is thin,
  say so. 2-3 items.

competitive_position.where_we_trail
  Areas where REWE is meaningfully ahead or our deficit is larger.
  Be specific about the gap. 2-3 items.

competitive_position.battlegrounds
  Themes where neither app clearly wins and first-mover takes the category.
  1-3 items.

strategic_opportunities
  2-4 time-sensitive windows — either REWE shipped a regression, or a
  category is open, or there's an urgent user need nobody serves. Rank by
  immediacy. Be specific about what the window is and when it closes.

sprint_recommendations
  Top 5 actions ranked by priority. Mix quick wins (effort: low, timeline:
  days/weeks) with strategic bets. Include a specific, measurable A/B test
  hypothesis for each. "app" should be "lidl-plus" for all — we're writing
  Lidl's sprint plan, not REWE's.

methodology
  2-3 sentences. Factual. Note that reviews come from Google Play Store,
  DE market, May 2026; 600 reviews scraped, 432 retained after content-quality
  filtering; themes extracted and enriched via a multi-stage Claude pipeline;
  limitations include single-platform snapshot, no longitudinal data, and
  potential Android/iOS distribution skew.
"""

# ── JSON schema ───────────────────────────────────────────────────────────────

def _issue_item() -> dict:
    return {
        "type": "object",
        "properties": {
            "rank":              {"type": "integer"},
            "theme":             {"type": "string"},
            "severity":          {"type": "string", "enum": ["critical", "serious", "moderate"]},
            "what_is_happening": {"type": "string"},
            "business_impact":   {"type": "string"},
            "user_voice_de":     {"type": "string"},
            "recommended_fix":   {"type": "string"},
            "effort":            {"type": "string", "enum": ["low", "medium", "high"]},
            "timeline":          {"type": "string", "enum": ["days", "weeks", "months"]},
        },
        "required": ["rank", "theme", "severity", "what_is_happening",
                     "business_impact", "user_voice_de", "recommended_fix",
                     "effort", "timeline"],
        "additionalProperties": False,
    }


def _lead_item() -> dict:
    return {
        "type": "object",
        "properties": {
            "area":           {"type": "string"},
            "finding":        {"type": "string"},
            "how_to_protect": {"type": "string"},
        },
        "required": ["area", "finding", "how_to_protect"],
        "additionalProperties": False,
    }


def _trail_item() -> dict:
    return {
        "type": "object",
        "properties": {
            "area":            {"type": "string"},
            "finding":         {"type": "string"},
            "risk_if_ignored": {"type": "string"},
        },
        "required": ["area", "finding", "risk_if_ignored"],
        "additionalProperties": False,
    }


def _battleground_item() -> dict:
    return {
        "type": "object",
        "properties": {
            "area":                   {"type": "string"},
            "situation":              {"type": "string"},
            "first_mover_advantage":  {"type": "string"},
        },
        "required": ["area", "situation", "first_mover_advantage"],
        "additionalProperties": False,
    }


def _opportunity_item() -> dict:
    return {
        "type": "object",
        "properties": {
            "opportunity":              {"type": "string"},
            "why_now":                  {"type": "string"},
            "competitor_vulnerability": {"type": "string"},
            "our_move":                 {"type": "string"},
        },
        "required": ["opportunity", "why_now", "competitor_vulnerability", "our_move"],
        "additionalProperties": False,
    }


def _sprint_item() -> dict:
    return {
        "type": "object",
        "properties": {
            "priority_rank":   {"type": "integer"},
            "app":             {"type": "string", "enum": ["lidl-plus", "rewe"]},
            "action":          {"type": "string"},
            "ab_test":         {"type": "string"},
            "expected_impact": {"type": "string"},
            "effort":          {"type": "string", "enum": ["low", "medium", "high"]},
            "rationale":       {"type": "string"},
        },
        "required": ["priority_rank", "app", "action", "ab_test",
                     "expected_impact", "effort", "rationale"],
        "additionalProperties": False,
    }


OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "executive_summary": {"type": "string"},
        "product_health": {
            "type": "object",
            "properties": {
                "overall_verdict": {"type": "string"},
                "critical_issues": {"type": "array", "items": _issue_item()},
                "what_users_value": {"type": "string"},
            },
            "required": ["overall_verdict", "critical_issues", "what_users_value"],
            "additionalProperties": False,
        },
        "competitive_position": {
            "type": "object",
            "properties": {
                "where_we_lead":  {"type": "array", "items": _lead_item()},
                "where_we_trail": {"type": "array", "items": _trail_item()},
                "battlegrounds":  {"type": "array", "items": _battleground_item()},
            },
            "required": ["where_we_lead", "where_we_trail", "battlegrounds"],
            "additionalProperties": False,
        },
        "strategic_opportunities": {"type": "array", "items": _opportunity_item()},
        "sprint_recommendations":  {"type": "array", "items": _sprint_item()},
        "methodology": {"type": "string"},
    },
    "required": [
        "executive_summary", "product_health", "competitive_position",
        "strategic_opportunities", "sprint_recommendations", "methodology",
    ],
    "additionalProperties": False,
}

# ── Prompt builder ────────────────────────────────────────────────────────────

def build_user_message(themes: list[dict]) -> str:
    lines = [f"Here are the {len(themes)} theme reports. Produce the PM briefing.\n"]

    for t in themes:
        signal = t["comparative_signal"]
        dominant = t.get("dominant_app", "")
        signal_str = f"asymmetric ({dominant} dominates)" if signal == "asymmetric" else "symmetric"

        lines.append(f"### {t['theme']}")
        lines.append(f"PM action: {t['pm_action']}  |  Signal: {signal_str}")
        lines.append(f"Lidl Plus: {t['stats']['lidl-plus']['count']} reviews, "
                     f"avg ★{t['stats']['lidl-plus']['avg_rating']}, "
                     f"{t['stats']['lidl-plus']['severity_pct']['high']}% high-sev")
        lines.append(f"REWE:      {t['stats']['rewe']['count']} reviews, "
                     f"avg ★{t['stats']['rewe']['avg_rating']}, "
                     f"{t['stats']['rewe']['severity_pct']['high']}% high-sev")
        lines.append(f"Description: {t['theme_description']}")
        lines.append(f"Lidl summary: {t['lidl_summary']}")
        lines.append(f"REWE summary: {t['rewe_summary']}")
        lines.append(f"A/B test: {t['ab_test_idea']}")
        if t.get("strategic_note"):
            lines.append(f"Strategic note: {t['strategic_note']}")
        lines.append("")

    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    # Merge synthesis fields (themes_report) with stats/signal (stage2a_input)
    report  = {t["theme"]: t for t in json.loads(INPUT_REPORT.read_text())}
    stage2a = {t["theme"]: t for t in json.loads(INPUT_STAGE2A.read_text())}
    themes = []
    for theme_name, r in report.items():
        s = stage2a.get(theme_name, {})
        themes.append({**r, **{k: v for k, v in s.items() if k not in r}})

    print(f"Loaded {len(themes)} themes (merged report + stage2a stats)")
    print("Sending single synthesis call to Claude…\n")

    client = anthropic.Anthropic()

    for attempt in range(3):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=8192,
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
                    {"role": "user", "content": build_user_message(themes)},
                ],
            )
            break
        except anthropic.RateLimitError:
            wait = 60 * (attempt + 1)
            print(f"Rate limited — waiting {wait}s…")
            time.sleep(wait)
        except anthropic.APIStatusError as exc:
            if exc.status_code >= 500 and attempt < 2:
                time.sleep(10)
            else:
                raise
    else:
        raise RuntimeError("API call failed after 3 attempts.")

    usage = response.usage
    print(
        f"✓  cache_read={usage.cache_read_input_tokens} "
        f"cache_write={usage.cache_creation_input_tokens} "
        f"uncached={usage.input_tokens} "
        f"out={usage.output_tokens}"
    )

    text = next(b.text for b in response.content if b.type == "text")
    briefing = json.loads(text)

    # Inject report_meta from Python (fixed values, no need to ask Claude)
    briefing["report_meta"] = {
        **REPORT_META,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    OUTPUT_JSON.write_text(json.dumps(briefing, ensure_ascii=False, indent=2))
    print(f"✓  Saved briefing to {OUTPUT_JSON}\n")

    # ── Preview ───────────────────────────────────────────────────────────────
    print("── Executive Summary ────────────────────────────────────────────────")
    print(briefing["executive_summary"])

    print("\n── Product Health ───────────────────────────────────────────────────")
    print(f"Verdict: {briefing['product_health']['overall_verdict']}")
    print(f"\nCritical issues ({len(briefing['product_health']['critical_issues'])}):")
    for issue in briefing["product_health"]["critical_issues"]:
        print(f"  #{issue['rank']} [{issue['severity'].upper()}] {issue['theme']}")
        print(f"     Fix: {issue['recommended_fix']}")
        print(f"     Effort: {issue['effort']} / Timeline: {issue['timeline']}")

    print("\n── Competitive Position ─────────────────────────────────────────────")
    print("We lead:")
    for item in briefing["competitive_position"]["where_we_lead"]:
        print(f"  + {item['area']}: {item['finding']}")
    print("We trail:")
    for item in briefing["competitive_position"]["where_we_trail"]:
        print(f"  - {item['area']}: {item['finding']}")
    print("Battlegrounds:")
    for item in briefing["competitive_position"]["battlegrounds"]:
        print(f"  ~ {item['area']}: {item['situation']}")

    print("\n── Sprint Recommendations ───────────────────────────────────────────")
    for rec in briefing["sprint_recommendations"]:
        print(f"  #{rec['priority_rank']} [{rec['effort']}] {rec['action']}")


if __name__ == "__main__":
    main()
