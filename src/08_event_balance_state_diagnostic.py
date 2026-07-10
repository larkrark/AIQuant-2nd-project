from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

import final_project_config as cfg


"""
08_event_balance_state_diagnostic.py

목적
----
02번에서 만든 사건균형·위험누적지표와
04번에서 만든 HSI 5상태가 해석상 정합적인지 확인한다.

이 파일은 백테스트를 하지 않는다.
사건균형지표가 HSI 상태를 대체할 수 있는지 보는 것이 아니라,
HSI 내부 신호의 위험·완화 누적 흐름이 상태분류와 잘 맞물리는지 진단한다.

입력
----
data/processed/main_final_hsi_state5_table.csv
data/processed/main_final_hsi_event_balance_monthly.csv

출력
----
data/processed/main_final_event_balance_state_diagnostic.csv

output/tables/main_final_event_balance_state_crosstab.csv
output/tables/main_final_event_balance_intensity_crosstab.csv
output/tables/main_final_event_balance_state_numeric_summary.csv
output/tables/main_final_event_balance_state_diagnostic_summary.csv

docs/main_final_event_balance_state_diagnostic_note.md
"""


INPUT_STATE_TABLE = cfg.PROCESSED_DIR / "main_final_hsi_state5_table.csv"
INPUT_EVENT_BALANCE = cfg.PROCESSED_DIR / "main_final_hsi_event_balance_monthly.csv"

OUTPUT_DIAGNOSTIC = cfg.PROCESSED_DIR / "main_final_event_balance_state_diagnostic.csv"

OUTPUT_STATE_CROSSTAB = cfg.TABLE_DIR / "main_final_event_balance_state_crosstab.csv"
OUTPUT_INTENSITY_CROSSTAB = cfg.TABLE_DIR / "main_final_event_balance_intensity_crosstab.csv"
OUTPUT_NUMERIC_SUMMARY = cfg.TABLE_DIR / "main_final_event_balance_state_numeric_summary.csv"
OUTPUT_DIAGNOSTIC_SUMMARY = cfg.TABLE_DIR / "main_final_event_balance_state_diagnostic_summary.csv"

OUTPUT_NOTE = cfg.DOCS_DIR / "main_final_event_balance_state_diagnostic_note.md"


YEAR_MONTH_COL = "year_month"

EVENT_COLS = [
    "event_balance_raw",
    "event_intensity_raw",
    "event_balance_13612w",
    "event_intensity_13612w",
    "event_balance_13612w_label",
    "event_intensity_13612w_label",
]


def save_csv(df: pd.DataFrame, path: Path, index: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=index, encoding="utf-8-sig")


def read_csv(path: Path, label: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{label} 파일이 없습니다: {path}")
    return pd.read_csv(path, encoding="utf-8-sig")


def normalize_year_month(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    if YEAR_MONTH_COL not in out.columns:
        out = out.rename(columns={out.columns[0]: YEAR_MONTH_COL})

    out[YEAR_MONTH_COL] = out[YEAR_MONTH_COL].astype(str)
    return out


def build_diagnostic_table(state_table: pd.DataFrame, event_balance: pd.DataFrame) -> pd.DataFrame:
    state = normalize_year_month(state_table)
    event = normalize_year_month(event_balance)

    keep_state_cols = [
        YEAR_MONTH_COL,
        "hsi_state",
        "state_kr",
        "risk_component",
        "relief_component",
        "state_direction",
        "state_intensity",
        "state_reason",
    ]

    keep_state_cols = [c for c in keep_state_cols if c in state.columns]
    keep_event_cols = [YEAR_MONTH_COL] + [c for c in EVENT_COLS if c in event.columns]

    merged = state[keep_state_cols].merge(
        event[keep_event_cols],
        on=YEAR_MONTH_COL,
        how="left",
    )

    merged["event_balance_sign"] = np.select(
        [
            merged["event_balance_13612w"] > 0.05,
            merged["event_balance_13612w"] < -0.05,
        ],
        [
            "risk_dominant",
            "relief_dominant",
        ],
        default="mixed_or_neutral",
    )

    merged["event_balance_state_match"] = np.select(
        [
            merged["hsi_state"].isin(["risk_warning", "accident_zone"])
            & (merged["event_balance_13612w"] > 0),

            merged["hsi_state"].eq("risk_relief")
            & (merged["event_balance_13612w"] < 0),

            merged["hsi_state"].eq("conflict")
            & (merged["event_intensity_13612w"] >= 0.20),
        ],
        [
            "risk_state_with_risk_accumulation",
            "relief_state_with_relief_accumulation",
            "conflict_with_high_or_medium_intensity",
        ],
        default="weak_or_mixed_match",
    )

    return merged


def build_state_crosstab(diag: pd.DataFrame) -> pd.DataFrame:
    ct = pd.crosstab(
        diag["hsi_state"],
        diag["event_balance_13612w_label"],
        dropna=False,
    )

    ct = ct.reset_index()
    return ct


def build_intensity_crosstab(diag: pd.DataFrame) -> pd.DataFrame:
    ct = pd.crosstab(
        diag["hsi_state"],
        diag["event_intensity_13612w_label"],
        dropna=False,
    )

    ct = ct.reset_index()
    return ct


def build_numeric_summary(diag: pd.DataFrame) -> pd.DataFrame:
    summary = (
        diag
        .groupby(["hsi_state", "state_kr"])
        .agg(
            months=(YEAR_MONTH_COL, "count"),
            mean_event_balance=("event_balance_13612w", "mean"),
            median_event_balance=("event_balance_13612w", "median"),
            mean_event_intensity=("event_intensity_13612w", "mean"),
            median_event_intensity=("event_intensity_13612w", "median"),
            risk_dominant_ratio=("event_balance_sign", lambda s: (s == "risk_dominant").mean()),
            relief_dominant_ratio=("event_balance_sign", lambda s: (s == "relief_dominant").mean()),
            mixed_or_neutral_ratio=("event_balance_sign", lambda s: (s == "mixed_or_neutral").mean()),
        )
        .reset_index()
    )

    return summary


def build_diagnostic_summary(diag: pd.DataFrame) -> pd.DataFrame:
    valid = diag.dropna(subset=["event_balance_13612w", "event_intensity_13612w"]).copy()

    risk_states = valid[valid["hsi_state"].isin(["risk_warning", "accident_zone"])]
    relief_states = valid[valid["hsi_state"].eq("risk_relief")]
    conflict_states = valid[valid["hsi_state"].eq("conflict")]

    rows = []

    rows.append({
        "diagnostic_item": "risk_state_positive_balance_ratio",
        "value": (risk_states["event_balance_13612w"] > 0).mean() if len(risk_states) > 0 else np.nan,
        "months": len(risk_states),
        "interpretation": "risk_warning/accident_zone에서 사건균형이 위험 우세인지 확인",
        "status": "OK" if len(risk_states) > 0 else "CHECK",
    })

    rows.append({
        "diagnostic_item": "relief_state_negative_balance_ratio",
        "value": (relief_states["event_balance_13612w"] < 0).mean() if len(relief_states) > 0 else np.nan,
        "months": len(relief_states),
        "interpretation": "risk_relief에서 사건균형이 완화 우세인지 확인",
        "status": "OK" if len(relief_states) > 0 else "CHECK",
    })

    rows.append({
        "diagnostic_item": "conflict_medium_or_high_intensity_ratio",
        "value": (conflict_states["event_intensity_13612w"] >= 0.20).mean() if len(conflict_states) > 0 else np.nan,
        "months": len(conflict_states),
        "interpretation": "conflict에서 극단 신호가 많이 누적되는지 확인",
        "status": "OK" if len(conflict_states) > 0 else "CHECK",
    })

    rows.append({
        "diagnostic_item": "valid_months",
        "value": len(valid),
        "months": len(valid),
        "interpretation": "사건균형지표와 HSI 상태가 모두 유효한 월 수",
        "status": "OK" if len(valid) > 0 else "CHECK",
    })

    return pd.DataFrame(rows)


def build_note(numeric_summary: pd.DataFrame, diagnostic_summary: pd.DataFrame) -> str:
    lines = []

    lines.append("# main_final 사건균형지표와 HSI 5상태 정합성 진단 노트")
    lines.append("")
    lines.append(f"- 생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## 1. 목적")
    lines.append("")
    lines.append(
        "이 단계는 사건균형지표가 HSI 상태분류와 해석상 맞물리는지 확인한다. "
        "사건균형지표는 외부 사건 달력이 아니라 HSI 내부 신호의 위험·완화 누적 흐름을 요약한 보조지표이다."
    )
    lines.append("")
    lines.append("## 2. 해석 기준")
    lines.append("")
    lines.append("- risk_warning / accident_zone에서는 event_balance가 양수이면 정합적이다.")
    lines.append("- risk_relief에서는 event_balance가 음수이면 정합적이다.")
    lines.append("- conflict에서는 event_balance 방향보다 event_intensity가 높은지가 중요하다.")
    lines.append("")
    lines.append("## 3. 진단 요약")
    lines.append("")
    lines.append("| diagnostic_item | value | months | status | interpretation |")
    lines.append("|---|---:|---:|---|---|")
    for _, row in diagnostic_summary.iterrows():
        value = "" if pd.isna(row["value"]) else f"{row['value']:.4f}"
        lines.append(
            f"| {row['diagnostic_item']} | {value} | {row['months']} | "
            f"{row['status']} | {row['interpretation']} |"
        )
    lines.append("")
    lines.append("## 4. 상태별 사건균형 요약")
    lines.append("")
    lines.append("| hsi_state | months | mean_event_balance | mean_event_intensity |")
    lines.append("|---|---:|---:|---:|")
    for _, row in numeric_summary.iterrows():
        lines.append(
            f"| {row['hsi_state']} | {row['months']} | "
            f"{row['mean_event_balance']:.6f} | {row['mean_event_intensity']:.6f} |"
        )
    lines.append("")
    lines.append("## 5. 다음 단계")
    lines.append("")
    lines.append(
        "`09_event_balance_filter_backtest.py`에서는 사건균형지표를 HSI 상태를 대체하는 신호가 아니라 "
        "±5~10%p 보조 비중 조정 필터로 제한하여 실험한다."
    )
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    print("=" * 80)
    print("08_event_balance_state_diagnostic.py 실행 시작")
    print("=" * 80)

    cfg.ensure_final_directories()

    print("[1] 입력 파일 로드")
    state_table = read_csv(INPUT_STATE_TABLE, "HSI 5상태표")
    event_balance = read_csv(INPUT_EVENT_BALANCE, "월말 사건균형지표")
    print(f"    state_table shape = {state_table.shape}")
    print(f"    event_balance shape = {event_balance.shape}")

    print("[2] 정합성 진단 테이블 생성")
    diag = build_diagnostic_table(state_table, event_balance)
    save_csv(diag, OUTPUT_DIAGNOSTIC)
    print(f"    저장: {OUTPUT_DIAGNOSTIC}")

    print("[3] crosstab 생성")
    state_ct = build_state_crosstab(diag)
    intensity_ct = build_intensity_crosstab(diag)

    save_csv(state_ct, OUTPUT_STATE_CROSSTAB)
    save_csv(intensity_ct, OUTPUT_INTENSITY_CROSSTAB)

    print(f"    저장: {OUTPUT_STATE_CROSSTAB}")
    print(f"    저장: {OUTPUT_INTENSITY_CROSSTAB}")

    print("[4] 숫자 요약표 생성")
    numeric_summary = build_numeric_summary(diag)
    diagnostic_summary = build_diagnostic_summary(diag)

    save_csv(numeric_summary, OUTPUT_NUMERIC_SUMMARY)
    save_csv(diagnostic_summary, OUTPUT_DIAGNOSTIC_SUMMARY)

    print(f"    저장: {OUTPUT_NUMERIC_SUMMARY}")
    print(f"    저장: {OUTPUT_DIAGNOSTIC_SUMMARY}")

    print("[5] Markdown 노트 저장")
    note = build_note(numeric_summary, diagnostic_summary)
    OUTPUT_NOTE.write_text(note, encoding="utf-8")
    print(f"    저장: {OUTPUT_NOTE}")

    print("\n[진단 요약]")
    print(diagnostic_summary.to_string(index=False))

    print("\n[상태별 사건균형 숫자 요약]")
    print(numeric_summary.to_string(index=False))

    print("=" * 80)
    print("08_event_balance_state_diagnostic.py 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()