"""
23_build_final_report_with_figure_layout.py

목적
- 22번에서 생성한 추가 그림까지 포함하여 결과보고서 최종 배치본을 만든다.
- 기존 보고서 초안의 "추가 권장 시각화" 메모를 실제 그림 배치 문단으로 정리한다.

입력 후보
1) docs/main_final_hsi_overlay_result_report_with_recommendations.md
2) docs/main_final_hsi_overlay_result_report.md

출력
- docs/main_final_hsi_overlay_result_report_with_figures.md

사용 예시
(.venv) PS ...> python src/23_build_final_report_with_figure_layout.py
"""

from __future__ import annotations

from pathlib import Path


# ============================================================
# 0. 경로 설정
# ============================================================

def find_project_root() -> Path:
    here = Path(__file__).resolve()

    if here.parent.name == "src":
        return here.parent.parent

    for p in [here.parent, *here.parents]:
        if (p / "docs").exists() or (p / "output").exists():
            return p

    return Path.cwd().resolve()


PROJECT_ROOT = find_project_root()
DOCS_DIR = PROJECT_ROOT / "docs"
OUTPUT_FIGURES = PROJECT_ROOT / "output" / "figures"

DOCS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FIGURES.mkdir(parents=True, exist_ok=True)


# ============================================================
# 1. 입출력 파일 선택
# ============================================================

INPUT_CANDIDATES = [
    DOCS_DIR / "reports" / "main_final_hsi_overlay_result_report_with_recommendations.md",
    DOCS_DIR / "reports" / "main_final_hsi_overlay_result_report.md",
]

OUTPUT_PATH = DOCS_DIR / "reports" / "main_final_hsi_overlay_result_report_with_figures.md"


def find_input_report() -> Path:
    for path in INPUT_CANDIDATES:
        if path.exists():
            return path

    raise FileNotFoundError(
        "결과보고서 입력 파일을 찾지 못했습니다.\n"
        + "\n".join(f" - {p}" for p in INPUT_CANDIDATES)
    )


# ============================================================
# 2. 그림 존재 여부 메모
# ============================================================

FIGURE_CHECKS = {
    "HSI 5상태 분포": OUTPUT_FIGURES / "main_final_report_hsi_state_distribution_bar.png",
    "누적수익률 비교": OUTPUT_FIGURES / "main_final_report_cumulative_comparison.png",
    "Drawdown 비교": OUTPUT_FIGURES / "main_final_report_drawdown_comparison.png",
    "λ별 성과와 Turnover 비교": OUTPUT_FIGURES / "main_final_report_lambda_family_comparison.png",
    "후보 판단 분포 도넛차트": OUTPUT_FIGURES / "main_final_report_candidate_decision_donut.png",
    "후보 판단 분포 막대바": OUTPUT_FIGURES / "main_final_report_candidate_decision_bar.png",
    "최종 후보 Turnover 비교": OUTPUT_FIGURES / "main_final_report_turnover_comparison.png",
    "거래비용 민감도 비교": OUTPUT_FIGURES / "main_final_report_cost_drag_comparison.png",
    "위험-수익 산점도": OUTPUT_FIGURES / "main_final_report_risk_return_scatter.png",
}


def make_figure_status_table() -> str:
    lines = [
        "## 부록 C. 그림 파일 생성 여부 점검",
        "",
        "| 그림 | 파일 | 상태 |",
        "|---|---|---|",
    ]

    for name, path in FIGURE_CHECKS.items():
        rel = path.relative_to(PROJECT_ROOT).as_posix()
        status = "생성 확인" if path.exists() else "아직 없음"
        lines.append(f"| {name} | `{rel}` | {status} |")

    lines.append("")
    return "\n".join(lines)


# ============================================================
# 3. 보고서 문단 치환
# ============================================================

def replace_state_distribution_section(text: str) -> str:
    old = """> 추가 권장 시각화: `main_final_hsi_state5_distribution.csv` 기반 HSI 5상태 분포 가로 막대바  
> 권장 파일명: `output/figures/main_final_report_hsi_state_distribution_bar.png`"""

    new = """#### 그림 1. HSI 5상태 분포

아래 그림은 HSI 상태가 전체 기간 동안 어떤 비율로 나타났는지 보여준다. 이 그림은 HSI가 어떤 시장상태를 주로 생성했는지 확인하기 위한 기초 자료이다.

![Fig 1. HSI 5상태 분포](../output/figures/main_final_report_hsi_state_distribution_bar.png)

그림에서 `risk_relief`가 가장 높은 비중을 차지하고, `conflict`는 매우 낮은 비중으로 나타난다. 이는 현재 상태분류 기준에서 위험 완화와 강한 위험 구간은 비교적 뚜렷하게 포착되지만, 신호 충돌 구간은 보수적으로 분류될 수 있음을 의미한다."""

    return text.replace(old, new)


def replace_candidate_decision_section(text: str) -> str:
    old = """> 추가 권장 시각화: 후보 판단 분포 도넛차트 또는 가로 막대바  
> 권장 파일명: `output/figures/main_final_report_candidate_decision_donut.png`"""

    new = """#### 그림 4. 후보 판단 분포

아래 그림은 전체 후보가 최종 선별 과정에서 어떻게 분류되었는지 보여준다.

![Fig 4. 후보 판단 분포](../output/figures/main_final_report_candidate_decision_donut.png)

후보 판단 분포를 보면 전체 후보 중 다수가 Turnover 기준에서 제외되었다. 이는 HSI 상태분류나 신호 조합 자체보다, 상태 변화가 포트폴리오 비중 변화로 이어지는 과정에서 회전율 관리가 중요하다는 점을 보여준다."""

    return text.replace(old, new)


def renumber_figures(text: str) -> str:
    """
    HSI 상태분포와 후보 판단 분포가 추가되면서 본문 그림 번호를 자연스럽게 다시 맞춘다.
    기존 보고서의 그림 문구만 교체하며, 경로는 유지한다.
    """
    replacements = {
        "### 그림 1. 누적수익률 비교": "### 그림 2. 누적수익률 비교",
        "![Fig 1. 누적수익률 비교]": "![Fig 2. 누적수익률 비교]",
        "### 그림 2. Drawdown 비교": "### 그림 3. Drawdown 비교",
        "![Fig 2. Drawdown 비교]": "![Fig 3. Drawdown 비교]",
        "### 그림 3. λ별 성과와 평균 Turnover 비교": "### 그림 5. λ별 성과와 평균 Turnover 비교",
        "![Fig 3. λ별 성과와 평균 Turnover 비교]": "![Fig 5. λ별 성과와 평균 Turnover 비교]",
        "### 그림 4. 최종 후보 Turnover 비교": "### 그림 6. 최종 후보 Turnover 비교",
        "![Fig 4. 최종 후보 Turnover 비교]": "![Fig 6. 최종 후보 Turnover 비교]",
        "### 그림 5. 거래비용 민감도 비교": "### 그림 7. 거래비용 민감도 비교",
        "![Fig 5. 거래비용 민감도 비교]": "![Fig 7. 거래비용 민감도 비교]",
        "### 그림 6. 위험-수익 산점도": "### 그림 8. 위험-수익 산점도",
        "![Fig 6. 위험-수익 산점도]": "![Fig 8. 위험-수익 산점도]",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def remove_recommendation_appendix(text: str) -> str:
    """
    with_recommendations 파일을 입력으로 쓸 경우, 부록 B의 작업지시 성격 문단은
    최종 배치본에서는 길어질 수 있어 간단한 완료 메모로 바꾼다.
    """
    start = text.find("\n## 부록 B. 추가 권장 시각화 및 보고서 보완 계획")
    end = text.find("\n## 부록. 주요 용어 정리")

    if start == -1 or end == -1 or end <= start:
        return text

    replacement = """
## 부록 B. 추가 시각화 반영 메모

본 보고서에는 21번에서 생성한 핵심 성과 그림과 22번에서 추가 생성한 권장 시각화를 함께 배치하였다.

추가 반영된 그림은 다음과 같다.

1. HSI 5상태 분포 가로 막대바  
   - `output/figures/main_final_report_hsi_state_distribution_bar.png`
2. 후보 판단 분포 도넛차트  
   - `output/figures/main_final_report_candidate_decision_donut.png`

두 그림은 각각 HSI 상태분류 구조와 최종 후보 선별 기준을 설명하는 위치에 배치하였다.
"""

    return text[:start] + "\n" + replacement + "\n" + text[end:]


def add_final_figure_status(text: str) -> str:
    status_table = make_figure_status_table()

    if "## 부록 C. 그림 파일 생성 여부 점검" in text:
        return text

    marker = "\n## 부록. 주요 용어 정리"
    if marker in text:
        return text.replace(marker, "\n" + status_table + "\n" + marker, 1)

    return text + "\n\n---\n\n" + status_table


# ============================================================
# 4. 메인
# ============================================================

def main() -> None:
    print("=" * 80)
    print("23_build_final_report_with_figure_layout.py 실행 시작")
    print("=" * 80)

    input_path = find_input_report()
    print(f"[1] 입력 보고서: {input_path}")

    text = input_path.read_text(encoding="utf-8")

    print("[2] 추가 그림 배치 문단 반영")
    text = replace_state_distribution_section(text)
    text = replace_candidate_decision_section(text)

    print("[3] 그림 번호 재정리")
    text = renumber_figures(text)

    print("[4] 권장사항 부록 정리")
    text = remove_recommendation_appendix(text)

    print("[5] 그림 파일 점검표 추가")
    text = add_final_figure_status(text)

    OUTPUT_PATH.write_text(text, encoding="utf-8")
    print(f"[6] 저장: {OUTPUT_PATH}")

    print("\n[그림 파일 확인]")
    for name, path in FIGURE_CHECKS.items():
        status = "OK" if path.exists() else "MISSING"
        print(f"  {status:7s} {name}: {path.name}")

    print("=" * 80)
    print("23_build_final_report_with_figure_layout.py 실행 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()
