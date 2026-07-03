# 14번 Macro Companion Overlay Note

## 목적
HSI baseline 위에 macro companion을 soft overlay 형태로 얹었을 때, 기존 HSI baseline의 성과가 크게 훼손되지 않으면서 MDD와 위험조정지표가 일부 개선되는지 확인한다.

## 핵심 구조

```text
HSI baseline 목표비중
→ macro risk flag 확인
→ macro_defense_addon × overlay_strength 계산
→ 069500 비중을 소폭 축소
→ 축소분을 114260, 153130으로 배분
→ 월별 수익률 백테스트
```

## 성과 요약

- HSI baseline CAGR: 7.73%
- Macro soft overlay CAGR: 7.73%
- CAGR 차이: -0.0005%p
- HSI baseline MDD: -23.46%
- Macro soft overlay MDD: -23.36%
- MDD 개선폭: 0.0965%p
- Sharpe 차이: 0.0007
- Calmar 차이: 0.0013

## 조정 요약

- 전체 월 수: 172
- macro 데이터 사용 가능 월: 150
- macro risk 월: 74
- 실제 조정 월: 56
- 평균 조정폭: 0.1875%p
- 최대 조정폭: 2.5000%p

## 결론
14번 macro companion overlay는 HSI baseline을 대체하는 독립 전략이 아니라, HSI baseline 위에 외생 macro 위험을 약하게 반영해 본 soft overlay 보조 실험이다. 성과 훼손은 거의 없었고 MDD, Sharpe, Calmar는 아주 소폭 개선되었지만, 개선폭은 최종 후보를 바꿀 정도로 크지 않았다. 따라서 14번은 최종 모델이 아니라 보조 진단 실험으로 분류한다.

## 후속 연결
15번 Lambda + macro overlay sensitivity에서는 GDP를 직접 위험 조건에서 제외한 no-GDP 금리·환율 중심 macro overlay를 Lambda 후보 위에 다시 검토하였다. 그 결과 macro overlay는 최종 후보를 바꾸지 못했고, 최종 후보는 Lambda 0.1과 Lambda 0.3으로 유지되었다.
