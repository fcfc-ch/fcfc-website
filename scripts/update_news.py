"""
Calls the Claude API (with the built-in web_search tool) to produce a short,
current set of "Trade desk notes" for the FC Finance Consulting site, and
writes the result to news.json at the repo root.

Runs automatically via .github/workflows/update-news.yml (daily, plus manual
trigger). Requires an ANTHROPIC_API_KEY secret set on the repo.

Local test:
    pip install -r scripts/requirements.txt
    export ANTHROPIC_API_KEY=sk-ant-...
    python scripts/update_news.py
"""

import json
import os
import re
import sys
from datetime import datetime, timezone

import anthropic

MODEL = "claude-sonnet-5"
NEWS_PATH = os.path.join(os.path.dirname(__file__), "..", "news.json")
NUM_ITEMS = 6
MIN_COMPANY_ITEMS = 3

# Organisations named on fcfc.ch — keep in sync with the West Africa, Asia and banking sections.
COMPANIES = [
    "NNPC Ltd", "Afreximbank", "Ghana Gold Board (GoldBod)",
    "Ghana Ministry of Lands and Natural Resources", "Stanbic Bank Ghana", "Zenith Bank Ghana",
    "Reliance Industries", "Indian Oil Corporation", "HPCL", "BPCL",
    "PETRONAS / PETCO", "Pertamina Patra Niaga", "Chandra Asri Pacific",
    "SOCAR STAR Refinery", "Tüpraş", "Nakkaş Holding", "SOCAR",
    "BCP Banque de Commerce et de Placements", "Arab Bank (Switzerland)",
    "Raiffeisen Bank International", "First Abu Dhabi Bank (FAB)",
]

SYSTEM_PROMPT = f"""You are drafting short "trade desk notes" for the website of a Swiss \
commodity advisory firm (FC Finance Consulting GmbH, Zug) covering business development, \
trade finance and trading operations.

Use web search to find genuinely recent developments (last ~7 days where possible).

PART A — at least {MIN_COMPANY_ITEMS} items about these organisations the firm works with:
{", ".join(COMPANIES)}.
Good topics: tenders, supply or offtake deals, financing facilities, refinery or trading news,
licensing or regulatory decisions, results that matter to commodity flows.

PART B — the remaining items on:
- commodity trade finance and structured finance
- commodity trading technology (CTRM/ETRM) and operations
- logistics and regulation relevant to commodity trading

Output EXACTLY {NUM_ITEMS} items as a JSON array. For each item:
- "date": the item's date in YYYY-MM-DD format (use today's date if unclear)
- "tag": ONE short uppercase label, 2-5 characters (e.g. "NOC", "BANK", "GOLD", "FIN", "CTRM", "LOG", "REG")
- "company": the organisation from the list above if the item is about one, otherwise ""
- "headline": under 9 words, plain and specific, no clickbait (English)
- "summary": 1-2 sentences, under 40 words, entirely in your own words (English). Never copy
  wording from a source; you may name the source organisation in prose but never quote it.
- "url": the https URL of the main source you used (a page you actually found), or ""
- "i18n": translations of headline and summary, in the same neutral business register:
  {{"de": {{"headline": "...", "summary": "..."}}, "fr": {{...}}, "it": {{...}}}}
  German uses Swiss spelling (ss instead of ß).

Rules:
- Do not fabricate specifics (numbers, names, dates, URLs) you did not find via search.
- If you cannot find recent news for a listed organisation, skip it; never invent an item.
- Output ONLY the JSON array. No prose, no markdown code fences, no preamble.
"""

USER_PROMPT = "Find current, relevant items and produce the JSON array now."


def extract_json_array(text: str):
    """Pull a JSON array out of the model's reply, tolerating stray fences or prose."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON array found in model output:\n" + text[:500])
    return json.loads(match.group(0))


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY is not set.", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": USER_PROMPT}],
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 10}],
    )

    text_blocks = [b.text for b in response.content if getattr(b, "type", None) == "text"]
    full_text = "\n".join(text_blocks)

    items = extract_json_array(full_text)

    # Basic validation / normalization so a malformed model reply can't break the page.
    clean_items = []
    for raw in items[:NUM_ITEMS]:
        if not isinstance(raw, dict):
            continue
        url = str(raw.get("url", "")).strip()
        if not url.startswith("https://"):
            url = ""
        i18n = {}
        raw_i18n = raw.get("i18n") if isinstance(raw.get("i18n"), dict) else {}
        for lang in ("de", "fr", "it"):
            t = raw_i18n.get(lang)
            if isinstance(t, dict) and t.get("headline") and t.get("summary"):
                i18n[lang] = {
                    "headline": str(t["headline"]).strip(),
                    "summary": str(t["summary"]).strip(),
                }
        clean_items.append({
            "date": str(raw.get("date", ""))[:10],
            "tag": str(raw.get("tag", "NOTE")).upper()[:6],
            "company": str(raw.get("company", "")).strip(),
            "headline": str(raw.get("headline", "")).strip(),
            "summary": str(raw.get("summary", "")).strip(),
            "url": url,
            "i18n": i18n,
        })

    if not clean_items:
        print("ERROR: model returned no usable items, keeping existing news.json", file=sys.stderr)
        sys.exit(1)

    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "items": clean_items,
    }

    with open(NEWS_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Wrote {len(clean_items)} items to {os.path.abspath(NEWS_PATH)}")


if __name__ == "__main__":
    main()
