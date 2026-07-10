from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SEARCH_DIRS = [
    PROJECT_ROOT / "data" / "processed",
    PROJECT_ROOT / "output" / "tables",
    PROJECT_ROOT / "output",
]

OUT_DIR = PROJECT_ROOT / "output" / "tables"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def safe_read_csv(path: Path) -> pd.DataFrame | None:
    try:
        return pd.read_csv(path)
    except Exception:
        return None


def main() -> None:
    rows = []

    csv_files = []
    for d in SEARCH_DIRS:
        if d.exists():
            csv_files.extend(d.rglob("*.csv"))

    print(f"[INFO] csv files found: {len(csv_files)}")

    for path in csv_files:
        df = safe_read_csv(path)
        if df is None or df.empty:
            continue

        numeric_cols = [
            col for col in df.columns
            if pd.api.types.is_numeric_dtype(df[col])
        ]

        for col in numeric_cols:
            s = pd.to_numeric(df[col], errors="coerce")
            if s.dropna().empty:
                continue

            min_val = s.min()
            max_val = s.max()
            max_abs = s.abs().max()

            # 그림에서 보인 폭주값 후보를 찾기 위한 넓은 기준
            suspicious = False
            reason = []

            if max_abs > 100:
                suspicious = True
                reason.append("abs(value) > 100")

            if "drawdown" in col.lower() and min_val < -1:
                suspicious = True
                reason.append("drawdown < -1")

            if "return" in col.lower() and "cumulative" not in col.lower() and max_abs > 1:
                suspicious = True
                reason.append("return abs > 1")

            if suspicious:
                rows.append({
                    "file": str(path.relative_to(PROJECT_ROOT)),
                    "column": col,
                    "min": min_val,
                    "max": max_val,
                    "max_abs": max_abs,
                    "reason": " / ".join(reason),
                    "n_rows": len(df),
                    "columns": ", ".join(df.columns),
                })

    result = pd.DataFrame(rows)

    out_path = OUT_DIR / "main_final_spike_source_file_candidates.csv"
    result.to_csv(out_path, index=False, encoding="utf-8-sig")

    print(f"[SAVED] {out_path}")

    if result.empty:
        print("[RESULT] CSV 안에서는 obvious spike source를 못 찾았습니다.")
        print("[NEXT] plotting script 내부 계산 문제일 가능성이 커집니다.")
    else:
        print("[RESULT] suspicious files:")
        print(result[["file", "column", "min", "max", "reason"]].head(50).to_string(index=False))


if __name__ == "__main__":
    main()