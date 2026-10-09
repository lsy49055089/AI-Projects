"""NumPy 기반 Deep Q-Network와 경험 재생 메모리."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class Transition:
    state: np.ndarray
    action: int
    reward: float
    next_state: np.ndarray
    done: bool
    next_mask: np.ndarray


class QNetwork:
    def __init__(self, state_size: int, action_size: int, rng: np.random.Generator, lr: float = 0.001):
        dims = [state_size, 64, 64, action_size]
        self.weights = [
            (rng.standard_normal((dims[i], dims[i + 1]))
             * np.sqrt(2.0 / dims[i])).astype(np.float32)
            for i in range(3)
        ]
        self.biases = [np.zeros(dims[i + 1], dtype=np.float32) for i in range(3)]
        self.lr = lr
        self.mw = [np.zeros_like(w) for w in self.weights]
        self.vw = [np.zeros_like(w) for w in self.weights]
        self.mb = [np.zeros_like(b) for b in self.biases]
        self.vb = [np.zeros_like(b) for b in self.biases]
        self.update_count = 0

    def predict(self, states: np.ndarray) -> np.ndarray:
        h = np.asarray(states, dtype=np.float32)
        for w, b in zip(self.weights[:-1], self.biases[:-1]):
            h = np.maximum(h @ w + b, 0)
        return h @ self.weights[-1] + self.biases[-1]

    def train_batch(self, states: np.ndarray, actions: np.ndarray, targets: np.ndarray) -> float:
        h0 = np.asarray(states, dtype=np.float32)
        z1 = h0 @ self.weights[0] + self.biases[0]
        h1 = np.maximum(z1, 0)
        z2 = h1 @ self.weights[1] + self.biases[1]
        h2 = np.maximum(z2, 0)
        q = h2 @ self.weights[2] + self.biases[2]
        idx = np.arange(len(actions))
        errors = q[idx, actions] - targets
        delta = np.clip(errors, -5.0, 5.0) / len(actions)
        grad_q = np.zeros_like(q)
        grad_q[idx, actions] = delta
        gw2, gb2 = h2.T @ grad_q, grad_q.sum(axis=0)
        gz2 = (grad_q @ self.weights[2].T) * (z2 > 0)
        gw1, gb1 = h1.T @ gz2, gz2.sum(axis=0)
        gz1 = (gz2 @ self.weights[1].T) * (z1 > 0)
        gw0, gb0 = h0.T @ gz1, gz1.sum(axis=0)

        self.update_count += 1
        t = self.update_count
        for i, (gw, gb) in enumerate(zip([gw0, gw1, gw2], [gb0, gb1, gb2])):
            np.clip(gw, -10.0, 10.0, out=gw)
            np.clip(gb, -10.0, 10.0, out=gb)
            self.mw[i] = 0.9 * self.mw[i] + 0.1 * gw
            self.vw[i] = 0.999 * self.vw[i] + 0.001 * (gw * gw)
            self.mb[i] = 0.9 * self.mb[i] + 0.1 * gb
            self.vb[i] = 0.999 * self.vb[i] + 0.001 * (gb * gb)
            mw_hat = self.mw[i] / (1 - 0.9**t)
            vw_hat = self.vw[i] / (1 - 0.999**t)
            mb_hat = self.mb[i] / (1 - 0.9**t)
            vb_hat = self.vb[i] / (1 - 0.999**t)
            self.weights[i] -= self.lr * mw_hat / (np.sqrt(vw_hat) + 1e-8)
            self.biases[i] -= self.lr * mb_hat / (np.sqrt(vb_hat) + 1e-8)
        return float(np.mean(errors**2))

    def copy_from(self, other: "QNetwork") -> None:
        self.weights = [w.copy() for w in other.weights]
        self.biases = [b.copy() for b in other.biases]


class DQNAgent:
    def __init__(
        self,
        state_size: int,
        action_size: int,
        seed: int = 42,
        gamma: float = 0.95,
        epsilon_decay: float = 0.99,
        epsilon_min: float = 0.05,
        batch_size: int = 64,
        target_sync_every: int = 100,
    ):
        self.rng = np.random.default_rng(seed)
        self.state_size = state_size
        self.action_size = action_size
        self.memory: deque[Transition] = deque(maxlen=12000)
        self.gamma = gamma
        self.epsilon = 1.0
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min
        self.batch_size = batch_size
        self.target_sync_every = target_sync_every
        self.learn_steps = 0
        self.model = QNetwork(state_size, action_size, self.rng)
        self.target_model = QNetwork(state_size, action_size, self.rng)
        self.update_target_model()

    def act(self, state: np.ndarray, mask: np.ndarray, greedy: bool = False) -> int:
        available = np.flatnonzero(mask)
        if len(available) == 0:
            raise ValueError("선택 가능한 적재 위치가 없습니다.")
        if not greedy and self.rng.random() < self.epsilon:
            return int(self.rng.choice(available))
        qvalues = self.model.predict(state.reshape(1, -1))[0]
        return int(available[np.argmax(qvalues[available])])

    def remember(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool,
        next_mask: np.ndarray,
    ) -> None:
        self.memory.append(
            Transition(state.copy(), action, reward, next_state.copy(), done, next_mask.copy())
        )

    def replay(self) -> float | None:
        if len(self.memory) < self.batch_size:
            return None
        indices = self.rng.choice(len(self.memory), size=self.batch_size, replace=False)
        batch = [self.memory[int(i)] for i in indices]
        states = np.stack([t.state for t in batch])
        next_states = np.stack([t.next_state for t in batch])
        actions = np.array([t.action for t in batch], dtype=np.int64)
        rewards = np.array([t.reward for t in batch], dtype=np.float32)
        dones = np.array([t.done for t in batch], dtype=bool)
        masks = np.stack([t.next_mask for t in batch])
        next_q = self.target_model.predict(next_states)
        next_q[~masks] = -np.inf
        best_q = np.max(next_q, axis=1)
        best_q[~np.isfinite(best_q)] = 0
        targets = rewards + self.gamma * best_q * (~dones)
        loss = self.model.train_batch(states, actions, targets)
        self.learn_steps += 1
        if self.learn_steps % self.target_sync_every == 0:
            self.update_target_model()
        return loss

    def end_episode(self) -> None:
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def update_target_model(self) -> None:
        self.target_model.copy_from(self.model)

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {f"W{i}": w for i, w in enumerate(self.model.weights)}
        payload.update({f"b{i}": b for i, b in enumerate(self.model.biases)})
        payload["epsilon"] = np.array(self.epsilon)
        np.savez_compressed(path, **payload)

    def load(self, path: str | Path) -> None:
        with np.load(path, allow_pickle=False) as arr:
            self.model.weights = [arr[f"W{i}"].astype(np.float32) for i in range(3)]
            self.model.biases = [arr[f"b{i}"].astype(np.float32) for i in range(3)]
            self.epsilon = float(arr["epsilon"])
        self.update_target_model()
