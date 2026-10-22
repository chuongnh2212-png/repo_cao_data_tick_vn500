"""Kiểm tra chất lượng dữ liệu. Luôn chạy TRƯỚC khi phân tích."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config

# Nguồn DSC đôi khi thiếu vài lệnh lẻ (SSI 22/10/2026: 3 lệnh, 0,08% KL). Dưới ngưỡng này chỉ cảnh báo.
MISSING_TOLERANCE = 0.005


def check_trades(trades: pd.DataFrame) -> list[dict]:
    """Kiểm tra khớp lệnh một mã/ngày. Trả về danh sách vấn đề (rỗng = sạch)."""
    issues: list[dict] = []
    if trades.empty:
        return [{"check": "empty", "detail": "không có bản ghi"}]
    for (sym, d), x in trades.groupby(["symbol", "date"]):
        def add(check, detail, level="warn"):
            issues.append({"symbol": sym, "date": str(d), "check": check, "level": level, "detail": detail})

        total = int(x["vol"].sum())
        acc = int(x["acc_vol"].max())
        if acc != total:
            gaps = int(((x["acc_vol"].diff() != x["vol"]) & x["acc_vol"].diff().notna()).sum())
            miss = (acc - total) / max(acc, 1)
            level = "warn" if abs(miss) <= MISSING_TOLERANCE else "error"
            add("acc_vol", f"nguồn thiếu {acc - total:,} cp ({miss:.2%}) ở {gaps} chỗ; lũy kế {acc:,} vs cộng lệnh {total:,}", level)
        buy = int(x.loc[x.side == "B", "vol"].sum())
        sell = int(x.loc[x.side == "S", "vol"].sum())
        cb, cs = int(x["cum_buy"].max()), int(x["cum_sell"].max())
        if abs(cb - buy) + abs(cs - sell) > MISSING_TOLERANCE * max(total, 1):
            add("side_totals", f"mua/bán chủ động lũy kế {cb:,}/{cs:,} ≠ cộng từng lệnh {buy:,}/{sell:,}")
        if x["time"].iloc[-1] < config.SESSION_CLOSE:
            add("incomplete_day", f"lệnh cuối lúc {x['time'].iloc[-1]} < {config.SESSION_CLOSE} → có thể lấy giữa phiên")
        ex = x["exchange"].iloc[0]
        off = x[[p % config.tick_size(p, ex) != 0 for p in x["price"]]]
        if len(off):
            add("tick", f"{len(off)} lệnh giá sai bước giá, ví dụ {off['price'].iloc[0]}")
        ref = x["reference"].iloc[-1]
        lim = config.PRICE_LIMIT.get(ex, 0.15)
        if ref and ref == ref:
            out = x[(x["price"] > ref * (1 + lim) + 1e-6) | (x["price"] < ref * (1 - lim) - 1e-6)]
            if len(out):
                add("price_limit", f"{len(out)} lệnh ngoài biên độ ±{lim:.0%} quanh tham chiếu {ref}", "error")
        if (x["vol"] <= 0).any():
            add("vol_nonpositive", "có lệnh KL ≤ 0", "error")
        if x["seq"].duplicated().any():
            add("dup_seq", "trùng sequenceMsg", "error")
    return issues


def check_ohlcv(daily: pd.DataFrame, price_unit: float = 1000.0) -> pd.DataFrame:
    """Kiểm tra nến ngày (cột Date, Open, High, Low, Close, Volume, [Exchange]).

    price_unit: 1000 nếu giá tính bằng nghìn đồng, 1 nếu VND.
    Trả về các phiên đáng ngờ: vượt biên độ (dấu hiệu sự kiện quyền chưa điều chỉnh),
    sai bước giá (dấu hiệu giá đã điều chỉnh lùi), trùng ngày, phiên O=H=L=C (trần/sàn trắng).
    """
    d = daily.sort_values("Date").reset_index(drop=True).copy()
    ex = d["Exchange"] if "Exchange" in d else pd.Series("HOSE", index=d.index)
    ret = d["Close"].pct_change()
    lim = ex.map(lambda e: config.PRICE_LIMIT.get(str(e).upper(), 0.07))
    flags = []
    for i, r in d.iterrows():
        f = []
        if i > 0 and abs(ret.iloc[i]) > lim.iloc[i] + 0.003:
            f.append(f"vượt biên độ ({ret.iloc[i]:+.1%}) → kiểm tra sự kiện quyền")
        p = r["Close"] * price_unit
        if round(p) % config.tick_size(p, str(ex.iloc[i])) != 0:
            f.append("giá lẻ bước giá → dữ liệu đã điều chỉnh lùi")
        if r["Open"] == r["High"] == r["Low"] == r["Close"]:
            f.append("O=H=L=C → trần/sàn trắng hoặc không giao dịch")
        if f:
            flags.append({"Date": r["Date"], "Close": r["Close"], "ret": ret.iloc[i], "flags": "; ".join(f)})
    out = pd.DataFrame(flags)
    dups = d[d["Date"].duplicated(keep=False)]
    if len(dups):
        out = pd.concat([out, pd.DataFrame({"Date": dups["Date"], "flags": "trùng ngày"})], ignore_index=True)
    return out


def adjust_before(daily: pd.DataFrame, date: str, factor: float, adjust_volume: bool = False) -> pd.DataFrame:
    """Nhân giá các phiên TRƯỚC `date` với `factor` (và chia KL nếu adjust_volume).

    Dùng khi nguồn dữ liệu chỉ điều chỉnh một phần cho sự kiện quyền.
    Ví dụ SSI: adjust_before(df, '2026-07-10', 18.82 / 23.55).
    """
    d = daily.copy()
    m = pd.to_datetime(d["Date"]) < pd.Timestamp(date)
    for c in ["Open", "High", "Low", "Close"]:
        d.loc[m, c] = d.loc[m, c] * factor
    if adjust_volume:
        d.loc[m, "Volume"] = (d.loc[m, "Volume"] / factor).round()
    return d
