# HSI 기반 ETF 방어형 Overlay 프로젝트 팀 공용 할일 체크리스트

## 0. 현재 기준 요약

본 프로젝트는 ETF 가격 데이터를 바탕으로 HSI 시장상태를 분류하고, 그 상태를 ETF 자산군 비중 조정으로 연결하는 방어형 자산배분 전략 실험이다.

현재까지는 `buy / watch / caution` 3분류를 최종 전략 상태로 사용하지 않고, 프로젝트용 HSI 5상태 체계인 `risk_relief`, `neutral_watch`, `conflict`, `risk_warning`, `accident_zone`을 기준으로 실험을 진행하였다.

현재 기준 비중 규칙은 `main_v2b`이다. `main_v2b`는 `conflict`를 즉시 방어전환 신호로 보지 않고 관찰 상태로 처리하며, `risk_warning`과 `accident_zone`에서만 위험자산 비중을 축소하는 규칙이다.

---

## 1. 완료된 작업

### 1-1. 데이터 준비 및 정렬

- [x] ETF 일별 가격 데이터 생성
- [x] 월말 가격 데이터 생성
- [x] 월간 수익률 데이터 생성
- [x] 데이터 결측 및 사용 가능 기간 점검
- [x] 월말 HSI 상태를 다음 달 월간 수익률에 연결
- [x] look-ahead bias 방지를 위해 `월말 신호 → 다음 달 수익률` 구조 적용

주요 산출물:

```text
data/processed/daily_prices.csv
data/processed/monthly_prices.csv
data/processed/monthly_returns.csv
output/tables/flex_data_quality_summary.csv
output/tables/flex_hsi_return_alignment_rank.csv
output/tables/flex_hsi_return_alignment_zscore.csv
```

### 1-2. HSI 5상태 체계 구축

- [x] 기존 `buy / watch / caution` 3분류를 최종 전략 상태로 바로 사용하지 않기로 정리
- [x] HSI 5상태 체계 정의
- [x] rank 기준 HSI 5상태표 생성
- [x] zscore 기준 HSI 5상태표 생성
- [x] HSI 5상태 분포표 생성

| HSI 상태 | 한국어 이름 | 의미 |
|---|---|---|
| `risk_relief` | 위험 완화 우세 | 위험 완화 신호가 우세 |
| `neutral_watch` | 관찰·중립 | 방향성이 약하거나 뚜렷하지 않음 |
| `conflict` | 충돌 상태 | 위험 악화와 완화 신호가 동시에 강함 |
| `risk_warning` | 위험 악화 우세 | 위험 악화 신호가 우세 |
| `accident_zone` | 강한 위험 악화 | 강한 방어전환 필요 |

주요 산출물:

```text
output/tables/main_v2_hsi_state5_table_rank.csv
output/tables/main_v2_hsi_state5_table_zscore.csv
output/tables/main_v2_hsi_state5_definition.csv
output/tables/main_v2_hsi_state5_distribution.csv
```

### 1-3. main_v2 / main_v2b 비교 실험

- [x] `main_v2`: `conflict`를 소폭 방어로 처리
- [x] `main_v2b`: `conflict`를 관찰 상태로 처리
- [x] EW, main_v2, main_v2b 백테스트 수행
- [x] 성과평가표 생성
- [x] 규칙 비교표 생성
- [x] Turnover 비교 수행

주요 관찰:

- `main_v2b`는 `main_v2` 대비 평균 Turnover가 감소하였다.
- rank 기준에서는 `main_v2b`가 EW 대비 MDD도 소폭 개선하였다.
- zscore 기준에서는 `main_v2b`가 main_v2보다는 개선되었으나, EW 대비 우위는 아직 약하다.
- 누적수익률은 EW가 여전히 우위이므로, 현재 전략은 최종 확정이 아니라 후속 최적화와 Robustness 검증이 필요하다.

주요 산출물:

```text
output/tables/main_v2_performance_summary.csv
output/tables/main_v2b_performance_summary.csv
output/tables/main_v2_rule_comparison_summary.csv
output/tables/main_v2_rule_comparison_comment.csv
```

### 1-4. 본문용 시각화 완료

- [x] Fig.1 HSI 5상태 분포
- [x] Fig.2 누적수익률 비교
- [x] Fig.3 Drawdown 비교
- [x] Fig.4 HSI 상태별 포트폴리오 비중 변화
- [x] Fig.5 Turnover 비교
- [x] Fig.6 main_v2 vs main_v2b 규칙 비교 요약
- [x] 시각화 산출물 인덱스 생성

---

## 2. 데이터 담당자 할일

### 2-1. 기존 HSI 5지표 재확인

- [ ] 기존 HSI 5지표 계산식 확인
- [ ] 지표별 방향 통일 기준 확인
- [ ] rank / zscore 산출 방식 확인
- [ ] 월말 기준으로 HSI 입력 신호를 정렬할 수 있는지 확인

| 번호 | 신호 | 역할 | 방향 처리 |
|---:|---|---|---|
| 1 | 최근 1개월 수익률 | 단기 수익 흐름 | 값이 클수록 안정 → 부호 반전 |
| 2 | 13612W 모멘텀 | 중장기 추세 | 값이 클수록 안정 → 부호 반전 |
| 3 | 10개월 SMA 대비 위치 | 장기 추세 위치 | 값이 클수록 안정 → 부호 반전 |
| 4 | 최근 3개월 변동성 | 위험 흔들림 | 값이 클수록 위험 → 그대로 사용 |
| 5 | 현금성 자산 대비 상대강도 | 위험자산과 현금성 자산의 상대 우위 | 값이 클수록 안정 → 부호 반전 |

### 2-2. 추가 지표 후보 계산

- [ ] `ma20_gap` 계산
- [ ] `ma60_gap` 계산
- [ ] `vol20` 계산
- [ ] `drawdown_60` 계산
- [ ] `risk_vs_cash_ret20` 계산
- [ ] 위 지표들을 월말 기준으로 정리
- [ ] ETF별 또는 대표 위험자산 기준으로 계산 범위 확정

| 실험명 | 추가 지표 | 질문 |
|---|---|---|
| `main_v3a_trend` | `ma20_gap`, `ma60_gap` | 단기·중기 추세 정보를 추가하면 상태분류가 안정되는가? |
| `main_v3b_risk_damage` | `vol20`, `drawdown_60` | 변동성과 고점 대비 손상도를 추가하면 방어 신호가 명확해지는가? |
| `main_v3c_relative_strength` | `risk_vs_cash_ret20` | 위험자산이 현금성 자산보다 약해지는 구간을 더 잘 포착하는가? |
| `main_v3d_core_signal_enhanced` | 추가 5지표 전체 | 추세·위험강도·손상도·상대강도를 함께 넣으면 개선되는가? |

### 2-3. 데이터 담당자 출력 요청 형식

- [ ] `data/processed/hsi_signal_inputs_extended.csv` 생성
- [ ] `Date` 컬럼 포함
- [ ] 기존 HSI 5지표 포함
- [ ] 추가 지표 후보 포함
- [ ] 결측치 및 계산 가능 시작일 표시
- [ ] 월말 기준 데이터 제공 가능 여부 확인

요청 컬럼 예시:

```text
Date
ret_1m
momentum_13612w
sma10_gap
vol_3m
relative_strength_cash
ma20_gap
ma60_gap
vol20
drawdown_60
risk_vs_cash_ret20
```

---

## 3. 전략 담당자 할일

### 3-1. 신호 조합 실험

- [ ] `main_v3_baseline`: 기존 HSI 5지표 + main_v2b 비중 규칙
- [ ] `main_v3a_trend`: 기존 5지표 + `ma20_gap`, `ma60_gap`
- [ ] `main_v3b_risk_damage`: 기존 5지표 + `vol20`, `drawdown_60`
- [ ] `main_v3c_relative_strength`: 기존 5지표 + `risk_vs_cash_ret20`
- [ ] `main_v3d_core_signal_enhanced`: 기존 5지표 + 추가 5지표 전체

실험 원칙:

- [ ] 비중 규칙은 `main_v2b`로 고정
- [ ] 신호 조합만 바꾸어 원인 해석 가능하게 유지
- [ ] rank 기본, zscore 보조 비교 유지
- [ ] 상태 분포, 성과, Drawdown, Turnover 함께 확인

### 3-2. 제한된 비중 Grid Search

- [ ] 신호 조합 실험에서 해석 가능한 후보 1~2개 선택
- [ ] 선택된 신호 조합에 한해 제한된 비중 Grid Search 수행
- [ ] HSI 상태가 나빠질수록 위험자산 비중이 커지지 않게 설정
- [ ] 위험자산 비중 감소분은 114260, 153130에 균등 배분

비중 후보 예시:

| 상태 | 위험자산 비중 후보 |
|---|---:|
| `risk_relief` | 0.3333 또는 0.40 |
| `neutral_watch` | 0.3333 |
| `conflict` | 0.3333 또는 0.30 |
| `risk_warning` | 0.25, 0.20, 0.15 |
| `accident_zone` | 0.15, 0.10, 0.05 |

### 3-3. Turnover 및 거래비용 가정

- [ ] 평균 Turnover 기준 적용
- [ ] 최대 Turnover 기준 적용
- [ ] 거래비용은 실제 비용 추정이 아니라 백테스트 평가 방식으로서 합리적인 단순화 가정으로 처리
- [ ] 팀 합의로 비용률 시나리오 결정
- [ ] 비용률 적용 전 결과와 적용 후 결과를 모두 비교

예비 Turnover 필터:

```text
avg_turnover <= 0.05
max_turnover <= 0.25
```

거래비용 가정 표현:

```text
본 프로젝트에서는 실제 ETF 거래비용을 정밀 추정하기보다, 백테스트 평가 방식으로서 합리적인 단순화 가정을 적용한다. 거래비용은 원천 가격 데이터가 아니라 HSI overlay 전략이 만들어낸 Turnover에 따라 사후적으로 발생하는 평가 조건으로 처리한다.
```

### 3-4. Robustness 검증

- [ ] 기간 분할 검증
- [ ] 위기구간 검증
- [ ] 거래비용 반영 검증
- [ ] 주변 파라미터 민감도 검증
- [ ] rank / zscore 양쪽에서 결과가 유지되는지 확인

---

## 4. 팀 합의 필요 항목

- [ ] ETF 최종 유니버스 확정
- [ ] 위험자산 / 채권형 / 현금성 자산군 분류 확정
- [ ] 추가 지표 계산 기준 확정
- [ ] `risk_vs_cash_ret20`의 현금성 기준 ETF 확정
- [ ] 거래비용 단순화 가정 비용률 확정
- [ ] Turnover 상한 기준 확정
- [ ] Robustness 위기구간 기준 확정
- [ ] 최종 보고서에서 rank / zscore를 어떻게 배치할지 확정

---

## 5. 팀 공유용 한 줄 요약

현재 HSI 5상태 overlay의 기본 구조와 본문용 시각화는 완료되었다. 다음 단계에서는 데이터 담당자가 기존 HSI 5지표와 추가 지표 후보를 계산해 제공하고, 전략 담당자는 `main_v2b` 비중 규칙을 기준으로 신호 조합별 효과를 비교한다. 이후 해석 가능한 조합에 한해 제한된 비중 Grid Search와 Turnover 필터, Robustness 검증을 진행한다.