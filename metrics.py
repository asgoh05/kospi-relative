"""수익률/상대강도 지표 계산 모듈 (순수 함수, 테스트 가능)."""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

# (라벨, 기준 캘린더 일수). YTD 는 None 으로 따로 처리.
PERIODS: list[tuple[str, int | None]] = [
    ("어제", 1),
    ("1주", 7),
    ("1개월", 30),
    ("3개월", 91),
    ("6개월", 182),
    ("YTD", None),
    ("1년", 365),
]


def normalize_to_100(s: pd.Series) -> pd.Series:
    """첫 유효값을 100 으로 맞춰 정규화."""
    s = s.dropna()
    if s.empty:
        return s
    base = s.iloc[0]
    if base == 0:
        return s
    return s / base * 100.0


def moving_average(s: pd.Series, window: int = 14) -> pd.Series:
    """window 일 단순 이동평균선 (앞쪽 NaN 제거)."""
    return s.dropna().rolling(window).mean().dropna()


def ma_rate(s: pd.Series, window: int = 14) -> float | None:
    """window 일 이동평균선의 최근 1거래일 등락률(%) = (MA_t/MA_{t-1} - 1)*100.

    이동평균을 먼저 구해 노이즈를 줄인 뒤, 그 '평균선' 자체의 하루치 기울기를 본다.
    데이터가 부족하면 None.
    """
    ma = moving_average(s, window)
    if len(ma) < 2 or ma.iloc[-2] == 0:
        return None
    return (ma.iloc[-1] / ma.iloc[-2] - 1.0) * 100.0


def ma_rate_excess(
    stock: pd.Series, index: pd.Series, window: int = 14
) -> tuple[float | None, float | None, float | None]:
    """종목/지수 각각의 이동평균선 등락률과 그 차이(초과, %p)를 반환.

    (stock_ma_rate, index_ma_rate, excess) — excess = stock - index.
    """
    sr = ma_rate(stock, window)
    ir = ma_rate(index, window)
    ex = (sr - ir) if (sr is not None and ir is not None) else None
    return sr, ir, ex


def align(a: pd.Series, b: pd.Series) -> tuple[pd.Series, pd.Series]:
    """두 시계열을 공통 날짜로 정렬."""
    df = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    return df["a"], df["b"]


def excess_return_series(stock: pd.Series, index: pd.Series) -> pd.Series:
    """지수 대비 누적 초과수익률(%) 시계열.

    같은 시작점 기준 (종목 누적수익률 - 지수 누적수익률).
    값이 0 이면 지수와 동일하게 움직였다는 의미.
    """
    s, i = align(stock, index)
    if s.empty:
        return pd.Series(dtype="float64")
    s_ret = s / s.iloc[0] - 1.0
    i_ret = i / i.iloc[0] - 1.0
    return (s_ret - i_ret) * 100.0


def _value_asof(s: pd.Series, target: pd.Timestamp) -> float | None:
    """target 날짜 또는 그 이전의 가장 가까운 값."""
    s = s.dropna()
    if s.empty:
        return None
    idx = s.index[s.index <= target]
    if len(idx) == 0:
        return None
    return float(s.loc[idx[-1]])


def _pct_change_over(s: pd.Series, days: int | None) -> float | None:
    s = s.dropna()
    if s.empty:
        return None
    last_date = s.index[-1]
    last_val = float(s.iloc[-1])
    if days is None:  # YTD
        start = pd.Timestamp(year=last_date.year, month=1, day=1)
        # 연초 직전(작년 마지막 거래일) 종가 기준
        prior = s.index[s.index < start]
        if len(prior):
            base = float(s.loc[prior[-1]])
        else:
            base = float(s.iloc[0])
    else:
        target = last_date - pd.Timedelta(days=days)
        base = _value_asof(s, target)
    if base is None or base == 0:
        return None
    return (last_val / base - 1.0) * 100.0


def period_returns(stock: pd.Series, index: pd.Series) -> pd.DataFrame:
    """기간별 종목 수익률 / 지수 수익률 / 초과수익률(%) 표."""
    rows = []
    for label, days in PERIODS:
        s_ret = _pct_change_over(stock, days)
        i_ret = _pct_change_over(index, days)
        excess = None
        if s_ret is not None and i_ret is not None:
            excess = s_ret - i_ret
        rows.append(
            {
                "기간": label,
                "종목": s_ret,
                "지수": i_ret,
                "초과": excess,
            }
        )
    return pd.DataFrame(rows)
