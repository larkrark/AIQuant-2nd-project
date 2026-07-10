# 15번 Lambda + Macro Overlay Sensitivity Note

## 목적
Lambda 0.1과 Lambda 0.3 후보 위에 macro companion을 약하게 얹었을 때 MDD를 낮추면서 CAGR과 Turnover를 크게 훼손하지 않는지 확인한다.

```text
HSI = 시장상태 판단
lambda = 목표비중으로 이동하는 속도
macro companion = 약한 방어 보정
```

## 조합 수

```text
lambda 후보: [0.1, 0.3]
macro_scale 후보: [0.0, 0.25, 0.5, 0.75]
전체 조합 수: 8
조합 상한: 24
```

## GDP 처리
GDP는 직접 위험 조건에서 제외했다.
사용된 macro signal version은 다음과 같다.

```text
no_gdp_rate_fx_verified
```

`no_gdp_rate_fx_verified`이면 금리·환율 컬럼을 이용해 GDP 제외 신호가 확인된 것이다.  
`fallback_existing_macro_may_include_gdp`이면 필요한 세부 컬럼이 부족하여 기존 macro_defense_addon을 사용한 것이므로 GDP 제외 검증으로는 제한이 있다.

## 동적 선택 점수 1순위

```text
strategy_id: lambda_0.1_macro_0.00
selection_score: 0.6857
CAGR: 8.69%
MDD: -14.74%
Sharpe: 0.787
Calmar: 0.590
avg Turnover: 2.46%
```

## 보고서 문장
후속 실험에서는 Lambda 0.1과 Lambda 0.3 후보 위에 macro companion을 직접 비중 보정값으로 얹는 방식을 비교하였다. 이때 macro_scale은 성과를 임의로 개선하기 위한 최적화 계수가 아니라, macro 보조 신호의 반영 강도에 따른 민감도를 확인하기 위한 사전 설정 범위로 사용하였다. GDP는 계절성·기저효과·발표 지연 문제를 고려하여 직접 위험 조건에서 제외하고, 금리와 환율의 위험형 이탈을 중심으로 macro overlay를 구성하였다.
