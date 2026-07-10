
# -*- coding: utf-8 -*-
"""
make_final_visualization_addons.py

목적
----
최종 보고 기준 00~17 실험 흐름을 설명하기 위한 추가 시각화 생성 스크립트입니다.
이 파일은 새 실험이 아니라, 이미 종료된 00~17 실험 산출물을 발표/README/Streamlit에서
덜 헷갈리게 보여주기 위한 '시각화 보강용 유틸리티'입니다.

생성 대상
---------
필수:
1. main_final_experiment_flow_diagram.png
2. main_final_time_alignment_diagram.png
3. main_final_hsi_state_timeline.png
4. main_final_lambda_weight_transition_01_03.png
5. main_final_tail_event_defense_comparison.png

선택:
6. main_final_benchmark_alignment_cumulative_return.png
7. main_final_benchmark_alignment_drawdown.png
8. main_final_lambda_macro_sensitivity_tradeoff.png

실행 위치
---------
프로젝트 루트에서 실행:
    .\\.venv\\Scripts\\python.exe .\\src\\make_final_visualization_addons.py

필요 입력
---------
가능하면 아래 산출물이 이미 존재해야 합니다.
- data/processed/main_final_benchmark_alignment_strategy_timeseries.csv
- output/tables/main_final_benchmark_alignment_tail_event_summary.csv
- output/tables/main_final_lambda_macro_overlay_sensitivity_summary.csv

일부 파일이 없어도 가능한 그림만 생성하고, 누락 파일은 경고만 출력합니다.
"""


from pathlib import Path
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# ============================================================
# 0. 경로 설정
# ============================================================

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
TABLES = ROOT / "output" / "tables"
FIGURES = ROOT / "output" / "figures"
DOCS = ROOT / "docs"

FIGURES.mkdir(parents=True, exist_ok=True)
DOCS.mkdir(parents=True, exist_ok=True)

STRATEGY_TS_CANDIDATES = [
    DATA / "main_final_benchmark_alignment_strategy_timeseries.csv",
    DATA / "main_final_regime_robustness_strategy_timeseries.csv",
]

TAIL_SUMMARY_CANDIDATES = [
    TABLES / "main_final_benchmark_alignment_tail_event_summary.csv",
    TABLES / "main_final_regime_robustness_tail_event_summary.csv",
]

MACRO_SENSITIVITY_CANDIDATES = [
    TABLES / "main_final_lambda_macro_overlay_sensitivity_summary.csv",
]

FINAL_COMPARISON_ORDER = [
    "Fixed 70/20/10 BM",
    "EW Benchmark",
    "HSI baseline",
    "Lambda 0.1",
    "Lambda 0.3",
]


# ============================================================
# 1. 공통 유틸
# ============================================================

def read_csv_safely(path: Path) -> pd.DataFrame:
    for enc in ["utf-8-sig", "utf-8", "cp949"]:
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path)


def first_existing(paths: list[Path]) -> Path | None:
    for p in paths:
        if p.exists():
            return p
    return None


def parse_month_series(s: pd.Series) -> pd.Series:
    x = pd.to_datetime(s, errors="coerce")
    if x.notna().mean() < 0.5:
        x = pd.to_datetime(s.astype(str) + "-01", errors="coerce")
    return x.dt.to_period("M").dt.to_timestamp("M")


def find_first_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def set_korean_font() -> None:
    plt.rcParams["font.family"] = "Malgun Gothic"
    plt.rcParams["axes.unicode_minus"] = False

def savefig(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=180, bbox_inches="tight")
    plt.close()
    print(f"    저장: {path}")


def normalize_return_col(df: pd.DataFrame, col: str) -> pd.Series:
    r = pd.to_numeric(df[col], errors="coerce")
    if r.abs().max(skipna=True) > 1.0:
        r = r / 100.0
    return r


# ============================================================
# 2. 데이터 로드
# ============================================================

def load_strategy_timeseries() -> pd.DataFrame | None:
    path = first_existing(STRATEGY_TS_CANDIDATES)
    if path is None:
        warnings.warn("전략 시계열 파일을 찾지 못했습니다. 일부 그림을 건너뜁니다.")
        return None

    df = read_csv_safely(path)
    print(f"[로드] strategy timeseries: {path}")

    date_col = find_first_col(df, ["return_month", "Date", "date", "year_month", "month"])
    if date_col is None:
        warnings.warn(f"전략 시계열에서 날짜 컬럼을 찾지 못했습니다: {list(df.columns)}")
        return None
    df["plot_month"] = parse_month_series(df[date_col])

    if "strategy_name" not in df.columns:
        st_col = find_first_col(df, ["strategy", "model_id", "strategy_id"])
        if st_col is None:
            warnings.warn("전략명 컬럼을 찾지 못했습니다.")
            return None
        df = df.rename(columns={st_col: "strategy_name"})

    ret_col = find_first_col(df, ["strategy_return", "portfolio_return", "monthly_return", "return"])
    if ret_col is not None:
        df["strategy_return_for_plot"] = normalize_return_col(df, ret_col)
        df["cum_return_for_plot"] = (
            df.sort_values("plot_month")
              .groupby("strategy_name")["strategy_return_for_plot"]
              .transform(lambda x: (1 + x.fillna(0.0)).cumprod())
        )
        df["drawdown_for_plot"] = (
            df.sort_values("plot_month")
              .groupby("strategy_name")["cum_return_for_plot"]
              .transform(lambda x: x / x.cummax() - 1)
        )
    elif "cum_return" in df.columns:
        df["cum_return_for_plot"] = pd.to_numeric(df["cum_return"], errors="coerce")
        df["drawdown_for_plot"] = (
            df.sort_values("plot_month")
              .groupby("strategy_name")["cum_return_for_plot"]
              .transform(lambda x: x / x.cummax() - 1)
        )

    return df.dropna(subset=["plot_month"]).copy()


def load_tail_summary() -> pd.DataFrame | None:
    path = first_existing(TAIL_SUMMARY_CANDIDATES)
    if path is None:
        warnings.warn("큰 손실월 요약 파일을 찾지 못했습니다. tail event 그림을 건너뜁니다.")
        return None
    print(f"[로드] tail summary: {path}")
    return read_csv_safely(path)


def load_macro_sensitivity() -> pd.DataFrame | None:
    path = first_existing(MACRO_SENSITIVITY_CANDIDATES)
    if path is None:
        warnings.warn("15번 macro sensitivity 요약 파일을 찾지 못했습니다. macro trade-off 그림을 건너뜁니다.")
        return None
    print(f"[로드] macro sensitivity: {path}")
    return read_csv_safely(path)


# ============================================================
# 3. 구조 설명용 그림
# ============================================================

def plot_experiment_flow_diagram() -> None:
    """
    발표자가 크게 보여줄 수 있도록 00~17을 너무 세분화하지 않고 7개 박스로 축약한다.
    """
    set_korean_font()
    fig, ax = plt.subplots(figsize=(15, 5))
    ax.axis("off")

    nodes = [
        ("00~05\n데이터 정리\nHSI baseline", 0.06, 0.65),
        ("06~09\nEvent / Diagnostic\n상태 해석 보조", 0.23, 0.65),
        ("10~11\nLambda / Theta\n비중 전환 점검", 0.40, 0.65),
        ("12~15\nMacro companion\n보조 민감도", 0.57, 0.65),
        ("16\nRegime robustness\n후보 역할 검증", 0.74, 0.65),
        ("17\nBenchmark alignment\nBM 기준 정렬", 0.91, 0.65),
        ("최종 후보\nλ=0.1 보수형\nλ=0.3 균형형", 0.37, 0.24),
        ("비교 기준\nMain BM: Fixed 70/20/10\nAux BM: EW\nInternal: HSI baseline", 0.66, 0.24),
    ]

    for text, x, y in nodes:
        ax.text(
            x, y, text,
            ha="center", va="center", fontsize=11,
            bbox=dict(boxstyle="round,pad=0.45", linewidth=1.2, facecolor="white")
        )

    arrow_pairs = [(0, 1), (1, 2), (2, 4), (3, 4), (4, 5), (5, 6), (5, 7), (2, 3)]
    coords = [(x, y) for _, x, y in nodes]
    for i, j in arrow_pairs:
        x1, y1 = coords[i]
        x2, y2 = coords[j]
        ax.annotate(
            "", xy=(x2 - 0.055 if x2 > x1 else x2, y2), xytext=(x1 + 0.055 if x2 > x1 else x1, y1),
            arrowprops=dict(arrowstyle="->", lw=1.4)
        )

    ax.set_title("Main final experiment flow: 00~17", fontsize=16, pad=20)
    savefig(FIGURES / "main_final_experiment_flow_diagram.png")


def plot_time_alignment_diagram() -> None:
    set_korean_font()
    fig, ax = plt.subplots(figsize=(13, 4.5))
    ax.axis("off")

    items = [
        ("t월 말\nETF 가격 관측", 0.12),
        ("HSI 5상태\n계산", 0.32),
        ("Lambda\n부분조정 비중", 0.52),
        ("t+1월\nETF 수익률 적용", 0.72),
        ("성과 계산\nCAGR·MDD·Turnover", 0.90),
    ]

    y = 0.55
    for text, x in items:
        ax.text(
            x, y, text,
            ha="center", va="center", fontsize=12,
            bbox=dict(boxstyle="round,pad=0.5", linewidth=1.2, facecolor="white")
        )

    for (_, x1), (_, x2) in zip(items[:-1], items[1:]):
        ax.annotate("", xy=(x2 - 0.07, y), xytext=(x1 + 0.07, y),
                    arrowprops=dict(arrowstyle="->", lw=1.5))

    ax.text(
        0.5, 0.18,
        "핵심: t월 말에 관측 가능한 신호만 사용하고, 해당 신호는 다음 달 수익률에 적용한다.",
        ha="center", va="center", fontsize=12
    )
    ax.set_title("Signal-to-return timing alignment", fontsize=16, pad=20)
    savefig(FIGURES / "main_final_time_alignment_diagram.png")


# ============================================================
# 4. 데이터 기반 그림
# ============================================================

def plot_hsi_state_timeline(ts: pd.DataFrame | None) -> None:
    if ts is None:
        return
    if "hsi_state" not in ts.columns:
        warnings.warn("hsi_state 컬럼이 없어 HSI 상태 타임라인을 건너뜁니다.")
        return

    set_korean_font()

    # 전략별 중복 제거. 상태는 전략에 관계없이 같은 월이면 동일하다고 보고 첫 값 사용.
    df = (
        ts[["plot_month", "hsi_state"]]
        .dropna()
        .drop_duplicates("plot_month")
        .sort_values("plot_month")
        .reset_index(drop=True)
    )
    if df.empty:
        warnings.warn("HSI 상태 타임라인용 데이터가 비어 있습니다.")
        return

    state_order = ["risk_relief", "neutral_watch", "conflict", "risk_warning", "accident_zone", "insufficient_data", "unknown"]
    state_map = {s: i for i, s in enumerate(state_order)}
    df["state_code"] = df["hsi_state"].astype(str).map(state_map).fillna(len(state_order) - 1)

    fig, ax = plt.subplots(figsize=(15, 2.8))
    ax.imshow([df["state_code"].to_numpy()], aspect="auto")
    ax.set_yticks([])
    ax.set_title("HSI state timeline", fontsize=15, pad=15)

    # 연도 단위 tick
    years = sorted(df["plot_month"].dt.year.unique())
    tick_positions = []
    tick_labels = []
    for y in years:
        idx = df.index[df["plot_month"].dt.year == y]
        if len(idx):
            tick_positions.append(int(idx[0]))
            tick_labels.append(str(y))
    ax.set_xticks(tick_positions)
    ax.set_xticklabels(tick_labels, rotation=0)

    # 범례 대체: 아래에 상태 순서 텍스트
    ax.set_xlabel("State order: " + " | ".join(state_order), fontsize=9)
    savefig(FIGURES / "main_final_hsi_state_timeline.png")


def plot_lambda_weight_transition(ts: pd.DataFrame | None) -> None:
    if ts is None:
        return
    required = ["strategy_name", "plot_month", "weight_069500"]
    missing = [c for c in required if c not in ts.columns]
    if missing:
        warnings.warn(f"Lambda 비중 전환 그림에 필요한 컬럼이 없습니다: {missing}")
        return

    set_korean_font()
    df = ts[ts["strategy_name"].isin(["HSI baseline", "Lambda 0.1", "Lambda 0.3"])].copy()
    if df.empty:
        warnings.warn("Lambda 0.1/0.3 또는 HSI baseline 전략을 찾지 못했습니다.")
        return

    fig, ax = plt.subplots(figsize=(14, 5))
    for name, sub in df.groupby("strategy_name"):
        sub = sub.sort_values("plot_month")
        w = pd.to_numeric(sub["weight_069500"], errors="coerce")
        if w.max(skipna=True) <= 1.5:
            w = w * 100
        ax.plot(sub["plot_month"], w, label=name, linewidth=1.8)

    ax.set_title("Risk asset weight transition: HSI baseline vs Lambda candidates", fontsize=14)
    ax.set_xlabel("Month")
    ax.set_ylabel("069500 weight (%)")
    ax.legend(loc="best")
    ax.grid(True, alpha=0.25)
    savefig(FIGURES / "main_final_lambda_weight_transition_01_03.png")


def plot_tail_event_defense(tail: pd.DataFrame | None) -> None:
    if tail is None:
        return
    if "strategy_name" not in tail.columns:
        warnings.warn("tail summary에 strategy_name 컬럼이 없습니다.")
        return

    # 가능한 컬럼명 후보
    value_col = find_first_col(tail, [
        "avg_tail_month_return_pct",
        "avg_tail_return_pct",
        "avg_tail_month_return",
        "avg_tail_return",
    ])
    if value_col is None:
        warnings.warn(f"tail summary에서 평균 손실월 수익률 컬럼을 찾지 못했습니다: {list(tail.columns)}")
        return

    set_korean_font()
    df = tail.copy()
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
    if df[value_col].abs().max(skipna=True) <= 1.0:
        df[value_col] = df[value_col] * 100

    order = FINAL_COMPARISON_ORDER
    df["strategy_name"] = pd.Categorical(df["strategy_name"], categories=order, ordered=True)
    df = df.sort_values("strategy_name").dropna(subset=[value_col])

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(df["strategy_name"].astype(str), df[value_col])
    ax.set_title("Defense in 069500 bottom 10% loss months", fontsize=14)
    ax.set_xlabel("Strategy")
    ax.set_ylabel("Average strategy return in tail months (%)")
    ax.axhline(0, linewidth=1)
    ax.tick_params(axis="x", rotation=25)
    ax.grid(True, axis="y", alpha=0.25)
    savefig(FIGURES / "main_final_tail_event_defense_comparison.png")


def plot_benchmark_cumulative_and_drawdown(ts: pd.DataFrame | None) -> None:
    if ts is None:
        return
    if "cum_return_for_plot" not in ts.columns:
        warnings.warn("누적수익률 계산에 필요한 컬럼이 없어 benchmark cumulative 그림을 건너뜁니다.")
        return

    set_korean_font()
    order = FINAL_COMPARISON_ORDER
    df = ts[ts["strategy_name"].isin(order)].copy()

    fig, ax = plt.subplots(figsize=(14, 5))
    for name in order:
        sub = df[df["strategy_name"] == name].sort_values("plot_month")
        if not sub.empty:
            ax.plot(sub["plot_month"], sub["cum_return_for_plot"], label=name, linewidth=1.8)
    ax.set_title("Benchmark alignment: cumulative return", fontsize=14)
    ax.set_xlabel("Month")
    ax.set_ylabel("Cumulative return index")
    ax.legend(loc="best")
    ax.grid(True, alpha=0.25)
    savefig(FIGURES / "main_final_benchmark_alignment_cumulative_return.png")

    if "drawdown_for_plot" in df.columns:
        fig, ax = plt.subplots(figsize=(14, 5))
        for name in order:
            sub = df[df["strategy_name"] == name].sort_values("plot_month")
            if not sub.empty:
                ax.plot(sub["plot_month"], sub["drawdown_for_plot"] * 100, label=name, linewidth=1.8)
        ax.set_title("Benchmark alignment: drawdown", fontsize=14)
        ax.set_xlabel("Month")
        ax.set_ylabel("Drawdown (%)")
        ax.legend(loc="best")
        ax.grid(True, alpha=0.25)
        savefig(FIGURES / "main_final_benchmark_alignment_drawdown.png")


def plot_macro_sensitivity_tradeoff(macro: pd.DataFrame | None) -> None:
    if macro is None:
        return
    required = ["lambda_value", "macro_scale", "CAGR_pct", "MDD_pct", "Calmar", "avg_turnover_pct"]
    missing = [c for c in required if c not in macro.columns]
    if missing:
        warnings.warn(f"macro sensitivity 그림에 필요한 컬럼이 없습니다: {missing}")
        return

    set_korean_font()
    df = macro.copy()
    df["lambda_label"] = "Lambda " + df["lambda_value"].astype(float).map(lambda x: f"{x:.1f}")
    df = df.sort_values(["lambda_value", "macro_scale"])

    # Calmar와 Turnover를 한 그림에 억지로 넣지 않고, trade-off를 표 형태 그림으로 정리
    show = df[["lambda_label", "macro_scale", "CAGR_pct", "MDD_pct", "Calmar", "avg_turnover_pct"]].copy()
    show = show.round({
        "macro_scale": 2,
        "CAGR_pct": 3,
        "MDD_pct": 3,
        "Calmar": 3,
        "avg_turnover_pct": 3,
    })
    show.columns = ["Lambda", "macro_scale", "CAGR(%)", "MDD(%)", "Calmar", "Turnover(%)"]

    fig, ax = plt.subplots(figsize=(12, 4.8))
    ax.axis("off")
    tbl = ax.table(
        cellText=show.values,
        colLabels=show.columns,
        loc="center",
        cellLoc="center",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(9)
    tbl.scale(1, 1.3)
    ax.set_title("Lambda + macro overlay sensitivity trade-off", fontsize=14, pad=18)
    savefig(FIGURES / "main_final_lambda_macro_sensitivity_tradeoff.png")


# ============================================================
# 5. 인덱스 파일 작성
# ============================================================

def write_visual_index(created_files: list[Path]) -> None:
    rows = []
    descriptions = {
        "main_final_experiment_flow_diagram.png": "00~17 최종 실험 흐름을 발표용으로 축약한 구조도",
        "main_final_time_alignment_diagram.png": "t월 말 신호를 t+1월 수익률에 적용하는 시간 정렬 설명도",
        "main_final_hsi_state_timeline.png": "월별 HSI 5상태 변화 타임라인",
        "main_final_lambda_weight_transition_01_03.png": "HSI baseline, Lambda 0.1, Lambda 0.3의 069500 비중 전환 비교",
        "main_final_tail_event_defense_comparison.png": "Fixed 70/20/10 BM을 메인 BM으로, EW Benchmark를 보조 BM으로 함께 놓고 069500 하위 10% 손실월의 전략별 평균 방어 성과를 비교",
        "main_final_benchmark_alignment_cumulative_return.png": "Fixed 70/20/10 BM을 메인 BM으로 포함한 17번 BM alignment 기준 5개 전략 누적수익률 비교",
        "main_final_benchmark_alignment_drawdown.png": "Fixed 70/20/10 BM을 메인 BM으로 포함한 17번 BM alignment 기준 5개 전략 드로다운 비교",
        "main_final_lambda_macro_sensitivity_tradeoff.png": "15번 Lambda + macro overlay 민감도 trade-off 표 그림",
    }

    for p in created_files:
        rows.append({
            "file": p.name,
            "path": str(p.relative_to(ROOT)),
            "purpose": descriptions.get(p.name, ""),
            "final_report_use": "main_or_appendix",
        })

    out = pd.DataFrame(rows)
    out_path = TABLES / "main_final_visualization_addon_index.csv"
    out.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"    저장: {out_path}")


def main() -> None:
    print("=" * 80)
    print("make_final_visualization_addons.py 실행 시작")
    print("=" * 80)

    before = set(FIGURES.glob("main_final_*.png"))

    print("[1] 구조 설명용 그림 생성")
    plot_experiment_flow_diagram()
    plot_time_alignment_diagram()

    print("[2] 데이터 로드")
    ts = load_strategy_timeseries()
    tail = load_tail_summary()
    macro = load_macro_sensitivity()

    print("[3] 데이터 기반 그림 생성")
    plot_hsi_state_timeline(ts)
    plot_lambda_weight_transition(ts)
    plot_tail_event_defense(tail)
    plot_benchmark_cumulative_and_drawdown(ts)
    plot_macro_sensitivity_tradeoff(macro)

    after = set(FIGURES.glob("main_final_*.png"))
    created_or_updated = sorted(after - before)
    # 이미 존재하던 파일을 업데이트했을 수도 있으므로 이번 스크립트의 대상 파일을 별도 기록
    target_names = [
        "main_final_experiment_flow_diagram.png",
        "main_final_time_alignment_diagram.png",
        "main_final_hsi_state_timeline.png",
        "main_final_lambda_weight_transition_01_03.png",
        "main_final_tail_event_defense_comparison.png",
        "main_final_benchmark_alignment_cumulative_return.png",
        "main_final_benchmark_alignment_drawdown.png",
        "main_final_lambda_macro_sensitivity_tradeoff.png",
    ]
    target_paths = [FIGURES / n for n in target_names if (FIGURES / n).exists()]

    print("[4] 시각화 추가 인덱스 저장")
    write_visual_index(target_paths)

    print("\n[생성/갱신 대상]")
    for p in target_paths:
        print(f"    {p}")

    print("=" * 80)
    print("make_final_visualization_addons.py 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()
