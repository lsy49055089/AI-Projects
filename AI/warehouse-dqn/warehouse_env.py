"""격자형 2층 창고의 물품 배치 환경."""

from __future__ import annotations

import random
from typing import Any

import numpy as np


class WarehouseEnv:
    LAYOUT = np.array(
        [
            [1, 1, 1, 1, 1, 1, 1],
            [0, 0, 0, 0, 0, 0, 0],
            [1, 1, 1, 1, 1, 1, 1],
            [0, 0, 0, 0, 0, 0, 0],
            [1, 1, 1, 1, 1, 1, 1],
            [0, 0, 0, 0, 0, 0, 0],
            [1, 1, 0, 0, 0, 1, 1],
            [1, 1, 0, 0, 0, 1, 1],
            [1, 1, 0, 0, 0, 1, 1],
            [0, 0, 0, 0, 0, 0, 0],
        ],
        dtype=np.uint8,
    )
    RETURN_POSITIONS = frozenset((row, col) for row in (6, 7, 8) for col in (0, 1))
    FLOOR_CAPACITY = {1: 100.0, 2: 50.0}

    def __init__(self, combined_states: list[dict[str, Any]], max_steps: int = 30, seed: int = 42):
        self.states = [dict(item) for item in combined_states]
        self.products = [item for item in self.states if item.get("Type") == "Product"]
        self.returns = [item for item in self.states if item.get("Type") == "Return Zone"]
        if not self.products or not self.returns:
            raise ValueError("Product와 Return Zone 상품이 각각 한 개 이상 필요합니다.")
        for item in self.states:
            weight = float(item.get("Weight", 0))
            if not 0 < weight <= self.FLOOR_CAPACITY[1]:
                raise ValueError(f"상품 무게는 0 초과 100 이하여야 합니다: {item.get('Name')}")
        if max_steps < 1:
            raise ValueError("max_steps는 1 이상이어야 합니다.")

        self.rng = random.Random(seed)
        self.layout = self.LAYOUT.copy()
        self.valid_positions = [tuple(map(int, pos)) for pos in np.argwhere(self.layout == 1)]
        self.action_size = len(self.valid_positions)
        self.max_steps = max_steps
        self.state_size = self.layout.size * 2 + 6
        self.step_level = 1
        self.reset(step_level=1)

    @staticmethod
    def floor_for(item: dict[str, Any]) -> int:
        # 50 이하 경량 물품은 2층, 50 초과 중량 물품은 1층에 적재한다.
        return 2 if float(item["Weight"]) <= 50 else 1

    def _choose_item(self) -> dict[str, Any]:
        pool = self.products if self.next_type == "Product" else self.returns
        item = self.rng.choice(pool)
        self.next_type = "Return Zone" if self.next_type == "Product" else "Product"
        return item

    def reset(self, step_level: int = 1) -> np.ndarray:
        if step_level not in (1, 2, 3, 4):
            raise ValueError("step_level은 1~4여야 합니다.")
        self.step_level = step_level
        self.state_1f = np.zeros_like(self.layout, dtype=np.float32)
        self.state_2f = np.zeros_like(self.layout, dtype=np.float32)
        self.items_1f = np.full(self.layout.shape, None, dtype=object)
        self.items_2f = np.full(self.layout.shape, None, dtype=object)
        self.total_reward = 0.0
        self.steps = 0
        self.next_type = "Product"
        self.current_item = self._choose_item()
        return self.observe()

    def observe(self) -> np.ndarray:
        item = self.current_item
        item_floor = self.floor_for(item)
        extra = np.array(
            [
                float(item["Weight"]) / 100.0,
                min(float(item.get("UnitPrice", 0)), 50.0) / 50.0,
                min(float(item.get("Quantity", 0)), 300.0) / 300.0,
                float(item.get("Type") == "Return Zone"),
                float(item_floor == 1),
                self.steps / self.max_steps,
            ],
            dtype=np.float32,
        )
        return np.concatenate(
            [
                (self.state_1f / self.FLOOR_CAPACITY[1]).ravel(),
                (self.state_2f / self.FLOOR_CAPACITY[2]).ravel(),
                extra,
            ]
        ).astype(np.float32)

    def available_actions(self) -> np.ndarray:
        floor_state = self.state_1f if self.floor_for(self.current_item) == 1 else self.state_2f
        return np.array([floor_state[x, y] == 0 for x, y in self.valid_positions], dtype=bool)

    def _reward_for(self, pos: tuple[int, int], item: dict[str, Any]) -> float:
        x, y = pos
        is_return = item["Type"] == "Return Zone"
        in_return_zone = pos in self.RETURN_POSITIONS
        reward = 0.5  # 비어 있는 적재 위치에 물품을 배치한다.

        if is_return:
            reward += 5.0 if in_return_zone else -10.0
        else:
            reward += -5.0 if in_return_zone else 10.0

        if self.step_level >= 2:
            reward += 1.0  # 층별 중량 제한을 만족하는 물품만 배치한다.

        if self.step_level >= 3 and is_return:
            quantity = float(item.get("Quantity", 0))
            if x == 8 and y in (0, 1) and quantity >= 30:
                reward += 1.0
            elif x == 7 and y in (0, 1) and quantity >= 15:
                reward += 0.7
            elif x == 6 and y in (0, 1) and quantity >= 1:
                reward += 0.5

        if self.step_level >= 4 and not is_return:
            unit_price = float(item.get("UnitPrice", 0))
            if x == 0 and unit_price >= 4:
                reward += 1.0
            elif x == 2 and unit_price >= 2:
                reward += 0.7
            elif x == 4 and unit_price < 2:
                reward += 0.5

        return float(np.clip(reward, -15, 15))

    def step(self, action: int) -> tuple[np.ndarray, float, bool, dict[str, Any]]:
        if not 0 <= action < self.action_size:
            raise IndexError(f"행동 인덱스가 범위를 벗어났습니다: {action}")
        item = self.current_item
        x, y = self.valid_positions[action]
        floor = self.floor_for(item)
        floor_state = self.state_1f if floor == 1 else self.state_2f
        floor_items = self.items_1f if floor == 1 else self.items_2f
        placed = floor_state[x, y] == 0

        if placed:
            floor_state[x, y] = float(item["Weight"])
            floor_items[x, y] = dict(item)
            reward = self._reward_for((x, y), item)
        else:
            reward = -15.0

        self.total_reward += reward
        self.steps += 1
        info = {"floor": floor, "position": (x, y), "placed": bool(placed), "item": dict(item)}
        done = self.steps >= self.max_steps
        if not done:
            self.current_item = self._choose_item()
            done = not self.available_actions().any()
        return self.observe(), float(reward), bool(done), info
