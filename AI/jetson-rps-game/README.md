# Jetson AI Rock–Paper–Scissors

NVIDIA Jetson Orin Nano와 USB 카메라를 이용해 사용자의 손을 실시간으로 검출하고, MobileNetV2 기반 TensorRT 엔진으로 가위·바위·보를 분류하는 온디바이스 AI 게임입니다.

## 핵심 기능

- **4가지 게임 모드**: 1인전, 2인전, 하나 빼기, 묵찌빠
- **온디바이스 추론**: Jetson Orin Nano에서 TensorRT 엔진 실행
- **실시간 손 인식**: USB 카메라 영상에서 손 영역 검출 및 가위·바위·보 분류
- **웹 스트리밍 UI**: Flask를 이용해 같은 네트워크의 PC 브라우저에서 게임 화면 확인
- **게임 상태 관리**: 카운트다운, 다수결 판정, 점수 계산, 라운드 및 승패 처리

## 게임 모드

| 모드 | 구성 | 승리 조건 |
|---|---|---|
| 1 Player | 사용자 대 CPU | 먼저 2점 획득 |
| 2 Players | 사용자 1 대 사용자 2 | 먼저 2점 획득 |
| One Out | 두 손을 낸 뒤 한 손을 선택하는 하나 빼기 | 먼저 2점 획득 |
| Muk Jji Ppa | 공격권을 반영한 묵찌빠 | 먼저 2점 획득 |

모드 선택 화면에서 손가락 1~4개를 약 1초간 유지하면 해당 모드를 선택할 수 있습니다.

## 기술 구성

- Device: NVIDIA Jetson Orin Nano
- Camera: USB Camera (`/dev/video0`, 640×480)
- Model: MobileNetV2, 3 classes (`SCISSORS`, `ROCK`, `PAPER`)
- Inference: NVIDIA TensorRT, PyCUDA
- Vision: OpenCV, cvzone HandDetector
- Web: Flask streaming server (`8090`)

## 프로젝트 구조

```text
jetson-rps-game/
├── RPS_MobileNetV2_Upgrade.engine
├── README.md
├── requirements.txt
└── app/
    ├── RPS_Web_4mode.py
    ├── trt_module.py
    └── assets/
        ├── paper.png
        ├── rock.png
        └── scissors.png
```

## 실행 방법

Jetson에 TensorRT, PyCUDA 및 카메라 환경이 구성되어 있어야 합니다.

```bash
cd jetson-rps-game/app
python RPS_Web_4mode.py
```

실행 후 같은 네트워크의 PC 브라우저에서 아래 주소로 접속합니다.

```text
http://<JETSON_IP>:8090
```

## 조작 방법

- `SPACE`: 시작
- `R`: 현재 게임 재시작
- `M`: 모드 선택 화면
- `Q`: 프로그램 종료

> TensorRT 엔진은 생성 당시의 JetPack·TensorRT·CUDA 및 Jetson 환경과의 호환성이 필요할 수 있습니다.
