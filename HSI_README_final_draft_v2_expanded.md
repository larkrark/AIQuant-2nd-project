# HSI 기반 ETF RoboAdvisor Overlay 프로젝트 최종 README 초안

## 1. 프로젝트 정의

본 프로젝트는 HSI 기반 시장상태 해석 신호를 이용해 ETF 포트폴리오의 위험자산 비중을 조절하는 방어형 RoboAdvisor prototype이다.

HSI는 미래 수익률을 직접 예측하는 모델이 아니다. HSI는 가격 기반 신호를 이용해 현재 시장상태가 위험 완화 방향인지, 위험 악화 방향인지, 또는 양방향 신호가 충돌하는 구간인지를 해석하기 위한 프로젝트 내부 합성지표이다.

```text
HSI = 시장상태 해석 지표
baseline = HSI 상태를 ETF 목표비중으로 연결한 내부 기준선
λ overlay = 목표비중으로 한 번에 이동하지 않고 천천히 이동하는 부분조정 구조
최종 후보 = Lambda 0.1 / Lambda 0.3
```

## 2. 최종 운영 원칙

1. 최종 후보는 Lambda 0.1과 Lambda 0.3 두 가지로 유지한다.
2. Lambda 0.1은 저회전·보수형 운용 후보로 분류한다.
3. Lambda 0.3은 수익성과 Calmar 측면의 균형형 후보로 분류한다.
4. Fixed 70/20/10 BM은 최종 비교의 메인 BM으로 사용한다.
5. EW Benchmark는 동일 ETF 유니버스의 단순분산 보조 BM으로 사용한다.
6. HSI baseline은 HSI 상태를 목표비중에 즉시 반영한 내부 기준선이며, 최종 후보는 아니다.
7. Macro companion은 최종 후보를 대체할 정도의 개선 효과를 보이지 않았으므로, 보조 진단 layer로 둔다.
8. 15번 Lambda + macro overlay 실험은 macro 보정 강도에 따른 trade-off를 확인한 후속 진단 실험으로 분류한다.
9. 16번은 최종 후보인 Lambda 0.1과 Lambda 0.3의 robustness를 점검한 검증 실험이다.
10. 17번은 Fixed 70/20/10 BM을 추가하여 비교 기준을 정렬한 BM alignment 보강 실험이다.

## 3. ETF 유니버스

| 티커 | 자산군 | 프로젝트 내 역할 |
|---|---|---|
| `069500` | KODEX 200 | 위험자산 |
| `114260` | KODEX 국고채3년 | 채권형 방어자산 |
| `153130` | KODEX 단기채권 | 현금성 방어자산 |

## 4. 리밸런싱 구조

본 전략은 지표 변화에 따라 매일 수시 대응하는 구조가 아니다. 월말에 관측 가능한 HSI 상태를 기준으로 다음 달 ETF 비중에 반영하는 월간 리밸런싱 구조이다.

```text
t월 말 가격·신호 확인
→ t월 말 HSI 상태 산출
→ t+1월 ETF 수익률에 적용
→ 다음 월말에 다시 리밸런싱
```

성과지표 계산에서 사용하는 `12`는 월간 수익률을 연간 성과지표로 환산하기 위한 평가 단위이다.

## 5. Benchmark 체계

| 구분 | 전략 | 역할 |
|---|---|---|
| 메인 BM | Fixed 70/20/10 BM | 주식 70%, 국고채 20%, 단기채권 10% 고정 보유 |
| 보조 BM | EW Benchmark | 동일 ETF 3개를 1/3씩 보유 |
| 내부 기준선 | HSI baseline | HSI 상태를 목표비중에 즉시 반영 |
| 최종 후보 | Lambda 0.1 / Lambda 0.3 | HSI 목표비중으로 천천히 이동하는 부분조정 후보 |

## 6. 전체 실험 흐름

00~05번은 데이터 기준, HSI 5상태 분류, baseline 백테스트를 구축한 기본 파이프라인이다. 06~09번은 HSI 상태분류가 신호 조합, 상대속도, event balance 측면에서 납득 가능한지 확인한 진단 실험이다. 10~11번은 Lambda와 Theta를 통해 비중 전환 속도와 상태분류 민감도를 점검한 모델 개선 실험이다. 12~15번은 macro companion과 macro overlay를 통해 외부 거시환경을 보조적으로 반영할 수 있는지 확인한 후속 진단 실험이다. 16번은 최종 후보의 robustness 검증, 17번은 Fixed 70/20/10 BM을 포함한 benchmark alignment 보강 실험이다. 20·21·23번은 최종 후보 선별과 보고서용 산출물 정리 단계이며, 50번대는 전략 입력이 아니라 시장 사건 달력 기반 사후 해석 layer이다.

| 번호 | 실험 목적 | 수행 및 결과 |
|---:|---|---|
| 00 | 프로젝트 기준 고정 | ETF 코드, 경로, 상태명, 수익률 단위, 공통 파라미터를 확인하였다. 이후 모든 실험의 기준 설정 단계로 사용하였다. |
| 01 | 데이터 구조화 | ETF 유니버스, 월말 가격, 월간 수익률, 자산군 표를 생성하였다. HSI 계산과 백테스트에 사용할 입력 데이터를 정리하였다. |
| 02 | Event balance 생성 | 위험 사건과 완화 사건의 균형지표를 만들었다. HSI 상태분류를 보조적으로 해석하기 위한 내부 진단 자료로 사용하였다. |
| 03 | 월말 신호 정렬 | 월말 기준 HSI 입력 신호를 정렬하였다. t월 말 신호를 t+1월 수익률에 적용하는 구조를 마련하였다. |
| 04 | HSI 5상태 분류 | `risk_relief`, `neutral_watch`, `conflict`, `risk_warning`, `accident_zone`의 5상태를 생성하였다. 프로젝트의 핵심 상태분류 결과이다. |
| 05 | HSI baseline 백테스트 | HSI 상태별 ETF 목표비중 규칙을 적용해 baseline 백테스트를 수행하였다. HSI가 실제 자산배분으로 연결될 수 있음을 확인했지만, 즉시 전환 방식이라 Turnover와 MDD 부담이 남았다. |
| 06 | 상대속도 진단 | HSI 신호 변화량과 반응 속도를 점검하였다. 상태 변화가 단순 결과값이 아니라 신호의 변화 흐름과 연결되는지 확인하였다. |
| 07 | 신호 조합 비교 | 여러 신호 조합별 결과를 비교하였다. 특정 신호 하나에 과도하게 의존하지 않는지 확인하는 ablation 성격의 진단을 수행하였다. |
| 08 | Event balance 정합성 진단 | HSI 상태와 event balance 흐름이 서로 납득 가능하게 맞물리는지 확인하였다. HSI 상태 해석을 보조하는 진단 결과로 사용하였다. |
| 09 | Event filter 실험 | baseline 비중 위에 event balance 기반 보조 필터를 적용할 수 있는지 점검하였다. 최종 후보라기보다 보조 후보 또는 해석용 실험으로 정리하였다. |
| 10 | Lambda 부분조정 실험 | 목표비중으로 즉시 이동하지 않고 `λ`만큼 일부 조정하는 방식을 실험하였다. HSI baseline의 급격한 비중 전환을 완화하는 핵심 개선 실험이다. |
| 11 | Theta 민감도 실험 | HSI 상태분류 기준인 `θ` 변화에 따라 상태분포와 성과가 얼마나 민감하게 바뀌는지 확인하였다. 상태분류의 robustness를 점검하는 실험이다. |
| 12 | Macro companion layer 생성 | 금리·환율·GDP 기반 macro 보조 layer를 만들었다. HSI를 대체하는 모델이 아니라, 외부 거시환경을 함께 해석하기 위한 보조장치로 정리하였다. |
| 13 | HSI × macro diagnostic | HSI 위험상태와 macro 위험신호가 얼마나 겹치는지 진단하였다. HSI 위험 판단이 외부 macro 환경과 어느 정도 일치하는지 확인했고, 14번 macro overlay의 근거가 되었다. |
| 14 | Macro overlay no GDP | GDP를 제외하고 금리·환율 중심의 macro 보정값을 HSI baseline 비중 위에 소폭 반영하였다. HSI 상태는 유지하고 위험자산 비중만 작게 조정하는 soft overlay 실험으로 수행하였다. |
| 15 | Lambda + macro overlay | Lambda 0.1 / 0.3 후보 위에 macro overlay 강도를 달리 적용하였다. macro_scale별 trade-off를 확인했으며, 최종 후보를 대체하기보다는 후속 진단 실험으로 정리하였다. |
| 16 | Regime robustness 검증 | Lambda 0.1과 Lambda 0.3을 기간별, HSI 상태별, 큰 손실월 기준으로 점검하였다. 최종 후보가 무너지지 않았고, Lambda 0.1은 저회전·방어형, Lambda 0.3은 균형형 후보로 역할이 분리되었다. |
| 17 | Benchmark alignment 보강 | Fixed 70/20/10 BM을 메인 BM으로 추가하고, EW Benchmark, HSI baseline, Lambda 0.1, Lambda 0.3을 같은 기준으로 비교하였다. Fixed BM은 CAGR이 높지만 MDD가 크고, Lambda 후보는 수익률 극대화보다 낙폭 대비 성과 개선에 의미가 있음을 확인하였다. |
| 20 | 최종 후보 선별 | 거래비용, Turnover, 성과지표를 함께 고려해 후보를 압축하였다. HSI 기반 전략을 실제 운용 가능성 기준에서 추려내는 모델 셀렉션 단계이다. |
| 21 | 후보별 보고서 표·그림 생성 | 후보 전략별 보고서용 표와 그림을 생성하였다. Lambda 후보들을 발표 가능한 산출물 형태로 정리하였다. |
| 23 | 보고서용 후보표 정리 | shortlist, 비용 민감도, Lambda family 표를 정리하였다. 최종 후보 판단을 보고서에 넣을 수 있는 형태로 정리한 실험이다. |
| 50번대 | 시장 사건 달력 기반 사후 해석 | 외부 시장 사건 달력과 HSI 상태를 대조하였다. 전략 입력값으로 사용하지 않고, HSI 상태 변화가 실제 시장 사건 구간에서 납득 가능한지 설명하는 사후 해석·시각화 layer로 둔다. |

이 실험 흐름에서 핵심은 HSI baseline이 최종 전략으로 채택된 것이 아니라는 점이다. baseline은 HSI 상태가 ETF 비중 조절로 연결될 수 있음을 확인하는 내부 기준선이다. 이후 Lambda 부분조정을 통해 baseline의 급격한 비중 전환을 완화하였고, 최종적으로 Lambda 0.1과 Lambda 0.3이 서로 다른 성격의 후보로 남았다.

Lambda 0.1은 저회전·보수형 운용 후보이며, Lambda 0.3은 수익성과 Calmar 측면의 균형형 후보이다. Macro companion과 event balance는 HSI를 대체하는 신호가 아니라, HSI 상태와 후보 전략을 해석하기 위한 보조 진단 layer로 사용한다. 17번 Benchmark alignment를 통해 Fixed 70/20/10 BM을 메인 BM으로 추가함으로써, 본 전략이 단순 수익률 극대화 전략이 아니라 낙폭 대비 성과와 운용 안정성을 고려한 방어형 ETF RoboAdvisor 후보임을 더 명확히 정리하였다.


## 7. 16번 Regime robustness 요약

16번 실험은 새 후보를 만드는 실험이 아니라, 최종 후보로 남은 Lambda 0.1과 Lambda 0.3을 기간별·HSI 상태별·큰 손실월 기준으로 흔들어 보는 검증 실험이다.

| 전략 | CAGR | MDD | Sharpe | Calmar | 평균 Turnover |
|---|---:|---:|---:|---:|---:|
| EW Benchmark | 6.59% | -13.57% | 0.834 | 0.486 | 0.00% |
| HSI baseline | 7.83% | -23.46% | 0.613 | 0.334 | 22.02% |
| Lambda 0.1 | 8.69% | -14.74% | 0.787 | 0.590 | 2.46% |
| Lambda 0.3 | 9.15% | -15.22% | 0.779 | 0.601 | 6.89% |

핵심 해석은 다음과 같다.

```text
Lambda 0.3 = 전체 CAGR·Calmar 우위 후보
Lambda 0.1 = 저회전·MDD·큰 손실월 방어 후보
EW Benchmark = Sharpe 기준으로 여전히 강한 비교 기준
HSI baseline = 상태를 비중으로 연결하는 기준선이나 Turnover와 MDD 부담이 큼
```

## 8. 17번 Benchmark alignment 요약

17번 실험은 Fixed 70/20/10 BM을 추가하여 최종 비교 기준을 정렬한 실험이다.

| 전략 | CAGR | MDD | Sharpe | Calmar | 평균 Turnover | 역할 |
|---|---:|---:|---:|---:|---:|---|
| Fixed 70/20/10 BM | 11.05% | -25.67% | 0.710 | 0.431 | 0.00% | 메인 BM |
| EW Benchmark | 6.59% | -13.57% | 0.834 | 0.486 | 0.00% | 보조 BM |
| HSI baseline | 7.83% | -23.46% | 0.613 | 0.334 | 22.02% | 내부 기준선 |
| Lambda 0.1 | 8.69% | -14.74% | 0.787 | 0.590 | 2.46% | 후보 |
| Lambda 0.3 | 9.15% | -15.22% | 0.779 | 0.601 | 6.89% | 후보 |

Fixed 70/20/10 BM은 CAGR이 가장 높았지만 MDD도 가장 컸다. 반면 Lambda 0.1과 Lambda 0.3은 Fixed BM보다 CAGR은 낮았지만 MDD를 크게 낮추고 Calmar를 개선하였다.

## 9. 최종 후보 역할 분담

| 후보 | 역할 | 강점 | 약점 | 최종 판단 |
|---|---|---|---|---|
| Fixed 70/20/10 BM | 메인 BM | CAGR 최고 | MDD 큼 | 비교 기준 |
| EW Benchmark | 보조 BM | Sharpe 최고, MDD 안정 | CAGR 낮음 | 비교 기준 |
| HSI baseline | 내부 기준선 | HSI 상태→비중 연결 가능 | MDD·Turnover 부담 큼 | 최종 후보 아님 |
| Lambda 0.1 | 저회전·보수형 후보 | Turnover 낮음, 큰 손실월 방어 | CAGR은 0.3보다 낮음 | 최종 후보 |
| Lambda 0.3 | 균형형 후보 | CAGR·Calmar 우위 | MDD·Turnover는 0.1보다 높음 | 최종 후보 |
| Lambda + macro | 보조 진단 후보 | MDD 소폭 개선 | CAGR·Calmar·Turnover 비용 발생 | 부록/후속 |

## 10. 최종 결론

본 프로젝트는 HSI를 미래 수익률 예측기로 사용하지 않았다. HSI는 가격 기반 신호를 이용해 시장상태를 해석하는 내부 합성지표이며, ETF 위험자산 비중 조절을 돕는 overlay 보조지표로 사용하였다.

HSI baseline은 HSI 상태를 ETF 목표비중으로 연결할 수 있음을 보여주었지만, 목표비중으로 즉시 이동하는 구조 때문에 MDD와 Turnover 부담이 컸다. 이에 따라 λ 부분조정을 적용하였고, Lambda 0.1과 Lambda 0.3이 최종 후보로 남았다.

```text
HSI baseline 자체가 최종 전략은 아니다.
HSI 상태분류는 시장상태를 ETF 비중 행동으로 번역하는 기준이다.
λ overlay는 baseline의 과격한 비중 전환을 완화하는 핵심 개선 장치이다.
Lambda 0.1과 Lambda 0.3은 운용 목적에 따라 구분되는 최종 우선 후보이다.
```
