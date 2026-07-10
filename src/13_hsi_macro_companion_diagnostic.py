from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd


"""
13_hsi_macro_companion_diagnostic.py

목적
----
12번에서 만든 금리·환율·GDP 기반 macro companion layer를
main_final HSI 5상태표와 결합하여 진단한다.

핵심 질문
---------
1. HSI가 risk_warning / accident_zone으로 판단한 달에
   macro companion도 위험형 보조 신호를 냈는가?

2. HSI는 위험이 아니었지만 macro companion이 위험을 본 달은 있었는가?

3. 매크로 자료가 없는 구간은 몇 개월이며,
   이 구간을 분석에서 어떻게 제외해야 하는가?

주의
----
이 파일은 baseline 전략 비중을 바꾸지 않는다.
즉, 진단용 companion analysis이며,
후속 overlay 실험은 별도 파일에서 수행한다.
"""


# ============================================================
# 0. 경로 설정
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
TABLE_DIR = PROJECT_ROOT / "output" / "tables"
DOCS_DIR = PROJECT_ROOT / "docs"

for d in [PROCESSED_DIR, TABLE_DIR, DOCS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


INPUT_HSI_STATE = PROCESSED_DIR / "main_final_hsi_state5_table.csv"
INPUT_MACRO = PROCESSED_DIR / "main_final_macro_companion_features_monthly.csv"

OUTPUT_JOINED = PROCESSED_DIR / "main_final_hsi_macro_companion_joined_monthly.csv"

OUTPUT_QUALITY = TABLE_DIR / "main_final_hsi_macro_companion_quality_check.csv"
OUTPUT_OVERLAP_SUMMARY = TABLE_DIR / "main_final_hsi_macro_overlap_summary.csv"
OUTPUT_OVERLAP_BY_STATE = TABLE_DIR / "main_final_hsi_macro_overlap_by_state.csv"
OUTPUT_RISK_MONTHS = TABLE_DIR / "main_final_hsi_macro_risk_months.csv"
OUTPUT_RECENT_MONTHS = TABLE_DIR / "main_final_hsi_macro_recent_months.csv"

OUTPUT_NOTE = DOCS_DIR / "main_final_hsi_macro_companion_diagnostic_note.md"


# ============================================================
# 1. 설정값
# ============================================================

RISK_TICKER = "069500"

HSI_RISK_STATES = ["risk_warning", "accident_zone"]
HSI_RELIEF_STATES = ["risk_relief"]

MACRO_RISK_REGIMES = [
    "rate_fx_risk_departure",
    "policy_growth_pressure",
    "risk_departure_plus_growth_pressure",
]

MACRO_RELIEF_REGIMES = [
    "rate_fx_relief_departure",
]


# ============================================================
# 2. 유틸 함수
# ============================================================

def require_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"필수 입력 파일을 찾을 수 없습니다: {path}")


def read_csv(path: Path) -> pd.DataFrame:
    require_file(path)
    return pd.read_csv(path, encoding="utf-8-sig")


def to_bool_series(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s

    return (
        s.astype(str)
        .str.lower()
        .str.strip()
        .map({
            "true": True,
            "1": True,
            "yes": True,
            "y": True,
            "false": False,
            "0": False,
            "no": False,
            "n": False,
        })
        .fillna(False)
        .astype(bool)
    )


def safe_numeric(s: pd.Series, default: float = 0.0) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").fillna(default)


# ============================================================
# 3. 입력 로드
# ============================================================

def load_hsi_state_table() -> pd.DataFrame:
    hsi = read_csv(INPUT_HSI_STATE)
    hsi = hsi.copy()

    if "year_month" not in hsi.columns:
        raise KeyError("HSI 상태표에 year_month 컬럼이 없습니다.")

    if "hsi_state" not in hsi.columns:
        raise KeyError("HSI 상태표에 hsi_state 컬럼이 없습니다.")

    hsi["year_month"] = hsi["year_month"].astype(str)

    # ticker 컬럼이 있고 069500이 있으면 위험자산 기준 상태만 사용
    if "ticker" in hsi.columns:
        hsi["ticker"] = hsi["ticker"].astype(str).str.zfill(6)
        if RISK_TICKER in set(hsi["ticker"]):
            hsi = hsi[hsi["ticker"] == RISK_TICKER].copy()

    if "state_valid" in hsi.columns:
        hsi["state_valid"] = to_bool_series(hsi["state_valid"])
    else:
        hsi["state_valid"] = True

    # 같은 월이 중복되면 state_valid=True를 우선하고 마지막 행을 사용
    hsi = hsi.sort_values(["year_month", "state_valid"])
    hsi = hsi.drop_duplicates(subset=["year_month"], keep="last").copy()

    keep_cols = [
        "year_month",
        "ticker",
        "hsi_state",
        "state_kr",
        "hsi_direction",
        "hsi_intensity",
        "state_valid",
        "score_return",
        "score_volatility",
        "score_drawdown",
        "score_bond",
        "score_cash",
    ]

    keep_cols = [c for c in keep_cols if c in hsi.columns]

    return hsi[keep_cols].sort_values("year_month").reset_index(drop=True)


def load_macro_features() -> pd.DataFrame:
    macro = read_csv(INPUT_MACRO)
    macro = macro.copy()

    if "year_month" not in macro.columns:
        raise KeyError("macro companion 파일에 year_month 컬럼이 없습니다.")

    macro["year_month"] = macro["year_month"].astype(str)

    if "macro_data_available" not in macro.columns:
        required = ["rate_level", "usdkrw", "rate_fx_departure"]
        if all(c in macro.columns for c in required):
            macro["macro_data_available"] = macro[required].notna().all(axis=1).astype(int)
        else:
            macro["macro_data_available"] = 0

    if "gdp_data_available" not in macro.columns:
        if "gdp_growth_decimal_lagged" in macro.columns:
            macro["gdp_data_available"] = macro["gdp_growth_decimal_lagged"].notna().astype(int)
        else:
            macro["gdp_data_available"] = 0

    if "macro_companion_regime_filled" not in macro.columns:
        if "macro_companion_regime" in macro.columns:
            macro["macro_companion_regime_filled"] = macro["macro_companion_regime"]
        else:
            macro["macro_companion_regime_filled"] = np.nan

        macro.loc[
            macro["macro_data_available"] == 0,
            "macro_companion_regime_filled",
        ] = "macro_data_unavailable"

    return macro.sort_values("year_month").reset_index(drop=True)


# ============================================================
# 4. 결합 및 진단 플래그
# ============================================================

def build_joined_diagnostic(hsi: pd.DataFrame, macro: pd.DataFrame) -> pd.DataFrame:
    joined = pd.merge(
        hsi,
        macro,
        on="year_month",
        how="left",
        suffixes=("_hsi", "_macro"),
    )

    joined["macro_data_available"] = safe_numeric(
        joined.get("macro_data_available", pd.Series(index=joined.index)),
        default=0,
    ).astype(int)

    joined["gdp_data_available"] = safe_numeric(
        joined.get("gdp_data_available", pd.Series(index=joined.index)),
        default=0,
    ).astype(int)

    joined["macro_defense_addon"] = safe_numeric(
        joined.get("macro_defense_addon", pd.Series(index=joined.index)),
        default=0.0,
    )

    joined["hsi_risk_flag"] = (
        joined["hsi_state"].isin(HSI_RISK_STATES)
        & joined["state_valid"].astype(bool)
    ).astype(int)

    joined["hsi_relief_flag"] = (
        joined["hsi_state"].isin(HSI_RELIEF_STATES)
        & joined["state_valid"].astype(bool)
    ).astype(int)

    regime = joined.get(
        "macro_companion_regime_filled",
        pd.Series(np.nan, index=joined.index),
    ).astype(str)

    joined["macro_risk_flag"] = (
        (joined["macro_data_available"] == 1)
        & (
            regime.isin(MACRO_RISK_REGIMES)
            | (joined["macro_defense_addon"] > 0)
        )
    ).astype(int)

    joined["macro_relief_flag"] = (
        (joined["macro_data_available"] == 1)
        & regime.isin(MACRO_RELIEF_REGIMES)
    ).astype(int)

    conditions = [
        joined["macro_data_available"] == 0,
        joined["state_valid"].astype(bool) == False,
        (joined["hsi_risk_flag"] == 1) & (joined["macro_risk_flag"] == 1),
        (joined["hsi_risk_flag"] == 1) & (joined["macro_risk_flag"] == 0),
        (joined["hsi_risk_flag"] == 0) & (joined["macro_risk_flag"] == 1),
        (joined["hsi_relief_flag"] == 1) & (joined["macro_relief_flag"] == 1),
    ]

    choices = [
        "macro_data_unavailable",
        "hsi_state_invalid",
        "both_hsi_and_macro_risk",
        "hsi_risk_only",
        "macro_risk_only",
        "both_relief",
    ]

    joined["hsi_macro_overlap_type"] = np.select(
        conditions,
        choices,
        default="no_risk_overlap",
    )

    joined["hsi_macro_risk_agreement_flag"] = (
        joined["hsi_macro_overlap_type"] == "both_hsi_and_macro_risk"
    ).astype(int)

    joined["hsi_macro_disagreement_flag"] = (
        joined["hsi_macro_overlap_type"].isin(["hsi_risk_only", "macro_risk_only"])
    ).astype(int)

    return joined.sort_values("year_month").reset_index(drop=True)


# ============================================================
# 5. 요약표
# ============================================================

def make_quality_check(
    hsi: pd.DataFrame,
    macro: pd.DataFrame,
    joined: pd.DataFrame,
) -> pd.DataFrame:
    rows = []

    rows.append({
        "check_item": "hsi_rows",
        "result": len(hsi),
        "status": "OK" if len(hsi) > 0 else "CHECK",
        "note": "HSI 상태표 월 수",
    })

    rows.append({
        "check_item": "macro_rows",
        "result": len(macro),
        "status": "OK" if len(macro) > 0 else "CHECK",
        "note": "macro companion feature 월 수",
    })

    rows.append({
        "check_item": "joined_rows",
        "result": len(joined),
        "status": "OK" if len(joined) == len(hsi) else "CHECK",
        "note": "HSI 월 기준으로 macro를 붙인 결과 row 수",
    })

    if len(joined) > 0:
        rows.append({
            "check_item": "date_range",
            "result": f"{joined['year_month'].min()} ~ {joined['year_month'].max()}",
            "status": "OK",
            "note": "진단 대상 기간",
        })

    macro_available = int(joined["macro_data_available"].sum())
    gdp_available = int(joined["gdp_data_available"].sum())

    rows.append({
        "check_item": "macro_data_available_months",
        "result": macro_available,
        "status": "OK" if macro_available > 0 else "CHECK",
        "note": "금리·환율 기반 macro companion 계산 가능 월 수",
    })

    rows.append({
        "check_item": "gdp_data_available_months",
        "result": gdp_available,
        "status": "OK" if gdp_available > 0 else "CHECK",
        "note": "GDP lagged 성장률 사용 가능 월 수",
    })

    hsi_risk_months = int(joined["hsi_risk_flag"].sum())
    macro_risk_months = int(joined["macro_risk_flag"].sum())
    both_risk_months = int(joined["hsi_macro_risk_agreement_flag"].sum())

    rows.append({
        "check_item": "hsi_risk_months",
        "result": hsi_risk_months,
        "status": "OK",
        "note": "HSI가 risk_warning 또는 accident_zone인 월 수",
    })

    rows.append({
        "check_item": "macro_risk_months",
        "result": macro_risk_months,
        "status": "OK",
        "note": "macro companion이 위험형 보조 신호를 낸 월 수",
    })

    rows.append({
        "check_item": "both_hsi_and_macro_risk_months",
        "result": both_risk_months,
        "status": "OK",
        "note": "HSI 위험과 macro 위험이 동시에 나타난 월 수",
    })

    if hsi_risk_months > 0:
        agreement_ratio = both_risk_months / hsi_risk_months
        rows.append({
            "check_item": "macro_support_ratio_within_hsi_risk",
            "result": f"{agreement_ratio:.4f}",
            "status": "OK",
            "note": "HSI 위험 월 중 macro 위험도 함께 나타난 비율",
        })

    return pd.DataFrame(rows)


def make_overlap_summary(joined: pd.DataFrame) -> pd.DataFrame:
    counts = (
        joined["hsi_macro_overlap_type"]
        .value_counts(dropna=False)
        .rename_axis("hsi_macro_overlap_type")
        .reset_index(name="count")
    )

    counts["ratio_all_months"] = counts["count"] / len(joined)

    available_count = int((joined["macro_data_available"] == 1).sum())

    counts["ratio_macro_available_months"] = np.where(
        available_count > 0,
        counts["count"] / available_count,
        np.nan,
    )

    return counts


def make_overlap_by_state(joined: pd.DataFrame) -> pd.DataFrame:
    if "macro_companion_regime_filled" not in joined.columns:
        joined["macro_companion_regime_filled"] = "unknown"

    table = pd.crosstab(
        joined["hsi_state"],
        joined["macro_companion_regime_filled"],
        dropna=False,
    )

    table = table.reset_index()

    return table


def make_risk_months(joined: pd.DataFrame) -> pd.DataFrame:
    mask = (
        (joined["hsi_risk_flag"] == 1)
        | (joined["macro_risk_flag"] == 1)
        | (joined["hsi_macro_overlap_type"] == "both_relief")
    )

    cols = [
        "year_month",
        "hsi_state",
        "state_kr",
        "hsi_direction",
        "hsi_intensity",
        "state_valid",
        "macro_data_available",
        "gdp_data_available",
        "rate_level",
        "rate_change_1m",
        "usdkrw",
        "usdkrw_return_1m",
        "gdp_growth_pct_lagged",
        "gdp_growth_band",
        "rate_fx_departure",
        "rate_fx_risk_departure_flag",
        "rate_fx_relief_departure_flag",
        "policy_growth_pressure_flag",
        "macro_defense_addon",
        "macro_companion_regime_filled",
        "hsi_risk_flag",
        "macro_risk_flag",
        "hsi_macro_overlap_type",
    ]

    cols = [c for c in cols if c in joined.columns]

    return joined.loc[mask, cols].copy()


def make_recent_months(joined: pd.DataFrame, n: int = 24) -> pd.DataFrame:
    cols = [
        "year_month",
        "hsi_state",
        "state_kr",
        "macro_data_available",
        "gdp_data_available",
        "macro_companion_regime_filled",
        "hsi_risk_flag",
        "macro_risk_flag",
        "hsi_macro_overlap_type",
        "macro_defense_addon",
        "rate_level",
        "usdkrw",
        "gdp_growth_pct_lagged",
    ]

    cols = [c for c in cols if c in joined.columns]

    return joined[cols].tail(n).copy()


# ============================================================
# 6. 노트
# ============================================================

def make_note(
    quality: pd.DataFrame,
    overlap_summary: pd.DataFrame,
) -> str:
    lines = []

    lines.append("# main_final HSI + macro companion diagnostic note")
    lines.append("")
    lines.append(f"- 생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## 1. 목적")
    lines.append("")
    lines.append(
        "본 진단은 main_final HSI 5상태표와 금리·환율·GDP 기반 macro companion layer를 결합하여, "
        "가격 기반 HSI 위험상태가 매크로 보조 위험 신호와 같은 시점에 나타나는지 확인하기 위한 것이다."
    )
    lines.append("")
    lines.append("## 2. 해석 기준")
    lines.append("")
    lines.append("- `both_hsi_and_macro_risk`: HSI 위험상태와 macro 위험 보조신호가 동시에 나타난 월")
    lines.append("- `hsi_risk_only`: HSI는 위험상태이나 macro 보조신호는 위험을 보지 않은 월")
    lines.append("- `macro_risk_only`: HSI는 위험상태가 아니지만 macro 보조신호가 위험을 본 월")
    lines.append("- `both_relief`: HSI 완화상태와 macro 완화형 이탈이 동시에 나타난 월")
    lines.append("- `macro_data_unavailable`: 금리·환율 macro 자료가 없어 companion layer 판정에서 제외되는 월")
    lines.append("")
    lines.append("## 3. 품질 점검 요약")
    lines.append("")
    lines.append("| check_item | result | status | note |")
    lines.append("|---|---:|---|---|")

    for _, row in quality.iterrows():
        lines.append(
            f"| {row['check_item']} | {row['result']} | {row['status']} | {row['note']} |"
        )

    lines.append("")
    lines.append("## 4. 겹침 유형 요약")
    lines.append("")
    lines.append("| hsi_macro_overlap_type | count | ratio_all_months | ratio_macro_available_months |")
    lines.append("|---|---:|---:|---:|")

    for _, row in overlap_summary.iterrows():
        lines.append(
            f"| {row['hsi_macro_overlap_type']} | {row['count']} | "
            f"{row['ratio_all_months']:.4f} | "
            f"{row['ratio_macro_available_months']:.4f} |"
        )

    lines.append("")
    lines.append("## 5. 주의")
    lines.append("")
    lines.append(
        "본 파일은 전략 비중을 직접 바꾸는 overlay가 아니라 진단용 결합표이다. "
        "macro companion 신호는 HSI baseline을 보조적으로 해석하기 위한 장치이며, "
        "성과 비교를 위해 비중을 변경하는 실험은 별도 파일에서 수행한다."
    )
    lines.append("")

    return "\n".join(lines)


# ============================================================
# 7. 실행
# ============================================================

def main() -> None:
    print("=" * 80)
    print("13_hsi_macro_companion_diagnostic.py 실행 시작")
    print("=" * 80)

    print("[1] 입력 파일 확인")
    for path in [INPUT_HSI_STATE, INPUT_MACRO]:
        require_file(path)
        print(f"    OK: {path}")

    print("[2] 입력 데이터 로드")
    hsi = load_hsi_state_table()
    macro = load_macro_features()

    print(f"    hsi shape = {hsi.shape}")
    print(f"    macro shape = {macro.shape}")

    print("[3] HSI + macro 결합")
    joined = build_joined_diagnostic(hsi, macro)
    print(f"    joined shape = {joined.shape}")

    print("[4] 요약표 생성")
    quality = make_quality_check(hsi, macro, joined)
    overlap_summary = make_overlap_summary(joined)
    overlap_by_state = make_overlap_by_state(joined)
    risk_months = make_risk_months(joined)
    recent_months = make_recent_months(joined, n=24)

    print("[5] 저장")
    joined.to_csv(OUTPUT_JOINED, index=False, encoding="utf-8-sig")
    quality.to_csv(OUTPUT_QUALITY, index=False, encoding="utf-8-sig")
    overlap_summary.to_csv(OUTPUT_OVERLAP_SUMMARY, index=False, encoding="utf-8-sig")
    overlap_by_state.to_csv(OUTPUT_OVERLAP_BY_STATE, index=False, encoding="utf-8-sig")
    risk_months.to_csv(OUTPUT_RISK_MONTHS, index=False, encoding="utf-8-sig")
    recent_months.to_csv(OUTPUT_RECENT_MONTHS, index=False, encoding="utf-8-sig")

    note = make_note(
        quality=quality,
        overlap_summary=overlap_summary,
    )
    OUTPUT_NOTE.write_text(note, encoding="utf-8")

    print("\n[저장 완료]")
    for path in [
        OUTPUT_JOINED,
        OUTPUT_QUALITY,
        OUTPUT_OVERLAP_SUMMARY,
        OUTPUT_OVERLAP_BY_STATE,
        OUTPUT_RISK_MONTHS,
        OUTPUT_RECENT_MONTHS,
        OUTPUT_NOTE,
    ]:
        print(f"- {path}")

    print("\n[품질 점검]")
    print(quality.to_string(index=False))

    print("\n[겹침 유형 요약]")
    print(overlap_summary.to_string(index=False))

    print("\n[최근 24개월]")
    print(recent_months.to_string(index=False))

    print("\n" + "=" * 80)
    print("13_hsi_macro_companion_diagnostic.py 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()