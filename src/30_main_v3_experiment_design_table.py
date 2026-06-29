from pathlib import Path
from datetime import datetime

import pandas as pd


"""
30_main_v3_experiment_design_table.py

목적
----
main_v2 / main_v2b 기준선 실험 이후,
새로운 데이터 담당자 파일을 받아 main_v3 실험으로 넘어가기 전에
후속 실험 설계표를 만든다.

이 파일은 백테스트를 실행하지 않는다.
신호 조합 실험, 비중 Grid Search, Turnover 필터, 거래비용 단순화 가정,
Robustness 검증 계획을 표로 정리한다.

출력
----
output/tables/main_v3_signal_experiment_design.csv
output/tables/main_v3_weight_grid_design.csv
output/tables/main_v3_filter_criteria.csv
output/tables/main_v3_robustness_plan.csv
docs/main_v3_experiment_design_note.md
"""


# ============================================================
# 0. 경로 설정
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TABLE_DIR = PROJECT_ROOT / "output" / "tables"
DOCS_DIR = PROJECT_ROOT / "docs"

TABLE_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_SIGNAL_DESIGN = TABLE_DIR / "main_v3_signal_experiment_design.csv"
OUTPUT_WEIGHT_GRID = TABLE_DIR / "main_v3_weight_grid_design.csv"
OUTPUT_FILTER_CRITERIA = TABLE_DIR / "main_v3_filter_criteria.csv"
OUTPUT_ROBUSTNESS_PLAN = TABLE_DIR / "main_v3_robustness_plan.csv"
OUTPUT_NOTE = DOCS_DIR / "main_v3_experiment_design_note.md"


# ============================================================
# 1. 신호 조합 실험 설계
# ============================================================

def build_signal_experiment_design() -> pd.DataFrame:
    rows = [
        {
            "experiment_id": "main_v3_baseline",
            "experiment_name": "기준 HSI 5지표",
            "base_signals": (
                "ret_1m; momentum_13612w; sma10_gap; "
                "vol_3m; relative_strength_cash"
            ),
            "additional_signals": "",
            "fixed_allocation_rule": "main_v2b",
            "main_question": "기존 HSI 5지표와 main_v2b 비중 규칙의 기준 성과는 어떠한가?",
            "purpose": "후속 신호 확장 실험의 기준선",
            "status": "planned",
        },
        {
            "experiment_id": "main_v3a_trend",
            "experiment_name": "추세 보강 실험",
            "base_signals": (
                "ret_1m; momentum_13612w; sma10_gap; "
                "vol_3m; relative_strength_cash"
            ),
            "additional_signals": "ma20_gap; ma60_gap",
            "fixed_allocation_rule": "main_v2b",
            "main_question": "단기·중기 추세 정보를 추가하면 HSI 상태분류가 더 안정되는가?",
            "purpose": "추세 신호 보강 효과 확인",
            "status": "planned",
        },
        {
            "experiment_id": "main_v3b_risk_damage",
            "experiment_name": "위험강도·손상도 보강 실험",
            "base_signals": (
                "ret_1m; momentum_13612w; sma10_gap; "
                "vol_3m; relative_strength_cash"
            ),
            "additional_signals": "vol20; drawdown_60",
            "fixed_allocation_rule": "main_v2b",
            "main_question": "최근 변동성과 고점 대비 손상도를 추가하면 방어 신호가 더 명확해지는가?",
            "purpose": "위험 악화 상태 포착력 확인",
            "status": "planned",
        },
        {
            "experiment_id": "main_v3c_relative_strength",
            "experiment_name": "상대강도 보강 실험",
            "base_signals": (
                "ret_1m; momentum_13612w; sma10_gap; "
                "vol_3m; relative_strength_cash"
            ),
            "additional_signals": "risk_vs_cash_ret20",
            "fixed_allocation_rule": "main_v2b",
            "main_question": "위험자산이 현금성 자산보다 약해지는 구간을 HSI가 더 잘 포착하는가?",
            "purpose": "위험자산과 현금성 자산 간 상대 우위 확인",
            "status": "planned",
        },
        {
            "experiment_id": "main_v3d_core_signal_enhanced",
            "experiment_name": "통합 보강형 실험",
            "base_signals": (
                "ret_1m; momentum_13612w; sma10_gap; "
                "vol_3m; relative_strength_cash"
            ),
            "additional_signals": (
                "ma20_gap; ma60_gap; vol20; "
                "drawdown_60; risk_vs_cash_ret20"
            ),
            "fixed_allocation_rule": "main_v2b",
            "main_question": "추세·위험강도·손상도·상대강도를 모두 보강하면 HSI overlay가 개선되는가?",
            "purpose": "전체 확장 신호 조합의 종합 효과 확인",
            "status": "planned",
        },
    ]

    return pd.DataFrame(rows)


# ============================================================
# 2. 제한된 비중 Grid Search 설계
# ============================================================

def build_weight_grid_design() -> pd.DataFrame:
    rows = []

    risk_relief_candidates = [0.3333, 0.40]
    neutral_watch_candidates = [0.3333]
    conflict_candidates = [0.3333, 0.30]
    risk_warning_candidates = [0.25, 0.20, 0.15]
    accident_zone_candidates = [0.15, 0.10, 0.05]

    grid_id = 0

    for risk_relief in risk_relief_candidates:
        for neutral_watch in neutral_watch_candidates:
            for conflict in conflict_candidates:
                for risk_warning in risk_warning_candidates:
                    for accident_zone in accident_zone_candidates:
                        # 단조적 방어 조건:
                        # 상태가 나빠질수록 위험자산 비중이 커지면 안 됨.
                        monotonic_ok = (
                            risk_relief >= neutral_watch
                            and neutral_watch >= conflict
                            and conflict >= risk_warning
                            and risk_warning >= accident_zone
                        )

                        if not monotonic_ok:
                            continue

                        grid_id += 1

                        rows.append(
                            {
                                "grid_id": f"grid_{grid_id:03d}",
                                "risk_relief_weight": risk_relief,
                                "neutral_watch_weight": neutral_watch,
                                "conflict_weight": conflict,
                                "risk_warning_weight": risk_warning,
                                "accident_zone_weight": accident_zone,
                                "defensive_allocation_rule": (
                                    "위험자산 비중을 제외한 나머지를 "
                                    "114260과 153130에 50:50 배분"
                                ),
                                "monotonic_defense_check": "OK",
                                "note": (
                                    "HSI 상태가 나빠질수록 위험자산 비중이 "
                                    "커지지 않는 후보만 포함"
                                ),
                            }
                        )

    return pd.DataFrame(rows)


# ============================================================
# 3. 후보 필터 및 거래비용 단순화 가정
# ============================================================

def build_filter_criteria() -> pd.DataFrame:
    rows = [
        {
            "criteria_id": "filter_001",
            "criteria_name": "MDD 조건",
            "metric": "mdd",
            "rule": "EW 대비 MDD가 개선되거나 최소한 과도하게 악화되지 않을 것",
            "threshold": "mdd_diff_vs_ew >= 0 또는 허용범위 내",
            "purpose": "방어형 전략 목적 확인",
        },
        {
            "criteria_id": "filter_002",
            "criteria_name": "평균 Turnover 상한",
            "metric": "avg_turnover",
            "rule": "평균 Turnover가 예비 상한을 넘지 않을 것",
            "threshold": "avg_turnover <= 0.05",
            "purpose": "과도한 매매 방지",
        },
        {
            "criteria_id": "filter_003",
            "criteria_name": "최대 Turnover 상한",
            "metric": "max_turnover",
            "rule": "단일 리밸런싱 시점의 Turnover가 예비 상한을 넘지 않을 것",
            "threshold": "max_turnover <= 0.25",
            "purpose": "급격한 비중 변경 방지",
        },
        {
            "criteria_id": "filter_004",
            "criteria_name": "Sharpe / Calmar 조건",
            "metric": "sharpe; calmar",
            "rule": "위험 대비 성과가 과도하게 훼손되지 않을 것",
            "threshold": "EW 및 main_v2b 기준과 비교",
            "purpose": "수익률만으로 후보를 선택하지 않기",
        },
        {
            "criteria_id": "filter_005",
            "criteria_name": "거래비용 단순화 가정",
            "metric": "cost_adjusted_return",
            "rule": "Turnover에 팀 합의 비용률을 곱해 사후 평가",
            "threshold": "비용률은 팀 합의로 설정",
            "purpose": "실제 거래비용 정밀 추정이 아닌 백테스트 평가 방식의 합리적 단순화",
        },
        {
            "criteria_id": "filter_006",
            "criteria_name": "rank / zscore 일관성",
            "metric": "method_consistency",
            "rule": "특정 점수화 방식에서만 우연히 좋은 후보는 후순위",
            "threshold": "rank와 zscore 결과를 함께 확인",
            "purpose": "점수화 방식 의존성 확인",
        },
    ]

    return pd.DataFrame(rows)


# ============================================================
# 4. Robustness 검증 계획
# ============================================================

def build_robustness_plan() -> pd.DataFrame:
    rows = [
        {
            "robustness_id": "robust_001",
            "test_name": "기간 분할 검증",
            "input_candidate": "Grid Search 통과 후보",
            "test_condition": "초반 / 중반 / 후반 구간 분할",
            "main_question": "특정 기간에만 우연히 좋은 결과인가?",
            "expected_output": "main_v3_robustness_period_results.csv",
        },
        {
            "robustness_id": "robust_002",
            "test_name": "위기구간 검증",
            "input_candidate": "Grid Search 통과 후보",
            "test_condition": "큰 하락 또는 변동성 확대 구간",
            "main_question": "위기구간에서 방어 효과가 유지되는가?",
            "expected_output": "main_v3_robustness_crisis_results.csv",
        },
        {
            "robustness_id": "robust_003",
            "test_name": "거래비용 민감도 검증",
            "input_candidate": "Grid Search 통과 후보",
            "test_condition": "팀 합의 비용률 시나리오",
            "main_question": "비용률을 반영해도 결과가 크게 무너지지 않는가?",
            "expected_output": "main_v3_transaction_cost_sensitivity.csv",
        },
        {
            "robustness_id": "robust_004",
            "test_name": "주변 파라미터 민감도 검증",
            "input_candidate": "최종 후보 주변 비중 조합",
            "test_condition": "인접한 위험자산 비중 후보",
            "main_question": "후보 주변 값에서도 결과가 급격히 나빠지지 않는가?",
            "expected_output": "main_v3_local_parameter_robustness.csv",
        },
        {
            "robustness_id": "robust_005",
            "test_name": "rank / zscore 비교 검증",
            "input_candidate": "최종 후보",
            "test_condition": "rank 기본, zscore 보조",
            "main_question": "특정 점수화 방식에만 의존한 결과인가?",
            "expected_output": "main_v3_method_consistency_check.csv",
        },
    ]

    return pd.DataFrame(rows)


# ============================================================
# 5. Markdown 노트 생성
# ============================================================

def make_markdown_note(
    signal_design: pd.DataFrame,
    weight_grid: pd.DataFrame,
    filter_criteria: pd.DataFrame,
    robustness_plan: pd.DataFrame,
) -> str:
    lines = []

    lines.append("# main_v3 후속 실험 설계 노트")
    lines.append("")
    lines.append(f"- 생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## 1. 현재 위치")
    lines.append("")
    lines.append(
        "main_v2 / main_v2b 기준선 실험과 본문용 시각화는 완료되었다. "
        "후속 실험에서는 새로운 데이터 담당자 파일을 받기 전에, "
        "어떤 실험을 어떤 기준으로 진행할지 먼저 설계표로 고정한다."
    )
    lines.append("")
    lines.append("## 2. 기준선")
    lines.append("")
    lines.append("- 기준 비중 규칙: `main_v2b`")
    lines.append("- 기준 신호 조합: 기존 HSI 5지표")
    lines.append("- 기본 점수화 방식: rank")
    lines.append("- 보조 비교 방식: zscore")
    lines.append("")
    lines.append("`main_v2b`는 `conflict` 상태를 즉시 방어전환으로 보지 않고 관찰 상태로 처리하는 규칙이다.")
    lines.append("")
    lines.append("## 3. 신호 조합 실험")
    lines.append("")
    lines.append("신호 조합 실험에서는 비중 규칙을 `main_v2b`로 고정하고, 신호 조합만 바꾼다.")
    lines.append("")
    lines.append("| 실험명 | 추가 신호 | 질문 |")
    lines.append("|---|---|---|")

    for _, row in signal_design.iterrows():
        additional = row["additional_signals"] if row["additional_signals"] else "없음"
        lines.append(
            f"| `{row['experiment_id']}` | {additional} | {row['main_question']} |"
        )

    lines.append("")
    lines.append("## 4. 제한된 비중 Grid Search")
    lines.append("")
    lines.append(
        f"단조적 방어 조건을 만족하는 비중 후보는 총 {len(weight_grid)}개이다. "
        "상태가 나빠질수록 위험자산 비중이 커지지 않는 후보만 포함한다."
    )
    lines.append("")
    lines.append("위험자산 비중을 제외한 나머지는 114260과 153130에 50:50으로 배분한다.")
    lines.append("")
    lines.append("## 5. Turnover와 거래비용")
    lines.append("")
    lines.append(
        "Turnover 상한은 성과가 좋아 보이더라도 과도한 매매를 유발하는 후보를 "
        "제외하거나 후순위로 두기 위한 안정성 필터이다."
    )
    lines.append("")
    lines.append("- 예비 평균 Turnover 상한: `avg_turnover <= 0.05`")
    lines.append("- 예비 최대 Turnover 상한: `max_turnover <= 0.25`")
    lines.append("")
    lines.append(
        "거래비용은 실제 ETF 거래비용을 정밀 추정하는 것이 아니라, "
        "백테스트 평가 방식으로서 합리적인 단순화 가정으로 처리한다."
    )
    lines.append("")
    lines.append("## 6. Robustness 검증")
    lines.append("")
    lines.append("| 검증 | 질문 |")
    lines.append("|---|---|")

    for _, row in robustness_plan.iterrows():
        lines.append(f"| {row['test_name']} | {row['main_question']} |")

    lines.append("")
    lines.append("## 7. 최종 판단 원칙")
    lines.append("")
    lines.append(
        "최종 후보는 수익률 1등 조합이 아니라, HSI 상태 해석이 유지되고, "
        "MDD와 Drawdown 측면의 위험관리 효과가 있으며, "
        "Turnover가 과도하지 않고, Robustness 검증에서도 크게 무너지지 않는 조합으로 판단한다."
    )
    lines.append("")

    return "\n".join(lines)


# ============================================================
# 6. 실행
# ============================================================

def main() -> None:
    print("=" * 70)
    print("30_main_v3_experiment_design_table.py 실행 시작")
    print("=" * 70)

    signal_design = build_signal_experiment_design()
    weight_grid = build_weight_grid_design()
    filter_criteria = build_filter_criteria()
    robustness_plan = build_robustness_plan()

    signal_design.to_csv(OUTPUT_SIGNAL_DESIGN, index=False, encoding="utf-8-sig")
    weight_grid.to_csv(OUTPUT_WEIGHT_GRID, index=False, encoding="utf-8-sig")
    filter_criteria.to_csv(OUTPUT_FILTER_CRITERIA, index=False, encoding="utf-8-sig")
    robustness_plan.to_csv(OUTPUT_ROBUSTNESS_PLAN, index=False, encoding="utf-8-sig")

    note = make_markdown_note(
        signal_design=signal_design,
        weight_grid=weight_grid,
        filter_criteria=filter_criteria,
        robustness_plan=robustness_plan,
    )
    OUTPUT_NOTE.write_text(note, encoding="utf-8")

    print("[저장 완료]")
    print(f"- {OUTPUT_SIGNAL_DESIGN}")
    print(f"- {OUTPUT_WEIGHT_GRID}")
    print(f"- {OUTPUT_FILTER_CRITERIA}")
    print(f"- {OUTPUT_ROBUSTNESS_PLAN}")
    print(f"- {OUTPUT_NOTE}")

    print("\n[신호 조합 실험 설계]")
    print(signal_design[["experiment_id", "experiment_name", "additional_signals", "fixed_allocation_rule"]])

    print("\n[비중 Grid 후보 수]")
    print(f"- {len(weight_grid)}개")

    print("\n[필터 기준]")
    print(filter_criteria[["criteria_name", "metric", "threshold"]])

    print("\n[Robustness 계획]")
    print(robustness_plan[["test_name", "main_question"]])

    print("\n" + "=" * 70)
    print("30_main_v3_experiment_design_table.py 실행 완료")
    print("=" * 70)


if __name__ == "__main__":
    main()