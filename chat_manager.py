import asyncio
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import random
import json

class GameManagerAgent(Agent):
    class GameManagerBehaviour(CyclicBehaviour):
        def __init__(self, players):
            super().__init__()
            self.players = players  # List of player JIDs (addresses)
            self.current_phase = "setup"
            self.round = 1
            self.actions_received = 0  # Count of received actions
            self.map = self.get_map()

        def get_map(self):
            # Just return a dummy map for now
            return {"regions": 5, "resources": {"coal": 10, "oil": 8}}

        async def run(self):
            print(f"GameManager: Current phase is {self.current_phase}")
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

            await asyncio.sleep(1)  # Wait between phases

        async def setup_phase(self):
            print("GameManager: Starting setup phase.")
            # Notify all players that the game has started and we're in the setup phase
            for player in self.players:
                await self.send_phase_update(player, "setup")

            self.current_phase = "phase1"  # Move to phase1 after setup

        async def phase1(self):
            print("GameManager: Starting phase 1.")
            self.actions_received = 0
            for player in self.players:
                await self.send_phase_update(player, "phase1")

        async def phase2(self):
            print("GameManager: Starting phase 2.")
            self.actions_received = 0
            for player in self.players:
                await self.send_phase_update(player, "phase2")

        async def phase3(self):
            print("GameManager: Starting phase 3.")
            self.actions_received = 0
            for player in self.players:
                await self.send_phase_update(player, "phase3")

        async def phase4(self):
            print("GameManager: Starting phase 4.")
            self.actions_received = 0
            for player in self.players:
                await self.send_phase_update(player, "phase4")

        async def phase5(self):
            print("GameManager: Starting phase 5.")
            self.actions_received = 0
            for player in self.players:
                await self.send_phase_update(player, "phase5")

        async def send_phase_update(self, player_jid, phase):
            # Send phase update to the player
            msg = Message(to=player_jid)
            msg.set_metadata("performative", "inform")
            msg.body = json.dumps({"phase": phase, "map": self.map})
            await self.send(msg)
            print(f"GameManager: Sent phase {phase} update to {player_jid}")

        async def on_message(self, msg):
            # Handle actions received from players
            print(f"GameManager: Received message from {msg.sender}")
            content = json.loads(msg.body)
            print(f"GameManager: Player {msg.sender} did {content['action']} in {self.current_phase}")

            self.actions_received += 1

            # If all players have taken their action, move to the next phase
            if self.actions_received == len(self.players):
                print(f"GameManager: All players completed actions for {self.current_phase}")
                self.advance_phase()

        def advance_phase(self):
            # Cycle through phases
            if self.current_phase == "phase5":
                self.current_phase = "phase1"
                self.round += 1
                print(f"GameManager: Round {self.round} begins, back to phase 1.")
            else:
                next_phase = int(self.current_phase[-1]) + 1
                self.current_phase = f"phase{next_phase}"
            print(f"GameManager: Transitioned to {self.current_phase}")

    async def setup(self):
        players = ["player1@localhost", "player2@localhost"]  # Example JIDs for players
        game_behaviour = self.GameManagerBehaviour(players)
        self.add_behaviour(game_behaviour)

class PlayerAgent(Agent):
    class PlayerBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=10)  # Wait for a message from GameManager
            if msg:
                content = json.loads(msg.body)
                phase = content["phase"]
                print(f"{self.agent.jid}: Received phase {phase}")

                # Decide an action based on the current phase
                if phase == "setup":
                    action = "ready"
                else:
                    action = random.choice(["build", "bid", "pass", "buy resources"])

                # Send action back to the GameManager
                response = Message(to="gamemanager@localhost")  # Replace with GameManager's JID
                response.set_metadata("performative", "inform")
                response.body = json.dumps({"action": action})

                await self.send(response)
                print(f"{self.agent.jid}: Sent action {action} for phase {phase}")

    async def setup(self):
        player_behaviour = self.PlayerBehaviour()
        self.add_behaviour(player_behaviour)

# Set up agents and start the system
if __name__ == "__main__":
    game_manager = GameManagerAgent("gamemanager@localhost", "password")
    player1 = PlayerAgent("player1@localhost", "password")
    player2 = PlayerAgent("player2@localhost", "password")

    game_manager.start()
    player1.start()
    player2.start()

    try:
        while True:
            asyncio.sleep(1)
    except KeyboardInterrupt:
        game_manager.stop()
        player1.stop()
        player2.stop()
