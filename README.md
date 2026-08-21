# On-Device AI Projects

NVIDIA Jetson Orin Nano에서 구현한 Computer Vision·실시간 추론 프로젝트를 정리한 포트폴리오 저장소입니다.

## Projects

| 프로젝트 | 핵심 내용 | 주요 기술 |
|---|---|---|
| [Jetson AI Rock–Paper–Scissors](./AI/jetson-rps-game) | 손을 실시간으로 분류해 1인전·2인전·하나 빼기·묵찌빠를 제공하는 4모드 웹 게임 | MobileNetV2, TensorRT, OpenCV, Flask |
| [Multi-Camera CCTV Re-ID](./AI/multicam-cctv-reid) | 여러 카메라에서 동일 인물을 연결하고 이동 경로를 판단하는 팀 프로젝트 | YOLO, ByteTrack, OSNet, MQTT |

- [Original CCTV Team Repository](https://github.com/realisshoon/jetson-multicam-re_id-tracking)

각 프로젝트 폴더에는 구현 내용, 실행 환경, 핵심 기술과 원본 코드를 정리했습니다.
