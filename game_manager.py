# game_manager.py

import asyncio
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import json
import re
import logging

# Import necessary classes and data structures
from objects import ResourceMarket, PowerPlantMarket, PowerPlant
from map_graph import BoardMap, citiesUS, edgesUS
from rule_tables import (
    city_cashback,
    resource_replenishment,
    building_cost,
    step_start_cities,
    game_end_cities
)
from game_environment import Environment  # Import Environment class


def split_parts():
    print("\n" + "-" * 30 + "\n")

def log_break():
    with open("log.txt", "a") as log_file:
        log_file.write("\n" + "-" * 30 + "\n")

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
    print(f"Message added to log: {message}")

#############################################################################
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GameManagerAgent(Agent):
    class GameBehaviour(CyclicBehaviour):
        def __init__(self, game_manager, player_jids):
            super().__init__()
            self.game_manager = game_manager
            self.player_jids = player_jids  # List of player JIDs
            self.players = {}  # Will be initialized in the setup phase
            self.current_phase = "setup"
            self.round = 1
            self.current_step = 2  # Game starts at Step 1
            self.game_over = False
            self.environment = None  # Will be initialized in setup phase

        async def run(self):
            if self.game_over:
                await asyncio.sleep(1)
                return  # Exit the behaviour when the game is over

            if self.current_phase == "setup":
                await self.setup_phase()
            elif self.current_phase == "phase1":
                log_break()
                await self.phase1()
            elif self.current_phase == "phase2":
                log_break()
                await self.phase2()
            elif self.current_phase == "phase3":
                log_break()
                await self.phase3()
            elif self.current_phase == "phase4":
                log_break()
                await self.phase4()
            elif self.current_phase == "phase5":
                log_break()
                await self.phase5()
            await asyncio.sleep(1)

        async def setup_phase(self):
            print("Game Manager is setting up the game.")
            # Initialize the environment with the number of players
            player_no = len(self.player_jids)
            self.environment = Environment(player_no)

            # Build mappings between JIDs and player IDs
            self.jid_to_player_id = {}
            self.player_id_to_jid = {}
            for jid in self.player_jids:
                player_name = jid.split('@')[0]  # e.g., 'player1'

                # Extract integer player ID
                match = re.search(r'\d+', player_name)
                if match:
                    player_id = int(match.group())
                else:
                    raise ValueError(f"Invalid player name format: {player_name}")

                self.jid_to_player_id[jid] = player_id
                self.player_id_to_jid[player_id] = jid

                # Ensure the environment has data for this player_id
                if player_id not in self.environment.players.keys():
                    raise KeyError(f"Player ID {player_id} not found in environment.")

                player_data = self.environment.players[player_id]
                self.players[jid] = {
                    "jid": jid,
                    "name": player_id,
                    "elektro": player_data['elektro'],
                    "power_plants": player_data['power_plants'],
                    "resources": player_data['resources'],
                    "cities": player_data['cities_owned'],
                    "houses": player_data['houses'],
                    "position": player_data['position'],
                    "has_bought_power_plant": player_data.get('has_bought_power_plant', False)
                }

            # Ensure order_players contains integer player IDs
            # For example, [1, 2, 3]
            if not all(isinstance(p, int) for p in self.environment.order_players):
                raise ValueError("order_players should contain integer player IDs.")

            self.player_order = [self.player_id_to_jid[p] for p in self.environment.order_players]
            #print(f'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n{self.player_order}\naaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa')

            # Notify all players about the setup phase completion
            for jid in self.player_jids:
                msg = Message(to=jid)
                msg.body = json.dumps({
                    "phase": "setup",
                    "map": "Map data here",  # You can serialize the map if needed
                    "player_order": self.players[jid]["position"],
                    "list_order_complete": self.player_order
                })
                await self.send(msg)

            # Proceed to Phase 1
            self.current_phase = "phase1"
            print("Moving to Phase 1")

        async def phase1(self):
            print("Phase 1: Determine Player Order")
            # Determine player order based on number of cities and largest power plant
            sorted_players = self.determine_player_order()

            # Update player positions
            for index, player in enumerate(sorted_players):
                player["position"] = index + 1

            # Notify players of the new order
            for player in sorted_players:
                msg = Message(to=player["jid"])
                msg.body = json.dumps({
                    "phase": "phase1",
                    "player_order": player["position"]
                })
                await self.send(msg)

            # Proceed to Phase 2
            self.current_phase = "phase2"
            print("Moving to Phase 2")

        async def phase2(self):
            print("Phase 2: Auction Power Plants")
            # Reset players' auction status
            for player in self.players.values():
                player["has_bought_power_plant"] = False

            # Players take turns starting auctions based on player order
            player_order = self.get_players_in_order()
            for player in player_order:
                if player["has_bought_power_plant"]:
                    continue  # Skip if already bought a power plant this round
                await self.handle_player_auction_choice(player)

            # End of Phase 2
            self.current_phase = "phase3"
            print("Moving to Phase 3")

        async def handle_player_auction_choice(self, player):
            """
            Handles the player's choice to either start an auction or pass.
            """
            # Determine if it's the first round
            is_first_round = self.round == 1

            # Players must buy a power plant in the first round
            can_pass = not is_first_round

            # Prepare the list of power plants for the player to choose from
            available_power_plants = [
                self.serialize_power_plant(pp) for pp in self.environment.power_plant_market.current_market
            ]

            msg = Message(to=player["jid"])
            msg.body = json.dumps({
                "phase": "phase2",
                "action": "choose_or_pass",
                "power_plants": available_power_plants,
                "can_pass": can_pass
            })
            await self.send(msg)

            # Wait for player's response
            response = await self.receive(timeout=30)
            if response and str(response.sender).split('/')[0] == player["jid"]:
                try:
                    data = json.loads(response.body)
                    choice = data.get("choice", "pass")
                except json.JSONDecodeError:
                    print(f"Invalid JSON response from {player['jid']}. Treating as pass.")
                    choice = "pass"
            else:
                print(f"No response from {player['jid']}. Treating as pass.")
                choice = "pass"

            if choice == "pass" and can_pass:
                player["has_bought_power_plant"] = True
                print(f"{player['jid']} chooses to pass on starting an auction.")
            elif choice == "auction":
                chosen_plant_number = data.get("power_plant_number", None)
                chosen_plant = self.get_power_plant_by_number(chosen_plant_number)
                if chosen_plant:
                    await self.conduct_auction(chosen_plant, player)
                else:
                    # Invalid choice, treat as pass
                    print(f"Invalid power plant choice by {player['jid']}. They pass this auction phase.")
                    player["has_bought_power_plant"] = True
            else:
                # Invalid choice or player couldn't pass
                player["has_bought_power_plant"] = True
                print(f"{player['jid']} cannot afford any power plant and passes.")

        async def conduct_auction(self, power_plant, starting_player):
            active_players = [p for p in self.get_players_in_order() if not p["has_bought_power_plant"]]
            if starting_player not in active_players:
                active_players.append(starting_player)
            base_min_bid = power_plant.min_bid

            # Prompt starting player for initial bid
            msg = Message(to=starting_player["jid"])
            msg.body = json.dumps({
                "phase": "phase2",
                "action": "initial_bid",
                "base_min_bid": base_min_bid,
                "power_plant": self.serialize_power_plant(power_plant)
            })
            await self.send(msg)

            # Wait for player's response
            response = await self.receive(timeout=15)
            if response and str(response.sender).split('/')[0] == starting_player["jid"]:
                try:
                    data = json.loads(response.body)
                    bid = data.get("bid", 0)
                except json.JSONDecodeError:
                    print(f"Invalid JSON bid from {starting_player['jid']}. Starting bid is {base_min_bid}.")
                    bid = base_min_bid
            else:
                # No response; starting player must bid at least the base_min_bid
                print(f"No response from {starting_player['jid']} for initial bid. Starting bid is {base_min_bid}.")
                bid = base_min_bid

            if bid >= base_min_bid and bid <= starting_player["elektro"]:
                current_bid = bid
                highest_bidder = starting_player
            else:
                # Invalid bid; starting player must bid at least the base_min_bid
                current_bid = base_min_bid
                highest_bidder = starting_player
                print(f"{starting_player['jid']} made an invalid initial bid. Starting bid is {base_min_bid}.")

            bidding_active = True
            bidders = active_players.copy()

            # Proceed with bidding from other players
            while bidding_active and len(bidders) > 1:
                for player in bidders.copy():
                    if player == highest_bidder:
                        continue  # Skip the highest bidder
                    msg = Message(to=player["jid"])
                    msg.body = json.dumps({
                        "phase": "phase2",
                        "action": "bid",
                        "current_bid": current_bid,
                        "power_plant": self.serialize_power_plant(power_plant)
                    })
                    await self.send(msg)

                    response = await self.receive(timeout=15)
                    if response and str(response.sender).split('/')[0] == player["jid"]:
                        try:
                            data = json.loads(response.body)
                            bid = data.get("bid", 0)
                        except json.JSONDecodeError:
                            print(f"Invalid JSON bid from {player['jid']}. They pass.")
                            bid = 0

                        if bid > current_bid and bid <= player["elektro"]:
                            current_bid = bid
                            highest_bidder = player
                            print(f"{player['jid']} bids {bid} for power plant {power_plant.min_bid}.")
                        else:
                            print(f"{player['jid']} passes or cannot outbid {current_bid}.")
                            bidders.remove(player)
                            if len(bidders) == 1:
                                bidding_active = False
                                break
                    else:
                        print(f"No response from {player['jid']}. They pass.")
                        bidders.remove(player)
                        if len(bidders) == 1:
                            bidding_active = False
                            break

            # Finalize auction
            if highest_bidder is not None:
                highest_bidder["elektro"] -= current_bid
                highest_bidder["power_plants"].append(power_plant)
                highest_bidder["has_bought_power_plant"] = True
                print(f"{highest_bidder['jid']} wins the auction for power plant {power_plant.min_bid} with a bid of {current_bid} Elektro.")

                print("Highest bidder: ", highest_bidder)
                # Handle discard if necessary
                if len(highest_bidder["power_plants"]) > 3:
                    await self.handle_power_plant_discard(highest_bidder)

                print("Highest bidder after waiting for discard: ", highest_bidder)

                # Update the power plant market
                self.environment.power_plant_market.remove_plant_from_market(power_plant)
                self.environment.power_plant_market.update_markets()

                # Notify all players of the auction result
                for p in self.players.values():
                    msg = Message(to=p["jid"])
                    msg.body = json.dumps({
                        "phase": "phase2",
                        "action": "auction_result",
                        "winner": highest_bidder["jid"],
                        "power_plant": self.serialize_power_plant(power_plant),
                        "bid": current_bid
                    })
                    await self.send(msg)

                # If starting player did not win, they can choose to start another auction
                if starting_player != highest_bidder and not starting_player["has_bought_power_plant"]:
                    await self.handle_player_auction_choice(starting_player)
            else:
                print("Auction ended with no winner.")

        def get_power_plant_by_number(self, number):
            """
            Retrieves a PowerPlant object from the current market given its min_bid number.
            """
            # Check in the current market only
            for plant in self.environment.power_plant_market.current_market:
                if plant.min_bid == number:
                    return plant
            return None

        async def handle_power_plant_discard(self, player):
            """
            When a player has more than 3 power plants, they must discard one (not the one just bought).
            """
            # Exclude the just bought power plant
            discardable_plants = [pp for pp in player["power_plants"] if pp != player["power_plants"][-1]]

            msg = Message(to=player["jid"])
            msg.body = json.dumps({
                "phase": "phase2",
                "action": "discard_power_plant",
                "power_plants": [self.serialize_power_plant(pp) for pp in discardable_plants]
            })
            await self.send(msg)

            # Wait for player's response
            response = await self.receive(timeout=30)
            if response and str(response.sender).split('/')[0] == player["jid"]:
                try:
                    data = json.loads(response.body)
                    discard_number = data.get("discard_number", None)
                except json.JSONDecodeError:
                    discard_number = None

                discarded_plant = self.get_player_power_plant_by_number(player, discard_number)
                if discarded_plant and discarded_plant != player["power_plants"][-1]:
                    player["power_plants"].remove(discarded_plant)
                    print(f"{player['jid']} discarded power plant {discarded_plant.min_bid}.")
                else:
                    # Invalid choice; automatically discard the oldest plant (excluding the just bought one)
                    if discardable_plants:
                        plant_to_discard = discardable_plants[0]
                        player["power_plants"].remove(plant_to_discard)
                        print(f"Invalid discard number from {player['jid']}. Automatically discarding power plant {plant_to_discard.min_bid}.")
                    else:
                        print(f"No discardable plants for {player['jid']}.")
            else:
                # No response; automatically discard the oldest plant (excluding the just bought one)
                if discardable_plants:
                    plant_to_discard = discardable_plants[0]
                    player["power_plants"].remove(plant_to_discard)
                    print(f"No response from {player['jid']} on discard. Automatically discarding power plant {plant_to_discard.min_bid}.")
                else:
                    print(f"No discardable plants for {player['jid']}.")

        def get_player_power_plant_by_number(self, player, number):
            for plant in player["power_plants"]:
                if plant.min_bid == number:
                    return plant
            return None

        def get_players_in_order(self):
            # Return a list of players (dict) sorted by their position
            sorted_players = sorted(
                self.players.values(),
                key=lambda p: p["position"]
            )
            return sorted_players

        def get_players_in_reverse_order(self):
            # Return a list of players (dict) sorted by their position in reverse order
            sorted_players = sorted(
                self.players.values(),
                key=lambda p: p["position"],
                reverse=True
            )
            return sorted_players

        def determine_player_order(self):
            # Sort players based on number of cities connected and largest power plant
            players_list = list(self.players.values())

            # Sort by number of cities first, descending
            # Then by largest power plant number, descending
            # If a player has no power plants, it treats largest power plant as 0
            def largest_power_plant_num(player):
                if player["power_plants"]:
                    return max(pp.min_bid for pp in player["power_plants"])
                return 0

            players_list.sort(key=lambda p: (-len(p["cities"]), -largest_power_plant_num(p)))
            return players_list

        def serialize_power_plant(self, power_plant):
            """
            Serializes a PowerPlant object into a dictionary for sending via message.
            """
            return {
                "min_bid": power_plant.min_bid,
                "cities": power_plant.cities,
                "resource_type": power_plant.resource_type,
                "resource_num": power_plant.resource_num,
                "is_hybrid": power_plant.is_hybrid,
                "is_step": power_plant.is_step
            }

        async def phase3(self):
            print("Phase 3: Buy Resources")
            # Players buy resources in reverse player order
            player_order = self.get_players_in_reverse_order()
            for player in player_order:
                await self.handle_resource_purchase(player)

            # Proceed to Phase 4
            self.current_phase = "phase4"
            print("Moving to Phase 4")

        async def handle_resource_purchase(self, player):
            msg = Message(to=player["jid"])
            msg.body = json.dumps({
                "phase": "phase3",
                "action": "buy_resources",
                "resource_market": self.environment.resource_market.in_market
            })
            await self.send(msg)

            # Wait for player's response
            response = await self.receive(timeout=30)
            if response and str(response.sender).split('/')[0] == player["jid"]:
                try:
                    data = json.loads(response.body)
                    purchases = data.get("purchases", {})
                except json.JSONDecodeError:
                    print(f"Invalid JSON response from {player['jid']} in resource purchase phase.")
                    purchases = {}

                total_cost = 0

                for resource, amount in purchases.items():
                    price = self.calculate_resource_price(resource, amount)
                    if price <= player["elektro"] and amount <= self.environment.resource_market.in_market.get(resource, 0):
                        player["elektro"] -= price
                        player["resources"][resource] += amount
                        self.environment.resource_market.in_market[resource] -= amount
                        total_cost += price
                    else:
                        print(f"{player['jid']} cannot purchase {amount} of {resource}")

                # Notify player of the purchase result
                msg = Message(to=player["jid"])
                msg.body = json.dumps({
                    "phase": "phase3",
                    "action": "purchase_result",
                    "purchases": purchases,
                    "total_cost": total_cost
                })
                await self.send(msg)
            else:
                print(f"No response from {player['jid']} in resource purchase phase.")

        def calculate_resource_price(self, resource, amount):
            # Implement resource price calculation using the environment's price table
            total_price = 0
            resource_market = self.environment.resource_market
            resource = str(resource).strip()
            for _ in range(amount):
                price = resource_market.resource_price(resource)
                if price is not None:
                    total_price += price
                else:
                    print(f"Not enough {resource} available.")
                    break
            return total_price

        async def phase4(self):
            print("Phase 4: Build Houses")
            # Players build houses in reverse player order
            player_order = self.get_players_in_reverse_order()
            for player in player_order:
                await self.handle_build_houses(player)

            # Proceed to Phase 5
            self.current_phase = "phase5"
            print("Moving to Phase 5")

        async def handle_build_houses(self, player):
            msg = Message(to=player["jid"])
            msg.body = json.dumps({
                "phase": "phase4",
                "action": "build_houses",
                "map_status": self.environment.map.get_status(),
                "step": self.current_step
            })
            await self.send(msg)

            # Wait for player's response
            response = await self.receive(timeout=30)
            if response and str(response.sender).split('/')[0] == player["jid"]:
                try:
                    data = json.loads(response.body)
                    cities_to_build = data.get("cities", [])
                except json.JSONDecodeError:
                    print(f"Invalid JSON response from {player['jid']} in build houses phase.")
                    cities_to_build = []

                total_cost = 0
                for city_tag in cities_to_build:
                    cost = self.calculate_building_cost(player, city_tag)
                    if cost <= player["elektro"] and self.is_city_available(city_tag, player):
                        player["elektro"] -= cost
                        player["cities"].append(city_tag)
                        total_cost += cost
                        self.environment.map.update_owner(player["jid"], city_tag)
                    else:
                        print(f"{player['jid']} cannot build in {city_tag}")

                # Notify player of the build result
                msg = Message(to=player["jid"])
                msg.body = json.dumps({
                    "phase": "phase4",
                    "action": "build_result",
                    "cities": cities_to_build,
                    "total_cost": total_cost
                })
                await self.send(msg)
            else:
                print(f"No response from {player['jid']} in build houses phase.")

        def calculate_building_cost(self, player, city_tag):
            # Implement building cost calculation using the environment's building cost
            city = self.environment.map.map.nodes.get(city_tag)
            if city:
                occupancy = len(city.get('owners', []))
                if occupancy < self.current_step:
                    building_cost = self.environment.building_cost[self.current_step]
                    # For simplicity, assume connection cost is zero
                    return building_cost
            return float('inf')

        def is_city_available(self, city_tag, player):
            city = self.environment.map.map.nodes.get(city_tag)
            if city:
                occupancy = len(city.get('owners', []))
                if occupancy < self.current_step:
                    return True
            return False

        async def phase5(self):
            print("Phase 5: Bureaucracy")

            # Request cities_powered from all players
            for player_id, player in self.players.items():
                msg = Message(to=player["jid"])
                msg.body = json.dumps({
                    "phase": "phase5",
                    "action": "power_cities_request"
                })
                await self.send(msg)
                print(f"Requested cities to power from Player {player_id}.")

            # Collect responses
            for player_id, player in self.players.items():
                response = await self.receive(timeout=30)
                if response:
                    data = json.loads(response.body)
                    if data.get("phase") == "phase5" and data.get("action") == "power_cities":
                        cities_powered = data.get("cities_powered", 0)
                        resources_consumed = data.get("resources_consumed", {})
                        updated_elektro = data.get("elektro", 0)

                        # Verify and update player's Elektro
                        expected_income = city_cashback[cities_powered] if cities_powered < len(city_cashback) else \
                        city_cashback[-1]

                        '''
                        actual_income = updated_elektro - player["elektro"]
                        if actual_income != expected_income:
                            print(
                                f"Warning: Player {player_id} reported unexpected income. Expected: {expected_income}, Got: {actual_income}.")
                        player["elektro"] = updated_elektro'''

                        # Deduct consumed resources
                        for resource, amount in resources_consumed.items():
                            if resource in player["resources"]:
                                player["resources"][resource] -= amount
                                if player["resources"][resource] < 0:
                                    player["resources"][resource] = 0  # Prevent negative resources
                                print(f"Player {player_id}: Consumed {amount} of {resource}.")

                        # Update player's powered cities
                        player["cities_powered"] = cities_powered

                        '''
                        print(f"Player {player_id} powered {cities_powered} cities,"
                              f" earned {expected_income} Elektro, "
                              f"and consumed {resources_consumed} resources.")'''

            # Resupply the resource market
            self.resupply_resource_market()
            print("Resupplied the resource market.")

            # Update the power plant market
            self.update_power_plant_market_phase5()
            print("Updated the power plant market.")
            print("Player status before game end check:")
            for player_id, player_data in self.players.items():
                print(
                    f"Player {player_id}: Cities owned = {len(player_data['cities'])}, Cities = {player_data['cities']}")

            # Check for game end conditions
            if self.check_game_end():
                await self.end_game()
            else:
                # Proceed to the next round
                self.current_phase = "phase1"
                self.round += 1
                print(f"Starting Round {self.round}")

        def calculate_income(self, player):
            cities_powered = self.calculate_cities_powered(player)
            income_table = self.environment.city_cashback
            income = income_table[cities_powered] if cities_powered < len(income_table) else income_table[-1]
            print(f"Player {player['jid']} powers {cities_powered} cities and earns {income} elektro.")
            return income

        def calculate_cities_powered(self, player):
            # Determine how many cities the player can power based on resources and power plants
            total_capacity = 0
            for plant in player["power_plants"]:
                resource_types = plant.resource_type
                resource_needed = plant.resource_num
                if not resource_types:  # Eco plants
                    total_capacity += plant.cities
                else:
                    # Check if player has enough resources
                    if plant.is_hybrid:
                        # For hybrid, sum resources
                        total_resources = sum(player["resources"][rtype] for rtype in resource_types)
                        if total_resources >= resource_needed:
                            total_capacity += plant.cities
                    else:
                        rtype = resource_types[0]
                        if player["resources"][rtype] >= resource_needed:
                            total_capacity += plant.cities
            return min(total_capacity, len(player["cities"]))

        def consume_resources(self, player):
            for plant in player["power_plants"]:
                resource_needed = plant.resource_num
                if not plant.resource_type:
                    continue  # Eco-friendly plants consume no resources
                elif plant.is_hybrid:
                    # For hybrid, consume resources from available types
                    for rtype in plant.resource_type:
                        available = player["resources"][rtype]
                        consume = min(resource_needed, available)
                        player["resources"][rtype] -= consume
                        resource_needed -= consume
                        if resource_needed == 0:
                            break
                else:
                    rtype = plant.resource_type[0]
                    if player["resources"][rtype] >= resource_needed:
                        player["resources"][rtype] -= resource_needed

        def resupply_resource_market(self):
            """
            Resupplies the resource market based on the current step, number of players, and resource replenishment table.
            Caps resources at their maximum limits for the market.
            """
            nplayers = len(self.player_jids)
            current_step = self.current_step
            resource_replenishment_table = self.environment.resource_replenishment

            # Ensure valid step and player count
            if current_step not in resource_replenishment_table:
                print(f"Invalid game step: {current_step}. Cannot resupply resources.")
                return

            if nplayers not in resource_replenishment_table[current_step]:
                print(f"Invalid number of players: {nplayers}. Cannot resupply resources.")
                return

            # Get replenishment rates for the current step and number of players
            rates = resource_replenishment_table[current_step][nplayers]
            resource_market = self.environment.resource_market

            # Apply replenishment
            for resource, amount in rates.items():
                current_quantity = resource_market.in_market.get(resource, 0)
                max_quantity = resource_market.max_market.get(resource,
                                                              float('inf'))  # Assume a maximum capacity exists
                new_quantity = min(current_quantity + amount, max_quantity)

                # Update the resource market with the new quantity
                resource_market.in_market[resource] = new_quantity
                print(f"Resupplied {resource}: {current_quantity} -> {new_quantity} (Added: {amount})")

        def update_resource_prices(resource_market, price_table):
            """
            Updates the resource prices in the market based on current quantities.

            :param resource_market: A dictionary containing the quantities of resources in the market.
            :param price_table: A dictionary defining the pricing for each resource based on quantity ranges.
            """
            resource_prices = {}

            for resource, quantity in resource_market.items():
                if resource not in price_table:
                    print(f"No pricing information available for {resource}. Skipping.")
                    continue

                # Uranium has direct mapping, handle it separately
                if resource == "uranium":
                    for qty, price in price_table[resource].items():
                        if quantity >= qty:
                            resource_prices[resource] = price
                            break
                else:
                    # Other resources use ranges
                    for range_key, price in sorted(price_table[resource].items(), reverse=True):
                        if isinstance(range_key, tuple) and range_key[0] <= quantity <= range_key[1]:
                            resource_prices[resource] = price
                            break

            return resource_prices

        def update_power_plant_market_phase5(self):
            # Remove the lowest-numbered power plant from the current market and replace it
            if self.environment.power_plant_market.deck:
                # Remove the lowest-numbered power plant from the current market
                removed_plant = self.environment.power_plant_market.current_market.pop(0)
                # Draw a new power plant from the deck and add it to the future market
                new_plant = self.environment.power_plant_market.deck.pop(0)
                self.environment.power_plant_market.future_market.append(new_plant)
                # Update the markets
                self.environment.power_plant_market.update_markets()

        def check_game_end(self):
            """
            Check if the game has ended by verifying if any player has connected the required number of cities.

            :return: True if the game has ended, False otherwise.
            """
            end_game_cities = self.environment.game_end_cities

            for player_id, player_data in self.players.items():
                num_cities = len(player_data["cities"])
                if num_cities >= end_game_cities:
                    print(
                        f"Game has ended. Player {player_id} has connected {num_cities} cities (required: {end_game_cities}).")
                    return True

            return False

        async def end_game(self):
            print("Game Over. Calculating final scores.")
            # Determine the winner
            max_cities_powered = 0
            winner = None
            for player in self.players.values():
                cities_powered = self.calculate_cities_powered(player)
                if cities_powered > max_cities_powered:
                    max_cities_powered = cities_powered
                    winner = player
                elif cities_powered == max_cities_powered:
                    # Tie-breaker: player with more elektro
                    print("player[elektro]", {player["elektro"]})
                    print("winner[elektro]", {winner["elektro"]})
                    if player["elektro"] > winner["elektro"]:
                        winner = player

            # Announce the winner to all players
            for player in self.players.values():
                msg = Message(to=player["jid"])
                msg.body = json.dumps({
                    "phase": "game_over",
                    "winner": winner["jid"],
                    "final_elektro": winner["elektro"]
                })
                await self.send(msg)
            self.game_over = True



    def __init__(self, jid, password, player_jids):
        super().__init__(jid, password)
        self.player_jids = player_jids

    async def setup(self):
        print("Game Manager agent starting...")
        game_behaviour = self.GameBehaviour(self, self.player_jids)
        self.add_behaviour(game_behaviour)
