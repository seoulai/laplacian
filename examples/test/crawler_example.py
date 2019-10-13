"""
James Park, laplacian.k@gmail.com
seoulai.com
2018
"""

import seoulai_gym as gym
import numpy as np
import time
import logging

from seoulai_gym.envs.market.agents import Agent
from seoulai_gym.envs.market.base import Constants
from itertools import count

logging.basicConfig(level=logging.INFO, format='%(asctime)s, %(message)s')

class RandomAgent(Agent):

    def set_actions(
        self,
    )->dict:

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

        your_actions = {}

        your_actions = dict(
            holding = 0,
            buy_all = (+100, '%'),
            sell_all= (-100, '%'),
        )

        return your_actions 

    def algo(
        self,
        state,
    ):
        # print(state.keys())

        return self.action(np.random.choice(range(self.action_spaces)))


    def postprocess(
        self,
        obs,
        action,
        next_obs,
        rewards,
    ):
        observation = {}
        order_books = obs["order_book"]
        trades = obs["trade"]
        observation.update(dict(
            order_book=order_books,
            trade=trades,))
        logging.info(f"{observation}")

if __name__ == "__main__":

    your_id = "random"
    mode = Constants.HACKATHON    # participants can select mode 

    a1 = RandomAgent(
         your_id,
         )

    env = gym.make("Market")
    env.participate(your_id, mode)
    obs = env.reset()

    for t in count():    # Online RL
        action = a1.act(obs)    # Local function
        next_obs, rewards, done, _= env.step(**action)
        a1.postprocess(obs, action, next_obs, rewards)


        time.sleep(0.3)
        obs = next_obs
