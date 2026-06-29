# HSI 회의 공유용 파일 묶음

이 묶음은 아침회의에서 바로 공유하거나, VS Code / GitHub에서 열어 보기 좋도록 Markdown(.md) 형식으로 정리한 파일입니다.

이번 수정본에는 기존 회의 파일 흐름을 유지하면서 다음 내용이 추가되었습니다.

- `buy / watch / caution`을 계산 결과 확인용 1차 라벨로 유지
- 보고서와 정식 1차 테스트에서는 별도 HSI 상태 정의표로 재해석
- HSI를 단순 매매 신호가 아니라 위험 악화·위험 완화·강도·충돌을 해석하는 시장상태 분류 체계로 설명
- `practice/hsi_indicator_generation_practice.ipynb`를 HSI 원신호와 상태명 복구용 참고자료로 정리
- 정식 1차 테스트 전 `hsi_state_definition.csv`, `signal_definition_table.csv`, `signal_direction_table.csv` 필요성 추가

## 추천 확장자

| 용도 | 추천 확장자 | 이유 |
|---|---|---|
| Git / VS Code / 팀 작업 공유 | `.md` | 체크박스와 표가 그대로 보이고, 변경 이력 관리가 쉬움 |
| 최종 제출 / 보고서형 공유 | `.docx` | 표와 문단 배치가 안정적이고, 비개발자에게 공유하기 좋음 |
| 수치 결과 / 필터링 / 정렬 | `.csv` 또는 `.xlsx` | 계산 결과와 표 데이터를 다루기 좋음 |

현재 단계에서는 `.md`가 가장 적합합니다. 코드 저장소에 함께 올리기 쉽고, 체크박스 기반 진행상황을 계속 업데이트하기 좋습니다.

## 파일 구성

| 파일명 | 용도 |
|---|---|
| `01_meeting_agenda.md` | 아침회의 안건 |
| `02_current_progress.md` | 현재까지 완료된 진행상황 |
| `03_next_tasks_checklist.md` | 앞으로 해야 할 일 체크리스트 |
| `04_file_output_map.md` | 입력/출력 파일 위치와 역할 정리 |
| `05_team_message_summary.md` | 데이터 담당자/회의록 담당자/발표자에게 전달할 문구 |
