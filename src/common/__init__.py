"""
공통 모듈 패키지.

파이프라인 스크립트들이 중복으로 정의하던 경로/설정/입출력/시각화/성과지표/
백테스트 헬퍼를 한곳으로 모은 패키지입니다. 각 스크립트는 여기서 import 하여
동일한 구현을 공유합니다.

하위 모듈
--------
- paths   : 프로젝트 경로 상수 (PROJECT_ROOT, TABLE_DIR, ...)
- config  : 실험 공통 상수 (ASSETS, WEIGHT_COLS, INITIAL_CAPITAL, ...)
- io_utils: CSV 로더/세이버
- viz     : matplotlib 한글 폰트 설정
- metrics : 성과지표 계산
- backtest: 월말 상태 → 다음 달 수익률 정렬, turnover, 정렬 점검표
"""
