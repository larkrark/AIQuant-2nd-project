# Adoption Decision 마진 민감도 분석 노트

34_adoption_decision.py의 4개 마진(calmar_ratio_min=0.90, mdd_worsen_max_pp=2.0, tail_worsen_max_pp=0.3, turnover_cap_mult=1.5)은 판정 기준으로만 문서화되어 있고 산출식은 없다. 본 분석은 각 마진을 baseline보다 엄격한 방향으로 강화했을 때, 각 후보(특히 dynamic_v1)가 몇 단계까지 non-inferior 판정을 유지하는지 확인한다.

## Breaking point 요약

| 마진 | 후보 | baseline | 강화 방향 | 최초 탈락 지점 | grid 끝까지 통과 |
|---|---|---:|---|---|---|
| calmar_ratio_min | asym_up0.1_down0.3 | 0.9 | increasing | nan | True |
| calmar_ratio_min | asym_up0.1_down0.5 | 0.9 | increasing | nan | True |
| calmar_ratio_min | asym_up0.2_down0.3 | 0.9 | increasing | nan | True |
| calmar_ratio_min | dynamic_v1 | 0.9 | increasing | nan | True |
| calmar_ratio_min | dynamic_v1_macro | 0.9 | increasing | nan | True |
| mdd_worsen_max_pp | asym_up0.1_down0.3 | 2.0 | decreasing | nan | True |
| mdd_worsen_max_pp | asym_up0.1_down0.5 | 2.0 | decreasing | nan | True |
| mdd_worsen_max_pp | asym_up0.2_down0.3 | 2.0 | decreasing | nan | True |
| mdd_worsen_max_pp | dynamic_v1 | 2.0 | decreasing | nan | True |
| mdd_worsen_max_pp | dynamic_v1_macro | 2.0 | decreasing | nan | True |
| tail_worsen_max_pp | asym_up0.1_down0.3 | 0.3 | decreasing | nan | True |
| tail_worsen_max_pp | asym_up0.1_down0.5 | 0.3 | decreasing | nan | True |
| tail_worsen_max_pp | asym_up0.2_down0.3 | 0.3 | decreasing | nan | True |
| tail_worsen_max_pp | dynamic_v1 | 0.3 | decreasing | nan | True |
| tail_worsen_max_pp | dynamic_v1_macro | 0.3 | decreasing | 0.1 | False |
| turnover_cap_mult | asym_up0.1_down0.3 | 1.5 | decreasing | nan | True |
| turnover_cap_mult | asym_up0.1_down0.5 | 1.5 | decreasing | nan | True |
| turnover_cap_mult | asym_up0.2_down0.3 | 1.5 | decreasing | nan | True |
| turnover_cap_mult | dynamic_v1 | 1.5 | decreasing | nan | True |
| turnover_cap_mult | dynamic_v1_macro | 1.5 | decreasing | nan | True |

## 해석 (초안)

[TODO] dynamic_v1이 grid 끝까지(가장 엄격한 값에서도) 통과한다면, adoption 마진을 다소 엄격하게 잡았어도 채택 결론이 바뀌지 않는다는 근거가 된다. 반대로 baseline 근처에서 바로 탈락한다면, 그 마진이 결론을 좌우하는 취약한 지점이므로 보고서에서 '이 마진 설정에 결론이 의존적'이라고 정직하게 밝혀야 한다.
