# player_agent.py

import asyncio
import random
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import json

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
                    # Additional setup logic if needed

                elif phase == "phase1":
                    # Handle player order notification
                    player_order = data.get("player_order")
                    print(f"Player {self.agent.player_id} is in position {player_order}")

                elif phase == "phase2":
                    if action == "choose_power_plant":
                        # Receive the power plant market
                        power_plant_market = data.get("power_plants", [])
                        self.agent.power_plant_market = power_plant_market
                        # Decide which power plant to start an auction with
                        chosen_plant_number = self.choose_power_plant(power_plant_market)
                        choice_msg = Message(to=sender)
                        choice_data = {
                            "power_plant_number": chosen_plant_number
                        }
                        choice_msg.body = json.dumps(choice_data)
                        await self.send(choice_msg)
                        print(f"Player {self.agent.player_id} chooses to auction power plant {chosen_plant_number}.")

                    elif action == "initial_bid":
                        # Handle initial bid from starting player
                        base_min_bid = data.get("base_min_bid")
                        power_plant = data.get("power_plant")
                        bid_amount = self.decide_initial_bid(base_min_bid, power_plant)
                        bid_msg = Message(to=sender)
                        bid_data = {
                            "bid": bid_amount
                        }
                        bid_msg.body = json.dumps(bid_data)
                        await self.send(bid_msg)
                        print(f"Player {self.agent.player_id} places initial bid of {bid_amount} on power plant {power_plant.get('min_bid', 'unknown')}.")

                    elif action == "bid":
                        # Receive bid request
                        current_bid = data.get("current_bid", 0)
                        power_plant = data.get("power_plant", {})
                        # Decide whether to bid or pass
                        bid_amount = self.decide_bid_amount(current_bid, power_plant)
                        bid_msg = Message(to=sender)
                        bid_data = {
                            "bid": bid_amount
                        }
                        bid_msg.body = json.dumps(bid_data)
                        await self.send(bid_msg)
                        if bid_amount > current_bid:
                            print(f"Player {self.agent.player_id} bids {bid_amount} for power plant {power_plant.get('min_bid', 'unknown')}.")
                        else:
                            print(f"Player {self.agent.player_id} passes on bidding.")

                    elif action == "discard_power_plant":
                        # Player has more than 3 power plants and must discard one
                        power_plants = data.get("power_plants", [])
                        discard_number = self.choose_power_plant_to_discard(power_plants)
                        discard_msg = Message(to=sender)
                        discard_data = {
                            "discard_number": discard_number
                        }
                        discard_msg.body = json.dumps(discard_data)
                        await self.send(discard_msg)
                        print(f"Player {self.agent.player_id} discards power plant {discard_number}.")

                    elif action == "auction_result":
                        # Handle auction result
                        winner = data.get("winner")
                        power_plant = data.get("power_plant", {})
                        bid = data.get("bid", 0)
                        if winner == self.agent.jid:
                            # Add the power plant to the player's state
                            self.agent.power_plants.append(power_plant)
                            self.agent.elektro -= bid  # Deduct the bid amount
                            print(f"Player {self.agent.player_id} won the auction for power plant {power_plant.get('min_bid', '')} with bid {bid}.")
                        else:
                            print(f"Player {self.agent.player_id} observed that player {winner} won the auction for power plant {power_plant.get('min_bid', '')} with bid {bid}.")

                elif phase == "phase3":
                    if action == "buy_resources":
                        # Receive resource market information
                        resource_market = data.get("resource_market", {})
                        # Decide which resources to buy
                        purchases = self.decide_resources_to_buy(resource_market)
                        purchase_msg = Message(to=sender)
                        purchase_data = {
                            "purchases": purchases  # Dict of resources to buy
                        }
                        purchase_msg.body = json.dumps(purchase_data)
                        await self.send(purchase_msg)
                        print(f"Player {self.agent.player_id} decides to buy resources: {purchases}.")

                    elif action == "purchase_result":
                        # Handle purchase result
                        purchases = data.get("purchases", {})
                        total_cost = data.get("total_cost", 0)
                        # Update player's resources and elektro
                        for resource, amount in purchases.items():
                            self.agent.resources[resource] += amount
                        self.agent.elektro -= total_cost
                        print(f"Player {self.agent.player_id} purchased resources: {purchases} for total cost {total_cost}.")

                elif phase == "phase4":
                    if action == "build_houses":
                        # Receive map status and current step
                        map_status = data.get("map_status", {})
                        current_step = data.get("step", 1)
                        self.agent.step = current_step
                        # Decide where to build
                        cities_to_build = self.decide_cities_to_build(map_status)
                        build_msg = Message(to=sender)
                        build_data = {
                            "cities": cities_to_build
                        }
                        build_msg.body = json.dumps(build_data)
                        await self.send(build_msg)
                        print(f"Player {self.agent.player_id} decides to build in cities: {cities_to_build}.")

                    elif action == "build_result":
                        # Handle build result
                        cities = data.get("cities", [])
                        total_cost = data.get("total_cost", 0)
                        # Update player's cities
                        self.agent.houses.extend(cities)
                        self.agent.elektro -= total_cost
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

        # Decision-making methods
        def choose_power_plant(self, market):
            # Simple logic to choose the cheapest power plant
            if not market:
                print(f"Player {self.agent.player_id} finds no available power plants.")
                return None
            cheapest_plant = min(market, key=lambda pp: pp.get('min_bid', float('inf')))
            if cheapest_plant:
                return cheapest_plant.get('min_bid', None)
            return None

        def decide_initial_bid(self, base_min_bid, power_plant):
            # Decide the initial bid
            # For simplicity, always bid the base minimum if the player can afford it
            if self.agent.elektro >= base_min_bid:
                return base_min_bid
            else:
                return 0  # Can't afford even the base minimum

        def decide_bid_amount(self, current_bid, power_plant):
            # Decide whether to bid higher
            max_affordable_bid = self.agent.elektro
            if current_bid + 1 <= max_affordable_bid:
                # For simplicity, bid one more than the current bid
                return current_bid + 1
            else:
                # Can't afford to bid higher; pass
                return 0

        def choose_power_plant_to_discard(self, power_plants):
            # Decide which power plant to discard when over the limit
            # Simple strategy: discard the plant with the smallest min_bid
            if not power_plants:
                return None
            plant_to_discard = min(power_plants, key=lambda pp: pp.get('min_bid', float('inf')))
            return plant_to_discard.get('min_bid', None)

        def decide_resources_to_buy(self, resource_market):
            # Simple logic: buy resources needed for one round of operation
            purchases = {}
            for plant in self.agent.power_plants:
                resource_types = plant.get('resource_type', [])
                resource_needed = plant.get('resource_num', 0)
                if not resource_types or resource_needed == 0:
                    continue  # Eco-friendly plant, no resources needed
                if plant.get('is_hybrid', False):
                    # Hybrid plant: buy resources in any combination
                    for rtype in resource_types:
                        available = resource_market.get(rtype, 0)
                        if available > 0 and self.agent.elektro > 0:
                            # Buy as much as possible up to resource_needed
                            amount_to_buy = min(available, resource_needed)
                            purchases[rtype] = purchases.get(rtype, 0) + amount_to_buy
                            resource_needed -= amount_to_buy
                            self.agent.elektro -= amount_to_buy * 1  # Simplified cost
                            if resource_needed <= 0:
                                break
                else:
                    # Non-hybrid plant: buy required resources
                    rtype = resource_types[0]
                    available = resource_market.get(rtype, 0)
                    if available > 0 and self.agent.elektro > 0:
                        amount_to_buy = min(available, resource_needed)
                        purchases[rtype] = purchases.get(rtype, 0) + amount_to_buy
                        self.agent.elektro -= amount_to_buy * 1  # Simplified cost
                # Note: This is a simplified example; you should adjust prices and logic as per game rules
            return purchases

        def decide_cities_to_build(self, map_status):
            # Simple logic: attempt to build in the first city that is not yet owned by this agent
            for city, data in map_status.items():
                if city not in self.agent.houses:
                    # Assume we can afford it for now and city is within step occupancy
                    return [city]
            return []

    async def setup(self):
        print(f"Player {self.player_id} agent starting...")
        receive_phase_behaviour = self.ReceivePhaseBehaviour()
        self.add_behaviour(receive_phase_behaviour)
