from datetime import datetime
from pathlib import Path

import pandas as pd

import final_project_config as cfg


"""
00_final_project_config_check.py

목적
----
최종 프로젝트 기준을 확인하고 고정한다.

이 파일은 전략 실험을 실행하지 않는다.
대신 다음 항목을 점검한다.

1. 최종 데이터 담당 모듈 HSI_data_pipeline_0629_5.py 존재 여부
2. 최종 데이터 번들 hsi_data_bundle.xlsx 존재 여부
3. 필수 시트 존재 여부
4. 월간 수익률 단위 규칙
5. ETF 유니버스
6. 최종 baseline 리밸런싱 규칙
7. 사건균형지표, 상대속도, θ, λ, 외부 사건 달력의 역할 구분
8. docs/main_final_project_config_note.md 저장
"""


def read_bundle_sheet_names(bundle_path: Path) -> list[str]:
    """
    엑셀 번들의 시트명을 읽는다.
    """
    xls = pd.ExcelFile(bundle_path)
    return xls.sheet_names


def build_bundle_check(bundle_path: Path, sheet_names: list[str]) -> pd.DataFrame:
    """
    hsi_data_bundle.xlsx 필수 시트 존재 여부 점검표.
    """
    rows = []

    for sheet in cfg.REQUIRED_BUNDLE_SHEETS:
        rows.append({
            "check_group": "required_sheet",
            "item": sheet,
            "status": "OK" if sheet in sheet_names else "MISSING",
            "note": "hsi_data_bundle.xlsx 필수 시트",
        })

    for sheet in cfg.CORE_EXPERIMENT_SHEETS:
        rows.append({
            "check_group": "core_experiment_sheet",
            "item": sheet,
            "status": "OK" if sheet in sheet_names else "MISSING",
            "note": "후속 실험에서 직접 사용하는 핵심 시트",
        })

    rows.append({
        "check_group": "bundle_path",
        "item": str(bundle_path),
        "status": "OK" if bundle_path.exists() else "MISSING",
        "note": "후속 실험 기준 입력 번들",
    })

    rows.append({
        "check_group": "data_pipeline",
        "item": str(cfg.FINAL_DATA_PIPELINE_FILE),
        "status": "OK" if cfg.FINAL_DATA_PIPELINE_FILE.exists() else "MISSING",
        "note": "데이터 담당 최종 모듈",
    })

    rows.append({
        "check_group": "market_event_calendar",
        "item": str(cfg.SHOCK_CALENDAR_DRAFT),
        "status": "OK" if cfg.SHOCK_CALENDAR_DRAFT.exists() else "OPTIONAL_NOT_FOUND",
        "note": "외부 사건 달력 초안. 전략 입력 아님.",
    })

    rows.append({
        "check_group": "market_event_calendar",
        "item": str(cfg.MARKET_EVENT_CALENDAR_FILE),
        "status": "OK" if cfg.MARKET_EVENT_CALENDAR_FILE.exists() else "OPTIONAL_NOT_FOUND",
        "note": "최종 권장 외부 사건 달력 파일명. 50번대에서 정리 예정.",
    })

    return pd.DataFrame(rows)


def build_allocation_rule_table() -> pd.DataFrame:
    """
    최종 baseline 리밸런싱 규칙표 생성.
    """
    rows = []

    for state, rule in cfg.FINAL_BASELINE_ALLOCATION_RULES.items():
        rows.append({
            "allocation_rule_name": cfg.FINAL_ALLOCATION_RULE_NAME,
            "hsi_state": state,
            "state_kr": rule["state_kr"],
            cfg.RISK_TICKER: rule[cfg.RISK_TICKER],
            cfg.BOND_TICKER: rule[cfg.BOND_TICKER],
            cfg.CASH_TICKER: rule[cfg.CASH_TICKER],
            "risk_weight_pct": rule[cfg.RISK_TICKER] * 100,
            "bond_weight_pct": rule[cfg.BOND_TICKER] * 100,
            "cash_weight_pct": rule[cfg.CASH_TICKER] * 100,
            "rule_note": rule["rule_note"],
        })

    return pd.DataFrame(rows)


def build_pipeline_step_table() -> pd.DataFrame:
    """
    최종 00~11번 및 50번대 실행 흐름표 생성.
    """
    rows = []

    for i, (file_name, role) in enumerate(cfg.FINAL_PIPELINE_STEPS, start=0):
        rows.append({
            "pipeline_layer": "final_reproducible_pipeline",
            "step_no": i,
            "file_name": file_name,
            "role": role,
        })

    for file_name, role in cfg.MARKET_EVENT_PIPELINE_STEPS:
        step_no = int(file_name.split("_")[0])
        rows.append({
            "pipeline_layer": "market_event_calendar_layer",
            "step_no": step_no,
            "file_name": file_name,
            "role": role,
        })

    return pd.DataFrame(rows)


def build_bundle_sheet_map(bundle_path: Path, sheet_names: list[str]) -> pd.DataFrame:
    """
    hsi_data_bundle.xlsx 실제 시트별 행·열 수 요약표.
    """
    rows = []

    for sheet in sheet_names:
        try:
            df = pd.read_excel(bundle_path, sheet_name=sheet)
            rows.append({
                "sheet_name": sheet,
                "rows": len(df),
                "columns": len(df.columns),
                "status": "OK",
                "note": "읽기 성공",
            })
        except Exception as e:
            rows.append({
                "sheet_name": sheet,
                "rows": None,
                "columns": None,
                "status": "READ_ERROR",
                "note": str(e),
            })

    return pd.DataFrame(rows)


def build_config_note(
    bundle_path: Path,
    sheet_names: list[str],
    bundle_check: pd.DataFrame,
    allocation_rule: pd.DataFrame,
) -> str:
    """
    docs/main_final_project_config_note.md 내용 생성.
    """
    lines = []

    lines.append("# main_final 프로젝트 설정 노트")
    lines.append("")
    lines.append(f"- 생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## 1. 최종 기준 파일")
    lines.append("")
    lines.append(f"- 데이터 담당 최종 모듈: `{cfg.FINAL_DATA_PIPELINE_FILE}`")
    lines.append(f"- 후속 실험 기준 데이터 번들: `{bundle_path}`")
    lines.append("")
    lines.append("이제 후속 실험은 데이터를 다시 수집하기보다, 데이터 담당자 산출물인 `hsi_data_bundle.xlsx`를 기준 입력으로 사용한다.")
    lines.append("")
    lines.append("## 2. 최종 ETF 유니버스")
    lines.append("")
    lines.append("| ticker | name | role |")
    lines.append("|---|---|---|")
    for ticker in cfg.TICKERS:
        lines.append(
            f"| {ticker} | {cfg.TICKER_NAME_MAP[ticker]} | {cfg.TICKER_ROLE_MAP[ticker]} |"
        )
    lines.append("")
    lines.append("## 3. 수익률 단위 규칙")
    lines.append("")
    lines.append("- `monthly_return_decimal`: 백테스트 계산용 decimal 단위")
    lines.append("- `monthly_return_pct`: 사람이 확인하기 위한 percent 단위")
    lines.append("")
    lines.append("예시:")
    lines.append("")
    lines.append("```text")
    lines.append("2.5% → monthly_return_pct = 2.5")
    lines.append("2.5% → monthly_return_decimal = 0.025")
    lines.append("```")
    lines.append("")
    lines.append("## 4. hsi_data_bundle.xlsx 필수 시트 점검")
    lines.append("")
    lines.append("| sheet | status | note |")
    lines.append("|---|---|---|")
    req = bundle_check[bundle_check["check_group"] == "required_sheet"]
    for _, row in req.iterrows():
        lines.append(f"| {row['item']} | {row['status']} | {row['note']} |")
    lines.append("")
    lines.append("## 5. 최종 baseline 리밸런싱 규칙")
    lines.append("")
    lines.append(
        "리밸런싱 규칙은 HSI 상태분류 결과를 실제 ETF 목표 비중으로 변환하는 연결 규칙이다. "
        "HSI는 미래 수익률을 직접 예측하는 모델이 아니므로, 본 규칙은 시장상태에 따라 "
        "위험자산 노출을 확대하거나 축소하는 방어형 자산배분 규칙으로 설계한다."
    )
    lines.append("")
    lines.append("| HSI 상태 | 해석 | 069500 | 114260 | 153130 |")
    lines.append("|---|---|---:|---:|---:|")
    for _, row in allocation_rule.iterrows():
        lines.append(
            f"| {row['hsi_state']} | {row['state_kr']} | "
            f"{row[cfg.RISK_TICKER]:.0%} | "
            f"{row[cfg.BOND_TICKER]:.0%} | "
            f"{row[cfg.CASH_TICKER]:.0%} |"
        )
    lines.append("")
    lines.append("설계 원칙:")
    lines.append("")
    for key, value in cfg.REBALANCING_RULE_DESIGN_PRINCIPLES.items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## 6. 후속 실험의 역할 구분")
    lines.append("")
    lines.append(f"- 사건균형지표: {cfg.HSI_EVENT_BALANCE_ROLE}")
    lines.append(f"- 상대속도 실험: {cfg.RELATIVE_SPEED_ROLE}")
    lines.append(f"- θ 실험: {cfg.THETA_EXPERIMENT_ROLE}")
    lines.append(f"- λ 실험: {cfg.LAMBDA_EXPERIMENT_ROLE}")
    lines.append(f"- 외부 사건 달력: {cfg.MARKET_EVENT_CALENDAR_ROLE}")
    lines.append("")
    lines.append("## 7. 최종 실행 흐름")
    lines.append("")
    lines.append("```text")
    for file_name, role in cfg.FINAL_PIPELINE_STEPS:
        lines.append(f"{file_name}  # {role}")
    lines.append("")
    for file_name, role in cfg.MARKET_EVENT_PIPELINE_STEPS:
        lines.append(f"{file_name}  # {role}")
    lines.append("```")
    lines.append("")
    lines.append("## 8. 현재 발견된 번들 시트")
    lines.append("")
    lines.append("```text")
    for sheet in sheet_names:
        lines.append(sheet)
    lines.append("```")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    print("=" * 80)
    print("00_final_project_config_check.py 실행 시작")
    print("=" * 80)

    print("[1] 최종 폴더 구조 확인 및 생성")
    cfg.ensure_final_directories()
    print("    OK")

    print("[2] 최종 데이터 담당 모듈 확인")
    cfg.require_file(cfg.FINAL_DATA_PIPELINE_FILE, label="최종 데이터 담당 모듈")
    print(f"    OK: {cfg.FINAL_DATA_PIPELINE_FILE}")

    print("[3] hsi_data_bundle.xlsx 확인")
    bundle_path = cfg.find_data_bundle()
    print(f"    OK: {bundle_path}")

    print("[4] 번들 시트명 읽기")
    sheet_names = read_bundle_sheet_names(bundle_path)
    print(f"    OK: {len(sheet_names)}개 시트 발견")
    print("    " + ", ".join(sheet_names))

    print("[5] 필수 시트 점검")
    bundle_check = build_bundle_check(bundle_path, sheet_names)
    missing = bundle_check[bundle_check["status"] == "MISSING"]

    if missing.empty:
        print("    OK: 필수 시트 모두 존재")
    else:
        print("    CHECK: 누락 시트 있음")
        print(missing.to_string(index=False))

    print("[6] 번들 시트 맵 생성")
    sheet_map = build_bundle_sheet_map(bundle_path, sheet_names)
    sheet_map.to_csv(cfg.FINAL_BUNDLE_SHEET_MAP, index=False, encoding="utf-8-sig")
    print(f"    저장: {cfg.FINAL_BUNDLE_SHEET_MAP}")

    print("[7] 점검표 저장")
    bundle_check.to_csv(cfg.FINAL_BUNDLE_CHECK_TABLE, index=False, encoding="utf-8-sig")
    print(f"    저장: {cfg.FINAL_BUNDLE_CHECK_TABLE}")

    print("[8] 최종 baseline 리밸런싱 규칙표 저장")
    allocation_rule = build_allocation_rule_table()
    allocation_rule.to_csv(cfg.FINAL_ALLOCATION_RULE_TABLE, index=False, encoding="utf-8-sig")
    print(f"    저장: {cfg.FINAL_ALLOCATION_RULE_TABLE}")

    print("[9] 최종 실행 흐름표 저장")
    pipeline_steps = build_pipeline_step_table()
    pipeline_steps.to_csv(cfg.FINAL_PIPELINE_STEP_TABLE, index=False, encoding="utf-8-sig")
    print(f"    저장: {cfg.FINAL_PIPELINE_STEP_TABLE}")

    print("[10] 설정 노트 저장")
    note = build_config_note(
        bundle_path=bundle_path,
        sheet_names=sheet_names,
        bundle_check=bundle_check,
        allocation_rule=allocation_rule,
    )
    cfg.FINAL_CONFIG_NOTE.write_text(note, encoding="utf-8")
    print(f"    저장: {cfg.FINAL_CONFIG_NOTE}")

    print("[11] 설정 요약 출력")
    cfg.print_config_summary()

    print("\n[필수 시트 점검 요약]")
    print(bundle_check.to_string(index=False))

    print("\n[최종 baseline 리밸런싱 규칙]")
    print(allocation_rule.to_string(index=False))

    if not missing.empty:
        raise RuntimeError(
            "hsi_data_bundle.xlsx에 필수 시트가 누락되어 있습니다. "
            "위의 MISSING 항목을 확인하세요."
        )

    print("=" * 80)
    print("00_final_project_config_check.py 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()