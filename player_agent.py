# player_agent.py

import asyncio
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import random
import json

class ReceivePhaseBehaviour(CyclicBehaviour):
    async def run(self):
        msg = await self.receive(timeout=10)
        if msg:
            sender = str(msg.sender).split('/')[0]
            if msg.body == "REQUEST_CITIES":
                # Send the number of connected cities back to the Game Manager
                response = Message(to=sender)
                response.body = f"CITIES:{len(self.agent.houses)}"
                await self.send(response)
            elif msg.body == "REQUEST_POWER":
                # Calculate how many cities the player can power
                num_powered_cities = self.calculate_powered_cities()
                # Remove used resources
                self.consume_resources(num_powered_cities)
                # Send response to Game Manager
                response = Message(to=sender)
                response.body = f"POWERED_CITIES:{num_powered_cities}"
                await self.send(response)
            elif msg.body.startswith("EARNINGS:"):
                # Update player's money
                income = int(msg.body.split(":")[1])
                self.agent.elektro += income
                print(f"Player {self.agent.player_id} received income: {income}. Total Elektro: {self.agent.elektro}")
            elif msg.body.startswith("PHASE_1"):
                # Handle player order notification
                player_order = msg.get_metadata("player_order")
                print(f"Player {self.agent.player_id} is in position {player_order}")
            elif msg.body.startswith("PHASE_2:"):
                # Receive the power plant market
                power_plant_market = json.loads(msg.body.split(":", 1)[1])
                self.agent.power_plant_market = power_plant_market
                # Decide which power plant to auction
                chosen_plant = self.choose_power_plant(power_plant_market)
                if chosen_plant is not None:
                    # Send choice to Game Manager
                    choice_msg = Message(to="gamemanager@localhost")
                    choice_msg.body = f"AUCTION:{chosen_plant}"
                    await self.send(choice_msg)
            elif msg.body == "CHOOSE_PLANT":
                # Decide which power plant to auction
                chosen_plant = self.choose_power_plant(self.agent.power_plant_market)
                if chosen_plant is not None:
                    # Send choice to Game Manager
                    choice_msg = Message(to="gamemanager@localhost")
                    choice_msg.body = f"AUCTION:{chosen_plant}"
                    await self.send(choice_msg)
            elif msg.body == "BID_REQUEST":
                # Decide on a bid amount
                bid_amount = self.decide_bid_amount()
                bid_msg = Message(to="gamemanager@localhost")
                bid_msg.body = f"BID:{bid_amount}"
                await self.send(bid_msg)
                print(f"Player {self.agent.player_id} sent bid: {bid_amount}")
            elif msg.body.startswith("PHASE_3:"):
                resource_market = json.loads(msg.body.split(":", 1)[1])
                # Decide which resources to buy
                resources_to_buy = self.decide_resources_to_buy(resource_market)
                # Send purchase to Game Manager
                purchase_msg = Message(to="gamemanager@localhost")
                purchase_msg.body = f"BUY_RESOURCES:{json.dumps(resources_to_buy)}"
                await self.send(purchase_msg)
                print(f"Player {self.agent.player_id} is buying resources: {resources_to_buy}")
            elif msg.body.startswith("PHASE_4:"):
                map_status = json.loads(msg.body.split(":", 1)[1])
                current_step = int(msg.get_metadata("step"))
                self.agent.step = current_step
                # Decide where to build
                cities_to_build = self.decide_cities_to_build(map_status)
                # Send building action to Game Manager
                build_msg = Message(to="gamemanager@localhost")
                build_msg.body = f"BUILD_HOUSES:{json.dumps(cities_to_build)}"
                await self.send(build_msg)
                print(f"Player {self.agent.player_id} is building houses in: {cities_to_build}")
            elif msg.body.startswith("AUCTION_WIN:"):
                # Handle auction win
                parts = msg.body.split(":")
                if len(parts) >= 3:
                    plant_number = int(parts[1])
                    bid_amount = int(parts[2])
                    # Add the power plant to player's state
                    self.agent.power_plants.append(plant_number)
                    print(f"Player {self.agent.player_id} won auction for plant {plant_number} with bid {bid_amount}")
                else:
                    print(f"Player {self.agent.player_id} received malformed AUCTION_WIN message: {msg.body}")
            elif msg.body.startswith("PURCHASE_CONFIRMED:"):
                # Handle purchase confirmation
                parts = msg.body.split(":")
                if len(parts) >= 3:
                    resource_type = parts[1]
                    amount = int(parts[2])
                    self.agent.resources[resource_type] += amount
                    print(f"Player {self.agent.player_id} successfully purchased {amount} {resource_type}")
                else:
                    print(f"Player {self.agent.player_id} received malformed PURCHASE_CONFIRMED message: {msg.body}")
            elif msg.body.startswith("PURCHASE_FAILED:"):
                # Handle purchase failure
                parts = msg.body.split(":")
                if len(parts) >= 3:
                    resource_type = parts[1]
                    reason = parts[2]
                    print(f"Player {self.agent.player_id} failed to purchase {resource_type}: {reason}")
                else:
                    print(f"Player {self.agent.player_id} received malformed PURCHASE_FAILED message: {msg.body}")
            elif msg.body.startswith("BUILD_CONFIRMED:"):
                # Handle build confirmation
                parts = msg.body.split(":")
                if len(parts) >= 2:
                    city = parts[1]
                    self.agent.houses.append(city)
                    print(f"Player {self.agent.player_id} successfully built in {city}")
                else:
                    print(f"Player {self.agent.player_id} received malformed BUILD_CONFIRMED message: {msg.body}")
            elif msg.body.startswith("BUILD_FAILED:"):
                # Handle build failure
                parts = msg.body.split(":")
                if len(parts) >= 3:
                    city = parts[1]
                    reason = parts[2]
                    print(f"Player {self.agent.player_id} failed to build in {city}: {reason}")
                else:
                    print(f"Player {self.agent.player_id} received malformed BUILD_FAILED message: {msg.body}")
            elif msg.body == "GAME_END":
                winner = msg.get_metadata("winner")
                if winner == self.agent.jid:
                    print(f"Player {self.agent.player_id} has won the game!")
                else:
                    print(f"Player {self.agent.player_id} has lost. Winner: {winner}")
                await self.agent.stop()
            else:
                print(f"Player {self.agent.player_id} received an unknown message: {msg.body}")
        else:
            print(f"Player {self.agent.player_id} did not receive any phase message.")
        await asyncio.sleep(1)  # Yield control to event loop

    def choose_power_plant(self, market):
        pass

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
        self.power_plants = []  # List of power plant numbers
        self.resources = {"coal": 0, "oil": 0, "garbage": 0, "uranium": 0}
        self.elektro = 50  # Starting money
        self.connected_cities = 0
        self.power_plant_market = []  # Latest power plant market info
        self.step = 1  # Current game step

    async def setup(self):
        print(f"Player {self.player_id} agent starting...")
        receive_phase_behaviour = ReceivePhaseBehaviour()
        self.add_behaviour(receive_phase_behaviour)
