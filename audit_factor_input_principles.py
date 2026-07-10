# -*- coding: utf-8 -*-
"""
audit_factor_input_principles.py

E24 factor loading 입력을 만들기 전에,
현재 CSV들이 우리 실험 원칙에 부합하는지 점검한다.

이 스크립트는 원본 파일을 수정하지 않는다.
감사 결과와 preview만 output/tables에 저장한다.
"""

from pathlib import Path
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
PROCESSED = ROOT / "data" / "processed"
OUT = ROOT / "output" / "tables"
OUT.mkdir(parents=True, exist_ok=True)

RET_DEC = PROCESSED / "main_final_monthly_return_decimal.csv"
RET_PCT = PROCESSED / "main_final_monthly_return_pct.csv"
ALIGN = PROCESSED / "main_final_monthly_signal_return_alignment_preview.csv"
MACRO = PROCESSED / "main_final_macro_companion_features_monthly.csv"
HSI_MACRO_JOINED = PROCESSED / "main_final_hsi_macro_companion_joined_monthly.csv"

AUDIT_FILE = OUT / "factor_input_principle_audit.csv"
PREVIEW_FILE = OUT / "factor_inputs_monthly_preview_audit.csv"

TICKERS = ["069500", "114260", "153130"]


def audit_row(item, status, detail):
    return {"item": item, "status": status, "detail": detail}


def to_month_end(s):
    raw = s.astype(str).str.strip()

    parsed = pd.to_datetime(raw, format="%Y-%m", errors="coerce")

    mask = parsed.isna()
    if mask.any():
        parsed.loc[mask] = pd.to_datetime(raw.loc[mask], format="%Y-%m-%d", errors="coerce")

    mask = parsed.isna()
    if mask.any():
        parsed.loc[mask] = pd.to_datetime(raw.loc[mask], format="%b-%y", errors="coerce")

    mask = parsed.isna()
    if mask.any():
        parsed.loc[mask] = pd.to_datetime(raw.loc[mask], errors="coerce")

    if parsed.isna().any():
        bad = raw.loc[parsed.isna()].head(10).tolist()
        raise ValueError(f"날짜 변환 실패 예시: {bad}")

    return parsed.dt.to_period("M").dt.to_timestamp("M")


def load_return_file(path):
    df = pd.read_csv(path, encoding="utf-8-sig")
    df = df.rename(columns={df.columns[0]: "Date", "69500": "069500"})
    df["Date"] = to_month_end(df["Date"])

    for col in TICKERS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df.sort_values("Date")


def main():
    rows = []

    # 1. 파일 존재 확인
    files = {
        "decimal_return": RET_DEC,
        "pct_return_check": RET_PCT,
        "alignment_check": ALIGN,
        "macro_features": MACRO,
    }

    for name, path in files.items():
        rows.append(
            audit_row(
                f"파일 존재: {name}",
                "PASS" if path.exists() else "FAIL",
                str(path),
            )
        )

    if not RET_DEC.exists():
        raise FileNotFoundError(f"decimal 수익률 파일 없음: {RET_DEC}")
    if not MACRO.exists():
        raise FileNotFoundError(f"macro companion features 파일 없음: {MACRO}")
    if not ALIGN.exists():
        raise FileNotFoundError(f"alignment preview 파일 없음: {ALIGN}")

    # 2. decimal 수익률 확인
    ret_dec = load_return_file(RET_DEC)

    missing = [c for c in ["Date"] + TICKERS if c not in ret_dec.columns]
    rows.append(
        audit_row(
            "decimal 수익률 필요 열",
            "PASS" if not missing else "FAIL",
            f"missing={missing}",
        )
    )

    max_abs_return = ret_dec[TICKERS].abs().max().max()
    rows.append(
        audit_row(
            "수익률 단위 decimal 확인",
            "PASS" if max_abs_return < 1 else "FAIL",
            f"max_abs_return={max_abs_return:.8f}",
        )
    )

    # 3. pct / decimal 관계 확인
    if RET_PCT.exists():
        ret_pct = load_return_file(RET_PCT)

        merged = ret_dec[["Date"] + TICKERS].merge(
            ret_pct[["Date"] + TICKERS],
            on="Date",
            suffixes=("_dec", "_pct"),
            how="inner",
        )

        max_diffs = []
        for t in TICKERS:
            diff = (merged[f"{t}_pct"] / 100.0 - merged[f"{t}_dec"]).abs().max()
            max_diffs.append(diff)

        max_diff = max(max_diffs)
        rows.append(
            audit_row(
                "pct/decimal 관계 확인",
                "PASS" if max_diff < 1e-6 else "WARN",
                f"max_abs((pct/100)-decimal)={max_diff:.12f}",
            )
        )
    else:
        rows.append(
            audit_row(
                "pct/decimal 관계 확인",
                "WARN",
                "pct 파일이 없어 단위 검산 생략",
            )
        )

    # 4. t월 신호 → t+1월 수익률 정렬 확인
    align = pd.read_csv(ALIGN, encoding="utf-8-sig")
    if "alignment_rule" in align.columns:
        rules = sorted(align["alignment_rule"].dropna().astype(str).unique().tolist())
        rule_ok = rules == ["signal_month_t_to_return_month_t_plus_1"]
    else:
        rules = ["NO_ALIGNMENT_RULE_COLUMN"]
        rule_ok = False

    rows.append(
        audit_row(
            "t월 신호 → t+1월 수익률 규칙",
            "PASS" if rule_ok else "FAIL",
            f"rules={rules}",
        )
    )

    # 5. macro companion features 확인
    macro = pd.read_csv(MACRO, encoding="utf-8-sig")

    required_macro_cols = [
        "year_month",
        "rate_up_flag",
        "fx_up_flag",
        "macro_data_available",
    ]
    missing_macro = [c for c in required_macro_cols if c not in macro.columns]

    rows.append(
        audit_row(
            "MacroRisk 구성용 최소 열",
            "PASS" if not missing_macro else "FAIL",
            f"missing={missing_macro}",
        )
    )

    macro["Date"] = to_month_end(macro["year_month"])

    for col in ["rate_up_flag", "fx_up_flag", "macro_data_available"]:
        if col in macro.columns:
            macro[col] = pd.to_numeric(macro[col], errors="coerce")

    flag_ok = True
    flag_detail = []
    for col in ["rate_up_flag", "fx_up_flag"]:
        vals = sorted(macro[col].dropna().unique().tolist())
        if not set(vals).issubset({0, 1, 0.0, 1.0}):
            flag_ok = False
        flag_detail.append(f"{col}={vals}")

    rows.append(
        audit_row(
            "macro flag 0/1 여부",
            "PASS" if flag_ok else "FAIL",
            "; ".join(flag_detail),
        )
    )

    # 6. MacroRisk 단순 합산
    available = macro["macro_data_available"].fillna(0).astype(int) == 1
    macro["MacroRisk"] = np.where(
        available,
        macro["rate_up_flag"].fillna(0).astype(int)
        + macro["fx_up_flag"].fillna(0).astype(int),
        np.nan,
    )

    macro_vals = sorted(macro["MacroRisk"].dropna().unique().tolist())
    macro_ok = set(macro_vals).issubset({0, 1, 2, 0.0, 1.0, 2.0})

    rows.append(
        audit_row(
            "MacroRisk 0/1/2 단순 점수",
            "PASS" if macro_ok else "FAIL",
            f"MacroRisk unique={macro_vals}",
        )
    )

    # 7. GDP 제외 원칙 확인
    gdp_cols = [c for c in macro.columns if "gdp" in c.lower()]
    rows.append(
        audit_row(
            "GDP 변수 1차 E24 제외",
            "PASS",
            f"파일 내 GDP 관련 열은 있으나 preview factor에는 사용하지 않음: {gdp_cols}",
        )
    )

    # 8. factor preview 생성
    factors = pd.DataFrame()
    factors["Date"] = ret_dec["Date"]
    factors["Market"] = ret_dec["069500"]
    factors["Bond"] = ret_dec["114260"]

    factors["Momentum"] = (
        (1.0 + ret_dec["069500"]).rolling(3).apply(np.prod, raw=True) - 1.0
    )

    factors["Volatility"] = ret_dec["069500"].rolling(12).std() * np.sqrt(12)

    factors = factors.merge(
        macro[["Date", "MacroRisk"]],
        on="Date",
        how="left",
    )

    before = len(factors)
    factors_clean = factors.dropna(
        subset=["Market", "Bond", "Momentum", "Volatility", "MacroRisk"]
    ).copy()
    after = len(factors_clean)

    vol_min = factors_clean["Volatility"].min()
    vol_max = factors_clean["Volatility"].max()

    rows.append(
        audit_row(
            "Annualized Volatility 생성",
            "PASS" if after >= 36 and vol_max < 1 else "WARN",
            f"range={vol_min:.8f}~{vol_max:.8f}, formula=rolling_std_12m*sqrt(12)",
        )
    )

    rows.append(
        audit_row(
            "factor preview 유효 표본",
            "PASS" if after >= 36 else "FAIL",
            f"before_dropna={before}, after_dropna={after}, period={factors_clean['Date'].min()}~{factors_clean['Date'].max()}",
        )
    )

    # 9. HSI-macro joined 파일은 해석용
    if HSI_MACRO_JOINED.exists():
        joined = pd.read_csv(HSI_MACRO_JOINED, encoding="utf-8-sig")
        useful = [
            c for c in [
                "hsi_state",
                "macro_risk_flag",
                "hsi_macro_overlap_type",
                "hsi_macro_risk_agreement_flag",
                "hsi_macro_disagreement_flag",
            ]
            if c in joined.columns
        ]
        rows.append(
            audit_row(
                "HSI-macro joined 파일 용도",
                "PASS",
                f"factor input이 아니라 해석·보고서용: {useful}",
            )
        )
    else:
        rows.append(
            audit_row(
                "HSI-macro joined 파일 용도",
                "WARN",
                "파일 없음. E24에는 필수 아님.",
            )
        )

    audit = pd.DataFrame(rows)
    audit.to_csv(AUDIT_FILE, index=False, encoding="utf-8-sig")

    factors_clean.to_csv(PREVIEW_FILE, index=False, encoding="utf-8-sig")

    print("\n[팩터 입력 원칙 감사 결과]")
    print(audit.to_string(index=False))

    print("\n[팩터 preview 앞부분]")
    print(factors_clean.head().to_string(index=False))

    print("\n[팩터 preview 뒷부분]")
    print(factors_clean.tail().to_string(index=False))

    print("\n[저장 파일]")
    print(f"- {AUDIT_FILE}")
    print(f"- {PREVIEW_FILE}")

    fail_count = int((audit["status"] == "FAIL").sum())
    warn_count = int((audit["status"] == "WARN").sum())

    print("\n[요약]")
    print(f"FAIL={fail_count}, WARN={warn_count}")

    if fail_count > 0:
        raise SystemExit("FAIL 항목이 있습니다. factor_inputs_monthly.csv 생성 전에 수정이 필요합니다.")

    print("원칙 감사 통과: factor_inputs_monthly.csv 생성 단계로 진행 가능합니다.")


if __name__ == "__main__":
    main()