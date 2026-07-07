"""
새 파이프라인 오케스트레이션.

단계 지도/구현 상태 출력용 진입점.
    cd src && python3 -m pipeline.run
"""

from dataclasses import dataclass


@dataclass
class Stage:
    key: str
    exp_range: str
    title: str
    status: str  # 구현 | 부분구현 | 스텁


STAGES = [
    Stage("stage_a_data", "00~01", "데이터 기준 정리", "스텁"),
    Stage("stage_b_hsi", "02~05", "HSI 신호·5상태·baseline", "스텁"),
    Stage("stage_c_diagnostics", "06~09", "진단 보조 layer", "스텁"),
    Stage("stage_d_lambda", "10~11", "Lambda 부분조정 overlay", "구현"),
    Stage("stage_e_macro", "12~15", "Macro companion/soft overlay", "스텁"),
    Stage("stage_f_robustness", "16", "Regime robustness", "스텁"),
    Stage("stage_g_benchmark", "17", "Benchmark alignment(Fixed 70/20/10)", "구현"),
    Stage("stage_factor", "RA팩터", "팩터 로딩 분석(β·t-stat·VIF·rolling)", "구현"),
    Stage("stage_attribution", "RA기여", "성과 기여도 분해(SAA·타이밍·λ·비용)", "구현"),
    Stage("stage_selection", "20~23", "최종 후보 선별(비용·Turnover)", "구현"),
]


def print_pipeline_map() -> None:
    print("=" * 76)
    print("HSI Overlay 새 파이프라인 (src/pipeline) — 단계 지도")
    print("=" * 76)
    print(f"{'단계':<20}{'실험':<8}{'상태':<8}제목")
    print("-" * 76)
    for s in STAGES:
        print(f"{s.key:<20}{s.exp_range:<8}{s.status:<8}{s.title}")
    print("-" * 76)
    done = sum(s.status != "스텁" for s in STAGES)
    print(f"구현/부분구현 {done} / 전체 {len(STAGES)} 단계")
    print("공통 기반: src/common | 과거 코드: src/legacy | 참고: docs/reports")
    print("스텁 단계 실행에는 리포트가 참조하는 main_final_* 입력 데이터가 필요(현재 repo에 없음).")
    print("=" * 76)


if __name__ == "__main__":
    print_pipeline_map()
