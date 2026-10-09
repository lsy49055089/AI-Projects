"""예제 주문 데이터로 전처리부터 DQN 학습까지 실행한다."""

from __future__ import annotations

import argparse
from pathlib import Path

from create_sample_data import generate_sample_csv
from evaluate import evaluate
from preprocessing import export_json, preprocess, read_retail_data
from train import train


def main() -> None:
    parser = argparse.ArgumentParser(description="창고 배치 학습 실행 예제")
    parser.add_argument("--episodes", type=int, default=16)
    parser.add_argument("--max-steps", type=int, default=20)
    parser.add_argument("--gif-every", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--eval-episodes", type=int, default=60)
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    csv_path = root / "data" / "sample_online_retail.csv"
    json_path = root / "data" / "Combined_States_sample.json"
    generate_sample_csv(csv_path, args.seed)
    records = preprocess(read_retail_data(csv_path), args.seed)
    export_json(records, json_path)
    print(f"샘플 데이터 {len(records)}개 항목: {json_path}")
    train(
        data_path=json_path,
        output_dir=root / "output" / "demo",
        episodes=args.episodes,
        max_steps=args.max_steps,
        seed=args.seed,
        gif_every=args.gif_every,
        batch_size=32,
    )
    evaluate(
        data_path=json_path,
        model_path=root / "output" / "demo" / "dqn_weights.npz",
        output_path=root / "output" / "demo" / "history" / "evaluation.json",
        episodes=args.eval_episodes,
        max_steps=args.max_steps,
        seed=args.seed + 1000,
    )


if __name__ == "__main__":
    main()
