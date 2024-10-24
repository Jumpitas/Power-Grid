import asyncio
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import random
import json

class GameManagerAgent(Agent):
    class GameBehaviour(CyclicBehaviour):
        def __init__(self, game_manager):
            super().__init__()
            self.game_manager = game_manager
            self.players = []  # List of player JIDs
            self.current_phase = "setup"
            self.round = 1
            self.map = self.get_map()
            self.player_actions = {}  # Track player actions for the current phase

        def get_map(self):
            # You can define the map or board here.
            return {"example_map": "map_data"}  # Placeholder map representation

        async def run(self):
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
            await asyncio.sleep(1)

        async def setup_phase(self):
            print("Game Manager is setting up the game.")
            # For simplicity, assume we have two players
            self.players = ["player1@localhost", "player2@localhost"]

            # Notify all players about the setup phase completion
            for player in self.players:
                msg = Message(to=player)
                msg.body = json.dumps({"phase": "setup", "map": self.map})
                await self.send(msg)

            # Move to the first phase after setup
            self.current_phase = "phase1"
            print("Moving to Phase 1")

        async def phase1(self):
            print("Game Manager starting Phase 1: Player actions")
            self.player_actions = {}  # Reset actions for the new phase

            # Notify all players about phase1
            for player in self.players:
                msg = Message(to=player)
                msg.body = json.dumps({"phase": "phase1", "map": self.map})
                await self.send(msg)

            # Wait for all players to send their actions
            await self.wait_for_all_players()

            print(f"All actions received for Phase 1: {self.player_actions}")
            self.current_phase = "phase2"
            print("Moving to Phase 2")

        async def phase2(self):
            print("Game Manager starting Phase 2: Auction phase")
            self.player_actions = {}

            # Notify all players about phase2
            for player in self.players:
                msg = Message(to=player)
                msg.body = json.dumps({"phase": "phase2"})
                await self.send(msg)

            # Wait for all players to send their actions
            await self.wait_for_all_players()

            print(f"All actions received for Phase 2: {self.player_actions}")
            self.current_phase = "phase3"
            print("Moving to Phase 3")

        async def phase3(self):
            print("Game Manager starting Phase 3: Resource allocation")
            self.player_actions = {}

            # Notify all players about phase3
            for player in self.players:
                msg = Message(to=player)
                msg.body = json.dumps({"phase": "phase3"})
                await self.send(msg)

            # Wait for all players to send their actions
            await self.wait_for_all_players()

            print(f"All actions received for Phase 3: {self.player_actions}")
            self.current_phase = "phase4"
            print("Moving to Phase 4")

        async def phase4(self):
            print("Game Manager starting Phase 4: Trading phase")
            self.player_actions = {}

            # Notify all players about phase4
            for player in self.players:
                msg = Message(to=player)
                msg.body = json.dumps({"phase": "phase4"})
                await self.send(msg)

            # Wait for all players to send their actions
            await self.wait_for_all_players()

            print(f"All actions received for Phase 4: {self.player_actions}")
            self.current_phase = "phase5"
            print("Moving to Phase 5")

        async def phase5(self):
            print("Game Manager starting Phase 5: Endgame scoring")
            self.player_actions = {}

            # Notify all players about phase5
            for player in self.players:
                msg = Message(to=player)
                msg.body = json.dumps({"phase": "phase5"})
                await self.send(msg)

            # Wait for all players to send their actions
            await self.wait_for_all_players()

            print(f"All actions received for Phase 5: {self.player_actions}")
            print("Game over. Final scores calculated.")
            self.round += 1  # Increment round counter
            self.current_phase = "phase1"  # Start next round from phase 1
            print("Resetting for the next round, starting from Phase 1.")

        async def wait_for_all_players(self):
            """
            Wait until actions from all players are received before proceeding to the next phase.
            """
            while len(self.player_actions) < len(self.players):
                # Wait for responses from players
                msg = await self.receive(timeout=10)  # Wait for up to 10 seconds for a response
                if msg:
                    sender_jid = str(msg.sender)
                    action = json.loads(msg.body)  # Parse the player's action
                    self.player_actions[sender_jid] = action
                    print(f"Received action from {sender_jid}: {action}")

                await asyncio.sleep(1)  # Avoid busy-waiting

    async def setup(self):
        print("Game Manager agent starting...")
        game_behaviour = self.GameBehaviour(self)
        self.add_behaviour(game_behaviour)


class PlayerAgent(Agent):
    class PlayerBehaviour(CyclicBehaviour):
        def __init__(self, player_name):
            super().__init__()
            self.player_name = player_name

        async def run(self):
            # Wait for a message from the GameManagerAgent
            msg = await self.receive(timeout=5)  # Wait for 5 seconds for a message
            if msg:
                content = json.loads(msg.body)
                phase = content.get("phase")
                print(f"{self.player_name} received message for phase: {phase}")

                if phase == "setup":
                    await self.handle_setup(content)
                elif phase == "phase1":
                    await self.handle_phase1(content)
                elif phase == "phase2":
                    await self.handle_phase2(content)
                elif phase == "phase3":
                    await self.handle_phase3(content)
                elif phase == "phase4":
                    await self.handle_phase4(content)
                elif phase == "phase5":
                    await self.handle_phase5(content)

            await asyncio.sleep(1)

        async def handle_setup(self, content):
            # Setup logic for the player
            print(f"{self.player_name} setting up...")

        async def handle_phase1(self, content):
            # Phase 1 logic for the player
            print(f"{self.player_name} deciding action for phase 1...")
            action = {"action": "build", "location": random.choice(["A", "B", "C"])}
            response = Message(to="gamemanager@localhost")
            response.body = json.dumps(action)
            await self.send(response)
            print(f"{self.player_name} sent action: {action}")

        async def handle_phase2(self, content):
            # Phase 2 logic for the player
            print(f"{self.player_name} deciding action for phase 2 (auction)...")
            action = {"action": "bid", "amount": random.randint(10, 100)}
            response = Message(to="gamemanager@localhost")
            response.body = json.dumps(action)
            await self.send(response)
            print(f"{self.player_name} sent auction bid: {action}")

        async def handle_phase3(self, content):
            # Phase 3 logic for the player
            print(f"{self.player_name} deciding action for phase 3 (resource allocation)...")
            action = {"action": "allocate", "resources": random.randint(1, 5)}
            response = Message(to="gamemanager@localhost")
            response.body = json.dumps(action)
            await self.send(response)
            print(f"{self.player_name} sent resource allocation: {action}")

        async def handle_phase4(self, content):
            # Phase 4 logic for the player
            print(f"{self.player_name} deciding action for phase 4 (trading)...")
            action = {"action": "trade", "offer": random.randint(5, 20)}
            response = Message(to="gamemanager@localhost")
            response.body = json.dumps(action)
            await self.send(response)
            print(f"{self.player_name} sent trade offer: {action}")

        async def handle_phase5(self, content):
            # Phase 5 logic for the player
            print(f"{self.player_name} calculating final score...")
            action = {"action": "final_score", "score": random.randint(50, 150)}
            response = Message(to="gamemanager@localhost")
            response.body = json.dumps(action)
            await self.send(response)
            print(f"{self.player_name} phase 5 over, should now return to phase 1: {action}")

    async def setup(self):
        print(f"{self.jid} starting...")
        player_behaviour = self.PlayerBehaviour(self.jid)
        self.add_behaviour(player_behaviour)


async def main():
    # Create GameManagerAgent
    game_manager = GameManagerAgent("gamemanager@localhost", "password")

    # Create PlayerAgents
    player1 = PlayerAgent("player1@localhost", "password")
    player2 = PlayerAgent("player2@localhost", "password")

    # Start agents
    await game_manager.start()
    await player1.start()
    await player2.start()

    # Keep agents running for a while
    await asyncio.sleep(60)  # Adjust as necessary

    # Stop agents
    await game_manager.stop()
    await player1.stop()
    await player2.stop()


if __name__ == "__main__":
    asyncio.run(main())
