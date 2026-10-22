"""Báo cáo cung cầu một mã: biểu đồ PNG + tóm tắt markdown.

    python -m vnflow.report SSI                               # từ khớp lệnh đã thu thập (data/levels, data/daily)
    python -m vnflow.report SSI --ohlcv data/ohlcv/SSI.xlsx --anchors 2025-08-29 2026-07-28
    python -m vnflow.report SSI --ohlcv ... --adjust 2026-07-10:0.7992
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from . import analysis, config, quality, store

GREY, BLUE, GREEN, RED = "#9a9a94", "#2b6fd6", "#3f9e5a", "#c8504b"


def _fmt(x: float) -> str:
    return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def plot_profile(p: pd.DataFrame, va: dict, title: str, out: Path, last: float | None = None) -> None:
    fig, ax = plt.subplots(figsize=(8, max(4, len(p) * 0.18)))
    h = (p["price"].diff().median() or 1) * 0.85
    if {"buy_vol", "sell_vol"} <= set(p.columns):
        ax.barh(p["price"], p["buy_vol"], height=h, color=GREEN, alpha=0.7, label="Mua chủ động")
        ax.barh(p["price"], p["sell_vol"], left=p["buy_vol"], height=h, color=RED, alpha=0.7, label="Bán chủ động")
        if "auction_vol" in p:
            ax.barh(p["price"], p["auction_vol"], left=p["buy_vol"] + p["sell_vol"], height=h, color=GREY, alpha=0.6, label="ATO/ATC")
        ax.legend(loc="lower right", frameon=False)
    else:
        ax.barh(p["price"], p["vol"], height=h, color=GREY)
    ax.axhline(va["poc"], color=BLUE, lw=1.5, label="POC")
    ax.axhspan(va["val"], va["vah"], color=BLUE, alpha=0.06)
    if last:
        ax.axhline(last, color="black", ls="--", lw=1)
    ax.set_title(title, loc="left", fontsize=11)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(out, dpi=140); plt.close(fig)


def plot_price(o: pd.DataFrame, anchors: list[str], title: str, out: Path) -> None:
    fig, (a1, a2, a3) = plt.subplots(3, 1, figsize=(10, 7), sharex=True, gridspec_kw={"height_ratios": [3, 1, 1]})
    a1.plot(o["Date"], o["Close"], color=BLUE, lw=1.4, label="Đóng cửa")
    for a in anchors:
        a1.plot(o["Date"], analysis.avwap_series(o, a), ls="--", lw=1, label=f"AVWAP từ {a}")
    a1.legend(frameon=False, fontsize=8); a1.set_title(title, loc="left", fontsize=11)
    a2.bar(o["Date"], o["Volume"] / 1e6, color=GREY, width=1); a2.set_ylabel("KL (tr)")
    c = analysis.cmf(o)
    a3.bar(o["Date"], c, color=[GREEN if v >= 0 else RED for v in c.fillna(0)], width=1, alpha=0.7); a3.set_ylabel("CMF20")
    for a in (a1, a2, a3):
        a.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(out, dpi=140); plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("symbol")
    ap.add_argument("--start"); ap.add_argument("--end")
    ap.add_argument("--ohlcv", help="file nến ngày (xlsx/csv)")
    ap.add_argument("--price-unit", type=float, default=1000.0, help="1000 nếu giá nến tính bằng nghìn đồng")
    ap.add_argument("--adjust", nargs="*", default=[], help="YYYY-MM-DD:hệ_số, nhân giá trước ngày đó")
    ap.add_argument("--anchors", nargs="*", default=[], help="các mốc AVWAP")
    ap.add_argument("--step", type=float, default=0.5, help="nấc profile ước lượng (đơn vị giá nến)")
    a = ap.parse_args()
    sym = a.symbol.upper()
    out = config.REPORTS / sym
    out.mkdir(parents=True, exist_ok=True)
    md = [f"# Báo cáo cung cầu {sym}", ""]

    lv = store.load_levels(sym, a.start, a.end)
    if len(lv):
        p = analysis.profile_from_levels(lv)
        va = analysis.value_area(p)
        dl = store.load_daily(sym, a.start, a.end).sort_values("date")
        last = float(dl["close"].iloc[-1])
        plot_profile(p, va, f"{sym}: khớp lệnh theo bước giá {lv['date'].min()}–{lv['date'].max()}", out / "profile_khop_lenh.png", last)
        md += ["## Khớp lệnh thật (data/levels)",
               f"- Kỳ: {lv['date'].min()} → {lv['date'].max()} ({lv['date'].nunique()} phiên)",
               f"- POC {_fmt(va['poc'])} · Value Area {_fmt(va['val'])}–{_fmt(va['vah'])} · giá cuối {_fmt(last)}",
               f"- Delta kỳ: {int(p['delta'].sum()):,} cp · lô lớn mua/bán: {int(p['large_buy_vol'].sum()):,} / {int(p['large_sell_vol'].sum()):,}",
               "", "![profile](profile_khop_lenh.png)", ""]

    if a.ohlcv:
        o = store.load_ohlcv(a.ohlcv)
        flags = quality.check_ohlcv(o, a.price_unit)  # kiểm tra dữ liệu GỐC, trước khi hiệu chỉnh
        n_tick = 0
        if len(flags):
            flags["Date"] = pd.to_datetime(flags["Date"]).dt.strftime("%Y-%m-%d")
            flags["ret"] = flags["ret"].map(lambda r: "" if pd.isna(r) else f"{r:+.1%}")
            n_tick = flags["flags"].str.contains("bước giá").sum()
            flags = flags[~flags["flags"].eq("giá lẻ bước giá → dữ liệu đã điều chỉnh lùi")]
        for adj in a.adjust:
            d, f = adj.split(":")
            o = quality.adjust_before(o, d, float(f))
        p = analysis.profile_from_ohlcv(o, a.step)
        va = analysis.value_area(p)
        last = float(o["Close"].iloc[-1])
        plot_profile(p, va, f"{sym}: profile ước lượng từ nến ngày", out / "profile_uoc_luong.png", last)
        plot_price(o, a.anchors, f"{sym}: giá, AVWAP, KL, CMF", out / "gia_avwap_cmf.png")
        v = analysis.vsa(o).tail(20).copy()
        v["Date"] = v["Date"].dt.strftime("%Y-%m-%d")
        tick_note = f"{n_tick} phiên có giá lẻ bước giá (dữ liệu đã điều chỉnh lùi) — không liệt kê." if n_tick else ""
        md += ["## Nến ngày (ước lượng)",
               f"- POC {_fmt(va['poc'])} · Value Area {_fmt(va['val'])}–{_fmt(va['vah'] + a.step)} · giá cuối {_fmt(last)}"]
        for an in a.anchors:
            md.append(f"- AVWAP từ {an}: {_fmt(analysis.avwap(o, an))}")
        md += ["", "![profile](profile_uoc_luong.png)", "", "![price](gia_avwap_cmf.png)", "",
               "### Kiểm tra dữ liệu gốc", flags.to_markdown(index=False) if len(flags) else "Không phát hiện bất thường lớn.",
               "", tick_note, f"Hiệu chỉnh đã áp dụng: {', '.join(a.adjust) or 'không'}", "",
               "### VSA 20 phiên gần nhất (nhãn là gợi ý, cần đọc bối cảnh)",
               v[["Date", "Close", "rv", "rs", "clv", "vsa"]].round(2).to_markdown(index=False), ""]
    (out / "README.md").write_text("\n".join(md), encoding="utf-8")
    print(f"Đã ghi {out}")


if __name__ == "__main__":
    main()
