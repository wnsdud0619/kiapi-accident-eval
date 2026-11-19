# 자율주행 사고재현 S/W 통합 신뢰성 검증 플랫폼

실사고 기준 데이터(DSSAD/EDR)와 교통사고 재현 S/W 출력 데이터(위치·속도 CSV)를 동일 시간축 및 좌표계에서 정합하여 정량 지표 산출과 시각화를 수행하는 Streamlit 기반 검증 애플리케이션입니다.

## 구성 파일

- `app.py`: Streamlit 웹 UI 및 정합·평가 지표 연산 코드
- `run_app.py`: 주소창 없는 앱 창 실행 런처 (단일 `.exe` 패키징 진입점 겸용)
- `PNG/Wordmark.png`: 상단 헤더 로고 이미지
- `requirements.txt`: 실행에 필요한 Python 패키지 목록
- `test_data/시나리오 1~5/`: 시나리오별 시험용 기준(DSSAD)·재현 결과(위치/속도) CSV 데이터셋 (15개 파일)

## Windows 단일 실행 파일(`.exe`) 다운로드 및 실행

Python이나 별도 라이브러리가 설치되어 있지 않은 다른 Windows PC에서도 **`.exe` 파일 1개만 복사해 바로 실행**할 수 있습니다.

- **릴리스 페이지:** [v1.0.0 Releases](https://github.com/wnsdud0619/kiapi-accident-eval/releases/tag/v1.0.0)
- **직접 다운로드:** [KIAPI_Accident_Eval.exe (108.75 MiB)](https://github.com/wnsdud0619/kiapi-accident-eval/releases/download/v1.0.0/KIAPI_Accident_Eval.exe)
  - GitHub 일반 Git 커밋의 파일당 `100 MiB` 제한으로 인해 실행 파일은 GitHub Releases 에셋으로 배포됩니다.
  - 로컬 빌드 시 파일명은 `사고재현_검증플랫폼.exe`이며, GitHub 다운로드 시 한글 치환 방지를 위해 영문 파일명(`KIAPI_Accident_Eval.exe`, 표시 라벨 `사고재현_검증플랫폼.exe`)으로 제공됩니다.

### 실행 동작 및 참고 사항

1. **실행 방식:** `.exe`를 더블클릭하면 내부 로컬 서버(`127.0.0.1` 임의 포트)를 실행한 뒤, PC에 설치된 Microsoft Edge 또는 Google Chrome의 `--app` 모드(주소창 없는 독립 앱 창, `1480×920`)로 화면을 엽니다. Edge/Chrome을 찾지 못하면 기본 웹 브라우저로 열립니다.
2. **초기 기동 시간:** `--onefile` 단일 파일 압축 해제 특성상 더블클릭 후 앱 창이 뜨기까지 **약 20초 내외**가 걸릴 수 있습니다.
3. **종료 및 작업 경로:** 앱 창을 닫으면 백그라운드 로컬 서버 프로세스도 함께 종료됩니다. 실행 로그(`app.log`)와 격리된 빈 작업 디렉터리(`workdir`)는 `%LOCALAPPDATA%\KIAPI_Accident_Eval\` 아래에 생성됩니다.
4. **Windows SmartScreen 안내:** 코드 서명이 없는 내부 배포용 실행 파일이므로 PC에 따라 `Windows의 PC 보호` 창이 나타날 수 있으며, 이 경우 **추가 정보 → 실행**으로 실행할 수 있습니다.

## 시나리오 테스트 데이터 (`test_data/시나리오 1~5/`)

[`test_data`](test_data) 폴더에는 `시나리오 1`부터 `시나리오 5`까지 **총 15개의 CSV 파일**(시나리오당 3개)이 포함되어 있습니다. 참고용 주행 영상(`.mp4`)은 저장소 용량 관리를 위해 제외했습니다.

### 시나리오별 3개 파일 구성

| 파일 패턴 | 역할 | 주요 컬럼 및 주기 | 비고 |
| :--- | :--- | :--- | :--- |
| `3_<N>_Car_1.csv` | **기준 데이터 (DSSAD/EDR)** | `Time`, `GNSS positioning/location-x`, `GNSS positioning/location-y`(100ms, 10 Hz), `ADS-determined vehicle speed`(10ms, 100 Hz), `WheelSpeedFR/FL/RR/RL` 등 | 상단 2행(`Data Type`, `Period`) 메타데이터 포함 (앱에서 헤더 자동 탐지) |
| `tesla_model_y_DrivingPath_*.csv` | **재현 S/W 위치·궤적** | `frame`, `time(s)`(20ms, 50 Hz), `gnss_src_x(m)`, `gnss_src_y(m)`, `gnss_x(m)`, `gnss_y(m)`, `simulationPosition`, `simulationAngle` | 앱 기본 위치 컬럼으로 `gnss_src_x(m)`, `gnss_src_y(m)` 사용 |
| `tesla_model_y_Essentials_*.csv` | **재현 S/W 속도·상태** | `frame`, `time(s)`(20ms, 50 Hz), `Speed(km/h)`, `RPM(rpm)`, `Gear()`, `Throttle(%)`, `Brake(%)`, `Steering(rad)` | `DrivingPath` 파일과 `frame` 기준으로 자동 병합 |

### 시나리오 1~5 데이터 요약

| 시나리오 | 기준 데이터 (`3_*_Car_1.csv`) | 재현 위치 (`DrivingPath`) | 재현 속도 (`Essentials`) | 특징 |
| :--- | :--- | :--- | :--- | :--- |
| **시나리오 1** | `3_1_Car_1.csv`<br>2,654행 · `27.85~41.12s` · GNSS 133점 · `0.0~29.2 km/h` | `tesla_model_y_DrivingPath_2026-11-02_10-01-11.csv`<br>664행 · `0.00~13.26s` | `tesla_model_y_Essentials_2026-11-02_10-01-17.csv`<br>664행 · `0.00~13.26s` · `-0.2~29.2 km/h` | |
| **시나리오 2** | `3_2_Car_1.csv`<br>1,921행 · `17.00~26.60s` · GNSS 97점 · `39.6~45.4 km/h` | `tesla_model_y_DrivingPath_2026-11-02_10-09-18.csv`<br>571행 · `0.00~11.40s` | `tesla_model_y_Essentials_2026-11-02_10-06-23.csv`<br>587행 · `0.00~11.72s` · `0.5~45.8 km/h` | 위치(571행)·속도(587행) 길이 차이 (`outer` 병합) |
| **시나리오 3** | `3_3_Car_1.csv`<br>1,434행 · `49.50~56.66s` · GNSS 72점 · `42.9~49.9 km/h` | `tesla_model_y_DrivingPath_2026-11-02_10-18-06.csv`<br>399행 · `0.00~7.96s` | `tesla_model_y_Essentials_2026-11-02_10-18-17.csv`<br>399행 · `0.00~7.96s` · `-1.5~48.4 km/h` | |
| **시나리오 4** | `3_4_Car_1.csv`<br>2,701행 · `14.00~27.50s` · GNSS 136점 · `0.0~52.5 km/h` | `tesla_model_y_DrivingPath_2026-11-02_10-21-45.csv`<br>676행 · `0.00~13.50s` | `tesla_model_y_Essentials_2026-11-02_10-21-37.csv`<br>676행 · `0.00~13.50s` · `-0.2~51.0 km/h` | |
| **시나리오 5** | `3_5_Car_1.csv`<br>2,771행 · `29.15~43.00s` · GNSS 139점 · `0.0~74.2 km/h` | `tesla_model_y_DrivingPath_2026-11-05_18-15-42.csv`<br>693행 · `0.00~13.84s` | `tesla_model_y_Essentials_2026-11-05_18-15-31.csv`<br>693행 · `0.00~13.84s` · `-0.2~64.4 km/h` | |

### 앱에서 시나리오 데이터 불러오기

1. 앱 좌측 **`1. 데이터 및 프로세스 제어`** 영역에서 **`▶ 기준 데이터 (DSSAD/EDR)`** 업로더에 시나리오 폴더의 `3_<N>_Car_1.csv` 파일을 업로드합니다.
2. **`▶ 재현 S/W 데이터 (최대 2개 파일)`** 업로더에 같은 시나리오 폴더의 `tesla_model_y_DrivingPath_*.csv`와 `tesla_model_y_Essentials_*.csv` **2개 파일을 함께 선택**해 업로드합니다.
3. **`▶ 타임스탬프 동기화 & 샘플링 보정`**의 **`기준 데이터 기반 자동 동기화`**(기본 체크)가 켜져 있으면, 재현 시간(`0.00s~`)에 기준 데이터 시작 시각(예: 시나리오 1은 `+27.85s`)이 자동 적용됩니다. 필요 시 체크를 해제하고 `수동 Time Offset (초)`을 조정합니다.

## 소스 코드 설치 및 실행

```bash
pip install -r requirements.txt
streamlit run app.py
# 또는 주소창 없는 앱 창으로 실행:
python run_app.py
```

## Windows 단일 실행 파일(`.exe`) 빌드 방법

```bash
pip install pyinstaller
pyinstaller --noconfirm --clean --onefile --windowed --name "사고재현_검증플랫폼" ^
  --add-data "app.py;." --add-data "PNG\Wordmark.png;PNG" ^
  --collect-all streamlit --collect-data plotly ^
  --copy-metadata streamlit --copy-metadata plotly --copy-metadata pandas ^
  --copy-metadata numpy --copy-metadata altair --copy-metadata pyarrow ^
  --copy-metadata packaging run_app.py
```

## 주요 기능

1. **데이터 입력 및 정합**
   - 가변 헤더 CSV 자동 파싱(`parse_flexible_csv`) 및 기준/재현 신호 자동 탐지
   - 다중 재현 결과 파일(`frame` / `time(s)` 기준) 병합 및 Time Offset 동기화
   - 이종 샘플링 정합(`align_to_ref`: 허용 오차 내 직접 매칭, 그 외 선형 보간)
2. **시각화 (3개 탭)**
   - 주행 궤적 비교 (GNSS Map View, 1:1 종횡비 고정 옵션)
   - 속도 추종성 비교 (내부 통로 영역 표시)
   - 진행방향 기준 직교 오차 분석 (Frenet Lateral / Longitudinal)
3. **정량 평가 지표**
   - 궤적 `Accuracy(T)`: 기준 궤적 폴리라인까지의 최단거리가 임계거리 `T` 이하인 비율(%)
   - 속도 Corridor 점수: ISO/TS 18571 Corridor 방식(`a0`, `b0`, `k_Z` 설정 가능)
   - 보조 오차 통계: 횡방향·종방향·속도 오차의 MAE, RMSE, 최대 편차
