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
        st.info(
            "**해석 방법**: β가 +이면(빨강) 그 팩터가 오를 때 전략도 같이 오르는 노출, "
            "−이면(파랑) 반대 방향 노출. |β|가 1을 크게 넘으면 해당 팩터에 과도하게 기대는 전략이다. "
            "alpha가 0보다 뚜렷하게 크면 팩터로 설명되지 않는 초과수익이 있다는 뜻."
        )
        st.dataframe(data["loading_summary"], use_container_width=True, hide_index=True)

    with tabs[1]:
        factors = fc.rolling_factor_columns(data["rolling_ts"])
        if factors:
            sel = st.selectbox(
                "팩터 선택", factors, index=0,
                format_func=fc.factor_label_kr,
            )
            st.plotly_chart(fc.rolling_exposure_fig(data["rolling_ts"], sel), use_container_width=True)
            st.info(
                "**해석 방법**: 선이 0 위에 있으면 그 시기에 팩터와 같은 방향으로 움직였다는 뜻. "
                "β가 시기에 따라 부호가 뒤집히거나 크게 출렁이면 노출이 불안정해 "
                "전체 기간 β 하나로 전략 성격을 단정하기 어렵다."
            )
        else:
            st.warning("rolling 시계열에 팩터 컬럼(_beta)이 없습니다.")

    with tabs[2]:
        if data.get("vif") is not None:
            st.plotly_chart(fc.vif_bar_fig(data["vif"]), use_container_width=True)
            st.info(
                "**해석 방법**: VIF가 5 이상이면 다른 팩터와 정보가 겹쳐(다중공선성) "
                "β 추정이 불안정해지고 과적합 위험이 커진다 → 해당 팩터 제거·통합을 검토. "
                "10 이상이면 사실상 중복 팩터로 본다."
            )
        else:
            st.info("VIF 표(factor_vif.csv)가 없어 생략했습니다. screen_factors로 생성할 수 있습니다.")

    with tabs[3]:
        st.plotly_chart(fc.attribution_waterfall_fig(data["attr_summary"]), use_container_width=True)
        st.info(
            "**해석 방법**: 막대가 +이면 그 요인이 EW 대비 초과수익에 보탬, −이면 깎아먹음. "
            "상태 타이밍이 +인데 거래비용 −가 그만큼 크면 신호는 맞아도 실익이 없는 전략이다. "
            "네 요인의 합 = 맨 오른쪽 합계(가법 분해)."
        )
        st.plotly_chart(fc.attribution_cumulative_fig(data["attr_cumulative"]), use_container_width=True)
        st.info(
            "**해석 방법**: 각 선이 우상향하면 그 요인이 꾸준히 기여했다는 뜻. "
            "특정 구간(위기 등)에서만 급등했다면 그 시기 방어가 성과의 대부분 — "
            "구간 의존적 성과인지 확인이 필요하다."
        )
        st.dataframe(data["attr_summary"], use_container_width=True, hide_index=True)
