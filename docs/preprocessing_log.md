# HSI 데이터 전처리 로그

- 생성 시각: 2026-06-30 13:03:48
- 처리 단계: 10건 / 제외 항목: 4건

## 1. 데이터 처리 과정

| 순번 | 시각 | 처리 내용 |
|---:|:---|:---|
| 1 | 13:03:48 | ETF 선정 완료: 후보 5종목 중 3종목 선정 |
| 2 | 13:03:51 | 가격 데이터 로드: 3487일 × 3종목 (시작 2012-03-07, ffill 적용) |
| 3 | 13:03:51 | 상장일·데이터 기간 점검 완료 |
| 4 | 13:03:51 | 결측치 점검 완료: 총 결측 0건 (load_price_data 내 ffill 처리) |
| 5 | 13:03:52 | 거래량·거래대금 유동성 점검 완료 |
| 6 | 13:03:52 | 월말 가격표·월간 수익률표(pct/decimal) 리샘플링 완료 |
| 7 | 13:03:52 | 기본 입력 신호 6종 계산 완료 (ret_1m=21d, ret_3m=63d, ma_gap=MA60, vol=20d, rs=21d, benchmark=069500) |
| 8 | 13:03:52 | 확장 입력 신호 5종 계산 완료 (ret_6m=126d, ret_12m=252d, drawdown=MAX60d, shock=|<-3%|×60d, defensive_rs vs 153130) |
| 9 | 13:03:52 | HSI 표준화 점수·direction/intensity 산출 완료 |
| 10 | 13:03:58 | 산출물 합본 저장: C:\quant_lec\quant_model\day5\day5_hsi_dynamic_allocation_project\AIQuant-2nd-project\output\tables\hsi_data_bundle.xlsx (18개 시트) |

## 2. 제외 / 미선정 사유

| ticker | name | 제외·미선정 사유 |
|:---|:---|:---|
| 148020 | KOSEF 국고채10년 | 자산군 내 HSI 커버리지 점수 열위로 미선정 |
| 395160 | TIGER KOFR금리액티브(합성) | 데이터 연수 부족(4년 < 기준 10년) |
| 069500 | KODEX 200 | 데이터 기간 점검: 시작 9년 이상 지연 |
| 114260 | KODEX 국고채3년 | 데이터 기간 점검: 시작 2년 이상 지연 |

## 3. 비고

- 산출물은 hsi_data_bundle.xlsx 하나로 합본 (표별 시트 분리)
- Grid Search / Robustness / Turnover·거래비용 / 백테스트는 후속 파트에서 완료
