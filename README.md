# Trustpilot reviews scraper

Get any company's Trustpilot reviews and TrustScore as JSON rows, from Python or curl, without a Trustpilot login or business account.
This repo also has a script that benchmarks competitors in one command.

The data comes from the [Trustpilot Reviews & TrustScore Scraper](https://apify.com/heyitsgautham/trustpilot-reviews-scraper), an Apify actor I built and maintain.
It's paid per result, $0.25 per 1,000 reviews, and the company summary rows are free.
The code here is MIT licensed.

## Benchmark your competitors

`benchmark_competitors.py` takes a few domains and prints one Markdown table.
It puts each company's all-time TrustScore next to its latest reviews, so you see who's slipping right now.

```bash
pip install -r requirements.txt
export APIFY_TOKEN=your_token_here
python benchmark_competitors.py monzo.com revolut.com wise.com starlingbank.com --recent 30
```

My run on 26 Oct 2026 printed this.

```
Reading the latest 30 reviews of 4 businesses, at most $0.0300

| Business | TrustScore | Reviews | 1-star, all time | Recent avg | 1-star, recent | Replied, recent |
|---|---|---|---|---|---|---|
| Revolut | 4.7 | 479,128 | 7% | 4.80 (30) | 0% | 0% |
| Monzo | 4.6 | 73,727 | 10% | 4.63 (30) | 7% | 3% |
| Starling | 4.4 | 48,407 | 12% | 3.87 (30) | 23% | 67% |
| Wise | 4.3 | 303,720 | 9% | 4.10 (30) | 10% | 0% |
```

Starling stands out.
Its latest 30 reviews average 3.87 against a 4.4 TrustScore, and 23% of them are 1-star.
It's also the only one of the four answering most of its new reviews.

Thirty reviews is a small sample, so raise `--recent` before you draw conclusions.
The script caps the run's charge at `--recent` times the number of businesses times $0.00025, and prints that cap first.
Add `--out benchmark.md` to save the table.

## Quick start in Python

```python
import os
from apify_client import ApifyClient

client = ApifyClient(os.environ["APIFY_TOKEN"])
run = client.actor("heyitsgautham/trustpilot-reviews-scraper").call(run_input={
    "businesses": ["monzo.com", "https://de.trustpilot.com/review/www.zalando.de"],
    "maxReviewsPerBusiness": 100,
    "stars": ["1", "2"],
    "datePeriod": "last3months",
})
for row in client.dataset(run.default_dataset_id).iterate_items():
    if row["type"] == "review":
        print(row["businessName"], row["rating"], row["title"])
```

This uses `apify-client` 3.x, where `call()` returns a run object, so it's `run.default_dataset_id` rather than a dict lookup.

## Quick start with curl

Start a run and wait up to 2 minutes for it, then read its dataset.
This needs `jq`.

```bash
RUN=$(curl -s -X POST "https://api.apify.com/v2/acts/heyitsgautham~trustpilot-reviews-scraper/runs?waitForFinish=120" \
  -H "Authorization: Bearer $APIFY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"businesses": ["monzo.com"], "maxReviewsPerBusiness": 3, "stars": ["1"]}')
DATASET=$(echo "$RUN" | jq -r .data.defaultDatasetId)

curl -s "https://api.apify.com/v2/datasets/$DATASET/items?format=json&clean=true" \
  -H "Authorization: Bearer $APIFY_TOKEN"
```

I ran exactly this and got three 1-star Monzo reviews plus Monzo's free company row.

## What comes back

Every business gives one free `company` row, with the TrustScore, total reviews, reviews in the last 12 months, the count per star, categories, whether the profile is claimed, and how often and how fast the company replies to negative reviews.
For Monzo on 26 Oct 2026 that was a 4.6 TrustScore over 73,727 reviews, 7,412 of them 1-star, a 50% reply rate and 2.92 days to reply.

Then one `review` row per review, which is the part you pay for.
This one is from the benchmark run above.

```json
{
  "type": "review",
  "status": "ok",
  "businessDomain": "starlingbank.com",
  "businessName": "Starling",
  "reviewId": "6addb5d35ddc2615c7168063",
  "rating": 5,
  "title": "Very straight forward to open and use the account",
  "text": "Very straight forward to open and use the account",
  "language": "en",
  "reviewDate": "2026-10-25T09:54:59.000Z",
  "experienceDate": "2026-10-21",
  "updatedDate": null,
  "isVerified": true,
  "source": "AFSv2",
  "likes": 0,
  "replyText": "Hi there, \n\nThanks for leaving a review!\n\nIt's lovely to know you're finding the app straightforward. \n\nIf you ever need help, we're here 24/7.\n\nHappy banking,\nTeam Starling",
  "replyDate": "2026-10-25T10:13:23.000Z",
  "reviewerCountry": "GB",
  "reviewerReviewCount": 12,
  "reviewUrl": "https://www.trustpilot.com/reviews/6addb5d35ddc2615c7168063"
}
```

The scraper doesn't collect reviewer names, emails or phone numbers.

## Inputs worth knowing

| Input | What it does |
|---|---|
| `businesses` | Trustpilot review URLs from any country site, or plain domains like `monzo.com` |
| `maxReviewsPerBusiness` | Stop after this many reviews per business |
| `stars` | Only these star ratings, such as `["1", "2"]` |
| `language` | `all` by default, or a code such as `de`. Trustpilot's own site shows only English unless you change it |
| `datePeriod` | `last30days`, `last3months`, `last6months`, `last12months` or `any` |
| `verifiedOnly`, `withRepliesOnly` | Only verified reviews, or only ones the company answered |
| `keyword` | Only reviews containing a word such as `refund`, through Trustpilot's own search |
| `topics`, `reviewerCountries` | Trustpilot's topic tags, and two-letter reviewer countries |
| `onlyNewSinceLastRun`, `publishedAfter` | For a scheduled feed of new reviews only |

## The 200-review wall

Logged-out visitors see 10 pages of 20 reviews per filter combination, and page 11 sends you to a login.
The scraper never logs in.
Instead it reads narrower slices, each star and language, then verified, replied and topic filters, and each slice gets its own 200.
In a 56-company test it returned 95,165 reviews, and on small and mid-size companies it gets most of the history, back to 2007 on Amazon.
On companies with tens of thousands of reviews a run returns part of the history, not all of it.

## Price

| Apify tier | Per 1,000 reviews |
|---|---|
| No discount | $0.25 |
| Bronze | $0.225 |
| Silver | $0.20 |
| Gold | $0.175 |

Company rows, unknown domains and failed fetches are free, and there's no start fee.
Apify's free plan includes $5 a month, enough for 20,000 reviews.

## Limits

- Trustpilot rate-limits heavy reading. The scraper slows down, and a page that fails 10 times is skipped and counted in the company row's `message`.
- Trustpilot ignores its own `last7days` filter, so the scraper doesn't offer it. Use `publishedAfter: "7 days"` instead.
- Reviews Trustpilot removed or hid aren't available.
- Use the data in ways that respect Trustpilot's terms and reviewers' privacy.

## License

MIT for the code in this repo.
