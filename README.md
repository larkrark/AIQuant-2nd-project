## 파일 구성 및 역할

본 프로젝트의 최종 실행 흐름은 `00~11번` 파일을 기준으로 정리한다.
기존에 작성된 `31~36번` 파일은 삭제하지 않고, 개발 과정에서 생성된 prototype 또는 draft experiment로 보존한다.

### Final reproducible pipeline

| 파일                                        | 역할                                                                                                                                                    |
| ----------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `00_final_project_config.py`              | 프로젝트 공통 설정 파일. 경로, 티커, 수익률 단위, HSI 상태명, 공통 파라미터를 한 곳에서 관리한다.                                                                                          |
| `01_build_final_data_artifacts.py`        | `HSI_data_pipeline_0629_4.py`를 기준으로 ETF 유니버스, 자산군 분류표, 월말 가격표, 월간 수익률표, HSI 기본 입력 신호표를 생성한다. 월간 수익률은 백테스트용 decimal 단위와 원 파이프라인 확인용 pct 단위를 구분하여 관리한다. |
| `02_build_hsi_event_balance_indicator.py` | HSI 입력 신호의 과거 20/80분위수 기준으로 위험 사건과 완화 사건을 정의하고, 사건균형지표와 사건강도지표를 생성한다.                                                                                 |
| `03_prepare_monthly_signal_inputs.py`     | 일별 또는 원천 HSI 입력 신호를 월말 기준으로 정리하여 월간 상태분류와 백테스트에 사용할 수 있는 입력표로 변환한다.                                                                                   |
| `04_build_hsi_state5_baseline.py`         | HSI direction, intensity, conflict 조건을 이용해 기본 5상태를 생성한다. 상태는 위험 완화, 중립 관찰, 충돌, 위험 악화, 사고 구간으로 해석한다.                                                   |
| `05_backtest_baseline_main_v2b.py`        | 기본 HSI 5상태와 main_v2b 비중 규칙을 이용해 baseline 백테스트를 수행한다. 월말 신호를 다음 달 수익률에 적용하여 시점 정합성을 유지한다.                                                              |
| `06_build_extended_signal_inputs.py`      | 기존 HSI 신호 외에 추가 신호 후보를 생성한다. 이후 신호 조합 실험과 확장 검증의 입력으로 사용한다.                                                                                           |
| `07_run_signal_combo_backtests.py`        | 기본 신호와 추가 신호 후보를 조합하여 여러 신호 세트별 백테스트를 수행한다. 목적은 최고 수익률 조합만 찾는 것이 아니라, MDD, Turnover, 해석 가능성이 유지되는 신호 조합을 비교하는 것이다.                                    |
| `08_event_balance_state_diagnostic.py`    | 사건균형지표와 HSI 5상태가 서로 납득 가능한 방향으로 움직이는지 확인한다. 위험 사건 누적 구간에서 HSI가 위험 악화 쪽으로 이동하는지, 완화 사건 누적 구간에서 위험 완화 쪽으로 이동하는지를 점검한다.                                  |
| `09_event_balance_filter_backtest.py`     | 사건균형지표를 보조 필터로 추가한 전략을 실험한다. 사건균형지표는 HSI 상태를 대체하는 신호가 아니라, 상태 판단의 반복성 또는 누적성을 확인하는 보조 필터로 사용한다.                                                       |
| `10_inertia_lambda_experiment.py`         | 포트폴리오 비중을 한 번에 전환하지 않고 일부만 조정하는 관성 또는 부분 조정 λ 실험을 수행한다. 목적은 Turnover를 줄이면서 방어 성과가 유지되는지 확인하는 것이다.                                                     |
| `11_theta_sensitivity_experiment.py`      | HSI 상태분류 민감도 기준인 θ를 변화시키며 상태분포, MDD, Sharpe, Calmar, Turnover가 안정적으로 유지되는지 확인한다. θ는 예측 파라미터가 아니라 상태분류 민감도 조절값으로 해석한다.                                 |

### Market event calendar layer

`50번대` 파일은 외부 시장 사건 달력을 다루는 별도 해석 레이어이다.
이 파일들은 HSI 계산이나 포트폴리오 비중 결정에 직접 사용하지 않는다.
대신 HSI 상태 산출 이후 주요 시장 사건 구간과 사후적으로 대조하여, HSI 상태 변화와 방어 성과가 실제 시장 사건 구간에서 납득 가능하게 나타났는지 확인하는 용도로 사용한다.

| 파일                                         | 역할                                                            |
| ------------------------------------------ | ------------------------------------------------------------- |
| `market_event_calendar.py`                 | 외부 시장 사건 참조표를 정의한다. 전략 입력값이 아니라 사후 해석, 시각화 주석, 위기구간 검증용 자료이다. |
| `50_build_market_event_calendar_table.py`  | `market_event_calendar.py`를 표준 CSV 형태로 변환한다.                  |
| `51_align_hsi_state_with_market_events.py` | HSI 상태표와 시장 사건 구간을 월 단위로 대조한다.                                |
| `52_plot_event_annotated_hsi_timeline.py`  | 주요 시장 사건 주석이 포함된 HSI 상태 타임라인 그림을 생성한다.                        |

### Prototype / draft experiment files

기존 `31~36번` 파일은 삭제하지 않고 개발 과정의 prototype 또는 draft experiment로 보존한다.
최종 재현 가능한 실행 흐름은 `00~11번` 파일을 기준으로 하며, `31~36번` 파일은 실험 아이디어, 중간 검토, 구조 전환 과정의 참고 자료로 관리한다.

정리하면, 본 프로젝트의 최종 실행 기준은 다음과 같다.

```text
00~11번
→ 최종 데이터 기준 final reproducible pipeline

31~36번
→ 개발 과정의 prototype / draft experiment

50번대
→ 외부 시장 사건 달력 기반 사후 해석·시각화·위기구간 검증 레이어
```
이건 최종 00번 설계에 반드시 반영해야 합니다.
그리고 아주 중요한 점이 하나 있어요.

지금 제안하신 비중표는 우리가 앞서 쓰던 main_v2b 규칙과 다릅니다.

기존 main_v2b:
risk_relief / neutral / conflict → 동일비중 유지
risk_warning / accident_zone → 방어

새 최종 baseline 제안:
risk_relief부터 accident_zone까지 상태별 목표 비중이 단계적으로 변함

따라서 최종 파이프라인에서는 이름을 이렇게 분리하는 게 좋습니다.

FINAL_BASELINE_ALLOCATION_RULES
→ 최종 보고서용 기본 리밸런싱 규칙

LEGACY_MAIN_V2B_ALLOCATION_RULES
→ 이전 실험 비교용 / 부록용

즉, 최종 본선은 새 비중표로 가고, 기존 main_v2b는 “개발 과정의 보수적 기준선”으로 남기는 게 깔끔합니다.

## 실험 버전 관리 및 주의사항

본 프로젝트에는 초기 prototype 실험 코드와 최종 발표용 main_final 파이프라인이 함께 존재한다.

정리하면 다음과 같다.

- `00~36`: prototype / experiment archive
- `00~11`: main_final 재현 파이프라인
- `50`: 외부 사건 달력 기반 사후 해석 보조 자료

초기 실험의 핵심 아이디어는 새 `main_final` 파이프라인에 대부분 반영되었지만, 초기 코드와 산출물이 그대로 최종 결과에 사용되는 것은 아니다.

초기 00~36번 스크립트는 HSI 아이디어를 빠르게 구현하고 여러 계산 흐름을 탐색한 prototype archive이다. 이 단계에는 일부 하드코딩된 파일 참조, 과도기 산출물, 수익률 단위 처리 문제가 포함될 수 있으므로 최종 발표 기준으로 사용하지 않는다.

최종 발표와 보고서에서는 `main_final` 기준으로 재구성한 00~09번 파이프라인 결과를 사용한다. 이 파이프라인은 데이터 번들 확인, 수익률 단위 점검, 사건균형지표 생성, 월말 신호 정렬, HSI 5상태 분류, baseline 백테스트, 상대속도 진단, 신호 조합 비교, 사건균형 정합성 및 보조 필터 실험으로 구성된다.

baseline 즉시비중 전략은 HSI 상태를 ETF 비중으로 연결하는 기준선이며, 최종 방어형 전략으로 단정하지 않는다. 이후 λ 부분조정과 θ 민감도 실험을 통해 비중 전환 속도와 상태분류 기준의 안정성을 함께 검토한다.

09번 사건균형 필터는 병합 과정에서 사건균형 컬럼이 중복되어 모든 월이 `no_adjustment_missing_event_balance`로 처리되는 문제가 있었다. 이를 수정한 뒤 재실행한 결과, 사건균형 필터는 실제로 작동하였다.

재실행 결과, `HSI_event_balance_filter_overlay`는 baseline 대비 CAGR과 최종 누적수익률은 낮아졌지만, MDD와 연변동성은 소폭 완화되었고 평균 Turnover는 증가하지 않았다. 다만 개선 폭이 크지는 않으므로, 현재 단계에서는 사건균형 필터를 최종 전략 요소로 확정하기보다 HSI 상태분류를 보조적으로 조정하는 진단 후보로 해석한다.

### λ 부분조정 실험 해석

baseline 전략은 HSI 상태에 따라 목표 ETF 비중으로 즉시 이동하는 구조이다. 이 방식은 HSI 상태를 포트폴리오 비중으로 연결하는 기준선 역할은 하지만, 실행 결과 EW보다 MDD와 연변동성, Turnover가 크게 나타났다.

이를 보완하기 위해 λ 부분조정 실험을 수행하였다. λ는 현재 비중에서 목표 비중으로 이동하는 속도를 조절하는 값이다. λ=1.0은 목표 비중으로 즉시 이동하는 방식이고, λ가 작아질수록 기존 비중을 더 많이 유지하면서 천천히 이동한다.

실험 결과 λ를 낮추면 평균 Turnover와 MDD가 함께 완화되는 경향이 관찰되었다. 특히 λ=0.3은 CAGR, MDD, Sharpe, Turnover의 균형이 비교적 좋게 나타났다. 다만 이 결과만으로 λ=0.3을 최적값으로 단정하지 않고, θ 민감도와 거래비용을 함께 고려한 후속 검증 후보로 해석한다.

| 전략    | 해석         |  CAGR |     MDD |   연변동성 | Sharpe | 평균 Turnover |
| ----- | ---------- | ----: | ------: | -----: | -----: | ----------: |
| EW    | 단순 비교 기준   | 6.51% | -13.57% |  7.97% |  0.832 |       0.00% |
| λ=1.0 | 즉시 목표비중 이동 | 7.73% | -23.46% | 13.67% |  0.611 |      22.09% |
| λ=0.7 | 빠른 부분조정    | 8.06% | -19.96% | 12.51% |  0.682 |      15.41% |
| λ=0.5 | 중간 부분조정    | 8.58% | -17.52% | 12.20% |  0.735 |      11.14% |
| λ=0.3 | 균형 후보      | 9.09% | -15.22% | 12.05% |  0.782 |       6.95% |
| λ=0.1 | 매우 느린 조정   | 8.66% | -14.74% | 11.26% |  0.793 |       2.52% |
### 21_build_candidate_report_tables_and_figures , 20_select_final_candidates_with_cost_and_turnover  θ×λ 결합 실험

| 후보           |  CAGR |     MDD | Sharpe | Calmar | 평균 Turnover | 최대 Turnover | 20bp 비용 훼손 |
| ------------ | ----: | ------: | -----: | -----: | ----------: | ----------: | ---------: |
| Lambda 0.1   | 8.62% | -14.79% |  0.791 |  0.583 |       2.52% |       6.02% |    0.065%p |
| Lambda 0.3   | 8.99% | -15.33% |  0.775 |  0.587 |       6.95% |      20.01% |    0.181%p |
| EW Benchmark | 6.51% | -13.57% |  0.832 |  0.480 |       0.00% |       0.00% |    0.000%p |

Lambda 0.1과 Lambda 0.3은 EW보다 CAGR과 Calmar가 높고,
MDD는 EW보다 조금 크지만 baseline 즉시비중 전략보다 크게 완화되었다.
또한 Turnover와 거래비용 민감도도 관리 가능한 수준으로 낮아졌다.

EW는 Sharpe가 가장 높다.
따라서 Lambda 후보가 모든 지표에서 EW를 이겼다고 말하면 안 된다.
대신 Lambda 후보는 수익성, Calmar, Turnover, 비용 민감도 측면에서
방어형 overlay 후보로 검토할 가치가 있다고 표현하는 것이 안전하다.


### 12번 계산 흐름 - 금리·환율·GDP 3개만
일별 금리
→ 월말 금리
→ 국고3년 금리 변화폭
→ rate_z

일별 환율
→ 월말 원/달러
→ 원/달러 월간 변화율
→ fx_z

rate_z와 fx_z
→ 금리-환율 이탈률

분기 GDP 성장률
→ 월별로 forward-fill
→ 1개월 lag
→ GDP 성장 구간 판정

금리-환율 이탈률 + GDP 성장 구간
→ macro_defense_addon

금리-환율 이탈률
rate_fx_departure
= abs(rate_z + fx_z) / (abs(rate_z) + abs(fx_z) + EPS)

### 12번 결과 해석 기준
0에 가까움:
금리와 환율이 서로 반대 방향에 가깝게 움직임

1에 가까움:
금리와 환율이 같은 방향으로 움직이는 이탈 상태

*그리고 위험형 이탈은 이것만 인정합니다.*
금리 상승 + 원/달러 상승 + 이탈률 높음

*GDP는 공식 정책목표가 아니라 내부 기준으로 사용합니다.*
GDP 성장률 2~3%:
성장 안정 구간

GDP 성장률 2% 미만:
성장 둔화 또는 성장 압력 구간


**해석 주의사항**

1. NaN은 대부분 “계산 오류”가 아니라 자료가 없는 기간이 main_final 월 기준에 포함되어 있어서 생긴 결측입니다.

HSI 최종 수익률 월은 2012-04부터 있는데, 이번 매크로 자료는 대부분 2014년 이후부터 있습니다. 그래서 앞쪽 2012-04~2013-12 구간은 매크로 자료가 없습니다.

2. missing_count_rate_level = 21 정상입니다
금리 자료는 2014년 이후부터 있으니, main_final 기준으로 정렬하면 앞의 21개월은 금리값이 비게 됩니다.
의미:
금리 데이터 오류가 아니라,
HSI 백테스트 시작일이 매크로 자료 시작일보다 빠름

**그래서 rate_level, usdkrw, macro_defense_addon, rate_fx_departure가 모두 21개씩 비는 것은 자연스럽습니다.**

3. missing_count_rate_change_1m = 22 정상입니다

: 21개는 위와 같은 이유입니다. 그리고 1개가 추가되는 이유는 2014-01 첫 금리값은 있지만,

전월 2013-12 금리값이 없으므로 'rate_change_1m = 현재 금리 - 전월 금리' 를 계산할 수 없음.

**그래서 21개월 자료 없음 + 첫 변화율 계산 불가 1개월 = 22개**

**환율도 똑같습니다.**

missing_count_usdkrw = 21
missing_count_usdkrw_return_1m = 22

4. missing_count_gdp_growth_decimal_lagged = 27 정상입니다

GDP 자료는 2014-03부터 시작, 그러면 main_final 시작인 2012-04부터 2014-03 전후까지는 GDP를 붙일 수 없습니다. 

GDP는 분기 자료라서 2026-04~2026-06에 해당하는 최신 성장률이 아직 확정되지 않아 파일에 없을 확률이 높습니다.

그래서 27개 NaN은 '초기 GDP 미보유 구간 + 1개월 lag 때문에 생기는 첫 GDP 사용 불가 구간 + 2026-04~2026-06 최신 GDP 미보유 구간'을 

이유로 **자료 주기에 의한 차이 입니다.** 

5. regime_nan = 21의 의미

이건 2012-04~2013-12 구간입니다.

매크로 자료가 아예 없어서:
금리 없음
환율 없음
GDP 없음
rate_fx_departure 없음
macro_defense_addon 없음
macro_companion_regime 없음

**이 21개는 중립이 아닙니다.** 
**2012-04~2013-12 구간은 매크로 보조자료가 존재하지 않아 macro companion layer를 적용하지 않았다.**

마지막으로 

6. 최근 2026-04~2026-06 NaN

최근 3개월은 금리와 환율은 있습니다. 그런데 GDP만 없습니다. 예를 들어 아래와 같은 경우를 말합니다.

2026-05
rate_level = 3.731
usdkrw = 1505.8
rate_fx_risk_departure_flag = 1
macro_defense_addon = 0.010

gdp_growth_pct_lagged = NaN
gdp_growth_band = NaN


그래서 이 구간은 이렇게 해석합니다. 금리-환율 보조신호는 계산 가능하다. 다만 GDP 성장률 보조판정은 자료 부족으로 제외된다.
**2026-05와 2026-06의 macro_defense_addon = 0.010은 GDP 때문이 아니라, 금리 상승 + 원/달러 상승 + 이탈률 높음 때문에 부여된 것 이다**

7. 이탈률 , 방어 보조값 파악

rate_fx_departure_range   0.0000 ~ 1.0000     OK   이탈률은 0~1 범위 안에 정상적으로 들어옴
macro_defense_addon_max   0.0250              OK   방어 보조값은 최대 0.03 제한 안에 들어옴


8. 그외 규칙 작용 예시 

그리고 최근 2025-10, 2025-11은 규칙이 잘 작동한 예시입니다.

금리 상승
원/달러 상승
GDP 성장률 2% 미만
→ risk_departure_plus_growth_pressure
→ macro_defense_addon = 0.025

계산 고리가 의도대로 움직였습니다.

### 12번 해석에서 NaN은? 

현재 NaN은 대부분 오류가 아니라, main_final 백테스트 기간이 2012-04부터 시작하는 반면 매크로 자료는 2014년 이후부터 시작해서 생긴 정상적인 결측입니다. 최근 2026-04~2026-06의 NaN은 GDP 자료가 2026-03까지만 있어서 생긴 GDP 전용 결측이며, 금리-환율 보조신호는 정상 계산되고 있습니다.

### NaN 해석 컬럼 추가 조치

이전:
regime_nan 21

현재:
regime_macro_data_unavailable 21

매크로 자료가 없는 구간으로 명확히 분리


확인.
전체 정렬 상태
main_final 기준 월 수: 171개월
금리·환율 사용 가능: 150개월
GDP 사용 가능: 144개월
매크로 자료 없음: 21개월
이 21개월은 그냥 판정 제외 구간입니다.


GDP만 없는 최근 구간
2026-04  macro_data_available=1  gdp_data_available=0
2026-05  macro_data_available=1  gdp_data_available=0
2026-06  macro_data_available=1  gdp_data_available=0
금리와 환율은 계산 가능하다.
하지만 GDP lagged 값은 아직 없다.

그래서 2026-05, 2026-06의 방어 보조값은 GDP 때문이 아닙니다.

2026-05 macro_defense_addon = 0.010
2026-06 macro_defense_addon = 0.010

이 값은 오직 이 조건 때문입니다.

금리 상승 + 원/달러 상승 + 금리-환율 이탈률 높음

**최근 구간 해석**(최근 10행)
2026년 4~6월은 GDP 성장률 자료가 아직 연결되지 않아 성장 압력 판정은 제외하였다. 다만 금리와 환율 자료는 존재하므로 금리-환율 이탈률 기반 보조 신호는 계산하였다.


**신호 요약 해석**
macro_data_available = 150 / 171 = 87.72%
gdp_data_available   = 144 / 171 = 84.21%

이건 전체 171개월 기준 비율입니다.

실제로 매크로 자료가 있는 150개월만 기준으로 보면:

rate_fx_risk_departure_flag = 38 / 150 ≈ 25.3%
rate_fx_relief_departure_flag = 28 / 150 ≈ 18.7%

GDPrate_fx_relief_departure_flag = 28 / 150 ≈ 18.7%


GDP 자료가 있는 144개월만 기준으로 보면:

policy_growth_pressure_flag = 36 / 144 = 25.0%
gdp_below_2_flag = 72 / 144 = 50.0%


### 23_build_report_candidate_tables_goldfriend (20,21 차이) θ×λ 결합 실험

1. baseline을 최종 후보로 올리지 않고 기준선으로만 둔다.
2. λ 후보를 가장 중요하게 보되, “최적”이 아니라 “우선 검토 후보”로 표시한다.
3. event filter는 작동 확인 후보로 두되, 개선 폭 제한을 명시한다.
4. 거래비용 표는 “정밀 비용 백테스트”가 아니라 “보고서용 단순 비용 민감도”로 표시한다.
5. shortlist는 공격적으로 뽑지 않고, 발표에 올릴 후보만 보수적으로 남긴다.

C:\quant_lec\quant_model\day5\day5_hsi_dynamic_allocation_project\AIQuant-2nd-project\output\tables

23_main_final_report_candidate_comparison_table.csv   
23_main_final_report_candidate_cost_pivot.csv  
23_main_final_report_candidate_shortlist.csv
23_main_final_report_candidate_timeseries_subset.csv 
23_main_final_report_lambda_family_table.csv    

정리 예정
발표시에 차례대로
→ 전체 후보 비교표
→ 발표·보고서에 올릴 핵심 후보표
→ 거래비용 민감도 보조표
→ λ 실험 핵심 발표표
→ Streamlit / Plotly 그래프용 후보 시계열

baseline은 기준선이다.
λ 부분조정은 개선 방향이다.
event filter는 보조 진단 후보이다.
최종 우수성은 단정하지 않고, 운용 가능성을 검토한다.

### 13_hsi_macro_companion_diagnostic

1. 진단표만 만듭니다.
HSI가 위험이라고 본 달에,
금리·환율·GDP 보조장치도 위험 쪽을 같이 보고 있었는가?



### 14_이어서 실험 할 것.
-> 비중 조절 관여도

-> 기본 구조

HSI baseline 비중 + macro companion 보조값
= macro overlay 비중


-> HSI 상태는 그대로 둡니다.

risk_relief       → 70 / 20 / 10
neutral_watch     → 50 / 35 / 15
conflict          → 35 / 40 / 25
risk_warning      → 20 / 45 / 35
accident_zone     → 0 / 30 / 70

*여기에 매크로 보조값이 위험을 말하면, 위험자산 069500 비중을 아주 조금 줄입니다.*
HSI baseline을 망가뜨리지 않으면서도 매크로 경고를 반영할 수 있는 정도로만.

-> 적용 강도는 상황별로 다르게

***13번에서 겹침 유형 정리***

both_hsi_and_macro_risk = 26개월
hsi_risk_only           = 21개월
macro_risk_only         = 48개월
both_relief             = 16개월

그래서 적용 강도는 이렇게 나누는 게 좋습니다.

both_hsi_and_macro_risk:
HSI도 위험, macro도 위험
→ macro_defense_addon 100% 적용

macro_risk_only:
HSI는 위험 아님, macro만 위험
→ macro_defense_addon 25~50%만 적용

hsi_risk_only:
HSI는 위험, macro는 위험 아님
→ 기존 HSI baseline 그대로 유지

both_relief:
HSI 완화 + macro 완화
→ baseline 그대로 유지


-> 첫 실험 값 : macro_risk_only가 많아도 과잉방어를 줄이는 방향으로
both_hsi_and_macro_risk      → 1.00배
macro_risk_only + conflict   → 0.50배
macro_risk_only + neutral    → 0.50배
macro_risk_only + risk_relief → 0.25배
나머지                       → 0.00배


*줄인 비중은 어디로 보낼까?*

위험자산 069500에서 줄인 비중은 방어자산으로 보냅니다.

**그런데 금리 상승 구간에서는 장기채나 중기채도 손실을 볼 수 있으니, 줄인 비중을 국고채 3년 114260에 많이 보내기보다 단기채권PLUS 153130에 더 보내는 게 자연스럽습니다.**

예시.
069500 감소분의 30% → 114260
069500 감소분의 70% → 153130
HSI 비중.
069500 70%
114260 20%
153130 10%
적용.(매크로 보정 감소분이 2.5%p라면:)
069500: 70.0% - 2.5% = 67.5%
114260: 20.0% + 0.75% = 20.75%
153130: 10.0% + 1.75% = 11.75%

**수식으로 정리 (단, macro_data_available = 0이면 아무것도 하지 않습니다.)** → baseline 비중 그대로 사용
delta = macro_defense_addon × overlay_strength

weight_069500_new = weight_069500_base - delta
weight_114260_new = weight_114260_base + delta × 0.30
weight_153130_new = weight_153130_base + delta × 0.70


이 방식은 HSI를 대체하지 않습니다.

HSI = 주 판단
macro companion = 작은 보정