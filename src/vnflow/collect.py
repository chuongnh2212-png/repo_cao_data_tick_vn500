"""Thu thập khớp lệnh trong ngày cho danh sách mã, lưu bảng bước giá + tóm tắt ngày.

Chạy sau 15:00 (giờ Việt Nam) mỗi ngày giao dịch:
    python -m vnflow.collect                       # toàn bộ config/tickers.txt
    python -m vnflow.collect --symbols SSI MBB     # vài mã
    python -m vnflow.collect --keep-raw            # lưu thêm khớp lệnh thô (data/raw, không commit)

API chỉ trả về NGÀY HIỆN TẠI → bỏ lỡ ngày nào là mất dữ liệu ngày đó.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime

import pandas as pd
import requests

from . import aggregate, config, dsc, quality, store


def read_tickers(path=config.TICKERS_FILE) -> list[str]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.split("#", 1)[0].strip().upper()
        if s:
            out.append(s)
    return list(dict.fromkeys(out))


def run(symbols: list[str], keep_raw: bool = False, allow_partial: bool = False) -> dict:
    today = dsc.today_vn()
    now = datetime.now(config.TZ).strftime("%H:%M")
    if now < "15:00" and not allow_partial:
        sys.exit(f"Bây giờ {now} < 15:00: phiên chưa kết thúc. Dùng --allow-partial nếu chỉ muốn thử.")
    session = requests.Session()
    trades, problems, skipped = [], [], []
    for i, sym in enumerate(symbols, 1):
        try:
            df = dsc.fetch(sym, session)
        except dsc.DSCError as e:
            problems.append({"symbol": sym, "check": "fetch", "level": "error", "detail": str(e)})
            continue
        finally:
            time.sleep(config.REQUEST_DELAY_SEC)
        if df.empty:
            skipped.append(sym)
            continue
        if df["date"].iloc[0] != today:
            skipped.append(sym)  # dữ liệu ngày khác → ngày nghỉ hoặc mã không giao dịch
            continue
        trades.append(df)
        if i % 50 == 0:
            print(f"  {i}/{len(symbols)} mã", flush=True)
    summary = {"date": str(today), "requested": len(symbols), "collected": len(trades),
               "skipped": skipped, "fetch_errors": [p["symbol"] for p in problems]}
    if not trades:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return summary
    all_t = pd.concat(trades, ignore_index=True)
    problems += quality.check_trades(all_t)
    store.write_day(aggregate.price_levels(all_t), config.LEVELS_DIR, today)
    store.write_day(aggregate.daily_summary(all_t), config.DAILY_DIR, today)
    store.write_day(aggregate.large_trades(all_t), config.LARGE_DIR, today)
    if keep_raw:
        store.write_day(all_t, config.RAW_DIR, today)
    config.QUALITY_DIR.mkdir(parents=True, exist_ok=True)
    summary["issues"] = len(problems)
    (config.QUALITY_DIR / f"{today:%Y-%m-%d}.json").write_text(
        json.dumps({"summary": summary, "issues": problems}, ensure_ascii=False, indent=1, default=str),
        encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--symbols", nargs="*", help="danh sách mã; mặc định đọc config/tickers.txt")
    ap.add_argument("--keep-raw", action="store_true", help="lưu khớp lệnh thô vào data/raw")
    ap.add_argument("--allow-partial", action="store_true", help="cho chạy trước 15:00 (dữ liệu chưa đủ ngày)")
    a = ap.parse_args()
    syms = [s.upper() for s in a.symbols] if a.symbols else read_tickers()
    run(syms, keep_raw=a.keep_raw, allow_partial=a.allow_partial)


if __name__ == "__main__":
    main()
