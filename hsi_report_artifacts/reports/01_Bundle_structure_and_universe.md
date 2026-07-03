# 01_Bundle_structure_and_universe

## 실험명
**01번 데이터 번들 로드와 입출력 구조 정리**

## 1. 목적

01번 단계의 목적은 데이터 담당자가 제공한 최종 번들을 후속 실험에서 사용할 수 있도록 구조화하는 것이다. 이 단계는 데이터를 새로 수집하는 단계가 아니라, 이미 정리된 번들의 시트와 컬럼을 확인하고 후속 실험의 기준 입력으로 분리하는 단계이다.

## 2. 입력 구조표

| 번호 | 입력 구분 | 파일명/객체 | 필수 컬럼 | 설명 | 다음 단계 | 상태 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | ETF 후보 정보 | etf_info.csv | ticker, name, asset_class, risk_group, listing_date, note | 실험 대상 ETF의 기본 정보 표. 후보 선정의 출발점. | ETF 유니버스 선정 | 제공 |
| 2 | ETF 선정 기준 | selection_criteria | min_data_years, reference_year, exclude_leverage, exclude_inverse, required_asset_classes | ETF 포함/제외 기준. 최소 사용기간·레버리지/인버스 제외 등. | 최종 ETF 유니버스 확정 | 제공 |
| 3 | 원천 가격 데이터 | korea_etf.csv / 개별 가격 파일 | Date, Open, High, Low, Close, Volume | ETF별 일별 가격. 월말 가격·월간 수익률·HSI 원신호의 기초. | 전처리 및 리샘플링 | 제공 |
| 4 | 전처리 가격 데이터 | monthly_prices.csv | Date, ETF별 월말 가격 컬럼 | 일별 데이터를 월말 기준으로 정리한 가격표. | 월간 수익률 계산 | 제공 |
| 5 | 월간 수익률 데이터 | monthly_returns.csv | Date, ETF별 월간 수익률 컬럼 | 백테스트 성과 계산에 쓰는 월간 수익률 데이터. | 신호 계산 / 성과 계산 | 제공 |
| 6 | 기준 자산 정보 | benchmark_info / 변수 | benchmark_ticker | 상대강도 계산 기준이 되는 ETF/시장지수 정보. | 상대강도 계산 | 제공 |
| 7 | HSI 기본 파라미터 | DEFAULT_PARAMS | ret_window, ma_window, momentum_window, vol_window, rs_window | HSI 5지표 계산에 필요한 기간 설정(기본형 기준값). | 입력 신호 계산 | 제공 |
| 8 | 확장 파라미터 | EXTENDED_PARAMS | ret_6m, ret_12m, ma_short_window, ma_mid_window, vol_short_window, drawdown_window, rs_short_window, shock_threshold | 확장 컬럼(ret_6m·ret_12m·drawdown·shock_count·defensive_rs) 계산 조건. | 확장 실험 | 제공 |
| 9 | 데이터 품질 점검 기준 | quality_rules | 결측치 허용 기준, 최소 관측기간, 거래량/거래대금 기준 | 데이터 사용 가능 여부 판단 기준(결측·기간·유동성). | 유니버스 정제 | 제공 |
| 10 | 자산군 분류 기준 | asset_class_rules | 주식형 / 채권형 / 금 / 달러 / 원자재 / 대체자산 등 | ETF를 자산군으로 묶는 기준(위험·방어 자산 구분). | 비중 조절 규칙 설계 | 제공 |
| 11 | 신호 방향 정의 | signal_direction_map.csv | signal_name, raw_direction, hsi_sign, interpretation | 각 입력 신호의 위험 악화/완화 방향 정의(부호 통일 근거). | HSI 점수화 / direction 계산 | 제공 |
| 12 | 점수화 방식 설정 | scaling_config | method, window, score_range, note | 원신호를 HSI 점수로 변환하는 방식(rank/z-score 비교). | HSI 점수화 비교 | 제공 |

## 3. 출력 구조표

| 번호 | 역할 그룹 | 출력 구분 | 주요 컬럼 | 의미 | 합본 시트 | 상태 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | ①ETF·자산군 | ETF 기본정보표 | ticker, name, asset_class, risk_group, listing_date, data_years, note | 실험 대상 ETF 후보·자산군·위험그룹 기본 정보. | etf_info | 산출 |
| 2 | ①ETF·자산군 | 자산군 분류표 | ticker, asset_class_kr, underlying_asset, role, risk_level, coverage_count, discussion_note | 자산군·추종자산·위험등급 분류와 분류 논의 항목. | asset_class | 산출 |
| 3 | ②가격·수익률 | 월말 가격표 | year_month, ticker, month_end_price | 리밸런싱 기준 월말 종가. | monthly_price | 산출 |
| 4 | ②가격·수익률 | 월간 수익률표 | year_month, ticker, monthly_return | 전략 성과 계산의 기본 입력(월간 수익률 %). | monthly_return | 산출 |
| 5 | ③HSI 입력신호 | HSI 입력 신호표(원신호) | ret_1m, ret_3m, ma_gap, momentum, volatility, relative_strength (+확장: ret_6m, ret_12m, drawdown, shock_count, defensive_rs) | HSI 계산 직전 단계의 원신호(부호 반전 전 실제값). | signal_inputs | 산출 |
| 6 | ④점수화 중간 | 지표 점수표(raw scores) | date, ticker, score_return/ma_pos/momentum/vol/rs (-10~+10) | 표준화·부호 통일 후 지표별 점수. | raw_scores | 산출 |
| 7 | ④점수화 중간 | HSI 방향 점수표 | date, ticker, direction (-1~+1) | 위험 악화/완화 방향성 점수. | hsi_direction | 산출 |
| 8 | ④점수화 중간 | HSI 상태 분류표 | date, ticker, signal (buy/watch/caution) | 방향 임계 기준 상태 라벨(3단계). | hsi_signal | 부분 |
| 9 | ④점수화 중간 | 신호 방향 정의표 | signal_name, raw_direction, hsi_sign, interpretation | 각 신호의 위험 악화/완화 방향 정의(부호 반전 근거). | signal_direction_map | 산출 |
| 10 | ⑤snapshot | HSI 최신 snapshot | ticker, date, direction, intensity, signal, score_* | 기준일 HSI 점수·상태 요약(빠른 확인용). | snapshot | 산출 |
| 11 | ⑥품질 점검 | 데이터 기간 점검표 | ticker, listing_date, data_start_actual, data_end, trading_days, status | 상장일 대비 실제 사용 가능 기간 확인. | data_period | 산출 |
| 12 | ⑥품질 점검 | 결측치 점검표 | ticker, total_rows, missing_count, missing_pct, ffill_applied | ETF별 결측치 현황·처리 방법. | missing_summary | 산출 |
| 13 | ⑥품질 점검 | 유동성 점검표 | ticker, avg_daily_volume, avg_daily_turnover_krw, overall_pass, status | 거래량·거래대금 기준 유동성 점검. | liquidity_check | 산출 |
| 14 | ⑥품질 점검 | 제외 사유표 | ticker, name, reason | 후보 미선정·제외 사유 기록. | exclusions | 산출 |

## 4. 월말 가격과 월간 수익률

| 항목 | 행 수 | 기간 |
|---|---:|---|
| monthly_price | 172 | 2012-03~2026-06 |
| monthly_return | 171 | 2012-04~2026-06 |

월말 가격은 ETF별 월말 기준 가격이며, 월간 수익률은 다음 단계에서 백테스트 계산용 단위로 변환하여 사용한다. 보고서에서는 수익률 단위를 반드시 구분한다.

수익률 단위(설명: percent와 decimal을 구분해야 한다. 예를 들어 2.5%는 표시용으로 2.5, 계산용 decimal로는 0.025이다.)

## 5. 신호 방향 정의

| 신호 | 원신호 방향 | HSI 부호 | 해석 |
| --- | --- | --- | --- |
| return | 높을수록 양호 | 반전(-) | 수익률↑ → 위험 완화 |
| ma_pos | MA 위=양호 | 반전(-) | 이동평균 상회 → 위험 완화 |
| momentum | 높을수록 양호 | 반전(-) | 모멘텀↑ → 위험 완화 |
| vol | 높을수록 위험 | 유지(+) | 변동성↑ → 위험 악화 |
| rs | 기준 대비 강함=양호 | 반전(-) | 상대강도↑ → 위험 완화 |

신호 방향 정의표는 HSI를 해석할 때 중요한 역할을 한다. 수익률, 이동평균 위치, 모멘텀처럼 높을수록 좋은 신호는 위험 완화 방향으로 반전하여 해석하고, 변동성처럼 높을수록 위험한 신호는 위험 악화 방향으로 해석한다.

## 6. 결론

01번 단계의 핵심은 입력과 출력의 구조를 문서화한 것이다. 이 구조가 있어야 이후 03번 신호 입력, 04번 HSI 상태분류, 05번 baseline 백테스트가 어떤 데이터를 받아 어떤 산출물을 만드는지 설명할 수 있다.
