from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from .paths import LEGACY_FIGURE_DIR, LEGACY_TABLE_DIR, MIDTERM_DIR, MIDTERM_FIGURE_DIR, MIDTERM_TABLE_DIR, MIDTERM_VERSION


CORE_FIGURES = [
    ("HSI 모래시계 개념도", "fig00_hsi_hourglass_concept.png"),
    ("HSI 상태 점수와 사건 주석", "fig14_hsi_state_score_with_event_annotations.png"),
    ("P/S-wave 사건 압력과 사건 주석", "fig13_p_s_wave_with_event_annotations.png"),
    ("충돌 상태와 사건 주석", "fig15_mixed_zone_with_event_annotations.png"),
    ("HSI 5상태 분포", "fig12_hsi_state5_distribution.png"),
]

SUPPORT_FIGURES = [
    ("P/S-wave 사건 압력", "fig09_p_s_wave_event_pressure.png"),
    ("양방향 충격 혼합구간", "fig10_two_sided_shock_mixed_zone.png"),
    ("HSI 상태 점수 추이", "fig11_hsi_state_score_trend.png"),
]

TABLES = [
    ("월별 HSI 상태 요약", "monthly_hsi_state_summary.csv"),
    ("사건 구간별 HSI 해석", "event_hsi_interpretation_summary.csv"),
    ("설계/검증 상태 요약", "design_validation_state_summary.csv"),
    ("설계/검증 파동 요약", "design_validation_wave_summary.csv"),
    ("State5 매핑 감사", "state5_mapping_audit.csv"),
]


def resolve_figure(filename: str) -> Path:
    preferred = MIDTERM_FIGURE_DIR / filename
    if preferred.exists():
        return preferred
    return LEGACY_FIGURE_DIR / filename


def resolve_table(filename: str) -> Path:
    preferred = MIDTERM_TABLE_DIR / filename
    if preferred.exists():
        return preferred
    return LEGACY_TABLE_DIR / filename


@st.cache_data
def read_table(path_text: str) -> pd.DataFrame:
    path = Path(path_text)
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig")


def render_gallery() -> None:
    st.subheader("핵심 그래프")
    for title, filename in CORE_FIGURES:
        path = resolve_figure(filename)
        if path.exists():
            st.markdown(f"**{title}**")
            st.image(str(path), use_container_width=True)
        else:
            st.warning(f"파일을 찾을 수 없습니다: {filename}")

    st.subheader("보조 그래프")
    cols = st.columns(3)
    for idx, (title, filename) in enumerate(SUPPORT_FIGURES):
        path = resolve_figure(filename)
        with cols[idx % 3]:
            if path.exists():
                st.image(str(path), caption=title, use_container_width=True)
            else:
                st.warning(filename)


def render_tables() -> None:
    st.subheader("발표용 표")
    for title, filename in TABLES:
        path = resolve_table(filename)
        with st.expander(title, expanded=False):
            if not path.exists():
                st.warning(f"파일을 찾을 수 없습니다: {filename}")
                continue
            df = read_table(str(path))
            st.caption(str(path))
            st.dataframe(df, use_container_width=True, hide_index=True)


def render() -> None:
    st.title("기존 중간발표 자료")
    st.caption(f"보존 위치: {MIDTERM_DIR} | 버전: {MIDTERM_VERSION}")
    st.info("이 페이지는 기존 중간발표 산출물을 수정하지 않고 참조합니다.")

    overview, gallery, tables = st.tabs(["개요", "그래프", "표"])
    with overview:
        readme = MIDTERM_DIR / "README.md"
        if readme.exists():
            st.markdown(readme.read_text(encoding="utf-8", errors="replace"))
        else:
            st.write("중간발표 자료 폴더는 유지되어 있습니다.")
        st.write(f"그림 폴더: `{MIDTERM_FIGURE_DIR}`")
        st.write(f"표 폴더: `{MIDTERM_TABLE_DIR}`")
    with gallery:
        render_gallery()
    with tables:
        render_tables()

