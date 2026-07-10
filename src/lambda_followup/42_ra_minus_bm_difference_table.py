from pathlib import Path
import pandas as pd


def find_input_table(table_dir: Path) -> Path:
    """
    Final RA vs BM 성과표 파일을 찾는다.
    파일명이 조금 다를 수 있으므로 후보 파일을 순서대로 확인한다.
    """
    candidates = [
        table_dir / "main_final_final_ra_vs_bm_performance_table.csv",
        table_dir / "main_final_ra_vs_bm_performance_table.csv",
        table_dir / "main_final_is_oos_performance_table.csv",
    ]

    for path in candidates:
        if path.exists():
            return path

    raise FileNotFoundError(
        "Final RA vs BM 성과표 CSV를 찾지 못했습니다.\n"
        "확인 후보:\n"
        + "\n".join(str(p) for p in candidates)
    )


def fmt_pct(value: float) -> str:
    return f"{value:.2f}%"


def fmt_pp(value: float) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%p"


def fmt_ratio(value: float) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}"


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    table_dir = root / "output" / "tables"
    table_dir.mkdir(parents=True, exist_ok=True)

    input_path = find_input_table(table_dir)
    print(f"[INFO] input table: {input_path}")

    df = pd.read_csv(input_path)

    required_cols = {
        "period",
        "strategy",
        "cumulative_return_pct",
        "cagr_pct",
        "ann_vol_pct",
        "mdd_pct",
        "sharpe",
        "calmar",
    }

    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"필수 컬럼이 없습니다: {sorted(missing)}")

    periods = ["OOS", "FULL"]
    ra_name = "Final_RA_dynamic_v1"
    bm_name = "FixedBM_70_20_10"

    rows = []

    for period in periods:
        sub = df[df["period"].eq(period)].copy()

        if sub.empty:
            raise ValueError(f"{period} 구간 데이터가 없습니다.")

        ra_row = sub[sub["strategy"].eq(ra_name)]
        bm_row = sub[sub["strategy"].eq(bm_name)]

        if ra_row.empty:
            raise ValueError(f"{period} 구간에서 {ra_name} 전략을 찾지 못했습니다.")
        if bm_row.empty:
            raise ValueError(f"{period} 구간에서 {bm_name} 전략을 찾지 못했습니다.")

        ra = ra_row.iloc[0]
        bm = bm_row.iloc[0]

        # 1) 수익률 계열: RA - BM
        rows.append({
            "구간": period,
            "항목": "누적수익률",
            "Final_RA_dynamic_v1": fmt_pct(ra["cumulative_return_pct"]),
            "FixedBM_70_20_10": fmt_pct(bm["cumulative_return_pct"]),
            "RA−BM / 개선폭": fmt_pp(ra["cumulative_return_pct"] - bm["cumulative_return_pct"]),
            "해석": "수익률 알파"
        })

        rows.append({
            "구간": period,
            "항목": "CAGR",
            "Final_RA_dynamic_v1": fmt_pct(ra["cagr_pct"]),
            "FixedBM_70_20_10": fmt_pct(bm["cagr_pct"]),
            "RA−BM / 개선폭": fmt_pp(ra["cagr_pct"] - bm["cagr_pct"]),
            "해석": "수익률 알파"
        })

        # 2) 위험 계열: 낮을수록 좋으므로 BM - RA를 개선폭으로 표시
        vol_improve = bm["ann_vol_pct"] - ra["ann_vol_pct"]
        rows.append({
            "구간": period,
            "항목": "연환산 변동성",
            "Final_RA_dynamic_v1": fmt_pct(ra["ann_vol_pct"]),
            "FixedBM_70_20_10": fmt_pct(bm["ann_vol_pct"]),
            "RA−BM / 개선폭": f"변동성 {vol_improve:.2f}%p 감소",
            "해석": "방어 지표"
        })

        # MDD는 음수이므로 abs 기준으로 낙폭 개선폭을 표시
        mdd_improve = abs(bm["mdd_pct"]) - abs(ra["mdd_pct"])
        rows.append({
            "구간": period,
            "항목": "MDD",
            "Final_RA_dynamic_v1": fmt_pct(ra["mdd_pct"]),
            "FixedBM_70_20_10": fmt_pct(bm["mdd_pct"]),
            "RA−BM / 개선폭": f"낙폭 {mdd_improve:.2f}%p 개선",
            "해석": "방어 지표"
        })

        # 3) 위험조정 지표: RA - BM
        rows.append({
            "구간": period,
            "항목": "Sharpe",
            "Final_RA_dynamic_v1": f"{ra['sharpe']:.2f}",
            "FixedBM_70_20_10": f"{bm['sharpe']:.2f}",
            "RA−BM / 개선폭": fmt_ratio(ra["sharpe"] - bm["sharpe"]),
            "해석": "위험조정 성과"
        })

        rows.append({
            "구간": period,
            "항목": "Calmar",
            "Final_RA_dynamic_v1": f"{ra['calmar']:.2f}",
            "FixedBM_70_20_10": f"{bm['calmar']:.2f}",
            "RA−BM / 개선폭": fmt_ratio(ra["calmar"] - bm["calmar"]),
            "해석": "위험조정 성과"
        })

    out = pd.DataFrame(rows)

    csv_path = table_dir / "main_final_ra_minus_bm_difference_table.csv"
    md_path = table_dir / "main_final_ra_minus_bm_difference_table.md"

    out.to_csv(csv_path, index=False, encoding="utf-8-sig")

    with md_path.open("w", encoding="utf-8") as f:
        f.write("[표 13-1-1. Final_RA_dynamic_v1과 FixedBM_70_20_10의 RA−BM 차이]\n\n")
        f.write(out.to_markdown(index=False))
        f.write("\n")

    print(f"[OK] saved csv: {csv_path}")
    print(f"[OK] saved md : {md_path}")
    print()
    print(out.to_markdown(index=False))


if __name__ == "__main__":
    main()