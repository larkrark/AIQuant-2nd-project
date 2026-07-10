# HSI 프로젝트 최종 진단표 모음

## 1. 실험별 역할·입출력·검증 진단표

| 실험 | 역할 | 주요 입력 | 주요 출력 | 검증한 것 | 최종 판단 |
|---|---|---|---|---|---|
| 00 | 프로젝트 기준 고정 | config, data bundle, ETF 정의 | 기준 점검 문서 | 경로, 티커, 수익률 단위, 실험 역할 | 통과 |
| 01 | 데이터 구조화 | hsi_data_bundle.xlsx | processed CSV | 월말 가격, 수익률 단위, ETF 유니버스 | 통과 |
| 02 | event balance 생성 | HSI 입력 신호 | event_balance table | 위험/완화 사건 누적 흐름 | 보조 진단 |
| 03 | 월말 신호 정렬 | HSI signal, returns | monthly signal input | 월말 신호 → 다음 달 수익률 | 통과 |
| 04 | HSI 5상태 분류 | direction, intensity, conflict | HSI state5 table | 시장상태 label 생성 | 핵심 구조 |
| 05 | baseline 백테스트 | HSI state, monthly returns | baseline weights/timeseries | HSI 상태→ETF 비중 연결 | 내부 기준선 |
| 06 | 상대속도 진단 | HSI 신호 변화량 | relative speed table | 신호 반응 속도 | 보조 진단 |
| 07 | 신호 조합 비교 | signal combos | combo backtest summary | 특정 신호 의존도 | ablation |
| 08 | event balance 정합성 | HSI state, event balance | state/event diagnostic | HSI 상태와 내부 사건 흐름 | 보조 진단 |
| 09 | event filter | baseline weights, event balance | event filter backtest | 사건균형 보조 필터 효과 | 보조 후보 |
| 10 | λ 부분조정 | baseline target weights, returns | lambda family | 비중 전환 속도 효과 | 핵심 개선 |
| 11 | θ 민감도 | HSI score, θ values | theta sensitivity | 상태분류 민감도 | robustness |
| 12 | macro companion | rate, FX, GDP | macro features | macro 보조 환경 | 보조 layer |
| 13 | HSI×macro diagnostic | HSI state, macro features | overlap summary | HSI 위험과 macro 위험 겹침 | 14번 근거 |
| 14 | macro overlay no GDP | baseline weights, macro | macro overlay results | GDP 제외 macro 보정 효과 | 후속 후보 |
| 15 | Lambda + macro overlay | Lambda candidates, macro | macro sensitivity | macro_scale trade-off | 후속 진단 |
| 16 | regime robustness | Lambda 0.1/0.3, returns | period/state/tail tables | 최종 후보 robustness | 검증 통과, 역할 분리 |
| 17 | benchmark alignment | Fixed BM, EW, Lambda | BM alignment tables | 메인·보조 BM 정렬 | 보강 완료 |
| 20·21·23 | 최종 후보표·그림 | candidate outputs | report tables/figures | 후보 압축, 비용, 시각화 | 보고서 기준 |
| 50번대 | 시장 사건 달력 | external event calendar | event annotation | 사후 해석 | 전략 입력 아님 |

## 2. 검증 수행 범위와 한계표

| 검증 항목 | 수행 여부 | 관련 실험 | 현재 판단 | 보강 필요성 |
|---|---|---|---|---|
| 데이터 기준 고정 | 수행 | 00~01 | 최종 번들, ETF 유니버스, 수익률 단위 구분 | 낮음 |
| 수익률 단위 점검 | 수행 | 01, 05 이후 | decimal/pct 혼동 위험 관리 | 낮음 |
| 월말 리밸런싱 시점 정합성 | 수행 | 03, 05, 16, 17 | 월말 신호 → 다음 달 수익률 | 중간 |
| HSI 상태분류 | 수행 | 04 | 5상태 생성 완료 | 낮음 |
| baseline 검증 | 수행 | 05 | 상태→비중 연결 확인 | 낮음 |
| λ 민감도 | 수행 | 10, 16 | Lambda 0.1 / 0.3 역할 분리 | 낮음 |
| θ 민감도 | 수행 | 11 | 상태분류 민감도 점검 | 중간 |
| macro overlay | 수행 | 14, 15 | 최종 후보를 뒤집지 못함 | 낮음 |
| 기간분할 robustness | 수행 | 16, 17 | 4개 구간 비교 | 낮음 |
| HSI 상태별 조건부 진단 | 수행 | 16, 17 | 상태별 평균 월수익률 확인 | 중간 |
| 큰 손실월 진단 | 수행 | 16, 17 | 069500 하위 10% 손실월 확인 | 낮음 |
| 메인 BM 정렬 | 보강 완료 | 17 | Fixed 70/20/10 BM 추가 | 낮음 |
| 보조 BM 비교 | 수행 | 16, 17 | EW Benchmark 유지 | 낮음 |
| 거래비용 민감도 | 수행 | 15, 20, 23 | 단순 비용 민감도 | 중간 |
| 실제 체결비용·세금 | 미수행 | 없음 | 상용 운용 수준은 아님 | 높음 |
| walk-forward 검증 | 미수행 | 없음 | 후속 필요 | 높음 |
| 독립 holdout 검증 | 미수행 | 없음 | 후속 필요 | 높음 |
| Monte Carlo / bootstrap | 미수행 | 없음 | 선택적 후속 | 중간 |

## 3. 후속 실험·실제 시연 계획표

| 후속 과제 | 필요 이유 | 우선순위 |
|---|---|---:|
| walk-forward 검증 | 후보 선택 구간과 평가 구간을 분리하기 위해 필요 | 높음 |
| 독립 holdout 검증 | 전체 기간에 맞춘 결과인지 확인하기 위해 필요 | 높음 |
| 실제 거래비용·세금·슬리피지 반영 | 실제 운용 가능성을 보수적으로 평가하기 위해 필요 | 높음 |
| 월말 리밸런싱 시연 대시보드 | 실제 사용자가 월말에 어떤 비중을 받는지 보여주기 위해 필요 | 중간 |
| 위험성향별 포트폴리오 확장 | 보수형, 중립형, 적극형 RoboAdvisor로 확장 가능 | 중간 |
| 외부 BM 추가 검토 | KOSPI200 단독, 채권혼합형 BM 등 추가 비교 가능 | 중간 |
