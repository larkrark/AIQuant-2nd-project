from datetime import datetime
from pathlib import Path
import importlib.util

import numpy as np
import pandas as pd

import final_project_config as cfg


"""
50_build_market_event_calendar_table.py

목적
----
shock_calendar.py 또는 src/market_event_calendar.py에 정리된 외부 시장 사건 달력을
표준 CSV로 변환한다.

중요
----
시장 사건 달력은 HSI 계산이나 비중 결정에 직접 사용하지 않는다.
HSI 상태와 백테스트 결과를 먼저 산출한 뒤,
주요 시장 사건 구간과 사후적으로 대조하는 해석·검증·시각화 보조 자료이다.

입력 후보
---------
project_root/shock_calendar.py
src/market_event_calendar.py

출력
----
data/reference/market_event_calendar.csv
output/tables/market_event_calendar_master.csv
output/tables/market_event_calendar_quality_check.csv

docs/main_final_market_event_calendar_note.md
"""


OUTPUT_REFERENCE_CALENDAR = cfg.REFERENCE_DIR / "market_event_calendar.csv"
OUTPUT_MASTER_CALENDAR = cfg.TABLE_DIR / "market_event_calendar_master.csv"
OUTPUT_QUALITY_CHECK = cfg.TABLE_DIR / "market_event_calendar_quality_check.csv"
OUTPUT_NOTE = cfg.DOCS_DIR / "main_final_market_event_calendar_note.md"


CANDIDATE_VARIABLE_NAMES = [
    "market_event_calendar",
    "MARKET_EVENT_CALENDAR",
    "shock_calendar",
    "SHOCK_CALENDAR",
    "events",
    "EVENTS",
]


def save_csv(df: pd.DataFrame, path: Path, index: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=index, encoding="utf-8-sig")


def choose_calendar_file() -> Path:
    """
    최종 권장 파일이 있으면 우선 사용하고,
    없으면 프로젝트 루트의 shock_calendar.py를 사용한다.
    """
    if cfg.MARKET_EVENT_CALENDAR_FILE.exists():
        return cfg.MARKET_EVENT_CALENDAR_FILE

    if cfg.SHOCK_CALENDAR_DRAFT.exists():
        return cfg.SHOCK_CALENDAR_DRAFT

    raise FileNotFoundError(
        "외부 사건 달력 파일을 찾지 못했습니다.\n"
        f"- 권장: {cfg.MARKET_EVENT_CALENDAR_FILE}\n"
        f"- 초안: {cfg.SHOCK_CALENDAR_DRAFT}"
    )


def load_python_module(path: Path):
    spec = importlib.util.spec_from_file_location("market_event_calendar_module", path)
    module = importlib.util.module_from_spec(spec)

    if spec.loader is None:
        raise ImportError(f"모듈 로더를 생성하지 못했습니다: {path}")

    spec.loader.exec_module(module)
    return module


def find_calendar_object(module):
    for name in CANDIDATE_VARIABLE_NAMES:
        if hasattr(module, name):
            return name, getattr(module, name)

    available = [name for name in dir(module) if not name.startswith("_")]
    raise AttributeError(
        "사건 달력 변수명을 찾지 못했습니다. "
        f"후보 변수명: {CANDIDATE_VARIABLE_NAMES}\n"
        f"현재 공개 객체: {available}"
    )


def flatten_event_object(obj) -> list[dict]:
    """
    다양한 구조의 사건 달력 객체를 list[dict]로 변환한다.

    지원:
    - list[dict]
    - dict[str, dict]
    - dict[str, list[dict]]
    - dict[str, list[str]]
    - pandas DataFrame
    """
    rows = []

    if isinstance(obj, pd.DataFrame):
        return obj.to_dict("records")

    if isinstance(obj, list):
        for i, item in enumerate(obj, start=1):
            if isinstance(item, dict):
                row = item.copy()
                row.setdefault("event_id", f"event_{i:03d}")
                rows.append(row)
            else:
                rows.append({
                    "event_id": f"event_{i:03d}",
                    "event_name": str(item),
                })
        return rows

    if isinstance(obj, dict):
        event_no = 1

        for key, value in obj.items():
            if isinstance(value, dict):
                row = value.copy()
                row.setdefault("event_id", str(key))
                row.setdefault("event_group", str(key))
                rows.append(row)
                event_no += 1

            elif isinstance(value, list):
                for j, item in enumerate(value, start=1):
                    if isinstance(item, dict):
                        row = item.copy()
                        row.setdefault("event_id", f"{key}_{j:03d}")
                        row.setdefault("event_group", str(key))
                        rows.append(row)
                    else:
                        rows.append({
                            "event_id": f"{key}_{j:03d}",
                            "event_group": str(key),
                            "event_name": str(item),
                        })
                    event_no += 1

            else:
                rows.append({
                    "event_id": f"event_{event_no:03d}",
                    "event_group": str(key),
                    "event_name": str(value),
                })
                event_no += 1

        return rows

    raise TypeError(f"지원하지 않는 사건 달력 객체 타입입니다: {type(obj)}")


def standardize_calendar(rows: list[dict], source_file: Path, variable_name: str) -> pd.DataFrame:
    df = pd.DataFrame(rows).copy()

    rename_candidates = {
        "name": "event_name",
        "title": "event_name",
        "event": "event_name",
        "start": "start_date",
        "start_dt": "start_date",
        "begin": "start_date",
        "end": "end_date",
        "end_dt": "end_date",
        "finish": "end_date",
        "date": "start_date",
        "type": "event_type",
        "category": "event_type",
        "description": "event_description",
        "note": "event_note",
    }

    for old, new in rename_candidates.items():
        if old in df.columns and new not in df.columns:
            df = df.rename(columns={old: new})

    if "event_id" not in df.columns:
        df.insert(0, "event_id", [f"event_{i:03d}" for i in range(1, len(df) + 1)])

    if "event_name" not in df.columns:
        df["event_name"] = df["event_id"].astype(str)

    if "start_date" not in df.columns:
        df["start_date"] = pd.NaT

    if "end_date" not in df.columns:
        df["end_date"] = df["start_date"]

    df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
    df["end_date"] = pd.to_datetime(df["end_date"], errors="coerce")

    df["end_date"] = df["end_date"].fillna(df["start_date"])

    df["start_year_month"] = df["start_date"].dt.to_period("M").astype(str)
    df["end_year_month"] = df["end_date"].dt.to_period("M").astype(str)

    if "event_type" not in df.columns:
        df["event_type"] = "market_event"

    if "event_span_type" not in df.columns:
        df["event_span_type"] = np.where(
            df["start_year_month"] == df["end_year_month"],
            "point_or_single_month",
            "multi_month",
        )

    if "visual_priority" not in df.columns:
        df["visual_priority"] = 3

    if "use_in_report" not in df.columns:
        df["use_in_report"] = True

    if "strategy_input" not in df.columns:
        df["strategy_input"] = False

    if "data_available_flag" not in df.columns:
        df["data_available_flag"] = df["start_date"] >= pd.to_datetime(cfg.DATA_START_DATE)

    if "backtest_flag" not in df.columns:
        df["backtest_flag"] = df["data_available_flag"]

    df["source_file"] = str(source_file)
    df["source_variable"] = variable_name
    df["calendar_role"] = "post_hoc_interpretation_only"

    preferred_cols = [
        "event_id",
        "event_name",
        "event_group",
        "event_type",
        "start_date",
        "end_date",
        "start_year_month",
        "end_year_month",
        "event_span_type",
        "visual_priority",
        "use_in_report",
        "strategy_input",
        "data_available_flag",
        "backtest_flag",
        "calendar_role",
        "event_description",
        "event_note",
        "source_file",
        "source_variable",
    ]

    for col in preferred_cols:
        if col not in df.columns:
            df[col] = ""

    remaining = [c for c in df.columns if c not in preferred_cols]
    df = df[preferred_cols + remaining]

    df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    df["end_date"] = pd.to_datetime(df["end_date"], errors="coerce").dt.strftime("%Y-%m-%d")

    df = df.sort_values(["start_date", "event_id"]).reset_index(drop=True)

    return df


def build_quality_check(calendar: pd.DataFrame, source_file: Path, variable_name: str) -> pd.DataFrame:
    rows = []

    rows.append({
        "item": "source_file",
        "value": str(source_file),
        "status": "OK" if source_file.exists() else "MISSING",
        "note": "외부 사건 달력 원천 파일",
    })

    rows.append({
        "item": "source_variable",
        "value": variable_name,
        "status": "OK",
        "note": "불러온 사건 달력 변수명",
    })

    rows.append({
        "item": "event_rows",
        "value": len(calendar),
        "status": "OK" if len(calendar) > 0 else "CHECK",
        "note": "표준화된 사건 수",
    })

    rows.append({
        "item": "missing_start_date",
        "value": int(calendar["start_date"].isna().sum() + (calendar["start_date"] == "NaT").sum()),
        "status": "OK" if not ((calendar["start_date"].isna()) | (calendar["start_date"] == "NaT")).any() else "CHECK",
        "note": "start_date 누락 여부",
    })

    rows.append({
        "item": "strategy_input_false_count",
        "value": int((calendar["strategy_input"] == False).sum()),
        "status": "OK" if (calendar["strategy_input"] == False).all() else "CHECK",
        "note": "시장 사건 달력은 전략 입력이 아니어야 함",
    })

    rows.append({
        "item": "data_available_events",
        "value": int(calendar["data_available_flag"].astype(bool).sum()),
        "status": "OK",
        "note": f"{cfg.DATA_START_DATE} 이후 사건 수",
    })

    return pd.DataFrame(rows)


def build_note(calendar: pd.DataFrame, quality: pd.DataFrame) -> str:
    lines = []

    lines.append("# main_final 외부 시장 사건 달력 표준화 노트")
    lines.append("")
    lines.append(f"- 생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## 1. 목적")
    lines.append("")
    lines.append(
        "이 단계는 외부 시장 사건 달력을 표준 CSV로 변환한다. "
        "시장 사건 달력은 HSI 계산이나 ETF 비중 결정에 직접 사용하지 않고, "
        "HSI 상태 산출 이후 주요 시장 사건 구간과 사후적으로 대조하는 해석·검증 자료로 사용한다."
    )
    lines.append("")
    lines.append("## 2. 원칙")
    lines.append("")
    lines.append("- strategy_input = False")
    lines.append("- calendar_role = post_hoc_interpretation_only")
    lines.append("- 50번대 파일은 사후 해석·시각화·위기구간 검증 레이어이다.")
    lines.append("")
    lines.append("## 3. 품질 점검")
    lines.append("")
    lines.append("| item | value | status | note |")
    lines.append("|---|---|---|---|")
    for _, row in quality.iterrows():
        lines.append(f"| {row['item']} | {row['value']} | {row['status']} | {row['note']} |")
    lines.append("")
    lines.append("## 4. 사건 수")
    lines.append("")
    lines.append(f"- 총 사건 수: {len(calendar)}")
    if "event_type" in calendar.columns:
        lines.append("")
        lines.append("| event_type | count |")
        lines.append("|---|---:|")
        for event_type, count in calendar["event_type"].value_counts().items():
            lines.append(f"| {event_type} | {count} |")
    lines.append("")
    lines.append("## 5. 다음 단계")
    lines.append("")
    lines.append(
        "`51_align_hsi_state_with_market_events.py`에서 HSI 상태표와 월 단위로 대조하고, "
        "`52_plot_event_annotated_hsi_timeline.py`에서 사건 주석이 들어간 HSI 타임라인을 만들 수 있다."
    )
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    print("=" * 80)
    print("50_build_market_event_calendar_table.py 실행 시작")
    print("=" * 80)

    cfg.ensure_final_directories()

    print("[1] 사건 달력 파일 선택")
    source_file = choose_calendar_file()
    print(f"    사용 파일: {source_file}")

    print("[2] Python 모듈 로드")
    module = load_python_module(source_file)
    variable_name, calendar_obj = find_calendar_object(module)
    print(f"    사용 변수: {variable_name}")

    print("[3] 사건 달력 객체 평탄화")
    rows = flatten_event_object(calendar_obj)
    print(f"    사건 rows = {len(rows)}")

    print("[4] 표준 캘린더 생성")
    calendar = standardize_calendar(rows, source_file, variable_name)

    save_csv(calendar, OUTPUT_REFERENCE_CALENDAR)
    save_csv(calendar, OUTPUT_MASTER_CALENDAR)

    print(f"    저장: {OUTPUT_REFERENCE_CALENDAR}")
    print(f"    저장: {OUTPUT_MASTER_CALENDAR}")

    print("[5] 품질 점검표 생성")
    quality = build_quality_check(calendar, source_file, variable_name)
    save_csv(quality, OUTPUT_QUALITY_CHECK)
    print(f"    저장: {OUTPUT_QUALITY_CHECK}")

    print("[6] Markdown 노트 저장")
    note = build_note(calendar, quality)
    OUTPUT_NOTE.write_text(note, encoding="utf-8")
    print(f"    저장: {OUTPUT_NOTE}")

    print("\n[품질 점검]")
    print(quality.to_string(index=False))

    print("\n[사건 달력 최근 20행]")
    preview_cols = [
        "event_id",
        "event_name",
        "event_type",
        "start_date",
        "end_date",
        "strategy_input",
        "calendar_role",
    ]
    preview_cols = [c for c in preview_cols if c in calendar.columns]
    print(calendar[preview_cols].tail(20).to_string(index=False))

    print("=" * 80)
    print("50_build_market_event_calendar_table.py 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()