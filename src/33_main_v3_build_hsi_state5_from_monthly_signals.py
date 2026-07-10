from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd


"""
33_main_v3_build_hsi_state5_from_monthly_signals.py

목적
----
32번에서 만든 월말 HSI 신호 입력표를 사용해
HSI 5상태 분류표를 생성한다.

현재 단계에서는 비중 조정, 백테스트, Grid Search를 실행하지 않는다.
이 파일은 월말 신호가 HSI 상태분류로 자연스럽게 연결되는지 확인한다.

입력
----
data/processed/main_v3_monthly_signal_inputs_long.csv
data/processed/monthly_returns.csv

출력
----
data/processed/main_v3_hsi_state5_table.csv
data/processed/main_v3_hsi_state_return_alignment_preview.csv

output/tables/main_v3_hsi_state5_distribution.csv
output/tables/main_v3_hsi_state5_quality_check.csv

docs/main_v3_hsi_state5_note.md
"""


# ============================================================
# 0. 경로 설정
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
TABLE_DIR = PROJECT_ROOT / "output" / "tables"
DOCS_DIR = PROJECT_ROOT / "docs"

DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
TABLE_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

INPUT_MONTHLY_SIGNAL_LONG = DATA_PROCESSED_DIR / "main_v3_monthly_signal_inputs_long.csv"
INPUT_MONTHLY_RETURNS = DATA_PROCESSED_DIR / "monthly_returns.csv"

OUTPUT_HSI_STATE_TABLE = DATA_PROCESSED_DIR / "main_v3_hsi_state5_table.csv"
OUTPUT_ALIGNMENT_PREVIEW = DATA_PROCESSED_DIR / "main_v3_hsi_state_return_alignment_preview.csv"

OUTPUT_STATE_DISTRIBUTION = TABLE_DIR / "main_v3_hsi_state5_distribution.csv"
OUTPUT_QUALITY_CHECK = TABLE_DIR / "main_v3_hsi_state5_quality_check.csv"

OUTPUT_NOTE = DOCS_DIR / "main_v3_hsi_state5_note.md"


# ============================================================
# 1. 설정
# ============================================================

RISK_TICKER = "069500"

# 069500은 benchmark이므로 score_rs는 상태분류에서 제외한다.
CORE_STATE_SIGNALS = [
    "score_return",
    "score_ma_pos",
    "score_momentum",
    "score_vol",
]

# score는 대체로 -10 ~ +10 범위.
# 양수 = 위험 악화 방향, 음수 = 위험 완화 방향.
SCORE_SCALE = 10.0

MIN_VALID_SIGNALS = 3
NEUTRAL_SCORE_BAND = 1.0

STATE_ORDER = [
    "risk_relief",
    "neutral_watch",
    "conflict",
    "risk_warning",
    "accident_zone",
    "insufficient_data",
]


# ============================================================
# 2. 유틸 함수
# ============================================================

def require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"필수 입력 파일을 찾을 수 없습니다: {path}")


def classify_state(
    hsi_direction: float,
    hsi_intensity: float,
    positive_count: int,
    negative_count: int,
    neutral_count: int,
    valid_signal_count: int,
) -> tuple[str, str]:
    """
    HSI 5상태를 분류한다.

    상태 의미
    --------
    risk_relief      : 위험 완화 우세
    neutral_watch    : 관찰·중립
    conflict         : 위험 악화와 완화 신호가 충돌
    risk_warning     : 위험 악화 우세
    accident_zone    : 강한 위험 악화
    insufficient_data: warm-up 등으로 신호 부족
    """
    if valid_signal_count < MIN_VALID_SIGNALS:
        return (
            "insufficient_data",
            f"valid_signal_count={valid_signal_count} < {MIN_VALID_SIGNALS}",
        )

    conflict_ratio = (
        min(positive_count, negative_count) / valid_signal_count
        if valid_signal_count > 0
        else 0
    )

    # 악화와 완화 신호가 함께 있고, 방향값이 한쪽으로 강하게 기울지 않으면 conflict.
    if (
        positive_count >= 1
        and negative_count >= 1
        and conflict_ratio >= 0.25
        and abs(hsi_direction) < 0.20
    ):
        return (
            "conflict",
            (
                f"positive={positive_count}, negative={negative_count}, "
                f"conflict_ratio={conflict_ratio:.2f}, direction={hsi_direction:.3f}"
            ),
        )

    # 양수 방향은 위험 악화.
    if (
        hsi_direction >= 0.35
        and hsi_intensity >= 0.35
        and positive_count >= 3
    ):
        return (
            "accident_zone",
            (
                f"strong risk direction: direction={hsi_direction:.3f}, "
                f"intensity={hsi_intensity:.3f}, positive={positive_count}"
            ),
        )

    if hsi_direction >= 0.15 and positive_count >= 2:
        return (
            "risk_warning",
            (
                f"risk warning: direction={hsi_direction:.3f}, "
                f"positive={positive_count}, negative={negative_count}"
            ),
        )

    # 음수 방향은 위험 완화.
    if hsi_direction <= -0.15 and negative_count >= 2:
        return (
            "risk_relief",
            (
                f"risk relief: direction={hsi_direction:.3f}, "
                f"negative={negative_count}, positive={positive_count}"
            ),
        )

    return (
        "neutral_watch",
        (
            f"neutral/watch: direction={hsi_direction:.3f}, "
            f"positive={positive_count}, negative={negative_count}, neutral={neutral_count}"
        ),
    )


def build_hsi_state_table(monthly_signal_long: pd.DataFrame) -> pd.DataFrame:
    rows = []

    risk_df = monthly_signal_long[
        monthly_signal_long["ticker"].astype(str) == RISK_TICKER
    ].copy()

    risk_df = risk_df.sort_values("year_month")

    for _, row in risk_df.iterrows():
        year_month = row["year_month"]

        signal_values = {}
        for col in CORE_STATE_SIGNALS:
            value = row[col] if col in row.index else np.nan
            signal_values[col] = value

        score_series = pd.Series(signal_values, dtype="float64")
        valid_scores = score_series.dropna()

        valid_signal_count = len(valid_scores)

        if valid_signal_count == 0:
            hsi_direction = np.nan
            hsi_intensity = np.nan
            positive_count = 0
            negative_count = 0
            neutral_count = 0
        else:
            positive_count = int((valid_scores > NEUTRAL_SCORE_BAND).sum())
            negative_count = int((valid_scores < -NEUTRAL_SCORE_BAND).sum())
            neutral_count = int(valid_signal_count - positive_count - negative_count)

            # score가 -10~+10 범위라는 점을 이용해 -1~+1 방향값으로 축소.
            hsi_direction = valid_scores.sum() / (valid_signal_count * SCORE_SCALE)

            # 신호 강도는 절댓값 평균을 0~1 범위로 축소.
            hsi_intensity = valid_scores.abs().mean() / SCORE_SCALE

        hsi_state, state_reason = classify_state(
            hsi_direction=hsi_direction if not pd.isna(hsi_direction) else 0,
            hsi_intensity=hsi_intensity if not pd.isna(hsi_intensity) else 0,
            positive_count=positive_count,
            negative_count=negative_count,
            neutral_count=neutral_count,
            valid_signal_count=valid_signal_count,
        )

        state_valid = hsi_state != "insufficient_data"

        active_signals = ", ".join(valid_scores.index.tolist())

        rows.append({
            "year_month": year_month,
            "score_method_source": row.get("score_method_source", ""),
            "risk_ticker": RISK_TICKER,
            "risk_asset_name": row.get("name", ""),
            "hsi_direction": round(hsi_direction, 6) if not pd.isna(hsi_direction) else np.nan,
            "hsi_intensity": round(hsi_intensity, 6) if not pd.isna(hsi_intensity) else np.nan,
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": neutral_count,
            "valid_signal_count": valid_signal_count,
            "state_valid": state_valid,
            "hsi_state": hsi_state,
            "state_reason": state_reason,
            "active_signals": active_signals,
            "score_return": row.get("score_return", np.nan),
            "score_ma_pos": row.get("score_ma_pos", np.nan),
            "score_momentum": row.get("score_momentum", np.nan),
            "score_vol": row.get("score_vol", np.nan),
            "score_rs_excluded_reason": "069500 is benchmark; score_rs excluded from state rule",
        })

    return pd.DataFrame(rows)


def build_state_distribution(hsi_state_table: pd.DataFrame) -> pd.DataFrame:
    total_all = len(hsi_state_table)

    dist = (
        hsi_state_table
        .groupby(["hsi_state", "state_valid"], dropna=False)
        .size()
        .reset_index(name="month_count")
    )

    dist["share_all_months"] = dist["month_count"] / total_all

    valid_total = int(hsi_state_table["state_valid"].sum())
    dist["share_valid_months"] = dist.apply(
        lambda r: (
            r["month_count"] / valid_total
            if r["state_valid"] and valid_total > 0
            else np.nan
        ),
        axis=1,
    )

    dist["state_order"] = dist["hsi_state"].apply(
        lambda x: STATE_ORDER.index(x) if x in STATE_ORDER else 999
    )

    return dist.sort_values("state_order").drop(columns="state_order")


def build_alignment_preview(
    hsi_state_table: pd.DataFrame,
    monthly_returns: pd.DataFrame,
) -> pd.DataFrame:
    returns = monthly_returns.copy()

    if "year_month" in returns.columns:
        returns = returns.set_index("year_month")

    returns.index = returns.index.astype(str)
    returns.index.name = "return_month"

    returns_renamed = returns.copy()
    returns_renamed.columns = [f"next_return_{c}" for c in returns_renamed.columns]

    returns_renamed = returns_renamed.reset_index()
    returns_renamed["signal_month"] = (
        pd.PeriodIndex(returns_renamed["return_month"], freq="M") - 1
    ).astype(str)

    state_small = hsi_state_table.copy()
    state_small = state_small.rename(columns={"year_month": "signal_month"})

    keep_cols = [
        "signal_month",
        "hsi_state",
        "state_valid",
        "hsi_direction",
        "hsi_intensity",
        "positive_count",
        "negative_count",
        "valid_signal_count",
    ]

    aligned = pd.merge(
        state_small[keep_cols],
        returns_renamed,
        on="signal_month",
        how="inner",
    )

    aligned["alignment_rule"] = "signal_month_t_to_return_month_t_plus_1"

    return aligned


def build_quality_check(
    hsi_state_table: pd.DataFrame,
    state_distribution: pd.DataFrame,
    alignment_preview: pd.DataFrame,
) -> pd.DataFrame:
    total_months = len(hsi_state_table)
    valid_months = int(hsi_state_table["state_valid"].sum())
    invalid_months = total_months - valid_months

    valid_df = hsi_state_table[hsi_state_table["state_valid"]].copy()

    rows = []

    rows.append({
        "check_item": "hsi_state_table_shape",
        "result": f"{hsi_state_table.shape[0]} rows x {hsi_state_table.shape[1]} columns",
        "status": "OK" if total_months > 0 else "CHECK",
        "note": "월별 HSI 상태표 생성 여부",
    })

    rows.append({
        "check_item": "valid_state_months",
        "result": valid_months,
        "status": "OK" if valid_months > 0 else "CHECK",
        "note": "warm-up 이후 상태분류 가능 월 수",
    })

    rows.append({
        "check_item": "insufficient_data_months",
        "result": invalid_months,
        "status": "INFO",
        "note": "rolling 계산 초기 구간은 insufficient_data가 자연스러움",
    })

    rows.append({
        "check_item": "first_valid_month",
        "result": valid_df["year_month"].iloc[0] if len(valid_df) > 0 else "",
        "status": "OK" if len(valid_df) > 0 else "CHECK",
        "note": "백테스트 연결 시 이 시점 이후 사용 권장",
    })

    rows.append({
        "check_item": "last_valid_month",
        "result": valid_df["year_month"].iloc[-1] if len(valid_df) > 0 else "",
        "status": "OK" if len(valid_df) > 0 else "CHECK",
        "note": "상태분류 마지막 월",
    })

    unique_states = sorted(valid_df["hsi_state"].unique().tolist()) if len(valid_df) > 0 else []
    rows.append({
        "check_item": "valid_state_types",
        "result": ", ".join(unique_states),
        "status": "OK" if len(unique_states) >= 2 else "CHECK",
        "note": "한 가지 상태만 나오면 기준 조정 필요",
    })

    rows.append({
        "check_item": "alignment_preview_shape",
        "result": f"{alignment_preview.shape[0]} rows x {alignment_preview.shape[1]} columns",
        "status": "OK" if len(alignment_preview) > 0 else "CHECK",
        "note": "월말 HSI 상태와 다음 달 수익률 연결 preview",
    })

    return pd.DataFrame(rows)


def make_markdown_note(
    hsi_state_table: pd.DataFrame,
    state_distribution: pd.DataFrame,
    quality_check: pd.DataFrame,
) -> str:
    lines = []

    lines.append("# main_v3 HSI 5상태 분류 노트")
    lines.append("")
    lines.append(f"- 생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## 1. 목적")
    lines.append("")
    lines.append(
        "32번에서 생성한 월말 HSI 신호 입력표를 사용해 HSI 5상태 분류표를 생성하였다. "
        "이번 단계는 비중 조정과 백테스트로 넘어가기 전, 월말 신호가 상태분류로 연결되는지 확인하는 단계이다."
    )
    lines.append("")
    lines.append("## 2. 상태 정의")
    lines.append("")
    lines.append("| 상태 | 의미 |")
    lines.append("|---|---|")
    lines.append("| risk_relief | 위험 완화 우세 |")
    lines.append("| neutral_watch | 관찰·중립 |")
    lines.append("| conflict | 위험 악화 신호와 위험 완화 신호가 충돌 |")
    lines.append("| risk_warning | 위험 악화 우세 |")
    lines.append("| accident_zone | 강한 위험 악화 |")
    lines.append("| insufficient_data | rolling 계산 초기 구간 등으로 신호 부족 |")
    lines.append("")
    lines.append("## 3. 사용 신호")
    lines.append("")
    lines.append(
        "상태분류는 위험자산 대표 ETF인 `069500`의 핵심 신호를 기준으로 계산하였다. "
        "`069500`은 상대강도 benchmark이므로 `score_rs`는 자기비교 값으로 보아 상태분류에서 제외하였다."
    )
    lines.append("")
    lines.append("사용 신호:")
    lines.append("")
    for sig in CORE_STATE_SIGNALS:
        lines.append(f"- `{sig}`")
    lines.append("")
    lines.append("## 4. 상태분포")
    lines.append("")
    lines.append("| hsi_state | state_valid | month_count | share_all_months | share_valid_months |")
    lines.append("|---|---|---:|---:|---:|")

    for _, row in state_distribution.iterrows():
        share_all = (
            f"{row['share_all_months']:.4f}"
            if not pd.isna(row["share_all_months"])
            else ""
        )
        share_valid = (
            f"{row['share_valid_months']:.4f}"
            if not pd.isna(row["share_valid_months"])
            else ""
        )
        lines.append(
            f"| {row['hsi_state']} | {row['state_valid']} | "
            f"{row['month_count']} | {share_all} | {share_valid} |"
        )

    lines.append("")
    lines.append("## 5. 품질 점검")
    lines.append("")
    lines.append("| check_item | result | status | note |")
    lines.append("|---|---|---|---|")

    for _, row in quality_check.iterrows():
        lines.append(
            f"| {row['check_item']} | {row['result']} | {row['status']} | {row['note']} |"
        )

    lines.append("")
    lines.append("## 6. 다음 단계")
    lines.append("")
    lines.append(
        "다음 단계에서는 이 HSI 상태표를 `main_v2b` 기준 비중 규칙에 연결하여 "
        "월별 리밸런싱 비중표를 생성한다. 이후 월간 수익률과 결합해 백테스트로 넘어간다."
    )
    lines.append("")

    return "\n".join(lines)


# ============================================================
# 3. 실행
# ============================================================

def main() -> None:
    print("=" * 80)
    print("33_main_v3_build_hsi_state5_from_monthly_signals.py 실행 시작")
    print("=" * 80)

    print("[1] 입력 파일 확인")
    for path in [INPUT_MONTHLY_SIGNAL_LONG, INPUT_MONTHLY_RETURNS]:
        require_file(path)
        print(f"    OK: {path}")

    print("[2] 입력 데이터 로드")
    monthly_signal_long = pd.read_csv(INPUT_MONTHLY_SIGNAL_LONG, dtype={"ticker": str})
    monthly_returns = pd.read_csv(INPUT_MONTHLY_RETURNS)

    print(f"    monthly_signal_long shape = {monthly_signal_long.shape}")
    print(f"    monthly_returns shape = {monthly_returns.shape}")

    print("[3] HSI 5상태 분류표 생성")
    hsi_state_table = build_hsi_state_table(monthly_signal_long)

    print("[4] 상태분포 생성")
    state_distribution = build_state_distribution(hsi_state_table)

    print("[5] 월말 상태와 다음 달 수익률 연결 preview 생성")
    alignment_preview = build_alignment_preview(
        hsi_state_table=hsi_state_table,
        monthly_returns=monthly_returns,
    )

    print("[6] 품질 점검표 생성")
    quality_check = build_quality_check(
        hsi_state_table=hsi_state_table,
        state_distribution=state_distribution,
        alignment_preview=alignment_preview,
    )

    print("[7] CSV 저장")
    hsi_state_table.to_csv(OUTPUT_HSI_STATE_TABLE, index=False, encoding="utf-8-sig")
    alignment_preview.to_csv(OUTPUT_ALIGNMENT_PREVIEW, index=False, encoding="utf-8-sig")
    state_distribution.to_csv(OUTPUT_STATE_DISTRIBUTION, index=False, encoding="utf-8-sig")
    quality_check.to_csv(OUTPUT_QUALITY_CHECK, index=False, encoding="utf-8-sig")

    print("[8] Markdown 노트 저장")
    note = make_markdown_note(
        hsi_state_table=hsi_state_table,
        state_distribution=state_distribution,
        quality_check=quality_check,
    )
    OUTPUT_NOTE.write_text(note, encoding="utf-8")

    print("\n[저장 완료]")
    for path in [
        OUTPUT_HSI_STATE_TABLE,
        OUTPUT_ALIGNMENT_PREVIEW,
        OUTPUT_STATE_DISTRIBUTION,
        OUTPUT_QUALITY_CHECK,
        OUTPUT_NOTE,
    ]:
        print(f"- {path}")

    print("\n[품질 점검]")
    print(quality_check.to_string(index=False))

    print("\n[상태분포]")
    print(state_distribution.to_string(index=False))

    print("\n[상태표 preview]")
    preview_cols = [
        "year_month",
        "hsi_state",
        "state_valid",
        "hsi_direction",
        "hsi_intensity",
        "positive_count",
        "negative_count",
        "valid_signal_count",
        "state_reason",
    ]
    print(hsi_state_table[preview_cols].head(15).to_string(index=False))

    print("\n" + "=" * 80)
    print("33_main_v3_build_hsi_state5_from_monthly_signals.py 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()