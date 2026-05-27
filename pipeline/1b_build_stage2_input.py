"""
Stage 2A — Pure Python, no API calls.

For each theme (substantive reviews only), computes per-app stats and selects
up to 5 representative reviews per app using a diversity strategy:
  slot 1 — highest-severity review (prefer lowest rating as tiebreaker)
  slot 2 — medium-severity review  (not already picked)
  slot 3 — low-severity review     (not already picked)
  slots 4-5 — reviews with non-null feature_request (not already picked)
  fill — remaining reviews if still under 5

Output: data/stage2a_input.json
"""

import json
from pathlib import Path
from typing import Optional

import pandas as pd

DATA_DIR    = Path(__file__).parent.parent / "data"
INPUT_CSV   = DATA_DIR / "reviews_enriched.csv"
OUTPUT_JSON = DATA_DIR / "stage2a_input.json"

APPS = ["lidl-plus", "rewe"]

REVIEW_FIELDS = [
    "app", "rating", "review", "sentiment",
    "specific_complaint", "feature_request", "severity",
]


# ── Selection helpers ─────────────────────────────────────────────────────────

def _best(pool: pd.DataFrame, severity: str, exclude_ids: set) -> Optional[int]:
    """Return the index of the best review at the given severity level,
    preferring the lowest rating (then longest review) as a tiebreaker.
    Returns None if no candidate exists."""
    candidates = pool[
        (pool["severity"] == severity) & (~pool.index.isin(exclude_ids))
    ]
    if candidates.empty:
        return None
    candidates = candidates.copy()
    candidates["_len"] = candidates["review"].fillna("").str.len()
    candidates = candidates.sort_values(["rating", "_len"], ascending=[True, False])
    return candidates.index[0]


def select_representative(pool: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """Pick up to n diverse reviews from pool."""
    if pool.empty:
        return pool.iloc[0:0]

    selected_ids: set = set()
    order: list = []

    # Slots 1–3: one per severity level
    for sev in ("high", "medium", "low"):
        idx = _best(pool, sev, selected_ids)
        if idx is not None:
            order.append(idx)
            selected_ids.add(idx)

    # Slots 4–5: reviews with a non-null feature_request
    if len(order) < n:
        fr_pool = pool[
            pool["feature_request"].notna()
            & pool["feature_request"].ne("")
            & (~pool.index.isin(selected_ids))
        ].copy()
        fr_pool["_len"] = fr_pool["review"].fillna("").str.len()
        fr_pool = fr_pool.sort_values(["rating", "_len"], ascending=[True, False])
        for idx in fr_pool.index:
            if len(order) >= n:
                break
            order.append(idx)
            selected_ids.add(idx)

    # Fill remaining slots
    if len(order) < n:
        remaining = pool[~pool.index.isin(selected_ids)].copy()
        remaining["_len"] = remaining["review"].fillna("").str.len()
        remaining = remaining.sort_values(["rating", "_len"], ascending=[True, False])
        for idx in remaining.index:
            if len(order) >= n:
                break
            order.append(idx)
            selected_ids.add(idx)

    return pool.loc[order]


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    df = pd.read_csv(INPUT_CSV)

    # Substantive reviews only
    sub = df[df["content_quality"] == "substantive"].copy()

    themes = sorted(sub["primary_theme"].dropna().unique())
    output = []

    for theme in themes:
        theme_df = sub[sub["primary_theme"] == theme]

        stats: dict = {}
        rep_reviews: dict = {}

        for app in APPS:
            app_df = theme_df[theme_df["app"] == app]
            n = len(app_df)

            if n == 0:
                stats[app] = {
                    "count": 0,
                    "avg_rating": None,
                    "severity_pct": {"high": 0, "medium": 0, "low": 0},
                }
                rep_reviews[app] = []
                continue

            stats[app] = {
                "count": n,
                "avg_rating": round(float(app_df["rating"].mean()), 2),
                "severity_pct": {
                    sev: round(len(app_df[app_df["severity"] == sev]) / n * 100, 1)
                    for sev in ("high", "medium", "low")
                },
            }
            selected = select_representative(app_df)
            rep_reviews[app] = selected[REVIEW_FIELDS].to_dict(orient="records")

        # Comparative signal
        lc = stats.get("lidl-plus", {}).get("count", 0)
        rc = stats.get("rewe", {}).get("count", 0)
        min_c = min(lc, rc)
        max_c = max(lc, rc)

        if min_c == 0 or max_c / min_c >= 2.0:
            signal = "asymmetric"
            dominant: Optional[str] = "lidl-plus" if lc >= rc else "rewe"
        else:
            signal = "symmetric"
            dominant = None

        output.append({
            "theme":               theme,
            "comparative_signal":  signal,
            "dominant_app":        dominant,
            "stats":               stats,
            "representative_reviews": rep_reviews,
        })

    OUTPUT_JSON.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"Wrote {len(output)} themes → {OUTPUT_JSON}")

    for entry in output:
        lc = entry["stats"].get("lidl-plus", {}).get("count", 0)
        rc = entry["stats"].get("rewe", {}).get("count", 0)
        print(
            f"  {entry['theme']:<55} "
            f"lidl={lc:>3}  rewe={rc:>3}  {entry['comparative_signal']}"
        )


if __name__ == "__main__":
    main()
