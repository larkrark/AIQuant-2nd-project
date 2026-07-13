# 대시보드 배포방법 변경 검토: Streamlit Community Cloud 대안 비교

작성일: 2026-07-12

## 배경

현재 대시보드(`docs/tab/*.py`)는 Streamlit Community Cloud(구 Streamlit Share)에 배포되어 있다. 무료 티어는 약 12시간 무접속 시 앱이 sleep 상태로 전환되어, 접속자가 "wake up" 버튼을 누르고 재기동을 기다려야 한다. 팀원·외부 열람자 경험이 나빠 대안을 검토한다.

참고: 본 대시보드는 정적 CSV(`docs/tab/*.csv`)만 읽고 실시간 데이터 수집이 없다. 따라서 서버리스(정적) 배포도 기술적으로 가능하다.

## 대안 비교

| 항목 | ① Streamlit Cloud 유지 + keep-alive | ② Hugging Face Spaces | ③ GitHub Pages + stlite | ④ Render 무료 티어 |
|---|---|---|---|---|
| 비용 | 무료 | 무료 (CPU basic: 2 vCPU / 16GB RAM) | 무료 | 무료 |
| Sleep 정책 | 12h sleep이나 ping으로 방지 | 48h 무접속 시 sleep, **방문 시 자동 기상** | 서버 없음 — 절대 안 잠듦 | 15분 무접속 시 spin-down, 월 750시간 제한 |
| 수동으로 켜야 하나 | 아니오 (Actions가 대신 ping) | 아니오 (자동 기상, 수십 초 대기) | 아니오 | 아니오 (단, 재기동 ~1분 대기 잦음) |
| 이전 작업량 | 워크플로 YAML 1개 추가 | repo 푸시 + Space 생성 (코드 수정 거의 없음) | CSV 로딩을 raw URL fetch로 수정, index.html 구성 | Dockerfile 또는 시작 명령 설정 |
| 리소스 | ~2.7GB RAM | 16GB RAM — 가장 넉넉 | 사용자 브라우저에서 실행 (Pyodide/WASM) | 512MB RAM 수준 |
| 단점 | 근본 해결 아님, ping 워크플로 관리 필요 | HF 계정 필요, 48h 이상 무접속이면 첫 방문자는 로딩 대기 | 초기 로딩 느림(패키지 다운로드), 일부 패키지 미지원 가능 | 현재보다 더 자주 잠듦 — **비추천** |

## 각 안 상세

### ① Streamlit Cloud 유지 + GitHub Actions keep-alive

현 배포를 그대로 두고, GitHub Actions cron으로 4~6시간마다 앱 URL에 접속(또는 Selenium으로 wake 버튼 클릭)해 sleep을 방지한다. 변경 비용이 가장 낮지만 플랫폼 정책 변경에 취약하고, 우회책 성격이라 장기 해법으로는 부적합하다.

### ② Hugging Face Spaces (권장)

Streamlit SDK를 공식 지원하므로 repo를 Space에 푸시하면 그대로 동작한다. `requirements.txt`만 맞추면 되고, 무료 사양(16GB RAM)이 Streamlit Cloud보다 훨씬 넉넉하다. 48시간 무접속 시 sleep하지만 방문자가 접속하면 자동으로 재기동되므로 운영자가 수동으로 켤 필요가 없다. 팀 공유용 저트래픽 대시보드에 가장 무난하다.

### ③ GitHub Pages + stlite

stlite는 Pyodide(WASM)로 Streamlit을 브라우저 안에서 실행한다. 서버가 없으므로 sleep 개념 자체가 없고 GitHub Pages에 정적 파일로 올리면 끝이다. 본 대시보드처럼 정적 CSV + pandas + plotly 구성과 잘 맞는다. 단, CSV를 로컬 경로 대신 raw.githubusercontent.com URL에서 fetch하도록 수정해야 하고, 첫 로딩 시 브라우저가 Python 패키지를 내려받아 수십 초 걸린다. plotly는 버전 고정(`plotly==5.*`)이 필요할 수 있다.

### ④ Render 무료 티어

15분 무접속 시 spin-down되어 현재보다 오히려 자주 멈춘다. 검토 제외.

## 결론

- 최소 변경으로 당장 문제를 없애려면 **①(keep-alive)**.
- 제대로 이전한다면 **②(HF Spaces)** — 코드 수정 거의 없이 자동 기상 + 넉넉한 리소스.
- 유지보수 제로·영구 무료를 원하면 **③(stlite)** — 단, 코드 수정과 초기 로딩 트레이드오프 감수.

## 출처

- [Streamlit Community Cloud](https://streamlit.io/cloud)
- [Streamlit 포럼: 앱 sleep 관련 논의](https://discuss.streamlit.io/t/web-apps-keeps-on-sleeping-after-30-minutes-or-a-day-of-inactivity/97350)
- [GitHub Actions + Selenium keep-alive 방법](https://dev.to/virgoalpha/keeping-your-streamlit-app-awake-using-selenium-and-github-actions-4ajd)
- [KDnuggets: 무료 Python 앱 호스팅 5가지](https://www.kdnuggets.com/5-free-ways-to-host-a-python-application)
- [stlite (In-browser Streamlit)](https://github.com/whitphx/stlite)
- [stlite GitHub Pages 배포 가이드](https://webapps.hsma.co.uk/stlite_github_pages.html)
