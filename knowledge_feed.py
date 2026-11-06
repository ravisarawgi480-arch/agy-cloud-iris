import os
import sys
import json
import ssl
import urllib.request
import time

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INTEL_CACHE_PATH = os.path.join(BASE_DIR, "curated_intel.json")

KEYWORDS = [
    "agent", "agents", "browser", "playwright", "automation", "whatsapp",
    "gemini", "claude", "llm", "voice", "ios", "telegram", "render",
    "python", "ocr", "workflow", "sqlite", "duckdb"
]

def fetch_live_tech_intel():
    """
    Autonomously scans top developer & tech intelligence feeds,
    filtering strictly for Ravi's high-ROI tech stack.
    """
    ctx = ssl._create_unverified_context()
    curated_items = []

    try:
        req = urllib.request.Request(
            'https://hacker-news.firebaseio.com/v0/topstories.json',
            headers={'User-Agent': 'AGY-Iris-Knowledge-Watcher/1.0'}
        )
        with urllib.request.urlopen(req, context=ctx, timeout=8) as res:
            top_ids = json.loads(res.read())[:40]

        for item_id in top_ids:
            try:
                item_req = urllib.request.Request(
                    f'https://hacker-news.firebaseio.com/v0/item/{item_id}.json',
                    headers={'User-Agent': 'AGY-Iris-Knowledge-Watcher/1.0'}
                )
                with urllib.request.urlopen(item_req, context=ctx, timeout=4) as item_res:
                    story = json.loads(item_res.read())

                title = story.get('title', '')
                url = story.get('url', f"https://news.ycombinator.com/item?id={item_id}")
                score = story.get('score', 0)

                # Match against Ravi's relevant business & tech keywords
                lower_title = title.lower()
                matched_kw = [kw for kw in KEYWORDS if kw in lower_title]

                if matched_kw and score >= 20:
                    curated_items.append({
                        "id": item_id,
                        "title": title,
                        "url": url,
                        "score": score,
                        "tags": matched_kw,
                        "timestamp": int(time.time())
                    })
                    if len(curated_items) >= 5:
                        break
            except Exception:
                continue

    except Exception as e:
        print(f"[INTEL] Fetch error: {e}", flush=True)

    if curated_items:
        with open(INTEL_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(curated_items, f, indent=2)
        print(f"[INTEL] Successfully cached {len(curated_items)} high-signal tech intelligence items.", flush=True)
        return curated_items

    # Fallback if offline / empty
    if os.path.exists(INTEL_CACHE_PATH):
        try:
            with open(INTEL_CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    return []

def get_formatted_daily_signal():
    items = fetch_live_tech_intel()
    if not items and os.path.exists(INTEL_CACHE_PATH):
        try:
            with open(INTEL_CACHE_PATH, "r", encoding="utf-8") as f:
                items = json.load(f)
        except Exception:
            items = []

    if not items:
        return (
            "🔥 *TODAY'S AI SIGNAL:* Autonomous Browser-Use Agents\n"
            "• *Trend:* AI models can now operate live Chrome browsers in cloud to fill forms and extract documents."
        )

    best = items[0]
    return (
        f"🔥 *TODAY'S HIGH-SIGNAL TECH RADAR:*\n"
        f"• *Title:* {best['title']}\n"
        f"• *Tags:* #{', #'.join(best['tags'])}\n"
        f"• *Link:* {best['url']}"
    )

if __name__ == "__main__":
    results = fetch_live_tech_intel()
    print("Found items:")
    for r in results:
        print(f"• [{r['score']} pts] {r['title']} ({', '.join(r['tags'])})")
