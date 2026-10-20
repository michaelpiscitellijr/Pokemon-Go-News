import html
import json
import os
import re
import urllib.request
from pathlib import Path
from urllib.parse import urljoin

LIST_URL = "https://pokemongo.com/en/news"
WEBHOOK = os.environ["DISCORD_WEBHOOK_URL"]
STATE_FILE = Path("posted.json")
POST_COUNT = 3  # how many of the latest posts to look at
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; PogoNewsBot/1.0)"}


def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def latest_links():
    page = fetch(LIST_URL)
    found = re.findall(r'href="([^"]*?/news/[^"#?/]+)"', page)
    links = []
    for href in found:
        url = urljoin(LIST_URL, href)
        if url not in links:
            links.append(url)
    return links[:POST_COUNT]


def meta(page, prop):
    patterns = [
        rf'<meta[^>]+(?:property|name)="{prop}"[^>]+content="([^"]*)"',
        rf'<meta[^>]+content="([^"]*)"[^>]+(?:property|name)="{prop}"',
    ]
    for pattern in patterns:
        m = re.search(pattern, page, re.I)
        if m:
            return html.unescape(m.group(1)).strip()
    return ""


def post_to_discord(url):
    page = fetch(url)
    title = meta(page, "og:title") or url
    desc = meta(page, "og:description")
    image = meta(page, "og:image")

    embed = {"title": title[:256], "url": url, "color": 0xEE1515}
    if desc:
        embed["description"] = desc[:300]
    if image:
        embed["image"] = {"url": image}

    body = json.dumps({"embeds": [embed]}).encode()
    req = urllib.request.Request(
        WEBHOOK,
        data=body,
        headers={**HEADERS, "Content-Type": "application/json"},
    )
    urllib.request.urlopen(req, timeout=30)
    print("Posted:", title)


def main():
    seen = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else []
    new = [u for u in latest_links() if u not in seen]

    # Oldest first, so the newest post ends up at the bottom of the channel
    for url in reversed(new):
        post_to_discord(url)
        seen.append(url)

    STATE_FILE.write_text(json.dumps(seen[-100:], indent=2))
    if not new:
        print("Nothing new.")


if __name__ == "__main__":
    main()
