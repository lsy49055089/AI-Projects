# Jetson AI Rock–Paper–Scissors

Jetson에서 손 영상을 TensorRT로 분류하고, 추론 결과를 4가지 모드의 웹 게임과 연결했습니다.

## 개요

| 항목 | 내용 |
|---|---|
| 기술 | Jetson Orin Nano · Python · MobileNetV2 · TensorRT/PyCUDA · OpenCV · Flask |


## 담당 역할

- TensorRT 손 영상 분류와 게임 입력 연동
- 1인전·2인전·하나 빼기·묵찌빠의 상태·승패 처리
- Flask 영상 스트리밍과 모드 선택·게임 UI 연동


## 설계·구현

### 핵심 기능

- **4가지 게임 모드**: 1인전, 2인전, 하나 빼기, 묵찌빠
- **온디바이스 추론**: Jetson Orin Nano에서 TensorRT 엔진 실행
- **실시간 손 인식**: USB 카메라 영상에서 손 영역 검출 및 가위·바위·보 분류
- **웹 스트리밍 UI**: Flask를 이용해 같은 네트워크의 PC 브라우저에서 게임 화면 확인
- **게임 상태 관리**: 카운트다운, 다수결 판정, 점수 계산, 라운드 및 승패 처리

### 게임 모드

| 모드 | 구성 | 승리 조건 |
|---|---|---|
| 1 Player | 사용자 대 CPU | 먼저 2점 획득 |
| 2 Players | 사용자 1 대 사용자 2 | 먼저 2점 획득 |
| One Out | 두 손을 낸 뒤 한 손을 선택하는 하나 빼기 | 먼저 2점 획득 |
| Muk Jji Ppa | 공격권을 반영한 묵찌빠 | 먼저 2점 획득 |

모드 선택 화면에서 손가락 1~4개를 약 1초간 유지하면 해당 모드를 선택할 수 있습니다.

### 기술 구성

- Device: NVIDIA Jetson Orin Nano
- Camera: USB Camera (`/dev/video0`, 640×480)
- Model: MobileNetV2, 3 classes (`SCISSORS`, `ROCK`, `PAPER`)
- Inference: NVIDIA TensorRT, PyCUDA
- Vision: OpenCV, cvzone HandDetector
- Web: Flask streaming server (`8090`)


## 검증 결과

<a id="실행검증-근거"></a>

### 소스·실행 자산 검사

자동 검사는 Python 구문, 엔진 무결성, 필수 UI 자산을 확인합니다.

| Check | Result |
|---|---:|
| Python source syntax | **PASS** |
| TensorRT engine size | **5,264,692 bytes** |
| TensorRT engine SHA-256 | `db398d57…ff1780b4` |
| UI assets | **3 / 3 present** |

```bash
python AI/jetson-rps-game/scripts/validate_package.py
```

GitHub Actions는 push/PR마다 Python 구문, 엔진 무결성, 필수 UI 자산을 검사합니다. 카메라 추론과 게임 실행에는 Jetson의 TensorRT·CUDA·JetPack 호환 환경이 필요합니다.


## 실행 방법

### Jetson 실행

Jetson에 TensorRT, PyCUDA 및 카메라 환경을 구성한 뒤 저장소 루트에서 실행합니다.

```bash
cd AI/jetson-rps-game/app
python RPS_Web_4mode.py
```

실행 후 같은 네트워크의 PC 브라우저에서 아래 주소로 접속합니다.

```text
http://<JETSON_IP>:8090
```

### 조작 방법

- `SPACE`: 시작
- `R`: 현재 게임 재시작
- `M`: 모드 선택 화면
- `Q`: 프로그램 종료

> TensorRT 엔진은 생성 당시의 JetPack·TensorRT·CUDA 및 Jetson 환경과의 호환성이 필요할 수 있습니다.

### 프로젝트 구조

```text
jetson-rps-game/
├── RPS_MobileNetV2_Upgrade.engine
├── README.md
├── requirements.txt
├── model-manifest.json
├── scripts/
│   └── validate_package.py
└── app/
    ├── RPS_Web_4mode.py
    ├── trt_module.py
    └── assets/
        ├── paper.png
        ├── rock.png
        └── scissors.png
```


---

[웹 포트폴리오](https://seungyeol-rtl-portfolio.azuretide33.chatgpt.site) · [GitHub 프로필](https://github.com/lsy49055089)

[논문](https://github.com/lsy49055089/Parallel-Decision-Tree-Hardware) · [RTL / FPGA Design](https://github.com/lsy49055089/RTL-Design-Projects) · [Design Verification](https://github.com/lsy49055089/RTL-Verification-Projects) · [Embedded Systems](https://github.com/lsy49055089/Embedded-Systems-Projects) · [AI / CV](https://github.com/lsy49055089/AI-Projects)
