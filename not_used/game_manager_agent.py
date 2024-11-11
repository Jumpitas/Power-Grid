import asyncio
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import random
import json

class GameManagerAgent(CyclicBehaviour):
    def __init__(self):
        self.players = []
        self.current_phase = "setup" # string para guardar a fase do jogo atual
        self.round=1
        self.map = self.get_map()

    async def run(self):
        while True:
            if self.current_phase == "setup":
                await self.setup_phase()
            elif self.current_phase == "phase1":
                await self.phase1()
            elif self.current_phase == "phase2":
                await self.phase2()
            elif self.current_phase == "phase3":
                await self.phase3()
            elif self.current_phase == "phase4":
                await self.phase4()
            elif self.current_phase == "phase5":
                await self.phase5()
            else:
                pass
                # placeholder pq nao me lembro se ha mais
            await asyncio.sleep(1)  # Adjust timing as needed


    async def setup_phase(self):
        # a questao e ver se estas coisas ficam no main ou aq, eu acho que o main devia ser este
        # logic for the setup phase, ver os jogadores e assim, pode ser preciso
        for player in self.players:
            await player.setup() # se for preciso comecar a 0
        self.current_phase = "action"

    # Cyclic phase behaviour
    # in order: player order, auction, resources, build houses, produce electricity

    async def phase1(self):
        for player in self.players:
            action = await player.decide_action(self.map)  # Assume Player has a decide_action method
            await self.execute_action(player, action)
        self.current_phase = "phase2"

    async def phase2(self):
        for player in self.players:
            pass
        self.current_phase = "phase3"

    async def phase3(self):
        for player in self.players:
            # action = await player.decide_action(self.map)  # Assume Player has a decide_action method
            # await self.execute_action(player, action)
            self.current_phase = "phase4"

    async def phase4(self):
        for player in self.players:
            # action = await player.decide_action(self.map)  # Assume Player has a decide_action method
            # await self.execute_action(player, action)
            self.current_phase = "phase5"

    async def phase5(self):
        for player in self.players:
            # action = await player.decide_action(self.map)  # Assume Player has a decide_action method
            # await self.execute_action(player, action)
            self.current_phase = "phase1"

    # Phases are cyclic, steps aren't!

    '''
    async def resolve_player_actions(self, player):
        # Update player state based on actions taken
        await self.update_player_resources(player)

    def is_build_action_valid(self, action):
        # Logic to validate build action
        return True  # Placeholder

    async def apply_build_action(self, action):
        # Logic to apply the build action
        pass  # Placeholder

    async def process_trade(self, action):
        # Logic for processing trades
        pass  # Placeholder

    async def update_player_resources(self, player):
        # Logic to update resources for the player
        pass  # Placeholder
    '''

# as funcoes de baixo o chat disse q podiam ser uteis, a ver vamos
# acho que a planificacao deste manager devia ser algo assim