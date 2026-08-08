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
NUM_ITEMS = 4

SYSTEM_PROMPT = f"""You are drafting short "trade desk notes" for the website of a Swiss \
commodity trading operations & compliance consultancy (FC Finance Consulting GmbH, Zug).

Use web search to find genuinely recent developments (last ~7 days where possible) in:
- commodity trading technology (CTRM/ETRM systems, trading platforms, data/analytics tools)
- trade financing (commodity trade finance, structured finance, letters of credit, fintech)
- logistics relevant to commodity trading (freight, shipping, warehousing, supply chain)
- CTRM implementations, vendors, or regulatory/compliance developments (e.g. EMIR, REMIT)

Then output EXACTLY {NUM_ITEMS} items as a JSON array. For each item:
- "date": the item's date in YYYY-MM-DD format (use today's date if unclear)
- "tag": ONE short uppercase label, 3-5 characters (e.g. "CTRM", "OPS", "REG", "FIN", "LOG")
- "headline": under 8 words, plain and specific, no clickbait
- "summary": 1-2 sentences, under 40 words, written entirely in your own words (never copy
  wording from a source). If useful, name the source organization in prose (e.g. "per Reuters"),
  but never quote it directly.

Rules:
- Do not fabricate specifics (numbers, names, dates) you did not find via search.
- Prefer substance a commodity trading operations professional would find useful over generic
  market commentary.
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
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": USER_PROMPT}],
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 6}],
    )

    text_blocks = [b.text for b in response.content if getattr(b, "type", None) == "text"]
    full_text = "\n".join(text_blocks)

    items = extract_json_array(full_text)

    # Basic validation / normalization so a malformed model reply can't break the page.
    clean_items = []
    for raw in items[:NUM_ITEMS]:
        if not isinstance(raw, dict):
            continue
        clean_items.append({
            "date": str(raw.get("date", ""))[:10],
            "tag": str(raw.get("tag", "NOTE")).upper()[:6],
            "headline": str(raw.get("headline", "")).strip(),
            "summary": str(raw.get("summary", "")).strip(),
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
