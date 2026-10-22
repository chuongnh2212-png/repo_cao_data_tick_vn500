"""Đọc khớp lệnh từng lệnh từ API DSC.

Định dạng một bản ghi (kiểm tra ngày 22/10/2026, mã SSI):
    sequenceMsg "184572" · tradingdate "22/10/2026" · symbol "SSI" · formattedTime "09:15:01"
    lastColor "S" (B = mua chủ động, S = bán chủ động, KHÔNG có ở lệnh ATO/ATC)
    formattedMatchPrice "20450.0" (VND) · formattedVol "20600" · formattedAccVol "222400"
    formattedAccVal "4548080000.0" · totalBuyVol "0" · totalSellVol "20600" (lũy kế chủ động)
    averagePrice 20450 · reference 20400 · exchange "HOSE" · open/low/high · changePercent · kid
"""
from __future__ import annotations

import time
from datetime import date, datetime
from typing import Any

import pandas as pd
import requests

from . import config

COLUMNS = [
    "date", "time", "symbol", "exchange", "seq", "price", "vol", "value",
    "side", "acc_vol", "acc_val", "cum_buy", "cum_sell", "reference",
]


class DSCError(RuntimeError):
    pass


def fetch_raw(symbol: str, session: requests.Session | None = None) -> list[dict[str, Any]]:
    """Gọi API, trả về mảng bản ghi `d`. Thử lại khi lỗi mạng."""
    s = session or requests.Session()
    url = config.DSC_URL.format(symbol=symbol.upper())
    last_err: Exception | None = None
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            r = s.get(url, timeout=config.REQUEST_TIMEOUT_SEC,
                      headers={"User-Agent": "vn-orderflow/0.1 (research)"})
            r.raise_for_status()
            payload = r.json()
            if payload.get("s") != "ok":
                raise DSCError(f"{symbol}: s={payload.get('s')} ec={payload.get('ec')} em={payload.get('em')}")
            return payload.get("d") or []
        except (requests.RequestException, ValueError, DSCError) as e:
            last_err = e
            time.sleep(2 * attempt)
    raise DSCError(f"{symbol}: thất bại sau {config.MAX_RETRIES} lần: {last_err}")


def _num(x: Any) -> float:
    if x is None or x == "":
        return float("nan")
    if isinstance(x, (int, float)):
        return float(x)
    return float(str(x).replace(",", ""))


def parse(records: list[dict[str, Any]]) -> pd.DataFrame:
    """Chuyển bản ghi thô thành DataFrame chuẩn, sắp theo thời gian và sequenceMsg."""
    if not records:
        return pd.DataFrame(columns=COLUMNS)
    rows = []
    for r in records:
        side = (r.get("lastColor") or "").upper()
        price = _num(r.get("formattedMatchPrice"))
        vol = _num(r.get("formattedVol"))
        rows.append({
            "date": datetime.strptime(r["tradingdate"], "%d/%m/%Y").date(),
            "time": r.get("formattedTime", ""),
            "symbol": str(r.get("symbol", "")).upper(),
            "exchange": str(r.get("exchange", "")).upper(),
            "seq": int(_num(r.get("sequenceMsg"))),
            "price": price,
            "vol": int(vol),
            "value": price * vol,
            "side": side if side in ("B", "S") else "U",   # U = không xác định (ATO/ATC)
            "acc_vol": int(_num(r.get("formattedAccVol"))),
            "acc_val": _num(r.get("formattedAccVal")),
            "cum_buy": int(_num(r.get("totalBuyVol"))),
            "cum_sell": int(_num(r.get("totalSellVol"))),
            "reference": _num(r.get("reference")),
        })
    df = pd.DataFrame(rows, columns=COLUMNS)
    df = df.sort_values(["time", "seq"], kind="stable").reset_index(drop=True)
    df["session"] = "continuous"
    df.loc[(df["side"] == "U") & (df["time"] <= config.ATO_END), "session"] = "ATO"
    df.loc[(df["side"] == "U") & (df["time"] >= config.ATC_START), "session"] = "ATC"
    df.loc[(df["side"] == "U") & (df["session"] == "continuous"), "session"] = "unknown"
    return df


def fetch(symbol: str, session: requests.Session | None = None) -> pd.DataFrame:
    return parse(fetch_raw(symbol, session))


def today_vn() -> date:
    return datetime.now(config.TZ).date()
