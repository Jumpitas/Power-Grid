# game_manager_agent.py

import asyncio
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import json

# Import necessary classes and data structures
from objects import ResourceMarket, PowerPlantMarket, PowerPlant
from map_graph import BoardMap, citiesUS, edgesUS
from rule_tables import city_cashback, resource_replenishment, building_cost, step_start_cities, game_end_cities
# Note: Ensure that 'rule_tables' contains the necessary data structures.

class GameManagerAgent(Agent):
    class GameBehaviour(CyclicBehaviour):
        def __init__(self, game_manager, player_jids):
            super().__init__()
            self.game_manager = game_manager
            self.player_jids = player_jids  # List of player JIDs
            self.players = {}  # Will be initialized in the environment
            self.current_phase = "setup"
            self.round = 1
            self.current_step = 1  # Game starts at Step 1
            self.game_over = False

            # Initialize the PowerPlantMarket
            self.power_plant_market = PowerPlantMarket(len(player_jids))

            # Initialize the ResourceMarket
            self.resource_market = ResourceMarket()

            # Initialize the Map
            self.map = BoardMap(citiesUS, edgesUS)

            # Other game-related variables
            self.city_cashback = city_cashback
            self.resource_replenishment = resource_replenishment
            self.building_cost = building_cost
            self.game_end_cities = game_end_cities

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
            # Initialize player states
            self.jid_to_player_name = {}
            self.player_name_to_jid = {}
            for jid in self.player_jids:
                player_name = jid.split('@')[0]  # Extract player name from JID
                self.jid_to_player_name[jid] = player_name
                self.player_name_to_jid[player_name] = jid

                # Initialize player data
                self.players[jid] = {
                    "jid": jid,
                    "name": player_name,
                    "elektro": 50,  # Starting money
                    "power_plants": [],
                    "resources": {"coal": 0, "oil": 0, "garbage": 0, "uranium": 0},
                    "cities": [],
                    "houses": 22,  # Each player has 22 houses
                    "position": None,
                    "has_bought_power_plant": False
                }

            # Determine initial player order randomly
            import random
            shuffled_jids = self.player_jids.copy()
            random.shuffle(shuffled_jids)
            for index, jid in enumerate(shuffled_jids):
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

        async def phase2(self):
            print("Phase 2: Auction Power Plants")
            # Reset players' auction status
            for player in self.players.values():
                player["has_bought_power_plant"] = False

            # Players take turns starting auctions based on player_order
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
            available_power_plants = [self.serialize_power_plant(pp) for pp in self.power_plant_market.current_market]

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
                except json.JSONDecodeError:
                    print(f"Invalid JSON response from {player['jid']}. Treating as pass.")
                    choice = "pass"
                else:
                    choice = data.get("choice", "pass")
            else:
                print(f"No response from {player['jid']}. Treating as pass.")
                choice = "pass"

            if choice == "pass" and can_pass:
                player["has_bought_power_plant"] = True
                print(f"{player['jid']} chooses to pass on starting an auction.")
            elif choice == "auction":
                chosen_number = data.get("power_plant_number", None)
                chosen_plant = self.get_power_plant_by_number(chosen_number)
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

                # Handle discard if necessary
                if len(highest_bidder["power_plants"]) > 3:
                    await self.handle_power_plant_discard(highest_bidder)

                # Update the power plant market
                self.power_plant_market.remove_plant_from_market(power_plant)
                self.power_plant_market.update_markets()

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
            for plant in self.power_plant_market.current_market:
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
            # Placeholder: Skipping Phase 3
            # Notify players that Phase 3 is skipped
            for jid in self.player_jids:
                msg = Message(to=jid)
                msg.body = json.dumps({
                    "phase": "phase3",
                    "action": "buy_resources",
                    "resource_market": {},  # Empty since skipped
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
                    resource_market.in_market[resource] -= 1
                else:
                    print(f"Not enough {resource} available.")
                    break
            return total_price

        async def phase4(self):
            print("Phase 4: Build Houses")
            # Placeholder: Skipping Phase 4
            # Notify players that Phase 4 is skipped
            for jid in self.player_jids:
                msg = Message(to=jid)
                msg.body = json.dumps({
                    "phase": "phase4",
                    "action": "build_houses",
                    "map_status": {},  # Empty since skipped
                    "step": self.current_step
                })
                await self.send(msg)
            # Proceed to Phase 5
            self.current_phase = "phase5"
            print("Phase 4 is skipped. Moving to Phase 5")

        async def phase5(self):
            print("Phase 5: Bureaucracy")
            # Placeholder: Skipping Phase 5
            # Notify players that Phase 5 is skipped
            for jid in self.player_jids:
                msg = Message(to=jid)
                msg.body = json.dumps({
                    "phase": "phase5",
                    "action": "bureaucracy",
                })
                await self.send(msg)
            # Check for game end conditions
            if self.check_game_end():
                await self.end_game()
            else:
                # Proceed to the next round
                self.current_phase = "phase1"
                self.round += 1
                print(f"Starting Round {self.round}")

        def check_game_end(self):
            # Game ends when a player connects a certain number of cities
            nplayers = len(self.player_jids)
            end_game_cities = self.game_end_cities.get(nplayers, 17)  # Default to 17 if not specified
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
                cities_powered = len(player["cities"])  # Since we skipped resource phases
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

    def __init__(self, jid, password, player_jids):
        super().__init__(jid, password)
        self.player_jids = player_jids

    async def setup(self):
        print("Game Manager agent starting...")
        game_behaviour = self.GameBehaviour(self, self.player_jids)
        self.add_behaviour(game_behaviour)
