# CAGR 격차 원인 분해 노트 (dynamic_v1 vs FixedBM_70_20_10)

## 방법론

Final_RA_dynamic_v1과 FixedBM_70_20_10 간 수익률 격차의 원인을 정량적으로 확인하기 위해, 월별 산술 초과수익을 exposure effect와 timing effect로 분해하였다. exposure effect는 시간평균 비중 차이로 설명되는 부분이고, timing effect는 평균 대비 월별 비중 편차가 수익률에 기여한 부분이다. 이 분해는 월별 산술수익 기준 항등식이므로 residual은 사실상 0에 가까웠으며, 최대 잔차는 2.1×10⁻¹⁷ 수준으로 확인되었다.

여기서 timing effect는 dynamic_v1의 실제 월별 비중이 자기 평균비중에서 벗어난 부분이 수익률에 기여한 정도를 의미한다. 이 실제 월별 비중은 HSI 목표비중과 λ 실행규칙이 결합되어 산출된 결과이다. 따라서 본 보고서에서는 timing effect를 HSI 단독의 방향성 기여로 해석하지 않는다.

![월별 초과수익 누적 분해](../output/figures/main_final_cagr_gap_attribution_cumulative.png)

[그림 1. dynamic_v1과 FixedBM_70_20_10 간 월별 초과수익의 누적 exposure/timing 분해]

그림 1은 FULL 구간에서 exposure effect와 timing effect가 시간에 따라 어떻게 누적되었는지 보여준다. exposure effect(적색)는 시간이 지날수록 꾸준히 우하향하여, 위험자산을 구조적으로 적게 보유한 데 따른 손실이 누적적으로 커졌음을 보여준다. 반면 timing effect(청색)는 대체로 우상향하는 흐름을 보여, 월별 비중 조절이 평균노출 손실을 지속적으로 상쇄하는 방향으로 작동했음을 나타낸다. 두 곡선을 더한 값(점선)이 실제 산술 초과수익 누적 경로이며, 두 효과가 상당 부분 상쇄되면서도 순액은 음(-)의 방향에 머문 것을 확인할 수 있다.

![구간별 exposure/timing effect 비교](../output/figures/main_final_cagr_gap_attribution_period_summary.png)

[그림 2. FULL/IS/OOS 구간별 exposure effect와 timing effect 비교]

그림 2는 FULL, IS, OOS 세 구간에서 exposure effect와 timing effect의 크기를 나란히 비교한 것이다. 세 구간 모두 exposure effect는 뚜렷한 음(-)의 값을, timing effect는 뚜렷한 양(+)의 값을 보인다. 특히 OOS 구간의 timing effect가 IS 구간보다 크게 나타나, 검증구간에서도 비중 조절의 상쇄 효과가 약화되지 않았음을 보여준다.

## 구간별 결과

| 구간 | CAGR 격차(%p) | Exposure Effect(%p) | Timing Effect(%p) | Exposure 비중 | Timing 비중 |
|---|---:|---:|---:|---:|---:|
| FULL | -1.25 | -50.14 | +25.80 | 206.0% | -106.0% |
| IS | -0.81 | -9.97 | +0.41 | 104.3% | -4.3% |
| OOS | -2.05 | -44.68 | +29.90 | 302.2% | -202.2% |

[표 1. dynamic_v1 vs FixedBM_70_20_10 CAGR 격차의 exposure/timing 분해 요약]

표 1은 세 구간의 CAGR 격차와, 이를 구성하는 exposure effect·timing effect의 산술 합산치를 정리한 것이다. exposure effect와 timing effect의 비중(%)이 100%를 넘거나 음수로 나타나는 것은 두 효과가 서로 반대 방향으로 상쇄되기 때문이며, 오류가 아니다. FULL 구간에서는 exposure effect가 산술 초과수익의 206.0%에 해당하는 손실을 만들었지만, timing effect가 그중 106.0%를 다시 상쇄한 것으로 해석할 수 있다.

## 해석

FULL 구간에서 exposure effect는 -50.14%p, timing effect는 +25.80%p로 나타났다. 이는 FixedBM 대비 CAGR 열위의 주된 원인이 상태판단 타이밍의 실패라기보다, 방어형 설계에 따라 위험자산을 평균적으로 적게 보유한 데 있었음을 보여준다. 반면 HSI 목표비중과 λ 실행규칙이 결합된 월별 비중 조절 효과는 양(+)의 방향으로 나타나, 평균노출 축소에 따른 손실을 일부 상쇄하였다.

OOS 구간에서도 exposure effect는 -44.68%p, timing effect는 +29.90%p로 나타났다. 이는 검증구간에서 dynamic_v1의 월별 비중 조절이 평균노출 손실을 상당 부분 완화하는 방향으로 작동했음을 시사한다. 다만 이 결과만으로 HSI가 독립적으로 유효한 정보를 제공했다고 단정할 수는 없다. timing effect가 양(+)인 것이 HSI 목표비중 자체의 방향성 때문인지, 또는 변동성·rolling drawdown 조건에 따라 λ가 조절되는 메커니즘만으로도 재현 가능한 결과인지는 이 분해만으로 구분되지 않는다.

따라서 HSI의 독립적 기여를 더 엄밀히 확인하려면 HSI 목표비중을 무작위로 섞고 λ 실행 조건은 그대로 유지하는 ablation test 또는 placebo test가 필요하다. 이 검증에서 실제 dynamic_v1이 무작위 HSI 대조군보다 OOS 성과, MDD, Calmar, tail-month 방어력, rolling 안정성 측면에서 뚜렷하게 우수하다면 HSI 방향 정보의 기여를 더 강하게 주장할 수 있다. 반대로 무작위 대조군과 성과가 유사하다면 HSI의 독립 기여도는 제한적으로 해석해야 한다. (관련 검증 결과는 `main_final_hsi_shuffle_placebo_test_note.md` 참조)

또한 산술 초과수익의 합과 실제 복리 누적수익률 격차 사이에는 compounding interaction이 존재한다. FULL 기준 compounding interaction은 -41.56%p로 나타났다. 이는 계산 오류가 아니라 장기 복리 효과의 비선형성 때문이며, 특히 분석 후반부의 급격한 상승 구간에서 상대적으로 낮은 위험자산 노출이 유지되면서 수익률 격차가 산술 합산보다 크게 확대된 결과로 해석된다.

종합하면, Final_RA_dynamic_v1이 FixedBM_70_20_10 대비 CAGR에서 열위였던 것은 타이밍 실패 때문이라기보다, 방어형 전략 설계에 따른 평균 위험자산 노출 축소의 비용으로 해석하는 것이 적절하다. 다만 양(+)의 timing effect는 HSI와 λ가 결합된 결과이므로, HSI 자체의 독립 기여분은 후속 ablation test를 통해 별도로 확인해야 한다.