"""Tổng hợp khớp lệnh từng lệnh thành bảng theo bước giá và tóm tắt ngày."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config


def mark_large(trades: pd.DataFrame) -> pd.DataFrame:
    """Thêm cờ lô lớn: theo ngưỡng giá trị tuyệt đối và theo phân vị 99% của mã trong ngày."""
    t = trades.copy()
    t["large_abs"] = t["value"] >= config.LARGE_LOT_VALUE_VND
    q = t.groupby(["symbol", "date"])["vol"].transform(lambda s: s.quantile(config.LARGE_LOT_QUANTILE))
    t["large_q"] = t["vol"] >= q
    t["large"] = t["large_abs"] | t["large_q"]
    return t


def price_levels(trades: pd.DataFrame) -> pd.DataFrame:
    """Một dòng cho mỗi (mã, ngày, giá): KL tổng, mua/bán chủ động, KL phiên định kỳ, lô lớn."""
    if trades.empty:
        return pd.DataFrame()
    t = mark_large(trades)
    t["buy_vol"] = np.where(t["side"] == "B", t["vol"], 0)
    t["sell_vol"] = np.where(t["side"] == "S", t["vol"], 0)
    t["auction_vol"] = np.where(t["side"] == "U", t["vol"], 0)
    t["large_buy_vol"] = np.where(t["large"] & (t["side"] == "B"), t["vol"], 0)
    t["large_sell_vol"] = np.where(t["large"] & (t["side"] == "S"), t["vol"], 0)
    g = t.groupby(["symbol", "date", "exchange", "price"], as_index=False).agg(
        vol=("vol", "sum"), buy_vol=("buy_vol", "sum"), sell_vol=("sell_vol", "sum"),
        auction_vol=("auction_vol", "sum"), n_trades=("vol", "size"),
        n_large=("large", "sum"), large_buy_vol=("large_buy_vol", "sum"),
        large_sell_vol=("large_sell_vol", "sum"),
    )
    g["delta"] = g["buy_vol"] - g["sell_vol"]
    return g


def daily_summary(trades: pd.DataFrame) -> pd.DataFrame:
    """Một dòng cho mỗi (mã, ngày): OHLC, KL, giá trị, mua/bán chủ động, delta, VWAP, POC, lô lớn."""
    if trades.empty:
        return pd.DataFrame()
    t = mark_large(trades)
    out = []
    for (sym, d), x in t.groupby(["symbol", "date"], sort=True):
        lv = x.groupby("price")["vol"].sum()
        buy = int(x.loc[x.side == "B", "vol"].sum())
        sell = int(x.loc[x.side == "S", "vol"].sum())
        lg = x[x["large"]]
        out.append({
            "symbol": sym, "date": d, "exchange": x["exchange"].iloc[0],
            "reference": x["reference"].iloc[-1],
            "open": x["price"].iloc[0], "high": x["price"].max(), "low": x["price"].min(),
            "close": x["price"].iloc[-1],
            "vol": int(x["vol"].sum()), "value": float(x["value"].sum()),
            "buy_vol": buy, "sell_vol": sell, "delta": buy - sell,
            "ato_vol": int(x.loc[x.session == "ATO", "vol"].sum()),
            "atc_vol": int(x.loc[x.session == "ATC", "vol"].sum()),
            "vwap": float(x["value"].sum() / max(x["vol"].sum(), 1)),
            "poc": float(lv.idxmax()), "n_trades": int(len(x)),
            "n_large": int(len(lg)),
            "large_buy_vol": int(lg.loc[lg.side == "B", "vol"].sum()),
            "large_sell_vol": int(lg.loc[lg.side == "S", "vol"].sum()),
            "first_time": x["time"].iloc[0], "last_time": x["time"].iloc[-1],
        })
    return pd.DataFrame(out)


def large_trades(trades: pd.DataFrame) -> pd.DataFrame:
    t = mark_large(trades)
    cols = ["symbol", "date", "time", "seq", "price", "vol", "value", "side", "session", "large_abs", "large_q"]
    return t.loc[t["large"], cols].reset_index(drop=True)
