import os
import platform
import subprocess
import gnubg
from pybg.agents.base_agent import BaseAgent

print(dir(gnubg))


class GnubgAgent(BaseAgent):

    def make_decision(self, observation=None, action_mask=None):
        pass
