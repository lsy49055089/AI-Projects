"""창고 환경, 데이터 전처리, DQN 학습 단위 시험."""

import json

import numpy as np
import pandas as pd

from create_sample_data import generate_sample_csv
from dqn_agent import DQNAgent
from evaluate import evaluate
from preprocessing import export_json, preprocess, read_retail_data
from train import train
from warehouse_env import WarehouseEnv


ITEMS = [
    {"Name": "Product-A", "Type": "Product", "Weight": 70, "UnitPrice": 5, "Quantity": 25},
    {"Name": "Product-B", "Type": "Product", "Weight": 20, "UnitPrice": 2, "Quantity": 40},
    {"Name": "Return-A", "Type": "Return Zone", "Weight": 20, "UnitPrice": 5, "Quantity": 32},
    {"Name": "Return-B", "Type": "Return Zone", "Weight": 70, "UnitPrice": 3, "Quantity": 17},
]


def test_layout_state_action_space():
    env = WarehouseEnv(ITEMS, max_steps=10)
    state = env.reset(1)
    assert env.layout.shape == (10, 7)
    assert env.action_size == 33
    assert len(state) == 146
    assert env.available_actions().sum() == 33


def test_item_features_visible_before_action():
    env = WarehouseEnv(ITEMS, seed=6)
    state = env.reset(3)
    assert state[-3] == 0  # 첫 물품은 Product
    assert state[-2] == float(env.floor_for(env.current_item) == 1)
    assert state[-6] > 0


def test_position_reward_and_mask():
    env = WarehouseEnv(ITEMS, max_steps=12, seed=42)
    env.reset(4)
    assert env.current_item["Type"] == "Product"
    action = env.valid_positions.index((0, 0))
    floor = env.floor_for(env.current_item)
    next_state, reward, done, info = env.step(action)
    assert info["placed"] is True
    assert reward > 10
    assert not done
    assert env.current_item["Type"] == "Return Zone"
    assert len(next_state) == 146
    assert env.floor_for(info["item"]) == floor
    return_action = env.valid_positions.index((8, 0))
    _, return_reward, _, ret_info = env.step(return_action)
    assert ret_info["placed"]
    assert return_reward > 0


def test_occupied_cell_penalty():
    env = WarehouseEnv(ITEMS)
    env.reset()
    idx = env.valid_positions.index((2, 0))
    floor = env.floor_for(env.current_item)
    if floor == 1:
        env.state_1f[2, 0] = 99
    else:
        env.state_2f[2, 0] = 49
    assert not env.available_actions()[idx]
    _, reward, _, info = env.step(idx)
    assert reward == -15
    assert not info["placed"]


def test_preprocessing_return_and_feature_consistency():
    data = pd.DataFrame(
        [
            ["100", "A", "Widget", 10, 2.0],
            ["C101", "A", "Widget", -20, 2.0],
            ["102", "A", "Widget", 5, 2.0],
            ["103", "B", "Gadget", 0, 2.0],
            ["104", "C", "Invalid", 5, -1.0],
        ],
        columns=["InvoiceNo", "StockCode", "Description", "Quantity", "UnitPrice"],
    )
    records = preprocess(data, seed=42)
    assert len(records) == 2
    assert sorted(x["Type"] for x in records) == ["Product", "Return Zone"]
    assert {x["Quantity"] for x in records} == {15, 20}
    assert len({x["Weight"] for x in records}) == 1
    assert records == preprocess(data, seed=42)


def test_agent_replay_changes_weights_and_save(tmp_path):
    env = WarehouseEnv(ITEMS, max_steps=7)
    agent = DQNAgent(env.state_size, env.action_size, seed=42, batch_size=2, target_sync_every=2)
    before = [w.copy() for w in agent.model.weights]
    for _ in range(2):
        state = env.reset(2)
        available = env.available_actions()
        action = agent.act(state, available)
        next_state, reward, done, _ = env.step(action)
        agent.remember(state, action, reward, next_state, done, env.available_actions())
    assert agent.replay() is not None
    assert agent.learn_steps == 1
    assert any(not np.array_equal(a, b) for a, b in zip(before, agent.model.weights))
    agent.save(tmp_path / "weights.npz")
    other = DQNAgent(env.state_size, env.action_size, seed=43)
    other.load(tmp_path / "weights.npz")
    assert all(np.array_equal(a, b) for a, b in zip(agent.model.weights, other.model.weights))


def test_end_to_end_outputs(tmp_path):
    csv_path = generate_sample_csv(tmp_path / "sample.csv")
    records = preprocess(read_retail_data(csv_path))
    assert len(records) >= 40
    json_path = tmp_path / "Combined_States.json"
    export_json(records, json_path)
    out = tmp_path / "out"
    summary = train(json_path, out, episodes=4, max_steps=8, gif_every=4, batch_size=4)
    assert summary["training_updates"] > 0
    for relative in (
        "dqn_weights.npz", "graph/final_rewards_graph.png", "sample_episodes/episode_004.gif",
        "history/episode_rewards.csv", "history/highest_rewards.json", "history/training_summary.json",
    ):
        assert (out / relative).is_file(), relative
    with open(out / "history/highest_rewards.json", encoding="utf-8") as f:
        assert len(json.load(f)) == 4
    comparison = evaluate(json_path, out / "dqn_weights.npz", out / "history/evaluation.json", episodes=4, max_steps=8)
    assert "trained_mean_reward" in comparison
    assert "random_mean_reward" in comparison
