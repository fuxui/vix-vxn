#!/usr/bin/env python3
"""抓取 VIX/VXN（Cboe）+ SPX/NDX（FRED 主、东方财富兜底）每日收盘，写 data/history.json。

- VIX/VXN：Cboe 官方 CSV，权威、免 key、中美皆可访问。
- SPX/NDX：优先 FRED（SP500 / NASDAQ100，美国站，GitHub Actions 上稳定）；失败时兜底
  东方财富（100.SPX / 100.NDX100，国内可访问）。两者都失败则复用上次数据，不让更新整体失败。
纯标准库，无需 pip install。
"""

import csv
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

CBOE = "https://cdn.cboe.com/api/global/us_indices/daily_prices"
CBOE_SOURCES = {"VIX": "VIX_History.csv", "VXN": "VXN_History.csv"}

# FRED 序列：SP500 = 标普500，NASDAQ100 = 纳斯达克100
FRED_SOURCES = {"SPX": "SP500", "NDX": "NASDAQ100"}
# 东方财富 secid：100.SPX = 标普500，100.NDX100 = 纳斯达克100
EM_SOURCES = {"SPX": "100.SPX", "NDX": "100.NDX100"}
EM_BEG = "20230101"

KEEP_DAYS = 750  # ~3 年交易日，覆盖 1 年视图且 JSON 不大


def http_get(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


def fetch_cboe(symbol):
    raw = http_get(f"{CBOE}/{CBOE_SOURCES[symbol]}")
    rows = []
    for line in raw.splitlines()[1:]:  # 跳过 DATE,OPEN,HIGH,LOW,CLOSE
        p = line.split(",")
        if len(p) < 5:
            continue
        try:
            d = datetime.strptime(p[0], "%m/%d/%Y").date()
            rows.append({"date": d.isoformat(), "close": round(float(p[4]), 2)})
        except ValueError:
            continue
    return rows[-KEEP_DAYS:]


def fetch_fred(series_id):
    """FRED fredgraph.csv：首行表头，之后每行 YYYY-MM-DD,值。"""
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    raw = http_get(url, timeout=40)
    rows = []
    for line in raw.splitlines()[1:]:
        p = line.split(",")
        if len(p) < 2:
            continue
        try:
            close = float(p[1])
        except ValueError:
            continue
        rows.append({"date": p[0], "close": round(close, 2)})
    return rows[-KEEP_DAYS:]


def fetch_eastmoney(secid):
    """东方财富日 K：fields2=f51日期,f52开,f53收,f54高,f55低。返回 [{date, close}] 升序。"""
    end = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y%m%d")
    url = (
        "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        f"?secid={secid}&fields1=f1,f2,f3&fields2=f51,f52,f53,f54,f55"
        f"&klt=101&fqt=1&beg={EM_BEG}&end={end}"
    )
    data = json.loads(http_get(url, timeout=30))
    klines = ((data.get("data") or {}).get("klines")) or []
    rows = []
    for k in klines:
        p = k.split(",")
        if len(p) < 5:
            continue
        try:
            rows.append({"date": p[0], "close": round(float(p[2]), 2)})
        except ValueError:
            continue
    return rows[-KEEP_DAYS:]


def main():
    # 核心：Cboe VIX/VXN（失败则整体失败，让 Actions 标记失败）
    vix = fetch_cboe("VIX")
    vxn = fetch_cboe("VXN")
    print(f"VIX: {len(vix)} rows, latest {vix[-1]}")
    print(f"VXN: {len(vxn)} rows, latest {vxn[-1]}")

    root = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    out_path = os.path.join(root, "data", "history.json")

    payload = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "VIX": vix,
        "VXN": vxn,
    }

    old = {}
    if os.path.exists(out_path):
        try:
            old = json.load(open(out_path, encoding="utf-8"))
        except Exception:
            old = {}

    for key in ("SPX", "NDX"):
        rows = None
        try:
            rows = fetch_fred(FRED_SOURCES[key])
            print(f"{key}: FRED {len(rows)} rows, latest {rows[-1]}")
        except Exception as e:
            print(f"{key}: FRED 失败({type(e).__name__})，尝试东方财富…")
            try:
                rows = fetch_eastmoney(EM_SOURCES[key])
                print(f"{key}: Eastmoney {len(rows)} rows, latest {rows[-1]}")
            except Exception as e2:
                print(f"{key}: Eastmoney 也失败({type(e2).__name__})")
        if rows:
            payload[key] = rows
        elif key in old:
            payload[key] = old[key]
            print(f"{key}: 复用上次 {len(old[key])} 行")
        else:
            print(f"{key}: 暂无数据")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    tmp = out_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp, out_path)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    sys.exit(main())
