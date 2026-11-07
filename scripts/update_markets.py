"""
Fetches indicative market data for the fcfc.ch ticker strip and writes markets.json.

- FX: ECB euro reference rates via the Frankfurter API (free, no key).
  Shown as CHF per unit of EUR, USD, GBP and CHF per 100 JPY, with day-on-day change.
- Commodities (gold, Brent, WTI): OilPriceAPI (https://www.oilpriceapi.com).
  Needs a free API key stored as the repo secret OILPRICE_API_KEY. Without the key,
  the commodities block is simply left empty and the page shows FX only.

Runs from .github/workflows/update-markets.yml. Standard library only.
"""

import json
import os
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone

OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "markets.json")
UA = {"User-Agent": "fcfc-site-markets/1.0"}

FX = [  # (code, display pair, multiplier)
    ("EUR", "EUR/CHF", 1),
    ("USD", "USD/CHF", 1),
    ("GBP", "GBP/CHF", 1),
    ("JPY", "100 JPY/CHF", 100),
]

COMMODITIES = [  # (OilPriceAPI code, key, unit)
    ("GOLD_USD", "gold", "USD/oz"),
    ("BRENT_CRUDE_USD", "brent", "USD/bbl"),
    ("WTI_USD", "wti", "USD/bbl"),
]


def get_json(url, headers=None):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_fx():
    start = (date.today() - timedelta(days=10)).isoformat()
    symbols = ",".join(c for c, _, _ in FX)
    data = get_json(f"https://api.frankfurter.dev/v1/{start}..?base=CHF&symbols={symbols}")
    days = sorted(data.get("rates", {}).keys())
    if not days:
        raise ValueError("no FX data returned")
    last, prev = days[-1], (days[-2] if len(days) > 1 else None)
    out = []
    for code, pair, mult in FX:
        r_last = data["rates"][last].get(code)
        if not r_last:
            continue
        value = mult / r_last  # CHF per (mult) units of the currency
        change = None
        if prev and data["rates"][prev].get(code):
            v_prev = mult / data["rates"][prev][code]
            change = round((value / v_prev - 1) * 100, 2)
        out.append({"pair": pair, "value": round(value, 4), "change_pct": change, "date": last})
    return out


def fetch_commodities(api_key):
    out = []
    for code, key, unit in COMMODITIES:
        try:
            data = get_json(
                f"https://api.oilpriceapi.com/v1/prices/latest?by_code={code}",
                {"Authorization": f"Token {api_key}", "Content-Type": "application/json"},
            )
            d = data.get("data") or {}
            price = d.get("price")
            if price is None:
                raise ValueError(f"no price in response: {str(data)[:200]}")
            change = None
            ch = d.get("changes") or {}
            day = ch.get("24h") or ch.get("1d") or {}
            if isinstance(day, dict) and day.get("percent") is not None:
                change = round(float(day["percent"]), 2)
            out.append({
                "key": key,
                "unit": unit,
                "value": round(float(price), 2),
                "change_pct": change,
                "as_of": str(d.get("created_at", ""))[:16].replace("T", " "),
            })
        except Exception as e:  # keep going: one failed code must not hide the others
            print(f"WARN: {code}: {e}", file=sys.stderr)
    return out


def main():
    previous = {}
    if os.path.exists(OUT_PATH):
        try:
            with open(OUT_PATH, encoding="utf-8") as f:
                previous = json.load(f)
        except Exception:
            previous = {}

    try:
        fx = fetch_fx()
    except Exception as e:
        print(f"WARN: FX fetch failed, keeping previous values: {e}", file=sys.stderr)
        fx = previous.get("fx", [])

    key = os.environ.get("OILPRICE_API_KEY", "").strip()
    commodities = fetch_commodities(key) if key else []
    if key and not commodities:
        commodities = previous.get("commodities", [])

    if not fx and not commodities:
        print("ERROR: no market data at all, leaving markets.json untouched", file=sys.stderr)
        sys.exit(1)

    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fx": fx,
        "commodities": commodities,
        "sources": {
            "fx": "ECB euro reference rates (via Frankfurter)",
            "commodities": "OilPriceAPI" if commodities else None,
        },
    }
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"Wrote {len(fx)} FX and {len(commodities)} commodity quotes")


if __name__ == "__main__":
    main()
