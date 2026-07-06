"""
대시보드 페이지: 팩터 로딩 · 성과 기여도.

output/tables 의 stage_factor/stage_attribution 산출물이 있으면 그것을,
없으면 데모(합성) 데이터로 차트 레이아웃을 미리보기한다.
차트 로직은 dashboard.factor_charts(순수/plotly)로 분리.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard import factor_charts as fc
from dashboard.paths import LEGACY_TABLE_DIR

FILES = {
    "loading_summary": "factor_loading_summary.csv",
    "rolling_ts": "factor_loading_timeseries.csv",
    "attr_summary": "attribution_summary.csv",
    "attr_cumulative": "attribution_cumulative.csv",
}


def _load_real() -> dict | None:
    """실제 산출물이 모두 있으면 로드, 아니면 None."""
    data = {}
    for key, fname in FILES.items():
        p = LEGACY_TABLE_DIR / fname
        if not p.exists():
            return None
        df = pd.read_csv(p, encoding="utf-8-sig")
        for c in ("Date",):
            if c in df.columns:
                df[c] = pd.to_datetime(df[c])
        data[key] = df
    # VIF는 선택적(있으면 로드)
    vif_p = LEGACY_TABLE_DIR / "factor_vif.csv"
    if vif_p.exists():
        data["vif"] = pd.read_csv(vif_p, encoding="utf-8-sig")
    return data


def render() -> None:
    st.title("팩터 로딩 · 성과 기여도")
    st.caption("RA 요구사항: 팩터 분석/로딩 + 성과 기여도(attribution)")

    real = _load_real()
    if real is None:
        st.info(
            "아직 stage_factor / stage_attribution 산출물(output/tables)이 없습니다. "
            "팩터 데이터 인제스트 후 파이프라인을 실행하면 실제 값으로 채워집니다. "
            "아래는 **데모(합성) 미리보기**로, 차트 구성과 해석 방식을 보여줍니다."
        )
        data = fc.demo_bundle()
        data.setdefault("vif", None)
    else:
        data = real
        data.setdefault("vif", None)

    tabs = st.tabs(["팩터 로딩", "Rolling 노출", "상관·VIF", "성과 기여도"])

    with tabs[0]:
        st.plotly_chart(fc.factor_loading_heatmap_fig(data["loading_summary"]), use_container_width=True)
        st.caption("β>0: 해당 팩터에 양의 노출. alpha 행은 팩터로 설명되지 않는 초과수익.")
        st.dataframe(data["loading_summary"], use_container_width=True, hide_index=True)

    with tabs[1]:
        factors = fc.rolling_factor_columns(data["rolling_ts"])
        if factors:
            sel = st.selectbox("팩터 선택", factors, index=0)
            st.plotly_chart(fc.rolling_exposure_fig(data["rolling_ts"], sel), use_container_width=True)
            st.caption("36개월 rolling 회귀 β. 시간에 따른 노출 변화를 본다.")
        else:
            st.warning("rolling 시계열에 팩터 컬럼(_beta)이 없습니다.")

    with tabs[2]:
        if data.get("vif") is not None:
            st.plotly_chart(fc.vif_bar_fig(data["vif"]), use_container_width=True)
            st.caption("VIF가 임계(기본 5)를 넘으면 다중공선성 → 중복 팩터 제거 검토(팀검토 반영).")
        else:
            st.info("VIF 표(factor_vif.csv)가 없어 생략했습니다. screen_factors로 생성할 수 있습니다.")

    with tabs[3]:
        st.plotly_chart(fc.attribution_waterfall_fig(data["attr_summary"]), use_container_width=True)
        st.caption("EW 대비 초과수익 = SAA + 타이밍 + λ smoothing + 비용 (가법 분해).")
        st.plotly_chart(fc.attribution_cumulative_fig(data["attr_cumulative"]), use_container_width=True)
        st.dataframe(data["attr_summary"], use_container_width=True, hide_index=True)
