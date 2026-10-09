"""에피소드 보상 그래프와 층별 적재 GIF 시각화."""

from __future__ import annotations

from pathlib import Path

import imageio.v2 as imageio
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def save_rewards_graph(rewards: list[float], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(np.arange(1, len(rewards) + 1), rewards, label="Episode Reward", lw=1.5)
    if len(rewards) >= 10:
        window = min(20, len(rewards))
        moving_average = np.convolve(rewards, np.ones(window) / window, mode="valid")
        ax.plot(np.arange(window, len(rewards) + 1), moving_average, label=f"Moving Avg ({window})")
    ax.set(xlabel="Episode", ylabel="Total Reward", title="DQN Warehouse - Reward Progress")
    ax.legend()
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=135)
    plt.close(fig)
    return path


def render_frame(env, episode: int, step: int, rewards: list[float]) -> np.ndarray:
    fig, axes = plt.subplots(1, 3, figsize=(12, 4), dpi=85)
    views = [
        (env.state_1f, env.items_1f, 100, "Blues", "1F - Heavy Items"),
        (env.state_2f, env.items_2f, 50, "Oranges", "2F - Light Items"),
    ]
    for ax, (state, items, capacity, cmap, title) in zip(axes[:2], views):
        ax.imshow(state, cmap=cmap, vmin=0, vmax=capacity, interpolation="nearest")
        ax.set_title(title)
        ax.set_xticks(np.arange(env.layout.shape[1]))
        ax.set_yticks(np.arange(env.layout.shape[0]))
        ax.tick_params(labelsize=6, length=0)
        for x, y in env.valid_positions:
            item = items[x, y]
            if item is not None:
                label = f"{item['Weight']}\n{'R' if item['Type'] == 'Return Zone' else 'P'}"
                ax.text(y, x, label, ha="center", va="center", fontsize=6, color="black")
            elif (x, y) in env.RETURN_POSITIONS:
                ax.text(y, x, "R", ha="center", va="center", fontsize=6, alpha=0.6)
    axes[2].plot(np.arange(1, len(rewards) + 1), rewards, marker=".")
    axes[2].set(xlabel="Episode", ylabel="Reward", title="Episode Rewards")
    axes[2].grid(alpha=0.3)
    fig.suptitle(f"Episode {episode} / Step {step} / Level {env.step_level}", fontsize=11)
    fig.tight_layout()
    fig.canvas.draw()
    frame = np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy()
    plt.close(fig)
    return frame


def save_episode_gif(frames: list[np.ndarray], path: str | Path) -> Path | None:
    if not frames:
        return None
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    imageio.mimsave(path, frames, duration=0.4, loop=0)
    return path
