"""Nạp lịch sử MetaKit (xuất từ AmiBroker bằng amibroker/vnflow_export.afl) vào dự án.

    python -m vnflow.metakit C:\\vnflow\\metakit_export          # thư mục chứa <MÃ>.csv
    python -m vnflow.metakit metakit_export.zip                  # hoặc file zip

Ghi ra data/metakit/<MÃ>.parquet (một file mỗi mã, gộp với dữ liệu cũ theo ngày)
và in báo cáo kiểm tra quy ước trường (_CC, _NN) để phát hiện nếu MetaKit đổi thứ tự trường.

Cột:
    open, high, low, close   giá (nghìn đồng, theo MetaKit — có thể đã điều chỉnh)
    volume                   KL giao dịch; shares_out = số CP lưu hành
    cc_dat_ban, cc_dat_mua   KL đặt bán / đặt mua;  cc_lenh_ban, cc_lenh_mua = số lệnh đặt
    nn_kl_ban, nn_kl_mua     KL khối ngoại bán / mua; nn_gt_ban, nn_gt_mua = giá trị (đơn vị theo MetaKit)
"""
from __future__ import annotations

import argparse
import io
import zipfile
from pathlib import Path

import pandas as pd

from . import config

METAKIT_DIR = config.DATA / "metakit"
NUM = ["open", "high", "low", "close", "volume", "shares_out", "cc_dat_ban", "cc_dat_mua",
       "cc_lenh_ban", "cc_lenh_mua", "nn_kl_ban", "nn_kl_mua", "nn_gt_ban", "nn_gt_mua"]


def _read_csv(buf) -> pd.DataFrame:
    df = pd.read_csv(buf, dtype={"symbol": str})
    df["date"] = pd.to_datetime(df["date"]).dt.date
    for c in NUM:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def read_source(src: Path) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    if src.suffix.lower() == ".zip":
        with zipfile.ZipFile(src) as z:
            for name in z.namelist():
                if name.lower().endswith(".csv"):
                    df = _read_csv(io.BytesIO(z.read(name)))
                    if len(df):
                        out[df["symbol"].iloc[0].upper()] = df
    else:
        for f in sorted(src.glob("*.csv")):
            df = _read_csv(f)
            if len(df):
                out[df["symbol"].iloc[0].upper()] = df
    return out


def sanity(df: pd.DataFrame) -> dict:
    """Kiểm tra quy ước trường. Tỷ lệ vi phạm cao → MetaKit có thể xếp trường khác tài liệu."""
    x = df.dropna(subset=["volume"])
    x = x[x["volume"] > 0]
    n = max(len(x), 1)
    nn_ok = x.dropna(subset=["nn_kl_mua", "nn_kl_ban"])
    cc_ok = x.dropna(subset=["cc_dat_mua", "cc_dat_ban"])
    return {
        "rows": int(len(df)), "from": str(df["date"].min()), "to": str(df["date"].max()),
        "has_cc_pct": round(100 * len(cc_ok) / n, 1), "has_nn_pct": round(100 * len(nn_ok) / n, 1),
        # khối ngoại mua (hoặc bán) không thể vượt tổng KL khớp
        "nn_gt_volume_pct": round(100 * ((nn_ok["nn_kl_mua"] > nn_ok["volume"] * 1.001) |
                                         (nn_ok["nn_kl_ban"] > nn_ok["volume"] * 1.001)).mean(), 2) if len(nn_ok) else None,
        # KL khớp thường không vượt KL đặt mua
        "vol_gt_dat_mua_pct": round(100 * (cc_ok["volume"] > cc_ok["cc_dat_mua"] * 1.001).mean(), 2) if len(cc_ok) else None,
        # giá trị NN / KL NN ≈ giá → kiểm tra đơn vị giá trị
        "nn_gt_per_share_median": float((nn_ok["nn_gt_mua"] / nn_ok["nn_kl_mua"]).replace([float("inf")], pd.NA).median())
                                   if len(nn_ok) and (nn_ok["nn_kl_mua"] > 0).any() else None,
        "close_median": float(x["close"].median()) if len(x) else None,
    }


def save(sym: str, df: pd.DataFrame, base: Path = METAKIT_DIR) -> Path:
    base.mkdir(parents=True, exist_ok=True)
    p = base / f"{sym}.parquet"
    if p.exists():
        old = pd.read_parquet(p)
        df = pd.concat([old[~old["date"].isin(set(df["date"]))], df], ignore_index=True)
    df = df.sort_values("date").reset_index(drop=True)
    df.to_parquet(p, index=False, compression="zstd")
    return p


def load(sym: str, base: Path = METAKIT_DIR) -> pd.DataFrame:
    p = base / f"{sym.upper()}.parquet"
    return pd.read_parquet(p) if p.exists() else pd.DataFrame()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", help="thư mục chứa <MÃ>.csv hoặc file .zip")
    a = ap.parse_args()
    data = read_source(Path(a.source))
    rep = []
    for sym, df in data.items():
        save(sym, df)
        rep.append({"symbol": sym, **sanity(df)})
    r = pd.DataFrame(rep)
    print(f"Đã nạp {len(r)} mã vào {METAKIT_DIR}")
    if len(r):
        print(r.describe(include="all").T[["count", "mean", "min", "max"]].to_string())
        bad = r[(r["nn_gt_volume_pct"].fillna(0) > 1) | (r["vol_gt_dat_mua_pct"].fillna(0) > 20)]
        if len(bad):
            print("\nCẢNH BÁO: các mã nghi sai quy ước trường _CC/_NN:")
            print(bad[["symbol", "nn_gt_volume_pct", "vol_gt_dat_mua_pct"]].to_string(index=False))


if __name__ == "__main__":
    main()
