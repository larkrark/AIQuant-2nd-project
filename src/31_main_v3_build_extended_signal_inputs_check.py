from pathlib import Path
from datetime import datetime
import importlib.util

import pandas as pd


"""
31_main_v3_build_extended_signal_inputs_check.py

목적
----
데이터 담당 조원님의 HSI_data_pipeline_0629_3.py를
우리 프로젝트 폴더 구조에 맞게 연결하고, 입력데이터 산출물이
main_v3 후속 실험으로 넘어갈 수 있는지 확인한다.

이 파일은 Grid Search나 백테스트를 실행하지 않는다.

하는 일
-------
1. 주원님 데이터 파이프라인 모듈 import
2. ETF 유니버스 / 자산군 분류표 생성
3. 가격 데이터 로드
4. 데이터 기간 / 결측치 / 유동성 점검
5. 월말 가격 / 월간 수익률 생성
6. HSI 기본 입력 신호표 생성
7. 우리 프로젝트 폴더 구조에 맞게 CSV 저장
8. 연결 점검 요약 Markdown 저장

입력
----
src/HSI_data_pipeline_0629_3.py

출력
----
data/processed/selected_etf_universe.csv
data/processed/asset_class_map.csv
data/processed/monthly_prices.csv
data/processed/monthly_returns.csv
data/processed/hsi_signal_snapshot.csv
data/processed/hsi_raw_scores.csv

output/tables/data_period_check.csv
output/tables/missing_value_summary.csv
output/tables/missing_value_by_year.csv
output/tables/liquidity_check.csv
output/tables/main_v3_data_pipeline_check_summary.csv

docs/main_v3_data_pipeline_integration_note.md
"""


# ============================================================
# 0. 경로 설정
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
DATA_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
TABLE_DIR = PROJECT_ROOT / "output" / "tables"
DOCS_DIR = PROJECT_ROOT / "docs"

DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
TABLE_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

PIPELINE_PATH = SRC_DIR / "HSI_data_pipeline_0629_4.py"

OUTPUT_SELECTED_ETF = DATA_PROCESSED_DIR / "selected_etf_universe.csv"
OUTPUT_ASSET_CLASS = DATA_PROCESSED_DIR / "asset_class_map.csv"
OUTPUT_MONTHLY_PRICES = DATA_PROCESSED_DIR / "monthly_prices.csv"
OUTPUT_MONTHLY_RETURNS = DATA_PROCESSED_DIR / "monthly_returns.csv"
OUTPUT_HSI_SNAPSHOT = DATA_PROCESSED_DIR / "hsi_signal_snapshot.csv"
OUTPUT_HSI_RAW_SCORES = DATA_PROCESSED_DIR / "hsi_raw_scores.csv"

OUTPUT_PERIOD_CHECK = TABLE_DIR / "data_period_check.csv"
OUTPUT_MISSING_SUMMARY = TABLE_DIR / "missing_value_summary.csv"
OUTPUT_MISSING_YEARLY = TABLE_DIR / "missing_value_by_year.csv"
OUTPUT_LIQUIDITY_CHECK = TABLE_DIR / "liquidity_check.csv"
OUTPUT_CHECK_SUMMARY = TABLE_DIR / "main_v3_data_pipeline_check_summary.csv"

OUTPUT_NOTE = DOCS_DIR / "main_v3_data_pipeline_integration_note.md"


# ============================================================
# 1. 외부 파이프라인 모듈 로드
# ============================================================

def load_pipeline_module(module_path: Path):
    if not module_path.exists():
        raise FileNotFoundError(
            f"데이터 파이프라인 파일을 찾을 수 없습니다: {module_path}"
        )

    spec = importlib.util.spec_from_file_location(
        "hsi_data_pipeline_0629_3",
        module_path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ============================================================
# 2. 기본 점검 함수
# ============================================================

def make_selected_etf_universe_df(pipe) -> pd.DataFrame:
    rows = []

    for ticker, meta in pipe.ETF_UNIVERSE.items():
        rows.append({
            "ticker": ticker,
            "name": meta.get("name", ""),
            "asset_class": meta.get("asset_class", ""),
            "underlying_asset": meta.get("underlying_asset", ""),
            "risk_group": meta.get("risk_group", ""),
            "listing_date": meta.get("listing_date", ""),
            "data_over_10y": meta.get("data_over_10y", ""),
            "note": meta.get("note", ""),
            "discussion_note": meta.get("discussion_note", ""),
        })

    return pd.DataFrame(rows)


def make_check_summary(
    selected_etf_df: pd.DataFrame,
    period_df: pd.DataFrame,
    missing_summary_df: pd.DataFrame,
    liquidity_df: pd.DataFrame,
    monthly_prices: pd.DataFrame,
    monthly_returns: pd.DataFrame,
    hsi_snapshot: pd.DataFrame,
    hsi_raw_scores: pd.DataFrame,
) -> pd.DataFrame:
    rows = []

    rows.append({
        "check_item": "selected_etf_count",
        "result": len(selected_etf_df),
        "status": "OK" if len(selected_etf_df) == 3 else "CHECK",
        "note": "최종 ETF 3종 구성 여부",
    })

    rows.append({
        "check_item": "required_asset_classes",
        "result": ", ".join(sorted(selected_etf_df["asset_class"].unique())),
        "status": (
            "OK"
            if set(["equity", "bond", "money_market"]).issubset(
                set(selected_etf_df["asset_class"])
            )
            else "CHECK"
        ),
        "note": "equity / bond / money_market 포함 여부",
    })

    rows.append({
        "check_item": "monthly_prices_shape",
        "result": f"{monthly_prices.shape[0]} rows x {monthly_prices.shape[1]} columns",
        "status": "OK" if monthly_prices.shape[0] > 0 else "CHECK",
        "note": "월말 가격표 생성 여부",
    })

    rows.append({
        "check_item": "monthly_returns_shape",
        "result": f"{monthly_returns.shape[0]} rows x {monthly_returns.shape[1]} columns",
        "status": "OK" if monthly_returns.shape[0] > 0 else "CHECK",
        "note": "월간 수익률표 생성 여부",
    })

    total_missing = missing_summary_df["missing_count"].sum()
    rows.append({
        "check_item": "total_missing_after_load",
        "result": int(total_missing),
        "status": "OK" if total_missing == 0 else "CHECK",
        "note": "load_price_data 내부 ffill 이후 결측치",
    })

    liquidity_pass_count = int((liquidity_df["overall_pass"] == True).sum())
    rows.append({
        "check_item": "liquidity_pass_count",
        "result": liquidity_pass_count,
        "status": "OK" if liquidity_pass_count == len(liquidity_df) else "CHECK",
        "note": "거래량/거래대금 기준 통과 ETF 수",
    })

    rows.append({
        "check_item": "hsi_snapshot_rows",
        "result": len(hsi_snapshot),
        "status": "OK" if len(hsi_snapshot) == len(selected_etf_df) else "CHECK",
        "note": "최근일 HSI 스냅샷 생성 여부",
    })

    rows.append({
        "check_item": "hsi_raw_scores_shape",
        "result": f"{hsi_raw_scores.shape[0]} rows x {hsi_raw_scores.shape[1]} columns",
        "status": "OK" if hsi_raw_scores.shape[0] > 0 else "CHECK",
        "note": "HSI 원점수 테이블 생성 여부",
    })

    if "score_rs" in hsi_snapshot.columns:
        benchmark_rows = hsi_snapshot[hsi_snapshot["ticker"].astype(str) == "069500"]
        if len(benchmark_rows) > 0:
            rs_value = benchmark_rows["score_rs"].iloc[0]
            rs_note = (
                benchmark_rows["rs_note"].iloc[0]
                if "rs_note" in hsi_snapshot.columns
                else ""
            )
            rows.append({
                "check_item": "benchmark_rs_snapshot",
                "result": f"score_rs={rs_value}, rs_note={rs_note}",
                "status": "OK",
                "note": "069500은 benchmark 자기비교이므로 NaN 또는 benchmark 표기가 자연스러움",
            })

    return pd.DataFrame(rows)


def make_markdown_note(
    selected_etf_df: pd.DataFrame,
    asset_class_df: pd.DataFrame,
    period_df: pd.DataFrame,
    missing_summary_df: pd.DataFrame,
    liquidity_df: pd.DataFrame,
    monthly_prices: pd.DataFrame,
    monthly_returns: pd.DataFrame,
    hsi_snapshot: pd.DataFrame,
    check_summary: pd.DataFrame,
) -> str:
    lines = []

    lines.append("# main_v3 데이터 파이프라인 연결 점검 노트")
    lines.append("")
    lines.append(f"- 생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## 1. 목적")
    lines.append("")
    lines.append(
        "이 노트는 데이터 담당 조원님의 HSI 데이터 파이프라인 결과를 "
        "우리 프로젝트의 main_v3 후속 실험 구조에 연결할 수 있는지 확인하기 위해 작성되었다."
    )
    lines.append("")
    lines.append("현재 단계에서는 Grid Search, 비중 규칙 최적화, Robustness 검증을 실행하지 않는다.")
    lines.append("")
    lines.append("## 2. 생성된 주요 입력데이터")
    lines.append("")
    lines.append("- `data/processed/selected_etf_universe.csv`")
    lines.append("- `data/processed/asset_class_map.csv`")
    lines.append("- `data/processed/monthly_prices.csv`")
    lines.append("- `data/processed/monthly_returns.csv`")
    lines.append("- `data/processed/hsi_signal_snapshot.csv`")
    lines.append("- `data/processed/hsi_raw_scores.csv`")
    lines.append("")
    lines.append("## 3. ETF 유니버스")
    lines.append("")
    lines.append("| ticker | name | asset_class | underlying_asset | risk_group |")
    lines.append("|---|---|---|---|---|")

    for _, row in selected_etf_df.iterrows():
        lines.append(
            f"| {row['ticker']} | {row['name']} | {row['asset_class']} | "
            f"{row['underlying_asset']} | {row['risk_group']} |"
        )

    lines.append("")
    lines.append("## 4. 데이터 품질 요약")
    lines.append("")
    lines.append(f"- 월말 가격표 크기: `{monthly_prices.shape[0]} rows × {monthly_prices.shape[1]} columns`")
    lines.append(f"- 월간 수익률표 크기: `{monthly_returns.shape[0]} rows × {monthly_returns.shape[1]} columns`")
    lines.append(f"- 전체 결측치 수: `{int(missing_summary_df['missing_count'].sum())}`")
    lines.append(f"- 유동성 통과 ETF 수: `{int((liquidity_df['overall_pass'] == True).sum())}` / `{len(liquidity_df)}`")
    lines.append("")
    lines.append("## 5. HSI 스냅샷")
    lines.append("")
    lines.append("| ticker | name | direction | intensity | signal |")
    lines.append("|---|---|---:|---:|---|")

    for _, row in hsi_snapshot.iterrows():
        lines.append(
            f"| {row['ticker']} | {row['name']} | {row['direction']} | "
            f"{row['intensity']} | {row['signal']} |"
        )

    lines.append("")
    lines.append("## 6. benchmark rs 처리")
    lines.append("")
    lines.append(
        "069500은 상대강도 계산의 benchmark로 사용되므로, "
        "자기 자신과의 relative strength 값은 별도의 정보량을 갖지 않는다. "
        "따라서 스냅샷에서는 benchmark 또는 별도 note로 표시하고, "
        "원시 점수표에서는 계산 구조 보존을 위해 NaN이 남을 수 있다."
    )
    lines.append("")
    lines.append("## 7. main_v3 연결 판단")
    lines.append("")
    lines.append(
        "데이터 파트의 ETF 선정, 자산군 분류, 가격 로드, 결측치, 유동성, "
        "월말 가격, 월간 수익률, HSI 기본 입력 신호표는 main_v3 후속 실험으로 연결 가능하다."
    )
    lines.append("")
    lines.append("다음 단계에서는 `monthly_returns.csv`와 HSI 상태분류 테이블을 연결하여, "
                 "`main_v2b` 기준 비중 규칙 및 후속 신호 조합 실험으로 이어간다.")
    lines.append("")
    lines.append("## 8. 점검표")
    lines.append("")
    lines.append("| check_item | result | status | note |")
    lines.append("|---|---|---|---|")

    for _, row in check_summary.iterrows():
        lines.append(
            f"| {row['check_item']} | {row['result']} | {row['status']} | {row['note']} |"
        )

    lines.append("")

    return "\n".join(lines)


# ============================================================
# 3. 실행
# ============================================================

def main() -> None:
    print("=" * 80)
    print("31_main_v3_build_extended_signal_inputs_check.py 실행 시작")
    print("=" * 80)

    print(f"[1] 데이터 파이프라인 모듈 로드: {PIPELINE_PATH}")
    pipe = load_pipeline_module(PIPELINE_PATH)

    print("[2] ETF 유니버스 및 자산군 분류표 생성")
    selected_etf_df = make_selected_etf_universe_df(pipe)
    asset_class_df = pipe.make_asset_class_table()

    tickers = list(pipe.ETF_UNIVERSE.keys())
    print(f"    tickers = {tickers}")

    print("[3] 가격 데이터 로드")
    prices = pipe.load_price_data(
        tickers=tickers,
        start=pipe.DATA_START_DATE,
        source="yfinance"
    )
    print(f"    prices shape = {prices.shape}")

    print("[4] 데이터 기간 점검")
    period_df = pipe.check_data_period(prices)

    print("[5] 결측치 점검")
    missing_summary_df, missing_yearly_df = pipe.check_missing_values(prices)

    print("[6] 거래량 및 유동성 점검")
    try:
        volumes = pipe.load_volume_data(
            tickers=tickers,
            start=pipe.DATA_START_DATE,
            source="yfinance"
        )
    except Exception as e:
        print(f"    [주의] 거래량 로드 실패: {e}")
        volumes = None

    liquidity_df = pipe.check_liquidity(prices, volumes=volumes)

    print("[7] 월말 가격 및 월간 수익률 생성")
    monthly_prices = pipe.make_monthly_price_table(prices)
    monthly_returns = pipe.make_monthly_return_table(prices)

    print("[8] HSI 기본 입력 신호표 생성")
    signal_tables = pipe.make_hsi_signal_table(prices)
    hsi_snapshot = signal_tables["snapshot"]
    hsi_raw_scores = signal_tables["raw_scores"]

    print("[9] 연결 점검 요약 생성")
    check_summary = make_check_summary(
        selected_etf_df=selected_etf_df,
        period_df=period_df,
        missing_summary_df=missing_summary_df,
        liquidity_df=liquidity_df,
        monthly_prices=monthly_prices,
        monthly_returns=monthly_returns,
        hsi_snapshot=hsi_snapshot,
        hsi_raw_scores=hsi_raw_scores,
    )

    print("[10] CSV 저장")
    selected_etf_df.to_csv(OUTPUT_SELECTED_ETF, index=False, encoding="utf-8-sig")
    asset_class_df.to_csv(OUTPUT_ASSET_CLASS, index=False, encoding="utf-8-sig")
    monthly_prices.to_csv(OUTPUT_MONTHLY_PRICES, encoding="utf-8-sig")
    monthly_returns.to_csv(OUTPUT_MONTHLY_RETURNS, encoding="utf-8-sig")
    hsi_snapshot.to_csv(OUTPUT_HSI_SNAPSHOT, index=False, encoding="utf-8-sig")
    hsi_raw_scores.to_csv(OUTPUT_HSI_RAW_SCORES, encoding="utf-8-sig")

    period_df.to_csv(OUTPUT_PERIOD_CHECK, index=False, encoding="utf-8-sig")
    missing_summary_df.to_csv(OUTPUT_MISSING_SUMMARY, index=False, encoding="utf-8-sig")
    missing_yearly_df.to_csv(OUTPUT_MISSING_YEARLY, encoding="utf-8-sig")
    liquidity_df.to_csv(OUTPUT_LIQUIDITY_CHECK, index=False, encoding="utf-8-sig")
    check_summary.to_csv(OUTPUT_CHECK_SUMMARY, index=False, encoding="utf-8-sig")

    print("[11] Markdown 노트 저장")
    note = make_markdown_note(
        selected_etf_df=selected_etf_df,
        asset_class_df=asset_class_df,
        period_df=period_df,
        missing_summary_df=missing_summary_df,
        liquidity_df=liquidity_df,
        monthly_prices=monthly_prices,
        monthly_returns=monthly_returns,
        hsi_snapshot=hsi_snapshot,
        check_summary=check_summary,
    )
    OUTPUT_NOTE.write_text(note, encoding="utf-8")

    print("\n[저장 완료]")
    for path in [
        OUTPUT_SELECTED_ETF,
        OUTPUT_ASSET_CLASS,
        OUTPUT_MONTHLY_PRICES,
        OUTPUT_MONTHLY_RETURNS,
        OUTPUT_HSI_SNAPSHOT,
        OUTPUT_HSI_RAW_SCORES,
        OUTPUT_PERIOD_CHECK,
        OUTPUT_MISSING_SUMMARY,
        OUTPUT_MISSING_YEARLY,
        OUTPUT_LIQUIDITY_CHECK,
        OUTPUT_CHECK_SUMMARY,
        OUTPUT_NOTE,
    ]:
        print(f"- {path}")

    print("\n[점검 요약]")
    print(check_summary.to_string(index=False))

    print("\n" + "=" * 80)
    print("31_main_v3_build_extended_signal_inputs_check.py 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()