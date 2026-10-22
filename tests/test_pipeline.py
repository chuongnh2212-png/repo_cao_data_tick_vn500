"""Kiểm thử offline. Bản ghi mẫu theo đúng định dạng API DSC (SSI, 22/10/2026)."""
import json
from pathlib import Path

import pandas as pd
import pytest

from vnflow import aggregate, analysis, dsc, quality

FIX = Path(__file__).parent / "fixtures"


def rec(seq, t, side, price, vol, acc, buy, sell, ref=20400):
    r = {"sequenceMsg": str(seq), "tradingdate": "22/10/2026", "symbol": "SSI", "formattedTime": t,
         "formattedMatchPrice": f"{price}.0", "formattedVol": str(vol), "formattedAccVol": str(acc),
         "formattedAccVal": "0.0", "totalBuyVol": str(buy), "totalSellVol": str(sell),
         "averagePrice": 0, "reference": ref, "exchange": "HOSE"}
    if side:
        r["lastColor"] = side
    return r


@pytest.fixture
def day():
    """Một ngày tự nhất quán: ATO, khớp liên tục, ATC."""
    rows = [rec(1, "09:15:00", None, 20450, 201800, 201800, 0, 0),
            rec(2, "09:15:01", "S", 20450, 20600, 222400, 0, 20600),
            rec(3, "09:15:13", "B", 20450, 300, 222700, 300, 20600),
            rec(4, "10:01:00", "B", 20500, 80000, 302700, 80300, 20600),
            rec(5, "13:30:00", "S", 20350, 50000, 352700, 80300, 70600),
            rec(6, "14:45:00", None, 20400, 100000, 452700, 80300, 70600)]
    return dsc.parse(rows)


def test_parse_real_sample():
    raw = json.loads((FIX / "dsc_ssi_sample.json").read_text(encoding="utf-8"))
    df = dsc.parse(raw["d"])
    assert list(df["side"]) == ["U", "S", "B", "S", "B"]
    assert df["session"].iloc[0] == "ATO"
    assert df["price"].iloc[0] == 20450 and df["vol"].iloc[1] == 20600


def test_sessions_and_quality(day):
    assert list(day["session"]) == ["ATO", "continuous", "continuous", "continuous", "continuous", "ATC"]
    assert quality.check_trades(day) == []


def test_quality_detects_missing(day):
    issues = quality.check_trades(day.drop(index=3))
    assert any(i["check"] == "acc_vol" for i in issues)


def test_levels_and_summary(day):
    lv = aggregate.price_levels(day)
    r = lv.set_index("price").loc[20450]
    assert (r.vol, r.buy_vol, r.sell_vol, r.auction_vol) == (222700, 300, 20600, 201800)
    s = aggregate.daily_summary(day).iloc[0]
    assert s.delta == 80300 - 70600 and s.ato_vol == 201800 and s.atc_vol == 100000
    assert s.poc == 20450 and s.close == 20400


def test_large_lots(day):
    lt = aggregate.large_trades(day)
    assert 4 in set(lt["seq"])  # 80.000 cp × 20.500 = 1,64 tỷ ≥ 1 tỷ


def test_value_area():
    p = pd.DataFrame({"price": [1, 2, 3, 4, 5], "vol": [1, 5, 10, 3, 1]})
    va = analysis.value_area(p)
    assert va["poc"] == 3 and va["val"] == 2 and va["vah"] == 3


def test_ohlcv_checks_and_adjust():
    o = pd.DataFrame({"Date": pd.date_range("2026-07-08", periods=3),
                      "Open": [27.1, 26.9, 21.6], "High": [27.2, 27.0, 21.6],
                      "Low": [26.8, 26.8, 21.2], "Close": [27.1, 26.95, 21.22], "Volume": [1, 1, 1]})
    f = quality.check_ohlcv(o)
    assert any("vượt biên độ" in x for x in f["flags"])
    adj = quality.adjust_before(o, "2026-07-10", 18.82 / 23.55)
    assert abs(adj["Close"].pct_change().iloc[-1]) < 0.07
