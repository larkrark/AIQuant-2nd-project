# HSI 기반 ETF 자산배분 프로젝트 작업 인수인계 메모

## 목적

이 문서는 `IQuant-2nd-project`에서 `00번` 파일부터 최종 재현 파이프라인을 작업할 사람에게 전달하기 위한 정리본입니다.  
핵심은 기존 prototype 파일을 모두 버리는 것이 아니라, 최종 실행 흐름을 `00~11번`으로 다시 정리하고, 외부 사건 달력은 `50번대` 해석 레이어로 분리하는 것입니다.

본 프로젝트에서 HSI는 미래 수익률을 직접 예측하는 모델이 아닙니다.  
HSI는 가격 기반 시장환경신호를 이용해 시장 상태를 분류하고, 그 상태를 ETF 비중 조절 규칙으로 연결하는 **방어형 자산배분 overlay**입니다.

---

## 1. 최종 파일 구분

### Final reproducible pipeline

`00~11번` 파일은 최종 데이터 기준으로 다시 실행 가능한 파이프라인입니다.

| 파일 | 역할 |
|---|---|
| `00_final_project_config.py` | 경로, 티커, 수익률 단위, 상태명, 공통 설정을 한 곳에서 고정합니다. |
| `01_build_final_data_artifacts.py` | `HSI_data_pipeline_0629_4.py`를 기준으로 ETF 유니버스, 자산군표, 월말가격, 월간수익률 decimal/pct, HSI 기본 입력 신호표를 생성합니다. |
| `02_build_hsi_event_balance_indicator.py` | HSI 입력 신호의 20/80분위수 기반 사건균형지표를 생성합니다. |
| `03_prepare_monthly_signal_inputs.py` | 월말 HSI 신호 입력표를 정리합니다. |
| `04_build_hsi_state5_baseline.py` | 기본 HSI 5상태를 생성합니다. |
| `05_backtest_baseline_main_v2b.py` | baseline 백테스트를 수행합니다. |
| `06_build_extended_signal_inputs.py` | 추가 신호 후보를 생성합니다. |
| `07_run_signal_combo_backtests.py` | 신호 조합별 백테스트를 수행합니다. |
| `08_event_balance_state_diagnostic.py` | 사건균형지표와 HSI 5상태의 정합성을 확인합니다. |
| `09_event_balance_filter_backtest.py` | 사건균형지표를 보조 필터로 넣은 전략을 실험합니다. |
| `10_inertia_lambda_experiment.py` | 포트폴리오 관성 또는 부분 조정 λ 실험을 수행합니다. |
| `11_theta_sensitivity_experiment.py` | θ 민감도 검증을 수행합니다. |

### Prototype / draft experiment

기존 `31~36번` 파일은 삭제하지 않습니다.  
이 파일들은 개발 과정에서 나온 prototype 또는 draft experiment로 보존합니다.

```text
31~36번
→ 개발 과정의 prototype / draft experiment

00~11번
→ 최종 데이터 기준 final reproducible pipeline
```

### Market event calendar layer

`50번대` 파일은 외부 사건 달력 관련 파일입니다.  
외부 사건 달력은 전략 입력값이 아니라, HSI 상태 산출 이후 사후 해석·시각화·위기구간 검증에 사용합니다.

| 파일 | 역할 |
|---|---|
| `market_event_calendar.py` | 외부 시장 사건 참조표. 전략 입력 아님. |
| `50_build_market_event_calendar_table.py` | 외부 사건 달력을 표준 CSV로 변환합니다. |
| `51_align_hsi_state_with_market_events.py` | HSI 상태표와 사건 구간을 월 단위로 대조합니다. |
| `52_plot_event_annotated_hsi_timeline.py` | 사건 주석이 들어간 HSI 타임라인 그림을 생성합니다. |

주의 문장:

> `market_event_calendar.py`는 HSI 계산이나 비중 결정에 직접 사용하지 않습니다.  
> HSI 상태 산출 이후 주요 시장 사건 구간과 사후적으로 대조하여, HSI 상태 변화와 방어 성과가 실제 사건 구간에서 납득 가능하게 나타났는지 확인하는 해석·검증 자료로 사용합니다.

---

## 2. 전체 실행 흐름

권장 흐름은 아래와 같습니다.

```text
00_final_project_config.py
↓
01_build_final_data_artifacts.py
↓
02_build_hsi_event_balance_indicator.py
↓
03_prepare_monthly_signal_inputs.py
↓
04_build_hsi_state5_baseline.py
↓
05_backtest_baseline_main_v2b.py
↓
06_build_extended_signal_inputs.py
↓
07_run_signal_combo_backtests.py
↓
08_event_balance_state_diagnostic.py
↓
09_event_balance_filter_backtest.py
↓
10_inertia_lambda_experiment.py
↓
11_theta_sensitivity_experiment.py
↓
50~52번 market event calendar 해석·시각화
```

중요한 원칙은 다음과 같습니다.

```text
HSI 계산
→ 상태분류
→ 상태별 목표 비중
→ 월말 신호를 다음 달 수익률에 적용
→ 백테스트
→ 사건 달력으로 사후 해석
```

---

## 3. 데이터 파이프라인 주의점

`HSI_data_pipeline_0629_4.py`는 ETF 유니버스와 데이터 산출을 직접 수행하는 원천 파이프라인 파일입니다.

이 파일 안에는 다음 요소가 고정되어 있습니다.

```text
ETF_UNIVERSE
DATA_START_DATE = "2012-03-07"
BENCHMARK_TICKER = "069500"
```

현재 3개 ETF 기준 역할은 다음과 같습니다.

| 티커 | ETF | 역할 |
|---|---|---|
| `069500` | KODEX 200 | 위험자산 |
| `114260` | KODEX 국고채3년 | 방어 채권 |
| `153130` | KODEX 단기채권PLUS | 현금성 방어자산 |

`00_final_project_config.py`에서는 이 티커와 역할을 공통 설정으로 한 번만 정의하고, 이후 파일은 이 설정을 import해서 쓰는 것이 좋습니다.

---

## 4. 수익률 단위 주의

가장 중요한 주의점 중 하나는 월간 수익률 단위입니다.

`HSI_data_pipeline_0629_4.py`의 `make_monthly_return_table()`은 월간 수익률을 `%` 단위로 만듭니다.

```python
monthly_ret = make_monthly_price_table(prices).pct_change() * 100
```

하지만 백테스트 계산에는 보통 decimal 단위가 필요합니다.

```text
2.5%  → pct 단위: 2.5
2.5%  → decimal 단위: 0.025
```

따라서 `01_build_final_data_artifacts.py`에서는 두 단위를 명확히 분리하는 것이 좋습니다.

예시 파일명:

```text
monthly_returns_pct.csv
monthly_returns_decimal.csv
```

백테스트는 반드시 decimal 단위를 사용합니다.

---

## 5. HSI 상태와 리밸런싱 규칙

본 프로젝트에서 리밸런싱 규칙은 HSI 상태분류 결과를 실제 ETF 비중으로 변환하는 연결 규칙입니다.

HSI는 미래 수익률을 직접 예측하는 모델이 아니므로, 리밸런싱 규칙은 HSI 상태에 따라 위험자산 노출을 확대하거나 축소하는 방어형 자산배분 규칙으로 설계합니다.

### 기본 5상태

| HSI 상태 | 해석 |
|---|---|
| `risk_relief` | 위험 완화 우세 |
| `neutral_watch` | 중립 관찰 |
| `conflict` | 신호 충돌 |
| `risk_warning` | 위험 악화 우세 |
| `accident_zone` | 강한 위험 구간 |

### baseline 목표 비중

기획 단계의 baseline 규칙은 아래와 같이 둘 수 있습니다.

| HSI 상태 | 해석 | 069500 | 114260 | 153130 |
|---|---|---:|---:|---:|
| `risk_relief` | 위험 완화 우세 | 70% | 20% | 10% |
| `neutral_watch` | 중립 관찰 | 50% | 35% | 15% |
| `conflict` | 신호 충돌 | 35% | 40% | 25% |
| `risk_warning` | 위험 악화 우세 | 20% | 45% | 35% |
| `accident_zone` | 강한 위험 구간 | 0% | 30% | 70% |

이 규칙은 최종 최적 비중이 아니라 baseline 비중 규칙입니다.  
이후 θ 민감도, λ 실험, 사건균형지표 필터를 통해 안정성과 Turnover 영향을 확인합니다.

---

## 6. 리밸런싱 규칙 설계 원칙

리밸런싱 규칙은 다음 원칙을 따릅니다.

| 원칙 | 설명 |
|---|---|
| 단조성 | 위험 상태가 강해질수록 위험자산 비중은 감소해야 합니다. |
| 방어성 | 위험 악화 상태에서는 채권·현금성 자산 비중을 높입니다. |
| 비예측성 | HSI 상태를 미래수익률 예측값으로 보지 않습니다. |
| 시점 정합성 | 월말 HSI 상태를 다음 달 수익률에 적용합니다. |
| 과잉매매 제한 | Turnover가 과도하게 커지지 않도록 λ 또는 turnover cap을 검토합니다. |
| 해석 가능성 | 상태별 비중 변화가 사람이 이해 가능한 구조여야 합니다. |

보고서용 문장:

> 리밸런싱 규칙은 HSI 상태분류 결과를 실제 ETF 비중으로 변환하는 연결 규칙입니다.  
> 본 프로젝트에서 HSI는 미래 수익률을 직접 예측하는 모델이 아니라, 현재 관측 가능한 가격 기반 신호를 이용해 시장 상태를 분류하는 보조지표입니다.  
> 따라서 리밸런싱 규칙은 HSI 상태에 따라 위험자산 노출을 확대하거나 축소하는 방어형 자산배분 규칙으로 설계합니다.

---

## 7. 사건균형지표와 리밸런싱 규칙의 관계

사건균형지표는 외부 사건 달력이 아닙니다.  
HSI 입력 신호 자체에서 위험 악화 또는 위험 완화 방향의 극단 신호가 최근 기간 동안 얼마나 반복되었는지 보는 내부 보조지표입니다.

계산 개념:

```text
위험 사건 = HSI 방향 신호값 ≥ 과거 80분위수
완화 사건 = HSI 방향 신호값 ≤ 과거 20분위수

사건균형 = 위험 사건 비율 - 완화 사건 비율
사건강도 = 위험 사건 비율 + 완화 사건 비율
```

사용 원칙:

```text
HSI 상태를 대체하지 않습니다.
위험 또는 완화 신호가 반복적으로 누적되었는지 확인하는 보조 필터로 사용합니다.
```

예시:

| 조건 | 보정 아이디어 |
|---|---|
| 사건균형지표가 강한 위험 우세 | 위험자산에서 5~10%p 줄이고 현금성 방어자산으로 이동 |
| 사건균형지표가 강한 완화 우세 | 현금성 방어자산에서 5~10%p 줄이고 위험자산으로 이동 |
| 사건강도는 높지만 방향이 불명확 | conflict처럼 방어적으로 유지 |
| 외부 사건 달력과 겹침 | 전략 입력이 아니라 사후 해석용으로만 사용 |

---

## 8. λ 실험

`10_inertia_lambda_experiment.py`는 목표 비중으로 한 번에 이동하지 않고, 일부만 조정하는 실험입니다.

공식:

```text
actual_weight_t
= previous_weight + λ × (target_weight_t - previous_weight)
```

해석:

| λ | 의미 |
|---|---|
| 1.0 | 목표 비중으로 즉시 이동 |
| 0.5 | 목표 비중과 기존 비중의 중간까지만 이동 |
| 0.0 | 기존 비중 유지 |

목적:

```text
λ를 낮추면 Turnover는 줄어들 수 있지만 위험 대응이 늦어질 수 있습니다.
λ를 높이면 위험 대응은 빠르지만 Turnover와 거래비용이 커질 수 있습니다.
```

따라서 λ 실험은 최고 수익률을 찾는 실험이 아니라, Turnover와 방어 성과 사이의 균형을 확인하는 실험입니다.

---

## 9. θ 실험

`11_theta_sensitivity_experiment.py`는 HSI 상태분류 민감도 기준인 θ를 바꾸어 보는 실험입니다.

θ는 예측모델 파라미터가 아니라 상태분류 민감도 조절값입니다.

정의:

```text
θ = HSI 방향값이 어느 정도 커졌을 때
    위험 완화 또는 위험 악화 상태로 인정할 것인지 정하는 기준
```

권장 후보:

```text
θ = 0.10, 0.15, 0.20, 0.25, 0.30
```

실험 목적:

```text
θ를 많이 돌려서 가장 높은 CAGR을 찾는 것이 아닙니다.
θ가 조금 바뀌어도 MDD, Turnover, Sharpe, Calmar, 상태분포가 크게 무너지지 않는지 확인합니다.
```

보고서용 문장:

> θ 실험에서는 리밸런싱 규칙을 고정한 상태에서 HSI 상태분류 민감도만 변화시킵니다.  
> 이를 통해 성과 변화가 비중 규칙 때문인지, 상태분류 기준 변화 때문인지 구분합니다.

---

## 10. 외부 사건 달력의 위치

`market_event_calendar.py`는 외부 사건 참조표입니다.

역할:

```text
전략 입력값 X
사후 해석 O
시각화 주석 O
위기구간 검증 O
Robustness 해석 O
```

외부 사건 달력은 HSI 상태 계산 이후에 붙입니다.

```text
HSI 상태 계산
↓
백테스트 결과 생성
↓
market_event_calendar.py로 주요 사건 구간과 사후 대조
↓
event-annotated HSI timeline 생성
```

보고서용 문장:

> 시장 사건 달력은 HSI 계산이나 비중 결정에 직접 사용하지 않았습니다.  
> HSI 상태를 먼저 산출한 뒤, 주요 시장 사건 구간과 사후적으로 대조하여 위기·완화·혼합 국면을 얼마나 설명력 있게 포착했는지 확인하는 해석 및 검증 보조 자료로 사용했습니다.

---

## 11. 산출물 제안

리밸런싱 규칙과 실험 관련 산출물은 아래처럼 정리할 수 있습니다.

```text
output/tables/allocation_rule_table.csv
output/tables/baseline_target_weights.csv
output/tables/baseline_actual_weights_lambda.csv
output/tables/baseline_turnover_summary.csv
output/tables/event_balance_adjusted_weights.csv
output/tables/inertia_lambda_experiment_summary.csv
output/tables/theta_rebalancing_sensitivity_summary.csv
```

외부 사건 달력 관련 산출물:

```text
data/reference/market_event_calendar.csv

output/tables/market_event_calendar_master.csv
output/tables/market_event_backtest_windows.csv
output/tables/main_v3_hsi_state_event_overlap.csv

output/figures/main_v3_event_annotated_hsi_timeline.png

docs/main_v3_market_event_calendar_note.md
```

---

## 12. 최종 한 줄 요약

본 프로젝트의 최종 구조는 다음과 같습니다.

```text
00~11번
→ 최종 데이터 기준 final reproducible pipeline

31~36번
→ 개발 과정의 prototype / draft experiment

50번대
→ 외부 시장 사건 달력 기반 사후 해석·시각화·위기구간 검증 레이어
```

리밸런싱 규칙은 이 프로젝트에서 다음 역할을 합니다.

```text
HSI 상태
→ 상태별 목표 ETF 비중
→ 월말 신호를 다음 달 수익률에 적용
→ Turnover와 방어 성과 평가
```

즉, 리밸런싱 규칙은 HSI가 단순한 점수 계산으로 끝나지 않고 실제 ETF 자산배분 전략으로 연결되게 만드는 핵심 연결부입니다.
