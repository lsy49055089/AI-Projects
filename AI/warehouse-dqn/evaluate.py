"""학습 정책과 무작위 배치 정책을 동일 조건에서 비교한다."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from dqn_agent import DQNAgent
from train import load_states
from warehouse_env import WarehouseEnv


def evaluate(
    data_path: str | Path,
    model_path: str | Path,
    output_path: str | Path,
    episodes: int = 100,
    max_steps: int = 30,
    seed: int = 1042,
) -> dict:
    if episodes < 1:
        raise ValueError("episodes는 1 이상이어야 합니다.")
    states = load_states(data_path)
    eval_env = WarehouseEnv(states, max_steps=max_steps, seed=seed)
    random_env = WarehouseEnv(states, max_steps=max_steps, seed=seed)
    agent = DQNAgent(eval_env.state_size, eval_env.action_size, seed=seed)
    agent.load(model_path)
    random_rng = np.random.default_rng(seed)

    def run_episode(env: WarehouseEnv, greedy: bool) -> tuple[float, float]:
        obs = env.reset(step_level=4)
        good, count = 0, 0
        total = 0.0
        for _ in range(max_steps):
            mask = env.available_actions()
            if not mask.any():
                break
            choices = np.flatnonzero(mask)
            action = agent.act(obs, mask, greedy=True) if greedy else int(random_rng.choice(choices))
            obs, reward, done, info = env.step(action)
            item = info["item"]
            in_return_zone = info["position"] in env.RETURN_POSITIONS
            good += int((item["Type"] == "Return Zone") == in_return_zone)
            count += 1
            total += reward
            if done:
                break
        return total, good / count if count else 0.0

    scores_trained, scores_random, rates_trained, rates_random = [], [], [], []
    for _ in range(episodes):
        trained_score, trained_rate = run_episode(eval_env, greedy=True)
        random_score, random_rate = run_episode(random_env, greedy=False)
        scores_trained.append(trained_score)
        scores_random.append(random_score)
        rates_trained.append(trained_rate)
        rates_random.append(random_rate)

    summary = {
        "episodes": episodes,
        "step_level": 4,
        "trained_mean_reward": round(float(np.mean(scores_trained)), 3),
        "random_mean_reward": round(float(np.mean(scores_random)), 3),
        "trained_correct_zone_rate": round(float(np.mean(rates_trained)), 4),
        "random_correct_zone_rate": round(float(np.mean(rates_random)), 4),
        "seed": seed,
    }
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
    print(f"동일한 물품 순서에서 학습 정책과 무작위 배치 비교: {summary}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="DQN 학습 정책 평가")
    parser.add_argument("--data", default="data/Combined_States.json")
    parser.add_argument("--model", default="output/dqn_weights.npz")
    parser.add_argument("--output", default="output/history/evaluation.json")
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--max-steps", type=int, default=30)
    parser.add_argument("--seed", type=int, default=1042)
    args = parser.parse_args()
    evaluate(args.data, args.model, args.output, args.episodes, args.max_steps, args.seed)


if __name__ == "__main__":
    main()
