"""
Jetson TensorRT Rock-Paper-Scissors WEB GAME

MODE 1
- 1 PLAYER RPS
- PLAYER VS CPU
- FIRST TO 2

MODE 2
- 2 PLAYER RPS
- P1 VS P2
- FIRST TO 2

MODE 3
- ONE OUT
- PLAYER VS CPU
- FIRST TO 2

MODE 4
- MUK JJI PPA
- PLAYER VS CPU
- MUK-JJI-PPA WIN = 1 POINT
- FIRST TO 2

Browser Controls
SPACE : title -> mode select
R     : restart current mode
M     : mode select
Q     : quit
"""

from __future__ import annotations

import os
import random
import threading
import time

from collections import Counter
from typing import Optional

import cv2
import numpy as np
import pycuda.autoinit  # noqa: F401

from cvzone.HandTrackingModule import HandDetector

from flask import (
    Flask,
    Response,
    jsonify,
    render_template_string,
)

from trt_module import TRTInferenceEngine


# ============================================================
# PATH
# ============================================================

SCRIPT_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

ENGINE_PATH = os.path.join(
    os.path.dirname(SCRIPT_DIR),
    "RPS_MobileNetV2_Upgrade.engine",
)

ASSET_DIR = os.path.join(
    SCRIPT_DIR,
    "assets",
)


RPS_IMAGE_PATHS = {
    "ROCK": os.path.join(
        ASSET_DIR,
        "rock.png",
    ),
    "PAPER": os.path.join(
        ASSET_DIR,
        "paper.png",
    ),
    "SCISSORS": os.path.join(
        ASSET_DIR,
        "scissors.png",
    ),
}


# ============================================================
# BASIC CONFIG
# ============================================================

IMG_SIZE = 224

OFFSET = 20

FRAME_WIDTH = 640
FRAME_HEIGHT = 480


MODE_HOLD_SECONDS = 1.0

CLEAR_HOLD_SECONDS = 0.6

COUNTDOWN_SECONDS = 3.0

CAPTURE_SECONDS = 2.0

RESULT_SECONDS = 2.0


# 먼저 2점
WIN_TARGET = 2

MIN_VOTES = 3


# ============================================================
# ONE OUT
# ============================================================

SELECT_LINE_Y = 230

HANA_CAPTURE_SECONDS = 2.0

HANA_ANIMATION_SECONDS = 0.6

HANA_LINE_MARGIN = 20


# ============================================================
# MUK JJI PPA
# ============================================================

# 묵찌빠 한 번 패 인식 시간
MJP_CAPTURE_SECONDS = 1.5

# 공격권 결과 보여주는 시간
MJP_RESULT_SECONDS = 1.5

# 묵찌빠 1세트 승리 화면
MJP_SET_RESULT_SECONDS = 2.0


# ============================================================
# STATE
# ============================================================

STATE_TITLE = "TITLE"

STATE_MODE_SELECT = "MODE_SELECT"

STATE_WAIT_CLEAR = "WAIT_CLEAR"

STATE_COUNTDOWN = "COUNTDOWN"

STATE_CAPTURE = "CAPTURE"

STATE_RESULT = "RESULT"

STATE_GAME_OVER = "GAME_OVER"


# ONE OUT
STATE_HANA_CAPTURE_TWO = "HANA_CAPTURE_TWO"

STATE_HANA_SELECT = "HANA_SELECT"

STATE_HANA_ANIMATE = "HANA_ANIMATE"


# MUK JJI PPA
STATE_MJP_COUNTDOWN = "MJP_COUNTDOWN"

STATE_MJP_CAPTURE = "MJP_CAPTURE"

STATE_MJP_RESULT = "MJP_RESULT"

STATE_MJP_SET_RESULT = "MJP_SET_RESULT"


# ============================================================
# LABEL
# ============================================================

LABELS = {
    0: "SCISSORS",
    1: "ROCK",
    2: "PAPER",
}


COLORS = {
    "SCISSORS": (
        255,
        100,
        0,
    ),

    "ROCK": (
        0,
        220,
        0,
    ),

    "PAPER": (
        0,
        80,
        255,
    ),
}


# ============================================================
# FLASK WEB
# ============================================================

app = Flask(__name__)


latest_jpeg = None

jpeg_lock = threading.Lock()


pending_key = None

key_lock = threading.Lock()


HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>
Jetson AI RPS
</title>


<style>

* {
    box-sizing: border-box;
}


body {

    margin: 0;

    min-height: 100vh;

    background:
        radial-gradient(
            circle at top,
            #182331 0%,
            #0b1119 45%,
            #05080d 100%
        );

    color: white;

    font-family:
        Arial,
        Helvetica,
        sans-serif;

    display: flex;

    flex-direction: column;

    align-items: center;
}


h1 {

    margin:
        18px
        0
        3px;

    font-size: 32px;

    letter-spacing: 2px;

    color: #00e5c7;

    text-shadow:
        0 0 15px
        rgba(
            0,
            229,
            199,
            0.45
        );
}


.subtitle {

    color: #aeb8c4;

    margin-bottom: 8px;

    font-size: 14px;
}


.modes {

    color: #d6dee8;

    margin-bottom: 12px;

    font-size: 14px;
}


.game-frame {

    width: min(
        94vw,
        1050px
    );

    aspect-ratio: 4 / 3;

    overflow: hidden;

    background: black;

    border:
        2px
        solid
        #273544;

    border-radius: 16px;

    box-shadow:
        0 18px 55px
        rgba(
            0,
            0,
            0,
            0.65
        );
}


.game-frame img {

    width: 100%;

    height: 100%;

    display: block;

    object-fit: contain;
}


.controls {

    margin-top: 14px;

    margin-bottom: 20px;

    padding:
        11px
        20px;

    background:
        rgba(
            14,
            21,
            31,
            0.95
        );

    border:
        1px
        solid
        #263747;

    border-radius: 10px;

    color: #aab6c3;

    font-size: 14px;
}


.key {

    color: #00e5c7;

    font-weight: bold;
}

</style>

</head>


<body>


<h1>
ROCK PAPER SCISSORS
</h1>


<div class="subtitle">
Jetson AI Vision Game
</div>


<div class="modes">
1P &nbsp;·&nbsp;
2P &nbsp;·&nbsp;
ONE OUT &nbsp;·&nbsp;
MUK JJI PPA
</div>


<div class="game-frame">

    <img
        src="/stream"
        alt="RPS GAME"
    >

</div>


<div class="controls">

<span class="key">
SPACE
</span>
Start

&nbsp;&nbsp; | &nbsp;&nbsp;

<span class="key">
R
</span>
Restart

&nbsp;&nbsp; | &nbsp;&nbsp;

<span class="key">
M
</span>
Mode

&nbsp;&nbsp; | &nbsp;&nbsp;

<span class="key">
Q
</span>
Quit

</div>


<script>

document.addEventListener(
    "keydown",
    function(event) {

        let key =
            event.key.toLowerCase();


        if (
            event.code === "Space"
        ) {

            key = "space";
        }


        if (
            key === "space"
            ||
            key === "r"
            ||
            key === "m"
            ||
            key === "q"
        ) {

            event.preventDefault();


            fetch(
                "/key/" + key,
                {
                    method: "POST"
                }
            );
        }
    }
);

</script>


</body>

</html>
"""


@app.route("/")
def index():

    return render_template_string(
        HTML_PAGE
    )


def generate_stream():

    global latest_jpeg


    while True:

        with jpeg_lock:

            jpeg = latest_jpeg


        if jpeg is not None:

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + jpeg
                + b"\r\n"
            )


        time.sleep(
            0.025
        )


@app.route("/stream")
def stream():

    return Response(
        generate_stream(),

        mimetype=(
            "multipart/x-mixed-replace; "
            "boundary=frame"
        ),
    )


@app.route(
    "/key/<key>",
    methods=["POST"],
)
def receive_key(
    key,
):

    global pending_key


    with key_lock:

        pending_key = key


    return jsonify(
        {
            "ok": True,
            "key": key,
        }
    )


# ============================================================
# IMAGE PREPROCESS
# ============================================================

def make_square_img(
    img: np.ndarray,
) -> np.ndarray:

    height, width = (
        img.shape[:2]
    )


    if (
        height <= 0
        or width <= 0
    ):

        raise ValueError(
            "Empty hand crop"
        )


    background = np.full(
        (
            IMG_SIZE,
            IMG_SIZE,
            3,
        ),
        255,
        dtype=np.uint8,
    )


    aspect_ratio = (
        height / width
    )


    if aspect_ratio > 1:

        scale = (
            IMG_SIZE / height
        )


        resized_width = max(
            1,
            int(
                width * scale
            ),
        )


        resized = cv2.resize(
            img,
            (
                resized_width,
                IMG_SIZE,
            ),
        )


        x_offset = (
            IMG_SIZE
            - resized_width
        ) // 2


        background[
            :,
            x_offset:
            x_offset
            + resized_width,
        ] = resized


    else:

        scale = (
            IMG_SIZE / width
        )


        resized_height = max(
            1,
            int(
                height * scale
            ),
        )


        resized = cv2.resize(
            img,
            (
                IMG_SIZE,
                resized_height,
            ),
        )


        y_offset = (
            IMG_SIZE
            - resized_height
        ) // 2


        background[
            y_offset:
            y_offset
            + resized_height,
            :,
        ] = resized


    return background


def crop_hand(
    frame: np.ndarray,
    hand: dict,
):

    frame_height, frame_width = (
        frame.shape[:2]
    )


    x, y, width, height = (
        hand["bbox"]
    )


    x1 = max(
        0,
        x - OFFSET,
    )


    y1 = max(
        0,
        y - OFFSET,
    )


    x2 = min(
        frame_width,
        x
        + width
        + OFFSET,
    )


    y2 = min(
        frame_height,
        y
        + height
        + OFFSET,
    )


    if (
        x2 <= x1
        or y2 <= y1
    ):

        return (
            None,
            None,
        )


    cropped = frame[
        y1:y2,
        x1:x2,
    ]


    if cropped.size == 0:

        return (
            None,
            None,
        )


    return (
        cropped,
        (
            x1,
            y1,
            x2,
            y2,
        ),
    )


def classify_hand(
    frame: np.ndarray,
    hand: dict,
    engine: TRTInferenceEngine,
):

    cropped, bbox = crop_hand(
        frame,
        hand,
    )


    if (
        cropped is None
        or bbox is None
    ):

        return (
            None,
            0.0,
            None,
        )


    try:

        image = make_square_img(
            cropped
        )


    except ValueError:

        return (
            None,
            0.0,
            None,
        )


    image = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2RGB,
    )


    image = image.astype(
        np.float32
    )


    input_tensor = np.expand_dims(
        image,
        axis=0,
    )


    output = np.asarray(
        engine.infer(
            input_tensor
        )
    ).ravel()


    if (
        output.size == 0
        or not np.all(
            np.isfinite(
                output
            )
        )
    ):

        return (
            None,
            0.0,
            bbox,
        )


    answer = int(
        np.argmax(
            output
        )
    )


    label = LABELS.get(
        answer
    )


    confidence = float(
        output[
            answer
        ]
    )


    return (
        label,
        confidence,
        bbox,
    )


# ============================================================
# GAME LOGIC
# ============================================================

def majority_vote(
    votes: list[str],
) -> Optional[str]:

    if len(votes) < MIN_VOTES:

        return None


    return Counter(
        votes
    ).most_common(
        1
    )[0][0]


def decide_winner(
    choice_a: str,
    choice_b: str,
) -> int:

    if choice_a == choice_b:

        return 0


    beats = {

        "ROCK":
            "SCISSORS",

        "SCISSORS":
            "PAPER",

        "PAPER":
            "ROCK",
    }


    if (
        beats[
            choice_a
        ]
        == choice_b
    ):

        return 1


    return 2


# ============================================================
# DRAW
# ============================================================

def draw_text(
    frame,
    text,
    position,
    scale=1.0,
    color=(
        255,
        255,
        255,
    ),
    thickness=2,
):

    x, y = position


    cv2.putText(
        frame,
        text,
        (
            x,
            y,
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        (
            0,
            0,
            0,
        ),
        thickness + 3,
        cv2.LINE_AA,
    )


    cv2.putText(
        frame,
        text,
        (
            x,
            y,
        ),
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        color,
        thickness,
        cv2.LINE_AA,
    )


def draw_centered(
    frame,
    text,
    y,
    scale=1.0,
    color=(
        255,
        255,
        255,
    ),
    thickness=2,
):

    (
        text_size,
        _,
    ) = cv2.getTextSize(
        text,
        cv2.FONT_HERSHEY_SIMPLEX,
        scale,
        thickness,
    )


    text_width = (
        text_size[0]
    )


    x = max(
        10,
        (
            frame.shape[1]
            - text_width
        )
        // 2,
    )


    draw_text(
        frame,
        text,
        (
            x,
            y,
        ),
        scale,
        color,
        thickness,
    )


def draw_hand_result(
    frame,
    label,
    confidence,
    bbox,
    player_name,
):

    if bbox is None:

        return


    (
        x1,
        y1,
        x2,
        y2,
    ) = bbox


    color = COLORS.get(
        label or "",
        (
            255,
            255,
            255,
        ),
    )


    cv2.rectangle(
        frame,
        (
            x1,
            y1,
        ),
        (
            x2,
            y2,
        ),
        color,
        2,
    )


    if label is not None:

        draw_text(
            frame,
            (
                f"{player_name}: "
                f"{label} "
                f"{confidence:.2f}"
            ),
            (
                x1,
                max(
                    25,
                    y1 - 8,
                ),
            ),
            0.55,
            color,
            2,
        )


# ============================================================
# RPS IMAGE
# ============================================================

def load_rps_images():

    images = {}


    for (
        label,
        path,
    ) in RPS_IMAGE_PATHS.items():

        image = cv2.imread(
            path,
            cv2.IMREAD_UNCHANGED,
        )


        if image is None:

            raise FileNotFoundError(
                f"Could not load "
                f"{label}: "
                f"{path}"
            )


        images[
            label
        ] = image


    return images


def overlay_image(
    frame,
    image,
    x,
    y,
    width,
    height,
):

    resized = cv2.resize(
        image,
        (
            width,
            height,
        ),
    )


    frame_h, frame_w = (
        frame.shape[:2]
    )


    x1 = max(
        0,
        x,
    )

    y1 = max(
        0,
        y,
    )


    x2 = min(
        frame_w,
        x + width,
    )

    y2 = min(
        frame_h,
        y + height,
    )


    if (
        x1 >= x2
        or y1 >= y2
    ):

        return


    resized = resized[
        0:
        y2 - y1,
        0:
        x2 - x1,
    ]


    if (
        resized.ndim == 3
        and
        resized.shape[2] == 4
    ):

        foreground = (
            resized[
                :,
                :,
                :3,
            ]
            .astype(
                np.float32
            )
        )


        alpha = (
            resized[
                :,
                :,
                3,
            ]
            .astype(
                np.float32
            )
            / 255.0
        )


        alpha = alpha[
            :,
            :,
            np.newaxis,
        ]


        background = (
            frame[
                y1:y2,
                x1:x2,
            ]
            .astype(
                np.float32
            )
        )


        blended = (
            foreground
            * alpha
            +
            background
            * (
                1.0
                - alpha
            )
        )


        frame[
            y1:y2,
            x1:x2,
        ] = blended.astype(
            np.uint8
        )


    else:

        if resized.ndim == 2:

            resized = cv2.cvtColor(
                resized,
                cv2.COLOR_GRAY2BGR,
            )


        frame[
            y1:y2,
            x1:x2,
        ] = resized[
            :,
            :,
            :3,
        ]



# ============================================================
# MUK JJI PPA UI
# ============================================================

def draw_mjp_attacker_banner(
    frame,
    attacker,
):
    """
    묵찌빠 공격자를 화면 상단에 강하게 표시.
    첫 가위바위보 단계(attacker=None)에서는 표시하지 않는다.
    """

    if attacker is None:
        return


    if attacker == "PLAYER":

        text = ">>> PLAYER ATTACK <<<"

        color = (
            0,
            255,
            0,
        )

        bg_color = (
            0,
            90,
            0,
        )


    else:

        text = ">>> CPU ATTACK <<<"

        color = (
            0,
            80,
            255,
        )

        bg_color = (
            0,
            0,
            100,
        )


    # 반투명 배경
    overlay = frame.copy()


    cv2.rectangle(
        overlay,
        (
            135,
            45,
        ),
        (
            505,
            100,
        ),
        bg_color,
        -1,
    )


    cv2.addWeighted(
        overlay,
        0.55,
        frame,
        0.45,
        0,
        frame,
    )


    # 외곽선
    cv2.rectangle(
        frame,
        (
            135,
            45,
        ),
        (
            505,
            100,
        ),
        color,
        3,
    )


    draw_centered(
        frame,
        text,
        82,
        0.82,
        color,
        3,
    )


def draw_mjp_cpu_last(
    frame,
    game,
    rps_images,
    x=470,
    y=150,
):
    """
    진짜 묵찌빠 단계에서만
    마지막으로 공개된 CPU 패를 계속 표시한다.
    """

    # 첫 가위바위보 단계에서는 표시 금지
    if (
        game[
            "mjp_attacker"
        ]
        is None
    ):
        return


    display_cpu = (
        game[
            "mjp_display_cpu_choice"
        ]
    )


    if (
        display_cpu
        not in rps_images
    ):
        return


    draw_text(
        frame,
        "CPU LAST",
        (
            x,
            y,
        ),
        0.55,
        (
            0,
            255,
            255,
        ),
        2,
    )


    overlay_image(
        frame,
        rps_images[
            display_cpu
        ],
        x=x,
        y=y + 15,
        width=120,
        height=120,
    )


    draw_text(
        frame,
        display_cpu,
        (
            x,
            y + 155,
        ),
        0.55,
        COLORS.get(
            display_cpu,
            (
                255,
                255,
                255,
            ),
        ),
        2,
    )



# ============================================================
# RESET
# ============================================================

def reset_to_mode_select():

    return {

        "state":
            STATE_MODE_SELECT,

        "mode":
            None,


        "score1":
            0,

        "score2":
            0,


        "mode_candidate":
            None,

        "mode_candidate_since":
            None,


        "clear_since":
            None,

        "state_started":
            time.time(),


        "votes1":
            [],

        "votes2":
            [],


        "last_choice1":
            None,

        "last_choice2":
            None,

        "last_result":
            "",

        "match_winner":
            "",


        # ====================================================
        # ONE OUT
        # ====================================================

        "hana_left_choice":
            None,

        "hana_right_choice":
            None,

        "hana_left_x":
            None,

        "hana_right_x":
            None,


        "hana_com_choices":
            [],

        "hana_com_keep_index":
            None,


        "hana_player_choice":
            None,

        "hana_com_choice":
            None,


        "hana_animation_started":
            None,


        # ====================================================
        # MUK JJI PPA
        # ====================================================

        # None / PLAYER / CPU
        "mjp_attacker":
            None,

        "mjp_cpu_choice":
            None,

        # 마지막으로 공개된 CPU 패
        "mjp_display_cpu_choice":
            None,

        "mjp_message":
            "",

        "mjp_set_winner":
            None,
    }


# ============================================================
# NORMAL STATE START
# ============================================================

def begin_wait_clear(
    game,
):

    game["state"] = (
        STATE_WAIT_CLEAR
    )


    game["clear_since"] = None


    game["state_started"] = (
        time.time()
    )


    game["votes1"] = []

    game["votes2"] = []


def begin_countdown(
    game,
):

    game["state"] = (
        STATE_COUNTDOWN
    )


    game["state_started"] = (
        time.time()
    )


    game["votes1"] = []

    game["votes2"] = []


def begin_capture(
    game,
):

    game["state"] = (
        STATE_CAPTURE
    )


    game["state_started"] = (
        time.time()
    )


    game["votes1"] = []

    game["votes2"] = []


# ============================================================
# ONE OUT START
# ============================================================

def begin_hana_capture(
    game,
):

    game["state"] = (
        STATE_HANA_CAPTURE_TWO
    )


    game["state_started"] = (
        time.time()
    )


    game["votes1"] = []

    game["votes2"] = []


    game["hana_left_choice"] = None

    game["hana_right_choice"] = None


    game["hana_left_x"] = None

    game["hana_right_x"] = None


    game["hana_com_choices"] = []

    game["hana_com_keep_index"] = None


    game["hana_player_choice"] = None

    game["hana_com_choice"] = None


    game["hana_animation_started"] = None


# ============================================================
# MUK JJI PPA START
# ============================================================

def begin_mjp_countdown(
    game,
):

    game["state"] = (
        STATE_MJP_COUNTDOWN
    )


    game["state_started"] = (
        time.time()
    )


    game["votes1"] = []

    game["mjp_cpu_choice"] = None


def begin_mjp_capture(
    game,
):

    game["state"] = (
        STATE_MJP_CAPTURE
    )


    game["state_started"] = (
        time.time()
    )


    game["votes1"] = []


    # 플레이어 결과를 본 뒤
    # CPU가 정하는 것이 아니라
    # CAPTURE 시작 순간 미리 결정
    game["mjp_cpu_choice"] = (
        random.choice(
            list(
                COLORS.keys()
            )
        )
    )


# ============================================================
# NORMAL RPS FINISH
# ============================================================

def finish_round(
    game,
):

    choice1 = majority_vote(
        game["votes1"]
    )


    if game["mode"] == 1:

        choice2 = (
            random.choice(
                list(
                    COLORS.keys()
                )
            )
            if choice1
            else None
        )


    else:

        choice2 = majority_vote(
            game["votes2"]
        )


    game["last_choice1"] = (
        choice1
    )


    game["last_choice2"] = (
        choice2
    )


    if (
        choice1 is None
        or choice2 is None
    ):

        game[
            "last_result"
        ] = (
            "NOT ENOUGH HAND DATA "
            "- TRY AGAIN"
        )


    else:

        winner = decide_winner(
            choice1,
            choice2,
        )


        if winner == 0:

            game[
                "last_result"
            ] = "DRAW"


        elif winner == 1:

            game["score1"] += 1


            if game["mode"] == 1:

                game[
                    "last_result"
                ] = "PLAYER WIN"


            else:

                game[
                    "last_result"
                ] = "PLAYER 1 WIN"


        else:

            game["score2"] += 1


            if game["mode"] == 1:

                game[
                    "last_result"
                ] = "CPU WIN"


            else:

                game[
                    "last_result"
                ] = "PLAYER 2 WIN"


    game["state"] = (
        STATE_RESULT
    )


    game["state_started"] = (
        time.time()
    )


# ============================================================
# ONE OUT FINISH
# ============================================================

def finish_hana_round(
    game,
):

    choice1 = (
        game[
            "hana_player_choice"
        ]
    )


    choice2 = (
        game[
            "hana_com_choice"
        ]
    )


    game["last_choice1"] = (
        choice1
    )


    game["last_choice2"] = (
        choice2
    )


    if (
        choice1 is None
        or choice2 is None
    ):

        game[
            "last_result"
        ] = "ONE OUT ERROR"


    else:

        winner = decide_winner(
            choice1,
            choice2,
        )


        if winner == 0:

            game[
                "last_result"
            ] = "DRAW"


        elif winner == 1:

            game["score1"] += 1

            game[
                "last_result"
            ] = "PLAYER WIN"


        else:

            game["score2"] += 1

            game[
                "last_result"
            ] = "CPU WIN"


    game["state"] = (
        STATE_RESULT
    )


    game["state_started"] = (
        time.time()
    )


# ============================================================
# MUK JJI PPA FINISH
# ============================================================

def finish_mjp_capture(
    game,
):

    player_choice = majority_vote(
        game["votes1"]
    )

    cpu_choice = (
        game[
            "mjp_cpu_choice"
        ]
    )


    # --------------------------------------------------------
    # 손 인식 실패
    # CPU가 내부적으로 뽑은 새 패는 공개하지 않는다.
    # 이전 CPU LAST도 그대로 유지한다.
    # --------------------------------------------------------
    if player_choice is None:

        game["last_choice1"] = None
        game["last_choice2"] = None

        game[
            "mjp_message"
        ] = (
            "NOT ENOUGH HAND DATA"
        )

        game["state"] = (
            STATE_MJP_RESULT
        )

        game["state_started"] = (
            time.time()
        )

        return


    # 정상적으로 한 턴이 성립했을 때만 결과 공개
    game["last_choice1"] = (
        player_choice
    )

    game["last_choice2"] = (
        cpu_choice
    )

    # 이번에 실제로 공개된 CPU 패
    # 실제 묵찌빠 단계에서는 다음 패 공개 전까지 계속 표시됨
    game[
        "mjp_display_cpu_choice"
    ] = cpu_choice


    attacker = (
        game[
            "mjp_attacker"
        ]
    )


    # ========================================================
    # 첫 가위바위보
    # 공격자가 아직 없는 상태
    # ========================================================
    if attacker is None:

        winner = decide_winner(
            player_choice,
            cpu_choice,
        )

        # 비김 -> 공격권 없음, 다시 첫 가위바위보
        if winner == 0:

            game[
                "mjp_message"
            ] = (
                "DRAW - RPS AGAIN!"
            )

        # PLAYER가 첫 가위바위보 승 -> 묵찌빠 PLAYER 공격
        elif winner == 1:

            game[
                "mjp_attacker"
            ] = "PLAYER"

            game[
                "mjp_message"
            ] = (
                "PLAYER ATTACK!"
            )

        # CPU가 첫 가위바위보 승 -> 묵찌빠 CPU 공격
        else:

            game[
                "mjp_attacker"
            ] = "CPU"

            game[
                "mjp_message"
            ] = (
                "CPU ATTACK!"
            )

        game["state"] = (
            STATE_MJP_RESULT
        )

        game["state_started"] = (
            time.time()
        )

        return


    # ========================================================
    # 실제 묵찌빠 구간
    # ========================================================

    # 같은 패가 나오면 현재 공격자가 1세트 승리
    if player_choice == cpu_choice:

        if attacker == "PLAYER":

            game["score1"] += 1

            game[
                "mjp_set_winner"
            ] = "PLAYER"

            game[
                "mjp_message"
            ] = (
                "PLAYER MUK JJI PPA WIN!"
            )

        else:

            game["score2"] += 1

            game[
                "mjp_set_winner"
            ] = "CPU"

            game[
                "mjp_message"
            ] = (
                "CPU MUK JJI PPA WIN!"
            )

        # 세트가 끝났으므로 persistent CPU LAST 초기화
        # SET RESULT 화면은 last_choice2를 사용해서 방금 패를 보여준다.
        game[
            "mjp_display_cpu_choice"
        ] = None

        game["state"] = (
            STATE_MJP_SET_RESULT
        )

        game["state_started"] = (
            time.time()
        )

        return


    # 패가 다르면 일반 RPS 승자가 새 공격자
    winner = decide_winner(
        player_choice,
        cpu_choice,
    )

    if winner == 1:

        game[
            "mjp_attacker"
        ] = "PLAYER"

        game[
            "mjp_message"
        ] = (
            "PLAYER ATTACK!"
        )

    else:

        game[
            "mjp_attacker"
        ] = "CPU"

        game[
            "mjp_message"
        ] = (
            "CPU ATTACK!"
        )

    game["state"] = (
        STATE_MJP_RESULT
    )

    game["state_started"] = (
        time.time()
    )


# ============================================================
# START MATCH
# ============================================================

def start_match(
    game,
    mode,
):

    game.update(
        reset_to_mode_select()
    )


    game["mode"] = mode


    game["score1"] = 0

    game["score2"] = 0


    begin_wait_clear(
        game
    )


# ============================================================
# WEB START
# ============================================================

def start_web():

    app.run(
        host="0.0.0.0",
        port=8090,
        debug=False,
        use_reloader=False,
        threaded=True,
    )


# ============================================================
# MAIN
# ============================================================

def main() -> int:

    global latest_jpeg

    global pending_key


    # ========================================================
    # ENGINE
    # ========================================================

    if not os.path.exists(
        ENGINE_PATH
    ):

        print(
            "ERROR: TensorRT engine "
            f"not found: "
            f"{ENGINE_PATH}"
        )

        return 1


    # ========================================================
    # IMAGE LOAD
    # ========================================================

    try:

        rps_images = (
            load_rps_images()
        )


    except FileNotFoundError as error:

        print(
            f"ERROR: {error}"
        )

        return 1


    print(
        "RPS images loaded:"
    )


    for (
        label,
        image,
    ) in rps_images.items():

        print(
            f"  {label}: "
            f"{image.shape}"
        )


    # ========================================================
    # HAND + TRT
    # ========================================================

    detector = HandDetector(
        maxHands=2,
        detectionCon=0.65,
        minTrackCon=0.5,
    )


    engine = TRTInferenceEngine(
        ENGINE_PATH
    )


    # ========================================================
    # CAMERA
    # ========================================================

    camera = cv2.VideoCapture(
        0,
        cv2.CAP_V4L2,
    )


    camera.set(
        cv2.CAP_PROP_FRAME_WIDTH,
        FRAME_WIDTH,
    )


    camera.set(
        cv2.CAP_PROP_FRAME_HEIGHT,
        FRAME_HEIGHT,
    )


    camera.set(
        cv2.CAP_PROP_BUFFERSIZE,
        1,
    )


    if not camera.isOpened():

        print(
            "ERROR: Could not "
            "open /dev/video0"
        )

        return 1


    # ========================================================
    # WEB THREAD
    # ========================================================

    web_thread = threading.Thread(
        target=start_web,
        daemon=True,
    )


    web_thread.start()


    print()
    print("=" * 55)
    print("JETSON AI RPS - 4 MODE")
    print(
        "WEB: "
        "http://10.10.20.56:8090"
    )
    print("=" * 55)
    print()


    # ========================================================
    # GAME INIT
    # ========================================================

    game = reset_to_mode_select()


    game["state"] = (
        STATE_TITLE
    )


    previous_time = (
        time.time()
    )


    try:

        while camera.isOpened():

            ok, frame = (
                camera.read()
            )


            if not ok:

                print(
                    "ERROR: Camera "
                    "frame read failed"
                )

                break


            # 좌우 반전
            frame = cv2.flip(
                frame,
                1,
            )


            hands, frame = (
                detector.findHands(
                    frame,
                    draw=False,
                    flipType=False,
                )
            )


            hands = sorted(
                hands,
                key=lambda hand:
                    hand["bbox"][0],
            )


            now = time.time()


            # ==================================================
            # TITLE
            # ==================================================

            if (
                game["state"]
                == STATE_TITLE
            ):

                dark = np.zeros_like(
                    frame
                )


                frame = cv2.addWeighted(
                    frame,
                    0.25,
                    dark,
                    0.75,
                    0,
                )


                draw_centered(
                    frame,
                    "ROCK PAPER SCISSORS",
                    65,
                    1.25,
                    (
                        0,
                        255,
                        255,
                    ),
                    3,
                )


                draw_centered(
                    frame,
                    "JETSON AI GAME",
                    105,
                    0.72,
                    (
                        255,
                        255,
                        255,
                    ),
                    2,
                )


                overlay_image(
                    frame,
                    rps_images[
                        "ROCK"
                    ],
                    x=70,
                    y=135,
                    width=130,
                    height=130,
                )


                overlay_image(
                    frame,
                    rps_images[
                        "PAPER"
                    ],
                    x=255,
                    y=135,
                    width=130,
                    height=130,
                )


                overlay_image(
                    frame,
                    rps_images[
                        "SCISSORS"
                    ],
                    x=440,
                    y=135,
                    width=130,
                    height=130,
                )


                draw_centered(
                    frame,
                    "AI VISION RPS",
                    315,
                    0.8,
                    (
                        0,
                        255,
                        0,
                    ),
                    2,
                )


                draw_centered(
                    frame,
                    (
                        "1P / 2P / "
                        "ONE OUT / "
                        "MUK JJI PPA"
                    ),
                    350,
                    0.53,
                    (
                        255,
                        255,
                        255,
                    ),
                    2,
                )


                draw_centered(
                    frame,
                    "PRESS SPACE TO START",
                    415,
                    0.85,
                    (
                        0,
                        255,
                        255,
                    ),
                    2,
                )


            # ==================================================
            # MODE SELECT
            # ==================================================

            elif (
                game["state"]
                == STATE_MODE_SELECT
            ):

                draw_centered(
                    frame,
                    "ROCK PAPER SCISSORS",
                    45,
                    0.95,
                    (
                        0,
                        255,
                        255,
                    ),
                    2,
                )


                draw_centered(
                    frame,
                    "1 FINGER : 1 PLAYER",
                    90,
                    0.62,
                )


                draw_centered(
                    frame,
                    "2 FINGERS : 2 PLAYERS",
                    123,
                    0.62,
                )


                draw_centered(
                    frame,
                    "3 FINGERS : ONE OUT",
                    156,
                    0.62,
                )


                draw_centered(
                    frame,
                    "4 FINGERS : MUK JJI PPA",
                    189,
                    0.62,
                    (
                        0,
                        255,
                        255,
                    ),
                )


                draw_centered(
                    frame,
                    "Hold the sign for 1 second",
                    220,
                    0.50,
                    (
                        180,
                        180,
                        180,
                    ),
                )


                candidate = None


                if len(hands) == 1:

                    finger_count = (
                        detector
                        .fingersUp(
                            hands[0]
                        )
                        .count(1)
                    )


                    draw_centered(
                        frame,
                        (
                            "DETECTED FINGERS: "
                            f"{finger_count}"
                        ),
                        255,
                        0.75,
                        (
                            0,
                            255,
                            0,
                        ),
                    )


                    if finger_count in (
                        1,
                        2,
                        3,
                        4,
                    ):

                        candidate = (
                            finger_count
                        )


                if candidate is None:

                    game[
                        "mode_candidate"
                    ] = None


                    game[
                        "mode_candidate_since"
                    ] = None


                elif (
                    game[
                        "mode_candidate"
                    ]
                    != candidate
                ):

                    game[
                        "mode_candidate"
                    ] = candidate


                    game[
                        "mode_candidate_since"
                    ] = now


                else:

                    held = (
                        now
                        - game[
                            "mode_candidate_since"
                        ]
                    )


                    progress = min(
                        1.0,
                        held
                        / MODE_HOLD_SECONDS,
                    )


                    bar_x1 = 160

                    bar_y1 = 285

                    bar_x2 = 480

                    bar_y2 = 310


                    cv2.rectangle(
                        frame,
                        (
                            bar_x1,
                            bar_y1,
                        ),
                        (
                            bar_x2,
                            bar_y2,
                        ),
                        (
                            255,
                            255,
                            255,
                        ),
                        2,
                    )


                    cv2.rectangle(
                        frame,
                        (
                            bar_x1 + 2,
                            bar_y1 + 2,
                        ),
                        (
                            bar_x1
                            + 2
                            + int(
                                (
                                    bar_x2
                                    - bar_x1
                                    - 4
                                )
                                * progress
                            ),
                            bar_y2 - 2,
                        ),
                        (
                            0,
                            220,
                            0,
                        ),
                        -1,
                    )


                    if (
                        held
                        >= MODE_HOLD_SECONDS
                    ):

                        start_match(
                            game,
                            candidate,
                        )


            # ==================================================
            # WAIT CLEAR
            # ==================================================

            elif (
                game["state"]
                == STATE_WAIT_CLEAR
            ):

                if game["mode"] == 1:

                    mode_text = (
                        "1 PLAYER"
                    )


                elif game["mode"] == 2:

                    mode_text = (
                        "2 PLAYERS"
                    )


                elif game["mode"] == 3:

                    mode_text = (
                        "ONE OUT"
                    )


                else:

                    mode_text = (
                        "MUK JJI PPA"
                    )


                draw_centered(
                    frame,
                    mode_text,
                    55,
                    1.0,
                    (
                        0,
                        255,
                        255,
                    ),
                )


                draw_centered(
                    frame,
                    "REMOVE ALL HANDS",
                    220,
                    1.1,
                    (
                        0,
                        180,
                        255,
                    ),
                )


                draw_centered(
                    frame,
                    (
                        "Next round starts "
                        "automatically"
                    ),
                    260,
                    0.55,
                )


                # 실제 묵찌빠 단계에서만
                # 공격자 + 직전 CPU 패를 계속 표시
                if (
                    game["mode"] == 4
                    and
                    game[
                        "mjp_attacker"
                    ]
                    is not None
                ):

                    draw_mjp_attacker_banner(
                        frame,
                        game[
                            "mjp_attacker"
                        ],
                    )

                    draw_mjp_cpu_last(
                        frame,
                        game,
                        rps_images,
                        x=470,
                        y=285,
                    )


                if len(hands) == 0:

                    if (
                        game[
                            "clear_since"
                        ]
                        is None
                    ):

                        game[
                            "clear_since"
                        ] = now


                    elif (
                        now
                        - game[
                            "clear_since"
                        ]
                        >= CLEAR_HOLD_SECONDS
                    ):

                        if (
                            game["mode"]
                            == 3
                        ):

                            begin_hana_capture(
                                game
                            )


                        elif (
                            game["mode"]
                            == 4
                        ):

                            begin_mjp_countdown(
                                game
                            )


                        else:

                            begin_countdown(
                                game
                            )


                else:

                    game[
                        "clear_since"
                    ] = None


            # ==================================================
            # NORMAL COUNTDOWN
            # ==================================================

            elif (
                game["state"]
                == STATE_COUNTDOWN
            ):

                elapsed = (
                    now
                    - game[
                        "state_started"
                    ]
                )


                remaining = (
                    COUNTDOWN_SECONDS
                    - elapsed
                )


                number = max(
                    1,
                    int(
                        np.ceil(
                            remaining
                        )
                    ),
                )


                draw_centered(
                    frame,
                    "GET READY",
                    110,
                    1.0,
                    (
                        0,
                        255,
                        255,
                    ),
                )


                draw_centered(
                    frame,
                    str(
                        number
                    ),
                    285,
                    4.0,
                    (
                        0,
                        255,
                        0,
                    ),
                    5,
                )


                draw_centered(
                    frame,
                    (
                        "SHOW YOUR HAND "
                        "BEFORE ZERO"
                    ),
                    350,
                    0.65,
                )


                if (
                    elapsed
                    >= COUNTDOWN_SECONDS
                ):

                    begin_capture(
                        game
                    )


            # ==================================================
            # NORMAL CAPTURE
            # MODE 1 / MODE 2
            # ==================================================

            elif (
                game["state"]
                == STATE_CAPTURE
            ):

                elapsed = (
                    now
                    - game[
                        "state_started"
                    ]
                )


                draw_centered(
                    frame,
                    "SHOW!",
                    55,
                    1.25,
                    (
                        0,
                        255,
                        0,
                    ),
                    3,
                )


                # MODE 1
                if game["mode"] == 1:

                    if hands:

                        hand = max(
                            hands,
                            key=lambda item:
                                (
                                    item[
                                        "bbox"
                                    ][2]
                                    *
                                    item[
                                        "bbox"
                                    ][3]
                                ),
                        )


                        (
                            label,
                            confidence,
                            bbox,
                        ) = classify_hand(
                            frame,
                            hand,
                            engine,
                        )


                        if label is not None:

                            game[
                                "votes1"
                            ].append(
                                label
                            )


                        draw_hand_result(
                            frame,
                            label,
                            confidence,
                            bbox,
                            "PLAYER",
                        )


                    else:

                        draw_centered(
                            frame,
                            "SHOW ONE HAND",
                            400,
                            0.8,
                            (
                                0,
                                80,
                                255,
                            ),
                        )


                # MODE 2
                else:

                    if len(hands) >= 2:

                        player1_hand = (
                            hands[0]
                        )


                        player2_hand = (
                            hands[-1]
                        )


                        (
                            label1,
                            conf1,
                            bbox1,
                        ) = classify_hand(
                            frame,
                            player1_hand,
                            engine,
                        )


                        (
                            label2,
                            conf2,
                            bbox2,
                        ) = classify_hand(
                            frame,
                            player2_hand,
                            engine,
                        )


                        if label1 is not None:

                            game[
                                "votes1"
                            ].append(
                                label1
                            )


                        if label2 is not None:

                            game[
                                "votes2"
                            ].append(
                                label2
                            )


                        draw_hand_result(
                            frame,
                            label1,
                            conf1,
                            bbox1,
                            "P1",
                        )


                        draw_hand_result(
                            frame,
                            label2,
                            conf2,
                            bbox2,
                            "P2",
                        )


                    else:

                        draw_centered(
                            frame,
                            "SHOW TWO HANDS",
                            400,
                            0.8,
                            (
                                0,
                                80,
                                255,
                            ),
                        )


                capture_left = max(
                    0.0,
                    CAPTURE_SECONDS
                    - elapsed,
                )


                draw_text(
                    frame,
                    (
                        "CAPTURE: "
                        f"{capture_left:.1f}s"
                    ),
                    (
                        20,
                        90,
                    ),
                    0.65,
                    (
                        0,
                        255,
                        255,
                    ),
                )


                if (
                    elapsed
                    >= CAPTURE_SECONDS
                ):

                    finish_round(
                        game
                    )


            # ==================================================
            # ONE OUT : CAPTURE TWO
            # ==================================================

            elif (
                game["state"]
                == STATE_HANA_CAPTURE_TWO
            ):

                elapsed = (
                    now
                    - game[
                        "state_started"
                    ]
                )


                cv2.line(
                    frame,
                    (
                        0,
                        SELECT_LINE_Y,
                    ),
                    (
                        FRAME_WIDTH,
                        SELECT_LINE_Y,
                    ),
                    (
                        0,
                        255,
                        255,
                    ),
                    3,
                )


                draw_centered(
                    frame,
                    "ONE OUT",
                    45,
                    1.0,
                    (
                        0,
                        255,
                        255,
                    ),
                    3,
                )


                draw_centered(
                    frame,
                    (
                        "SHOW TWO HANDS "
                        "BELOW THE LINE"
                    ),
                    80,
                    0.65,
                )


                valid_hands = []


                for hand in hands:

                    (
                        x,
                        y,
                        w,
                        h,
                    ) = hand[
                        "bbox"
                    ]


                    center_y = (
                        y
                        + h // 2
                    )


                    if (
                        center_y
                        >
                        SELECT_LINE_Y
                        + HANA_LINE_MARGIN
                    ):

                        valid_hands.append(
                            hand
                        )


                valid_hands = sorted(
                    valid_hands,
                    key=lambda hand:
                        hand[
                            "bbox"
                        ][0],
                )


                if len(
                    valid_hands
                ) >= 2:

                    left_hand = (
                        valid_hands[
                            0
                        ]
                    )


                    right_hand = (
                        valid_hands[
                            -1
                        ]
                    )


                    (
                        label1,
                        conf1,
                        bbox1,
                    ) = classify_hand(
                        frame,
                        left_hand,
                        engine,
                    )


                    (
                        label2,
                        conf2,
                        bbox2,
                    ) = classify_hand(
                        frame,
                        right_hand,
                        engine,
                    )


                    if label1 is not None:

                        game[
                            "votes1"
                        ].append(
                            label1
                        )


                    if label2 is not None:

                        game[
                            "votes2"
                        ].append(
                            label2
                        )


                    draw_hand_result(
                        frame,
                        label1,
                        conf1,
                        bbox1,
                        "LEFT",
                    )


                    draw_hand_result(
                        frame,
                        label2,
                        conf2,
                        bbox2,
                        "RIGHT",
                    )


                else:

                    draw_centered(
                        frame,
                        "TWO HANDS REQUIRED",
                        440,
                        0.65,
                        (
                            0,
                            80,
                            255,
                        ),
                    )


                capture_left = max(
                    0.0,
                    HANA_CAPTURE_SECONDS
                    - elapsed,
                )


                draw_text(
                    frame,
                    (
                        "LOCK: "
                        f"{capture_left:.1f}s"
                    ),
                    (
                        20,
                        115,
                    ),
                    0.6,
                    (
                        0,
                        255,
                        255,
                    ),
                )


                if (
                    elapsed
                    >= HANA_CAPTURE_SECONDS
                ):

                    left_choice = (
                        majority_vote(
                            game[
                                "votes1"
                            ]
                        )
                    )


                    right_choice = (
                        majority_vote(
                            game[
                                "votes2"
                            ]
                        )
                    )


                    if (
                        left_choice
                        is None
                        or
                        right_choice
                        is None
                        or
                        len(
                            valid_hands
                        ) < 2
                    ):

                        game[
                            "votes1"
                        ] = []


                        game[
                            "votes2"
                        ] = []


                        game[
                            "state_started"
                        ] = now


                    else:

                        game[
                            "hana_left_choice"
                        ] = (
                            left_choice
                        )


                        game[
                            "hana_right_choice"
                        ] = (
                            right_choice
                        )


                        left_bbox = (
                            valid_hands[
                                0
                            ][
                                "bbox"
                            ]
                        )


                        right_bbox = (
                            valid_hands[
                                -1
                            ][
                                "bbox"
                            ]
                        )


                        game[
                            "hana_left_x"
                        ] = (
                            left_bbox[0]
                            +
                            left_bbox[2]
                            // 2
                        )


                        game[
                            "hana_right_x"
                        ] = (
                            right_bbox[0]
                            +
                            right_bbox[2]
                            // 2
                        )


                        choices = list(
                            COLORS.keys()
                        )


                        game[
                            "hana_com_choices"
                        ] = [

                            random.choice(
                                choices
                            ),

                            random.choice(
                                choices
                            ),
                        ]


                        game[
                            "hana_com_keep_index"
                        ] = (
                            random.randrange(
                                2
                            )
                        )


                        game["state"] = (
                            STATE_HANA_SELECT
                        )


                        game[
                            "state_started"
                        ] = now


            # ==================================================
            # ONE OUT : SELECT
            # ==================================================

            elif (
                game["state"]
                == STATE_HANA_SELECT
            ):

                cv2.line(
                    frame,
                    (
                        0,
                        SELECT_LINE_Y,
                    ),
                    (
                        FRAME_WIDTH,
                        SELECT_LINE_Y,
                    ),
                    (
                        0,
                        255,
                        255,
                    ),
                    3,
                )


                draw_centered(
                    frame,
                    "COM",
                    28,
                    0.7,
                    (
                        0,
                        255,
                        255,
                    ),
                    2,
                )


                com_choices = (
                    game[
                        "hana_com_choices"
                    ]
                )


                if len(
                    com_choices
                ) == 2:

                    overlay_image(
                        frame,
                        rps_images[
                            com_choices[
                                0
                            ]
                        ],
                        x=90,
                        y=40,
                        width=120,
                        height=120,
                    )


                    overlay_image(
                        frame,
                        rps_images[
                            com_choices[
                                1
                            ]
                        ],
                        x=430,
                        y=40,
                        width=120,
                        height=120,
                    )


                    draw_text(
                        frame,
                        com_choices[
                            0
                        ],
                        (
                            105,
                            180,
                        ),
                        0.55,
                        COLORS[
                            com_choices[
                                0
                            ]
                        ],
                    )


                    draw_text(
                        frame,
                        com_choices[
                            1
                        ],
                        (
                            445,
                            180,
                        ),
                        0.55,
                        COLORS[
                            com_choices[
                                1
                            ]
                        ],
                    )


                draw_centered(
                    frame,
                    "ONE OUT!",
                    275,
                    0.95,
                    (
                        0,
                        255,
                        0,
                    ),
                    3,
                )


                draw_centered(
                    frame,
                    (
                        "MOVE THE HAND YOU KEEP "
                        "ABOVE THE LINE"
                    ),
                    310,
                    0.48,
                )


                draw_text(
                    frame,
                    (
                        "L: "
                        f"{game['hana_left_choice']}"
                    ),
                    (
                        20,
                        345,
                    ),
                    0.55,
                    COLORS.get(
                        game[
                            "hana_left_choice"
                        ],
                        (
                            255,
                            255,
                            255,
                        ),
                    ),
                )


                draw_text(
                    frame,
                    (
                        "R: "
                        f"{game['hana_right_choice']}"
                    ),
                    (
                        450,
                        345,
                    ),
                    0.55,
                    COLORS.get(
                        game[
                            "hana_right_choice"
                        ],
                        (
                            255,
                            255,
                            255,
                        ),
                    ),
                )


                crossing_hands = []


                for hand in hands:

                    (
                        x,
                        y,
                        w,
                        h,
                    ) = hand[
                        "bbox"
                    ]


                    center_x = (
                        x
                        + w // 2
                    )


                    center_y = (
                        y
                        + h // 2
                    )


                    if (
                        center_y
                        <
                        SELECT_LINE_Y
                        - HANA_LINE_MARGIN
                    ):

                        crossing_hands.append(
                            (
                                center_x,
                                hand,
                            )
                        )


                if (
                    len(
                        crossing_hands
                    )
                    == 1
                ):

                    selected_x = (
                        crossing_hands[
                            0
                        ][0]
                    )


                    left_distance = abs(
                        selected_x
                        - game[
                            "hana_left_x"
                        ]
                    )


                    right_distance = abs(
                        selected_x
                        - game[
                            "hana_right_x"
                        ]
                    )


                    if (
                        left_distance
                        <= right_distance
                    ):

                        game[
                            "hana_player_choice"
                        ] = game[
                            "hana_left_choice"
                        ]


                    else:

                        game[
                            "hana_player_choice"
                        ] = game[
                            "hana_right_choice"
                        ]


                    keep_index = (
                        game[
                            "hana_com_keep_index"
                        ]
                    )


                    game[
                        "hana_com_choice"
                    ] = (
                        game[
                            "hana_com_choices"
                        ][
                            keep_index
                        ]
                    )


                    game[
                        "hana_animation_started"
                    ] = now


                    game["state"] = (
                        STATE_HANA_ANIMATE
                    )


            # ==================================================
            # ONE OUT : ANIMATION
            # ==================================================

            elif (
                game["state"]
                == STATE_HANA_ANIMATE
            ):

                cv2.line(
                    frame,
                    (
                        0,
                        SELECT_LINE_Y,
                    ),
                    (
                        FRAME_WIDTH,
                        SELECT_LINE_Y,
                    ),
                    (
                        0,
                        255,
                        255,
                    ),
                    3,
                )


                elapsed = (
                    now
                    - game[
                        "hana_animation_started"
                    ]
                )


                progress = min(
                    1.0,
                    elapsed
                    / HANA_ANIMATION_SECONDS,
                )


                start_y = 40

                target_y = 165


                current_y = int(
                    start_y
                    +
                    (
                        target_y
                        - start_y
                    )
                    * progress
                )


                com_choice = (
                    game[
                        "hana_com_choice"
                    ]
                )


                draw_centered(
                    frame,
                    "COM PICKS...",
                    35,
                    0.75,
                    (
                        0,
                        255,
                        255,
                    ),
                    2,
                )


                if (
                    com_choice
                    in rps_images
                ):

                    overlay_image(
                        frame,
                        rps_images[
                            com_choice
                        ],
                        x=260,
                        y=current_y,
                        width=120,
                        height=120,
                    )


                draw_centered(
                    frame,
                    (
                        "PLAYER: "
                        f"{game['hana_player_choice']}"
                    ),
                    420,
                    0.72,
                    COLORS.get(
                        game[
                            "hana_player_choice"
                        ],
                        (
                            255,
                            255,
                            255,
                        ),
                    ),
                )


                if progress >= 1.0:

                    finish_hana_round(
                        game
                    )


            # ==================================================
            # MODE 4 : MUK JJI PPA COUNTDOWN
            # ==================================================

            elif (
                game["state"]
                == STATE_MJP_COUNTDOWN
            ):

                elapsed = (
                    now
                    - game[
                        "state_started"
                    ]
                )

                remaining = (
                    COUNTDOWN_SECONDS
                    - elapsed
                )

                number = max(
                    1,
                    int(
                        np.ceil(
                            remaining
                        )
                    ),
                )

                attacker = (
                    game[
                        "mjp_attacker"
                    ]
                )


                # 첫 가위바위보 단계
                # CPU LAST / 공격자 배너를 표시하지 않는다.
                if attacker is None:

                    draw_centered(
                        frame,
                        "FIRST RPS",
                        75,
                        1.0,
                        (
                            0,
                            255,
                            255,
                        ),
                        3,
                    )

                    draw_centered(
                        frame,
                        (
                            "WIN THE FIRST RPS "
                            "TO ATTACK"
                        ),
                        115,
                        0.55,
                    )

                # 실제 묵찌빠 단계
                else:

                    draw_mjp_attacker_banner(
                        frame,
                        attacker,
                    )

                    draw_centered(
                        frame,
                        "MUK! JJI! PPA!",
                        135,
                        0.75,
                        (
                            0,
                            255,
                            255,
                        ),
                        2,
                    )

                    # 직전 CPU 패는 새 CPU 패이 공개될 때까지 유지
                    draw_mjp_cpu_last(
                        frame,
                        game,
                        rps_images,
                        x=470,
                        y=155,
                    )


                draw_centered(
                    frame,
                    str(
                        number
                    ),
                    290,
                    4.0,
                    (
                        0,
                        255,
                        0,
                    ),
                    5,
                )

                draw_centered(
                    frame,
                    (
                        "SHOW YOUR HAND "
                        "BEFORE ZERO"
                    ),
                    365,
                    0.6,
                )

                if (
                    elapsed
                    >= COUNTDOWN_SECONDS
                ):

                    begin_mjp_capture(
                        game
                    )


            # ==================================================
            # MODE 4 : MUK JJI PPA CAPTURE
            # ==================================================

            elif (
                game["state"]
                == STATE_MJP_CAPTURE
            ):

                elapsed = (
                    now
                    - game[
                        "state_started"
                    ]
                )

                attacker = (
                    game[
                        "mjp_attacker"
                    ]
                )


                # 첫 가위바위보
                if attacker is None:

                    title = (
                        "ROCK PAPER SCISSORS!"
                    )

                    title_y = 55
                    show_y = 105
                    capture_y = 145

                # 실제 묵찌빠
                else:

                    title = (
                        "MUK! JJI! PPA!"
                    )

                    title_y = 135
                    show_y = 180
                    capture_y = 220

                    draw_mjp_attacker_banner(
                        frame,
                        attacker,
                    )

                    # 새 CPU 패는 아직 숨겨져 있고
                    # 직전 공개 패만 계속 보여준다.
                    draw_mjp_cpu_last(
                        frame,
                        game,
                        rps_images,
                        x=470,
                        y=155,
                    )


                draw_centered(
                    frame,
                    title,
                    title_y,
                    0.95,
                    (
                        0,
                        255,
                        255,
                    ),
                    3,
                )

                draw_centered(
                    frame,
                    "SHOW!",
                    show_y,
                    1.25,
                    (
                        0,
                        255,
                        0,
                    ),
                    3,
                )


                if hands:

                    hand = max(
                        hands,
                        key=lambda item:
                            (
                                item[
                                    "bbox"
                                ][2]
                                *
                                item[
                                    "bbox"
                                ][3]
                            ),
                    )

                    (
                        label,
                        confidence,
                        bbox,
                    ) = classify_hand(
                        frame,
                        hand,
                        engine,
                    )

                    if label is not None:

                        game[
                            "votes1"
                        ].append(
                            label
                        )

                    draw_hand_result(
                        frame,
                        label,
                        confidence,
                        bbox,
                        "PLAYER",
                    )

                else:

                    draw_centered(
                        frame,
                        "SHOW ONE HAND",
                        400,
                        0.8,
                        (
                            0,
                            80,
                            255,
                        ),
                    )


                capture_left = max(
                    0.0,
                    MJP_CAPTURE_SECONDS
                    - elapsed,
                )

                draw_text(
                    frame,
                    (
                        "CAPTURE: "
                        f"{capture_left:.1f}s"
                    ),
                    (
                        20,
                        capture_y,
                    ),
                    0.65,
                    (
                        0,
                        255,
                        255,
                    ),
                )

                if (
                    elapsed
                    >= MJP_CAPTURE_SECONDS
                ):

                    finish_mjp_capture(
                        game
                    )


            # ==================================================
            # MODE 4 : EACH MUK JJI PPA TURN RESULT
            # ==================================================

            elif (
                game["state"]
                == STATE_MJP_RESULT
            ):

                choice1 = (
                    game[
                        "last_choice1"
                    ]
                    or
                    "NO DATA"
                )

                choice2 = (
                    game[
                        "last_choice2"
                    ]
                    or
                    "NO DATA"
                )

                attacker = (
                    game[
                        "mjp_attacker"
                    ]
                )


                # 공격권이 정해진 뒤에는 결과 화면에서도 크게 표시
                if attacker is not None:

                    draw_mjp_attacker_banner(
                        frame,
                        attacker,
                    )

                    message_y = 135
                    player_y = 180
                    cpu_y = 225
                    image_y = 245
                    score_y = 430

                else:

                    message_y = 65
                    player_y = 125
                    cpu_y = 175
                    image_y = 200
                    score_y = 425


                draw_centered(
                    frame,
                    game[
                        "mjp_message"
                    ],
                    message_y,
                    0.95,
                    (
                        0,
                        255,
                        255,
                    ),
                    3,
                )

                draw_centered(
                    frame,
                    (
                        "PLAYER: "
                        f"{choice1}"
                    ),
                    player_y,
                    0.8,
                    COLORS.get(
                        choice1,
                        (
                            255,
                            255,
                            255,
                        ),
                    ),
                )

                draw_centered(
                    frame,
                    (
                        "CPU: "
                        f"{choice2}"
                    ),
                    cpu_y,
                    0.8,
                    COLORS.get(
                        choice2,
                        (
                            255,
                            255,
                            255,
                        ),
                    ),
                )

                if (
                    choice2
                    in rps_images
                ):

                    overlay_image(
                        frame,
                        rps_images[
                            choice2
                        ],
                        x=255,
                        y=image_y,
                        width=130,
                        height=130,
                    )

                draw_centered(
                    frame,
                    (
                        "SCORE  "
                        f"{game['score1']}"
                        " : "
                        f"{game['score2']}"
                    ),
                    score_y,
                    0.85,
                    (
                        0,
                        255,
                        0,
                    ),
                    2,
                )

                if (
                    now
                    - game[
                        "state_started"
                    ]
                    >= MJP_RESULT_SECONDS
                ):

                    begin_wait_clear(
                        game
                    )


            # ==================================================
            # MODE 4 : ONE SET RESULT
            # ==================================================

            elif (
                game["state"]
                == STATE_MJP_SET_RESULT
            ):

                choice1 = (
                    game[
                        "last_choice1"
                    ]
                )


                choice2 = (
                    game[
                        "last_choice2"
                    ]
                )


                set_winner = (
                    game[
                        "mjp_set_winner"
                    ]
                )


                if set_winner == "PLAYER":

                    result_color = (
                        0,
                        255,
                        0,
                    )


                else:

                    result_color = (
                        0,
                        80,
                        255,
                    )


                draw_centered(
                    frame,
                    game[
                        "mjp_message"
                    ],
                    65,
                    0.95,
                    result_color,
                    3,
                )


                draw_centered(
                    frame,
                    (
                        "SAME SIGN!"
                    ),
                    110,
                    0.8,
                    (
                        0,
                        255,
                        255,
                    ),
                    2,
                )


                draw_centered(
                    frame,
                    (
                        "PLAYER: "
                        f"{choice1}"
                    ),
                    160,
                    0.75,
                    COLORS.get(
                        choice1,
                        (
                            255,
                            255,
                            255,
                        ),
                    ),
                )


                draw_centered(
                    frame,
                    (
                        "CPU: "
                        f"{choice2}"
                    ),
                    205,
                    0.75,
                    COLORS.get(
                        choice2,
                        (
                            255,
                            255,
                            255,
                        ),
                    ),
                )


                if (
                    choice2
                    in rps_images
                ):

                    overlay_image(
                        frame,
                        rps_images[
                            choice2
                        ],
                        x=265,
                        y=225,
                        width=110,
                        height=110,
                    )


                draw_centered(
                    frame,
                    (
                        "SCORE  "
                        f"{game['score1']}"
                        " : "
                        f"{game['score2']}"
                    ),
                    390,
                    1.0,
                    (
                        0,
                        255,
                        0,
                    ),
                    3,
                )


                # 이게 핵심
                # 한 판 이겨도 바로 끝나지 않음
                if (
                    now
                    - game[
                        "state_started"
                    ]
                    >= MJP_SET_RESULT_SECONDS
                ):

                    # 먼저 2점이면 최종 종료
                    if (
                        game["score1"]
                        >= WIN_TARGET
                        or
                        game["score2"]
                        >= WIN_TARGET
                    ):

                        if (
                            game["score1"]
                            > game["score2"]
                        ):

                            game[
                                "match_winner"
                            ] = (
                                "PLAYER WINS MATCH"
                            )


                        else:

                            game[
                                "match_winner"
                            ] = (
                                "CPU WINS MATCH"
                            )


                        game["state"] = (
                            STATE_GAME_OVER
                        )


                        game[
                            "state_started"
                        ] = now


                    # 아직 2점 아님
                    # 새 묵찌빠 세트
                    else:

                        # 새 묵찌빠 세트
                        # 첫 가위바위보부터 다시 시작
                        game[
                            "mjp_attacker"
                        ] = None


                        game[
                            "mjp_set_winner"
                        ] = None


                        game[
                            "mjp_cpu_choice"
                        ] = None


                        game[
                            "mjp_display_cpu_choice"
                        ] = None


                        begin_wait_clear(
                            game
                        )


            # ==================================================
            # MODE 1/2/3 ROUND RESULT
            # 기존 흐름
            # ==================================================

            elif (
                game["state"]
                == STATE_RESULT
            ):

                choice1 = (
                    game[
                        "last_choice1"
                    ]
                    or
                    "NO DATA"
                )


                choice2 = (
                    game[
                        "last_choice2"
                    ]
                    or
                    "NO DATA"
                )


                name2 = (
                    "CPU"
                    if
                    game["mode"]
                    in (
                        1,
                        3,
                    )
                    else
                    "P2"
                )


                name1 = (
                    "PLAYER"
                    if
                    game["mode"]
                    in (
                        1,
                        3,
                    )
                    else
                    "P1"
                )


                draw_centered(
                    frame,
                    game[
                        "last_result"
                    ],
                    70,
                    1.0,
                    (
                        0,
                        255,
                        255,
                    ),
                    3,
                )


                draw_centered(
                    frame,
                    (
                        f"{name1}: "
                        f"{choice1}"
                    ),
                    130,
                    0.8,
                    COLORS.get(
                        choice1,
                        (
                            255,
                            255,
                            255,
                        ),
                    ),
                )


                draw_centered(
                    frame,
                    (
                        f"{name2}: "
                        f"{choice2}"
                    ),
                    185,
                    0.8,
                    COLORS.get(
                        choice2,
                        (
                            255,
                            255,
                            255,
                        ),
                    ),
                )


                if (
                    game["mode"]
                    in (
                        1,
                        3,
                    )
                    and
                    choice2
                    in rps_images
                ):

                    overlay_image(
                        frame,
                        rps_images[
                            choice2
                        ],
                        x=245,
                        y=210,
                        width=150,
                        height=150,
                    )


                draw_centered(
                    frame,
                    (
                        "SCORE  "
                        f"{game['score1']}"
                        " : "
                        f"{game['score2']}"
                    ),
                    425,
                    0.9,
                    (
                        0,
                        255,
                        0,
                    ),
                    2,
                )


                if (
                    now
                    - game[
                        "state_started"
                    ]
                    >= RESULT_SECONDS
                ):

                    if (
                        game["score1"]
                        >= WIN_TARGET
                        or
                        game["score2"]
                        >= WIN_TARGET
                    ):

                        if (
                            game["score1"]
                            > game["score2"]
                        ):

                            game[
                                "match_winner"
                            ] = (
                                "PLAYER WINS MATCH"
                                if
                                game["mode"]
                                in (
                                    1,
                                    3,
                                )
                                else
                                "PLAYER 1 WINS MATCH"
                            )


                        else:

                            game[
                                "match_winner"
                            ] = (
                                "CPU WINS MATCH"
                                if
                                game["mode"]
                                in (
                                    1,
                                    3,
                                )
                                else
                                "PLAYER 2 WINS MATCH"
                            )


                        game["state"] = (
                            STATE_GAME_OVER
                        )


                        game[
                            "state_started"
                        ] = now


                    else:

                        begin_wait_clear(
                            game
                        )


            # ==================================================
            # FINAL RESULT
            # ==================================================

            elif (
                game["state"]
                == STATE_GAME_OVER
            ):

                # CPU 상대 모드
                if (
                    game["mode"]
                    in (
                        1,
                        3,
                        4,
                    )
                ):

                    player_won = (
                        game[
                            "match_winner"
                        ]
                        == "PLAYER WINS MATCH"
                    )


                    if player_won:

                        title = (
                            "VICTORY!"
                        )


                        title_color = (
                            0,
                            255,
                            0,
                        )


                        subtitle = (
                            "YOU WIN!"
                        )


                    else:

                        title = (
                            "DEFEAT"
                        )


                        title_color = (
                            0,
                            80,
                            255,
                        )


                        subtitle = (
                            "CPU WINS"
                        )


                # 2P
                else:

                    if (
                        game["score1"]
                        >
                        game["score2"]
                    ):

                        title = (
                            "PLAYER 1 WIN!"
                        )


                        subtitle = (
                            "PLAYER 1 "
                            "WINS MATCH"
                        )


                    else:

                        title = (
                            "PLAYER 2 WIN!"
                        )


                        subtitle = (
                            "PLAYER 2 "
                            "WINS MATCH"
                        )


                    title_color = (
                        0,
                        255,
                        0,
                    )


                draw_centered(
                    frame,
                    title,
                    115,
                    1.5,
                    title_color,
                    4,
                )


                draw_centered(
                    frame,
                    subtitle,
                    195,
                    1.0,
                    title_color,
                    3,
                )


                draw_centered(
                    frame,
                    (
                        "FINAL SCORE  "
                        f"{game['score1']}"
                        " : "
                        f"{game['score2']}"
                    ),
                    270,
                    0.95,
                    (
                        255,
                        255,
                        255,
                    ),
                    2,
                )


                if game["mode"] == 4:

                    draw_centered(
                        frame,
                        "MUK JJI PPA",
                        325,
                        0.75,
                        (
                            0,
                            255,
                            255,
                        ),
                        2,
                    )


            # ==================================================
            # COMMON HUD
            # ==================================================

            if (
                game["mode"]
                is not None
                and
                game["state"]
                not in (
                    STATE_RESULT,
                    STATE_MJP_RESULT,
                    STATE_MJP_SET_RESULT,
                    STATE_GAME_OVER,
                    STATE_TITLE,
                    STATE_MODE_SELECT,
                )
            ):

                opponent = (
                    "CPU"
                    if
                    game["mode"]
                    in (
                        1,
                        3,
                        4,
                    )
                    else
                    "P2"
                )


                draw_text(
                    frame,
                    (
                        "P1 "
                        f"{game['score1']}"
                        "  -  "
                        f"{game['score2']} "
                        f"{opponent}"
                    ),
                    (
                        20,
                        35,
                    ),
                    0.65,
                    (
                        255,
                        255,
                        255,
                    ),
                )


            # ==================================================
            # FPS
            # ==================================================

            current_time = (
                time.time()
            )


            delta = max(
                current_time
                - previous_time,
                1e-6,
            )


            previous_time = (
                current_time
            )


            fps = (
                1.0
                / delta
            )


            draw_text(
                frame,
                (
                    f"FPS: "
                    f"{fps:.1f}"
                ),
                (
                    frame.shape[1]
                    - 125,
                    30,
                ),
                0.55,
                (
                    0,
                    255,
                    255,
                ),
            )


            # ==================================================
            # DISPLAY BRIGHTNESS ONLY
            # AI INPUT은 위에서 이미 처리됨
            # ==================================================

            bright_frame = (
                cv2.convertScaleAbs(
                    frame,
                    alpha=1.12,
                    beta=20,
                )
            )


            # ==================================================
            # JPEG
            # ==================================================

            (
                encode_ok,
                jpeg_buffer,
            ) = cv2.imencode(
                ".jpg",
                bright_frame,
                [
                    cv2.IMWRITE_JPEG_QUALITY,
                    75,
                ],
            )


            if encode_ok:

                with jpeg_lock:

                    latest_jpeg = (
                        jpeg_buffer
                        .tobytes()
                    )


            # ==================================================
            # KEY
            # ==================================================

            with key_lock:

                key = pending_key

                pending_key = None


            # TITLE -> MENU
            if (
                game["state"]
                == STATE_TITLE
                and
                key == "space"
            ):

                game = (
                    reset_to_mode_select()
                )


            # QUIT
            if key == "q":

                break


            # MODE SELECT
            if key == "m":

                game = (
                    reset_to_mode_select()
                )


            # RESTART CURRENT MODE
            if (
                key == "r"
                and
                game["mode"]
                in (
                    1,
                    2,
                    3,
                    4,
                )
            ):

                selected_mode = (
                    game["mode"]
                )


                start_match(
                    game,
                    selected_mode,
                )


    except KeyboardInterrupt:

        print(
            "Stopped by user"
        )


    finally:

        camera.release()


    return 0


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )