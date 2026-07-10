from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
TABLE_DIR = PROJECT_ROOT / "output" / "tables"
TABLE_DIR.mkdir(parents=True, exist_ok=True)


FILES = {
    "return_decimal": PROCESSED_DIR / "main_final_monthly_return_decimal.csv",
    "return_pct": PROCESSED_DIR / "main_final_monthly_return_pct.csv",
    "baseline_weights": PROCESSED_DIR / "main_final_baseline_rebalance_weights.csv",
    "baseline_backtest": PROCESSED_DIR / "main_final_baseline_backtest_timeseries.csv",
}


def read_csv_if_exists(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        print(f"[MISSING] {path}")
        return None

    df = pd.read_csv(path)
    print(f"\n[LOAD] {path}")
    print(f"shape = {df.shape}")
    print(f"columns = {list(df.columns)}")
    return df


def find_numeric_columns(df: pd.DataFrame) -> list[str]:
    return [
        col for col in df.columns
        if pd.api.types.is_numeric_dtype(df[col])
    ]


def check_return_file(name: str, df: pd.DataFrame) -> pd.DataFrame:
    suspect_rows = []

    return_cols = [
        col for col in df.columns
        if "return" in col.lower() or "ret" in col.lower()
    ]

    if not return_cols:
        print(f"[WARN] {name}: return column not found")
        return pd.DataFrame()

    print(f"\n[CHECK RETURN] {name}")
    for col in return_cols:
        s = pd.to_numeric(df[col], errors="coerce")
        print(
            f"{col}: "
            f"min={s.min():.6f}, "
            f"max={s.max():.6f}, "
            f"median_abs={s.abs().median():.6f}, "
            f"max_abs={s.abs().max():.6f}"
        )

        bad = df.loc[s.abs() > 1].copy()
        if not bad.empty:
            bad["check_file"] = name
            bad["check_column"] = col
            bad["check_reason"] = "abs(return) > 1 : decimal 수익률이 아닐 가능성"
            suspect_rows.append(bad)

    if suspect_rows:
        return pd.concat(suspect_rows, ignore_index=True)
    return pd.DataFrame()


def check_weight_file(df: pd.DataFrame) -> pd.DataFrame:
    print("\n[CHECK WEIGHTS]")

    if "weight" not in df.columns:
        print("[WARN] weight column not found")
        return pd.DataFrame()

    # 가능한 날짜/전략 컬럼 자동 탐색
    strategy_cols = [c for c in ["strategy", "strategy_name"] if c in df.columns]
    month_cols = [
        c for c in ["signal_month", "return_month", "year_month", "month", "date"]
        if c in df.columns
    ]

    group_cols = strategy_cols + month_cols
    if not group_cols:
        print("[WARN] group columns not found. Only checking raw weight values.")
        print(df["weight"].describe())
        bad = df.loc[df["weight"].abs() > 1.5].copy()
        bad["check_reason"] = "weight > 1.5 : 비중이 70/20/10 형태일 가능성"
        return bad

    weight_sum = (
        df.groupby(group_cols, dropna=False)["weight"]
        .sum()
        .reset_index(name="weight_sum")
    )

    print(weight_sum["weight_sum"].describe())

    bad_sum = weight_sum.loc[
        (weight_sum["weight_sum"] < 0.99) |
        (weight_sum["weight_sum"] > 1.01)
    ].copy()

    if not bad_sum.empty:
        bad_sum["check_reason"] = "weight sum != 1 : 비중 합계 오류 가능성"

    bad_raw = df.loc[df["weight"].abs() > 1.5].copy()
    if not bad_raw.empty:
        bad_raw["check_reason"] = "raw weight > 1.5 : 0.7이 아니라 70으로 들어갔을 가능성"

    return pd.concat([bad_sum, bad_raw], ignore_index=True, sort=False)


def check_backtest_file(df: pd.DataFrame) -> pd.DataFrame:
    print("\n[CHECK BACKTEST RESULT]")

    suspect_rows = []

    numeric_cols = find_numeric_columns(df)
    for col in numeric_cols:
        s = pd.to_numeric(df[col], errors="coerce")
        print(
            f"{col}: "
            f"min={s.min():.6f}, "
            f"max={s.max():.6f}, "
            f"max_abs={s.abs().max():.6f}"
        )

    for col in df.columns:
        lower = col.lower()

        if "return" in lower:
            s = pd.to_numeric(df[col], errors="coerce")
            bad = df.loc[s.abs() > 1].copy()
            if not bad.empty:
                bad["check_column"] = col
                bad["check_reason"] = "portfolio return abs > 1 : 월 수익률 단위 오류 가능성"
                suspect_rows.append(bad)

        if "drawdown" in lower:
            s = pd.to_numeric(df[col], errors="coerce")
            bad = df.loc[s < -100].copy()
            if not bad.empty:
                bad["check_column"] = col
                bad["check_reason"] = "drawdown < -100% : 정상 포트폴리오에서 불가능"
                suspect_rows.append(bad)

        if "cum" in lower or "growth" in lower:
            s = pd.to_numeric(df[col], errors="coerce")
            bad = df.loc[s.abs() > 100].copy()
            if not bad.empty:
                bad["check_column"] = col
                bad["check_reason"] = "cumulative value too large : 누적수익 계산 폭주"
                suspect_rows.append(bad)

    if suspect_rows:
        return pd.concat(suspect_rows, ignore_index=True, sort=False)
    return pd.DataFrame()


def main() -> None:
    all_suspects = []

    loaded = {
        name: read_csv_if_exists(path)
        for name, path in FILES.items()
    }

    for name in ["return_decimal", "return_pct"]:
        df = loaded.get(name)
        if df is not None:
            suspects = check_return_file(name, df)
            if not suspects.empty:
                all_suspects.append(suspects)

    weights = loaded.get("baseline_weights")
    if weights is not None:
        suspects = check_weight_file(weights)
        if not suspects.empty:
            all_suspects.append(suspects)

    bt = loaded.get("baseline_backtest")
    if bt is not None:
        suspects = check_backtest_file(bt)
        if not suspects.empty:
            all_suspects.append(suspects)

    if all_suspects:
        out = pd.concat(all_suspects, ignore_index=True, sort=False)
        out_path = TABLE_DIR / "main_final_debug_recent_spike_suspects.csv"
        out.to_csv(out_path, index=False, encoding="utf-8-sig")
        print(f"\n[SAVED] {out_path}")
        print("\n[RESULT] 의심 행이 발견되었습니다. 위 CSV를 확인하세요.")
    else:
        print("\n[RESULT] obvious suspect not found. 다음 단계로 merge/alignment를 봐야 합니다.")


if __name__ == "__main__":
    main()