# player_agent.py
from time import sleep
import os
import asyncio
import random

from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import json

from objects import PowerPlant
from game_environment import Environment
from rule_tables import *
import globals
import networkx as nx

#######################  METHODS TO FORMAT STRINGS  ###########################

# methods to format strings at terminal outputs, don t need to be defined within the class
def split_parts():
    print("\n" + "-" * 30 + "\n")

#######################  METHODS TO CREATE THE LOG  #########################
def create_log():
    """
    Creates or clears the log file named 'log.txt'.
    """
    with open("log.txt", "w") as log_file:
        # Opening in 'w' mode ensures the file is emptied if it exists.
        pass
    print("Log file 'log.txt' created or cleared.")


def update_log(message):
    """
    Appends the given string to the next line of the log file, called "log.txt".

    :argument:
        message (str): The message to append to the log file.
    """
    with open("log.txt", "a") as log_file:
        log_file.write(message + "\n")
    #print(f"Message added to log: {message}")

#############################################################################



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

    def decide_cities_to_power(self):
        """
        Decides how many cities to power based on the player's resources, power plants, and owned cities.
        Updates Elektro and resources directly.
        """
        available_resources = self.resources.copy()
        cities_powered = 0
        resources_consumed = {}

        for plant in self.power_plants:
            resource_needed = plant.resource_num

            # Stop if we've powered all owned cities
            if cities_powered >= len(self.cities_owned):
                break

            # If it's free, just power
            if not plant.resource_type:
                # Eco-friendly plant: powers cities without consuming resources
                cities_powered += plant.cities

            # If it's hybrid, use any combination of resources
            elif plant.is_hybrid:
                # Hybrid plant: mix resources
                total_available = sum(available_resources.get(r, 0) for r in plant.resource_type)
                if total_available >= resource_needed:
                    consumed = {}
                    for rtype in plant.resource_type:
                        used = min(resource_needed, available_resources.get(rtype, 0))
                        if used > 0:
                            consumed[rtype] = consumed.get(rtype, 0) + used
                            available_resources[rtype] -= used
                            resource_needed -= used
                            if resource_needed == 0:
                                break

                    cities_powered += plant.cities
                    # Stop if we've powered all owned cities
                    if cities_powered >= len(self.cities_owned):
                        break
                    # Record consumed resources
                    for r, amt in consumed.items():
                        resources_consumed[r] = resources_consumed.get(r, 0) + amt
            else:
                # Single-resource plant
                rtype = plant.resource_type[0]
                if available_resources.get(rtype, 0) >= resource_needed:
                    available_resources[rtype] -= resource_needed
                    cities_powered += plant.cities
                    resources_consumed[rtype] = resources_consumed.get(rtype, 0) + resource_needed

        if cities_powered > len(self.cities_owned):
            cities_powered = len(self.cities_owned)

        # Calculate income based on city_cashback
        if cities_powered <= len(city_cashback):
            elektro_earned = city_cashback[cities_powered]
        else:
            elektro_earned = city_cashback[-1]  # Use max cashback value if cities_powered exceeds defined cashback

        # Update Elektro and resources
        self.elektro += elektro_earned
        self.resources = available_resources
        self.update_inventory()

        update_log(f"Player {self.player_id} powered {cities_powered} cities,"
                   f" earned {elektro_earned} Elektro,"
                   f" and consumed {resources_consumed}."
                   f"\n Elektro after cashback: {self.elektro}")
        return cities_powered, resources_consumed

    def print_status(self, phase=-1, round_no='placeholder_for_manager_retrieval', turn=-1, subphase=None, decision=""):
        print("\n##########################################################   CURRENTLY HAPPENING   ##########################################################  \n")
        print(f"It's the player {turn}'s turn: ")
        print(f"Current round: {round_no}")
        print(f"The current phase is {phase} and sub phase is {subphase}")
        print(f"The decision is: {decision}")
        globals.environment_instance.print_environment()
        sleep(1)
        os.system("clear")


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
                    update_log(f"Player {self.agent.player_id} received invalid JSON.")
                    return

                phase = data.get("phase")
                action = data.get("action")

                if phase == "setup":
                    # Handle setup phase
                    player_order = data.get("player_order")
                    self.agent.position = player_order
                    self.agent.update_inventory()
                    update_log(f"Player {self.agent.player_id} received setup information. Position: {player_order}")

                elif phase == "phase1":
                    # Handle player order notification
                    player_order = data.get("player_order")
                    self.agent.position = player_order
                    self.agent.update_inventory()
                    update_log(f"Player {self.agent.player_id} is in position {player_order}")
                    self.agent.print_status(phase=phase, round_no=data.get("round"), 
                                            turn=self.agent.player_id, subphase=action, decision = "Phase 1 (choose order based on city ownership).")


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
                                update_log(f"Player {self.agent.player_id} decides to pass on starting an auction.")
                                self.agent.print_status(phase=phase, round_no=data.get("round"), 
                                                        turn=self.agent.player_id,
                                                        subphase=action, decision="Pass.")

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
                                    update_log(f"Player {self.agent.player_id} chooses to auction power plant {chosen_plant_number}.")
                                    self.agent.print_status(phase=phase, round_no=data.get("round"),
                                                            turn=self.agent.player_id, 
                                                            subphase=action, decision="Proceed to auction.")


                                else:
                                    # Cannot afford any power plant, so pass
                                    choice_msg = Message(to=sender)
                                    choice_data = {
                                        "choice": "pass"
                                    }
                                    choice_msg.body = json.dumps(choice_data)
                                    await self.send(choice_msg)
                                    update_log(f"Player {self.agent.player_id} cannot afford any power plant and passes.")
                                    self.agent.print_status(phase=phase, round_no=data.get("round"),
                                                            turn=self.agent.player_id, 
                                                            subphase=action, decision="Pass (can't afford).")


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
                            update_log(f"Player {self.agent.player_id} must auction power plant {chosen_plant_number} (first round).")
                            self.agent.print_status(phase=phase, round_no=data.get("round"),
                                                    turn=self.agent.player_id, 
                                                    subphase=action, decision="Proceed to auction (mandatory).")

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
                        update_log(f"Player {self.agent.player_id} places initial bid of {bid_amount} on power plant {power_plant.min_bid if power_plant else 'unknown'}.")
                        self.agent.print_status(phase=phase, round_no=data.get("round"),
                                                turn=self.agent.player_id, 
                                                subphase=action, decision=f"Initial bid of {bid_amount} elektro.")


                    elif action == "bid":
                        wants_powerplant = [True,False] # adds randomness to player choice

                        # wants powerplant
                        if random.choice(wants_powerplant):

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
                                self.agent.print_status(phase=phase, round_no=data.get("round"),
                                                        turn=self.agent.player_id,
                                                        subphase=action,
                                                        decision=f"Bid {bid_amount} elektro for the power_plant {power_plant.min_bid if power_plant else 'unknown'}.")
                                update_log(f"Player {self.agent.player_id} bids {bid_amount} for power plant {power_plant.min_bid if power_plant else 'unknown'}.")
                            else:
                                self.agent.print_status(phase=phase, round_no=data.get("round"),
                                                        turn=self.agent.player_id,
                                                        subphase=action,
                                                        decision=f"Passes for {bid_amount}, not beneficial.")
                                update_log(f"Player {self.agent.player_id} passes on bidding.")

                        # doesn't want powerplant
                        else:
                            pass
                            bid_amount = 0
                            self.agent.print_status(phase=phase, round_no=data.get("round"),
                                                    turn=self.agent.player_id,
                                                    subphase=action,
                                                    decision=f"Passes on {bid_amount}, since he does.")
                            update_log(f"Player {self.agent.player_id} passes on bidding, doesn't want power plant.")

                        self.agent.print_status(phase=phase, round_no=data.get("round"),
                                                turn=self.agent.player_id, 
                                                subphase=action, decision=f"Passes, since it doesn't want the power plant.")

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
                        update_log(f"Player {self.agent.player_id} discards power plant {discard_number}.")
                        self.agent.print_status(phase=phase, round_no=data.get("round"),
                                                turn=self.agent.player_id, 
                                                subphase=action, decision=f"Discard {discard_number}, can't have more than 3 pp.")


                    elif action == "auction_result":
                        # Handle auction result
                        winner = data.get("winner")
                        power_plant_data = data.get("power_plant", {})
                        power_plant = PowerPlant.from_dict(power_plant_data) if power_plant_data else None
                        bid = data.get("bid", 0)

                        if winner == f'player{self.agent.player_id}@localhost':
                            self.agent.elektro -= bid  # Deduct the bid amount
                            self.agent.update_inventory()
                            # Add the power plant to the player's state only if it's not already present
                            if power_plant and all(pp.min_bid != power_plant.min_bid for pp in self.agent.power_plants):
                                self.agent.power_plants.append(power_plant)
                                self.agent.update_inventory()
                                update_log(f"Bid amount: {bid}")
                                update_log(f"Winner {self.agent.player_id} currently has {self.agent.elektro} elektro, after bidding")

                                update_log(f"Player {self.agent.player_id} won the auction for power plant {power_plant.min_bid} with bid {bid}.")
                                self.agent.print_status(phase=phase, round_no=data.get("round"),
                                                        turn=self.agent.player_id,
                                                        subphase=action, decision="Appends the power plant to the inventory and changes balance.")
                        else:
                            update_log(f"Player {self.agent.player_id} currently has {self.agent.elektro} elektro, after bidding")

                            update_log(f"Player {self.agent.player_id} observed that player {winner} won the auction for power plant {power_plant.min_bid if power_plant else 'unknown'} with bid {bid}.")

                elif phase == "phase3":
                    if action == "buy_resources":
                        # Receive resource market information
                        resource_market = data.get("resource_market", {})
                        # Decide which resources to buy
                        purchases, total_cost = self.decide_resources_to_buy(resource_market)
                        purchase_msg = Message(to=sender)
                        purchase_data = {
                            "purchases": purchases,  # Dict of resources to buy
                            "total_cost": total_cost  # Total cost of purchases
                        }
                        purchase_msg.body = json.dumps(purchase_data)
                        await self.send(purchase_msg)
                        update_log(f"Player {self.agent.player_id} decides to buy resources: {purchases} for total cost {total_cost}.")
                        update_log(f"Player {self.agent.player_id} currently has {self.agent.elektro} elektro")
                        self.agent.print_status(phase=phase, round_no=data.get("round"),
                                                turn=self.agent.player_id,
                                                subphase=action,
                                                decision=f"Buy resources: {purchases} for total cost {total_cost}.")


                    elif action == "purchase_result":
                        # Handle purchase result
                        purchases = data.get("purchases", {})
                        total_cost = data.get("total_cost", 0)
                        if total_cost > self.agent.elektro:
                            print(f"Error: Player {self.agent.player_id} cannot afford the total cost of {total_cost}.")
                            # Handle the error appropriately, possibly reverting the purchases
                        else:
                            # Deduct the total cost
                            self.agent.elektro -= total_cost
                            # Update player's resources
                            for resource, amount in purchases.items():
                                if amount > 0:
                                    self.agent.resources[resource] = self.agent.resources.get(resource, 0) + amount
                            self.agent.update_inventory()
                            update_log(f"Player {self.agent.player_id} purchased resources: {purchases} for total cost {total_cost}. Remaining elektro: {self.agent.elektro}")


                elif phase == "phase4":
                    if action == "build_houses":
                        # Receive map status and current step
                        map_status = data.get("map_status", {})
                        current_step = data.get("step", 2)
                        self.agent.step = current_step
                        # Decide where to build
                        cities_to_build = self.decide_cities_to_build(map_status)
                        build_msg = Message(to=sender)
                        build_data = {
                            "cities": cities_to_build
                        }
                        build_msg.body = json.dumps(build_data)
                        await self.send(build_msg)
                        update_log(f"Player {self.agent.player_id} decides to build in cities: {cities_to_build}.")
                        self.agent.print_status(phase=phase, round_no=data.get("round"),
                                                turn=self.agent.player_id,
                                                subphase=action,
                                                decision=f"Build in cities: {cities_to_build}.")

                    elif action == "build_result":
                        # Handle build result
                        cities = data.get("cities", [])
                        total_cost = data.get("total_cost", 0)
                        # Update player's cities
                        self.agent.cities_owned.extend(cities)
                        self.agent.cities_owned = list(set(self.agent.cities_owned))
                        self.agent.update_inventory()
                        update_log(f"Player {self.agent.player_id} "
                              f"chose to purchase {cities},"
                              f" updating them to {self.agent.cities_owned}"
                              f" totaling {total_cost}"
                              f" while having {self.agent.elektro}")
                        self.agent.update_inventory()
                        update_log(f"Player {self.agent.player_id} built houses in cities: {cities} for total cost {total_cost}.")


                elif phase == "phase5":
                    if action == "power_cities_request":
                        # Handle power cities request
                        update_log(f"Player {self.agent.player_id} received power_cities_request.")
                        # Decide how to power cities
                        cities_powered, resources_consumed = self.agent.decide_cities_to_power()
                        # Send the number of cities powered and resources consumed back to the manager
                        response = Message(to=sender)
                        response.body = json.dumps({
                            "phase": "phase5",
                            "action": "power_cities",
                            "cities_powered": cities_powered,
                            "resources_consumed": resources_consumed,
                            "elektro": self.agent.elektro  # Include updated Elektro
                        })
                        self.agent.print_status(phase=phase, round_no=data.get("round"),
                                                turn=self.agent.player_id,
                                                subphase=action,
                                                decision=f"Powered {cities_powered} for total cost {resources_consumed}.")
                        await self.send(response)

                elif phase == "check_game_end":
                    if action == "get_cities_owned":
                        # Respond with the list of cities owned
                        response = Message(to=sender)
                        response.body = json.dumps({
                            "phase": "check_game_end",
                            "action": "cities_owned",
                            "cities_owned": self.agent.cities_owned
                        })
                        await self.send(response)
                        update_log(
                            f"Player {self.agent.player_id} responded with cities_owned: {self.agent.cities_owned}")


                elif phase == "game_over":
                    # Handle game over
                    winner = data.get("winner")
                    final_elektro = data.get("final_elektro")
                    if winner == f'player{self.agent.player_id}@localhost':
                        update_log(f"Player {self.agent.player_id} has won the game with {final_elektro} Elektro!")
                    else:
                        update_log(f"Player {self.agent.player_id} has lost. Winner: {winner} with {final_elektro} Elektro.")
                    await self.agent.stop()

                elif phase == "end_game" and action == "get_final_stats":
                    # Respond with the number of cities powered and current Elektro
                    cities_powered = len(self.agent.cities_powered)
                    elektro = self.agent.elektro  # Current Elektro balance
                    response = Message(to=sender)
                    response.body = json.dumps({
                        "phase": "end_game",
                        "action": "final_stats",
                        "cities_powered": cities_powered,
                        "elektro": elektro
                    })
                    await self.send(response)
                    update_log(
                        f"Player {self.agent.player_id} reports {cities_powered} cities powered and {elektro} Elektro.")

                else:
                    update_log(f"Player {self.agent.player_id} received an unknown message: {msg.body}")
            else:
                update_log(f"Player {self.agent.player_id} did not receive any message.")
            await asyncio.sleep(0.2)  # Yield control to event loop


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
                update_log(f"Player {self.agent.player_id} finds no available power plants to auction.")
                return None

            # Evaluate power plants assuming 'market' contains PowerPlant objects
            affordable_plants = [pp for pp in market if pp.min_bid <= self.agent.elektro]
            if not affordable_plants:
                update_log(f"Player {self.agent.player_id} cannot afford any power plant.")
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
            Decide which resources to buy based on the power plants owned, their storage capacity, and the price table.
            Ensures the player does not spend more Elektro than they have and does not exceed storage capacity.
            Returns a dictionary of purchases and the total cost.
            """
            purchases = {"coal": 0, "oil": 0, "garbage": 0, "uranium": 0}
            total_cost = 0

            # Step 1: Calculate the total storage limits and current needs for each resource type
            resource_needs = {"coal": 0, "oil": 0, "garbage": 0, "uranium": 0}
            resource_storage_limits = {"coal": 0, "oil": 0, "garbage": 0, "uranium": 0}

            for plant in self.agent.power_plants:
                if plant.resource_type and plant.resource_num > 0:
                    for rtype in plant.resource_type:
                        # Calculate remaining capacity for the resource in this plant
                        remaining_capacity = plant.available_storage - sum(plant.storage.values())
                        resource_needs[rtype] += max(plant.resource_num - plant.storage.get(rtype, 0), 0)
                        resource_storage_limits[rtype] += remaining_capacity

            # Step 2: Helper function to get sorted unit costs for each resource type
            def get_sorted_unit_costs(resource_type):
                """
                Returns a list of unit costs sorted from cheapest to most expensive.
                """
                unit_costs = []
                available_units = resource_market.get(resource_type, 0)
                if available_units <= 0:
                    return unit_costs

                if resource_type == "uranium":
                    for unit, cost in price_table["uranium"].items():
                        if unit <= available_units:
                            unit_costs.append(cost)
                else:
                    for range_key, price in price_table[resource_type].items():
                        if isinstance(range_key, tuple):
                            for unit in range(range_key[0], range_key[1] + 1):
                                if unit <= available_units:
                                    unit_costs.append(price)
                unit_costs.sort()
                return unit_costs

            # Step 3: Create a sorted list of resources by cheapest unit cost
            resource_priority = []
            for resource in ["coal", "oil", "garbage", "uranium"]:
                unit_costs = get_sorted_unit_costs(resource)
                if unit_costs:
                    resource_priority.append((unit_costs[0], resource))
            resource_priority.sort(key=lambda x: x[0])

            # Step 4: Buy resources, considering storage and affordability
            for cost, resource in resource_priority:
                # Determine how much can be bought based on needs, availability, and storage
                current_stock = self.agent.resources.get(resource, 0) + purchases[resource]
                max_storage = resource_storage_limits[resource]
                if current_stock >= max_storage:
                    update_log(
                        f"{resource.capitalize()} storage at capacity ({current_stock}/{max_storage}). Skipping.")
                    continue

                needed = resource_needs[resource] - purchases[resource]
                available = resource_market.get(resource, 0)
                max_additional_storage = max_storage - current_stock

                if needed <= 0 or available <= 0:
                    update_log(f"No {resource} needed or available. Skipping.")
                    continue

                # Determine how many units can be bought
                units_to_buy = min(needed, available, max_additional_storage)
                max_affordable_units = self.agent.elektro // cost
                units_to_buy = min(units_to_buy, max_affordable_units)

                if units_to_buy <= 0:
                    update_log(f"Cannot afford {resource} at {cost} Elektro/unit.")
                    continue

                # Calculate total cost and enforce spending limit
                purchase_cost = units_to_buy * cost
                if purchase_cost > self.agent.elektro * 0.6:
                    units_affordable = int((self.agent.elektro * 0.6) // cost)
                    units_to_buy = min(units_to_buy, units_affordable)
                    purchase_cost = units_to_buy * cost

                if units_to_buy <= 0:
                    update_log(f"Purchase of {resource} exceeds spending limit. Skipping.")
                    continue

                # Register the purchase
                purchases[resource] += units_to_buy
                total_cost += purchase_cost
                self.agent.elektro -= purchase_cost

                update_log(f"Bought {units_to_buy} of {resource} for {purchase_cost} Elektro.")

            # Final Debugging Output
            update_log(
                f"Player {self.agent.player_id} decides to buy resources: {purchases} with total_cost: {total_cost} Elektro.")
            return purchases, total_cost

        def decide_cities_to_build(self, map_status):
            environment = globals.environment_instance
            board_map = environment.map
            available_elektro = self.agent.elektro
            available_houses = self.agent.houses
            cities_to_build = []

            update_log(f"Player {self.agent.player_id} has {available_elektro} elektro and {available_houses} houses.")

            # Calculate priorities for all cities not owned by the player
            city_priorities = []
            for city, data in map_status.items():
                if city in self.agent.cities_owned:
                    update_log(f"Player {self.agent.player_id} already owns city {city}. Skipping.")
                    continue

                if not board_map.is_city_available(city, environment.step):
                    update_log(f"City {city} is not available. Skipping.")
                    continue

                # Evaluate city priority
                priority = self.evaluate_city_priority(city, data)
                city_priorities.append((city, priority))

            # Sort cities by priority in descending order
            city_priorities.sort(key=lambda x: x[1], reverse=True)

            # Attempt to build only the highest-priority city
            for city, priority in city_priorities:
                connection_cost = board_map.get_connection_cost(f"player{self.agent.player_id}@localhost", city)
                building_cost = environment.building_cost[environment.step]
                total_cost = connection_cost + building_cost

                # Print the city and its associated costs
                update_log(
                    f"Considering city {city}: Connection cost = {connection_cost}, Building cost = {building_cost}, Total cost = {total_cost}")

                # Check if the player can afford the city
                if total_cost > available_elektro:
                    update_log(f"Player {self.agent.player_id} cannot afford city {city}. Skipping.")
                    continue

                if available_houses <= 0:
                    update_log(f"Player {self.agent.player_id} has no houses left to build in city {city}. Skipping.")
                    break

                # Deduct costs and ensure funds don't go negative
                if available_elektro - total_cost < 0:
                    update_log(f"Building in city {city} would result in negative elektro. Skipping.")
                    continue

                # Add city to build list and deduct costs
                cities_to_build.append(city)
                available_elektro -= total_cost
                available_houses -= 1

                # Update player's owned cities and resources
                self.agent.cities_owned.append(city)
                self.agent.elektro = available_elektro
                self.agent.houses = available_houses

                # Reflect changes in inventory
                self.agent.update_inventory()
                update_log(
                    f"Player {self.agent.player_id} builds in city {city}. Remaining elektro: {available_elektro}, houses: {available_houses}")

                # Stop after building one city
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

            # Handle occupancy score
            if isinstance(city_data, list):
                owners = city_data
            elif isinstance(city_data, dict):
                owners = city_data.get('owners', [])
            else:
                owners = []

            occupancy_score = max(0, environment.step - len(owners))

            # Combine scores (weights can be adjusted based on strategy)
            priority_score = proximity_score + occupancy_score
            update_log(
                f"City {city_tag}: Proximity score = {proximity_score}, Occupancy score = {occupancy_score}, Total priority = {priority_score}")
            return priority_score

    async def setup(self):
        update_log(f"Player {self.player_id} agent starting...")
        receive_phase_behaviour = PowerGridPlayerAgent.ReceivePhaseBehaviour()
        self.add_behaviour(receive_phase_behaviour)
