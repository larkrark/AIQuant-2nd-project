# main_v3 데이터 파이프라인 연결 점검 노트

- 생성 시각: 2026-06-29 23:16:21

## 1. 목적

이 노트는 데이터 담당 조원님의 HSI 데이터 파이프라인 결과를 우리 프로젝트의 main_v3 후속 실험 구조에 연결할 수 있는지 확인하기 위해 작성되었다.

현재 단계에서는 Grid Search, 비중 규칙 최적화, Robustness 검증을 실행하지 않는다.

## 2. 생성된 주요 입력데이터

- `data/processed/selected_etf_universe.csv`
- `data/processed/asset_class_map.csv`
- `data/processed/monthly_prices.csv`
- `data/processed/monthly_returns.csv`
- `data/processed/hsi_signal_snapshot.csv`
- `data/processed/hsi_raw_scores.csv`

## 3. ETF 유니버스

| ticker | name | asset_class | underlying_asset | risk_group |
|---|---|---|---|---|
| 069500 | KODEX 200 | equity | 주식형 | high |
| 114260 | KODEX 국고채3년 | bond | 채권형 | low |
| 153130 | KODEX 단기채권PLUS | money_market | 채권형 | very_low |

## 4. 데이터 품질 요약

- 월말 가격표 크기: `172 rows × 3 columns`
- 월간 수익률표 크기: `171 rows × 3 columns`
- 전체 결측치 수: `0`
- 유동성 통과 ETF 수: `3` / `3`

## 5. HSI 스냅샷

| ticker | name | direction | intensity | signal |
|---|---|---:|---:|---|
| 069500 | KODEX 200 | 0.0636 | 0.4148 | watch |
| 114260 | KODEX 국고채3년 | -0.2689 | 0.3002 | watch |
| 153130 | KODEX 단기채권PLUS | -0.0229 | 0.2004 | watch |

## 6. benchmark rs 처리

069500은 상대강도 계산의 benchmark로 사용되므로, 자기 자신과의 relative strength 값은 별도의 정보량을 갖지 않는다. 따라서 스냅샷에서는 benchmark 또는 별도 note로 표시하고, 원시 점수표에서는 계산 구조 보존을 위해 NaN이 남을 수 있다.

## 7. main_v3 연결 판단

데이터 파트의 ETF 선정, 자산군 분류, 가격 로드, 결측치, 유동성, 월말 가격, 월간 수익률, HSI 기본 입력 신호표는 main_v3 후속 실험으로 연결 가능하다.

다음 단계에서는 `monthly_returns.csv`와 HSI 상태분류 테이블을 연결하여, `main_v2b` 기준 비중 규칙 및 후속 신호 조합 실험으로 이어간다.

## 8. 점검표

| check_item | result | status | note |
|---|---|---|---|
| selected_etf_count | 3 | OK | 최종 ETF 3종 구성 여부 |
| required_asset_classes | bond, equity, money_market | OK | equity / bond / money_market 포함 여부 |
| monthly_prices_shape | 172 rows x 3 columns | OK | 월말 가격표 생성 여부 |
| monthly_returns_shape | 171 rows x 3 columns | OK | 월간 수익률표 생성 여부 |
| total_missing_after_load | 0 | OK | load_price_data 내부 ffill 이후 결측치 |
| liquidity_pass_count | 3 | OK | 거래량/거래대금 기준 통과 ETF 수 |
| hsi_snapshot_rows | 3 | OK | 최근일 HSI 스냅샷 생성 여부 |
| hsi_raw_scores_shape | 3486 rows x 15 columns | OK | HSI 원점수 테이블 생성 여부 |
| benchmark_rs_snapshot | score_rs=nan, rs_note= | OK | 069500은 benchmark 자기비교이므로 NaN 또는 benchmark 표기가 자연스러움 |
