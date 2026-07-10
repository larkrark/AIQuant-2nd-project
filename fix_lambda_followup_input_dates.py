# -*- coding: utf-8 -*-
"""
fix_lambda_followup_input_dates.py

목적:
1. main_final_monthly_return_decimal.csv의 Apr-12 같은 날짜를 2012-04-30 월말 날짜로 변환
2. main_final_baseline_rebalance_weights.csv의 year_month를 2012-03-31 같은 월말 날짜로 변환
3. 069500 열 이름 유지
4. weight_069500 계열을 w_star_069500 계열로 복사
"""

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "processed"

RETURNS_FILE = DATA / "main_final_monthly_return_decimal.csv"
WEIGHTS_FILE = DATA / "main_final_baseline_rebalance_weights.csv"


def parse_month_end(series: pd.Series) -> pd.Series:
    """
    Apr-12, May-12 같은 값을 2012-04-30, 2012-05-31 같은 월말 날짜로 변환.
    이미 2012-04-30 형식이어도 처리 가능.
    """
    raw = series.astype(str).str.strip()

    # 1차: Apr-12 형식
    parsed = pd.to_datetime(raw, format="%b-%y", errors="coerce")

    # 2차: 이미 날짜 형식인 경우
    mask = parsed.isna()
    if mask.any():
        parsed.loc[mask] = pd.to_datetime(raw.loc[mask], errors="coerce")

    if parsed.isna().any():
        bad = raw.loc[parsed.isna()].head(10).tolist()
        raise ValueError(f"날짜 변환 실패 값 예시: {bad}")

    return parsed.dt.to_period("M").dt.to_timestamp("M")


def fix_returns() -> None:
    df = pd.read_csv(RETURNS_FILE)

    # 첫 열이 Date/year_month 등 무엇이든 날짜열로 사용
    date_col = df.columns[0]

    # Excel이 069500을 69500으로 바꾼 경우 대비
    df = df.rename(columns={
        "69500": "069500",
        69500: "069500",
    })

    required = ["069500", "114260", "153130"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"수익률 파일에 필요한 열이 없습니다: {missing} / 현재 열: {df.columns.tolist()}")

    df[date_col] = parse_month_end(df[date_col])
    df = df[[date_col] + required].copy()
    df = df.rename(columns={date_col: "Date"})
    df = df.sort_values("Date")

    # decimal 수익률 확인
    max_abs = df[required].abs().max().max()
    if max_abs > 1.5:
        raise ValueError("수익률이 decimal이 아니라 % 단위처럼 보입니다. 100으로 나누지 않은 원본인지 확인하세요.")

    df.to_csv(RETURNS_FILE, index=False, encoding="utf-8-sig")
    print(f"[OK] returns 저장 완료: {RETURNS_FILE}")
    print(df.head())
    print(df.tail())


def fix_weights() -> None:
    df = pd.read_csv(WEIGHTS_FILE)

    if "year_month" not in df.columns:
        # 첫 열을 신호월로 간주
        df = df.rename(columns={df.columns[0]: "year_month"})

    df["year_month"] = parse_month_end(df["year_month"])

    # weight_* 열을 w_star_*로 복사
    rename_map = {
        "weight_069500": "w_star_069500",
        "weight_114260": "w_star_114260",
        "weight_153130": "w_star_153130",
    }

    for src, dst in rename_map.items():
        if src in df.columns and dst not in df.columns:
            df[dst] = df[src]

    required = ["hsi_state", "w_star_069500", "w_star_114260", "w_star_153130"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"비중 파일에 필요한 열이 없습니다: {missing} / 현재 열: {df.columns.tolist()}")

    keep_cols = ["year_month", "hsi_state", "w_star_069500", "w_star_114260", "w_star_153130"]

    # 있으면 참고용으로 유지
    optional_cols = [
        "return_year_month",
        "state_kr",
        "allocation_rule_name",
        "turnover",
    ]
    keep_cols += [c for c in optional_cols if c in df.columns]

    out = df[keep_cols].copy()
    out = out.rename(columns={"year_month": "Date"})
    out = out.sort_values("Date")

    out.to_csv(WEIGHTS_FILE, index=False, encoding="utf-8-sig")
    print(f"[OK] weights 저장 완료: {WEIGHTS_FILE}")
    print(out.head())
    print(out.tail())


def check_intersection() -> None:
    r = pd.read_csv(RETURNS_FILE, index_col=0, parse_dates=True).sort_index()
    w = pd.read_csv(WEIGHTS_FILE, index_col=0, parse_dates=True).sort_index()

    common = r.index.intersection(w.index)

    print("\n[날짜 확인]")
    print("returns:", r.index.min(), "→", r.index.max(), "rows:", len(r))
    print("weights:", w.index.min(), "→", w.index.max(), "rows:", len(w))
    print("intersection rows:", len(common))
    print("intersection first/last:", common.min(), "→", common.max())

    if len(common) < 24:
        raise ValueError("아직도 교집합이 24개월 미만입니다. 날짜열을 다시 확인하세요.")

    print("[OK] 날짜 교집합 정상입니다.")


def main() -> None:
    fix_returns()
    fix_weights()
    check_intersection()


if __name__ == "__main__":
    main()