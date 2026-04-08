"""Tests for connectors.adjust — DATA-03."""
import pandas as pd
import pytest

from connectors.adjust import adjust_ohlc


def test_adjust_ohlc_applies_rate(fake_ohlc_df):
    out = adjust_ohlc(fake_ohlc_df)
    # rows 0-2 have rate=2.0, rows 3-4 have rate=1.0
    assert out.loc[0, "adj_close"] == pytest.approx(10.2 * 2.0)
    assert out.loc[2, "adj_close"] == pytest.approx(12.2 * 2.0)
    assert out.loc[3, "adj_close"] == pytest.approx(13.2 * 1.0)
    assert out.loc[4, "adj_close"] == pytest.approx(14.2 * 1.0)
    assert out.loc[0, "adj_open"] == pytest.approx(10.0 * 2.0)
    assert out.loc[0, "adj_high"] == pytest.approx(10.5 * 2.0)
    assert out.loc[0, "adj_low"]  == pytest.approx(9.5 * 2.0)


def test_adjust_ohlc_preserves_raw_and_volume(fake_ohlc_df):
    out = adjust_ohlc(fake_ohlc_df)
    for col in ("openprice", "highestprice", "lowestprice", "closeprice", "totalvol"):
        assert col in out.columns
    assert (out["totalvol"] == fake_ohlc_df["totalvol"]).all()


def test_adjust_ohlc_missing_totaladjustrate_raises():
    df = pd.DataFrame({"closeprice": [1.0]})
    with pytest.raises(ValueError, match="totaladjustrate"):
        adjust_ohlc(df)


def test_adjust_ohlc_empty_df():
    df = pd.DataFrame(columns=[
        "openprice", "highestprice", "lowestprice", "closeprice", "totaladjustrate"
    ])
    out = adjust_ohlc(df)
    for col in ("adj_open", "adj_high", "adj_low", "adj_close"):
        assert col in out.columns
    assert len(out) == 0
