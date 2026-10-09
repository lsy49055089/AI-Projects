"""DQN 학습, 검증 기록, 시각화 및 모델 저장."""

from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path

import numpy as np

from dqn_agent import DQNAgent
from visualization import render_frame, save_episode_gif, save_rewards_graph
from warehouse_env import WarehouseEnv


def load_states(path: str | Path) -> list[dict]:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(
            f"데이터 파일이 없습니다: {path}\n"
            "먼저 preprocessing.py로 Combined_States.json을 생성하세요."
        )
    with path.open(encoding="utf-8") as handle:
        states = json.load(handle)
    if not isinstance(states, list):
        raise ValueError("JSON 최상위 데이터는 상품 객체 목록(list)이어야 합니다.")
    return states


def train(
    data_path: str | Path,
    output_dir: str | Path,
    episodes: int = 300,
    max_steps: int = 30,
    seed: int = 42,
    gif_every: int = 75,
    batch_size: int = 64,
) -> dict:
    if episodes < 1 or gif_every < 0 or batch_size < 1:
        raise ValueError("episodes와 batch_size는 1 이상, gif_every는 0 이상이어야 합니다.")
    start = time.perf_counter()
    output = Path(output_dir)
    graph_dir = output / "graph"
    gif_dir = output / "sample_episodes"
    history_dir = output / "history"
    for folder in (graph_dir, gif_dir, history_dir):
        folder.mkdir(parents=True, exist_ok=True)

    states = load_states(data_path)
    env = WarehouseEnv(states, max_steps=max_steps, seed=seed)
    agent = DQNAgent(env.state_size, env.action_size, seed=seed, batch_size=batch_size)
    rewards: list[float] = []
    rows: list[dict] = []
    best_per_level: dict[str, dict] = {}
    for index in range(episodes):
        episode = index + 1
        level = min((index * 4) // episodes + 1, 4)
        state = env.reset(step_level=level)
        total_reward = 0.0
        placed_count = 0
        losses = []
        frames = []
        record_frames = gif_every > 0 and (episode % gif_every == 0 or episode == episodes)
        for step_index in range(max_steps):
            available = env.available_actions()
            if not available.any():
                break
            action = agent.act(state, available)
            next_state, reward, done, info = env.step(action)
            next_mask = np.zeros(env.action_size, dtype=bool) if done else env.available_actions()
            agent.remember(state, action, reward, next_state, done, next_mask)
            loss = agent.replay()
            if loss is not None:
                losses.append(loss)
            state = next_state
            total_reward += reward
            placed_count += int(info["placed"])
            if record_frames:
                frames.append(render_frame(env, episode, step_index + 1, rewards + [total_reward]))
            if done:
                break
        rewards.append(total_reward)
        if record_frames:
            save_episode_gif(frames, gif_dir / f"episode_{episode:03d}.gif")
        row = {
            "episode": episode,
            "step_level": level,
            "steps": env.steps,
            "placed": placed_count,
            "total_reward": round(total_reward, 4),
            "epsilon": round(agent.epsilon, 5),
            "loss": round(float(np.mean(losses)), 5) if losses else "",
        }
        rows.append(row)
        level_key = f"Level {level}"
        if level_key not in best_per_level or total_reward > best_per_level[level_key]["total_reward"]:
            best_per_level[level_key] = {"episode": episode, "total_reward": round(total_reward, 4)}
        agent.end_episode()
        print(f"Episode {episode:3d}/{episodes} | Level {level} | "
              f"Steps {env.steps:2d} | Reward {total_reward:7.2f} | Epsilon {agent.epsilon:.3f}")

    with (history_dir / "episode_rewards.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with (history_dir / "highest_rewards.json").open("w", encoding="utf-8") as handle:
        json.dump(best_per_level, handle, ensure_ascii=False, indent=2)
    agent.save(output / "dqn_weights.npz")
    save_rewards_graph(rewards, graph_dir / "final_rewards_graph.png")
    result = {
        "episodes": episodes,
        "max_steps": max_steps,
        "state_size": env.state_size,
        "action_size": env.action_size,
        "training_updates": agent.learn_steps,
        "mean_reward": round(float(np.mean(rewards)), 3),
        "final_reward": round(rewards[-1], 3),
        "seconds": round(time.perf_counter() - start, 2),
        "data": str(data_path),
        "output": str(output),
    }
    with (history_dir / "training_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    print(f"\n학습 완료: {result}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="물류창고 DQN 학습")
    parser.add_argument("--data", default="data/Combined_States.json")
    parser.add_argument("--output", default="output")
    parser.add_argument("--episodes", type=int, default=300)
    parser.add_argument("--max-steps", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--gif-every", type=int, default=75, help="0이면 GIF 저장 안 함")
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()
    train(args.data, args.output, args.episodes, args.max_steps, args.seed, args.gif_every, args.batch_size)


if __name__ == "__main__":
    main()
