from __future__ import annotations

from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd

try:
    import final_project_config as cfg
except ModuleNotFoundError as exc:
    raise ModuleNotFoundError(
        "final_project_config.py를 찾지 못했습니다. "
        "이 파일을 기존 src 폴더에 저장한 뒤 실행해 주세요."
    ) from exc


"""
50_hsi_input_contribution.py

목적
----
04번 main_final HSI 5상태 계산식을 변경하지 않고,
각 입력점수가 다음 내부 계산값을 얼마나 구성했는지 변수별로 분해한다.

- risk_component
- relief_component
- state_direction
- state_intensity

중요
----
이 파일의 '기여도'는 미래수익률 예측에 대한 feature importance가 아니다.
HSI 상태판정 계산식 안에서 각 입력점수가 차지한 내부 계산 기여도이다.

기준 계산식
-----------
월 t의 유효 점수 수를 n_t, 점수 스케일을 10, 변수 j의 점수를 s_j,t라고 하면:

risk contribution      = max(s_j,t, 0)  / (n_t * 10)
relief contribution    = max(-s_j,t, 0) / (n_t * 10)
direction contribution = s_j,t          / (n_t * 10)
intensity contribution = abs(s_j,t)     / (n_t * 10)

입력
----
data/processed/main_final_monthly_signal_inputs_long.csv
data/processed/main_final_hsi_state5_table.csv

출력
----
output/tables/main_final_50_input_contribution_monthly.csv
output/tables/main_final_50_input_contribution_summary.csv
output/tables/main_final_50_input_contribution_by_state.csv
output/tables/main_final_50_input_contribution_formula.csv
output/tables/main_final_50_input_contribution_audit.csv
output/tables/main_final_50_input_contribution_audit_monthly.csv

output/figures/main_final_50_fig01_monthly_direction_contribution.png
output/figures/main_final_50_fig02_average_contribution_share.png
output/figures/main_final_50_fig03_state_mean_contribution_heatmap.png
output/figures/main_final_50_fig04_reconstruction_audit.png

docs/main_final_50_hsi_input_contribution_note.md
"""


# ============================================================
# 0. 입력·출력 경로
# ============================================================

INPUT_MONTHLY_SIGNAL_LONG = (
    cfg.PROCESSED_DIR / "main_final_monthly_signal_inputs_long.csv"
)
INPUT_STATE_TABLE = cfg.PROCESSED_DIR / "main_final_hsi_state5_table.csv"

OUTPUT_MONTHLY = cfg.TABLE_DIR / "main_final_50_input_contribution_monthly.csv"
OUTPUT_SUMMARY = cfg.TABLE_DIR / "main_final_50_input_contribution_summary.csv"
OUTPUT_BY_STATE = cfg.TABLE_DIR / "main_final_50_input_contribution_by_state.csv"
OUTPUT_FORMULA = cfg.TABLE_DIR / "main_final_50_input_contribution_formula.csv"
OUTPUT_AUDIT = cfg.TABLE_DIR / "main_final_50_input_contribution_audit.csv"
OUTPUT_AUDIT_MONTHLY = (
    cfg.TABLE_DIR / "main_final_50_input_contribution_audit_monthly.csv"
)

FIGURE_DIR = Path(getattr(cfg, "FIGURE_DIR", Path(cfg.TABLE_DIR).parent / "figures"))

OUTPUT_FIG_MONTHLY = (
    FIGURE_DIR / "main_final_50_fig01_monthly_direction_contribution.png"
)
OUTPUT_FIG_SHARE = (
    FIGURE_DIR / "main_final_50_fig02_average_contribution_share.png"
)
OUTPUT_FIG_STATE = (
    FIGURE_DIR / "main_final_50_fig03_state_mean_contribution_heatmap.png"
)
OUTPUT_FIG_AUDIT = (
    FIGURE_DIR / "main_final_50_fig04_reconstruction_audit.png"
)

OUTPUT_NOTE = cfg.DOCS_DIR / "main_final_50_hsi_input_contribution_note.md"


# ============================================================
# 1. 04번 baseline과 동일한 설정
# ============================================================

YEAR_MONTH_COL = "year_month"
TICKER_COL = "ticker"
MARKET_STATE_TICKER = str(cfg.RISK_TICKER).zfill(6)

SCORE_COLS = [
    "score_return",
    "score_ma_pos",
    "score_momentum",
    "score_vol",
    "score_rs",
]

SIGNAL_LABELS = {
    "score_return": "수익률(return)",
    "score_ma_pos": "이동평균 대비 위치(ma_pos)",
    "score_momentum": "모멘텀(momentum)",
    "score_vol": "변동성(vol)",
    "score_rs": "상대강도(rs)",
}

SCORE_SCALE = 10.0
MIN_VALID_SCORE_COUNT = 3

THETA_COMMON = 0.15
ACCIDENT_EXTRA = 0.20
DIRECTION_MARGIN = 0.05
CONFLICT_DIRECTION_BAND = 0.20

AUDIT_TOLERANCE = 1e-10

STATE_ORDER = [
    "risk_relief",
    "neutral_watch",
    "conflict",
    "risk_warning",
    "accident_zone",
    "insufficient_data",
]


# ============================================================
# 2. 공통 유틸
# ============================================================


def ensure_directories() -> None:
    """기존 config 함수와 개별 출력 폴더 생성을 함께 보장한다."""
    if hasattr(cfg, "ensure_final_directories"):
        cfg.ensure_final_directories()

    for path in [
        cfg.PROCESSED_DIR,
        cfg.TABLE_DIR,
        FIGURE_DIR,
        cfg.DOCS_DIR,
    ]:
        Path(path).mkdir(parents=True, exist_ok=True)


def read_csv(path: Path, label: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{label} 파일이 없습니다: {path}")
    return pd.read_csv(path, encoding="utf-8-sig")


def save_csv(df: pd.DataFrame, path: Path, index: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=index, encoding="utf-8-sig")


def set_plot_font() -> None:
    """Windows 우선으로 한글 폰트를 선택하고, 없으면 기본 폰트를 사용한다."""
    installed = {font.name for font in font_manager.fontManager.ttflist}
    for candidate in ["Malgun Gothic", "NanumGothic", "AppleGothic"]:
        if candidate in installed:
            plt.rcParams["font.family"] = candidate
            break
    plt.rcParams["axes.unicode_minus"] = False


def normalize_year_month(series: pd.Series) -> pd.Series:
    """YYYY-MM 형식으로 통일하되 변환할 수 없는 값은 원문 문자열을 유지한다."""
    raw = series.astype(str).str.strip()
    parsed = pd.to_datetime(raw, errors="coerce")
    result = raw.copy()
    valid = parsed.notna()
    result.loc[valid] = parsed.loc[valid].dt.to_period("M").astype(str)
    return result


def validate_required_columns(df: pd.DataFrame, required: list[str], label: str) -> None:
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"{label}에 필요한 컬럼이 없습니다: {missing}")


# ============================================================
# 3. 04번 상태분류 규칙 재현
# ============================================================


def classify_from_components(
    risk_component: float,
    relief_component: float,
    state_direction: float,
    valid_score_count: int,
) -> tuple[str, str]:
    """04_build_hsi_state5_baseline.py와 동일한 순서로 상태를 재분류한다."""
    if valid_score_count < MIN_VALID_SCORE_COUNT:
        return "insufficient_data", "valid_score_count_below_minimum"

    if (
        risk_component >= THETA_COMMON + ACCIDENT_EXTRA
        and state_direction > 0
    ):
        return "accident_zone", "risk_component_above_accident_threshold"

    if (
        risk_component >= THETA_COMMON
        and relief_component >= THETA_COMMON
        and abs(state_direction) <= CONFLICT_DIRECTION_BAND
    ):
        return "conflict", "risk_and_relief_components_both_active"

    if risk_component >= THETA_COMMON and state_direction > DIRECTION_MARGIN:
        return "risk_warning", "risk_component_dominant"

    if relief_component >= THETA_COMMON and state_direction < -DIRECTION_MARGIN:
        return "risk_relief", "relief_component_dominant"

    return "neutral_watch", "weak_or_balanced_signal"


# ============================================================
# 4. 입력변수별 내부 계산 기여도
# ============================================================


def prepare_market_signal_table(monthly_long: pd.DataFrame) -> pd.DataFrame:
    df = monthly_long.copy()

    validate_required_columns(
        df,
        [YEAR_MONTH_COL, TICKER_COL],
        "월말 HSI 입력표",
    )

    df[TICKER_COL] = df[TICKER_COL].astype(str).str.zfill(6)
    df[YEAR_MONTH_COL] = normalize_year_month(df[YEAR_MONTH_COL])

    market = df[df[TICKER_COL] == MARKET_STATE_TICKER].copy()
    if market.empty:
        raise ValueError(
            f"시장상태 기준 티커 {MARKET_STATE_TICKER} 행이 없습니다."
        )

    for score_col in SCORE_COLS:
        if score_col not in market.columns:
            market[score_col] = np.nan
        market[score_col] = pd.to_numeric(market[score_col], errors="coerce")

    duplicated = market.duplicated(subset=[YEAR_MONTH_COL], keep=False)
    if duplicated.any():
        duplicated_months = sorted(
            market.loc[duplicated, YEAR_MONTH_COL].astype(str).unique().tolist()
        )
        raise ValueError(
            "시장상태 기준 티커에 월별 중복행이 있습니다: "
            f"{duplicated_months[:10]}"
        )

    return market.sort_values(YEAR_MONTH_COL).reset_index(drop=True)


def build_monthly_contribution(market: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for _, row in market.iterrows():
        scores = pd.to_numeric(row[SCORE_COLS], errors="coerce")
        valid_mask = scores.notna()
        valid_count = int(valid_mask.sum())
        denominator = valid_count * SCORE_SCALE if valid_count > 0 else np.nan
        classification_valid = valid_count >= MIN_VALID_SCORE_COUNT

        output_row: dict[str, object] = {
            YEAR_MONTH_COL: row[YEAR_MONTH_COL],
            TICKER_COL: str(row[TICKER_COL]).zfill(6),
            "valid_score_count_reconstructed": valid_count,
            "contribution_denominator": denominator,
            "classification_valid": classification_valid,
        }

        for optional_col in [
            "ticker_name",
            "ticker_role",
            "score_date",
            "direction_date",
            "raw3_signal_date",
        ]:
            if optional_col in row.index:
                output_row[optional_col] = row.get(optional_col)

        for score_col in SCORE_COLS:
            score_value = scores.get(score_col, np.nan)
            output_row[score_col] = score_value
            output_row[f"{score_col}_is_valid"] = bool(pd.notna(score_value))

            if classification_valid and pd.notna(score_value):
                risk_value = max(float(score_value), 0.0) / denominator
                relief_value = max(-float(score_value), 0.0) / denominator
                direction_value = float(score_value) / denominator
                intensity_value = abs(float(score_value)) / denominator
            else:
                risk_value = np.nan
                relief_value = np.nan
                direction_value = np.nan
                intensity_value = np.nan

            output_row[f"{score_col}_risk_contribution"] = risk_value
            output_row[f"{score_col}_relief_contribution"] = relief_value
            output_row[f"{score_col}_direction_contribution"] = direction_value
            output_row[f"{score_col}_intensity_contribution"] = intensity_value

        risk_cols = [f"{col}_risk_contribution" for col in SCORE_COLS]
        relief_cols = [f"{col}_relief_contribution" for col in SCORE_COLS]
        direction_cols = [f"{col}_direction_contribution" for col in SCORE_COLS]
        intensity_cols = [f"{col}_intensity_contribution" for col in SCORE_COLS]

        if classification_valid:
            risk_component = float(
                np.nansum([output_row[col] for col in risk_cols])
            )
            relief_component = float(
                np.nansum([output_row[col] for col in relief_cols])
            )
            state_direction = float(
                np.nansum([output_row[col] for col in direction_cols])
            )
            state_intensity = float(
                np.nansum([output_row[col] for col in intensity_cols])
            )
        else:
            risk_component = np.nan
            relief_component = np.nan
            state_direction = np.nan
            state_intensity = np.nan

        reconstructed_state, reconstructed_reason = classify_from_components(
            risk_component=risk_component,
            relief_component=relief_component,
            state_direction=state_direction,
            valid_score_count=valid_count,
        )

        output_row.update(
            {
                "risk_component_reconstructed": risk_component,
                "relief_component_reconstructed": relief_component,
                "state_direction_reconstructed": state_direction,
                "state_intensity_reconstructed": state_intensity,
                "hsi_state_reconstructed": reconstructed_state,
                "state_reason_reconstructed": reconstructed_reason,
            }
        )
        rows.append(output_row)

    return pd.DataFrame(rows)


# ============================================================
# 5. 기존 상태표와의 계산 일치 검증
# ============================================================


def prepare_state_table(state_table: pd.DataFrame) -> pd.DataFrame:
    state = state_table.copy()
    validate_required_columns(
        state,
        [
            YEAR_MONTH_COL,
            "risk_component",
            "relief_component",
            "state_direction",
            "state_intensity",
            "valid_score_count",
            "hsi_state",
        ],
        "기존 HSI 상태표",
    )

    state[YEAR_MONTH_COL] = normalize_year_month(state[YEAR_MONTH_COL])
    if TICKER_COL in state.columns:
        state[TICKER_COL] = state[TICKER_COL].astype(str).str.zfill(6)
        state = state[state[TICKER_COL] == MARKET_STATE_TICKER].copy()

    for col in [
        "risk_component",
        "relief_component",
        "state_direction",
        "state_intensity",
        "valid_score_count",
    ]:
        state[col] = pd.to_numeric(state[col], errors="coerce")

    duplicated = state.duplicated(subset=[YEAR_MONTH_COL], keep=False)
    if duplicated.any():
        duplicated_months = sorted(
            state.loc[duplicated, YEAR_MONTH_COL].astype(str).unique().tolist()
        )
        raise ValueError(
            "기존 상태표에 월별 중복행이 있습니다: "
            f"{duplicated_months[:10]}"
        )

    keep = [
        YEAR_MONTH_COL,
        "risk_component",
        "relief_component",
        "state_direction",
        "state_intensity",
        "valid_score_count",
        "hsi_state",
    ]
    if "state_reason" in state.columns:
        keep.append("state_reason")

    return state[keep].sort_values(YEAR_MONTH_COL).reset_index(drop=True)


def build_audit(
    monthly_contribution: pd.DataFrame,
    state_table: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    merged = monthly_contribution.merge(
        state_table,
        on=YEAR_MONTH_COL,
        how="outer",
        validate="one_to_one",
        indicator=True,
    )

    metric_map = {
        "risk_component": "risk_component_reconstructed",
        "relief_component": "relief_component_reconstructed",
        "state_direction": "state_direction_reconstructed",
        "state_intensity": "state_intensity_reconstructed",
        "valid_score_count": "valid_score_count_reconstructed",
    }

    for original, reconstructed in metric_map.items():
        error_col = f"{original}_error"
        match_col = f"{original}_match"
        merged[error_col] = merged[reconstructed] - merged[original]

        both_nan = merged[reconstructed].isna() & merged[original].isna()
        numeric_match = merged[error_col].abs() <= AUDIT_TOLERANCE
        merged[match_col] = both_nan | numeric_match

    merged["hsi_state_match"] = (
        merged["hsi_state_reconstructed"].fillna("__NA__")
        == merged["hsi_state"].fillna("__NA__")
    )
    merged["row_complete_match"] = (
        merged[[f"{col}_match" for col in metric_map]].all(axis=1)
        & merged["hsi_state_match"]
        & merged["_merge"].eq("both")
    )

    summary_rows: list[dict[str, object]] = []

    for original, reconstructed in metric_map.items():
        error = merged[f"{original}_error"]
        comparable = merged[original].notna() | merged[reconstructed].notna()
        mismatch = comparable & ~merged[f"{original}_match"]

        summary_rows.append(
            {
                "audit_item": original,
                "comparison": f"{reconstructed} vs {original}",
                "comparable_rows": int(comparable.sum()),
                "mismatch_rows": int(mismatch.sum()),
                "max_abs_error": (
                    float(error.abs().max()) if error.notna().any() else 0.0
                ),
                "mean_abs_error": (
                    float(error.abs().mean()) if error.notna().any() else 0.0
                ),
                "tolerance": AUDIT_TOLERANCE,
                "status": "OK" if int(mismatch.sum()) == 0 else "CHECK",
            }
        )

    state_comparable = (
        merged["hsi_state"].notna()
        | merged["hsi_state_reconstructed"].notna()
    )
    state_mismatch = state_comparable & ~merged["hsi_state_match"]
    summary_rows.append(
        {
            "audit_item": "hsi_state",
            "comparison": "hsi_state_reconstructed vs hsi_state",
            "comparable_rows": int(state_comparable.sum()),
            "mismatch_rows": int(state_mismatch.sum()),
            "max_abs_error": np.nan,
            "mean_abs_error": np.nan,
            "tolerance": np.nan,
            "status": "OK" if int(state_mismatch.sum()) == 0 else "CHECK",
        }
    )

    missing_input = int((merged["_merge"] == "right_only").sum())
    missing_state = int((merged["_merge"] == "left_only").sum())
    summary_rows.extend(
        [
            {
                "audit_item": "missing_months_in_input",
                "comparison": "state table only",
                "comparable_rows": len(merged),
                "mismatch_rows": missing_input,
                "max_abs_error": np.nan,
                "mean_abs_error": np.nan,
                "tolerance": np.nan,
                "status": "OK" if missing_input == 0 else "CHECK",
            },
            {
                "audit_item": "missing_months_in_state_table",
                "comparison": "input table only",
                "comparable_rows": len(merged),
                "mismatch_rows": missing_state,
                "max_abs_error": np.nan,
                "mean_abs_error": np.nan,
                "tolerance": np.nan,
                "status": "OK" if missing_state == 0 else "CHECK",
            },
            {
                "audit_item": "all_fields_row_match",
                "comparison": "all reconstructed fields",
                "comparable_rows": len(merged),
                "mismatch_rows": int((~merged["row_complete_match"]).sum()),
                "max_abs_error": np.nan,
                "mean_abs_error": np.nan,
                "tolerance": np.nan,
                "status": (
                    "OK" if bool(merged["row_complete_match"].all()) else "CHECK"
                ),
            },
        ]
    )

    return pd.DataFrame(summary_rows), merged


# ============================================================
# 6. 요약표와 상태별 표
# ============================================================


def build_summary(monthly: pd.DataFrame) -> pd.DataFrame:
    direction_cols = [f"{col}_direction_contribution" for col in SCORE_COLS]
    total_abs = monthly[direction_cols].abs().sum(skipna=True).sum()

    rows: list[dict[str, object]] = []
    total_months = len(monthly)

    for score_col in SCORE_COLS:
        contribution_col = f"{score_col}_direction_contribution"
        valid_months = int(
            monthly[f"{score_col}_is_valid"].fillna(False).astype(bool).sum()
        )
        contribution_months = int(monthly[contribution_col].notna().sum())
        abs_sum = float(monthly[contribution_col].abs().sum(skipna=True))
        share = abs_sum / total_abs if total_abs > 0 else np.nan
        mean_signed = float(monthly[contribution_col].mean(skipna=True))
        mean_abs = float(monthly[contribution_col].abs().mean(skipna=True))

        is_active = valid_months > 0 and contribution_months > 0
        exclusion_reason = ""
        if valid_months == 0:
            exclusion_reason = "all_values_missing_or_not_provided"
        elif contribution_months == 0:
            exclusion_reason = "available_only_in_insufficient_data_months"

        rows.append(
            {
                "score_variable": score_col,
                "signal_label": SIGNAL_LABELS[score_col],
                "total_months": total_months,
                "raw_valid_months": valid_months,
                "contribution_valid_months": contribution_months,
                "raw_valid_ratio": valid_months / total_months if total_months else np.nan,
                "absolute_contribution_sum": abs_sum,
                "absolute_contribution_share": share,
                "mean_signed_direction_contribution": mean_signed,
                "mean_absolute_direction_contribution": mean_abs,
                "is_active_in_contribution": is_active,
                "exclusion_reason": exclusion_reason,
            }
        )

    return pd.DataFrame(rows).sort_values(
        ["is_active_in_contribution", "absolute_contribution_share"],
        ascending=[False, False],
    ).reset_index(drop=True)


def build_by_state(monthly_audit: pd.DataFrame) -> pd.DataFrame:
    valid = monthly_audit[
        monthly_audit["hsi_state_reconstructed"] != "insufficient_data"
    ].copy()

    rows: list[dict[str, object]] = []
    for state in STATE_ORDER:
        if state == "insufficient_data":
            continue
        state_df = valid[valid["hsi_state_reconstructed"] == state]
        if state_df.empty:
            continue

        for score_col in SCORE_COLS:
            rows.append(
                {
                    "hsi_state": state,
                    "months": len(state_df),
                    "score_variable": score_col,
                    "signal_label": SIGNAL_LABELS[score_col],
                    "mean_risk_contribution": state_df[
                        f"{score_col}_risk_contribution"
                    ].mean(skipna=True),
                    "mean_relief_contribution": state_df[
                        f"{score_col}_relief_contribution"
                    ].mean(skipna=True),
                    "mean_direction_contribution": state_df[
                        f"{score_col}_direction_contribution"
                    ].mean(skipna=True),
                    "mean_intensity_contribution": state_df[
                        f"{score_col}_intensity_contribution"
                    ].mean(skipna=True),
                    "valid_contribution_months": int(
                        state_df[f"{score_col}_direction_contribution"].notna().sum()
                    ),
                }
            )

    return pd.DataFrame(rows)


def build_formula_table() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "calculation_item": "variable_risk_contribution",
                "formula": "max(score_j_t, 0) / (valid_score_count_t * 10)",
                "meaning": "변수 j가 위험 악화 성분에 더한 내부 계산값",
            },
            {
                "calculation_item": "variable_relief_contribution",
                "formula": "max(-score_j_t, 0) / (valid_score_count_t * 10)",
                "meaning": "변수 j가 위험 완화 성분에 더한 내부 계산값",
            },
            {
                "calculation_item": "variable_direction_contribution",
                "formula": "score_j_t / (valid_score_count_t * 10)",
                "meaning": "변수 j가 최종 direction에 더하거나 뺀 내부 계산값",
            },
            {
                "calculation_item": "variable_intensity_contribution",
                "formula": "abs(score_j_t) / (valid_score_count_t * 10)",
                "meaning": "변수 j가 최종 intensity에 더한 내부 계산값",
            },
            {
                "calculation_item": "risk_component",
                "formula": "sum(variable_risk_contribution_j_t)",
                "meaning": "위험 악화 방향 기여의 합",
            },
            {
                "calculation_item": "relief_component",
                "formula": "sum(variable_relief_contribution_j_t)",
                "meaning": "위험 완화 방향 기여의 합",
            },
            {
                "calculation_item": "state_direction",
                "formula": "risk_component - relief_component",
                "meaning": "양수는 위험 악화, 음수는 위험 완화 방향",
            },
            {
                "calculation_item": "state_intensity",
                "formula": "risk_component + relief_component",
                "meaning": "방향과 무관한 전체 신호 강도",
            },
        ]
    )


# ============================================================
# 7. 시각화
# ============================================================


def get_active_score_cols(summary: pd.DataFrame) -> list[str]:
    active = summary.loc[
        summary["is_active_in_contribution"], "score_variable"
    ].tolist()
    if not active:
        raise ValueError("시각화할 유효 입력신호 기여도가 없습니다.")
    return active


def plot_monthly_direction_contribution(
    monthly: pd.DataFrame,
    summary: pd.DataFrame,
) -> None:
    set_plot_font()
    active_scores = get_active_score_cols(summary)

    plot_df = monthly.copy()
    plot_df["plot_date"] = pd.to_datetime(
        plot_df[YEAR_MONTH_COL].astype(str) + "-01",
        errors="coerce",
    )
    plot_df = plot_df.dropna(subset=["plot_date"]).sort_values("plot_date")

    fig, ax = plt.subplots(figsize=(18, 7))
    default_colors = plt.rcParams["axes.prop_cycle"].by_key().get("color", [])

    positive_bottom = np.zeros(len(plot_df))
    negative_bottom = np.zeros(len(plot_df))

    for index, score_col in enumerate(active_scores):
        values = plot_df[f"{score_col}_direction_contribution"].fillna(0.0).to_numpy()
        positive = np.where(values > 0, values, 0.0)
        negative = np.where(values < 0, values, 0.0)
        kwargs = {}
        if default_colors:
            kwargs["color"] = default_colors[index % len(default_colors)]

        ax.bar(
            plot_df["plot_date"],
            positive,
            bottom=positive_bottom,
            width=20,
            label=SIGNAL_LABELS[score_col],
            **kwargs,
        )
        ax.bar(
            plot_df["plot_date"],
            negative,
            bottom=negative_bottom,
            width=20,
            **kwargs,
        )
        positive_bottom += positive
        negative_bottom += negative

    ax.plot(
        plot_df["plot_date"],
        plot_df["state_direction_reconstructed"],
        linewidth=1.5,
        label="state_direction(재구성)",
    )
    ax.axhline(0.0, linewidth=0.8)
    ax.axhline(DIRECTION_MARGIN, linestyle="--", linewidth=0.8)
    ax.axhline(-DIRECTION_MARGIN, linestyle="--", linewidth=0.8)
    ax.axhline(THETA_COMMON, linestyle=":", linewidth=0.8)
    ax.axhline(-THETA_COMMON, linestyle=":", linewidth=0.8)

    ax.set_title(
        "HSI 입력변수별 월별 direction 내부 계산 기여도 "
        f"({MARKET_STATE_TICKER}, 월말 기준)"
    )
    ax.set_xlabel("월")
    ax.set_ylabel("direction 기여도")
    ax.legend(ncol=3)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUTPUT_FIG_MONTHLY, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_average_contribution_share(summary: pd.DataFrame) -> None:
    set_plot_font()
    active = summary[summary["is_active_in_contribution"]].copy()
    active = active.sort_values("absolute_contribution_share", ascending=True)

    fig, ax = plt.subplots(figsize=(10, 6))
    values = active["absolute_contribution_share"] * 100
    bars = ax.barh(active["signal_label"], values)

    for bar, value in zip(bars, values):
        ax.text(
            bar.get_width(),
            bar.get_y() + bar.get_height() / 2,
            f" {value:.1f}%",
            va="center",
        )

    ax.set_title("전체 기간 입력변수별 평균 절대기여 비중")
    ax.set_xlabel("비중(%)")
    ax.set_ylabel("입력신호")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUTPUT_FIG_SHARE, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_state_mean_contribution_heatmap(
    by_state: pd.DataFrame,
    summary: pd.DataFrame,
) -> None:
    set_plot_font()
    active_scores = get_active_score_cols(summary)
    state_order = [state for state in STATE_ORDER if state != "insufficient_data"]

    pivot = by_state.pivot(
        index="hsi_state",
        columns="score_variable",
        values="mean_direction_contribution",
    )
    pivot = pivot.reindex(index=state_order, columns=active_scores)

    matrix = pivot.to_numpy(dtype=float)
    finite = matrix[np.isfinite(matrix)]
    max_abs = float(np.max(np.abs(finite))) if finite.size else 1.0

    fig, ax = plt.subplots(figsize=(11, 6))
    image = ax.imshow(
        matrix,
        aspect="auto",
        vmin=-max_abs,
        vmax=max_abs,
    )

    ax.set_xticks(range(len(active_scores)))
    ax.set_xticklabels([SIGNAL_LABELS[col] for col in active_scores], rotation=25, ha="right")
    ax.set_yticks(range(len(state_order)))
    ax.set_yticklabels(state_order)
    ax.set_title("HSI 상태별 입력변수 평균 direction 기여도 (+ = 위험 악화)")

    for row_idx in range(matrix.shape[0]):
        for col_idx in range(matrix.shape[1]):
            value = matrix[row_idx, col_idx]
            text = "N/A" if not np.isfinite(value) else f"{value:+.3f}"
            ax.text(col_idx, row_idx, text, ha="center", va="center")

    fig.colorbar(image, ax=ax, label="평균 direction 기여도")
    fig.tight_layout()
    fig.savefig(OUTPUT_FIG_STATE, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_reconstruction_audit(monthly_audit: pd.DataFrame) -> None:
    set_plot_font()
    plot_df = monthly_audit.copy()
    plot_df["plot_date"] = pd.to_datetime(
        plot_df[YEAR_MONTH_COL].astype(str) + "-01",
        errors="coerce",
    )
    plot_df = plot_df.dropna(subset=["plot_date"]).sort_values("plot_date")

    metric_pairs = [
        ("risk_component", "risk_component_reconstructed", "risk_component"),
        ("relief_component", "relief_component_reconstructed", "relief_component"),
        ("state_direction", "state_direction_reconstructed", "state_direction"),
        ("state_intensity", "state_intensity_reconstructed", "state_intensity"),
    ]

    fig, ax = plt.subplots(figsize=(18, 7))
    for original, reconstructed, label in metric_pairs:
        error = plot_df[reconstructed] - plot_df[original]
        ax.plot(plot_df["plot_date"], error, linewidth=1.0, label=f"{label} 오차")

    ax.axhline(0.0, linewidth=0.8)
    ax.set_title("기존 HSI 계산값과 50번 재구성값의 월별 오차")
    ax.set_xlabel("월")
    ax.set_ylabel("재구성값 - 기존값")
    ax.legend(ncol=2)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUTPUT_FIG_AUDIT, dpi=180, bbox_inches="tight")
    plt.close(fig)


# ============================================================
# 8. 결과정리 Markdown
# ============================================================


def markdown_table(df: pd.DataFrame, columns: list[str]) -> list[str]:
    selected = df[columns].copy()
    lines = [
        "| " + " | ".join(columns) + " |",
        "|" + "|".join(["---"] * len(columns)) + "|",
    ]
    for _, row in selected.iterrows():
        values = []
        for col in columns:
            value = row[col]
            if isinstance(value, (float, np.floating)):
                values.append("" if pd.isna(value) else f"{value:.6g}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return lines


def build_note(
    summary: pd.DataFrame,
    by_state: pd.DataFrame,
    audit: pd.DataFrame,
    monthly_audit: pd.DataFrame,
) -> str:
    active = summary[summary["is_active_in_contribution"]].copy()
    inactive = summary[~summary["is_active_in_contribution"]].copy()

    all_audit_ok = bool((audit["status"] == "OK").all())
    matched_rows = int(monthly_audit["row_complete_match"].sum())
    total_rows = len(monthly_audit)

    rs_row = summary[summary["score_variable"] == "score_rs"]
    if rs_row.empty:
        rs_text = "최종 입력표에서 score_rs 항목을 확인하지 못했다."
    else:
        rs = rs_row.iloc[0]
        if int(rs["raw_valid_months"]) == 0:
            rs_text = (
                "069500의 score_rs는 전체 기간에서 유효값이 없어 내부 계산 기여도에서 제외되었다. "
                "이는 069500이 상대강도 benchmark인 자기비교 구조와 일치하는 결과로 해석할 수 있다."
            )
        else:
            rs_text = (
                f"069500의 score_rs 유효값은 {int(rs['raw_valid_months'])}개월이며, "
                f"전체 절대기여 비중은 {float(rs['absolute_contribution_share']) * 100:.2f}%였다. "
                "따라서 최종 입력표에서 실제 반영된 월 수와 값의 분포를 함께 해석해야 한다."
            )

    lines: list[str] = []
    lines.append("# 50번 HSI 입력변수별 내부 계산 기여도 결과정리")
    lines.append("")
    lines.append(f"- 생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- 기준 티커: `{MARKET_STATE_TICKER}`")
    lines.append("- 기준 시점: 월말 HSI 입력신호")
    lines.append("- 기준 상태규칙: `04_build_hsi_state5_baseline.py`와 동일")
    lines.append("")

    lines.append("## 1. 분석 목적")
    lines.append("")
    lines.append(
        "기존 최종 산출물에는 HSI 상태분포와 전략성과가 포함되어 있었지만, "
        "각 월의 상태판정 계산값이 입력신호별로 어떻게 구성되었는지를 직접 보여주는 자료는 없었다. "
        "50번 분석은 기존 상태판정식을 변경하지 않고 입력변수별 내부 계산 기여도를 분해한다."
    )
    lines.append("")

    lines.append("## 2. 문답으로 정리한 분석 범위")
    lines.append("")
    lines.append("### 질문 1. 이 기여도는 무엇을 뜻하는가?")
    lines.append("")
    lines.append(
        "미래수익률 예측에 대한 feature importance가 아니다. "
        "각 입력점수가 direction, intensity, risk_component, relief_component 계산에 "
        "얼마나 반영되었는지를 나타내는 내부 계산 기여도이다."
    )
    lines.append("")
    lines.append("### 질문 2. 왜 별도의 50번 분석을 수행했는가?")
    lines.append("")
    lines.append(
        "기존 HSI 결과가 어떤 입력신호 조합으로 형성되었는지를 설명하고, "
        "변수별 기여 합계가 기존 04번 계산과 일치하는지 검증하기 위해 수행하였다."
    )
    lines.append("")
    lines.append("### 질문 3. 이 결과로 무엇을 확인할 수 있는가?")
    lines.append("")
    lines.append(
        "월별 direction 구성, 전체 기간 평균 절대기여 비중, 상태별 평균 기여 방향, "
        "그리고 기존 HSI 계산값과 재구성값의 일치 여부를 확인할 수 있다."
    )
    lines.append("")
    lines.append("### 질문 4. 이 결과로 무엇을 주장할 수 없는가?")
    lines.append("")
    lines.append(
        "각 입력신호가 미래수익률을 독립적으로 예측했다거나, "
        "특정 신호가 전략성과의 인과적 원인이라고 주장할 수 없다."
    )
    lines.append("")

    lines.append("## 3. 분석대상 범위")
    lines.append("")
    lines.append(
        f"본 분석은 대표 위험자산 ETF인 `{MARKET_STATE_TICKER}`의 월말 입력신호를 기준으로 한다. "
        "투자대상은 ETF 3종이지만, 이 결과는 세 ETF 신호의 평균이 아니라 "
        "포트폴리오 비중조절의 기준이 되는 시장상태 신호의 내부 계산 분해이다."
    )
    lines.append("")

    lines.append("## 4. 계산식")
    lines.append("")
    lines.append("월 t의 유효 점수 수를 `n_t`, 변수 j의 점수를 `s_j,t`라고 하면:")
    lines.append("")
    lines.append("```text")
    lines.append("risk 기여(j,t)      = max(s_j,t, 0)  / (n_t × 10)")
    lines.append("relief 기여(j,t)    = max(-s_j,t, 0) / (n_t × 10)")
    lines.append("direction 기여(j,t) = s_j,t          / (n_t × 10)")
    lines.append("intensity 기여(j,t) = |s_j,t|        / (n_t × 10)")
    lines.append("")
    lines.append("risk_component_t     = Σ risk 기여(j,t)")
    lines.append("relief_component_t   = Σ relief 기여(j,t)")
    lines.append("state_direction_t    = Σ direction 기여(j,t)")
    lines.append("state_intensity_t    = Σ intensity 기여(j,t)")
    lines.append("```")
    lines.append("")

    lines.append("## 5. 입력변수별 전체 기간 기여 요약")
    lines.append("")
    summary_display = summary.copy()
    summary_display["absolute_contribution_share_pct"] = (
        summary_display["absolute_contribution_share"] * 100
    )
    lines.extend(
        markdown_table(
            summary_display,
            [
                "score_variable",
                "raw_valid_months",
                "contribution_valid_months",
                "absolute_contribution_share_pct",
                "is_active_in_contribution",
                "exclusion_reason",
            ],
        )
    )
    lines.append("")
    lines.append(rs_text)
    lines.append("")
    if not inactive.empty:
        inactive_names = ", ".join(inactive["score_variable"].tolist())
        lines.append(f"- 시각화 제외 또는 N/A 처리 신호: `{inactive_names}`")
        lines.append("")

    lines.append("## 6. 시각화")
    lines.append("")
    lines.append("### 6.1 월별 direction 내부 계산 기여도")
    lines.append("")
    lines.append("![월별 direction 기여도](../output/figures/main_final_50_fig01_monthly_direction_contribution.png)")
    lines.append("")
    lines.append("### 6.2 전체 기간 평균 절대기여 비중")
    lines.append("")
    lines.append("![평균 절대기여 비중](../output/figures/main_final_50_fig02_average_contribution_share.png)")
    lines.append("")
    lines.append("### 6.3 상태별 입력변수 평균 direction 기여도")
    lines.append("")
    lines.append("![상태별 평균 기여도](../output/figures/main_final_50_fig03_state_mean_contribution_heatmap.png)")
    lines.append("")

    lines.append("## 7. 기존 HSI 계산과의 일치 검증")
    lines.append("")
    lines.append(
        f"월별 전체 필드 일치 행은 `{matched_rows}/{total_rows}`이며, "
        f"종합 검증 상태는 `{'OK' if all_audit_ok else 'CHECK'}`이다."
    )
    lines.append("")
    lines.extend(
        markdown_table(
            audit,
            [
                "audit_item",
                "comparable_rows",
                "mismatch_rows",
                "max_abs_error",
                "status",
            ],
        )
    )
    lines.append("")
    lines.append("![재구성 오차](../output/figures/main_final_50_fig04_reconstruction_audit.png)")
    lines.append("")

    lines.append("## 8. 해석상 유의사항")
    lines.append("")
    lines.append(
        "전체 기간 평균 비중은 direction 기여도의 절댓값 합을 기준으로 계산한다. "
        "따라서 양수와 음수가 서로 상쇄되는 문제를 피하지만, "
        "미래수익률에 대한 예측력이나 인과효과를 의미하지 않는다."
    )
    lines.append("")
    lines.append(
        "상태별 평균 기여도는 해당 상태가 만들어진 뒤의 조건부 평균이다. "
        "상태 정의와 내부 계산의 정합성을 설명하는 자료로 사용하며, "
        "독립적인 성과 기여도 분석으로 해석하지 않는다."
    )
    lines.append("")

    lines.append("## 9. 결론")
    lines.append("")
    lines.append(
        "50번은 새로운 HSI 상태규칙을 추가하는 실험이 아니다. "
        "04번 baseline 상태판정 결과를 입력신호별로 분해하고, "
        "그 합계가 기존 risk/relief, direction, intensity 및 최종 상태와 일치하는지 "
        "재현·검증하는 보충 분석이다."
    )
    lines.append("")

    return "\n".join(lines)


# ============================================================
# 9. 실행
# ============================================================


def main() -> None:
    print("=" * 88)
    print("50_hsi_input_contribution.py 실행 시작")
    print("=" * 88)

    ensure_directories()

    print("[1] 입력 파일 로드")
    monthly_long = read_csv(INPUT_MONTHLY_SIGNAL_LONG, "월말 HSI signal long")
    state_table_raw = read_csv(INPUT_STATE_TABLE, "main_final HSI 상태표")
    print(f"    monthly_long shape = {monthly_long.shape}")
    print(f"    state_table shape = {state_table_raw.shape}")

    print("[2] 시장상태 기준 티커 입력표 정리")
    market = prepare_market_signal_table(monthly_long)
    state_table = prepare_state_table(state_table_raw)
    print(f"    기준 티커 = {MARKET_STATE_TICKER}")
    print(f"    market rows = {len(market)}")
    print(f"    state rows = {len(state_table)}")

    print("[3] 입력변수별 내부 계산 기여도 생성")
    monthly = build_monthly_contribution(market)

    print("[4] 기존 04번 계산값과 재구성값 검증")
    audit, monthly_audit = build_audit(monthly, state_table)

    print("[5] 요약표·상태별 표·계산식 표 생성")
    summary = build_summary(monthly_audit)
    by_state = build_by_state(monthly_audit)
    formula = build_formula_table()

    print("[6] CSV 저장")
    save_csv(monthly, OUTPUT_MONTHLY)
    save_csv(summary, OUTPUT_SUMMARY)
    save_csv(by_state, OUTPUT_BY_STATE)
    save_csv(formula, OUTPUT_FORMULA)
    save_csv(audit, OUTPUT_AUDIT)
    save_csv(monthly_audit, OUTPUT_AUDIT_MONTHLY)

    for path in [
        OUTPUT_MONTHLY,
        OUTPUT_SUMMARY,
        OUTPUT_BY_STATE,
        OUTPUT_FORMULA,
        OUTPUT_AUDIT,
        OUTPUT_AUDIT_MONTHLY,
    ]:
        print(f"    저장: {path}")

    print("[7] 시각화 저장")
    plot_monthly_direction_contribution(monthly_audit, summary)
    plot_average_contribution_share(summary)
    plot_state_mean_contribution_heatmap(by_state, summary)
    plot_reconstruction_audit(monthly_audit)

    for path in [
        OUTPUT_FIG_MONTHLY,
        OUTPUT_FIG_SHARE,
        OUTPUT_FIG_STATE,
        OUTPUT_FIG_AUDIT,
    ]:
        print(f"    저장: {path}")

    print("[8] 결과정리 Markdown 저장")
    note = build_note(summary, by_state, audit, monthly_audit)
    OUTPUT_NOTE.write_text(note, encoding="utf-8")
    print(f"    저장: {OUTPUT_NOTE}")

    print("\n[입력신호 기여 요약]")
    display_summary = summary[
        [
            "score_variable",
            "raw_valid_months",
            "contribution_valid_months",
            "absolute_contribution_share",
            "is_active_in_contribution",
            "exclusion_reason",
        ]
    ].copy()
    display_summary["absolute_contribution_share"] *= 100
    print(display_summary.to_string(index=False))

    print("\n[계산 일치 검증]")
    print(audit.to_string(index=False))

    if not (audit["status"] == "OK").all():
        failed = audit[audit["status"] != "OK"]
        print("\n[주의] 기존 04번 계산과 일치하지 않는 항목이 있습니다.")
        print(failed.to_string(index=False))
        print(
            "분모, 결측치 처리, 입력파일 버전 및 상태표 버전을 확인한 뒤 "
            "결과를 보고서에 반영하세요."
        )
    else:
        print("\n[검증 통과] 기존 04번 계산과 50번 재구성 결과가 일치합니다.")

    print("=" * 88)
    print("50_hsi_input_contribution.py 실행 완료")
    print("=" * 88)


if __name__ == "__main__":
    main()