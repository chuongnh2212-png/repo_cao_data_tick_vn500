"""Chạy thử toàn bộ luồng thu thập với API giả lập (không cần mạng)."""
from datetime import date, datetime

import pandas as pd

from vnflow import analysis, collect, config, dsc, store
from test_pipeline import rec


def test_collect_end_to_end(tmp_path, monkeypatch):
    for name in ["LEVELS_DIR", "DAILY_DIR", "LARGE_DIR", "QUALITY_DIR", "RAW_DIR"]:
        monkeypatch.setattr(config, name, tmp_path / name)
    monkeypatch.setattr(config, "REQUEST_DELAY_SEC", 0)
    monkeypatch.setattr(dsc, "today_vn", lambda: date(2026, 10, 22))

    def fake_fetch(sym, session=None):
        if sym == "NODATA":
            return dsc.parse([])
        rows = [rec(1, "09:15:00", None, 20450, 1000, 1000, 0, 0),
                rec(2, "10:00:00", "B", 20500, 60000, 61000, 60000, 0),
                rec(3, "14:45:00", None, 20450, 500, 61500, 60000, 0)]
        for r in rows:
            r["symbol"] = sym
        return dsc.parse(rows)

    monkeypatch.setattr(dsc, "fetch", fake_fetch)
    s = collect.run(["SSI", "MBB", "NODATA"], allow_partial=True)
    assert s["collected"] == 2 and s["skipped"] == ["NODATA"] and s["issues"] == 0
    lv = store.read_range(config.LEVELS_DIR, "MBB")
    assert set(lv["price"]) == {20450, 20500}
    p = analysis.profile_from_levels(lv)
    assert analysis.value_area(p)["poc"] == 20500


def test_amibroker_export(tmp_path, monkeypatch):
    from vnflow import aggregate, amibroker
    root = tmp_path / "data"
    rows = [rec(1, "09:15:00", None, 20450, 1000, 1000, 0, 0),
            rec(2, "10:00:00", "B", 20500, 60000, 61000, 60000, 0),
            rec(3, "14:45:00", None, 20450, 500, 61500, 60000, 0)]
    t = dsc.parse(rows)
    d = date(2026, 10, 22)
    store.write_day(aggregate.daily_summary(t), root / "daily", d)
    store.write_day(aggregate.price_levels(t), root / "levels", d)
    r = amibroker.export(None, tmp_path / "out", [root])
    assert r["symbols"] == 1
    daily = pd.read_csv(tmp_path / "out" / "vnflow_daily.csv")
    row = daily.iloc[0]
    assert row.Ticker == "SSI_OF" and str(row.Date) == "20261022" and row.Aux1 == 60000 and row.Close == 20.45
    lv = pd.read_csv(tmp_path / "out" / "levels" / "SSI.csv")
    assert list(lv.datenum.unique()) == [1261022] and set(lv.price) == {20.45, 20.5}


def test_write_day_merges(tmp_path):
    d = date(2026, 10, 22)
    store.write_day(pd.DataFrame({"symbol": ["A", "B"], "x": [1, 2]}), tmp_path, d)
    store.write_day(pd.DataFrame({"symbol": ["B"], "x": [9]}), tmp_path, d)
    out = store.read_range(tmp_path).sort_values("symbol")
    assert list(out.x) == [1, 9]


def test_metakit_import(tmp_path):
    from vnflow import metakit
    src = tmp_path / "exp"; src.mkdir()
    (src / "SSI.csv").write_text(
        "symbol,date,open,high,low,close,volume,shares_out,cc_dat_ban,cc_dat_mua,cc_lenh_ban,cc_lenh_mua,nn_kl_ban,nn_kl_mua,nn_gt_ban,nn_gt_mua\n"
        "SSI,2015-01-05,10.1000,10.3000,10.0000,10.2000,1000000,350000000,1500000,1800000,900,1100,50000,80000,510.0000,816.0000\n"
        "SSI,2015-01-06,10.2000,10.4000,10.1000,10.3000,900000,350000000,,,,,,,,\n", encoding="utf-8")
    data = metakit.read_source(src)
    assert set(data) == {"SSI"} and len(data["SSI"]) == 2
    rep = metakit.sanity(data["SSI"])
    assert rep["has_nn_pct"] == 50.0 and rep["nn_gt_volume_pct"] == 0
    p = metakit.save("SSI", data["SSI"], tmp_path / "mk")
    assert len(metakit.load("SSI", tmp_path / "mk")) == 2


def test_metakit_fill_fix():
    from vnflow import metakit
    df = pd.DataFrame({"nn_kl_ban": [9500, 10000], "nn_kl_mua": [9500, 0], "nn_gt_ban": [0, 118e6], "nn_gt_mua": [111.44e6, 0],
                       "cc_dat_ban": [274300, 5], "cc_dat_mua": [206100, 5], "cc_lenh_ban": [118, 0], "cc_lenh_mua": [145, 3]})
    f = metakit.fix_fill(df)
    assert list(f.nn_kl_ban) == [0, 10000] and list(f.nn_kl_mua) == [9500, 0]   # ABW 12/06/2023: mua ròng 9.500
    assert list(f.cc_dat_ban) == [274300, 0] and list(f.cc_dat_mua) == [206100, 5]
