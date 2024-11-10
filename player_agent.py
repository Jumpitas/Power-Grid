# player_agent.py

import asyncio
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import json

class ReceivePhaseBehaviour(CyclicBehaviour):
    async def run(self):
        msg = await self.receive(timeout=10)
        if msg:
            sender = str(msg.sender).split('/')[0]

            # Parse the JSON content of the message
            data = json.loads(msg.body)
            phase = data.get("phase")
            action = data.get("action")

            if phase == "setup":
                # Handle setup phase
                player_order = data.get("player_order")
                print(f"Player {self.agent.player_id} received setup information. Position: {player_order}")
                # Store player order if needed

            elif phase == "phase1":
                # Handle player order notification
                player_order = data.get("player_order")
                print(f"Player {self.agent.player_id} is in position {player_order}")
                # Store player order if needed

            elif phase == "phase2":
                if action == "choose_or_pass":
                    # Receive the power plant market
                    power_plant_market = data.get("power_plants")
                    self.agent.power_plant_market = power_plant_market
                    # Decide whether to choose a power plant or pass
                    chosen_plant_number = self.choose_power_plant(power_plant_market)
                    choice_msg = Message(to=sender)
                    choice_data = {
                        "action": "choose",
                        "power_plant_number": chosen_plant_number
                    }
                    choice_msg.body = json.dumps(choice_data)
                    await self.send(choice_msg)
                    print(f"Player {self.agent.player_id} chooses to auction power plant {chosen_plant_number}.")

                elif action == "bid":
                    # Receive bid request
                    current_bid = data.get("current_bid")
                    power_plant = data.get("power_plant")
                    # Decide whether to bid or pass
                    # For now, we'll pass
                    bid_msg = Message(to=sender)
                    bid_data = {
                        "bid": 0  # Zero or less indicates pass
                    }
                    bid_msg.body = json.dumps(bid_data)
                    await self.send(bid_msg)
                    print(f"Player {self.agent.player_id} decides to pass on bidding.")

                elif action == "auction_result":
                    # Handle auction result
                    winner = data.get("winner")
                    power_plant = data.get("power_plant")
                    bid = data.get("bid")
                    if winner == self.agent.jid:
                        # Add the power plant to player's state
                        self.agent.power_plants.append(power_plant)
                        print(f"Player {self.agent.player_id} won the auction for power plant {power_plant['min_bid']} with bid {bid}.")
                    else:
                        print(f"Player {self.agent.player_id} observed that player {winner} won the auction for power plant {power_plant['min_bid']} with bid {bid}.")

            elif phase == "phase3":
                if action == "buy_resources":
                    # Receive resource market information
                    resource_market = data.get("resource_market")
                    # Decide which resources to buy
                    # For now, we'll buy nothing
                    purchase_msg = Message(to=sender)
                    purchase_data = {
                        "purchases": {}  # Empty dict indicates buying nothing
                    }
                    purchase_msg.body = json.dumps(purchase_data)
                    await self.send(purchase_msg)
                    print(f"Player {self.agent.player_id} decides not to buy any resources.")

                elif action == "purchase_result":
                    # Handle purchase result
                    purchases = data.get("purchases")
                    total_cost = data.get("total_cost")
                    # Update player's resources
                    for resource, amount in purchases.items():
                        self.agent.resources[resource] += amount
                    print(f"Player {self.agent.player_id} purchased resources: {purchases} for total cost {total_cost}.")

            elif phase == "phase4":
                if action == "build_houses":
                    # Receive map status and current step
                    map_status = data.get("map_status")
                    current_step = data.get("step")
                    self.agent.step = current_step
                    # Decide where to build
                    # For now, we'll build nothing
                    build_msg = Message(to=sender)
                    build_data = {
                        "cities": []  # Empty list indicates building nowhere
                    }
                    build_msg.body = json.dumps(build_data)
                    await self.send(build_msg)
                    print(f"Player {self.agent.player_id} decides not to build any houses.")

                elif action == "build_result":
                    # Handle build result
                    cities = data.get("cities")
                    total_cost = data.get("total_cost")
                    # Update player's cities
                    self.agent.houses.extend(cities)
                    print(f"Player {self.agent.player_id} built houses in cities: {cities} for total cost {total_cost}.")

            elif phase == "game_over":
                # Handle game over
                winner = data.get("winner")
                final_elektro = data.get("final_elektro")
                if winner == self.agent.jid:
                    print(f"Player {self.agent.player_id} has won the game with {final_elektro} Elektro!")
                else:
                    print(f"Player {self.agent.player_id} has lost. Winner: {winner} with {final_elektro} Elektro.")
                await self.agent.stop()

            else:
                print(f"Player {self.agent.player_id} received an unknown message: {msg.body}")
        else:
            print(f"Player {self.agent.player_id} did not receive any message.")
        await asyncio.sleep(1)  # Yield control to event loop

    # Placeholder methods for decision-making
    def choose_power_plant(self, market):
        # Simple logic to choose the cheapest power plant
        cheapest_plant = min(market, key=lambda pp: pp['min_bid'])
        return cheapest_plant['min_bid']

    def decide_bid_amount(self):
        pass

    def decide_resources_to_buy(self, resource_market):
        pass

    def decide_cities_to_build(self, map_status):
        pass

    def calculate_powered_cities(self):
        pass

    def consume_resources(self, num_cities_powered):
        pass

    def get_power_capacity(self, plant_number):
        pass

class PowerGridPlayerAgent(Agent):
    def __init__(self, jid, password, player_id):
        super().__init__(jid, password)
        self.player_id = player_id
        self.houses = []  # List of city tags where the player has houses
        self.power_plants = []  # List of power plant dictionaries
        self.resources = {"coal": 0, "oil": 0, "garbage": 0, "uranium": 0}
        self.elektro = 50  # Starting money
        self.connected_cities = 0
        self.power_plant_market = []  # Latest power plant market info
        self.step = 1  # Current game step

    async def setup(self):
        print(f"Player {self.player_id} agent starting...")
        receive_phase_behaviour = ReceivePhaseBehaviour()
        self.add_behaviour(receive_phase_behaviour)
