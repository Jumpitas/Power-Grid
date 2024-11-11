# game_manager.py

import asyncio
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import json

# Import necessary classes and data structures
from objects import ResourceMarket, PowerPlantMarket
from map_graph import BoardMap, citiesUS, edgesUS
from rule_tables import city_cashback, resource_replenishment, building_cost, step_start_cities, game_end_cities
from game_environment import Environment

class GameManagerAgent(Agent):
    class GameBehaviour(CyclicBehaviour):
        def __init__(self, game_manager, player_jids):
            super().__init__()
            self.game_manager = game_manager
            self.player_jids = player_jids  # List of player JIDs
            self.players = {}  # Will be initialized in the environment
            self.current_phase = "setup"
            self.round = 1
            self.environment = None  # Will be initialized in setup phase
            self.current_step = 1  # Game starts at Step 1
            self.game_over = False

        async def run(self):
            if self.game_over:
                await asyncio.sleep(1)
                return  # Exit the behaviour when the game is over

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

            # Initialize the environment with the number of players
            player_no = len(self.player_jids)
            self.environment = Environment(player_no)

            # Initialize player states from the environment
            for jid, player_name in zip(self.player_jids, self.environment.players.keys()):
                player_data = self.environment.players[player_name]
                self.players[jid] = {
                    "jid": jid,
                    "elektro": player_data['elektro'],
                    "power_plants": player_data['power_plants'],
                    "resources": player_data['resources'],
                    "cities": player_data['cities_owned'],
                    "houses": player_data['houses'],
                    "position": 0,  # Will be updated in phase 1
                    "has_bought_power_plant": False,
                }

            # Use the player order from the environment
            self.player_order = self.environment.order_players.copy()
            # Map player names to JIDs
            self.player_order = [self.player_jids[int(p[-1]) - 1] for p in self.player_order]

            # Update positions based on the initial order
            for index, jid in enumerate(self.player_order):
                self.players[jid]["position"] = index + 1

            # Notify all players about the setup phase completion
            for jid in self.player_jids:
                msg = Message(to=jid)
                msg.body = json.dumps({
                    "phase": "setup",
                    "map": "Map data here",  # You can serialize the map if needed
                    "player_order": self.players[jid]["position"]
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

        def determine_player_order(self):
            # Sort players based on number of cities and largest power plant
            players_list = list(self.players.values())
            players_list.sort(key=lambda p: (-len(p["cities"]), -self.get_largest_power_plant_number(p)))
            return players_list

        def get_largest_power_plant_number(self, player):
            if player["power_plants"]:
                return max(plant.min_bid for plant in player["power_plants"])
            else:
                return 0

        async def phase2(self):
            print("Phase 2: Auction Power Plants")
            # Reset flags
            for player in self.players.values():
                player["has_bought_power_plant"] = False

            # Players take turns starting auctions
            player_order = self.get_players_in_order()
            for player in player_order:
                if player["has_bought_power_plant"]:
                    continue  # Skip if the player already bought a power plant
                await self.handle_auction_for_player(player)

            # Proceed to Phase 3
            self.current_phase = "phase3"
            print("Moving to Phase 3")

        async def handle_auction_for_player(self, player):
            # Send the current power plant market to the player
            current_market_info = [self.serialize_power_plant(pp) for pp in self.environment.power_plant_market.market[:4]]
            msg = Message(to=player["jid"])
            msg.body = json.dumps({
                "phase": "phase2",
                "action": "choose_or_pass",
                "power_plants": current_market_info
            })
            await self.send(msg)

            # Wait for player's response
            response = await self.receive(timeout=30)
            if response and str(response.sender).split('/')[0] == player["jid"]:
                data = json.loads(response.body)
                if data.get("action") == "pass":
                    player["has_bought_power_plant"] = True
                elif data.get("action") == "choose":
                    chosen_number = data.get("power_plant_number")
                    chosen_plant = self.get_power_plant_by_number(chosen_number)
                    if chosen_plant:
                        await self.conduct_auction(chosen_plant, player)
                    else:
                        print(f"Invalid power plant number chosen by {player['jid']}")
                else:
                    print(f"Invalid action received from {player['jid']}")
            else:
                print(f"No response from {player['jid']} in auction phase.")

        def serialize_power_plant(self, power_plant):
            return {
                "min_bid": power_plant.min_bid,
                "cities": power_plant.cities,
                "resource_type": power_plant.resource_type,
                "resource_num": power_plant.resource_num,
                "is_hybrid": power_plant.is_hybrid,
                "is_step": power_plant.is_step
            }

        def get_power_plant_by_number(self, number):
            for plant in self.environment.power_plant_market.market:
                if plant.min_bid == number:
                    return plant
            return None

        async def conduct_auction(self, power_plant, starting_player):
            active_players = [p for p in self.get_players_in_order() if not p["has_bought_power_plant"]]
            current_bid = power_plant.min_bid  # Minimum bid is the power plant's min_bid
            highest_bidder = starting_player
            bidding_active = True

            while bidding_active and len(active_players) > 1:
                for player in active_players:
                    if player["jid"] == highest_bidder["jid"]:
                        continue  # Skip the highest bidder's turn

                    msg = Message(to=player["jid"])
                    msg.body = json.dumps({
                        "phase": "phase2",
                        "action": "bid",
                        "current_bid": current_bid,
                        "power_plant": self.serialize_power_plant(power_plant)
                    })
                    await self.send(msg)

                    # Wait for player's bid
                    response = await self.receive(timeout=15)
                    if response and str(response.sender).split('/')[0] == player["jid"]:
                        data = json.loads(response.body)
                        bid = data.get("bid", 0)
                        if bid > current_bid and bid <= player["elektro"]:
                            current_bid = bid
                            highest_bidder = player
                        else:
                            # Player passes
                            active_players.remove(player)
                    else:
                        print(f"No response or invalid bid from {player['jid']}.")
                        active_players.remove(player)

                if len(active_players) <= 1:
                    bidding_active = False

            # Highest bidder buys the power plant
            highest_bidder["elektro"] -= current_bid

            # Can only have 3 !!!
            highest_bidder["power_plants"].append(power_plant)
            highest_bidder["has_bought_power_plant"] = True
            # Remove the power plant from the market
            self.environment.power_plant_market.market.remove(power_plant)
            # Draw a new power plant from the deck to replace it
            if self.environment.power_plant_market.deck:
                new_plant = self.environment.power_plant_market.deck.pop(0)
                self.environment.power_plant_market.market.append(new_plant)
                # Re-sort the market
                self.environment.power_plant_market.market.sort(key=lambda pp: pp.min_bid)

            # Notify players of the auction result
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

        def get_players_in_order(self):
            # Return a list of player dictionaries sorted by their position
            sorted_players = sorted(
                self.players.values(),
                key=lambda p: p["position"]
            )
            return sorted_players

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
                data = json.loads(response.body)

                # is the player buying resources implemented?
                purchases = data.get("purchases", {})
                total_cost = 0
                for resource, amount in purchases.items():
                    price = self.calculate_resource_price(resource, amount)
                    if price <= player["elektro"] and amount <= self.environment.resource_market.in_market[resource]:
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
            for _ in range(amount):
                price = resource_market.resource_price(resource)
                if price is not None:
                    total_price += price
                    resource_market.in_market[resource] -= 1
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
                data = json.loads(response.body)
                cities_to_build = data.get("cities", [])
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
            # Players earn income and resources are replenished
            for player in self.players.values():
                income = self.calculate_income(player)
                player["elektro"] += income
                self.consume_resources(player)

            self.resupply_resource_market()

            # Update the power plant market
            self.update_power_plant_market_phase5()

            # Check for game end conditions
            if self.check_game_end():
                await self.end_game()
            else:
                # Proceed to the next round
                self.current_phase = "phase1"
                self.round += 1
                print(f"Starting Round {self.round}")

        def calculate_income(self, player):
            # Calculate income based on the number of cities powered
            cities_powered = self.calculate_cities_powered(player)
            income_table = self.environment.city_cashback
            if cities_powered < len(income_table):
                return income_table[cities_powered]
            else:
                return income_table[-1]

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
            # Deduct resources used for powering cities
            for plant in player["power_plants"]:
                resource_types = plant.resource_type
                resource_needed = plant.resource_num
                if not resource_types:
                    continue  # Eco plants consume no resources
                else:
                    if plant.is_hybrid:
                        # For hybrid, consume resources from available types
                        for rtype in resource_types:
                            available = player["resources"][rtype]
                            consume = min(available, resource_needed)
                            player["resources"][rtype] -= consume
                            resource_needed -= consume
                            if resource_needed == 0:
                                break
                    else:
                        rtype = resource_types[0]
                        if player["resources"][rtype] >= resource_needed:
                            player["resources"][rtype] -= resource_needed

        def resupply_resource_market(self):
            # Resupply resources based on the current step and number of players
            nplayers = len(self.player_jids)
            rates = self.environment.resource_replenishment[self.current_step]
            for resource, amount in rates.items():
                self.environment.resource_market.in_market[resource] += amount
                # Cap at maximum (not implemented here)

        def update_power_plant_market_phase5(self):
            # Remove the lowest-numbered power plant and replace it
            if self.environment.power_plant_market.deck:
                self.environment.power_plant_market.market.pop(0)
                new_plant = self.environment.power_plant_market.deck.pop(0)
                self.environment.power_plant_market.market.append(new_plant)
                self.environment.power_plant_market.market.sort(key=lambda pp: pp.min_bid)

        def check_game_end(self):
            # Game ends when a player connects a certain number of cities
            nplayers = len(self.player_jids)
            end_game_cities = self.environment.game_end_cities
            for player in self.players.values():
                if len(player["cities"]) >= end_game_cities:
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

        def get_players_in_reverse_order(self):
            # Return a list of player dictionaries sorted by their position in reverse
            sorted_players = sorted(
                self.players.values(),
                key=lambda p: p["position"],
                reverse=True
            )
            return sorted_players

    def __init__(self, jid, password, player_jids):
        super().__init__(jid, password)
        self.player_jids = player_jids

    async def setup(self):
        print("Game Manager agent starting...")
        game_behaviour = self.GameBehaviour(self, self.player_jids)
        self.add_behaviour(game_behaviour)