"""
James Park, laplacian.k@gmail.com
seoulai.com
2018
"""

import seoulai_gym as gym
import numpy as np
import time
import requests

from seoulai_gym.envs.market.agents import Agent
from seoulai_gym.envs.market.base import Constants
from itertools import count


class HFTAgent(Agent):

    def api_upbit_get(
        self,
        cmd,
        data,
    ):
        url = "https://api.upbit.com/v1/" + cmd
        conditions = [key+"="+value for key, value in data.items()]
        query = "?" + "&".join(conditions)
        url += query
        r = requests.get(url)

        if r.status_code == 200:
            return r.json()
        return None

    def _get_upbit_price(
        self,
    ):
        # get upbit data
        trade_data = dict(market="KRW-BTC")
        trade = self.api_upbit_get("trades/ticks", trade_data)
        trade = trade[0]
        upbit_price = trade["trade_price"]
        return upbit_price

    def preprocess(
        self,
        obs,
    ):
        # get data
        upbit_price = self._get_upbit_price()
        trades = obs.get("trade")
        cur_price = trades["price"][0]
        print("seoul_ai", cur_price, "upbit_price", upbit_price)

        order_book = obs.get("order_book")
        buy_price = order_book.get("ask_price")
        sell_price = order_book.get("bid_price")
        print("buy_price", buy_price, "sell_price", sell_price)

        # n = 100
        # price_n= trades["price"][:n]

        # ma = np.mean(price_n)
        # std = np.std(price_n)
        # thresh_hold = 1.0

        your_state = dict(
            buy_signal=(upbit_price > buy_price * (1+self.fee_rt)),
            sell_signal=(upbit_price < sell_price * (1-self.fee_rt)),
        )

        return your_state 

    def algo(
        self,
        state,
    ):
        # print(state.keys())
        print(state["buy_signal"], state["sell_signal"])

        if state["buy_signal"]: 
            return self.action("buy_all")
        elif state["sell_signal"]:
            return self.action("sell_all")
        else:
            return self.action(0)    # you can use number of index.

    def postprocess(
        self,
        obs,
        action,
        next_obs,
        rewards,
    ):
        pass 


if __name__ == "__main__":

    your_id = "time_spread"
    mode = Constants.HACKATHON    # participants can select mode 

    """ 1. You must define dictionary of actions! (key = action_name, value = order_parameters)
        
        your_actions = dict(
            action_name1 = order_parameters 1,
            action_name2 = order_parameters 2,
            ...
        )

        2. Order parameters
        order_parameters = +10 It means that your agent'll buy 10 bitcoins.
        order_parameters = -20 It means that your agent'll sell 20 bitcoins.

        order_parameters = (+10, '%') It means buying 10% of the available amount.
        order_parameters = (-20, '%') It  means selling 20% of the available amount.

        3. If you want to add "hold" action, just define "your_hold_action_name = 0"

        4. You must return dictionary of actions.
    """

    your_actions = dict(
        holding = 0,
        buy_all= (+100, "%"),
        sell_all= (-100, "%"),
    )

    a1 = HFTAgent(
         your_id,
         your_actions,
         )

    env = gym.make("Market")
    env.participate(your_id, mode)
    obs = env.reset()

    for t in count():    # Online RL
        print("step {0}".format(t)) 

        agent_info = obs.get("agent_info")
        print("AGENT_INFO", agent_info)
        action = a1.act(obs)    # Local function
        next_obs, rewards, done, _= env.step(**action)
        a1.postprocess(obs, action, next_obs, rewards)
        print("ACTION", action)
        print("REWARDS", rewards)

        if done:
            break

        obs = next_obs
        print(f"==========================================================================================")
