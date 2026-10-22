"""Xuất dữ liệu khớp lệnh sang định dạng AmiBroker.

    python -m vnflow.amibroker                         # mọi mã có dữ liệu
    python -m vnflow.amibroker --symbols SSI MBB       # vài mã
    python -m vnflow.amibroker --out D:\\vnflow_out    # đổi thư mục xuất

Đầu ra (mặc định ./amibroker_out):
- vnflow_daily.csv: nạp vào AmiBroker bằng ASCII import (format amibroker/vnflow.format).
  Mỗi mã thành MỘT MÃ RIÊNG có hậu tố _OF (ví dụ SSI_OF) để không ghi đè dữ liệu giá đang dùng:
      Open/High/Low/Close/Volume = từ khớp lệnh trong ngày (giá nghìn đồng)
      Aux1 = KL mua chủ động · Aux2 = KL bán chủ động · OpenInt = delta lô lớn (mua − bán)
- levels/<MÃ>.csv: khớp lệnh theo bước giá từng ngày, để AFL vnflow_profile.afl vẽ Volume Profile thật.

Đọc dữ liệu từ data/ (đồng bộ GitHub) và data_local/ (chạy tay trên máy); trùng (mã, ngày) thì ưu tiên data/
nếu ngày đó đủ phiên, ngược lại lấy bản có nhiều KL hơn.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from . import config, store

SUFFIX = "_OF"


def _datenum(d: pd.Series) -> pd.Series:
    """DateNum() của AmiBroker: (năm − 1900) × 10000 + tháng × 100 + ngày."""
    d = pd.to_datetime(d)
    return (d.dt.year - 1900) * 10000 + d.dt.month * 100 + d.dt.day


def _load(kind: str, roots: list[Path], symbols: list[str] | None) -> pd.DataFrame:
    parts = []
    for prio, root in enumerate(roots):
        base = root / kind
        if not base.exists():
            continue
        df = store.read_range(base)
        if len(df):
            if symbols:
                df = df[df["symbol"].isin(symbols)]
            df = df.assign(_prio=prio)
            parts.append(df)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def export(symbols: list[str] | None, out: Path, roots: list[Path], price_unit: float = 1000.0) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    daily = _load("daily", roots, symbols)
    if daily.empty:
        return {"symbols": 0}
    # chọn bản tốt nhất cho mỗi (mã, ngày): đủ phiên trước, rồi KL lớn hơn, rồi nguồn ưu tiên
    daily["_full"] = daily["last_time"] >= config.SESSION_CLOSE
    daily = (daily.sort_values(["symbol", "date", "_full", "vol", "_prio"], ascending=[True, True, False, False, True])
                  .drop_duplicates(["symbol", "date"]))
    keep = daily[["symbol", "date", "_prio"]]

    d = daily.sort_values(["symbol", "date"])
    rows = pd.DataFrame({
        "Ticker": d["symbol"] + SUFFIX,
        "Date": pd.to_datetime(d["date"]).dt.strftime("%Y%m%d"),
        "Open": d["open"] / price_unit, "High": d["high"] / price_unit,
        "Low": d["low"] / price_unit, "Close": d["close"] / price_unit,
        "Volume": d["vol"], "OpenInt": d["large_buy_vol"] - d["large_sell_vol"],
        "Aux1": d["buy_vol"], "Aux2": d["sell_vol"],
    })
    rows.to_csv(out / "vnflow_daily.csv", index=False, float_format="%.4f")

    lv = _load("levels", roots, symbols)
    lv = lv.merge(keep, on=["symbol", "date", "_prio"], how="inner")
    (out / "levels").mkdir(exist_ok=True)
    for sym, x in lv.groupby("symbol"):
        x = x.sort_values(["date", "price"])
        pd.DataFrame({
            "datenum": _datenum(x["date"]), "date": pd.to_datetime(x["date"]).dt.strftime("%Y-%m-%d"),
            "price": x["price"] / price_unit, "vol": x["vol"], "buy": x["buy_vol"], "sell": x["sell_vol"],
            "auction": x["auction_vol"], "lbuy": x["large_buy_vol"], "lsell": x["large_sell_vol"],
        }).to_csv(out / "levels" / f"{sym}.csv", index=False, float_format="%.4f")
    return {"symbols": int(d["symbol"].nunique()), "days": int(d["date"].nunique()), "out": str(out)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--symbols", nargs="*")
    ap.add_argument("--out", default=str(config.ROOT / "amibroker_out"))
    ap.add_argument("--price-unit", type=float, default=1000.0, help="1000 = giá nghìn đồng như dữ liệu AmiBroker thường dùng")
    a = ap.parse_args()
    roots = [config.ROOT / "data", config.ROOT / "data_local"]
    syms = [s.upper() for s in a.symbols] if a.symbols else None
    print(export(syms, Path(a.out), roots, a.price_unit))


if __name__ == "__main__":
    main()
