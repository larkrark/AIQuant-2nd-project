from pathlib import Path

import numpy as np
import pandas as pd


"""
23_build_report_candidate_tables_goldfriend.py

목적
----
이미 생성된 main_final 성과표와 시계열을 읽어, 기준 발표·보고서용 후보 비교표를 별도로 생성한다.

이 파일은 새 백테스트를 실행하지 않는다.
기존 산출물을 읽어 후보 비교, 보수적 shortlist, 비용 민감도,
lambda family 표, 후보 시계열 subset을 만든다.

출력
----
output/tables/23_main_final_report_candidate_comparison_table.csv
output/tables/23_main_final_report_candidate_shortlist.csv
output/tables/23_main_final_report_candidate_cost_pivot.csv
output/tables/23_main_final_report_lambda_family_table.csv
output/tables/23_main_final_report_candidate_timeseries_subset.csv
"""


# ============================================================
# 1. 경로 설정
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"

OUTPUT_DIR = PROJECT_ROOT / "output"
TABLE_DIR = OUTPUT_DIR / "tables"

TABLE_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# 2. 입력 파일 후보
# ============================================================

PERFORMANCE_FILE_CANDIDATES = {
    "baseline": [
        TABLE_DIR / "main_final_baseline_performance_summary.csv",
    ],
    "event_filter": [
        TABLE_DIR / "main_final_event_balance_filter_performance_summary.csv",
    ],
    "signal_combo": [
        TABLE_DIR / "main_final_signal_combo_performance_summary.csv",
    ],
    "lambda": [
        TABLE_DIR / "main_final_lambda_performance_summary.csv",
        TABLE_DIR / "main_final_inertia_lambda_performance_summary.csv",
        TABLE_DIR / "main_final_lambda_experiment_performance_summary.csv",
    ],
    "theta": [
        TABLE_DIR / "main_final_theta_sensitivity_performance_summary.csv",
        TABLE_DIR / "main_final_theta_performance_summary.csv",
    ],
}

TURNOVER_FILE_CANDIDATES = {
    "baseline": [
        TABLE_DIR / "main_final_baseline_turnover_summary.csv",
    ],
    "event_filter": [
        TABLE_DIR / "main_final_event_balance_filter_turnover_summary.csv",
    ],
    "signal_combo": [
        TABLE_DIR / "main_final_signal_combo_turnover_summary.csv",
    ],
    "lambda": [
        TABLE_DIR / "main_final_lambda_turnover_summary.csv",
        TABLE_DIR / "main_final_inertia_lambda_turnover_summary.csv",
        TABLE_DIR / "main_final_lambda_experiment_turnover_summary.csv",
    ],
    "theta": [
        TABLE_DIR / "main_final_theta_sensitivity_turnover_summary.csv",
        TABLE_DIR / "main_final_theta_turnover_summary.csv",
    ],
}

TIMESERIES_FILE_CANDIDATES = {
    "baseline": [
        PROCESSED_DIR / "main_final_baseline_backtest_timeseries.csv",
    ],
    "event_filter": [
        PROCESSED_DIR / "main_final_event_balance_filter_backtest_timeseries.csv",
    ],
    "signal_combo": [
        PROCESSED_DIR / "main_final_signal_combo_backtest_timeseries.csv",
    ],
    "lambda": [
        PROCESSED_DIR / "main_final_lambda_backtest_timeseries.csv",
        PROCESSED_DIR / "main_final_inertia_lambda_backtest_timeseries.csv",
        PROCESSED_DIR / "main_final_lambda_experiment_backtest_timeseries.csv",
    ],
    "theta": [
        PROCESSED_DIR / "main_final_theta_sensitivity_backtest_timeseries.csv",
        PROCESSED_DIR / "main_final_theta_backtest_timeseries.csv",
    ],
}


# ============================================================
# 3. 출력 파일
# ============================================================

OUTPUT_COMPARISON = TABLE_DIR / "23_main_final_report_candidate_comparison_table.csv"
OUTPUT_SHORTLIST = TABLE_DIR / "23_main_final_report_candidate_shortlist.csv"
OUTPUT_COST_PIVOT = TABLE_DIR / "23_main_final_report_candidate_cost_pivot.csv"
OUTPUT_LAMBDA_FAMILY = TABLE_DIR / "23_main_final_report_lambda_family_table.csv"
OUTPUT_TS_SUBSET = TABLE_DIR / "23_main_final_report_candidate_timeseries_subset.csv"


# ============================================================
# 4. 공통 유틸
# ============================================================

def read_first_existing(paths: list[Path], source_group: str) -> pd.DataFrame:
    for path in paths:
        if path.exists():
            print(f"[LOAD] {source_group}: {path}")
            df = pd.read_csv(path, encoding="utf-8-sig")
            df["source_group"] = source_group
            df["source_file"] = path.name
            return df

    print(f"[SKIP] {source_group}: 파일 없음")
    return pd.DataFrame()


def save_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"[SAVE] {path} shape={df.shape}")


def normalize_strategy_name(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    if "strategy_name" not in out.columns:
        rename_candidates = [
            "strategy",
            "strategy_id",
            "combo_id",
            "lambda_id",
            "theta_id",
            "experiment_id",
            "candidate_id",
        ]

        for col in rename_candidates:
            if col in out.columns:
                out = out.rename(columns={col: "strategy_name"})
                break

    if "strategy_name" not in out.columns:
        raise ValueError(f"strategy_name 컬럼을 찾을 수 없습니다. columns={out.columns.tolist()}")

    out["strategy_name"] = out["strategy_name"].astype(str)
    return out


def to_numeric_if_exists(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()

    for col in cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    return out


def standardize_metric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    파일마다 컬럼명이 조금 달라도 보고서용 표에서 쓰는 이름으로 맞춘다.
    """
    out = df.copy()

    rename_map = {
        "cagr_pct": "CAGR_pct",
        "annual_volatility": "annual_volatility_pct",
        "annual_volatility_pct": "annual_volatility_pct",
        "mdd_pct": "MDD_pct",
        "MDD": "MDD_pct",
        "sharpe": "Sharpe",
        "sortino": "Sortino",
        "calmar": "Calmar",
        "winrate_pct": "WinRate_pct",
        "win_rate_pct": "WinRate_pct",
        "final_cum_return": "final_cumulative_return",
        "final_cumulative": "final_cumulative_return",
    }

    out = out.rename(columns={k: v for k, v in rename_map.items() if k in out.columns})
    return out


def infer_candidate_family(strategy_name: str, source_group: str) -> str:
    s = str(strategy_name)

    if s == "EW":
        return "benchmark"
    if s == "HSI_final_baseline_overlay":
        return "baseline"
    if "lambda" in s:
        return "lambda_partial_adjustment"
    if "event_balance_filter" in s:
        return "event_balance_filter"
    if "combo" in s:
        return "signal_combo"
    if "theta" in s:
        return "theta_sensitivity"
    if "baseline" in s:
        return "baseline"

    return source_group


def infer_presentation_role(strategy_name: str, family: str) -> str:
    s = str(strategy_name)

    if s == "EW":
        return "단순 비교 기준"
    if s == "HSI_final_baseline_overlay":
        return "즉시비중 baseline"
    if "lambda_0.1" in s:
        return "느린 부분조정 후보"
    if "lambda_0.3" in s:
        return "균형형 부분조정 후보"
    if "lambda_0.5" in s:
        return "중간 부분조정 후보"
    if "lambda_0.7" in s:
        return "빠른 부분조정 후보"
    if "lambda_1.0" in s:
        return "즉시이동 기준"
    if "event_balance_filter" in s:
        return "사건균형 보조 필터"
    if family == "signal_combo":
        return "신호 조합 진단"
    if family == "theta_sensitivity":
        return "θ 민감도 진단"

    return "검토 후보"


def extract_lambda_value(strategy_name: str) -> float:
    s = str(strategy_name)

    if s == "HSI_final_baseline_overlay":
        return 1.0

    if "lambda_" not in s:
        return np.nan

    try:
        tail = s.split("lambda_")[-1]
        number_text = tail.split("_")[0]
        return float(number_text)
    except Exception:
        return np.nan


# ============================================================
# 5. 입력 통합
# ============================================================

def load_performance_tables() -> pd.DataFrame:
    frames = []

    for source_group, paths in PERFORMANCE_FILE_CANDIDATES.items():
        df = read_first_existing(paths, source_group)

        if df.empty:
            continue

        df = standardize_metric_columns(df)
        df = normalize_strategy_name(df)
        frames.append(df)

    if not frames:
        raise FileNotFoundError("성과 요약 파일을 하나도 찾지 못했습니다.")

    perf = pd.concat(frames, ignore_index=True)

    numeric_cols = [
        "months",
        "final_cumulative_return",
        "CAGR_pct",
        "annual_volatility_pct",
        "MDD_pct",
        "Sharpe",
        "Sortino",
        "Calmar",
        "WinRate_pct",
    ]

    perf = to_numeric_if_exists(perf, numeric_cols)

    perf["candidate_family"] = perf.apply(
        lambda row: infer_candidate_family(row["strategy_name"], row["source_group"]),
        axis=1,
    )

    perf["presentation_role"] = perf.apply(
        lambda row: infer_presentation_role(row["strategy_name"], row["candidate_family"]),
        axis=1,
    )

    perf["lambda_value"] = perf["strategy_name"].apply(extract_lambda_value)

    return perf


def load_turnover_tables() -> pd.DataFrame:
    frames = []

    for source_group, paths in TURNOVER_FILE_CANDIDATES.items():
        df = read_first_existing(paths, source_group)

        if df.empty:
            continue

        df = normalize_strategy_name(df)
        frames.append(df)

    if not frames:
        print("[WARN] Turnover 파일이 없습니다.")
        return pd.DataFrame(columns=["strategy_name"])

    turnover = pd.concat(frames, ignore_index=True)

    numeric_cols = [
        "months",
        "avg_turnover_pct",
        "max_turnover_pct",
        "total_turnover_pct",
        "nonzero_turnover_months",
    ]

    turnover = to_numeric_if_exists(turnover, numeric_cols)

    return turnover


# ============================================================
# 6. 후보 비교표
# ============================================================

def build_candidate_comparison(perf: pd.DataFrame, turnover: pd.DataFrame) -> pd.DataFrame:
    if not turnover.empty:
        turnover_cols = [
            "strategy_name",
            "avg_turnover_pct",
            "max_turnover_pct",
            "total_turnover_pct",
            "nonzero_turnover_months",
        ]
        turnover_cols = [c for c in turnover_cols if c in turnover.columns]

        turnover_small = (
            turnover[turnover_cols]
            .drop_duplicates(subset=["strategy_name"], keep="last")
        )

        out = perf.merge(turnover_small, on="strategy_name", how="left")
    else:
        out = perf.copy()

    out = out.drop_duplicates(subset=["strategy_name", "candidate_family"], keep="last")

    baseline = out[out["strategy_name"].eq("HSI_final_baseline_overlay")]
    ew = out[out["strategy_name"].eq("EW")]

    if not baseline.empty:
        base = baseline.iloc[0]

        out["CAGR_vs_baseline_pct"] = out["CAGR_pct"] - base.get("CAGR_pct", np.nan)
        out["MDD_vs_baseline_pct"] = out["MDD_pct"] - base.get("MDD_pct", np.nan)
        out["vol_vs_baseline_pct"] = out["annual_volatility_pct"] - base.get("annual_volatility_pct", np.nan)
        out["turnover_vs_baseline_pct"] = out["avg_turnover_pct"] - base.get("avg_turnover_pct", np.nan)
    else:
        out["CAGR_vs_baseline_pct"] = np.nan
        out["MDD_vs_baseline_pct"] = np.nan
        out["vol_vs_baseline_pct"] = np.nan
        out["turnover_vs_baseline_pct"] = np.nan

    if not ew.empty:
        ew_row = ew.iloc[0]

        out["CAGR_vs_EW_pct"] = out["CAGR_pct"] - ew_row.get("CAGR_pct", np.nan)
        out["MDD_vs_EW_pct"] = out["MDD_pct"] - ew_row.get("MDD_pct", np.nan)
        out["Sharpe_vs_EW"] = out["Sharpe"] - ew_row.get("Sharpe", np.nan)
    else:
        out["CAGR_vs_EW_pct"] = np.nan
        out["MDD_vs_EW_pct"] = np.nan
        out["Sharpe_vs_EW"] = np.nan

    out["goldfriend_judgement"] = out.apply(make_goldfriend_judgement, axis=1)
    out["goldfriend_note"] = out.apply(make_goldfriend_note, axis=1)

    keep_cols = [
        "candidate_family",
        "presentation_role",
        "strategy_name",
        "lambda_value",
        "months",
        "final_cumulative_return",
        "CAGR_pct",
        "annual_volatility_pct",
        "MDD_pct",
        "Sharpe",
        "Sortino",
        "Calmar",
        "WinRate_pct",
        "avg_turnover_pct",
        "max_turnover_pct",
        "total_turnover_pct",
        "nonzero_turnover_months",
        "CAGR_vs_baseline_pct",
        "MDD_vs_baseline_pct",
        "vol_vs_baseline_pct",
        "turnover_vs_baseline_pct",
        "CAGR_vs_EW_pct",
        "MDD_vs_EW_pct",
        "Sharpe_vs_EW",
        "goldfriend_judgement",
        "goldfriend_note",
        "source_group",
        "source_file",
    ]

    keep_cols = [c for c in keep_cols if c in out.columns]

    family_order = {
        "benchmark": 0,
        "baseline": 1,
        "lambda_partial_adjustment": 2,
        "event_balance_filter": 3,
        "signal_combo": 4,
        "theta_sensitivity": 5,
    }

    out["_family_order"] = out["candidate_family"].map(family_order).fillna(99)
    out["_lambda_sort"] = out["lambda_value"].fillna(999)

    out = (
        out[keep_cols + ["_family_order", "_lambda_sort"]]
        .sort_values(["_family_order", "_lambda_sort", "strategy_name"])
        .drop(columns=["_family_order", "_lambda_sort"])
        .reset_index(drop=True)
    )

    return out


def make_goldfriend_judgement(row: pd.Series) -> str:
    strategy = row.get("strategy_name", "")
    family = row.get("candidate_family", "")

    cagr = row.get("CAGR_pct", np.nan)
    mdd = row.get("MDD_pct", np.nan)
    sharpe = row.get("Sharpe", np.nan)
    calmar = row.get("Calmar", np.nan)
    turnover = row.get("avg_turnover_pct", np.nan)

    if strategy == "EW":
        return "benchmark_only"

    if strategy == "HSI_final_baseline_overlay":
        return "baseline_not_final"

    if family == "lambda_partial_adjustment":
        if pd.notna(cagr) and pd.notna(mdd) and pd.notna(turnover):
            if cagr >= 8.5 and mdd >= -16.0 and turnover <= 8.0:
                return "primary_review_candidate"
            if cagr >= 8.0 and mdd >= -18.0 and turnover <= 12.0:
                return "secondary_review_candidate"
            if mdd >= -15.0 and turnover <= 4.0:
                return "defensive_review_candidate"
        return "lambda_observation"

    if family == "event_balance_filter":
        return "diagnostic_filter_candidate"

    if family == "signal_combo":
        if pd.notna(mdd) and pd.notna(sharpe):
            if mdd >= -21.0 and sharpe >= 0.65:
                return "combo_observation_candidate"
        return "combo_diagnostic_only"

    if family == "theta_sensitivity":
        return "sensitivity_diagnostic_only"

    return "review_only"


def make_goldfriend_note(row: pd.Series) -> str:
    strategy = row.get("strategy_name", "")
    judgement = row.get("goldfriend_judgement", "")

    if strategy == "EW":
        return "단순 동일가중 비교 기준이다."

    if strategy == "HSI_final_baseline_overlay":
        return "HSI 상태를 비중으로 연결하는 기준선이지만, 즉시비중 구조로 인해 MDD와 Turnover 부담이 커 최종 전략으로 단정하지 않는다."

    if "lambda_0.3" in strategy:
        return "CAGR, MDD, Turnover 균형이 비교적 좋아 우선 검토 후보로 둔다. 최적값으로 단정하지 않는다."

    if "lambda_0.1" in strategy:
        return "MDD와 Turnover 완화가 강한 느린 조정 후보이다. 수익성 둔화 여부를 함께 본다."

    if "lambda_0.5" in strategy:
        return "즉시비중과 느린 조정 사이의 중간 후보이다."

    if "lambda_0.7" in strategy:
        return "부분조정 효과는 있으나 Turnover 부담이 남아 있는 빠른 조정 후보이다."

    if "event_balance_filter" in strategy:
        return "사건균형 필터는 실제 작동했으나 개선 폭이 제한적이므로 진단·보조 후보로 해석한다."

    if judgement.startswith("combo"):
        return "신호 조합 변화에 따른 상태분포, 성과, MDD, Turnover 안정성을 보기 위한 진단 후보이다."

    return "후속 검토 대상이다."


# ============================================================
# 7. Shortlist
# ============================================================

def build_shortlist(comparison: pd.DataFrame) -> pd.DataFrame:
    keep_labels = [
        "primary_review_candidate",
        "secondary_review_candidate",
        "defensive_review_candidate",
        "diagnostic_filter_candidate",
    ]

    out = comparison[comparison["goldfriend_judgement"].isin(keep_labels)].copy()

    # 발표 핵심 후보를 안정적으로 포함
    forced_patterns = [
        "lambda_0.1",
        "lambda_0.3",
        "lambda_0.5",
        "HSI_event_balance_filter_overlay",
    ]

    forced = comparison[
        comparison["strategy_name"].apply(
            lambda s: any(pattern in str(s) for pattern in forced_patterns)
        )
    ].copy()

    out = pd.concat([out, forced], ignore_index=True)
    out = out.drop_duplicates(subset=["strategy_name"], keep="first")

    # baseline과 EW는 shortlist가 아니라 reference로 붙인다
    reference = comparison[
        comparison["strategy_name"].isin(["EW", "HSI_final_baseline_overlay"])
    ].copy()

    reference["goldfriend_judgement"] = reference["goldfriend_judgement"].replace({
        "benchmark_only": "reference",
        "baseline_not_final": "reference",
    })

    out = pd.concat([reference, out], ignore_index=True)
    out = out.drop_duplicates(subset=["strategy_name"], keep="first")

    judgement_order = {
        "reference": 0,
        "primary_review_candidate": 1,
        "secondary_review_candidate": 2,
        "defensive_review_candidate": 3,
        "diagnostic_filter_candidate": 4,
    }

    out["_order"] = out["goldfriend_judgement"].map(judgement_order).fillna(9)
    out["_lambda_sort"] = out["lambda_value"].fillna(999)

    out = (
        out.sort_values(["_order", "_lambda_sort", "strategy_name"])
        .drop(columns=["_order", "_lambda_sort"])
        .reset_index(drop=True)
    )

    out.insert(0, "shortlist_rank", range(1, len(out) + 1))

    return out


# ============================================================
# 8. 거래비용 pivot
# ============================================================

def build_cost_pivot(comparison: pd.DataFrame) -> pd.DataFrame:
    """
    보고서용 단순 거래비용 민감도.

    avg_turnover_pct는 월평균 turnover(%)로 해석한다.
    cost_bps는 turnover 금액에 대해 부과되는 비용 bps이다.

    annual_cost_drag_pct ≈ 월평균 turnover × 비용률 × 12개월
    """
    cost_bps_list = [0, 5, 10, 20, 30]

    rows = []

    target = comparison[
        comparison["candidate_family"].isin([
            "benchmark",
            "baseline",
            "lambda_partial_adjustment",
            "event_balance_filter",
        ])
    ].copy()

    for _, row in target.iterrows():
        strategy = row["strategy_name"]
        cagr = row.get("CAGR_pct", np.nan)
        turnover = row.get("avg_turnover_pct", np.nan)

        for cost_bps in cost_bps_list:
            if pd.isna(cagr) or pd.isna(turnover):
                annual_cost_drag_pct = np.nan
                cagr_after_cost = np.nan
            else:
                annual_cost_drag_pct = (turnover / 100.0) * (cost_bps / 10000.0) * 12.0 * 100.0
                cagr_after_cost = cagr - annual_cost_drag_pct

            rows.append({
                "strategy_name": strategy,
                "candidate_family": row.get("candidate_family", ""),
                "presentation_role": row.get("presentation_role", ""),
                "cost_bps": cost_bps,
                "CAGR_pct_before_cost": cagr,
                "avg_turnover_pct": turnover,
                "annual_cost_drag_pct_est": annual_cost_drag_pct,
                "CAGR_pct_after_cost_est": cagr_after_cost,
                "cost_note": "단순 비용 민감도이며 정밀 거래비용 백테스트가 아니다.",
            })

    return pd.DataFrame(rows)


# ============================================================
# 9. λ family table
# ============================================================

def build_lambda_family_table(comparison: pd.DataFrame) -> pd.DataFrame:
    out = comparison[
        comparison["candidate_family"].isin(["benchmark", "baseline", "lambda_partial_adjustment"])
    ].copy()

    out["lambda_display"] = out["lambda_value"].apply(
        lambda x: "" if pd.isna(x) else f"{x:.1f}"
    )

    out["lambda_interpretation"] = np.select(
        [
            out["strategy_name"].eq("EW"),
            out["strategy_name"].eq("HSI_final_baseline_overlay"),
            out["lambda_value"].eq(0.1),
            out["lambda_value"].eq(0.3),
            out["lambda_value"].eq(0.5),
            out["lambda_value"].eq(0.7),
            out["lambda_value"].eq(1.0),
        ],
        [
            "단순 비교 기준",
            "목표 비중 즉시 이동",
            "느린 부분조정",
            "균형형 부분조정",
            "중간 부분조정",
            "빠른 부분조정",
            "목표 비중 즉시 이동",
        ],
        default="λ 후보",
    )

    out["_sort"] = out["lambda_value"].fillna(-1)
    out = out.sort_values("_sort").drop(columns="_sort")

    keep_cols = [
        "lambda_value",
        "lambda_display",
        "lambda_interpretation",
        "strategy_name",
        "CAGR_pct",
        "MDD_pct",
        "annual_volatility_pct",
        "Sharpe",
        "Sortino",
        "Calmar",
        "avg_turnover_pct",
        "max_turnover_pct",
        "goldfriend_judgement",
        "goldfriend_note",
    ]

    keep_cols = [c for c in keep_cols if c in out.columns]

    return out[keep_cols].reset_index(drop=True)


# ============================================================
# 10. 시계열 subset
# ============================================================

def load_timeseries_tables() -> pd.DataFrame:
    frames = []

    for source_group, paths in TIMESERIES_FILE_CANDIDATES.items():
        df = read_first_existing(paths, source_group)

        if df.empty:
            continue

        df = normalize_strategy_name(df)
        frames.append(df)

    if not frames:
        print("[WARN] 시계열 파일이 없습니다.")
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)


def build_timeseries_subset(ts: pd.DataFrame, shortlist: pd.DataFrame) -> pd.DataFrame:
    if ts.empty or shortlist.empty:
        return pd.DataFrame()

    keep_strategies = set(shortlist["strategy_name"].astype(str))

    # 그래프 비교 기준은 항상 포함
    keep_strategies.update([
        "EW",
        "HSI_final_baseline_overlay",
    ])

    out = ts[ts["strategy_name"].astype(str).isin(keep_strategies)].copy()

    keep_cols = [
        "strategy_name",
        "year_month",
        "return_year_month",
        "hsi_state",
        "state_kr",
        "allocation_rule_name",
        "strategy_return",
        "turnover",
        "cumulative_return",
        "running_max",
        "drawdown",
    ]

    for col in out.columns:
        if col.startswith("weight_"):
            keep_cols.append(col)

    for col in out.columns:
        if col.startswith("return_"):
            keep_cols.append(col)

    keep_cols = list(dict.fromkeys([c for c in keep_cols if c in out.columns]))

    out = out[keep_cols].drop_duplicates()

    if "year_month" in out.columns:
        out = out.sort_values(["strategy_name", "year_month"]).reset_index(drop=True)

    return out


# ============================================================
# 11. main
# ============================================================

def main() -> None:
    print("=" * 80)
    print("23_build_report_candidate_tables_goldfriend.py 실행 시작")
    print("=" * 80)

    print("[1] 성과표 로드")
    perf = load_performance_tables()

    print("[2] Turnover 표 로드")
    turnover = load_turnover_tables()

    print("[3] 후보 비교표 생성")
    comparison = build_candidate_comparison(perf, turnover)
    save_csv(comparison, OUTPUT_COMPARISON)

    print("[4] shortlist 생성")
    shortlist = build_shortlist(comparison)
    save_csv(shortlist, OUTPUT_SHORTLIST)

    print("[5] 거래비용 민감도 표 생성")
    cost_pivot = build_cost_pivot(comparison)
    save_csv(cost_pivot, OUTPUT_COST_PIVOT)

    print("[6] lambda family 표 생성")
    lambda_family = build_lambda_family_table(comparison)
    save_csv(lambda_family, OUTPUT_LAMBDA_FAMILY)

    print("[7] 후보 시계열 subset 생성")
    ts = load_timeseries_tables()
    ts_subset = build_timeseries_subset(ts, shortlist)
    save_csv(ts_subset, OUTPUT_TS_SUBSET)

    print("\n[생성 완료 파일]")
    for path in [
        OUTPUT_COMPARISON,
        OUTPUT_SHORTLIST,
        OUTPUT_COST_PIVOT,
        OUTPUT_LAMBDA_FAMILY,
        OUTPUT_TS_SUBSET,
    ]:
        print(f"    {path}")

    print("=" * 80)
    print("23_build_report_candidate_tables_goldfriend.py 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()