# -*- coding: utf-8 -*-
"""
audit_price_to_return_consistency.py

목적:
1. data/processed/main_final_monthly_price.csv를 기준 가격 파일로 사용
2. 월별 수익률을 직접 재계산
3. data/processed/main_final_monthly_return_decimal.csv와 비교
4. 차이가 있으면 어느 월/티커에서 발생했는지 출력
5. 검증 결과를 output/tables에 저장

이 스크립트는 원본 파일을 수정하지 않습니다.
"""

from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
PROCESSED = ROOT / "data" / "processed"
OUT = ROOT / "output" / "tables"
OUT.mkdir(parents=True, exist_ok=True)

PRICE_FILE = PROCESSED / "main_final_monthly_price.csv"
RETURN_FILE = PROCESSED / "main_final_monthly_return_decimal.csv"

AUDIT_SUMMARY_FILE = OUT / "price_to_return_consistency_audit.csv"
DIFF_DETAIL_FILE = OUT / "price_to_return_consistency_diff_detail.csv"
RECALC_RETURN_FILE = OUT / "price_recalculated_monthly_return_decimal.csv"

TICKERS = ["069500", "114260", "153130"]


def parse_month_end(s: pd.Series) -> pd.Series:
    raw = s.astype(str).str.strip()

    # 2012-03, 2012-03-31, Mar-12 모두 어느 정도 대응
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


def load_price() -> pd.DataFrame:
    df = pd.read_csv(PRICE_FILE, encoding="utf-8-sig")
    df = df.rename(columns={df.columns[0]: "Date", "69500": "069500"})

    missing = [c for c in ["Date"] + TICKERS if c not in df.columns]
    if missing:
        raise ValueError(f"가격 파일 필요 열 누락: {missing} / 현재 열: {df.columns.tolist()}")

    df["Date"] = parse_month_end(df["Date"])

    for col in TICKERS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.sort_values("Date").set_index("Date")
    return df[TICKERS]


def load_return() -> pd.DataFrame:
    df = pd.read_csv(RETURN_FILE, encoding="utf-8-sig")
    df = df.rename(columns={df.columns[0]: "Date", "69500": "069500"})

    missing = [c for c in ["Date"] + TICKERS if c not in df.columns]
    if missing:
        raise ValueError(f"수익률 파일 필요 열 누락: {missing} / 현재 열: {df.columns.tolist()}")

    df["Date"] = parse_month_end(df["Date"])

    for col in TICKERS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.sort_values("Date").set_index("Date")
    return df[TICKERS]


def main() -> None:
    if not PRICE_FILE.exists():
        raise FileNotFoundError(f"가격 파일이 없습니다: {PRICE_FILE}")

    if not RETURN_FILE.exists():
        raise FileNotFoundError(f"수익률 파일이 없습니다: {RETURN_FILE}")

    price = load_price()
    ret_existing = load_return()

    # 가격에서 월수익률 재계산
    ret_recalc = price.pct_change().dropna()

    # 비교 가능한 공통 월만 사용
    common_idx = ret_recalc.index.intersection(ret_existing.index)
    ret_recalc_common = ret_recalc.loc[common_idx, TICKERS]
    ret_existing_common = ret_existing.loc[common_idx, TICKERS]

    diff = ret_recalc_common - ret_existing_common
    abs_diff = diff.abs()

    # 세부 차이 long format
    detail_rows = []
    for date in common_idx:
        for ticker in TICKERS:
            detail_rows.append(
                {
                    "Date": date.strftime("%Y-%m-%d"),
                    "ticker": ticker,
                    "return_from_price": ret_recalc_common.loc[date, ticker],
                    "return_existing_decimal": ret_existing_common.loc[date, ticker],
                    "diff": diff.loc[date, ticker],
                    "abs_diff": abs_diff.loc[date, ticker],
                }
            )

    diff_detail = pd.DataFrame(detail_rows)
    diff_detail = diff_detail.sort_values("abs_diff", ascending=False)

    # 요약
    tolerance_strict = 1e-10
    tolerance_loose = 1e-6

    max_abs_diff = diff_detail["abs_diff"].max()
    mean_abs_diff = diff_detail["abs_diff"].mean()

    strict_pass = bool(max_abs_diff <= tolerance_strict)
    loose_pass = bool(max_abs_diff <= tolerance_loose)

    summary = pd.DataFrame(
        [
            {
                "item": "price_file",
                "status": "INFO",
                "detail": str(PRICE_FILE),
            },
            {
                "item": "return_file",
                "status": "INFO",
                "detail": str(RETURN_FILE),
            },
            {
                "item": "price_period",
                "status": "INFO",
                "detail": f"{price.index.min().date()} → {price.index.max().date()}, rows={len(price)}",
            },
            {
                "item": "return_period",
                "status": "INFO",
                "detail": f"{ret_existing.index.min().date()} → {ret_existing.index.max().date()}, rows={len(ret_existing)}",
            },
            {
                "item": "common_period",
                "status": "PASS" if len(common_idx) >= 24 else "FAIL",
                "detail": f"{common_idx.min().date()} → {common_idx.max().date()}, rows={len(common_idx)}",
            },
            {
                "item": "max_abs_diff",
                "status": "PASS" if loose_pass else "WARN",
                "detail": f"{max_abs_diff:.12f}",
            },
            {
                "item": "mean_abs_diff",
                "status": "INFO",
                "detail": f"{mean_abs_diff:.12f}",
            },
            {
                "item": "strict_match_1e-10",
                "status": "PASS" if strict_pass else "WARN",
                "detail": f"max_abs_diff <= {tolerance_strict}",
            },
            {
                "item": "loose_match_1e-6",
                "status": "PASS" if loose_pass else "WARN",
                "detail": f"max_abs_diff <= {tolerance_loose}",
            },
        ]
    )

    # 저장
    ret_recalc_out = ret_recalc.reset_index()
    ret_recalc_out["Date"] = ret_recalc_out["Date"].dt.strftime("%Y-%m-%d")

    ret_recalc_out.to_csv(RECALC_RETURN_FILE, index=False, encoding="utf-8-sig")
    diff_detail.to_csv(DIFF_DETAIL_FILE, index=False, encoding="utf-8-sig")
    summary.to_csv(AUDIT_SUMMARY_FILE, index=False, encoding="utf-8-sig")

    print("\n[가격 → 수익률 재계산 검증 요약]")
    print(summary.to_string(index=False))

    print("\n[차이 상위 10개]")
    print(diff_detail.head(10).to_string(index=False))

    print("\n[저장 파일]")
    print(f"- {AUDIT_SUMMARY_FILE}")
    print(f"- {DIFF_DETAIL_FILE}")
    print(f"- {RECALC_RETURN_FILE}")

    if loose_pass:
        print("\n[판정] PASS: main_final_monthly_price.csv로 재계산한 수익률이 기존 decimal 수익률과 실질적으로 일치합니다.")
    else:
        print("\n[판정] WARN: 가격 재계산 수익률과 기존 decimal 수익률 사이에 차이가 있습니다.")
        print("차이 상위 월을 확인해 월말 가격 기준, 수정주가 기준, 최신 가격 반영 여부를 점검해야 합니다.")


if __name__ == "__main__":
    main()