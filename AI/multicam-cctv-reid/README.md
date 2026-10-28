# Multi-Camera Re-ID Tracking

여러 카메라의 인물 이동을 연결하는 시스템에서 OSNet 추론 인터페이스, MQTT·Camera A/B 초기 구현과 Jetson 검증 스크립트를 담당했습니다.

## 개요

| 항목 | 내용 |
|---|---|
| 형태 | 팀 프로젝트 |
| 기술 | Jetson Orin Nano · Python · YOLO · ByteTrack · OSNet · MQTT |

<a id="project-summary"></a>

여러 카메라 구간을 이동하는 사람을 실시간으로 탐지·추적하고, 카메라가 달라져도 동일인인지 판단하여 이동 경로의 정상 여부를 확인하는 시스템입니다.

단순 객체 검출을 넘어 **동일인 연결, 이동 방향, 이동 시간, 경로 이탈과 미도착 여부**를 종합적으로 판단하도록 구성했습니다.


## 담당 역할

<a id="my-contribution"></a>

- OSNet Re-ID 전처리·추론 인터페이스와 모델 metadata/manifest 초기 구성
- MQTT Client 및 Camera A/B Node prototype 구현
- Jetson 카메라·환경·Re-ID·YOLO Tracking 검증 스크립트 구성
- [초기 구현 커밋](https://github.com/realisshoon/jetson-multicam-re_id-tracking/commit/0c1673e7f7deb00a5881e4a9f1cd4cb55fc36269) · [실측 이동 시간 문서화](https://github.com/realisshoon/jetson-multicam-re_id-tracking/commit/fc56dbb30904e7188845384fea71b0c3afdf629b)


## 설계·구현

<a id="hardware"></a>

### 하드웨어

- NVIDIA Jetson Orin Nano Developer Kit × 4
- Logitech C270 HD Webcam × 4
- 카메라 1대와 Jetson 1대를 하나의 독립 노드로 구성

<a id="system-flow"></a>

### 데이터 흐름

1. **Person Detection** — YOLO로 사람 객체 탐지
2. **Single-Camera Tracking** — ByteTrack으로 카메라 내부 Track ID 유지
3. **Feature Extraction** — OSNet Re-ID로 외형 임베딩 추출
4. **Event Transfer** — MQTT를 통해 입장·퇴장·시간·방향 이벤트 전달
5. **Cross-Camera Matching** — 외형, 시간, 방향과 예상 경로를 결합해 동일인 판단
6. **Route Monitoring** — 실측 이동 시간 범위와 경로 이탈·미도착 상태 확인

<a id="route-scenario"></a>

### 경로 시나리오

- **Route 1:** A → B → D
- **Route 2:** A → C → D
- 각 노드는 독립적으로 영상을 처리하고 중앙 시스템이 카메라 간 이동 이벤트를 연결합니다.

<a id="core-technologies"></a>

### 기술 구성

| Area | Technology |
|---|---|
| Object Detection | YOLO |
| Tracking | ByteTrack |
| Person Re-ID | OSNet |
| Face Processing | YuNet / SFace |
| Image Processing | OpenCV |
| Edge Device | Jetson Orin Nano |
| Event Communication | MQTT |
| Language | Python |

<a id="key-features"></a>

### 주요 기능

- 다중 카메라 환경에서 사람 이동 연결
- 외형 특징과 시간·방향 조건을 결합한 동일인 판단
- 카메라별 독립 Edge AI 처리
- 경로 이탈과 B/C→D 구간의 실측 이동 시간 범위 검증
- ENTRY/EXIT 이벤트 및 대시보드 연동


## 검증 결과

Jetson 카메라·실행 환경·Re-ID·YOLO Tracking의 검증 스크립트를 구성하고, B/C→D 구간의 실측 이동 시간 범위를 문서화했습니다.

[검증 스크립트 초기 구현](https://github.com/realisshoon/jetson-multicam-re_id-tracking/commit/0c1673e7f7deb00a5881e4a9f1cd4cb55fc36269) · [실측 이동 시간 기록](https://github.com/realisshoon/jetson-multicam-re_id-tracking/commit/fc56dbb30904e7188845384fea71b0c3afdf629b)


## 실행 방법

<a id="repository--ownership"></a>

### 소스와 실행 자료

- **Original Repository:** [realisshoon/jetson-multicam-re_id-tracking](https://github.com/realisshoon/jetson-multicam-re_id-tracking)
- **Project Type:** Team Project
- **Source:** Python 구현과 공동 작업 이력은 원본 팀 저장소에서 확인할 수 있습니다.


---

[웹 포트폴리오](https://seungyeol-rtl-portfolio.azuretide33.chatgpt.site) · [GitHub 프로필](https://github.com/lsy49055089)

[논문](https://github.com/lsy49055089/Parallel-Decision-Tree-Hardware) · [RTL / FPGA Design](https://github.com/lsy49055089/RTL-Design-Projects) · [Design Verification](https://github.com/lsy49055089/RTL-Verification-Projects) · [Embedded Systems](https://github.com/lsy49055089/Embedded-Systems-Projects) · [AI / CV](https://github.com/lsy49055089/AI-Projects)
