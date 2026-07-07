"""
팩터 로딩·성과 기여도 차트/데이터 헬퍼.

streamlit에 의존하지 않는다(대시보드 페이지 factor_attribution.py가 streamlit을 담당).
- 순수 데이터 헬퍼(demo_bundle, loading_matrix, waterfall_values): plotly 없이도 테스트 가능.
- 그림 빌더(*_fig): plotly를 함수 내부에서 지연 임포트 → plotly 미설치 환경에서도 모듈 임포트 가능.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# ------------------------------------------------------------
# 데모(합성) 데이터 — 실제 산출물이 없을 때 미리보기용
# ------------------------------------------------------------

def demo_bundle() -> dict:
    """stage_factor/stage_attribution 로직으로 합성 데모 산출물을 만든다(스키마 일치)."""
    from pipeline.stage_factor import analyze_strategies, build_factor_matrix, compute_vif
    from pipeline.stage_attribution import run_attribution

    rng = np.random.default_rng(3)
    n = 60
    dates = pd.date_range("2019-01-31", periods=n, freq="ME")

    fac = pd.DataFrame({
        "Date": dates,
        "market": rng.normal(0, 1, n),
        "bond": rng.normal(0, 1, n),
        "vkospi": rng.normal(0, 1, n),
    })
    fm = build_factor_matrix(fac, standardize=False, lags={})
    y03 = 1.2 * fac["market"] - 0.6 * fac["bond"] + 0.2 * fac["vkospi"] + rng.normal(0, 0.01, n)
    y01 = 0.6 * fac["market"] - 0.3 * fac["bond"] + 0.1 * fac["vkospi"] + rng.normal(0, 0.01, n)
    strat = pd.DataFrame({"Date": dates, "lambda_0.3": y03, "lambda_0.1": y01})
    bm = pd.Series(np.zeros(n))
    loading_summary, rolling_ts = analyze_strategies(strat, bm, fm, factor_cols=["market", "bond", "vkospi"])

    vif = compute_vif(fm, ["market", "bond", "vkospi"]).reset_index()
    vif.columns = ["factor", "VIF"]

    returns = pd.DataFrame({
        "Date": dates,
        "069500": rng.normal(0.006, 0.04, n),
        "114260": rng.normal(0.002, 0.01, n),
        "153130": rng.normal(0.001, 0.002, n),
    })
    a = rng.uniform(0.1, 0.7, n)
    base = pd.DataFrame({
        "Date": dates,
        "069500_weight": a,
        "114260_weight": (1 - a) * 0.5,
        "153130_weight": 1 - a - (1 - a) * 0.5,
    })
    lam = base.copy()
    for c in ["069500_weight", "114260_weight", "153130_weight"]:
        lam[c] = 0.5 * base[c] + 0.5 * (1 / 3)
    turn = pd.Series(rng.uniform(0, 0.08, n))
    attr = run_attribution(returns, base, lam, turn, cost_rate=0.0010)

    return {
        "loading_summary": loading_summary,
        "rolling_ts": rolling_ts,
        "vif": vif,
        "attr_summary": attr["summary"],
        "attr_cumulative": attr["cumulative"],
    }


# ------------------------------------------------------------
# 순수 데이터 변환 헬퍼
# ------------------------------------------------------------

def loading_matrix(loading_summary: pd.DataFrame) -> pd.DataFrame:
    """로딩 요약 → 전략×팩터 beta 행렬(alpha 제외). 히트맵 입력."""
    m = loading_summary[loading_summary["factor"] != "alpha"]
    return m.pivot(index="strategy", columns="factor", values="beta")


def waterfall_values(attr_summary: pd.DataFrame) -> tuple[list, list, list]:
    """기여도 요약 → 워터폴 (labels, values, measure)."""
    order = ["saa", "timing", "lambda", "cost"]
    s = attr_summary.set_index("effect")["sum_contribution"]
    labels = order + ["total"]
    values = [float(s.get(e, 0.0)) for e in order] + [float(s.get("total_excess_vs_ew", 0.0))]
    measure = ["relative"] * len(order) + ["total"]
    return labels, values, measure


def rolling_factor_columns(rolling_ts: pd.DataFrame) -> list[str]:
    """rolling 시계열에서 팩터명 목록(_beta 접미사 제거)."""
    return [c[:-5] for c in rolling_ts.columns if c.endswith("_beta")]


# ------------------------------------------------------------
# 한글 표시명 매핑 (차트 표시 전용, 데이터 컬럼명·내부 라벨은 유지)
# ------------------------------------------------------------

FACTOR_LABEL_KR = {
    "market": "시장(주식)",
    "bond": "채권",
    "vkospi": "변동성(VKOSPI)",
    "alpha": "알파(미설명 초과수익)",
}

EFFECT_LABEL_KR = {
    "saa": "정적 배분(SAA)",
    "timing": "상태 타이밍",
    "lambda": "λ 부분조정",
    "cost": "거래비용",
    "total": "합계(EW 대비)",
}


def factor_label_kr(name: str) -> str:
    """팩터 코드명을 한글 표시명으로 변환(매핑에 없으면 원본 유지)."""
    return FACTOR_LABEL_KR.get(str(name), str(name))


# ------------------------------------------------------------
# 그림 빌더 (plotly 지연 임포트)
# ------------------------------------------------------------

def factor_loading_heatmap_fig(loading_summary: pd.DataFrame):
    import plotly.graph_objects as go
    m = loading_matrix(loading_summary)
    fig = go.Figure(data=go.Heatmap(
        z=m.to_numpy(),
        x=[factor_label_kr(c) for c in m.columns],
        y=list(m.index),
        colorscale="RdBu", zmid=0, colorbar_title="β (노출)",
    ))
    fig.update_layout(
        title="팩터 로딩 히트맵 (전략 × 팩터, β)",
        xaxis_title="팩터", yaxis_title="전략", height=360,
    )
    return fig


def rolling_exposure_fig(rolling_ts: pd.DataFrame, factor: str):
    import plotly.graph_objects as go
    col = f"{factor}_beta"
    fig = go.Figure()
    for s, g in rolling_ts.groupby("strategy"):
        g = g.sort_values("Date")
        fig.add_trace(go.Scatter(x=g["Date"], y=g[col], mode="lines", name=str(s)))
    fig.add_hline(y=0, line_dash="dot", line_color="gray")
    fig.update_layout(
        title=f"Rolling 팩터 노출 — {factor_label_kr(factor)} (36개월 β)",
        height=360, xaxis_title="기준월", yaxis_title="β (노출)",
    )
    return fig


def vif_bar_fig(vif: pd.DataFrame, threshold: float = 5.0):
    import plotly.graph_objects as go
    fig = go.Figure(go.Bar(
        x=[factor_label_kr(f) for f in vif["factor"]],
        y=vif["VIF"],
    ))
    fig.add_hline(y=threshold, line_dash="dash", annotation_text=f"임계값 VIF={threshold}")
    fig.update_layout(
        title="다중공선성 VIF (임계 초과 팩터는 중복 의심)",
        xaxis_title="팩터", yaxis_title="VIF", height=340,
    )
    return fig


def attribution_waterfall_fig(attr_summary: pd.DataFrame):
    import plotly.graph_objects as go
    labels, values, measure = waterfall_values(attr_summary)
    labels_kr = [EFFECT_LABEL_KR.get(l, l) for l in labels]
    fig = go.Figure(go.Waterfall(x=labels_kr, y=values, measure=measure))
    fig.update_layout(
        title="성과 기여도 분해 (EW 대비 초과수익)",
        xaxis_title="기여 요인", yaxis_title="누적 기여 (수익률)", height=360,
    )
    return fig


def attribution_cumulative_fig(attr_cumulative: pd.DataFrame):
    import plotly.graph_objects as go
    fig = go.Figure()
    label = {
        "cum_saa_effect": "정적 배분(SAA)", "cum_timing_effect": "상태 타이밍",
        "cum_lambda_effect": "λ 부분조정", "cum_cost_effect": "거래비용",
        "cum_total_excess_vs_ew": "합계(EW 대비)",
    }
    for col, name in label.items():
        if col in attr_cumulative.columns:
            fig.add_trace(go.Scatter(x=attr_cumulative["Date"], y=attr_cumulative[col], mode="lines", name=name))
    fig.add_hline(y=0, line_dash="dot", line_color="gray")
    fig.update_layout(
        title="누적 기여도 시계열",
        xaxis_title="기준월", yaxis_title="누적 기여 (수익률)", height=360,
    )
    return fig
