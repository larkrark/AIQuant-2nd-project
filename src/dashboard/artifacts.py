from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from .paths import (
    ARTIFACT_FIGURE_DIR,
    ARTIFACT_META_DIR,
    ARTIFACT_NOTE_DIR,
    ARTIFACT_REPORT_DIR,
    ARTIFACT_TABLE_DIR,
    ARTIFACTS_DIR,
)


REPORT_FLOW = [
    ("00~05", "Foundation / baseline", ["00_", "01_", "02_", "03_", "04_", "05_"]),
    ("10", "Lambda", ["main_final_lambda", "main_final_report_lambda", "10_"]),
    ("11", "Theta", ["main_final_theta", "11_"]),
    ("12~13", "Macro companion diagnostic", ["main_final_hsi_macro", "main_final_macro_companion", "main_final_macro_rate", "12_13_"]),
    ("14", "Macro overlay", ["main_final_macro_overlay", "14_"]),
    ("16~17", "Robustness / benchmark", ["main_final_regime", "main_final_benchmark", "16_", "17_"]),
    ("20~23", "Final candidate", ["main_final_candidate", "20_23_"]),
]

CURATED_TABLES = {
    "HSI 상태 분포": "04_hsi_state5_distribution_rebuilt.csv",
    "Baseline 성과": "05_baseline_performance_rebuilt.csv",
    "Baseline 비중 규칙": "05_baseline_allocation_rule_rebuilt.csv",
    "Macro overlap": "main_final_hsi_macro_overlap_type_summary.csv",
    "HSI state x macro risk": "main_final_hsi_state_macro_risk_summary.csv",
    "Macro overlay adjustment": "main_final_macro_overlay_weight_adjustment_by_state.csv",
}


@st.cache_data
def read_csv(path_text: str) -> pd.DataFrame:
    path = Path(path_text)
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, encoding="utf-8-sig")


@st.cache_data
def read_text(path_text: str) -> str:
    path = Path(path_text)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def manifest() -> pd.DataFrame:
    return read_csv(str(ARTIFACT_META_DIR / "artifact_manifest.csv"))


def link_check() -> pd.DataFrame:
    return read_csv(str(ARTIFACT_META_DIR / "report_figure_link_check.csv"))


def classify_flow(filename: str) -> str:
    for code, label, patterns in REPORT_FLOW:
        if any(pattern in filename for pattern in patterns):
            return f"{code} {label}"
    return "기타"


def artifact_files(category: str | None = None) -> pd.DataFrame:
    data = manifest()
    if data.empty:
        return data
    if category:
        data = data[data["category"] == category].copy()
    data["flow"] = data["source_file"].map(classify_flow)
    data["size_kb"] = (data["bytes"] / 1024).round(1)
    return data


def image_path(repo_path: str) -> Path:
    return ARTIFACTS_DIR / repo_path


def table_path(filename: str) -> Path:
    return ARTIFACT_TABLE_DIR / filename


def render_metric_row() -> None:
    data = manifest()
    checks = link_check()
    total_mb = data["bytes"].sum() / 1024 / 1024 if not data.empty else 0
    ok_links = int((checks["target_exists_in_package"].astype(str) == "True").sum()) if not checks.empty else 0

    cols = st.columns(5)
    cols[0].metric("Reports", int((data["category"] == "report_md").sum()) if not data.empty else 0)
    cols[1].metric("Figures", int((data["category"] == "figure").sum()) if not data.empty else 0)
    cols[2].metric("CSV tables", int((data["category"] == "table_csv").sum()) if not data.empty else 0)
    cols[3].metric("Link checks", f"{ok_links}/{len(checks)}" if not checks.empty else "0/0")
    cols[4].metric("Package size", f"{total_mb:.2f} MB")


def render_overview() -> None:
    readme = ARTIFACTS_DIR / "README_HSI_REPORT_ARTIFACTS.md"
    if readme.exists():
        st.markdown(read_text(str(readme)))

    data = artifact_files()
    if data.empty:
        st.warning("artifact_manifest.csv를 찾을 수 없습니다.")
        return

    left, right = st.columns([1.1, 0.9])
    with left:
        count_df = data.groupby(["flow", "category"], as_index=False).size()
        fig = px.bar(
            count_df,
            x="flow",
            y="size",
            color="category",
            barmode="group",
            labels={"flow": "실험 흐름", "size": "파일 수", "category": "유형"},
            title="실험 흐름별 산출물 수",
        )
        fig.update_layout(template="plotly_white", xaxis_tickangle=-22, height=430)
        st.plotly_chart(fig, width="stretch")
    with right:
        size_df = data.groupby("category", as_index=False)["bytes"].sum()
        size_df["size_mb"] = size_df["bytes"] / 1024 / 1024
        fig = px.bar(
            size_df,
            x="category",
            y="size_mb",
            color="category",
            labels={"category": "유형", "size_mb": "용량 (MB)"},
            title="유형별 패키지 용량",
        )
        fig.update_layout(template="plotly_white", showlegend=False, height=430)
        st.plotly_chart(fig, width="stretch")

    with st.expander("Manifest", expanded=False):
        st.dataframe(data[["flow", "category", "source_file", "repo_path", "size_kb"]], width="stretch", hide_index=True)


def render_link_check() -> None:
    checks = link_check()
    if checks.empty:
        st.warning("report_figure_link_check.csv를 찾을 수 없습니다.")
        return

    checks = checks.copy()
    checks["target_exists_in_package"] = checks["target_exists_in_package"].astype(str)
    status = checks.groupby("target_exists_in_package", as_index=False).size()
    fig = px.bar(
        status,
        x="target_exists_in_package",
        y="size",
        color="target_exists_in_package",
        labels={"target_exists_in_package": "패키지 내부 존재", "size": "링크 수"},
        title="보고서 그림 링크 점검",
    )
    fig.update_layout(template="plotly_white", showlegend=False, height=320)
    st.plotly_chart(fig, width="stretch")
    st.dataframe(checks, width="stretch", hide_index=True)


def render_figure_gallery() -> None:
    figures = artifact_files("figure")
    if figures.empty:
        st.warning("그림 파일을 찾을 수 없습니다.")
        return

    flow_options = ["전체"] + list(figures["flow"].drop_duplicates())
    selected_flow = st.selectbox("실험 흐름", flow_options)
    filtered = figures if selected_flow == "전체" else figures[figures["flow"] == selected_flow]

    default_count = min(4, len(filtered))
    selected = st.multiselect(
        "비교할 그림",
        filtered["source_file"].tolist(),
        default=filtered["source_file"].head(default_count).tolist(),
    )
    if not selected:
        st.info("비교할 그림을 하나 이상 선택하세요.")
        return

    selected_rows = filtered[filtered["source_file"].isin(selected)].copy()
    cols_per_row = st.slider("한 줄에 표시할 그림 수", 1, 3, 2)
    cols = st.columns(cols_per_row)
    for idx, row in enumerate(selected_rows.itertuples(index=False)):
        path = image_path(row.repo_path)
        with cols[idx % cols_per_row]:
            st.markdown(f"**{row.source_file}**")
            if path.exists():
                st.image(str(path), width="stretch")
                st.caption(f"{row.flow} | {row.size_kb:.1f} KB")
            else:
                st.warning(f"파일 없음: {path}")


def render_curated_charts() -> None:
    selected = st.selectbox("비교 표", list(CURATED_TABLES))
    filename = CURATED_TABLES[selected]
    df = read_csv(str(table_path(filename)))
    if df.empty:
        st.warning(f"표를 찾을 수 없습니다: {filename}")
        return

    st.caption(str(table_path(filename)))

    if filename == "04_hsi_state5_distribution_rebuilt.csv":
        fig = px.bar(
            df,
            x="state_kr",
            y="ratio_valid_pct",
            color="hsi_state",
            text="months",
            labels={"state_kr": "HSI 상태", "ratio_valid_pct": "유효 월 비중 (%)"},
            title="HSI 5상태 분포",
        )
    elif filename == "05_baseline_performance_rebuilt.csv":
        fig = px.scatter(
            df,
            x="avg_turnover_pct",
            y="Calmar",
            size="CAGR_pct",
            color="strategy_name",
            hover_data=["MDD_pct", "Sharpe", "goldfriend_judgement"],
            labels={"avg_turnover_pct": "평균 Turnover (%)", "Calmar": "Calmar"},
            title="Baseline 비교: Calmar x Turnover",
        )
    elif filename == "05_baseline_allocation_rule_rebuilt.csv":
        plot_df = df.melt(
            id_vars=["hsi_state", "state_kr"],
            value_vars=["weight_069500", "weight_114260", "weight_153130"],
            var_name="asset",
            value_name="weight",
        )
        fig = px.bar(
            plot_df,
            x="state_kr",
            y="weight",
            color="asset",
            labels={"state_kr": "HSI 상태", "weight": "목표 비중"},
            title="HSI 상태별 baseline 목표 비중",
        )
    elif "macro_overlay_weight_adjustment" in filename:
        fig = px.bar(
            df,
            x="segment",
            y="avg_delta_pctp",
            color="segment",
            hover_data=["months", "adjusted_months", "max_delta_pctp"],
            labels={"segment": "구간", "avg_delta_pctp": "평균 조정폭 (%p)"},
            title="Macro overlay 조정폭 비교",
        )
    elif "macro" in filename:
        y_col = "ratio_total_pct" if "ratio_total_pct" in df.columns else "months"
        x_col = "overlap_type" if "overlap_type" in df.columns else df.columns[0]
        fig = px.bar(
            df,
            x=x_col,
            y=y_col,
            color=x_col,
            labels={x_col: "구간", y_col: y_col},
            title=f"{selected} 비교",
        )
    else:
        fig = px.bar(df, x=df.columns[0], y=df.select_dtypes("number").columns[0], title=selected)

    fig.update_layout(template="plotly_white", xaxis_tickangle=-18, height=470, showlegend=True)
    st.plotly_chart(fig, width="stretch")
    st.dataframe(df, width="stretch", hide_index=True)


def render_table_browser() -> None:
    tables = artifact_files("table_csv")
    if tables.empty:
        st.warning("CSV 표를 찾을 수 없습니다.")
        return

    selected = st.selectbox("CSV 파일", tables["source_file"].tolist())
    row = tables[tables["source_file"] == selected].iloc[0]
    df = read_csv(str(image_path(row["repo_path"])))
    st.caption(str(image_path(row["repo_path"])))
    st.dataframe(df, width="stretch", hide_index=True)

    numeric_cols = df.select_dtypes("number").columns.tolist()
    text_cols = [col for col in df.columns if col not in numeric_cols]
    if numeric_cols and text_cols:
        left, right = st.columns(2)
        x_col = left.selectbox("X축", text_cols, index=0)
        y_col = right.selectbox("Y축", numeric_cols, index=0)
        chart = px.bar(df, x=x_col, y=y_col, color=x_col, title=f"{selected}: {y_col}")
        chart.update_layout(template="plotly_white", xaxis_tickangle=-18, showlegend=False)
        st.plotly_chart(chart, width="stretch")


def render_report_reader() -> None:
    reports = artifact_files("report_md")
    notes = artifact_files("note_md")
    docs = pd.concat([reports, notes], ignore_index=True)
    if docs.empty:
        st.warning("보고서 Markdown을 찾을 수 없습니다.")
        return

    selected = st.selectbox("문서", docs["source_file"].tolist())
    row = docs[docs["source_file"] == selected].iloc[0]
    path = image_path(row["repo_path"])
    st.caption(str(path))
    st.markdown(read_text(str(path)))


def render() -> None:
    st.title("HSI 산출물 비교용 테스트")
    st.caption(f"프로젝트 루트 기준: {ARTIFACTS_DIR}")
    st.info("hsi_report_artifacts를 root 구조(docs/reports, docs/experiment_notes, output/figures, output/tables)로 통합한 자료를 읽어 보고서, 그림, CSV 표를 비교합니다.")

    render_metric_row()

    tabs = st.tabs(["개요", "그림 비교", "표 비교", "CSV 탐색", "문서 미리보기", "링크 점검"])
    with tabs[0]:
        render_overview()
    with tabs[1]:
        render_figure_gallery()
    with tabs[2]:
        render_curated_charts()
    with tabs[3]:
        render_table_browser()
    with tabs[4]:
        render_report_reader()
    with tabs[5]:
        render_link_check()

