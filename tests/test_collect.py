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
