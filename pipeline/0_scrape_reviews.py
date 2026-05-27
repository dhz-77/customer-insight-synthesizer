"""
Pull recent Google Play reviews for Lidl Plus and REWE.

Source: Google Play Store (Android) via google-play-scraper.
Note: Google Play reviews have no title field — the column is kept in the
output schema (set to "") so downstream code expecting the iTunes schema
does not break.
"""
from google_play_scraper import reviews, Sort
import pandas as pd
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def scrape_app(app_name: str, app_id: str, lang: str = "de", country: str = "de", how_many: int = 300) -> pd.DataFrame:
    """Scrape reviews for one app from Google Play; returns a normalized DataFrame."""
    print(f"Scraping {app_name} ({app_id})...")
    scraped_at = datetime.now().isoformat()

    result, _ = reviews(
        app_id,
        lang=lang,
        country=country,
        sort=Sort.NEWEST,
        count=how_many,
    )

    records = [
        {
            "app":      app_name,
            "userName": r.get("userName", ""),
            "rating":   r.get("score", 0),
            "title":    "",                          # Google Play has no review title
            "review":   r.get("content", ""),
            "date":     r["at"].isoformat() if r.get("at") else "",
            "scraped_at": scraped_at,
        }
        for r in result
    ]

    df = pd.DataFrame(records)
    print(f"  → got {len(df)} reviews")
    return df


if __name__ == "__main__":
    apps = [
        {"name": "lidl-plus", "id": "com.lidl.eci.lidlplus"},
        {"name": "rewe",      "id": "de.rewe.app"},
    ]

    all_reviews = []
    for app in apps:
        df = scrape_app(app["name"], app["id"], lang="de", country="de", how_many=300)
        all_reviews.append(df)

    combined = pd.concat(all_reviews, ignore_index=True)
    combined = combined[["app", "userName", "rating", "title", "review", "date"]]
    combined.to_csv(DATA_DIR / "reviews_raw.csv", index=False)

    print(f"\nSaved {len(combined)} total reviews to data/reviews_raw.csv")
    print("\nSample by app:")
    print(combined.groupby("app").size())
    print("\nRating distribution:")
    print(combined.groupby(["app", "rating"]).size().unstack(fill_value=0))
    print("\nFirst 3 reviews:")
    print(combined.head(3).to_string())
