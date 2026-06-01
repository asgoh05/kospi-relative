"""코스피 대비 상대강도 & 추세 성장률 대시보드.

실행:  streamlit run app.py
"""

from __future__ import annotations

import datetime as dt
import html
from contextlib import contextmanager
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

KST = ZoneInfo("Asia/Seoul")

import data as D
import metrics as M

st.set_page_config(page_title="국민투자자 모니터", page_icon="🇰🇷", layout="wide")

st.markdown(
    """
    <style>
      .block-container {padding-top: 2.8rem; padding-bottom: 3rem; max-width: 1180px;}
      section[data-testid="stSidebar"] {width: 340px !important;}
      [data-testid="stMetricValue"] {font-size: 1.55rem;}
      [data-testid="stMetricLabel"] {opacity: 0.75;}
      div[role="radiogroup"] label {padding: 1px 0;}
      h1 {font-size: 1.9rem;}
      .sb-head {font-size: 0.8rem; font-weight: 700; letter-spacing: .04em;
                color: #6b7280; text-transform: uppercase; margin: 0 0 .25rem;}
      /* 브랜드 헤더 */
      .app-brand {display: flex; align-items: center; gap: 0.55rem;
                  padding: 0.25rem 0 1rem; margin-bottom: 1.25rem;
                  border-bottom: 1px solid #eef0f3;}
      .app-brand .logo {
        width: 2.1rem; height: 2.1rem; border-radius: 10px; flex: none;
        display: grid; place-items: center; font-size: 1.1rem;
        background: linear-gradient(135deg, #e84855 0%, #c0392b 100%);
        box-shadow: 0 2px 6px rgba(232,72,85,0.35);
      }
      .app-brand .txt {line-height: 1.15;}
      .app-brand .title {font-size: 1.12rem; font-weight: 800;
                         color: #1a2230; letter-spacing: -0.01em;}
      .app-brand .sub {font-size: 0.72rem; color: #8a929e; font-weight: 600;
                       letter-spacing: 0.01em;}
      section[data-testid="stSidebar"] .block-container {overflow-x: hidden;}
      /* 상위20 행: 세로 간격 최소화 */
      section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] {
        gap: 0.2rem; align-items: center;
      }
      section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"]:has(.top20-rank) {
        margin-bottom: 1px;
      }
      section[data-testid="stSidebar"] .top20-rank {
        color: #b0b6bf; font-size: 0.7rem; font-weight: 700;
        text-align: center; line-height: 1.85rem;
      }
      section[data-testid="stSidebar"] .top20-chg {
        font-size: 0.78rem; font-weight: 600; text-align: right;
        white-space: nowrap; line-height: 1.85rem; padding-right: 2px;
      }
      /* 종목 선택 버튼 (Streamlit 1.58 구조: data-testid=stButton 내부 button) */
      section[data-testid="stSidebar"] [data-testid="stButton"] button {
        padding: 0.18rem 0.5rem !important;
        min-height: 1.85rem !important; height: 1.85rem !important;
        font-size: 0.84rem !important; font-weight: 500 !important;
        border: none !important; border-radius: 7px !important;
        background: transparent !important; color: #1f2630 !important;
        box-shadow: none !important; width: 100% !important;
      }
      section[data-testid="stSidebar"] [data-testid="stButton"] button p {
        text-align: left !important; width: 100%;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
      }
      section[data-testid="stSidebar"] [data-testid="stButton"] button > div {
        justify-content: flex-start !important; width: 100%;
      }
      section[data-testid="stSidebar"] [data-testid="stButton"] button:hover {
        background: #f1f3f5 !important; color: #1f2630 !important;
      }
      /* 선택된 종목: 은은한 배경 + 좌측 빨간 강조선 */
      section[data-testid="stSidebar"] [data-testid="stButton"] button[kind="primary"] {
        background: #fdeef0 !important; color: #111 !important;
        font-weight: 700 !important;
        box-shadow: inset 3px 0 0 0 #e84855 !important;
      }
      /* 모바일에서도 상위20 행이 줄바꿈되지 않도록 가로 배치 고정 */
      section[data-testid="stSidebar"] div[data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
      }
      section[data-testid="stSidebar"] div[data-testid="stColumn"] {
        min-width: 0 !important;
      }
      /* 차트 위에서 세로 스크롤(손가락 위/아래)은 브라우저가 처리하도록 */
      .js-plotly-plot, .js-plotly-plot .plotly, .plot-container,
      [data-testid="stPlotlyChart"] {
        touch-action: pan-y !important;
      }
      /* 컴팩트 헤더 지표 카드 */
      .hdr-wrap {margin: 0.35rem 0 0.5rem; padding-top: 0.5rem;}
      .hdr-title {font-size: 1.55rem; font-weight: 800; color: #1a2230;
                  letter-spacing: -0.02em; line-height: 1.3; padding-top: 0.1rem;}
      /* 로딩 오버레이 (화면 중앙) */
      .lg-overlay {
        position: fixed; inset: 0; z-index: 9999;
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        background: rgba(255, 255, 255, 0.94);
        pointer-events: none;
      }
      .lg-dots { display: flex; gap: 10px; justify-content: center; }
      .lg-dots span {
        width: 14px; height: 14px; border-radius: 50%;
        background: #ff9a8b;
        animation: lg-bounce 0.6s ease-in-out infinite;
      }
      .lg-dots span:nth-child(2) { background: #ffc46b; animation-delay: 0.15s; }
      .lg-dots span:nth-child(3) { background: #7cc6c4; animation-delay: 0.3s; }
      @keyframes lg-bounce {
        0%, 100% { transform: translateY(0); opacity: 0.6; }
        50% { transform: translateY(-16px); opacity: 1; }
      }
      .lg-msg { text-align: center; color: #968d80; font-size: 14px; margin-top: 16px; }
      .hdr-sub {font-size: 0.78rem; color: #8a929e; font-weight: 500;
                margin: 0.15rem 0 0.7rem;}
      .hdr-sub b {color: #5b6470; font-weight: 700;}
      .metrics-row {display: flex; gap: 0.5rem; flex-wrap: wrap;}
      .mcard {flex: 1 1 110px; min-width: 105px;
              background: #f7f8fa; border: 1px solid #eef0f3;
              border-radius: 12px; padding: 0.6rem 0.8rem;}
      .mcard .ml {font-size: 0.72rem; color: #8a929e; font-weight: 600;
                  margin-bottom: 0.15rem; white-space: nowrap;}
      .mcard .mv {font-size: 1.2rem; font-weight: 800; color: #1a2230;
                  line-height: 1.2; white-space: nowrap;}
      .mcard .md {font-size: 0.8rem; font-weight: 700; margin-top: 0.1rem;
                  white-space: nowrap;}
      /* 탭: 좀 더 또렷하게 */
      button[data-baseweb="tab"] {font-size: 0.98rem !important;
                                  font-weight: 700 !important;}
      [data-testid="stTabs"] [data-baseweb="tab-list"] {gap: 0.4rem;}
      /* 토글과 표(상단 툴바) 겹침 방지 */
      [data-testid="stSegmentedControl"] {
        margin-bottom: 1rem !important;
      }
      .trend-table-spacer { height: 1.25rem; }
      [data-testid="stDataFrame"] {
        margin-top: 0.5rem !important;
        padding-top: 2rem !important;
      }
      [data-testid="stDataFrame"] [data-testid="stElementToolbar"] {
        top: 0.35rem !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---- 색상 ----
UP = "#e84855"      # 상승(빨강, 한국식)
DOWN = "#2d7dd2"    # 하락(파랑)
GRID = "rgba(120,120,120,0.15)"

# 모바일에서 차트 터치로 화면이 안 넘어가는 문제 방지: 드래그/줌/툴바 비활성화
PLOTLY_CONFIG = {
    "displayModeBar": False,
    "scrollZoom": False,
    "doubleClick": False,
    "staticPlot": False,
}


def loading_markup(msg: str = "데이터 수집중...") -> str:
    """화면 중앙 로딩 오버레이 HTML."""
    return (
        '<div class="lg-overlay">'
        '<div class="lg-dots"><span></span><span></span><span></span></div>'
        f'<p class="lg-msg">{html.escape(msg)}</p>'
        "</div>"
    )


@contextmanager
def cute_loading(msg: str = "데이터 수집중..."):
    """커스텀 로딩 오버레이를 띄운 뒤 작업이 끝나면 제거한다."""
    slot = st.empty()
    slot.markdown(loading_markup(msg), unsafe_allow_html=True)
    try:
        yield
    finally:
        slot.empty()


def color_for(v: float | None) -> str:
    if v is None:
        return "#888"
    return UP if v >= 0 else DOWN


def fmt_pct(v: float | None) -> str:
    if v is None or pd.isna(v):
        return "—"
    return f"{v:+.2f}%"


def metric_card(label: str, value: str, delta: float | None, suffix: str = "%") -> str:
    """컴팩트 지표 카드 HTML."""
    if delta is None or pd.isna(delta):
        md = '<div class="md" style="color:#9aa0a8">—</div>'
    else:
        c = UP if delta >= 0 else DOWN
        arrow = "▲" if delta >= 0 else "▼"
        md = f'<div class="md" style="color:{c}">{arrow} {delta:+.2f}{suffix}</div>'
    return (f'<div class="mcard"><div class="ml">{label}</div>'
            f'<div class="mv">{value}</div>{md}</div>')


def chg_icon(v: float | None) -> str:
    """전일 대비 등락 아이콘."""
    if v is None or pd.isna(v):
        return "·"
    if v > 0:
        return "▲"
    if v < 0:
        return "▼"
    return "·"


def truncate_name(name: str) -> str:
    """길이가 충분히 길 때만 줄여 표시 (대부분 종목명은 그대로 노출)."""
    if len(name) > 9:
        return name[:8] + "…"
    return name


def chg_html(v: float | None) -> str:
    if v is None or pd.isna(v):
        return '<span class="top20-chg" style="color:#888">—</span>'
    color = UP if v >= 0 else DOWN
    return f'<span class="top20-chg" style="color:{color}">{chg_icon(v)} {v:+.1f}%</span>'


# ---------------------------------------------------------------- 사이드바
st.sidebar.markdown(
    """
    <div class="app-brand">
      <div class="logo">🇰🇷</div>
      <div class="txt">
        <div class="title">국민투자자 모니터</div>
        <div class="sub">코스피 대비 상대강도 · 추세</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# 1) 검색 — 가장 핵심 동선
st.sidebar.markdown('<p class="sb-head">종목 검색</p>', unsafe_allow_html=True)
query = st.sidebar.text_input(
    "종목 검색", placeholder="종목명 또는 코드 (예: 카카오, 035720)",
    label_visibility="collapsed",
)
search_code = None
if query:
    results = D.search_stocks(query, limit=20)
    if results:
        res_labels = [f"{name} · {code} · {mk}" for code, name, mk in results]
        chosen = st.sidebar.selectbox("검색 결과", res_labels, label_visibility="collapsed")
        search_code = chosen.split(" · ")[1]
    else:
        st.sidebar.caption("검색 결과가 없습니다.")

# 2) 코스피 상위 20
st.sidebar.markdown('<p class="sb-head">코스피 상위 20</p>', unsafe_allow_html=True)
asof = D.last_trading_date()
st.sidebar.caption(f"시가총액 기준 · {asof:%Y-%m-%d} 종가 · ▲▼는 전일 대비 등락")

with cute_loading():
    ranked = D.get_top_kospi_change(20)
top_codes = [r["code"] for r in ranked]

if "list_code" not in st.session_state or st.session_state.list_code not in top_codes:
    st.session_state.list_code = top_codes[0]

list_box = st.sidebar.container(height=300)
for r in ranked:
    code, is_sel = r["code"], st.session_state.list_code == r["code"]
    c_rank, c_name, c_chg = list_box.columns([0.1, 0.62, 0.28], gap="small")
    with c_rank:
        st.markdown(f'<div class="top20-rank">{r["rank"]}</div>', unsafe_allow_html=True)
    with c_name:
        if st.button(
            truncate_name(r["name"]),
            key=f"top_{code}",
            help=r["name"] if r["name"] != truncate_name(r["name"]) else None,
            use_container_width=True,
            type="primary" if is_sel else "secondary",
        ):
            st.session_state.list_code = code
            st.rerun()
    with c_chg:
        st.markdown(chg_html(r["chg"]), unsafe_allow_html=True)

list_code = st.session_state.list_code

# 검색이 우선, 없으면 상위 20 선택
selected_code = search_code or list_code

# 3) 부수 설정은 접어둔다 (기간은 '코스피 대비 성과' 섹션 안에서 조절)
mkt_auto = D.detect_market(selected_code)
with st.sidebar.expander("⚙️ 보기 설정", expanded=False):
    mkt_choice = st.radio(
        "비교 지수", ["자동", "코스피", "코스닥"], index=0,
        help=f"자동 판별: {D.INDEX_LABEL.get(mkt_auto, mkt_auto)}",
    )
market = mkt_auto if mkt_choice == "자동" else ("KOSPI" if mkt_choice == "코스피" else "KOSDAQ")

# ---------------------------------------------------------------- 데이터 로딩
# 시작일을 자유롭게 지정할 수 있도록 충분히 긴 이력(약 5년)을 받아둔다.
today = dt.date.today()
fetch_start = today - dt.timedelta(days=365 * 5 + 30)

name = D.get_name(selected_code)
with cute_loading():
    stock_full = D.get_close(selected_code, fetch_start)
    index_full = D.get_index_close(market, fetch_start)

if stock_full.empty:
    st.error(f"'{name}({selected_code})' 시세를 불러오지 못했습니다. 코드/네트워크를 확인하세요.")
    st.stop()

idx_label = D.INDEX_LABEL.get(market, market)
data_start = stock_full.index[0].date()
data_end = stock_full.index[-1].date()

# ---------------------------------------------------------------- 헤더 지표
returns_tbl = M.period_returns(stock_full, index_full)
row_1d = returns_tbl.iloc[0]  # 어제 대비

last_price = float(stock_full.iloc[-1])
idx_last = float(index_full.iloc[-1]) if not index_full.empty else None
ex_1d = row_1d["초과"]

now_kst = dt.datetime.now(KST)

if ex_1d is not None and not pd.isna(ex_1d):
    ex_color = UP if ex_1d >= 0 else DOWN
    ex_val = f'<span style="color:{ex_color}">{ex_1d:+.2f}%p</span>'
else:
    ex_val = "—"
ex_card = ('<div class="mcard"><div class="ml">지수 대비(전일)</div>'
           f'<div class="mv">{ex_val}</div>'
           '<div class="md" style="color:#9aa0a8;font-weight:500">'
           '종목−지수 등락</div></div>')

cards = (
    metric_card("현재가", f"{last_price:,.0f}원", row_1d["종목"])
    + metric_card(f"{idx_label} 지수",
                  f"{idx_last:,.2f}" if idx_last is not None else "—", row_1d["지수"])
    + ex_card
)
st.markdown(
    f"""
    <div class="hdr-wrap">
      <div class="hdr-title">{name}</div>
      <div class="hdr-sub">{selected_code} · 비교 지수 <b>{idx_label}</b> ·
        종가일 <b>{stock_full.index[-1]:%Y-%m-%d}</b> · 조회 {now_kst:%Y-%m-%d %H:%M} KST</div>
    </div>
    """,
    unsafe_allow_html=True,
)

def _style(v):
    if pd.isna(v):
        return "color:#888"
    c = UP if v >= 0 else DOWN
    return f"color:{c}; font-weight:600"


tab_dash, tab_rel, tab_trend = st.tabs(
    ["🏠 대시보드", "📊 코스피 대비 성과", "📈 추세 성장률"]
)

# ---------------------------------------------------------------- 0) 대시보드
with tab_dash:
    st.markdown(f'<div class="metrics-row">{cards}</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------- 1) 상대강도
with tab_rel:
    # --- 기준 시점 & 매도 기준선 (모바일에선 기본 접힘) ---
    preset_days = {"1일": 1, "1주": 7, "2주": 14, "1개월": 30, "3개월": 91,
                   "6개월": 182, "1년": 365}
    preset_opts = list(preset_days.keys()) + ["YTD", "직접 지정(매수일)"]

    with st.expander("⚙️ 기준 시점 · 매도 기준 설정", expanded=False):
        preset = st.radio("기준 시점", preset_opts, index=5, horizontal=True)

        if preset == "YTD":
            default_start = dt.date(today.year, 1, 1)
        elif preset == "직접 지정(매수일)":
            default_start = today - dt.timedelta(days=182)
        else:
            default_start = today - dt.timedelta(days=preset_days[preset])
        default_start = max(default_start, data_start)

        # 매도 기준 방식 (선택은 URL 쿼리 파라미터에 저장 → 새로고침해도 유지)
        SELL_MODES = {
            "idx_start": "지수 대비 (시작일 기준)",
            "idx_peak": "지수 대비 (기간 내 고점 기준)",
            "price_peak": "주가 고점 대비",
        }
        _sell_labels = list(SELL_MODES.values())
        _sell_keys = list(SELL_MODES.keys())
        if "sell_mode" not in st.session_state:
            _qp = st.query_params.get("sell")
            st.session_state.sell_mode = SELL_MODES.get(_qp, SELL_MODES["idx_peak"])

        sell_help = (
            "매도를 결정하는 하락 기준을 고르는 방식입니다.\n\n"
            "**1. 지수 대비 (시작일 기준)**  \n"
            "시작일(매수일)을 0으로 두고, 그 이후 종목이 비교 지수보다 "
            "얼마나 더(또는 덜) 올랐는지(누적 초과수익률, %p)를 봅니다. "
            "이 값이 기준에 닿으면 매도 신호입니다. "
            "예: 기준 −10%p → 시작일 대비 지수보다 10%p 뒤처지면 신호.\n\n"
            "**2. 지수 대비 (기간 내 고점 기준)**  \n"
            "표시 기간 중 종목 주가가 가장 높았던 날을 새 출발점으로 잡고, "
            "그날 이후의 지수 대비 초과수익률(%p)을 봅니다. 고점을 찍은 뒤 "
            "지수 대비 얼마나 약해졌는지를 추적하는 방식입니다. "
            "예: 기준 −10%p → 고점 이후 지수보다 10%p 더 빠지면 신호.\n\n"
            "**3. 주가 고점 대비**  \n"
            "지수와 무관하게, 표시 기간 중 최고가 대비 현재 주가가 "
            "몇 % 떨어졌는지(절대 하락률, %)만 봅니다. "
            "예: 기준 −10% → 고점 대비 10% 하락하면 신호."
        )
        _mh = st.columns([1, 1])
        with _mh[0]:
            st.markdown("**매도 기준 방식**")
        with _mh[1]:
            # 모바일에서 hover 툴팁(help=)은 탭하면 깜빡이고 사라지므로
            # 탭하면 열려서 유지되는 popover 로 설명을 제공한다.
            with st.popover("ℹ️ 방식 설명", width="stretch"):
                st.markdown(sell_help)

        sell_label = st.radio(
            "매도 기준 방식", _sell_labels, key="sell_mode",
            label_visibility="collapsed",
        )
        if not sell_label:  # 선택 해제(None) 시 기본값 유지
            sell_label = SELL_MODES["idx_peak"]
        sell_mode = _sell_keys[_sell_labels.index(sell_label)]
        st.query_params["sell"] = sell_mode

        _thr_label = {
            "idx_start": "매도 기준 (지수 대비, %p)",
            "idx_peak": "매도 기준 (고점 이후 지수 대비, %p)",
            "price_peak": "매도 기준 (주가 고점 대비, %)",
        }[sell_mode]

        cset = st.columns([1.2, 1])
        with cset[0]:
            if preset == "직접 지정(매수일)":
                start_date = st.date_input(
                    "시작일 (매수일)", value=default_start,
                    min_value=data_start, max_value=data_end, format="YYYY-MM-DD",
                )
            else:
                start_date = default_start
                st.metric("시작일", f"{start_date:%Y-%m-%d}")

        with cset[1]:
            threshold = st.number_input(
                _thr_label, value=-10.0, step=1.0, format="%.1f",
                key="sell_threshold",
                help="선택한 매도 기준 방식이 이 값에 닿으면 매도하기로 한 계획선입니다.",
            )

    start_ts = pd.Timestamp(start_date)
    stock = stock_full[stock_full.index >= start_ts]
    index = index_full[index_full.index >= start_ts]
    # 1일 등 짧은 기간에 거래일이 1개뿐이면 직전 거래일을 포함해 최소 2개 확보
    if len(stock) < 2:
        stock = stock_full.tail(2)
        index = index_full.tail(2)

    st.caption(
        f"**{start_date:%Y-%m-%d}** 를 시작점(=100)으로 비교합니다. "
        "오른쪽 그래프가 0보다 위면 시장 대비 강세, 빨간 점선(매도 기준)에 닿으면 계획 도달입니다."
    )

    s_norm = M.normalize_to_100(stock)
    i_norm = M.normalize_to_100(index)
    excess = M.excess_return_series(stock, index)

    # 기간 중 고점 대비 하락률
    peak_idx = stock.idxmax()
    peak_price = float(stock.loc[peak_idx])
    cur_price = float(stock.iloc[-1])
    drop_from_peak = (cur_price / peak_price - 1.0) * 100.0 if peak_price else 0.0
    peak_norm = float(s_norm.loc[peak_idx])
    cur_norm = float(s_norm.iloc[-1])
    last_idx = s_norm.index[-1]
    is_below_peak = drop_from_peak <= -0.05

    # 옵션 2용: 주가 고점 날짜를 새 시작점으로 한 지수 대비 초과수익률
    idx_at_peak = M._value_asof(index, peak_idx)
    idx_cur = float(index.iloc[-1]) if not index.empty else None
    if idx_at_peak and idx_at_peak != 0 and peak_price and idx_cur is not None:
        excess_from_peak = (
            (cur_price / peak_price - 1.0) - (idx_cur / idx_at_peak - 1.0)
        ) * 100.0
    else:
        excess_from_peak = None

    rel_view = st.segmented_control(
        "차트 선택", ["정규화 주가", "지수 대비 초과수익률"],
        default="정규화 주가", key="rel_view", label_visibility="collapsed",
    )

    if rel_view in (None, "정규화 주가"):
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=s_norm.index, y=s_norm.values, name=name,
                                 line=dict(color=UP, width=2.4)))
        fig.add_trace(go.Scatter(x=i_norm.index, y=i_norm.values, name=idx_label,
                                 line=dict(color="#888", width=1.8, dash="dot")))
        # 고점 기준선 + 고점 마커
        fig.add_hline(y=peak_norm, line=dict(color="#c2c2c2", width=1, dash="dot"))
        fig.add_trace(go.Scatter(
            x=[peak_idx], y=[peak_norm], mode="markers+text",
            marker=dict(color=UP, size=12, symbol="star",
                        line=dict(color="white", width=1)),
            text=["고점"], textposition="top center",
            textfont=dict(size=11, color=UP), name="고점", showlegend=False,
            hovertemplate=f"고점 {peak_price:,.0f}원 ({peak_idx:%Y-%m-%d})<extra></extra>",
        ))
        # 고점과 현재가 사이 간격 표시 (현재가가 고점보다 낮을 때)
        if is_below_peak:
            fig.add_shape(type="line", x0=last_idx, x1=last_idx,
                          y0=cur_norm, y1=peak_norm,
                          line=dict(color=UP, width=1.4, dash="dot"))
            fig.add_annotation(
                x=last_idx, y=(cur_norm + peak_norm) / 2,
                text=f"고점대비 {drop_from_peak:.1f}%", showarrow=False,
                font=dict(color=UP, size=11), xanchor="right", xshift=-6,
                bgcolor="rgba(255,255,255,0.7)",
            )
        # 주가 고점 대비 매도 기준선 (옵션 3 선택 시)
        if sell_mode == "price_peak":
            sell_level = peak_norm * (1.0 + threshold / 100.0)
            fig.add_hline(
                y=sell_level, line=dict(color=UP, width=1.4, dash="dash"),
                annotation_text=f"매도 기준 {threshold:+.0f}%",
                annotation_position="bottom right",
                annotation_font=dict(color=UP, size=11),
            )
        fig.update_layout(
            title=dict(text="정규화 주가 (시작=100)", x=0, xanchor="left"),
            height=400, margin=dict(l=10, r=10, t=50, b=50),
            legend=dict(orientation="h", yanchor="top", y=-0.15, x=0),
            plot_bgcolor="white", yaxis=dict(gridcolor=GRID), xaxis=dict(gridcolor=GRID),
            dragmode=False,
        )
        st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)

    if rel_view == "지수 대비 초과수익률":
        fig2 = go.Figure()
        pos = excess.clip(lower=0)
        neg = excess.clip(upper=0)
        fig2.add_trace(go.Scatter(x=excess.index, y=pos.values, fill="tozeroy",
                                  mode="none", name="시장 대비 강세", fillcolor="rgba(232,72,85,0.45)"))
        fig2.add_trace(go.Scatter(x=excess.index, y=neg.values, fill="tozeroy",
                                  mode="none", name="시장 대비 약세", fillcolor="rgba(45,125,210,0.45)"))
        fig2.add_hline(y=0, line=dict(color="#444", width=1))
        if sell_mode == "idx_start":
            fig2.add_hline(
                y=threshold, line=dict(color=UP, width=1.4, dash="dash"),
                annotation_text=f"매도 기준 {threshold:+.0f}%p",
                annotation_position="bottom left",
                annotation_font=dict(color=UP, size=11),
            )
            ymin = min(float(excess.min()), threshold, 0.0)
        else:
            ymin = min(float(excess.min()), 0.0)
        ymax = max(float(excess.max()), 0.0)
        pad = max((ymax - ymin) * 0.10, 1.0)
        fig2.update_layout(
            title=dict(text="지수 대비 누적 초과수익률 (%)", x=0, xanchor="left"),
            height=400, margin=dict(l=10, r=10, t=50, b=50),
            legend=dict(orientation="h", yanchor="top", y=-0.15, x=0),
            plot_bgcolor="white",
            yaxis=dict(gridcolor=GRID, ticksuffix="%", range=[ymin - pad, ymax + pad]),
            xaxis=dict(gridcolor=GRID),
            dragmode=False,
        )
        st.plotly_chart(fig2, width="stretch", config=PLOTLY_CONFIG)

    # 선택된 매도 기준 방식에 해당하는 메시지 하나만 표시
    if sell_mode == "idx_start":
        cur_excess = float(excess.iloc[-1]) if not excess.empty else None
        if cur_excess is not None:
            gap = cur_excess - threshold
            if cur_excess <= threshold:
                st.error(
                    f"⚠️ {start_date:%Y-%m-%d} 이후 {name}의 주가는 {idx_label} 대비 "
                    f"**{cur_excess:+.2f}%p** — 매도 기준({threshold:+.1f}%p)에 도달/이탈했습니다."
                )
            else:
                msg = (
                    f"{start_date:%Y-%m-%d}부터 지금까지 {name}의 주가는 {idx_label} 대비 "
                    f"**{cur_excess:+.2f}%p** 움직였고, 매도 기준({threshold:+.1f}%p)까지 "
                    f"**{gap:+.2f}%p** 남았습니다."
                )
                (st.success if cur_excess >= 0 else st.info)(msg)

    elif sell_mode == "idx_peak":
        if excess_from_peak is not None:
            gap = excess_from_peak - threshold
            if excess_from_peak <= threshold:
                st.error(
                    f"⚠️ 주가 고점 {peak_price:,.0f}원({peak_idx:%Y-%m-%d}) 이후 {name}는 "
                    f"{idx_label} 대비 **{excess_from_peak:+.2f}%p** — "
                    f"매도 기준({threshold:+.1f}%p)에 도달/이탈했습니다."
                )
            else:
                msg = (
                    f"주가 고점({peak_idx:%Y-%m-%d}) 이후 {name}는 {idx_label} 대비 "
                    f"**{excess_from_peak:+.2f}%p**이고, 매도 기준({threshold:+.1f}%p)까지 "
                    f"**{gap:+.2f}%p** 남았습니다."
                )
                (st.success if excess_from_peak >= 0 else st.info)(msg)
        else:
            st.info("고점 기준 초과수익률을 계산할 데이터가 부족합니다.")

    else:  # price_peak
        peak_gap = drop_from_peak - threshold
        if drop_from_peak <= threshold:
            st.error(
                f"⚠️ 표시 기간 중 최고가 {peak_price:,.0f}원({peak_idx:%Y-%m-%d}) 대비 현재 "
                f"**{drop_from_peak:.2f}%** ({cur_price:,.0f}원) — "
                f"매도 기준({threshold:+.1f}%)에 도달/이탈했습니다."
            )
        elif is_below_peak:
            st.info(
                f"표시 기간 중 최고가 {peak_price:,.0f}원({peak_idx:%Y-%m-%d}) 대비 현재 "
                f"**{drop_from_peak:.2f}%** ({cur_price:,.0f}원)이고, "
                f"매도 기준({threshold:+.1f}%)까지 **{peak_gap:+.2f}%p** 남았습니다."
            )
        else:
            st.success(
                f"현재가 **{cur_price:,.0f}원** 이 표시 기간 중 최고가 수준입니다."
            )

# ---------------------------------------------------------------- 2) 추세 성장률
with tab_trend:
    st.caption("어제·1주·1개월·3개월·6개월·YTD·1년 수익률을 비교합니다. "
               "빨강=상승, 파랑=하락. 아래에서 절대·초과수익률·상세 표를 전환할 수 있습니다.")

    tbl = returns_tbl.copy()
    labels = tbl["기간"].tolist()

    trend_view = st.segmented_control(
        "보기 선택",
        ["절대 수익률", "지수 대비 초과수익률", "상세표"],
        default="절대 수익률", key="trend_view", label_visibility="collapsed",
    )

    if trend_view in (None, "절대 수익률"):
        vals = tbl["종목"].tolist()
        fig3 = go.Figure(go.Bar(
            x=vals, y=labels, orientation="h",
            marker_color=[color_for(v) for v in vals],
            text=[fmt_pct(v) for v in vals], textposition="auto",
        ))
        fig3.add_vline(x=0, line=dict(color="#444", width=1))
        fig3.update_layout(
            title=dict(text="기간별 절대 수익률 (%)", x=0, xanchor="left"),
            height=420, margin=dict(l=10, r=10, t=50, b=20),
            plot_bgcolor="white", xaxis=dict(gridcolor=GRID, ticksuffix="%"),
            yaxis=dict(autorange="reversed"),
            dragmode=False,
        )
        st.plotly_chart(fig3, width="stretch", config=PLOTLY_CONFIG)

    if trend_view == "지수 대비 초과수익률":
        vals = tbl["초과"].tolist()
        fig4 = go.Figure(go.Bar(
            x=vals, y=labels, orientation="h",
            marker_color=[color_for(v) for v in vals],
            text=[fmt_pct(v) for v in vals], textposition="auto",
        ))
        fig4.add_vline(x=0, line=dict(color="#444", width=1))
        fig4.update_layout(
            title=dict(text=f"기간별 {idx_label} 대비 초과수익률 (%p)", x=0, xanchor="left"),
            height=420, margin=dict(l=10, r=10, t=50, b=20),
            plot_bgcolor="white", xaxis=dict(gridcolor=GRID, ticksuffix="%"),
            yaxis=dict(autorange="reversed"),
            dragmode=False,
        )
        st.plotly_chart(fig4, width="stretch", config=PLOTLY_CONFIG)

    if trend_view == "상세표":
        st.markdown('<div class="trend-table-spacer" aria-hidden="true"></div>',
                    unsafe_allow_html=True)
        disp = tbl.set_index("기간")
        styled = (
            disp.style.format(lambda v: fmt_pct(v))
            .map(_style)
            .set_properties(**{"text-align": "right"})
        )
        st.dataframe(styled, width="stretch")

st.caption("데이터: FinanceDataReader · 투자 판단의 책임은 본인에게 있습니다.")
