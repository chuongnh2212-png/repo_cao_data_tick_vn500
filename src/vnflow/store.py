"""Đọc/ghi dữ liệu trong thư mục data/."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from . import config


def _path(base: Path, d: date) -> Path:
    return base / f"{d:%Y}" / f"{d:%Y-%m-%d}.parquet"


def write_day(df: pd.DataFrame, base: Path, d: date) -> Path:
    """Ghi file ngày. Nếu file đã có: thay dữ liệu của các mã vừa thu thập, giữ nguyên mã khác
    (để chạy tay vài mã không xóa mất dữ liệu 500 mã)."""
    p = _path(base, d)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists() and len(df) and "symbol" in df:
        old = pd.read_parquet(p)
        old = old[~old["symbol"].isin(set(df["symbol"]))]
        df = pd.concat([old, df], ignore_index=True) if len(old) else df
    df.to_parquet(p, index=False, compression="zstd")
    return p


def read_range(base: Path, symbol: str | None = None, start: str | None = None, end: str | None = None) -> pd.DataFrame:
    files = sorted(base.glob("*/*.parquet"))
    if start:
        files = [f for f in files if f.stem >= start]
    if end:
        files = [f for f in files if f.stem <= end]
    if not files:
        return pd.DataFrame()
    filters = [("symbol", "==", symbol.upper())] if symbol else None
    parts = [pd.read_parquet(f, filters=filters) for f in files]
    parts = [p for p in parts if len(p)]
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def load_levels(symbol: str, start: str | None = None, end: str | None = None) -> pd.DataFrame:
    return read_range(config.LEVELS_DIR, symbol, start, end)


def load_daily(symbol: str, start: str | None = None, end: str | None = None) -> pd.DataFrame:
    return read_range(config.DAILY_DIR, symbol, start, end)


def load_ohlcv(path: str | Path) -> pd.DataFrame:
    """Nạp nến ngày từ Excel/CSV dạng AmiBroker (Ticker, Date/Time, Open, High, Low, Close, Volume)
    hoặc cột chuẩn Date, Open, High, Low, Close, Volume. Trả về cột chuẩn."""
    path = Path(path)
    df = pd.read_excel(path) if path.suffix.lower() in (".xlsx", ".xls") else pd.read_csv(path)
    ren = {"Date/Time": "Date", "Ticker": "Symbol", "Market": "Exchange"}
    df = df.rename(columns=ren)
    df["Date"] = pd.to_datetime(df["Date"]).dt.normalize()
    if "Exchange" in df:
        df["Exchange"] = df["Exchange"].replace({"HSX": "HOSE"})
    return df.sort_values("Date").reset_index(drop=True)
