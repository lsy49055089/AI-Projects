import os
import json
import random
import numpy as np
import time
import matplotlib.pyplot as plt
import imageio
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout
from tensorflow.keras.optimizers import Adam
from collections import deque

combined_states_path = "C:/project/final/datasets/preprocessing/Combined_States.json"
graph_output_path = "C:/project/final/datasets/graph"
gif_output_path = "C:/project/final/datasets/sample_episodes"
history_output_path = "C:/project/final/datasets/history"

class WarehouseEnv:
    def __init__(self, combined_states):
        self.states = combined_states
        self.layout = np.array([
            [1, 1, 1, 1, 1, 1, 1],
            [0, 0, 0, 0, 0, 0, 0],
            [1, 1, 1, 1, 1, 1, 1],
            [0, 0, 0, 0, 0, 0, 0],
            [1, 1, 1, 1, 1, 1, 1],
            [0, 0, 0, 0, 0, 0, 0],
            [1, 1, 0, 0, 0, 1, 1],
            [1, 1, 0, 0, 0, 1, 1],
            [1, 1, 0, 0, 0, 1, 1],
            [0, 0, 0, 0, 0, 0, 0]
        ], dtype=int)
        self.max_weight_1f = 100
        self.max_weight_2f = 50
        self.state_1f = np.zeros_like(self.layout, dtype=np.float32)
        self.state_2f = np.zeros_like(self.layout, dtype=np.float32)
        self.items_1f = np.empty(self.layout.shape, dtype=object)
        self.items_2f = np.empty(self.layout.shape, dtype=object)
        self.total_reward = 0
        self.valid_positions = np.argwhere(self.layout == 1).tolist()
        self.current_item_type = "Product"

    def reset(self):
        self.state_1f = np.zeros_like(self.layout, dtype=float)
        self.state_2f = np.zeros_like(self.layout, dtype=float)
        self.items_1f = np.empty(self.layout.shape, dtype=object)
        self.items_2f = np.empty(self.layout.shape, dtype=object)
        self.total_reward = 0
        self.current_item_type = "Product"
        return np.concatenate([self.state_1f.flatten(), self.state_2f.flatten()])

    def get_next_item(self):
        if self.current_item_type == "Product":
            self.current_item_type = "Return Zone"
            item = random.choice([item for item in self.states if item["Type"] == "Product"])
        else:
            self.current_item_type = "Product"
            item = random.choice([item for item in self.states if item["Type"] == "Return Zone"])

        return item

    def step(self, action, item, step_level=1):
        x, y = self.valid_positions[action]
        weight = item.get("Weight", 0)
        unit_price = item.get("UnitPrice", 0)
        quantity = item.get("Quantity", 0)
        item_type = item.get("Type", "Product")
        name = item.get("Name", "Unknown")

        reward = 0

        if self.state_1f[x, y] == 0 or self.state_2f[x, y] == 0:
            reward += 0.5

        if step_level >= 1:
            if item_type == "Return Zone":
                if (x, y) in [(6, 0), (6, 1), (7, 0), (7, 1), (8, 0), (8, 1)]:
                    reward += 5
                else:
                    reward -= 10
            elif item_type == "Product":
                if (x, y) in [(6, 0), (6, 1), (7, 0), (7, 1), (8, 0), (8, 1)]:
                    reward -= 5
                else:
                    reward += 10

        if step_level >= 2:
            if x < 5:
                reward += 1.0 if 50 <= weight <= 200 else -1.0
            else:
                reward += 1.0 if 0 <= weight <= 50 else -1.0

        if step_level >= 3:
            if (x, y) in [(8, 0), (8, 1)]:
                reward += 1.0 if quantity >= 30 else 0
            elif (x, y) in [(7, 0), (7, 1)]:
                reward += 0.7 if quantity >= 15 else 0
            elif (x, y) in [(6, 0), (6, 1)]:
                reward += 0.5 if quantity >= 1 else 0

        if step_level >= 4:
            if x == 0:
                reward += 1.0 if unit_price >= 4 else 0
            elif x == 2:
                reward += 0.7 if unit_price >= 2 else 0
            elif x == 4:
                reward += 0.5 if unit_price < 2 else 0

        max_reward = 15
        min_reward = -15
        reward = np.clip(reward, min_reward, max_reward)

        if 50 <= weight <= 200:
            if self.state_1f[x, y] + weight <= self.max_weight_1f:
                self.state_1f[x, y] += weight
                self.items_1f[x, y] = item
        elif 0 <= weight <= 50:
            if self.state_2f[x, y] + weight <= self.max_weight_2f:
                self.state_2f[x, y] += weight
                self.items_2f[x, y] = item

        self.total_reward += reward
        next_state = np.concatenate([self.state_1f.flatten(), self.state_2f.flatten()])
        done = self.total_reward >= 5000

        return next_state, reward, done

class DQNAgent:
    def __init__(self, state_size, action_size):
        self.state_size = state_size
        self.action_size = action_size
        self.memory = deque(maxlen=12000)
        self.gamma = 0.95
        self.epsilon = 1.0
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.999
        self.model = self.build_model()
        self.target_model = self.build_model()
        self.update_target_model()

    def build_model(self):
        model = Sequential([
            Dense(64, input_dim=self.state_size, activation='relu'),
            Dense(64, activation='relu'),
            Dense(self.action_size, activation='linear')
        ])
        model.compile(loss='mse', optimizer=Adam(learning_rate=0.001))
        return model

    def act(self, state):
        if np.random.rand() <= self.epsilon:
            return random.randrange(self.action_size)
        act_values = self.model.predict(state, verbose=0)
        return np.argmax(act_values[0])
   
    def update_target_model(self):
        self.target_model.set_weights(self.model.get_weights())

    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))

    def replay(self, batch_size):
        minibatch = random.sample(self.memory, batch_size)
        for state, action, reward, next_state, done in minibatch:
            self._update_model(state, action, reward, next_state, done)

        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

        if random.random() < 0.1:
            self.update_target_model()

    def _update_model(self, state, action, reward, next_state, done):
        target = reward
        if not done:
            target += self.gamma * np.amax(self.target_model.predict(next_state, verbose=0)[0])
        target_f = self.model.predict(state, verbose=0)
        target_f[0][action] = target
        self.model.fit(state, target_f, epochs=1, verbose=0)

        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

def save_gif(frames, path, episode):
    os.makedirs(path, exist_ok=True)
    gif_path = os.path.join(path, f"episode_{episode}.gif")
    imageio.mimsave(gif_path, frames, fps=2)
    print(f"GIF 저장 완료: {gif_path}")

def save_highest_reward(epoch, data, path):
    os.makedirs(path, exist_ok=True)
    history_path = os.path.join(path, "highest_rewards.json")
   
    if os.path.exists(history_path):
        with open(history_path, "r", encoding="utf-8") as f:
            history = json.load(f)
    else:
        history = {}

    history[f"Epoch {epoch}"] = data

    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4, ensure_ascii=False)
    print(f"최고 점수 저장 완료: {history_path}")

def plot_rewards(rewards):
    plt.figure(figsize=(10, 5))
    plt.plot(rewards, label="Episode Reward")
    plt.xlabel("Episodes")
    plt.ylabel("Total Reward")
    plt.title("Reward Progression Over Episodes")
    plt.legend()
    plt.grid()
    plt.show()

def plot_rewards(rewards, save_path):
    plt.figure(figsize=(10, 5))
    plt.plot(rewards, label="Episode Reward")
    plt.xlabel("Episodes")
    plt.ylabel("Total Reward")
    plt.title("Reward Progression Over Episodes")
    plt.legend()
    plt.grid()
    plt.savefig(os.path.join(save_path, "final_rewards_graph.png"))
    plt.show()

start_time = time.time()

try:
    with open(combined_states_path, "r", encoding="utf-8") as f:
        combined_states = json.load(f)

    env = WarehouseEnv(combined_states)
    state_size = len(env.state_1f.flatten()) + len(env.state_2f.flatten())
    action_size = len(env.valid_positions)
    agent = DQNAgent(state_size, action_size)

    num_episodes = 300
    max_steps = 450
    episodes_per_level = num_episodes // 4
    max_step_level = 4

    all_rewards = []
    episode_rewards = []

    gif_output_path = "C:/project/final/datasets/sample_episodes"
    graph_output_path = "C:/project/final/datasets/graph"

    fig, axes = plt.subplots(1, 3, figsize=(18, 8))
    plt.ion()

    for episode in range(num_episodes):
        step_level = min((episode // episodes_per_level) + 1, max_step_level)

        state = env.reset().reshape(1, -1)
        total_reward = 0
        frames = []

        for step in range(max_steps):
            action = agent.act(state)
            item = env.get_next_item()
            next_state, reward, done = env.step(action, item, step_level=step_level)
            state = next_state.reshape(1, -1)
            total_reward += reward

            axes[0].clear()
            axes[0].imshow(env.state_1f, cmap="Blues", interpolation="nearest")
            axes[0].set_title(f"1F Layout (Weights) - Episode {episode + 1}, Step {step + 1}")
            axes[0].set_xticks([])
            axes[0].set_yticks([])

            for (x, y), value in np.ndenumerate(env.state_1f):
                if env.layout[x, y] == 1:
                    item = env.items_1f[x, y]
                    name = item.get("Name", "N/A") if item else "None"
                    weight = item.get("Weight", "N/A") if item else "None"
                    unit_price = item.get("UnitPrice", "N/A") if item else "None"
                    item_type = item.get("Type", "N/A") if item else "N/A"
                    quantity = item.get("Quantity", "N/A") if item else "None"
                    text = f"N:{name}\nWt:{weight}\nP:{unit_price}\nT:{item_type}\nQty:{quantity}"
                    axes[0].text(y, x, text, ha="center", va="center", fontsize=8, bbox=dict(facecolor='white', alpha=0.7))

            axes[1].clear()
            axes[1].imshow(env.state_2f, cmap="Oranges", interpolation="nearest")
            axes[1].set_title(f"2F Layout (Weights) - Episode {episode + 1}, Step {step + 1}")
            axes[1].set_xticks([])
            axes[1].set_yticks([])

            for (x, y), value in np.ndenumerate(env.state_2f):
                if env.layout[x, y] == 1:
                    item = env.items_2f[x, y]
                    name = item.get("Name", "N/A") if item else "None"
                    weight = item.get("Weight", "N/A") if item else "None"
                    unit_price = item.get("UnitPrice", "N/A") if item else "None"
                    item_type = item.get("Type", "N/A") if item else "N/A"
                    quantity = item.get("Quantity", "N/A") if item else "None"
                    text = f"N:{name}\nWt:{weight}\nP:{unit_price}\nT:{item_type}\nQty:{quantity}"
                    axes[1].text(y, x, text, ha="center", va="center", fontsize=8, bbox=dict(facecolor='white', alpha=0.7))

            axes[2].clear()
            axes[2].set_title("Episode Rewards Progress")
            axes[2].set_xlabel("Episodes")
            axes[2].set_ylabel("Total Reward")
            axes[2].plot(range(len(episode_rewards)), episode_rewards, color="green", label="Total Rewards")
            axes[2].legend()
            axes[2].grid(True)

            plt.tight_layout()
            plt.pause(0.005)

            fig.canvas.draw()
            frame = np.frombuffer(fig.canvas.tostring_rgb(), dtype='uint8')
            frame = frame.reshape(fig.canvas.get_width_height()[::-1] + (3,))
            frames.append(frame)

            if done:
                break

        episode_rewards.append(total_reward)
        print(f"Episode {episode + 1}/{num_episodes}, Step Level: {step_level}, Total Reward: {total_reward}")

        if (episode + 1) % 5 == 0:
            save_gif(frames, gif_output_path, episode + 1)

    plt.ioff()
    plot_rewards(episode_rewards, graph_output_path)

except Exception as e:
    print(f"Error occurred: {e}")

finally:
    end_time = time.time()
    elapsed_time = (end_time - start_time) / 60
    print(f"전체 실행 시간: {elapsed_time:.2f} 분")
    print("Training completed. All resources released.")
