# Multi-Camera Person Tracking & Re-ID CCTV

> **Team Project**  
> 실제 소스 코드와 공동 커밋 이력은 [원본 팀 저장소](https://github.com/realisshoon/jetson-multicam-re_id-tracking)에서 확인할 수 있습니다.

## Project Summary

여러 카메라 구간을 이동하는 사람을 실시간으로 탐지·추적하고, 카메라가 달라져도 동일인인지 판단하여 이동 경로의 정상 여부를 확인하는 시스템입니다.

단순 객체 검출을 넘어 **동일인 연결, 이동 방향, 이동 시간, 경로 이탈과 미도착 여부**를 종합적으로 판단하도록 구성했습니다.

## Hardware

- NVIDIA Jetson Orin Nano Developer Kit × 4
- Logitech C270 HD Webcam × 4
- 카메라 1대와 Jetson 1대를 하나의 독립 노드로 구성

## System Flow

1. **Person Detection** — YOLO로 사람 객체 탐지
2. **Single-Camera Tracking** — ByteTrack으로 카메라 내부 Track ID 유지
3. **Feature Extraction** — OSNet Re-ID로 외형 임베딩 추출
4. **Event Transfer** — MQTT를 통해 입장·퇴장·시간·방향 이벤트 전달
5. **Cross-Camera Matching** — 외형, 시간, 방향과 예상 경로를 결합해 동일인 판단
6. **Route Monitoring** — 지연, 미도착, 경로 이탈 등의 이상 상황 표시

## Route Scenario

- **Route 1:** A → B → D
- **Route 2:** A → C → D
- 각 노드는 독립적으로 영상을 처리하고 중앙 시스템이 카메라 간 이동 이벤트를 연결합니다.

## Core Technologies

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

## Key Features

- 다중 카메라 환경에서 사람 이동 연결
- 외형 특징과 시간·방향 조건을 결합한 동일인 판단
- 카메라별 독립 Edge AI 처리
- 경로 이탈과 예상 시간 초과 감지
- ENTRY/EXIT 이벤트 및 대시보드 연동

## Repository & Ownership

- **Original Repository:** [realisshoon/jetson-multicam-re_id-tracking](https://github.com/realisshoon/jetson-multicam-re_id-tracking)
- **Project Type:** Team Project
- 팀 프로젝트의 공동 작업 기록을 보존하기 위해 코드를 개인 저장소로 복사하지 않았습니다.
