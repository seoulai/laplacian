"""
James Park, laplacian.k@gmail.com
seoulai.com
2018
"""

import seoulai_gym as gym
import numpy as np
import pandas as pd
import random
import logging
import time

from seoulai_gym.envs.market.agents import Agent
from seoulai_gym.envs.market.base import Constants
from seoulai_gym.envs.market.utils import trades_slicer, get_ohclv
from itertools import count

from collections import deque
from keras.models import Sequential
from keras.layers import Dense
from keras.optimizers import Adam
from keras.models import load_model

logging.basicConfig(level=logging.INFO)


class DQNAgent(Agent):
    def __init__(
        self,
        agent_id: str,
    ):

        """ 1. You must define dictionary of actions! (key = action_name, value = order_parameters)

            your_actions = dict(
                action_name1 = order_parameters 1,
                action_name2 = order_parameters 2,
                ...
            )

            2. Order parameters
            order_parameters = +10 It means that your agent'll buy 10 bitcoins.
            order_parameters = -20 It means that your agent'll sell 20 bitcoins.

            order_parameters = (+10, "%") It means buying 10% of the available amount.
            order_parameters = (-20, "%") It  means selling 20% of the available amount.

            3. If you want to add "hold" action, just define "your_hold_action_name = 0"

            4. You must return dictionary of actions.
        """
        your_actions = dict(
            holding=0,
            buy_10per=(+10, "%"),
            buy_25per=(+25, "%"),
            buy_50per=(+50, "%"),
            buy_100per=(+100, "%"),
            sell_10per=(-10, "%"),
            sell_25per=(-25, "%"),
            sell_50per=(-50, "%"),
            sell_100per=(-100, "%"),
        )
        super().__init__(agent_id, your_actions)

        self.state_size = 6
        self.memory = deque(maxlen=2000)
        self.gamma = 0.95    # discount rate
        self.epsilon = 1.0  # exploration rate
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        self.learning_rate = 0.001
        self.model = self._build_model()
        self.batch_size = 32
        self.win_cnt = 0

    def _build_model(
        self,
    ):
        # Neural Net for Deep-Q learning Model
        model = Sequential()
        model.add(Dense(24, input_dim=self.state_size, activation="relu"))
        model.add(Dense(24, activation="relu"))
        model.add(Dense(self.action_spaces, activation="linear"))
        model.compile(loss="mse",
                      optimizer=Adam(lr=self.learning_rate))
        return model

    def remember(
        self,
        state,
        action,
        next_state,
        reward,
    ):
        data = (state, action, next_state, reward)
        self.memory.append(data)

    def replay(
        self,
    ):
        minibatch = random.sample(self.memory, self.batch_size)
        loss_history = []

        for state, action, next_state, reward in minibatch:
            target = (reward + self.gamma *
                      np.amax(self.model.predict(next_state)[0]))

            target_f = self.model.predict(state)
            index = action.get("index")
            target_f[0][index] = target
            hist = self.model.fit(state, target_f, epochs=1, verbose=0)
            loss_history.append(hist.history["loss"])

        logging.info(f"EPSILON {self.epsilon}")
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

        return loss_history

    def preprocess(
        self,
        obs,
    ):

        # get data
        order_book = obs.get("order_book")
        trades = obs.get("trade")
        agent_info = obs.get("agent_info")
        portfolio_rets = obs.get("portfolio_rets")

        # time series data
        price_list_200 = trades.get("price")
        volume_list_200 = trades.get("volume")

        # slice timeseries data(normal)
        price5 = price_list_200[:5]
        volume5 = volume_list_200[:5]

        # slice timeseries data(util)
        price_volume10 = trades_slicer(trades, start=0, end=10, keys=["price", "volume"])
        price10 = price_volume10["price"]
        volume10 = price_volume10["volume"]
        trade40 = trades_slicer(trades, end=40, to="df")
        trade200 = trades_slicer(trades, end=200, to="df")

        # get statistics (normal)
        ma5 = np.mean(price5)
        ma10 = np.mean(price10)
        ma40 = trade40.price.mean()
        ma200 = trade200.price.mean()
        mv5 = np.mean(volume5)

        # get statistics (util)
        ohclv = get_ohclv(trade200)

        # agent data
        cash = agent_info.get("cash")
        asset_qtys = agent_info.get("asset_qtys")
        asset_qty = asset_qtys["KRW-BTC"]

        # the last limit order book
        ask_price = order_book.get("ask_price")
        bid_price = order_book.get("bid_price")

        # the last trade
        cur_price = price_list_200[0]
        volume = volume_list_200[0]

        # target data
        gap = abs(ask_price-bid_price)
        pred_fee = round(cur_price*self.fee_rt, 4)
        portfolio_val = portfolio_rets.get("val")
        asset_val = round(asset_qty*cur_price, 4)

        # nomalized data
        cash_ratio = round(cash/portfolio_val, 2)
        gap_per = round(gap/pred_fee-1, 2)

        signal1 = 1.0 if ma5 > ma10 else 0.0
        signal2 = 1.0 if ma5 > ma40 else 0.0
        signal3 = 1.0 if ma5 > ma200 else 0.0

        ma200_ratio = round(cur_price/ma200-1, 3)

        state = [cash_ratio, gap_per, signal1, signal2, signal3, ma200_ratio]
        state = np.reshape(state, [1, self.state_size])

        return state

    def algo(
        self,
        state,
    ):
        # print(state.keys())

        logging.info(f"STATE {state}")

        if np.random.rand() <= self.epsilon:
            return self.action(np.random.choice(range(self.action_spaces)))
        else:
            act_values = self.model.predict(state)
            index = np.argmax(act_values[0])
            return self.action(index)

    def postprocess(
        self,
        obs,
        action,
        next_obs,
        rewards,
    ):

        self.logging(obs, action, next_obs, rewards)

        # define reward
        reward = rewards.get("real_hit")

        # win_ratio
        self.win_cnt += reward

        # transform data
        state = self.preprocess(obs)
        next_state = self.preprocess(next_obs)

        # remember
        self.remember(state, action, next_state, reward)

        # replay
        if len(self.memory) > self.batch_size:
            self.replay()

    def logging(
        self,
        obs,
        action,
        next_obs,
        rewards,
    ):
        # logging.info(f"OBS : {obs}")
        agent_info = obs.get("agent_info")
        logging.info(f"AGENT_INFO: {agent_info}")
        logging.info(f"ACTION : {action}")
        # logging.info(f"NEXT_OBS : {next_obs}")
        logging.info(f"REWARDS : {rewards}")

    def load(self, name):
        self.model.load_weights(name)

    def save(self, name):
        self.model.save_weights(name)


if __name__ == "__main__":

    your_id = "james_dqn"
    mode = Constants.TEST    # participants can select mode

    a1 = DQNAgent(
         your_id,
         )

    env = gym.make("Market")
    env.participate(your_id, mode)
    obs = env.reset()

    for t in count():    # Online RL
        logging.info(f"step {t}")

        action = a1.act(obs)    # Local function
        next_obs, rewards, done, _ = env.step(**action)
        a1.postprocess(obs, action, next_obs, rewards)

        # Win ratio
        win_ratio = round((a1.win_cnt/float(t+1))*100, 2)
        logging.info(f"WIN_RATIO {win_ratio}")

        if done:
            break

        obs = next_obs
        logging.info(f"==========================================================================================")
