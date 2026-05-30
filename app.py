"""코스피 대비 상대강도 & 추세 성장률 대시보드.

실행:  streamlit run app.py
"""

from __future__ import annotations

import datetime as dt

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import data as D
import metrics as M

st.set_page_config(page_title="코스피 대비 상대강도", page_icon="📈", layout="wide")

st.markdown(
    """
    <style>
      .block-container {padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1180px;}
      section[data-testid="stSidebar"] {width: 340px !important;}
      [data-testid="stMetricValue"] {font-size: 1.55rem;}
      [data-testid="stMetricLabel"] {opacity: 0.75;}
      div[role="radiogroup"] label {padding: 1px 0;}
      h1 {font-size: 1.9rem;}
      .sb-head {font-size: 0.8rem; font-weight: 700; letter-spacing: .04em;
                color: #6b7280; text-transform: uppercase; margin: 0 0 .25rem;}
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


def color_for(v: float | None) -> str:
    if v is None:
        return "#888"
    return UP if v >= 0 else DOWN


def fmt_pct(v: float | None) -> str:
    if v is None or pd.isna(v):
        return "—"
    return f"{v:+.2f}%"


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
st.sidebar.markdown("### 📈 코스피 상대강도")

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

ranked = D.get_top_kospi_change(20)
top_codes = [r["code"] for r in ranked]

if "list_code" not in st.session_state or st.session_state.list_code not in top_codes:
    st.session_state.list_code = top_codes[0]

for r in ranked:
    code, is_sel = r["code"], st.session_state.list_code == r["code"]
    c_rank, c_name, c_chg = st.sidebar.columns([0.1, 0.62, 0.28], gap="small")
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
with st.spinner("시세 불러오는 중..."):
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

st.title(f"{name}")
st.caption(
    f"{selected_code} · 비교 지수 **{idx_label}** · 기준일 {stock_full.index[-1]:%Y-%m-%d}"
)

c1, c2, c3 = st.columns(3)
c1.metric("현재가", f"{last_price:,.0f}원", fmt_pct(row_1d["종목"]))
c2.metric(
    f"{idx_label} 지수",
    f"{idx_last:,.2f}" if idx_last is not None else "—",
    fmt_pct(row_1d["지수"]),
)
c3.metric(
    "지수 대비 (전일)",
    fmt_pct(ex_1d) + "p" if ex_1d is not None and not pd.isna(ex_1d) else "—",
    help="종목 등락률 − 지수 등락률. 양수(빨강)면 시장보다 강하게 움직인 것.",
)

st.markdown("---")

# ---------------------------------------------------------------- 1) 상대강도
st.subheader("① 코스피 대비 상대 성과")

# --- 기준 시점 & 매도 기준선 (섹션 내부에서 조절) ---
preset_days = {"1일": 1, "1주": 7, "2주": 14, "1개월": 30, "3개월": 91,
               "6개월": 182, "1년": 365, "3년": 365 * 3}
preset_opts = list(preset_days.keys()) + ["YTD", "직접 지정(매수일)"]
ctl = st.columns([2.6, 1.2, 1.2])

with ctl[0]:
    preset = st.radio("기준 시점", preset_opts, index=5, horizontal=True)

if preset == "YTD":
    default_start = dt.date(today.year, 1, 1)
elif preset == "직접 지정(매수일)":
    default_start = today - dt.timedelta(days=182)
else:
    default_start = today - dt.timedelta(days=preset_days[preset])
default_start = max(default_start, data_start)

with ctl[1]:
    if preset == "직접 지정(매수일)":
        start_date = st.date_input(
            "시작일 (매수일)", value=default_start,
            min_value=data_start, max_value=data_end, format="YYYY-MM-DD",
        )
    else:
        start_date = default_start
        st.metric("시작일", f"{start_date:%Y-%m-%d}")

with ctl[2]:
    threshold = st.number_input(
        "매도 기준 (지수 대비, %p)", value=-10.0, step=1.0, format="%.1f",
        help="지수 대비 누적 초과수익률이 이 값에 닿으면 매도하기로 한 계획선",
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

lc, rc = st.columns([1, 1])

with lc:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=s_norm.index, y=s_norm.values, name=name,
                             line=dict(color=UP, width=2.4)))
    fig.add_trace(go.Scatter(x=i_norm.index, y=i_norm.values, name=idx_label,
                             line=dict(color="#888", width=1.8, dash="dot")))
    fig.update_layout(
        title=dict(text="정규화 주가 (시작=100)", x=0, xanchor="left"),
        height=400, margin=dict(l=10, r=10, t=50, b=50),
        legend=dict(orientation="h", yanchor="top", y=-0.15, x=0),
        plot_bgcolor="white", yaxis=dict(gridcolor=GRID), xaxis=dict(gridcolor=GRID),
        dragmode=False,
    )
    st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG)

with rc:
    fig2 = go.Figure()
    pos = excess.clip(lower=0)
    neg = excess.clip(upper=0)
    fig2.add_trace(go.Scatter(x=excess.index, y=pos.values, fill="tozeroy",
                              mode="none", name="시장 대비 강세", fillcolor="rgba(232,72,85,0.45)"))
    fig2.add_trace(go.Scatter(x=excess.index, y=neg.values, fill="tozeroy",
                              mode="none", name="시장 대비 약세", fillcolor="rgba(45,125,210,0.45)"))
    fig2.add_hline(y=0, line=dict(color="#444", width=1))
    fig2.add_hline(
        y=threshold, line=dict(color=UP, width=1.4, dash="dash"),
        annotation_text=f"매도 기준 {threshold:+.0f}%p",
        annotation_position="bottom left",
        annotation_font=dict(color=UP, size=11),
    )
    ymin = min(float(excess.min()), threshold, 0.0)
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

st.markdown("---")

# ---------------------------------------------------------------- 2) 추세 성장률
st.subheader("② 추세 성장률 (기간별 한눈에 보기)")
st.caption("어제·1주·1개월·3개월·6개월·YTD·1년 수익률을 막대로 비교합니다. "
           "빨강=상승, 파랑=하락. 오른쪽은 '지수 대비' 초과수익률입니다.")

tbl = returns_tbl.copy()
labels = tbl["기간"].tolist()

bl, br = st.columns([1, 1])

with bl:
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

with br:
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

# 표 (색상 히트맵)
st.markdown("##### 상세 표")
disp = tbl.set_index("기간")


def _style(v):
    if pd.isna(v):
        return "color:#888"
    c = UP if v >= 0 else DOWN
    return f"color:{c}; font-weight:600"


styled = (
    disp.style.format(lambda v: fmt_pct(v))
    .map(_style)
    .set_properties(**{"text-align": "right"})
)
st.dataframe(styled, width="stretch")

st.caption("데이터: FinanceDataReader · 투자 판단의 책임은 본인에게 있습니다.")
