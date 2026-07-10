from pathlib import Path
import pandas as pd


# ============================================================
# 15_make_macro_question_samples.py
#
# 목적:
# - data/raw 안의 사측 제공 macro CSV를 앞 40행 + 뒤 40행으로 샘플링
# - 샘플 CSV에 확인 필요한 부분만 '?' 표시
# - 주원님께 전달할 확인 메모와 질문표 생성
#
# 원본 CSV는 절대 수정하지 않음
# ============================================================


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

OUT_DIR = PROJECT_ROOT / "macro_review_for_juwon"
OUT_DIR.mkdir(parents=True, exist_ok=True)


RAW_FILES = {
    "gdp_growth": {
        "path": RAW_DIR / "2. 2014년 이후 매크로 데이터(GDP 성장률).csv",
        "label": "GDP 성장률",
        "columns_to_check": "날짜/분기 컬럼, GDP 성장률 값 컬럼",
        "question": "GDP는 분기자료·계절성·기저효과·발표지연 문제가 있으므로 최종 직접 반영에서 제외하고 비교·진단용으로만 두는 방향이 괜찮을까요?",
        "interpretation": "초기 후보로 검토했지만 최종 macro companion 직접 입력에서는 제외하는 방향입니다.",
    },
    "gov_bond_balance": {
        "path": RAW_DIR / "2. 2014년 이후 매크로 데이터(국채발행잔액).csv",
        "label": "국채발행잔액",
        "columns_to_check": "날짜 컬럼, 국채발행잔액 값 컬럼",
        "question": "국채발행잔액은 설명 부담이 있어 최종 모델 직접 입력보다 참고 후보군으로만 두는 것이 적절할까요?",
        "interpretation": "채권시장·유동성 참고 자료로는 의미가 있지만 최종 직접 반영 여부는 확인이 필요합니다.",
    },
    "trade_fx_reserve": {
        "path": RAW_DIR / "2. 2014년 이후 매크로 데이터(수입수출외환보유).csv",
        "label": "수입수출외환보유",
        "columns_to_check": "날짜 컬럼, 수출/수입/외환보유액 관련 컬럼",
        "question": "수입수출외환보유 자료는 최종 모델 직접 입력보다 대외건전성 참고 후보군으로만 두는 것이 적절할까요?",
        "interpretation": "대외건전성 설명에는 도움이 되지만 최종 전략에 넣으면 설명 변수가 많아질 수 있습니다.",
    },
    "interest_rate_rp": {
        "path": RAW_DIR / "2014년 이후 금리 자료(RP).csv",
        "label": "금리 자료(RP)",
        "columns_to_check": "날짜 컬럼, RP 금리값 컬럼",
        "question": "RP 금리는 단기금리 후보로 볼 수 있지만, 최종 금리 변수로 쓸지 또는 참고용으로 둘지 확인이 필요할까요?",
        "interpretation": "정책·단기 유동성 압력 후보입니다.",
    },
    "interest_rate": {
        "path": RAW_DIR / "2014년 이후 금리 자료.csv",
        "label": "금리 자료",
        "columns_to_check": "날짜 컬럼, 금리값 컬럼",
        "question": "금리 자료는 연율 %로 보고 월간 수익률처럼 변환하지 않고 변화폭/표준화 방식으로 사용하는 것이 맞을까요?",
        "interpretation": "최종 macro companion에서는 금리 압력 변수 후보로 사용합니다.",
    },
    "exchange_rate": {
        "path": RAW_DIR / "2014년 이후 환율 데이터.csv",
        "label": "환율 데이터",
        "columns_to_check": "날짜 컬럼, 원/달러 환율값 컬럼",
        "question": "환율은 월말 기준 전월 대비 변화율로 계산해 ETF 월말 기준과 맞추는 방식이 괜찮을까요?",
        "interpretation": "최종 macro companion에서는 외국인 수급·위험회피 압력 변수 후보로 사용합니다.",
    },
}


PROCESSED_FILES = {
    "macro_overlay_weights": {
        "path": PROCESSED_DIR / "main_final_macro_overlay_weights.csv",
        "label": "14번 macro overlay weights",
        "columns_to_check": "year_month, return_year_month, macro_overlay_delta, weight_069500, weight_114260, weight_153130",
        "question": "t월 신호와 조정 비중을 t+1월 수익률에 적용한 구조로 해석해도 괜찮을까요?",
        "interpretation": "14번은 최종 모델이 아니라 HSI baseline 위에 붙인 보조 macro soft overlay 실험입니다.",
    },
    "macro_overlay_backtest_timeseries": {
        "path": PROCESSED_DIR / "main_final_macro_overlay_backtest_timeseries.csv",
        "label": "14번 macro overlay backtest timeseries",
        "columns_to_check": "월별 수익률, 누적수익률, drawdown 관련 컬럼",
        "question": "14번 결과는 최종 후보 모델이 아니라 보조 실험 결과로 두는 것이 적절할까요?",
        "interpretation": "성과 개선 목적보다 macro 보조 layer의 영향 확인 목적입니다.",
    },
    "macro_hsi_joined": {
        "path": PROCESSED_DIR / "main_final_hsi_macro_companion_joined_monthly.csv",
        "label": "13번 HSI-macro joined table",
        "columns_to_check": "hsi_state, macro_risk_flag, macro_defense_addon 관련 컬럼",
        "question": "HSI 상태와 macro risk flag의 월말 정렬 기준이 기존 ETF 데이터 기준과 충돌하지 않는지 확인 부탁드립니다.",
        "interpretation": "13번은 HSI 위험상태와 macro 위험의 겹침을 보는 진단표입니다.",
    },
}


def read_csv_safely(path: Path) -> pd.DataFrame:
    encodings = ["utf-8-sig", "utf-8", "cp949", "euc-kr"]

    last_error = None
    for enc in encodings:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception as e:
            last_error = e

    raise RuntimeError(f"CSV 읽기 실패: {path}\n마지막 오류: {last_error}")


def make_head_tail(df: pd.DataFrame, n: int = 40) -> pd.DataFrame:
    if len(df) <= n * 2:
        sample = df.copy()
        sample.insert(0, "_sample_part", "all")
        return sample

    head = df.head(n).copy()
    tail = df.tail(n).copy()

    head.insert(0, "_sample_part", "head")
    tail.insert(0, "_sample_part", "tail")

    return pd.concat([head, tail], axis=0)


def detect_date_column(df: pd.DataFrame):
    candidates = [
        "date", "Date", "DATE",
        "날짜", "일자", "기준일", "시점", "년월",
        "year_month", "return_year_month",
        "month", "Month",
    ]

    for col in candidates:
        if col in df.columns:
            return col

    for col in df.columns:
        col_text = str(col)
        if any(key in col_text for key in ["날짜", "일자", "기준", "시점", "년월", "date", "Date", "month"]):
            return col

    return None


def add_review_columns(sample: pd.DataFrame, info: dict) -> pd.DataFrame:
    sample = sample.copy()

    sample["_review_mark"] = ""
    sample["_columns_to_check"] = ""
    sample["_review_question"] = ""
    sample["_my_interpretation"] = ""

    if len(sample) > 0:
        first_index = sample.index[0]
        sample.loc[first_index, "_review_mark"] = "?"
        sample.loc[first_index, "_columns_to_check"] = info["columns_to_check"]
        sample.loc[first_index, "_review_question"] = info["question"]
        sample.loc[first_index, "_my_interpretation"] = info["interpretation"]

    return sample


def summarize_one_file(group: str, name: str, info: dict) -> dict:
    path = info["path"]

    if not path.exists():
        return {
            "group": group,
            "name": name,
            "label": info["label"],
            "path": str(path),
            "exists": False,
            "rows": None,
            "cols": None,
            "date_column_detected": None,
            "date_min": None,
            "date_max": None,
            "missing_cells": None,
            "sample_file": None,
            "question": info["question"],
            "note": "파일 없음. 파일명 또는 경로 확인 필요",
        }

    df = read_csv_safely(path)
    sample = make_head_tail(df, n=40)
    sample = add_review_columns(sample, info)

    sample_file = f"sample_{name}_checked.csv"
    sample_path = OUT_DIR / sample_file
    sample.to_csv(sample_path, index=False, encoding="utf-8-sig")

    date_col = detect_date_column(df)
    date_min = None
    date_max = None

    if date_col is not None:
        parsed = pd.to_datetime(df[date_col], errors="coerce")
        if parsed.notna().any():
            date_min = parsed.min()
            date_max = parsed.max()

    return {
        "group": group,
        "name": name,
        "label": info["label"],
        "path": str(path),
        "exists": True,
        "rows": len(df),
        "cols": len(df.columns),
        "date_column_detected": date_col,
        "date_min": date_min,
        "date_max": date_max,
        "missing_cells": int(df.isna().sum().sum()),
        "sample_file": sample_file,
        "question": info["question"],
        "note": "",
    }


def write_note() -> None:
    note = """# Macro 자료 연결 기준 확인 요청

주원님, 제가 macro companion 실험을 붙이면서 사측 제공 macro 자료를 HSI 결과와 연결해 보았습니다.

전체 원자료를 다시 검수해 달라는 의미는 아니고, 제가 추가로 연결한 방식이 기존 ETF 가격·수익률 데이터 기준과 충돌하지 않는지만 확인받고 싶습니다.

확인하시기 편하도록 각 CSV는 앞 40행/뒤 40행만 잘라서 검토용 샘플로 만들었고, 확인이 필요한 부분에는 `_review_mark` 컬럼에 `?` 표시를 달았습니다. 구체적인 질문은 `_review_question` 컬럼에 적어두었습니다.

## 확인받고 싶은 핵심

1. ETF 월간 수익률 단위가 decimal 기준으로 맞는지
2. macro 자료의 월말 매칭 방식이 기존 ETF 데이터 기준과 충돌하지 않는지
3. 금리 자료는 연율 %로 보고 변화폭/표준화 방식으로 사용해도 되는지
4. GDP는 최종 직접 반영에서 제외하고 비교·진단용으로만 두는 방향이 괜찮은지
5. 국채발행잔액, 수입수출외환보유 자료는 최종 모델에 직접 넣기보다 참고 후보군으로만 두는 것이 적절한지
6. 14번 macro overlay 결과는 최종 모델이 아니라 보조 실험으로 두는 것이 적절한지

## GDP 제외 방향

GDP는 초기에는 macro companion 후보로 검토했지만, 최종 전략에 직접 반영하는 변수에서는 제외하는 방향이 적절하다고 판단했습니다.

첫째, GDP는 분기 자료라서 월말 리밸런싱 ETF 전략과 속도가 잘 맞지 않습니다.

둘째, GDP 값에는 음수 구간, 계절성, 기저효과가 섞일 수 있어 단순 기준으로 위험 신호를 만들면 실제 위험보다 자료 구조가 반영될 가능성이 있습니다.

셋째, GDP를 넣으면 발표 지연, 수정치, 분기→월 변환 방식까지 설명해야 해서 최종 모델의 설명 부담이 커집니다.

따라서 최종 macro companion에서는 금리와 환율 중심으로 보고, GDP는 비교·진단용으로만 남기는 방향을 검토하고 있습니다.

## 샘플 파일 보는 방법

각 `sample_..._checked.csv` 파일의 맨 오른쪽에 아래 검토용 컬럼을 추가했습니다.

- `_review_mark`: 확인 필요한 부분은 `?` 표시
- `_columns_to_check`: 어떤 컬럼을 봐주시면 되는지
- `_review_question`: 확인 질문
- `_my_interpretation`: 제가 현재 이해한 방식

원본 CSV는 수정하지 않았고, 검토용 샘플 파일에만 표시를 달았습니다.
"""
    note_path = OUT_DIR / "00_확인요청_메모.md"
    note_path.write_text(note, encoding="utf-8-sig")


def main() -> None:
    print("=" * 80)
    print("15_make_macro_question_samples.py 실행 시작")
    print("=" * 80)

    summary_rows = []

    print("[1] raw macro 파일 샘플 생성")
    for name, info in RAW_FILES.items():
        row = summarize_one_file("raw_macro", name, info)
        summary_rows.append(row)
        print(f"    {name}: exists={row['exists']} rows={row['rows']} sample={row['sample_file']}")

    print("[2] processed 결과 파일 샘플 생성")
    for name, info in PROCESSED_FILES.items():
        row = summarize_one_file("processed_result", name, info)
        summary_rows.append(row)
        print(f"    {name}: exists={row['exists']} rows={row['rows']} sample={row['sample_file']}")

    print("[3] 질문표 저장")
    summary_df = pd.DataFrame(summary_rows)
    summary_path = OUT_DIR / "review_file_summary.csv"
    summary_df.to_csv(summary_path, index=False, encoding="utf-8-sig")
    print(f"    저장: {summary_path}")

    question_cols = [
        "group",
        "name",
        "label",
        "sample_file",
        "exists",
        "rows",
        "cols",
        "date_column_detected",
        "date_min",
        "date_max",
        "question",
        "note",
    ]
    question_df = summary_df[question_cols].copy()
    question_path = OUT_DIR / "review_questions.csv"
    question_df.to_csv(question_path, index=False, encoding="utf-8-sig")
    print(f"    저장: {question_path}")

    print("[4] 확인요청 메모 저장")
    write_note()
    print(f"    저장: {OUT_DIR / '00_확인요청_메모.md'}")

    print("=" * 80)
    print("생성 완료")
    print(f"저장 폴더: {OUT_DIR}")
    print("=" * 80)

    display_cols = [
        "group",
        "name",
        "exists",
        "rows",
        "cols",
        "date_column_detected",
        "date_min",
        "date_max",
        "sample_file",
    ]
    print(summary_df[display_cols].to_string(index=False))


if __name__ == "__main__":
    main()