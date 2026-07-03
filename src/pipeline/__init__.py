"""
HSI Overlay 새 파이프라인 패키지.

hsi_report_artifacts/reports/ 의 최종 00~17 · 20~23 실험 흐름을 단계 모듈로 재구성한다.
공통 로직은 src/common(경로/설정/IO/성과지표/백테스트)을 재사용한다.

단계
----
- stage_a_data        : 00~01 데이터 기준 정리
- stage_b_hsi         : 02~05 HSI 신호·5상태·baseline
- stage_c_diagnostics : 06~09 진단 보조 layer
- stage_d_lambda      : 10~11 Lambda 부분조정 overlay        (핵심 로직 구현)
- stage_e_macro       : 12~15 Macro companion/soft overlay
- stage_f_robustness  : 16   regime robustness
- stage_g_benchmark   : 17   Fixed 70/20/10 benchmark alignment (구현)
- stage_selection     : 20~23 Turnover/거래비용/성과 기준 최종 후보 선별 (구현)

구현 상태: run.py 의 STAGES 표 참고.
"""
