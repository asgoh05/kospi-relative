"""주가/지수 데이터 로딩 모듈.

FinanceDataReader 를 사용해 한국 주식과 코스피/코스닥 지수 시세를 가져온다.
네트워크/포맷 문제에 대비해 폴백(하드코딩) 경로를 함께 둔다.
"""

from __future__ import annotations

import datetime as dt
import os

import requests


def _disable_proxies() -> None:
    """모든 requests 세션이 프록시 자동탐지를 하지 않도록 만든다.

    원인: 일부 환경(예: Cursor 통합 터미널, macOS 시스템 프록시 설정)은
    죽은 로컬 프록시(127.0.0.1:xxxxx)를 주입한다. requests 는 환경변수뿐 아니라
    macOS 시스템 프록시 설정까지 자동으로 읽기 때문에, 환경변수만 지워서는 부족하다.
    여기서는 세션의 trust_env 를 끄고 NO_PROXY 를 전체로 설정해 항상 직접 연결한다.

    회사망 등에서 '반드시 프록시를 거쳐야' 인터넷이 되는 환경이라면
    USE_SYSTEM_PROXY=1 환경변수를 주면 이 동작을 끌 수 있다.
    """
    if os.environ.get("USE_SYSTEM_PROXY") == "1":
        return

    # 1) 죽은 로컬 프록시 환경변수 제거
    for var in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
                "http_proxy", "https_proxy", "all_proxy"):
        os.environ.pop(var, None)
    # 2) 모든 호스트를 프록시 우회 대상으로
    os.environ["NO_PROXY"] = "*"
    os.environ["no_proxy"] = "*"

    # 3) requests 세션이 환경/시스템 프록시를 신뢰하지 않도록 패치
    _orig_init = requests.sessions.Session.__init__

    def _patched_init(self, *args, **kwargs):
        _orig_init(self, *args, **kwargs)
        self.trust_env = False

    requests.sessions.Session.__init__ = _patched_init


_disable_proxies()

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402
import FinanceDataReader as fdr  # noqa: E402

# 비교 대상 지수 심볼 (FinanceDataReader)
INDEX_SYMBOL = {"KOSPI": "KS11", "KOSDAQ": "KQ11"}
INDEX_LABEL = {"KOSPI": "코스피", "KOSDAQ": "코스닥"}

# StockListing 이 실패할 때를 대비한 코스피 시총 상위 폴백 목록.
FALLBACK_TOP_KOSPI = [
    ("005930", "삼성전자"),
    ("000660", "SK하이닉스"),
    ("373220", "LG에너지솔루션"),
    ("207940", "삼성바이오로직스"),
    ("005380", "현대차"),
    ("000270", "기아"),
    ("068270", "셀트리온"),
    ("105560", "KB금융"),
    ("005490", "POSCO홀딩스"),
    ("035420", "NAVER"),
    ("012330", "현대모비스"),
    ("028260", "삼성물산"),
    ("055550", "신한지주"),
    ("035720", "카카오"),
    ("051910", "LG화학"),
    ("006400", "삼성SDI"),
    ("003670", "포스코퓨처엠"),
    ("086790", "하나금융지주"),
    ("015760", "한국전력"),
    ("032830", "삼성생명"),
]


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def load_krx_listing() -> pd.DataFrame:
    """KRX 전체 상장 종목 목록을 반환한다. (Code, Name, Market, Marcap)"""
    df = fdr.StockListing("KRX")
    df = df.rename(columns={c: c.strip() for c in df.columns})
    keep = [c for c in ["Code", "Name", "Market", "Marcap"] if c in df.columns]
    df = df[keep].dropna(subset=["Code", "Name"]).copy()
    df["Code"] = df["Code"].astype(str).str.zfill(6)
    return df


def _safe_listing() -> pd.DataFrame | None:
    try:
        df = load_krx_listing()
        if df is None or df.empty:
            return None
        return df
    except Exception:
        return None


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def get_top_kospi(n: int = 20) -> list[tuple[str, str]]:
    """코스피 시총 상위 n개 (코드, 이름) 목록."""
    df = _safe_listing()
    if df is not None and "Market" in df.columns:
        kospi = df[df["Market"].str.upper().str.contains("KOSPI", na=False)]
        if "Marcap" in kospi.columns and kospi["Marcap"].notna().any():
            kospi = kospi.sort_values("Marcap", ascending=False)
            rows = list(zip(kospi["Code"].head(n), kospi["Name"].head(n)))
            if rows:
                return rows
    return FALLBACK_TOP_KOSPI[:n]


def last_trading_date() -> dt.date:
    """가장 최근 영업일(주말이면 직전 금요일). 공휴일까지는 보정하지 않는 근사값."""
    d = dt.date.today()
    while d.weekday() >= 5:  # 5=토, 6=일
        d -= dt.timedelta(days=1)
    return d


@st.cache_data(ttl=60 * 30, show_spinner=False)
def prev_day_change(code: str) -> float | None:
    """전일 종가 대비 최근 종가 등락률(%). 데이터 부족 시 None."""
    s = get_close(code, dt.date.today() - dt.timedelta(days=14))
    if s is None or len(s) < 2:
        return None
    prev, last = float(s.iloc[-2]), float(s.iloc[-1])
    if prev == 0:
        return None
    return (last / prev - 1.0) * 100.0


@st.cache_data(ttl=60 * 30, show_spinner=False)
def get_top_kospi_change(n: int = 20) -> list[dict]:
    """코스피 시총 상위 n개를 전일 대비 등락률과 함께 반환.

    각 항목: {code, name, rank, chg} (chg: 전일 대비 등락률 %, None 가능)
    순위는 최근 영업일 종가 기준 시가총액 순서이며, 캐시 만료(30분)마다 갱신된다.
    """
    pairs = get_top_kospi(n)
    out = []
    for i, (code, name) in enumerate(pairs):
        out.append({"code": code, "name": name, "rank": i + 1,
                    "chg": prev_day_change(code)})
    return out


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def search_stocks(query: str, limit: int = 30) -> list[tuple[str, str, str]]:
    """이름 또는 코드로 종목 검색. (코드, 이름, 시장) 목록 반환."""
    df = _safe_listing()
    if df is None:
        return []
    q = query.strip()
    if not q:
        return []
    mask = df["Name"].str.contains(q, case=False, na=False) | df["Code"].str.contains(q, na=False)
    hit = df[mask].head(limit)
    market_col = hit["Market"] if "Market" in hit.columns else ["" for _ in range(len(hit))]
    return list(zip(hit["Code"], hit["Name"], market_col))


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def detect_market(code: str) -> str:
    """종목 코드의 시장(KOSPI/KOSDAQ)을 판별한다. 기본값은 KOSPI."""
    code = str(code).zfill(6)
    df = _safe_listing()
    if df is not None and "Market" in df.columns:
        row = df[df["Code"] == code]
        if not row.empty:
            mk = str(row.iloc[0]["Market"]).upper()
            if "KOSDAQ" in mk:
                return "KOSDAQ"
            if "KOSPI" in mk:
                return "KOSPI"
    return "KOSPI"


@st.cache_data(ttl=60 * 30, show_spinner=False)
def get_name(code: str) -> str:
    code = str(code).zfill(6)
    df = _safe_listing()
    if df is not None:
        row = df[df["Code"] == code]
        if not row.empty:
            return str(row.iloc[0]["Name"])
    return code


@st.cache_data(ttl=60 * 30, show_spinner=False)
def get_close(symbol: str, start: dt.date) -> pd.Series:
    """심볼(종목코드 또는 지수코드)의 종가 시계열을 반환한다."""
    df = fdr.DataReader(symbol, start)
    if df is None or df.empty or "Close" not in df.columns:
        return pd.Series(dtype="float64")
    s = df["Close"].dropna()
    s.index = pd.to_datetime(s.index)
    s.name = symbol
    return s


def get_index_close(market: str, start: dt.date) -> pd.Series:
    symbol = INDEX_SYMBOL.get(market, "KS11")
    return get_close(symbol, start)
