from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

import final_project_config as cfg


"""
06_build_relative_speed_diagnostics.py

목적
----
월말 HSI 점수의 변화 속도를 계산해
각 신호가 전체 HSI 중심 흐름보다 빠르게 위험 악화 또는 위험 완화 방향으로 움직이는지 진단한다.

중요
----
이 실험은 선행/후행지표 예측 실험이 아니다.
빠른 신호와 느린 신호의 반응 속도 차이를 비교하는 HSI 내부 진단 실험이다.

정의
----
signal_velocity   = signal_score_t - signal_score_t-1
centroid_score    = 같은 월·같은 ETF의 HSI 점수 평균
centroid_velocity = centroid_score_t - centroid_score_t-1
relative_velocity = signal_velocity - centroid_velocity

해석
----
relative_velocity > 0 : 해당 신호가 중심보다 위험 악화 방향으로 더 빠르게 움직임
relative_velocity < 0 : 해당 신호가 중심보다 위험 완화 방향으로 더 빠르게 움직임

입력
----
data/processed/main_final_monthly_signal_inputs_long.csv
data/processed/main_final_hsi_state5_table.csv

출력
----
data/processed/main_final_relative_speed_long.csv

output/tables/main_final_relative_speed_rank_table.csv
output/tables/main_final_relative_speed_state_summary.csv
output/tables/main_final_relative_speed_quality_check.csv

docs/main_final_relative_speed_diagnostic_note.md
"""


INPUT_MONTHLY_SIGNAL_LONG = cfg.PROCESSED_DIR / "main_final_monthly_signal_inputs_long.csv"
INPUT_STATE_TABLE = cfg.PROCESSED_DIR / "main_final_hsi_state5_table.csv"

OUTPUT_RELATIVE_SPEED_LONG = cfg.PROCESSED_DIR / "main_final_relative_speed_long.csv"

OUTPUT_RANK_TABLE = cfg.TABLE_DIR / "main_final_relative_speed_rank_table.csv"
OUTPUT_STATE_SUMMARY = cfg.TABLE_DIR / "main_final_relative_speed_state_summary.csv"
OUTPUT_QUALITY_CHECK = cfg.TABLE_DIR / "main_final_relative_speed_quality_check.csv"

OUTPUT_NOTE = cfg.DOCS_DIR / "main_final_relative_speed_diagnostic_note.md"


YEAR_MONTH_COL = "year_month"
TICKER_COL = "ticker"

SCORE_COLS = [
    "score_return",
    "score_ma_pos",
    "score_momentum",
    "score_vol",
    "score_rs",
]

SIGNAL_FAMILY = {
    "return": "return_speed",
    "ma_pos": "trend_position",
    "momentum": "trend_momentum",
    "vol": "risk_damage",
    "rs": "relative_strength",
}

SIGNAL_SPEED_TYPE = {
    "return": "fast",
    "ma_pos": "slow",
    "momentum": "slow",
    "vol": "fast",
    "rs": "fast",
}

RELATIVE_VELOCITY_STRONG = 0.50
RELATIVE_VELOCITY_WEAK = 0.20


def save_csv(df: pd.DataFrame, path: Path, index: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=index, encoding="utf-8-sig")


def read_csv(path: Path, label: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{label} 파일이 없습니다: {path}")
    return pd.read_csv(path, encoding="utf-8-sig")


def build_relative_speed_long(monthly_long: pd.DataFrame, state_table: pd.DataFrame) -> pd.DataFrame:
    df = monthly_long.copy()
    df[TICKER_COL] = df[TICKER_COL].astype(str).str.zfill(6)

    for col in SCORE_COLS:
        if col not in df.columns:
            df[col] = np.nan
        df[col] = pd.to_numeric(df[col], errors="coerce")

    base_cols = [
        YEAR_MONTH_COL,
        TICKER_COL,
        "ticker_name",
        "ticker_role",
    ]

    base_cols = [c for c in base_cols if c in df.columns]

    long_df = df[base_cols + SCORE_COLS].melt(
        id_vars=base_cols,
        value_vars=SCORE_COLS,
        var_name="score_column",
        value_name="signal_score",
    )

    long_df["signal_name"] = long_df["score_column"].str.replace("score_", "", regex=False)
    long_df["signal_family"] = long_df["signal_name"].map(SIGNAL_FAMILY)
    long_df["signal_speed_type"] = long_df["signal_name"].map(SIGNAL_SPEED_TYPE)

    long_df = long_df.sort_values([TICKER_COL, "signal_name", YEAR_MONTH_COL]).reset_index(drop=True)

    long_df["signal_velocity"] = (
        long_df
        .groupby([TICKER_COL, "signal_name"])["signal_score"]
        .diff()
    )

    centroid = df[[YEAR_MONTH_COL, TICKER_COL] + SCORE_COLS].copy()
    centroid["centroid_score"] = centroid[SCORE_COLS].mean(axis=1, skipna=True)
    centroid = centroid.sort_values([TICKER_COL, YEAR_MONTH_COL]).reset_index(drop=True)
    centroid["centroid_velocity"] = (
        centroid
        .groupby(TICKER_COL)["centroid_score"]
        .diff()
    )

    long_df = long_df.merge(
        centroid[[YEAR_MONTH_COL, TICKER_COL, "centroid_score", "centroid_velocity"]],
        on=[YEAR_MONTH_COL, TICKER_COL],
        how="left",
    )

    long_df["relative_velocity"] = long_df["signal_velocity"] - long_df["centroid_velocity"]
    long_df["relative_speed_abs"] = long_df["relative_velocity"].abs()

    long_df["direction_label"] = np.select(
        [
            long_df["relative_velocity"] >= RELATIVE_VELOCITY_STRONG,
            long_df["relative_velocity"] <= -RELATIVE_VELOCITY_STRONG,
            long_df["relative_velocity"].abs() <= RELATIVE_VELOCITY_WEAK,
        ],
        [
            "risk_accelerating",
            "risk_relief_accelerating",
            "moving_with_centroid",
        ],
        default="weak_or_noise",
    )

    long_df["speed_rank"] = (
        long_df
        .groupby([YEAR_MONTH_COL, TICKER_COL])["relative_speed_abs"]
        .rank(method="dense", ascending=False)
    )

    state_keep = state_table[[YEAR_MONTH_COL, "hsi_state", "state_kr"]].copy()
    long_df = long_df.merge(state_keep, on=YEAR_MONTH_COL, how="left")

    long_df["interpretation"] = np.select(
        [
            long_df["direction_label"] == "risk_accelerating",
            long_df["direction_label"] == "risk_relief_accelerating",
            long_df["direction_label"] == "moving_with_centroid",
        ],
        [
            "중심 흐름보다 위험 악화 방향으로 빠르게 움직인 신호",
            "중심 흐름보다 위험 완화 방향으로 빠르게 움직인 신호",
            "전체 HSI 중심 흐름과 비슷하게 움직인 신호",
        ],
        default="상대속도는 있으나 강한 방향 신호로 해석하기는 어려움",
    )

    return long_df


def build_rank_table(relative_speed: pd.DataFrame) -> pd.DataFrame:
    rank_df = relative_speed.copy()

    rank_df = rank_df[
        (rank_df[TICKER_COL] == cfg.RISK_TICKER)
        & rank_df["relative_velocity"].notna()
        & (rank_df["speed_rank"] <= 5)
    ].copy()

    rank_df = rank_df.sort_values([YEAR_MONTH_COL, "speed_rank"])

    keep_cols = [
        YEAR_MONTH_COL,
        "hsi_state",
        "state_kr",
        TICKER_COL,
        "signal_name",
        "signal_family",
        "signal_speed_type",
        "signal_score",
        "signal_velocity",
        "centroid_velocity",
        "relative_velocity",
        "relative_speed_abs",
        "direction_label",
        "speed_rank",
        "interpretation",
    ]

    return rank_df[keep_cols].reset_index(drop=True)


def build_state_summary(relative_speed: pd.DataFrame) -> pd.DataFrame:
    valid = relative_speed.dropna(subset=["relative_velocity"]).copy()

    summary = (
        valid
        .groupby(["hsi_state", "state_kr", "signal_name", "signal_family", "signal_speed_type"])
        .agg(
            observations=("relative_velocity", "count"),
            mean_signal_score=("signal_score", "mean"),
            mean_signal_velocity=("signal_velocity", "mean"),
            mean_centroid_velocity=("centroid_velocity", "mean"),
            mean_relative_velocity=("relative_velocity", "mean"),
            mean_relative_speed_abs=("relative_speed_abs", "mean"),
            risk_accelerating_ratio=("direction_label", lambda s: (s == "risk_accelerating").mean()),
            relief_accelerating_ratio=("direction_label", lambda s: (s == "risk_relief_accelerating").mean()),
            moving_with_centroid_ratio=("direction_label", lambda s: (s == "moving_with_centroid").mean()),
        )
        .reset_index()
    )

    summary = summary.sort_values(
        ["hsi_state", "mean_relative_speed_abs"],
        ascending=[True, False],
    ).reset_index(drop=True)

    return summary


def build_quality_check(relative_speed: pd.DataFrame, rank_table: pd.DataFrame, state_summary: pd.DataFrame) -> pd.DataFrame:
    valid = relative_speed.dropna(subset=["relative_velocity"]).copy()

    rows = [
        {
            "item": "relative_speed_rows",
            "value": len(relative_speed),
            "status": "OK" if len(relative_speed) > 0 else "CHECK",
            "note": "상대속도 long 전체 행 수",
        },
        {
            "item": "valid_relative_velocity_rows",
            "value": len(valid),
            "status": "OK" if len(valid) > 0 else "CHECK",
            "note": "relative_velocity 유효 행 수",
        },
        {
            "item": "ticker_count",
            "value": relative_speed[TICKER_COL].nunique(),
            "status": "OK" if relative_speed[TICKER_COL].nunique() == len(cfg.TICKERS) else "CHECK",
            "note": "상대속도 계산 대상 ETF 수",
        },
        {
            "item": "signal_count",
            "value": relative_speed["signal_name"].nunique(),
            "status": "OK" if relative_speed["signal_name"].nunique() >= 4 else "CHECK",
            "note": "상대속도 계산 대상 신호 수",
        },
        {
            "item": "first_valid_month",
            "value": valid[YEAR_MONTH_COL].min() if not valid.empty else "N/A",
            "status": "OK" if not valid.empty else "CHECK",
            "note": "상대속도 첫 유효 월",
        },
        {
            "item": "last_valid_month",
            "value": valid[YEAR_MONTH_COL].max() if not valid.empty else "N/A",
            "status": "OK" if not valid.empty else "CHECK",
            "note": "상대속도 마지막 유효 월",
        },
        {
            "item": "rank_table_rows",
            "value": len(rank_table),
            "status": "OK" if len(rank_table) > 0 else "CHECK",
            "note": "069500 기준 월별 상대속도 상위 신호표 행 수",
        },
        {
            "item": "state_summary_rows",
            "value": len(state_summary),
            "status": "OK" if len(state_summary) > 0 else "CHECK",
            "note": "HSI 상태별 상대속도 요약표 행 수",
        },
    ]

    return pd.DataFrame(rows)


def build_note(quality: pd.DataFrame) -> str:
    lines = []

    lines.append("# main_final 상대속도 진단 노트")
    lines.append("")
    lines.append(f"- 생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## 1. 목적")
    lines.append("")
    lines.append(
        "상대속도 실험은 선행/후행지표 예측 실험이 아니라, "
        "HSI 내부 신호들이 전체 중심 흐름보다 위험 악화 또는 위험 완화 방향으로 "
        "얼마나 빠르게 움직이는지 진단하는 실험이다."
    )
    lines.append("")
    lines.append("## 2. 계산식")
    lines.append("")
    lines.append("```text")
    lines.append("signal_velocity   = signal_score_t - signal_score_t-1")
    lines.append("centroid_score    = 같은 월·같은 ETF의 HSI 점수 평균")
    lines.append("centroid_velocity = centroid_score_t - centroid_score_t-1")
    lines.append("relative_velocity = signal_velocity - centroid_velocity")
    lines.append("```")
    lines.append("")
    lines.append("## 3. 해석")
    lines.append("")
    lines.append("- relative_velocity > 0: 해당 신호가 중심보다 위험 악화 방향으로 빠르게 움직임")
    lines.append("- relative_velocity < 0: 해당 신호가 중심보다 위험 완화 방향으로 빠르게 움직임")
    lines.append("- moving_with_centroid: 전체 HSI 중심 흐름과 비슷하게 움직임")
    lines.append("")
    lines.append("## 4. 품질 점검")
    lines.append("")
    lines.append("| item | value | status | note |")
    lines.append("|---|---:|---|---|")
    for _, row in quality.iterrows():
        lines.append(f"| {row['item']} | {row['value']} | {row['status']} | {row['note']} |")
    lines.append("")
    lines.append("## 5. 다음 단계")
    lines.append("")
    lines.append(
        "`07_run_signal_combo_backtests.py`에서는 기본 신호, 확장 신호, 상대속도 진단 결과를 "
        "어떻게 전략 비교에 연결할지 실험한다."
    )
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    print("=" * 80)
    print("06_build_relative_speed_diagnostics.py 실행 시작")
    print("=" * 80)

    cfg.ensure_final_directories()

    print("[1] 입력 파일 로드")
    monthly_long = read_csv(INPUT_MONTHLY_SIGNAL_LONG, "월말 HSI signal long")
    state_table = read_csv(INPUT_STATE_TABLE, "HSI 5상태표")
    print(f"    monthly_long shape = {monthly_long.shape}")
    print(f"    state_table shape = {state_table.shape}")

    print("[2] 상대속도 long 생성")
    relative_speed = build_relative_speed_long(monthly_long, state_table)
    save_csv(relative_speed, OUTPUT_RELATIVE_SPEED_LONG)
    print(f"    저장: {OUTPUT_RELATIVE_SPEED_LONG}")

    print("[3] 월별 상대속도 rank table 생성")
    rank_table = build_rank_table(relative_speed)
    save_csv(rank_table, OUTPUT_RANK_TABLE)
    print(f"    저장: {OUTPUT_RANK_TABLE}")

    print("[4] 상태별 상대속도 요약표 생성")
    state_summary = build_state_summary(relative_speed)
    save_csv(state_summary, OUTPUT_STATE_SUMMARY)
    print(f"    저장: {OUTPUT_STATE_SUMMARY}")

    print("[5] 품질 점검표 생성")
    quality = build_quality_check(relative_speed, rank_table, state_summary)
    save_csv(quality, OUTPUT_QUALITY_CHECK)
    print(f"    저장: {OUTPUT_QUALITY_CHECK}")

    print("[6] Markdown 노트 저장")
    note = build_note(quality)
    OUTPUT_NOTE.write_text(note, encoding="utf-8")
    print(f"    저장: {OUTPUT_NOTE}")

    print("\n[품질 점검]")
    print(quality.to_string(index=False))

    print("\n[최근 15개 상대속도 rank]")
    print(rank_table.tail(15).to_string(index=False))

    print("\n[상태별 상대속도 요약 최근 15행]")
    print(state_summary.tail(15).to_string(index=False))

    print("=" * 80)
    print("06_build_relative_speed_diagnostics.py 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()