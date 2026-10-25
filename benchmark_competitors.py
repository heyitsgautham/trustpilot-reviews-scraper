"""Benchmark a set of competitors on Trustpilot and print a Markdown table.

For each business it shows the TrustScore and the share of 1-star reviews over
all time, then the same company's latest reviews: their average rating, how many
are 1-star and how many got a reply. A recent average well below the TrustScore
means things are getting worse right now.

Usage:
    export APIFY_TOKEN=...
    python benchmark_competitors.py monzo.com revolut.com wise.com --recent 30
"""

import argparse
import os
import sys
from collections import defaultdict
from decimal import Decimal

from apify_client import ApifyClient

ACTOR = "heyitsgautham/trustpilot-reviews-scraper"
PRICE_PER_REVIEW = Decimal("0.00025")


def pct(part, whole):
    return f"{part / whole:.0%}" if whole else "n/a"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("businesses", nargs="+", help="domains or Trustpilot review URLs")
    parser.add_argument("--recent", type=int, default=50, help="latest reviews to read per business (default 50)")
    parser.add_argument("--out", help="also write the table to this Markdown file")
    args = parser.parse_args()

    token = os.environ.get("APIFY_TOKEN")
    if not token:
        sys.exit("Set APIFY_TOKEN first. Get one at https://console.apify.com/settings/integrations")

    run_input = {
        "businesses": args.businesses,
        "maxReviewsPerBusiness": args.recent,
        "sort": "recency",
        "splitToGetMore": False,
    }
    cap = PRICE_PER_REVIEW * args.recent * len(args.businesses)
    print(f"Reading the latest {args.recent} reviews of {len(args.businesses)} businesses, at most ${cap:.4f}\n")

    client = ApifyClient(token)
    run = client.actor(ACTOR).call(run_input=run_input, max_total_charge_usd=cap, logger=None)
    if run is None or run.status != "SUCCEEDED":
        sys.exit(f"Run did not succeed: {run.status if run else 'no run'}")

    companies, reviews = [], defaultdict(list)
    for item in client.dataset(run.default_dataset_id).iterate_items():
        if item.get("type") == "review" and item.get("status") == "ok":
            reviews[item["businessDomain"]].append(item)
        elif item.get("type") == "company":
            companies.append(item)

    lines = [
        "| Business | TrustScore | Reviews | 1-star, all time | Recent avg | 1-star, recent | Replied, recent |",
        "|---|---|---|---|---|---|---|",
    ]
    for company in sorted(companies, key=lambda c: c.get("trustScore") or 0, reverse=True):
        if company.get("status") != "ok":
            print(f"Skipped {company.get('input') or company.get('domain')}: {company.get('message')}")
            continue
        dist = company.get("starDistribution") or {}
        total = sum(dist.values())
        recent = reviews[company["domain"]]
        avg = sum(r["rating"] for r in recent) / len(recent) if recent else None
        lines.append(
            f"| {company['name']} | {company['trustScore']} | {company['totalReviews']:,} "
            f"| {pct(dist.get('1', 0), total)} "
            f"| {f'{avg:.2f}' if avg is not None else 'n/a'} ({len(recent)}) "
            f"| {pct(sum(r['rating'] == 1 for r in recent), len(recent))} "
            f"| {pct(sum(bool(r.get('replyText')) for r in recent), len(recent))} |"
        )

    table = "\n".join(lines)
    print(table)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(table + "\n")


if __name__ == "__main__":
    main()
