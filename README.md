# 자율주행 사고재현 S/W 통합 신뢰성 검증 플랫폼

실사고 기준 데이터(DSSAD/EDR)와 교통사고 재현 S/W 출력 데이터(위치·속도 CSV)를 동일 시간축 및 좌표계에서 정합하여 정량 지표 산출과 시각화를 수행하는 Streamlit 기반 검증 애플리케이션입니다.

## 구성 파일

- `app.py`: Streamlit 웹 UI 및 정합·평가 지표 연산 코드
- `PNG/Wordmark.png`: 상단 헤더 로고 이미지
- `requirements.txt`: 실행에 필요한 Python 패키지 목록

## 설치 및 실행

```bash
pip install -r requirements.txt
streamlit run app.py
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
