# 팀 공유용 최종 요약

## 핵심 결론

이번 프로젝트의 최종 후보는 Lambda 0.1과 Lambda 0.3 두 가지로 유지한다.

- Lambda 0.1: 저회전·보수형 운용 후보
- Lambda 0.3: 수익성과 Calmar 측면의 균형형 후보

HSI baseline은 HSI 상태를 목표비중에 즉시 반영한 내부 기준선이며, 최종 후보는 아니다. baseline은 HSI 상태가 ETF 비중 조절로 연결될 수 있음을 보여주었지만, MDD와 Turnover 부담이 컸다.

Fixed 70/20/10 BM은 최종 비교의 메인 BM으로 사용한다. EW Benchmark는 동일 ETF 유니버스의 단순분산 보조 BM으로 사용한다.

Macro companion은 최종 후보를 대체할 정도의 개선 효과를 보이지 않았으므로, 보조 진단 layer로 둔다. 15번 Lambda + macro overlay 실험은 macro 보정 강도에 따른 trade-off를 확인한 후속 진단 실험으로 분류한다.

16번은 최종 후보인 Lambda 0.1과 Lambda 0.3의 robustness를 점검한 검증 실험이다. 17번은 Fixed 70/20/10 BM을 추가하여 비교 기준을 정렬한 BM alignment 보강 실험이다.

## 발표용 한 문단

본 프로젝트는 HSI를 미래 수익률 예측기로 사용하지 않고, 가격 기반 신호를 이용해 ETF 시장상태를 해석하는 내부 합성지표로 정의하였다. HSI baseline은 HSI 상태를 ETF 목표비중으로 연결할 수 있음을 보여주었지만, 목표비중으로 즉시 이동하는 구조 때문에 MDD와 Turnover 부담이 컸다. 이에 따라 λ 부분조정을 적용하였고, Lambda 0.1과 Lambda 0.3이 최종 후보로 남았다. Lambda 0.1은 저회전·보수형 후보이고, Lambda 0.3은 수익성과 Calmar의 균형 후보이다. Fixed 70/20/10 BM은 메인 BM으로, EW Benchmark는 보조 BM으로 둔다. macro companion은 최종 후보를 뒤집지 못했으므로 보조 진단 layer로 남긴다.

## 피해야 할 표현

- HSI가 시장을 예측했다.
- HSI 후보가 모든 지표에서 EW 또는 BM보다 우월하다.
- Lambda 0.3이 최적값이다.
- macro companion이 최종 전략을 개선했다.
- baseline이 최종 전략이다.

## 안전한 표현

- HSI는 시장상태 번역기이다.
- Lambda 후보는 운용 목적에 따라 구분되는 우선 후보이다.
- Fixed 70/20/10 BM은 CAGR은 높지만 MDD가 크다.
- Lambda 후보는 Fixed BM보다 CAGR은 낮지만 MDD와 Calmar 측면에서 방어형 후보로 볼 수 있다.
- macro companion은 최종 후보를 대체하지 못한 보조 진단 layer이다.
