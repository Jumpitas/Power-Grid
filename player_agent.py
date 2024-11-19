# player_agent.py

import asyncio
import random
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import json
from objects import PowerPlant
from game_environment import Environment

# Only for testing!
from objects import power_plant_socket
import globals


class PowerGridPlayerAgent(Agent):
    def __init__(self, jid, password, player_id):
        super().__init__(jid, password)
        self.player_id = player_id
        self.houses = 0  # Starting with 22 houses as per game rules
        self.elektro = 0  # Starting money
        self.cities_owned = []  # List of city tags where the player has houses
        self.number_cities_owned = 0
        self.cities_powered = []  # List of city tags that the player can power
        self.power_plants = []  # List of power plant dictionaries
        self.resources = {}
        self.has_bought_power_plant = False
        self.position = None  # Will be set during setup
        # Removed: self.power_plant_market as it's not needed as an attribute
        self.step = 2  # Current game step
        self.connected_cities = 0  # Number of connected cities

        globals.environment_instance = Environment(None)
        self.get_inventory()

        '''
        # Initialize power plants for testing
        if self.player_id == 1:
            self.power_plants = [power_plant_socket[20]]
        else:
            self.power_plants = [power_plant_socket[10]]
        '''

    def get_inventory(self):
        """
        Updates the player's attributes with the current inventory from the global environment.
        """
        inventory = globals.environment_instance.players[self.player_id]
        self.houses = inventory['houses']
        self.elektro = inventory['elektro']
        self.cities_owned = inventory['cities_owned']
        self.number_cities_owned = inventory['number_cities_owned']
        self.cities_powered = inventory['cities_powered']
        self.power_plants = inventory['power_plants']
        self.resources = inventory['resources']
        self.has_bought_power_plant = inventory['has_bought_power_plant']
        self.position = inventory['position']
        self.connected_cities = inventory['connected_cities']

    def update_inventory(self):
        """
        Updates the global environment's inventory for this player
        based on the current attributes.
        """
        globals.environment_instance.players[self.player_id] = {
            'houses': self.houses,
            'elektro': self.elektro,
            'cities_owned': self.cities_owned,
            'number_cities_owned': self.number_cities_owned,
            'cities_powered': self.cities_powered,
            'power_plants': self.power_plants,
            'resources': self.resources,
            'has_bought_power_plant': self.has_bought_power_plant,
            'position': self.position,
            'connected_cities': self.connected_cities
        }

    class ReceivePhaseBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=30)
            if msg:
                sender = str(msg.sender).split('/')[0]

                # Parse the JSON content of the message
                try:
                    data = json.loads(msg.body)
                except json.JSONDecodeError:
                    print(f"Player {self.agent.player_id} received invalid JSON.")
                    return

                phase = data.get("phase")
                action = data.get("action")

                if phase == "setup":
                    # Handle setup phase
                    player_order = data.get("player_order")
                    self.agent.position = player_order
                    print(f"Player {self.agent.player_id} received setup information. Position: {player_order}")
                    # Additional setup logic if needed

                elif phase == "phase1":
                    # Handle player order notification
                    player_order = data.get("player_order")
                    self.agent.position = player_order
                    print(f"Player {self.agent.player_id} is in position {player_order}")

                elif phase == "phase2":
                    if action == "choose_or_pass":
                        # Decide whether to start an auction or pass
                        power_plant_market_data = data.get("power_plants", [])
                        power_plant_market = [PowerPlant.from_dict(pp) for pp in power_plant_market_data]
                        can_pass = data.get("can_pass", True)
                        if can_pass:
                            # Decide to pass or choose a power plant
                            if self.should_pass(power_plant_market):
                                choice_msg = Message(to=sender)
                                choice_data = {
                                    "choice": "pass"
                                }
                                choice_msg.body = json.dumps(choice_data)
                                await self.send(choice_msg)
                                print(f"Player {self.agent.player_id} decides to pass on starting an auction.")
                            else:
                                chosen_plant_number = self.choose_power_plant_to_auction(power_plant_market)
                                if chosen_plant_number is not None:
                                    choice_msg = Message(to=sender)
                                    choice_data = {
                                        "choice": "auction",
                                        "power_plant_number": chosen_plant_number
                                    }
                                    choice_msg.body = json.dumps(choice_data)
                                    await self.send(choice_msg)
                                    print(
                                        f"Player {self.agent.player_id} chooses to auction power plant {chosen_plant_number}.")
                                else:
                                    # Cannot afford any power plant, so pass
                                    choice_msg = Message(to=sender)
                                    choice_data = {
                                        "choice": "pass"
                                    }
                                    choice_msg.body = json.dumps(choice_data)
                                    await self.send(choice_msg)
                                    print(f"Player {self.agent.player_id} cannot afford any power plant and passes.")
                        else:
                            # Must choose a power plant (first round)
                            chosen_plant_number = self.choose_power_plant_to_auction(power_plant_market)
                            choice_msg = Message(to=sender)
                            choice_data = {
                                "choice": "auction",
                                "power_plant_number": chosen_plant_number
                            }
                            choice_msg.body = json.dumps(choice_data)
                            await self.send(choice_msg)
                            print(
                                f"Player {self.agent.player_id} must auction power plant {chosen_plant_number} (first round).")

                    elif action == "initial_bid":
                        # Handle initial bid from starting player
                        base_min_bid = data.get("base_min_bid")
                        power_plant_data = data.get("power_plant")
                        power_plant = PowerPlant.from_dict(power_plant_data) if power_plant_data else None
                        bid_amount = self.decide_initial_bid(base_min_bid, power_plant)
                        bid_msg = Message(to=sender)
                        bid_data = {
                            "bid": bid_amount
                        }
                        bid_msg.body = json.dumps(bid_data)
                        await self.send(bid_msg)
                        print(
                            f"Player {self.agent.player_id} places initial bid of {bid_amount} on power plant {power_plant.min_bid if power_plant else 'unknown'}.")

                    elif action == "bid":
                        # Receive bid request
                        current_bid = data.get("current_bid", 0)
                        power_plant_data = data.get("power_plant", {})
                        power_plant = PowerPlant.from_dict(power_plant_data) if power_plant_data else None
                        # Decide whether to bid or pass
                        bid_amount = self.decide_bid_amount(current_bid, power_plant)
                        bid_msg = Message(to=sender)
                        bid_data = {
                            "bid": bid_amount
                        }
                        bid_msg.body = json.dumps(bid_data)
                        await self.send(bid_msg)
                        if bid_amount > current_bid:
                            print(
                                f"Player {self.agent.player_id} bids {bid_amount} for power plant {power_plant.min_bid if power_plant else 'unknown'}.")
                        else:
                            print(f"Player {self.agent.player_id} passes on bidding.")

                    elif action == "discard_power_plant":
                        # Player has more than 3 power plants and must discard one
                        power_plants_data = data.get("power_plants", [])
                        power_plants = [PowerPlant.from_dict(pp) for pp in power_plants_data]
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
                        power_plant_data = data.get("power_plant", {})
                        power_plant = PowerPlant.from_dict(power_plant_data) if power_plant_data else None
                        bid = data.get("bid", 0)
                        if winner == self.agent.jid:
                            # Add the power plant to the player's state
                            if power_plant:
                                self.agent.power_plants.append(power_plant)
                                self.agent.elektro -= bid  # Deduct the bid amount
                                print(
                                    f"Player {self.agent.player_id} won the auction for power plant {power_plant.min_bid} with bid {bid}.")
                        else:
                            print(
                                f"Player {self.agent.player_id} observed that player {winner} won the auction for power plant {power_plant.min_bid if power_plant else 'unknown'} with bid {bid}.")

                elif phase == "phase3":
                    if action == "buy_resources":
                        # Receive resource market information
                        resource_market = data.get("resource_market")
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
                            self.agent.resources[resource] = self.agent.resources.get(resource, 0) + amount
                        self.agent.elektro -= total_cost
                        print(
                            f"Player {self.agent.player_id} purchased resources: {purchases} for total cost {total_cost}.")

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
                        self.agent.cities_owned.extend(cities)
                        self.agent.elektro -= total_cost
                        print(
                            f"Player {self.agent.player_id} built houses in cities: {cities} for total cost {total_cost}.")

                elif phase == "phase5":
                    # Phase 5 (Bureaucracy)
                    print(f"Player {self.agent.player_id} acknowledges Phase 5 - Bureaucracy.")

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
        def should_pass(self, power_plant_market):
            """
            Decide whether to pass based on the current power plant market.
            """
            need_power_plant = len(self.agent.power_plants) < 3
            can_afford_any = any(
                pp.min_bid <= self.agent.elektro for pp in power_plant_market
            )
            return not need_power_plant or not can_afford_any

        def choose_power_plant_to_auction(self, market):
            """
            Choose the best affordable power plant to auction based on strategic evaluation.
            """
            if not market:
                print(f"Player {self.agent.player_id} finds no available power plants to auction.")
                return None

            # Evaluate power plants assuming 'market' contains PowerPlant objects
            affordable_plants = [pp for pp in market if pp.min_bid <= self.agent.elektro]
            if not affordable_plants:
                print(f"Player {self.agent.player_id} cannot afford any power plant.")
                return None

            # Strategy: pick the plant that provides the best ratio of cities powered per Elektro
            def plant_value(pp):
                return pp.cities / pp.min_bid if pp.min_bid > 0 else 0

            best_plant = max(affordable_plants, key=plant_value)
            return best_plant.min_bid if hasattr(best_plant, 'min_bid') else None

            # Strategy: pick the plant that provides the best ratio of cities powered per Elektro
            def plant_value(pp):
                return pp.get('cities', 0) / pp.get('min_bid', 1)

            best_plant = max(affordable_plants, key=plant_value)
            return best_plant.get('min_bid', None)

        def decide_initial_bid(self, base_min_bid, power_plant):
            # Decide the initial bid based on the value of the power plant
            plant_value = self.evaluate_power_plant(power_plant)
            # For simplicity, bid up to a certain percentage of our Elektro if the plant is valuable
            max_bid = int(self.agent.elektro * 0.6)
            bid = min(max_bid, base_min_bid)
            return bid if bid >= base_min_bid else 0

        def decide_bid_amount(self, current_bid, power_plant):
            # Decide whether to bid higher based on the plant's value and our Elektro
            plant_value = self.evaluate_power_plant(power_plant)
            max_affordable_bid = self.agent.elektro
            # Willing to bid up to the plant's evaluated value or our max affordable bid
            if current_bid < plant_value and current_bid + 1 <= max_affordable_bid:
                return current_bid + 1
            else:
                # Can't afford to bid higher or the plant isn't worth it
                return 0

        def evaluate_power_plant(self, power_plant):
            """
            Evaluate the power plant's worth to the agent.
            """
            cities_powered = power_plant.cities
            resource_types = power_plant.resource_type
            is_eco = len(resource_types) == 0
            # Prefer eco-friendly plants
            value = cities_powered * 10
            if is_eco:
                value += 20
            return value

        def choose_power_plant_to_discard(self, power_plants):
            """
            Decide which power plant to discard when over the limit.
            Strategy: discard the plant with the lowest number of cities powered.
            """
            if not power_plants:
                return None

            # Uses simple function to evaluate plants based on min_bid value
            plant_to_discard = min(power_plants, key=lambda plant: plant.min_bid)
            return plant_to_discard.min_bid

        def decide_resources_to_buy(self, resource_market):
            """
            Decide which resources to buy based on the power plants owned.
            """
            purchases = {"coal": 0, "oil": 0, "garbage": 0, "uranium": 0}
            for plant in self.agent.power_plants:
                print("\n\nPlant being checked: ", plant)

                # Access attributes directly
                resource_types = plant.resource_type
                resource_needed = plant.resource_num
                is_hybrid = plant.is_hybrid

                if not resource_types or resource_needed == 0:
                    continue  # Eco-friendly plant or no resources needed

                if is_hybrid:
                    # Hybrid plant: buy resources in any combination
                    for rtype in resource_types:
                        available = resource_market.get(rtype, 0)
                        if available > 0 and self.agent.elektro > 0:
                            # Purchase as much as possible (up to resource_needed)
                            amount_to_buy = min(available, resource_needed)
                            purchases[rtype] += amount_to_buy
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
                        purchases[rtype] += amount_to_buy
                        resource_needed -= amount_to_buy
                        self.agent.elektro -= amount_to_buy * 1  # Simplified cost
            return purchases

        def decide_cities_to_build(self, map_status):
            # Simple logic: attempt to build in the first city that is not yet owned by this agent
            for city, data in map_status.items():
                if city not in self.agent.cities_owned:
                    # Assume we can afford it for now and city is within step occupancy
                    return [city]
            return []

    async def setup(self):
        print(f"Player {self.player_id} agent starting...")
        receive_phase_behaviour = PowerGridPlayerAgent.ReceivePhaseBehaviour()
        self.add_behaviour(receive_phase_behaviour)
#