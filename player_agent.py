# player_agent.py
from time import sleep
import asyncio
import random
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import json
from objects import PowerPlant
from game_environment import Environment
from rule_tables import *

######################################################################

# methods to format strings at terminal outputs, don t need to be defined within the class
def clear_screen():
    print("\n" * 100)  # os.system ain t working :(

def split_parts():
    print("\n" + "-" * 30 + "\n")

def edit_order(player_list): # help to the formatting
    formatted_players = [f"player{player}" for player in player_list]

    # Join the players with " -> "
    result = " -> ".join(formatted_players)

    return result

######################################################################
import globals
import networkx as nx


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
        inventory = globals.environment_instance.players.get(self.player_id, {})
        self.houses = inventory.get('houses', 0)
        self.elektro = inventory.get('elektro', 0)
        self.cities_owned = inventory.get('cities_owned', [])
        self.number_cities_owned = inventory.get('number_cities_owned', 0)
        self.cities_powered = inventory.get('cities_powered', [])
        self.power_plants = inventory.get('power_plants', [])
        self.resources = inventory.get('resources', {})
        self.has_bought_power_plant = inventory.get('has_bought_power_plant', False)
        self.position = inventory.get('position', None)
        self.connected_cities = inventory.get('connected_cities', 0)

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


    def print_status(self, phase=-1, round_no=-1, turn=-1, order=[-1,-2,-3], subphase=None):
        print(f"The current phase is {phase} and sub phase is {subphase}")
        print(f"It's the player {turn}'s turn: ")
        print(f"Order for the round {round_no}: {edit_order(order)}")
        split_parts()
        globals.environment_instance.print_environment()
        sleep(3)

    class ReceivePhaseBehaviour(CyclicBehaviour):
        async def run(self):
            # Synchronize inventory at the start of each cycle
            self.agent.get_inventory()

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
                    self.agent.update_inventory()
                    print(f"Player {self.agent.player_id} received setup information. Position: {player_order}")
                    self.agent.print_status()

                elif phase == "phase1":
                    # Handle player order notification
                    player_order = data.get("player_order")
                    self.agent.position = player_order
                    self.agent.update_inventory()
                    print(f"Player {self.agent.player_id} is in position {player_order}")
                    self.agent.print_status()


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
                                self.agent.print_status()

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
                                    print(f"Player {self.agent.player_id} chooses to auction power plant {chosen_plant_number}.")
                                    self.agent.print_status()

                                else:
                                    # Cannot afford any power plant, so pass
                                    choice_msg = Message(to=sender)
                                    choice_data = {
                                        "choice": "pass"
                                    }
                                    choice_msg.body = json.dumps(choice_data)
                                    await self.send(choice_msg)
                                    print(f"Player {self.agent.player_id} cannot afford any power plant and passes.")
                                    self.agent.print_status()

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
                            print(f"Player {self.agent.player_id} must auction power plant {chosen_plant_number} (first round).")
                            self.agent.print_status()


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
                        print(f"Player {self.agent.player_id} places initial bid of {bid_amount} on power plant {power_plant.min_bid if power_plant else 'unknown'}.")
                        self.agent.print_status()

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
                            pass
                            #print(f"Player {self.agent.player_id} bids {bid_amount} for power plant {power_plant.min_bid if power_plant else 'unknown'}.")
                        else:
                            pass
                            #print(f"Player {self.agent.player_id} passes on bidding.")
                        self.agent.print_status()


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
                        #print(f"Player {self.agent.player_id} discards power plant {discard_number}.")
                        self.agent.print_status()


                    elif action == "auction_result":
                        # Handle auction result
                        winner = data.get("winner")
                        power_plant_data = data.get("power_plant", {})
                        power_plant = PowerPlant.from_dict(power_plant_data) if power_plant_data else None
                        bid = data.get("bid", 0)

                        # Not entering this condition !!!!!!!!!!
                        if winner == f'player{self.agent.player_id}@localhost':
                            # Add the power plant to the player's state
                            if power_plant:
                                self.agent.power_plants.append(power_plant)
                                self.agent.elektro -= bid  # Deduct the bid amount
                                self.agent.update_inventory()
                                print("Bid ammount: ", bid)
                                print(f"Winner {self.agent.player_id} currently has {self.agent.elektro} elektro, after bidding")
                                self.agent.print_status()

                                #print(f"Player {self.agent.player_id} won the auction for power plant {power_plant.min_bid} with bid {bid}.")
                        else:
                            print(f"Player {self.agent.player_id} currently has {self.agent.elektro} elektro, after bidding")
                            self.agent.print_status()

                            #print(f"Player {self.agent.player_id} observed that player {winner} won the auction for power plant {power_plant.min_bid if power_plant else 'unknown'} with bid {bid}.")

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
                        print(f"Player {self.agent.player_id} currently has {self.agent.elektro} elektro")

                    elif action == "purchase_result":
                        # Handle purchase result
                        purchases = data.get("purchases", {})
                        total_cost = data.get("total_cost", 0)
                        # Update player's resources and elektro
                        for resource, amount in purchases.items():
                            self.agent.resources[resource] = self.agent.resources.get(resource, 0) + amount
                        self.agent.elektro -= total_cost
                        self.agent.update_inventory()
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
                        #print(f"Player {self.agent.player_id} decides to build in cities: {cities_to_build}.")

                    elif action == "build_result":
                        # Handle build result
                        cities = data.get("cities", [])
                        total_cost = data.get("total_cost", 0)
                        # Update player's cities
                        self.agent.cities_owned.extend(cities)
                        self.agent.elektro -= total_cost
                        self.agent.update_inventory()
                        #print(f"Player {self.agent.player_id} built houses in cities: {cities} for total cost {total_cost}.")


                    elif phase == "phase5":
                        # Phase 5 (Bureaucracy)
                        print(f"Player {self.agent.player_id} acknowledges Phase 5 - Bureaucracy.")
                        # Decide how to power cities
                        cities_powered = self.decide_cities_to_power()
                        # Send the number of cities powered back to the manager
                        response = Message(to=sender)
                        response.body = json.dumps({
                            "phase": "phase5",
                            "action": "power_cities",
                            "cities_powered": cities_powered
                        })
                        await self.send(response)
                        print(f"Player {self.agent.player_id} decides to power {cities_powered} cities.")

                elif phase == "game_over":
                    # Handle game over
                    winner = data.get("winner")
                    final_elektro = data.get("final_elektro")
                    if winner == f'player{self.agent.player_id}@localhost':
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
            Leverages the existing evaluate_power_plant function for decision-making.
            Factors:
            - Whether the player needs a power plant.
            - Value of the power plants in the market.
            - Remaining Elektro after purchase.
            """
            # Player needs a power plant if they have less than 3
            need_power_plant = len(self.agent.power_plants) < 3

            # Filter affordable power plants
            affordable_plants = [pp for pp in power_plant_market if pp.min_bid <= self.agent.elektro]
            if not affordable_plants:
                # No affordable plants in the market
                return True

            # Evaluate all affordable plants
            evaluated_plants = [(pp, self.evaluate_power_plant(pp)) for pp in affordable_plants]

            # Choose the plant with the highest value
            best_plant, best_value = max(evaluated_plants, key=lambda x: x[1])

            # Determine if purchasing this plant leaves enough Elektro for future turns
            remaining_elektro = self.agent.elektro - best_plant.min_bid

            # Decision-making logic
            if remaining_elektro < 10:
                # Pass if buying the plant would leave too little Elektro
                return True

            # Pass if the player doesn't need a plant or the best plant is not worth it
            return not need_power_plant or best_value < 1.5

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
                return current_bid + 3
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
            Decide which resources to buy based on the power plants owned and the price table.
            Ensures that the player does not spend more Elektro than they have.
            """
            purchases = {"coal": 0, "oil": 0, "garbage": 0, "uranium": 0}

            def get_resource_cost(resource_type, amount_to_buy, resource_market):
                """
                Calculate the total cost for a given resource type and amount using the price table.
                """
                total_cost = 0
                available_units = resource_market.get(resource_type, 0)

                if resource_type == "uranium":
                    # Uranium has a direct mapping of quantity to price
                    for unit in range(1, amount_to_buy + 1):
                        if available_units >= unit:
                            total_cost += price_table["uranium"].get(unit, float('inf'))
                else:
                    # Coal, oil, and garbage have ranges for pricing
                    for unit in range(1, amount_to_buy + 1):
                        for range_key, price in price_table[resource_type].items():
                            if isinstance(range_key, tuple) and unit in range_key:
                                total_cost += price
                                break
                return total_cost

            for plant in self.agent.power_plants:
                resource_types = plant.resource_type
                resource_needed = plant.resource_num
                is_hybrid = plant.is_hybrid

                if not resource_types or resource_needed == 0:
                    continue  # Eco-friendly plant or no resources needed

                if is_hybrid:
                    # Hybrid plant: buy resources in any combination
                    for rtype in resource_types:
                        available = resource_market.get(rtype, 0)
                        if available > 0:
                            # Determine max affordable quantity
                            max_affordable = self.agent.elektro // get_resource_cost(rtype, 1, resource_market)
                            amount_to_buy = min(available, resource_needed, max_affordable)
                            total_cost = get_resource_cost(rtype, amount_to_buy, resource_market)

                            if total_cost <= self.agent.elektro:
                                purchases[rtype] += amount_to_buy
                                resource_needed -= amount_to_buy
                                self.agent.elektro -= total_cost

                            if resource_needed <= 0:
                                break
                else:
                    # Non-hybrid plant: buy required resources
                    rtype = resource_types[0]
                    available = resource_market.get(rtype, 0)
                    if available > 0:
                        # Determine max affordable quantity
                        max_affordable = self.agent.elektro // get_resource_cost(rtype, 1, resource_market)
                        amount_to_buy = min(available, resource_needed, max_affordable)
                        total_cost = get_resource_cost(rtype, amount_to_buy, resource_market)

                        if total_cost <= self.agent.elektro:
                            purchases[rtype] += amount_to_buy
                            resource_needed -= amount_to_buy
                            self.agent.elektro -= total_cost

            # Update inventory to reflect the purchases
            self.agent.update_inventory()
            return purchases

        def decide_cities_to_build(self, map_status):
            environment = globals.environment_instance
            board_map = environment.map
            available_elektro = self.agent.elektro
            cities_to_build = []

            print(f"Player {self.agent.player_id} has {available_elektro} elektro.")

            for city, data in map_status.items():
                # Skip cities the player already owns
                if city in self.agent.cities_owned:
                    print(f"Player {self.agent.player_id} already owns city {city}. Skipping.")
                    continue

                # Skip cities that are not available (e.g., fully occupied)
                if not board_map.is_city_available(city, environment.step):
                    print(f"City {city} is not available. Skipping.")
                    continue

                # Calculate connection cost
                connection_cost = board_map.get_connection_cost(f"player{self.agent.player_id}@localhost", city)
                building_cost = environment.building_cost[environment.step]
                total_cost = connection_cost + building_cost

                if total_cost > available_elektro:
                    print(f"Player {self.agent.player_id} cannot afford city {city}. Skipping.")
                    continue

                # Add city to build list and deduct costs
                cities_to_build.append(city)
                available_elektro -= total_cost
                self.agent.elektro -= total_cost  # Deduct from player's elektro
                self.agent.cities_owned.append(city)  # Add city to owned cities
                self.agent.update_inventory()  # Update inventory to reflect changes
                print(f"Player {self.agent.player_id} builds in city {city}. Remaining elektro: {available_elektro}")

                if available_elektro <= 0:
                    break

            return cities_to_build

        def evaluate_city_priority(self, city_tag, city_data):
            """
            Evaluate a city's priority for building.
            Factors:
            - Proximity to already owned cities.
            - Strategic growth potential.
            """
            environment = globals.environment_instance  # Access the global environment instance
            board_map = environment.map
            proximity_score = 0

            # Calculate proximity to owned cities
            for owned_city in self.agent.cities_owned:
                if nx.has_path(board_map.map, source=city_tag, target=owned_city):
                    proximity_score += 1

            # Factor in occupancy (fewer owners = higher priority)
            occupancy_score = max(0, environment.step - len(city_data.get('owners', [])))

            # Combine scores (weights can be adjusted based on strategy)
            return proximity_score + occupancy_score

        def decide_cities_to_power(self):
            """
            Decides how many cities to power based on the player's resources, power plants, and owned cities.
            """
            available_resources = self.agent.resources.copy()
            cities_powered = 0

            for plant in self.agent.power_plants:
                resource_needed = plant.resource_num
                if not plant.resource_type:
                    # Eco-friendly plant: powers cities without consuming resources
                    cities_powered += plant.cities
                elif plant.is_hybrid:
                    # Hybrid plant: mix resources
                    total_available = sum(available_resources[r] for r in plant.resource_type)
                    if total_available >= resource_needed:
                        for r in plant.resource_type:
                            used = min(resource_needed, available_resources[r])
                            available_resources[r] -= used
                            resource_needed -= used
                            if resource_needed == 0:
                                break
                        cities_powered += plant.cities
                else:
                    # Single-resource plant
                    rtype = plant.resource_type[0]
                    if available_resources[rtype] >= resource_needed:
                        available_resources[rtype] -= resource_needed
                        cities_powered += plant.cities

                # Stop if we've powered all owned cities
                if cities_powered >= len(self.agent.cities_owned):
                    break

            # Deduct resources from inventory
            self.agent.resources = available_resources
            self.agent.update_inventory()  # Update resources in the global inventory

            print(f"Player {self.agent.player_id} powered {cities_powered} cities.")
            return cities_powered

    async def setup(self):
        print(f"Player {self.player_id} agent starting...")
        receive_phase_behaviour = PowerGridPlayerAgent.ReceivePhaseBehaviour()
        self.add_behaviour(receive_phase_behaviour)
