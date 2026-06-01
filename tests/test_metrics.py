"""metrics 순수 함수 테스트.

metrics 는 streamlit/네트워크에 의존하지 않으므로 그대로 단위 테스트할 수 있다.
실행: pytest -q
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import metrics as M


def _series(values, start="2024-01-01", freq="B"):
    idx = pd.date_range(start=start, periods=len(values), freq=freq)
    return pd.Series(values, index=idx, dtype="float64")


# ---------------------------------------------------------------- normalize
def test_normalize_to_100_basic():
    s = _series([50, 75, 100])
    out = M.normalize_to_100(s)
    assert out.iloc[0] == pytest.approx(100.0)
    assert out.iloc[1] == pytest.approx(150.0)
    assert out.iloc[2] == pytest.approx(200.0)


def test_normalize_to_100_empty():
    out = M.normalize_to_100(pd.Series(dtype="float64"))
    assert out.empty


def test_normalize_to_100_zero_base_returns_original():
    s = _series([0, 10, 20])
    out = M.normalize_to_100(s)
    pd.testing.assert_series_equal(out, s)


# ---------------------------------------------------------------- excess
def test_excess_return_series_zero_when_identical():
    s = _series([100, 110, 121])
    ex = M.excess_return_series(s, s.copy())
    assert ex.iloc[0] == pytest.approx(0.0)
    assert ex.iloc[-1] == pytest.approx(0.0)


def test_excess_return_series_outperformance():
    stock = _series([100, 120])   # +20%
    index = _series([100, 110])   # +10%
    ex = M.excess_return_series(stock, index)
    assert ex.iloc[-1] == pytest.approx(10.0)  # 20% - 10% = 10%p


# ---------------------------------------------------------------- pct_change_over
def test_pct_change_over_days_boundary():
    # 연속 영업일 → "어제(1일)" 는 직전 거래일 대비
    s = _series([100, 101, 103])
    chg = M._pct_change_over(s, days=1)
    assert chg == pytest.approx((103 / 101 - 1) * 100.0)


def test_pct_change_over_ytd():
    # 작년 마지막 거래일 + 올해 며칠
    idx = pd.to_datetime(["2023-12-29", "2024-01-02", "2024-01-03"])
    s = pd.Series([100.0, 110.0, 120.0], index=idx)
    chg = M._pct_change_over(s, days=None)  # YTD: 작년 마지막 종가(100) 기준
    assert chg == pytest.approx(20.0)


def test_pct_change_over_empty():
    assert M._pct_change_over(pd.Series(dtype="float64"), days=1) is None


# ---------------------------------------------------------------- ma_rate
def test_ma_rate_insufficient_data():
    assert M.ma_rate(_series([1, 2, 3]), window=14) is None


def test_ma_rate_constant_series_is_zero():
    s = _series([100.0] * 20)
    assert M.ma_rate(s, window=14) == pytest.approx(0.0)


def test_ma_rate_excess_sign():
    # 종목은 매일 상승, 지수는 평평 → 종목 평균선 기울기가 더 가팔라 초과>0
    stock = _series(list(np.linspace(100, 140, 30)))
    index = _series([100.0] * 30)
    sr, ir, ex = M.ma_rate_excess(stock, index, window=14)
    assert sr is not None and ir == pytest.approx(0.0)
    assert ex == pytest.approx(sr)
    assert ex > 0
