"""Công cụ phân tích cung cầu: Volume Profile, AVWAP, VSA, CMF, delta/CVD.

Hai nguồn đầu vào:
- `levels`: bảng theo bước giá từ khớp lệnh thật (data/levels) → profile CHÍNH XÁC, có mua/bán chủ động.
- `ohlcv`: nến ngày (Date, Open, High, Low, Close, Volume) → profile ƯỚC LƯỢNG.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# ---------- Volume Profile ----------

def profile_from_levels(levels: pd.DataFrame, bin_size: float | None = None) -> pd.DataFrame:
    """Cộng dồn bảng bước giá qua nhiều ngày. bin_size (VND) để gộp nấc; None = giữ từng bước giá."""
    x = levels.copy()
    x["bin"] = x["price"] if not bin_size else np.floor(x["price"] / bin_size) * bin_size
    p = x.groupby("bin", as_index=False)[["vol", "buy_vol", "sell_vol", "auction_vol", "large_buy_vol", "large_sell_vol"]].sum()
    p["delta"] = p["buy_vol"] - p["sell_vol"]
    return p.rename(columns={"bin": "price"}).sort_values("price").reset_index(drop=True)


def profile_from_ohlcv(ohlcv: pd.DataFrame, step: float, points: int = 50) -> pd.DataFrame:
    """Ước lượng profile từ nến ngày: rải KL mỗi phiên trên [Low, High], trọng số tam giác
    đỉnh tại giá đại diện (H+L+C)/3, sàn 5%. Đây là ƯỚC LƯỢNG, không phải số khớp thật."""
    lo_all = np.floor(ohlcv["Low"].min() / step) * step
    bins = np.arange(lo_all, ohlcv["High"].max() + step, step)
    vol = np.zeros(len(bins))
    for r in ohlcv.itertuples():
        lo, hi, tp = r.Low, r.High, (r.High + r.Low + r.Close) / 3
        if hi > lo:
            g = np.linspace(lo, hi, points)
            w = np.maximum(1 - np.abs(g - tp) / ((hi - lo) / 2), 0.05)
        else:
            g, w = np.array([lo]), np.array([1.0])
        w = w / w.sum() * r.Volume
        idx = np.clip(((g - bins[0]) // step).astype(int), 0, len(bins) - 1)
        np.add.at(vol, idx, w)
    return pd.DataFrame({"price": bins, "vol": vol})


def value_area(profile: pd.DataFrame, pct: float = 0.70) -> dict:
    """POC và Value Area: mở rộng từ POC, mỗi bước lấy nấc kề lớn hơn, đến khi đủ pct."""
    p = profile.sort_values("price").reset_index(drop=True)
    v = p["vol"].to_numpy(dtype=float)
    poc = int(v.argmax())
    lo = hi = poc
    acc, total = v[poc], v.sum()
    while acc < pct * total and (lo > 0 or hi < len(v) - 1):
        a = v[lo - 1] if lo > 0 else -1
        b = v[hi + 1] if hi < len(v) - 1 else -1
        if a >= b:
            lo -= 1; acc += a
        else:
            hi += 1; acc += b
    return {"poc": float(p.loc[poc, "price"]), "val": float(p.loc[lo, "price"]),
            "vah": float(p.loc[hi, "price"]), "share": float(acc / total)}


def nodes(profile: pd.DataFrame, smooth: int = 3) -> pd.DataFrame:
    """Đánh dấu HVN/LVN: cực đại/cực tiểu cục bộ của KL đã làm trơn."""
    p = profile.sort_values("price").reset_index(drop=True).copy()
    s = p["vol"].rolling(smooth, center=True, min_periods=1).mean()
    p["node"] = ""
    p.loc[(s > s.shift(1)) & (s >= s.shift(-1)) & (s > s.median()), "node"] = "HVN"
    p.loc[(s < s.shift(1)) & (s <= s.shift(-1)) & (s < s.median()), "node"] = "LVN"
    return p


# ---------- Giá vốn đám đông ----------

def avwap(ohlcv: pd.DataFrame, anchor: str) -> float:
    """Anchored VWAP từ phiên `anchor` (YYYY-MM-DD) đến cuối dữ liệu, giá đại diện (H+L+C)/3."""
    d = ohlcv[pd.to_datetime(ohlcv["Date"]) >= pd.Timestamp(anchor)]
    tp = (d["High"] + d["Low"] + d["Close"]) / 3
    return float((tp * d["Volume"]).sum() / d["Volume"].sum())


def avwap_series(ohlcv: pd.DataFrame, anchor: str) -> pd.Series:
    d = ohlcv.copy()
    m = pd.to_datetime(d["Date"]) >= pd.Timestamp(anchor)
    tp = (d["High"] + d["Low"] + d["Close"]) / 3
    num = (tp * d["Volume"]).where(m).cumsum()
    den = d["Volume"].where(m).cumsum()
    return num / den


# ---------- VSA và dòng tiền ----------

def vsa(ohlcv: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    """Thêm rv (KL / TB n), rs (biên độ / TB n), clv (vị trí đóng cửa −1..+1), ret và nhãn gợi ý.
    Nhãn chỉ là gợi ý để người phân tích kiểm tra bằng bối cảnh và phiên sau."""
    d = ohlcv.sort_values("Date").reset_index(drop=True).copy()
    spread = d["High"] - d["Low"]
    d["rv"] = d["Volume"] / d["Volume"].rolling(n).mean().shift(1)
    d["rs"] = spread / spread.rolling(n).mean().shift(1)
    d["clv"] = ((d["Close"] - d["Low"]) - (d["High"] - d["Close"])) / spread.replace(0, np.nan)
    d["ret"] = d["Close"].pct_change()
    lab = pd.Series("", index=d.index)
    up, down = d["ret"] > 0, d["ret"] < 0
    lab[(d.rv >= 1.8) & (d.rs >= 1.3) & up & (d.clv >= 0.5)] = "SOS?"
    lab[(d.rv >= 1.8) & (d.rs >= 1.3) & down & (d.clv <= -0.5)] = "SOW?"
    lab[(d.rv >= 1.8) & (d.rs < 1.3) & (d.clv.abs() < 0.4)] = "nỗ lực không kết quả?"
    lab[(d.rv >= 1.8) & down & (d.clv >= 0.3)] = "stopping volume?"
    lab[(d.rv <= 0.7) & (d.rs <= 0.8) & up] = "no demand?"
    lab[(d.rv <= 0.7) & (d.rs <= 0.8) & down] = "no supply?"
    lab[(d.High > d.High.shift(1).rolling(10).max()) & (d.clv <= -0.6)] = "upthrust?"
    d["vsa"] = lab
    return d


def cmf(ohlcv: pd.DataFrame, n: int = 20) -> pd.Series:
    d = ohlcv.sort_values("Date")
    spread = (d["High"] - d["Low"]).replace(0, np.nan)
    clv = (((d["Close"] - d["Low"]) - (d["High"] - d["Close"])) / spread).fillna(0)
    mfv = clv * d["Volume"]
    return mfv.rolling(n).sum() / d["Volume"].rolling(n).sum()


def cvd(daily_summary: pd.DataFrame) -> pd.Series:
    """Delta tích lũy theo ngày từ khớp lệnh thật (data/daily)."""
    d = daily_summary.sort_values("date")
    return d["delta"].cumsum()
