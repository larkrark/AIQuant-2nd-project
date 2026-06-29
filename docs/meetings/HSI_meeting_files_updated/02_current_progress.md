# 02. 현재까지 진행상황

현재 단계는 전체 전략 성과를 확정한 단계가 아니라, **HSI 입력 데이터 생성 및 분위수/z-score 신호 산출 예비 실행 결과**로 보는 것이 적절하다.

예비 ETF 3종을 대상으로 `daily_prices.csv`, `monthly_prices.csv`, `monthly_returns.csv`, `hsi_summary_rank.csv`, `hsi_summary_zscore.csv`가 생성되는 것을 확인하였다.

다만 현재 결과는 전체 ETF 유니버스 기준이 아니라 **3개 ETF 예비 유니버스 기준**이다.

## A. 프로젝트 방향

- [x] 프로젝트 주제를 HSI 기반 ETF 방어형 자산배분 전략으로 정리했다.
- [x] HSI를 미래 수익률 예측모델이 아니라 시장상태 해석용 보조지표로 정리했다.
- [x] 개별기업 주식이 아니라 ETF 자산군 단위로 비중을 조정하는 전략으로 정리했다.
- [x] 기본 전략 위에 HSI를 얹는 overlay 구조로 설명할 수 있게 되었다.
- [x] 분위수 방식은 기본 실험 기준, z-score 방식은 비교용 보조 실험으로 유지하는 방향을 정리했다.
- [x] 현재 코드의 `buy / watch / caution` 라벨은 계산 결과 확인용 1차 라벨로 보고, 보고서와 정식 1차 테스트에서는 별도 HSI 상태 정의표로 재해석하는 방향을 검토하기로 했다.

## B. 코드 실행 및 저장 확인

| 항목 | 저장 파일 | 상태 |
|---|---|---|
| ETF 선정 결과 | `output/tables/selected_etf_universe.csv` | 완료 |
| 일별 가격 | `data/processed/daily_prices.csv` | 완료 |
| 월말 가격 | `data/processed/monthly_prices.csv` | 완료 |
| 월간 수익률 | `data/processed/monthly_returns.csv` | 완료 |
| 분위수 방식 HSI | `output/tables/hsi_summary_rank.csv` | 완료 |
| 분위수 방식 최근 스냅샷 | `output/tables/hsi_latest_snapshot_rank.csv` | 완료 |
| z-score 방식 HSI | `output/tables/hsi_summary_zscore.csv` | 완료 |
| z-score 방식 최근 스냅샷 | `output/tables/hsi_latest_snapshot_zscore.csv` | 완료 |

## C. 현재 코드 기준 진행상황

- [x] 데이터 담당자 모듈을 실행 가능하도록 최소 수정했다.
- [x] Spyder 환경에서 1차 실행을 확인했다.
- [x] VS Code `.venv` 환경에서 프로젝트 경로 인식과 저장을 확인했다.
- [x] `M` 월말 리샘플링 이슈를 확인했고, 현재 pandas 환경에서는 `ME` 기준이 필요함을 확인했다.
- [x] 일별 가격, 월말 가격, 월간 수익률, HSI 결과 저장까지 완료했다.
- [x] 분위수 방식과 z-score 방식의 HSI 결과가 모두 저장되어 비교 가능함을 확인했다.
- [x] `practice/hsi_indicator_generation_practice.ipynb`가 HSI 원신호, 상태명, 사건지표를 실험한 practice 노트북임을 확인했다.

## D. 저장된 주요 산출물

| 파일 | 의미 | 현재 판단 |
|---|---|---|
| `daily_prices.csv` | ETF별 일별 가격 데이터 | 정상 저장 |
| `monthly_prices.csv` | 월말 라벨 기준 마지막 관측 가격 | 정상 저장 |
| `monthly_returns.csv` | 월말 가격 기준 월간 수익률 | 정상 저장 |
| `hsi_summary_rank.csv` | 분위수 방식 일별 HSI 결과 | 정상 저장 |
| `hsi_summary_zscore.csv` | z-score 방식 일별 HSI 결과 | 정상 저장 |

## E. 아직 최종 완료로 보면 안 되는 부분

- [ ] 현재 Grid Search는 예비 점검용이다.
- [ ] 최종 Grid Search는 백테스트 성과지표와 연결해야 한다.
- [ ] HSI 상태 분류와 비중 조정 규칙은 아직 연결 전이다.
- [ ] 현재 코드의 `buy / watch / caution` 라벨을 프로젝트용 HSI 상태명으로 매핑하는 상태 정의표가 아직 필요하다.
- [ ] EW / RP / GMV / MDP 등 비교전략 백테스트는 아직 연결 전이다.
- [ ] 현재 결과는 전체 ETF 유니버스 기준이 아니라 3개 ETF 예비 유니버스 기준이다.
- [ ] 일별 HSI 신호를 월별 백테스트에 연결하는 방식은 회의에서 합의가 필요하다.

## F. 주의사항

`monthly_prices.csv`의 날짜 인덱스는 월말 날짜로 표시되지만, 값은 해당 월의 마지막 관측 가격을 사용한다. 예를 들어 `2026-06-30`으로 표시되어도 실제 마지막 거래일 가격이 반영될 수 있다.

현재 HSI 신호는 일별로 계산되어 있고, `monthly_returns.csv`는 월별 수익률이다. 따라서 백테스트에서는 일별 HSI 중 월말 HSI 상태를 추출한 뒤, 다음 달 ETF 수익률에 적용하는 방식으로 연결해야 한다.

초기 HSI 구간에서 `0.0 / watch`가 길게 나오는 부분은 충분한 rolling window가 확보되기 전의 예비 구간일 수 있다. 따라서 실제 상태 해석에서는 초기 구간을 제외하거나 `insufficient_data`로 구분하는 방안을 검토한다.

`buy / watch / caution`은 코드 실행 중 결과를 빠르게 확인하기 위한 1차 라벨로는 유용하다. 다만 HSI의 원래 의도는 단순 매매 판단이 아니라 위험 악화 신호와 위험 완화 신호의 방향, 강도, 충돌 정도를 함께 해석하는 시장상태 분류 체계이므로, 보고서와 정식 1차 테스트에서는 별도의 상태 정의표로 재해석하는 것이 적절하다.

## G. 현재 단계의 결론

현재 단계는 “전략 성과 검증 완료”가 아니라, **HSI 입력 데이터 생성 및 분위수/z-score 신호 산출 예비 실행 완료**로 정리하는 것이 적절하다.

다음 작업은 데이터 품질 점검, HSI 입력 원신호 정의, 분위수와 z-score 비교 시각화, 월말 HSI 상태 추출, HSI 상태 정의표 작성, EW+HSI 백테스트 순서로 진행한다.
