#!/usr/bin/env python3
"""Fetch daily VIX/VXN closes from Cboe's official history CSVs.

Writes data/history.json (repo root /data) so the GitHub-Actions cron keeps the
dashboard fresh. Standard library only — no pip install needed.
"""

import csv
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

BASE = "https://cdn.cboe.com/api/global/us_indices/daily_prices"
SOURCES = {"VIX": "VIX_History.csv", "VXN": "VXN_History.csv"}
KEEP_DAYS = 750  # ~3 years of trading days — enough for the 1y view, keeps JSON small


def fetch(symbol):
    url = f"{BASE}/{SOURCES[symbol]}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8")


def parse(raw):
    rows = []
    for line in raw.splitlines()[1:]:  # skip DATE,OPEN,HIGH,LOW,CLOSE header
        parts = line.split(",")
        if len(parts) < 5:
            continue
        try:
            d = datetime.strptime(parts[0], "%m/%d/%Y").date()
            close = float(parts[4])
        except ValueError:
            continue
        rows.append({"date": d.isoformat(), "close": round(close, 2)})
    return rows


def main():
    series = {}
    for symbol in SOURCES:
        rows = parse(fetch(symbol))
        series[symbol] = rows[-KEEP_DAYS:]
        print(f"{symbol}: {len(series[symbol])} rows, latest {series[symbol][-1]}")

    payload = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "VIX": series["VIX"],
        "VXN": series["VXN"],
    }

    root = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    out_dir = os.path.join(root, "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "history.json")
    tmp = out_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, out_path)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    sys.exit(main())
