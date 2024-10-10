# game_manager_agent.py

import asyncio
from spade.agent import Agent
from spade.behaviour import FSMBehaviour, State
from spade.message import Message
from map_graph import BoardMap, citiesUS, edgesUS
from objects import PowerPlant, power_plant_deck
from rule_tables import (
    city_cashback,
    resource_replenishment,
    step_start_cities,
    game_end_cities,
    resource_max_quantities,
    building_cost
)
import random
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

class GameManagerAgent(Agent):
    def __init__(self, jid, password, player_jids):
        super().__init__(jid, password)
        self.player_jids = player_jids  # List of player agent JIDs

        # Initialize game components
        self.initialize_game()

    def initialize_game(self):
        # Rule tables
        self.city_cashback = city_cashback
        self.resource_replenishment = resource_replenishment
        self.step_start_cities = step_start_cities
        self.game_end_cities = game_end_cities
        self.building_cost = building_cost

        # Initialize game variables
        self.step = 1  # Game starts at Step 1
        self.current_phase = 1  # Start with Phase 1
        self.player_cities = {}  # Player connected cities
        self.player_highest_plants = {}
        self.powered_cities = {}  # Player powered cities
        self.player_states = {}  # Player states: resources, power plants, money, houses
        for player_jid in self.player_jids:
            self.player_states[player_jid] = {
                'elektro': 50,
                'resources': {'coal': 0, 'oil': 0, 'garbage': 0, 'uranium': 0},
                'power_plants': [],
                'houses': [],
            }
        self.power_plant_deck = []
        self.current_market = []
        self.future_market = []
        self.resource_market = {
            "coal": {"price": 1, "quantity": 24},
            "oil": {"price": 3, "quantity": 18},
            "garbage": {"price": 7, "quantity": 6},
            "uranium": {"price": 14, "quantity": 2}
        }
        self.map = BoardMap(citiesUS, edgesUS)

        # Initialize the power plant market
        self.initialize_power_plants()

    async def setup(self):
        print("Game manager agent starting...")
        game_behaviour = GameBehaviour()
        game_behaviour.add_state(name="PHASE_1", state=Phase1DeterminePlayerOrder(), initial=True)
        game_behaviour.add_state(name="PHASE_2", state=Phase2AuctionPowerPlants())
        game_behaviour.add_state(name="PHASE_3", state=Phase3BuyResources())
        game_behaviour.add_state(name="PHASE_4", state=Phase4BuildHouses())
        game_behaviour.add_state(name="PHASE_5", state=Phase5Bureaucracy())

        # Add transitions between states
        game_behaviour.add_transition(source="PHASE_1", dest="PHASE_2")
        game_behaviour.add_transition(source="PHASE_2", dest="PHASE_3")
        game_behaviour.add_transition(source="PHASE_3", dest="PHASE_4")
        game_behaviour.add_transition(source="PHASE_4", dest="PHASE_5")
        game_behaviour.add_transition(source="PHASE_5", dest="PHASE_1")  # Loop back to PHASE_1

        self.add_behaviour(game_behaviour)

    def initialize_power_plants(self):
        # Use the power_plant_deck from objects.py
        self.power_plant_deck = power_plant_deck.copy()
        # Shuffle the deck
        random.shuffle(self.power_plant_deck)

        # Initialize a special object for Step 3 (doesn't use PowerPlant class)
        self.step3_card = PowerPlant(min_bid=None, cities=None, name="Step3")

        # Insert the Step 3 card into the deck; adjust position as needed
        self.power_plant_deck.insert(len(self.power_plant_deck) // 2, self.step3_card)

        # Initialize the market
        self.current_market = []
        self.future_market = []

        # Draw 8 cards to fill the market
        for _ in range(8):
            self.draw_power_plant()

        # Sort the market
        self.update_markets()

    def draw_power_plant(self):
        if self.power_plant_deck:
            plant = self.power_plant_deck.pop(0)
            if plant.name == "Step3":
                self.step = 3
                logging.info("Step 3 has begun!")
                self.remove_lowest_power_plant()
            else:
                self.future_market.append(plant)
        else:
            logging.warning("Power plant deck is empty!")

    def update_markets(self):
        # Combine current and future markets
        all_market = self.current_market + self.future_market
        # Remove Step 3 card from the combined market
        all_market = [plant for plant in all_market if not (plant.name == "Step3")]

        # Sort all_market by plant min_bid
        all_market.sort(key=lambda x: x.min_bid if isinstance(x.min_bid, int) else float('inf'))

        # First four plants are in the current market, the rest go to future market
        self.current_market = all_market[:4]
        self.future_market = all_market[4:]

    def remove_lowest_power_plant(self):
        if self.current_market:
            lowest_plant = min(self.current_market, key=lambda x: x.min_bid if isinstance(x.min_bid, int) else float('inf'))
            self.current_market.remove(lowest_plant)
            logging.info(f"Removed lowest power plant from market: {lowest_plant.min_bid}")
        else:
            logging.warning("No power plants to remove from the current market.")

    def get_power_plant_cost(self, plant_number):
        for plant in self.current_market:
            if plant.min_bid == plant_number:
                return plant.min_bid
        return None

    def remove_power_plant_from_market(self, plant_number):
        self.current_market = [
            plant for plant in self.current_market if plant.min_bid != plant_number
        ]

    def get_resource_max_quantity(self, resource_type):
        return resource_max_quantities.get(resource_type, 24)

    def build_house(self, player_jid, cities):
        success = True
        for city in cities:
            if not self.map.update_owner(player_jid, city):
                success = False
                logging.error(f"Failed to update owner for city {city} by {player_jid}")
                continue  # Continue processing other cities
            self.player_states[player_jid]['houses'].append(city)
            self.player_cities[player_jid] = self.player_cities.get(player_jid, 0) + 1
            logging.info(f"Player {player_jid} built in city {city}")
        return success


class GameBehaviour(FSMBehaviour):
    async def on_start(self):
        logging.info("GameBehaviour starting...")

    async def on_end(self):
        logging.info("GameBehaviour finished.")

# Define states for the FSM

class Phase1DeterminePlayerOrder(State):
    async def run(self):
        game_manager = self.agent
        players = game_manager.player_jids
        game_manager.player_cities = {}  # Reset
        game_manager.player_highest_plants = {}

        logging.info("Phase 1: Determine Player Order")

        # Request the number of connected cities from each player
        for player_jid in players:
            msg = Message(to=player_jid)
            msg.body = "REQUEST_CITIES"
            await self.send(msg)

        # Request the highest power plant from each player for tiebreakers
        for player_jid in players:
            msg = Message(to=player_jid)
            msg.body = "REQUEST_HIGHEST_PLANT"
            await self.send(msg)

        # Collect responses for connected cities
        for _ in players:
            msg = await self.receive(timeout=15)
            if msg and msg.body.startswith("CITIES:"):
                try:
                    num_cities = int(msg.body.split(":")[1])
                    player_jid = str(msg.sender).split('/')[0]
                    game_manager.player_cities[player_jid] = num_cities
                    logging.info(f"Received {num_cities} cities from {player_jid}")
                except ValueError:
                    logging.error(f"Invalid CITIES message from {msg.sender}: {msg.body}")

        # Collect responses for highest power plant
        for _ in players:
            msg = await self.receive(timeout=15)
            if msg and msg.body.startswith("HIGHEST_PLANT:"):
                try:
                    highest_plant = int(msg.body.split(":")[1])
                    player_jid = str(msg.sender).split('/')[0]
                    game_manager.player_highest_plants[player_jid] = highest_plant
                    logging.info(f"Received highest power plant {highest_plant} from {player_jid}")
                except ValueError:
                    logging.error(f"Invalid HIGHEST_PLANT message from {msg.sender}: {msg.body}")

        # Determine player order based on number of cities and tiebreakers
        sorted_players = sorted(
            game_manager.player_jids,
            key=lambda jid: (
                game_manager.player_cities.get(jid, 0),
                game_manager.player_highest_plants.get(jid, 0)
            ),
            reverse=True
        )

        game_manager.player_jids = sorted_players
        logging.info(f"Determined player order: {game_manager.player_jids}")

        # Notify players of the new order
        for idx, player_jid in enumerate(game_manager.player_jids):
            msg = Message(to=player_jid)
            msg.body = "PHASE_1:ORDER_DETERMINED"
            msg.set_metadata("phase", "PHASE_1")
            msg.set_metadata("player_order", str(idx + 1))
            await self.send(msg)
            logging.info(f"Notified {player_jid} of their order position {idx + 1}")

        await asyncio.sleep(1)  # Yield control to event loop
        self.set_next_state("PHASE_2")

class Phase2AuctionPowerPlants(State):
    async def run(self):
        game_manager = self.agent
        logging.info("Phase 2: Auction Power Plants")

        # Apply discount token to the lowest-numbered power plant in the current market
        if game_manager.current_market:
            discounted_plant = min(
                game_manager.current_market,
                key=lambda x: x.min_bid if isinstance(x.min_bid, int) else float('inf')
            )
            discounted_plant.discounted = True
            logging.info(f"Discount token applied to power plant {discounted_plant.min_bid}")
        else:
            logging.warning("Current market is empty. No discount token applied.")

        # Notify players of the current power plant market
        market_info = json.dumps([plant.to_dict() for plant in game_manager.current_market])
        for player_jid in game_manager.player_jids:
            msg = Message(to=player_jid)
            msg.body = f"PHASE_2:{market_info}"
            msg.set_metadata("phase", "PHASE_2")
            await self.send(msg)
            logging.info(f"Sent PHASE_2 market info to {player_jid}")

        await asyncio.sleep(1)  # Allow time for messages to be received

        # Auction logic for each player in order
        for player_jid in game_manager.player_jids:
            # Check if the player has already purchased the maximum allowed power plants this round
            if len(game_manager.player_states[player_jid]['power_plants']) >= 3:
                logging.info(f"{player_jid} has already purchased maximum power plants.")
                continue

            # Request auction choice from the player
            msg = Message(to=player_jid)
            msg.body = "CHOOSE_PLANT"
            msg.set_metadata("phase", "PHASE_2")
            await self.send(msg)
            logging.info(f"Requested auction choice from {player_jid}")

            # Receive player's choice
            choice_msg = await self.receive(timeout=20)
            if choice_msg and choice_msg.body.startswith("AUCTION:"):
                try:
                    plant_number = int(choice_msg.body.split(":")[1])
                    power_plant = next((plant for plant in game_manager.current_market if plant.min_bid == plant_number), None)
                    if power_plant:
                        # Conduct the auction for the chosen power plant
                        await self.conduct_auction(plant_number, player_jid)
                    else:
                        logging.error(f"Power plant {plant_number} not found in current market.")
                        # Notify player of invalid choice
                        failure_msg = Message(to=player_jid)
                        failure_msg.body = f"AUCTION_FAILED:{plant_number}:Power plant not available"
                        await self.send(failure_msg)
                except ValueError:
                    logging.error(f"Invalid AUCTION message from {player_jid}: {choice_msg.body}")
            else:
                logging.warning(f"No valid AUCTION message received from {player_jid}.")

        # After all players have had their turn in Phase 2, reset discount tokens
        if game_manager.current_market:
            for plant in game_manager.current_market:
                if hasattr(plant, 'discounted') and plant.discounted:
                    del plant.discounted
        logging.info("Phase 2 completed. Moving to Phase 3.")
        self.set_next_state("PHASE_3")

    async def conduct_auction(self, plant_number, starting_player_jid):
        game_manager = self.agent
        logging.info(f"Starting auction for power plant {plant_number} initiated by {starting_player_jid}")

        bidders = game_manager.player_jids.copy()
        if starting_player_jid in bidders:
            starting_index = bidders.index(starting_player_jid)
            bidders = bidders[starting_index:] + bidders[:starting_index]
        current_bid = 1  # Starting bid
        highest_bidder = None
        active_bidders = set(bidders)
        passed_bidders = set()

        power_plant = next((plant for plant in game_manager.current_market if plant.min_bid == plant_number), None)
        if not power_plant:
            logging.error(f"Power plant {plant_number} not found in current market.")
            return

        min_bid = 1 if getattr(power_plant, 'discounted', False) else power_plant.min_bid
        current_bid = min_bid

        while len(active_bidders) - len(passed_bidders) > 1:
            for bidder in list(active_bidders):
                if bidder in passed_bidders:
                    continue

                # Send BID_REQUEST
                bid_request = Message(to=bidder)
                bid_request.body = f"BID_REQUEST:{plant_number}:{current_bid}"
                bid_request.set_metadata("phase", "PHASE_2")
                await self.send(bid_request)
                logging.info(f"Requested bid from {bidder} for power plant {plant_number} with current bid {current_bid}")

                # Receive bid
                bid_msg = await self.receive(timeout=20)
                if bid_msg and bid_msg.body.startswith("BID:"):
                    try:
                        bid_amount = int(bid_msg.body.split(":")[1])
                        if bid_amount > current_bid:
                            current_bid = bid_amount
                            highest_bidder = bidder
                            logging.info(f"New highest bid: {current_bid} by {highest_bidder}")
                        else:
                            passed_bidders.add(bidder)
                            logging.info(f"{bidder} passed with bid {bid_amount}")
                    except ValueError:
                        passed_bidders.add(bidder)
                        logging.error(f"Invalid BID message from {bidder}: {bid_msg.body}")
                else:
                    passed_bidders.add(bidder)
                    logging.warning(f"{bidder} did not respond. They have passed.")

                # Check if auction can end
                if len(active_bidders) - len(passed_bidders) <= 1:
                    break

        # Determine the winner
        remaining_bidders = active_bidders - passed_bidders
        if remaining_bidders:
            winner = remaining_bidders.pop()
            logging.info(f"Auction won by {winner} with bid {current_bid}")

            # Deduct Elektro from the winner
            game_manager.player_states[winner]['elektro'] -= current_bid

            # Assign the power plant to the winner
            game_manager.player_states[winner]['power_plants'].append(power_plant.min_bid)

            # Send AUCTION_WIN message to the winner
            auction_win_msg = Message(to=winner)
            auction_win_msg.body = f"AUCTION_WIN:{power_plant.min_bid}:{current_bid}"
            auction_win_msg.set_metadata("phase", "PHASE_2")
            await self.send(auction_win_msg)
            logging.info(f"Sent AUCTION_WIN to {winner} for power plant {power_plant.min_bid} with bid {current_bid}")

            # Remove the power plant from the current market
            game_manager.current_market.remove(power_plant)

            # Draw a new power plant to replace it
            game_manager.draw_power_plant()

            # Update the markets
            game_manager.update_markets()
        else:
            logging.info("No bidders remained. Auction ended without a winner.")
            # Optionally, handle the power plant being returned to the market or discarded

class Phase3BuyResources(State):
    async def run(self):
        game_manager = self.agent
        logging.info("Phase 3: Buy Resources")

        # Serialize the resource market
        resource_market_info = json.dumps(game_manager.resource_market)
        # Reverse player order for this phase
        reversed_players = game_manager.player_jids[::-1]

        for player_jid in reversed_players:
            msg = Message(to=player_jid)
            msg.body = f"PHASE_3:{resource_market_info}"
            msg.set_metadata("phase", "PHASE_3")
            await self.send(msg)
            logging.info(f"Sent PHASE_3 resource market info to {player_jid}")

            # Receive resource purchase from the player
            purchase_msg = await self.receive(timeout=30)
            if purchase_msg and purchase_msg.body.startswith("BUY_RESOURCES:"):
                try:
                    resources = json.loads(purchase_msg.body.split(":", 1)[1])
                    # Process resource purchases
                    await self.process_resource_purchase(player_jid, resources)
                except json.JSONDecodeError:
                    logging.error(f"Invalid BUY_RESOURCES message from {player_jid}: {purchase_msg.body}")
            else:
                logging.warning(f"No valid BUY_RESOURCES message received from {player_jid}.")

        logging.info("Phase 3 completed. Moving to Phase 4.")
        self.set_next_state("PHASE_4")

    async def process_resource_purchase(self, player_jid, resources):
        game_manager = self.agent
        player_state = game_manager.player_states[player_jid]
        storage_limits = self.calculate_storage_limits(player_state)
        resource_prices = self.get_dynamic_resource_prices()

        for resource_type, amount in resources.items():
            if resource_type not in game_manager.resource_market:
                logging.error(f"Invalid resource type '{resource_type}' requested by {player_jid}")
                # Send failure message to player
                failure_msg = Message(to=player_jid)
                failure_msg.body = f"PURCHASE_FAILED:{resource_type}:Invalid resource type"
                await self.send(failure_msg)
                continue

            # Calculate available storage
            available_storage = storage_limits.get(resource_type, 0) - player_state['resources'].get(resource_type, 0)
            if available_storage <= 0:
                logging.info(f"{player_jid} has no storage available for {resource_type}")
                # Send failure message
                failure_msg = Message(to=player_jid)
                failure_msg.body = f"PURCHASE_FAILED:{resource_type}:No storage available"
                await self.send(failure_msg)
                continue

            # Adjust amount based on available storage
            purchasable_amount = min(amount, available_storage, game_manager.resource_market[resource_type]['quantity'])
            if purchasable_amount <= 0:
                logging.info(f"{player_jid} cannot purchase any {resource_type}")
                # Send failure message
                failure_msg = Message(to=player_jid)
                failure_msg.body = f"PURCHASE_FAILED:{resource_type}:Cannot purchase any"
                await self.send(failure_msg)
                continue

            # Calculate total cost
            price = resource_prices.get(resource_type, game_manager.resource_market[resource_type]['price'])
            total_cost = price * purchasable_amount

            if player_state['elektro'] < total_cost:
                purchasable_amount = player_state['elektro'] // price
                if purchasable_amount <= 0:
                    logging.info(f"{player_jid} does not have enough Elektro to buy {resource_type}")
                    # Send failure message
                    failure_msg = Message(to=player_jid)
                    failure_msg.body = f"PURCHASE_FAILED:{resource_type}:Not enough Elektro"
                    await self.send(failure_msg)
                    continue
                total_cost = price * purchasable_amount

            # Update resource market and player state
            game_manager.resource_market[resource_type]['quantity'] -= purchasable_amount
            player_state['resources'][resource_type] += purchasable_amount
            player_state['elektro'] -= total_cost

            # Send confirmation to player
            confirmation_msg = Message(to=player_jid)
            confirmation_msg.body = f"PURCHASE_CONFIRMED:{resource_type}:{purchasable_amount}"
            await self.send(confirmation_msg)
            logging.info(f"{player_jid} purchased {purchasable_amount} {resource_type} for {total_cost} Elektro")

    def calculate_storage_limits(self, player_state):
        storage_limits = {'coal': 0, 'oil': 0, 'garbage': 0, 'uranium': 0}
        for plant_number in player_state['power_plants']:
            # Fetch power plant details using GameManagerAgent's method
            plant_details = self.agent.get_power_plant_details(plant_number)
            if not plant_details:
                continue
            resource_type = plant_details['resource_type']
            if isinstance(resource_type, list):  # Hybrid plant
                for res in resource_type:
                    storage_limits[res] += plant_details['resource_num'] * 2
            elif resource_type:  # Non-ecological plant
                storage_limits[resource_type] += plant_details['resource_num'] * 2
            # Ecological plants do not require resources
        return storage_limits

    def get_dynamic_resource_prices(self):
        # Implement dynamic pricing based on current resource market
        # For simplicity, assume prices increase as quantity decreases
        prices = {}
        for resource, info in self.agent.resource_market.items():
            if info['quantity'] >= 18:
                prices[resource] = 1
            elif 10 <= info['quantity'] < 18:
                prices[resource] = 2
            elif 5 <= info['quantity'] < 10:
                prices[resource] = 3
            elif 1 <= info['quantity'] < 5:
                prices[resource] = 4
            else:
                prices[resource] = float('inf')  # Resource unavailable
        return prices

    def calculate_storage_limits(self, player_state):
        storage_limits = {'coal': 0, 'oil': 0, 'garbage': 0, 'uranium': 0}
        for plant_number in player_state['power_plants']:
            # Fetch power plant details (assuming a method or external data source)
            plant_details = self.get_power_plant_details(plant_number)
            if not plant_details:
                continue
            resource_type = plant_details['resource_type']
            if isinstance(resource_type, list):  # Hybrid plant
                for res in resource_type:
                    storage_limits[res] += plant_details['resource_num'] * 2
            elif resource_type:  # Non-ecological plant
                storage_limits[resource_type] += plant_details['resource_num'] * 2
            # Ecological plants do not require resources
        return storage_limits

    def get_dynamic_resource_prices(self):
        # Implement dynamic pricing based on current resource market
        # For simplicity, assume prices increase as quantity decreases
        prices = {}
        for resource, info in self.resource_market.items():
            if info['quantity'] >= 18:
                prices[resource] = 1
            elif 10 <= info['quantity'] < 18:
                prices[resource] = 2
            elif 5 <= info['quantity'] < 10:
                prices[resource] = 3
            elif 1 <= info['quantity'] < 5:
                prices[resource] = 4
            else:
                prices[resource] = float('inf')  # Resource unavailable
        return prices

    def get_power_plant_details(self, plant_number):
        # Placeholder for fetching power plant details
        # This should return a dictionary with 'resource_type' and 'resource_num'
        # based on the power plant number
        # Example:
        # { 'resource_type': 'coal', 'resource_num': 2 }
        # or for hybrid: { 'resource_type': ['coal', 'oil'], 'resource_num': 2 }
        # For ecological plants, 'resource_type' is None or empty
        for plant in self.current_market + self.future_market:
            if plant.min_bid == plant_number:
                return {
                    'resource_type': plant.resource_type,  # Assuming 'resource_type' attribute exists
                    'resource_num': plant.resource_num     # Assuming 'resource_num' attribute exists
                }
        return None

class Phase4BuildHouses(State):
    async def run(self):
        game_manager = self.agent
        logging.info("Phase 4: Build Houses")

        # Serialize the full map data including connections and ownership
        map_info = json.dumps(game_manager.map.to_dict())

        for player_jid in game_manager.player_jids:
            msg = Message(to=player_jid)
            msg.body = f"PHASE_4:{map_info}"
            msg.set_metadata("phase", "PHASE_4")
            await self.send(msg)
            logging.info(f"Sent PHASE_4 map info to {player_jid}")

        await asyncio.sleep(1)  # Allow time for messages to be received

        # Process building actions from players
        for player_jid in reversed(game_manager.player_jids):
            # Receive building action
            build_msg = await self.receive(timeout=20)
            if build_msg and build_msg.body.startswith("BUILD_HOUSES:"):
                try:
                    cities_to_build = json.loads(build_msg.body.split(":", 1)[1])
                    success = game_manager.build_house(player_jid, cities_to_build)
                    if success:
                        # Send BUILD_CONFIRMED message
                        confirm_msg = Message(to=player_jid)
                        confirm_msg.body = f"BUILD_CONFIRMED:{cities_to_build}"
                        await self.send(confirm_msg)
                        logging.info(f"{player_jid} successfully built in {cities_to_build}")
                    else:
                        # Send BUILD_FAILED message
                        fail_msg = Message(to=player_jid)
                        fail_msg.body = f"BUILD_FAILED:{cities_to_build}:Cannot build in city"
                        await self.send(fail_msg)
                        logging.warning(f"{player_jid} failed to build in {cities_to_build}")
                except json.JSONDecodeError:
                    logging.error(f"Invalid BUILD_HOUSES message from {player_jid}: {build_msg.body}")
            else:
                logging.warning(f"No valid BUILD_HOUSES message received from {player_jid}.")

        logging.info("Phase 4 completed. Moving to Phase 5.")
        self.set_next_state("PHASE_5")

class Phase5Bureaucracy(State):
    async def run(self):
        game_manager = self.agent
        logging.info("Phase 5: Bureaucracy")

        # Step 1: Earning cash
        game_manager.powered_cities = {}  # Reset
        for player_jid in game_manager.player_jids:
            # Request from players how many cities they can power
            msg = Message(to=player_jid)
            msg.body = "REQUEST_POWER"
            msg.set_metadata("phase", "PHASE_5")
            await self.send(msg)
            logging.info(f"Requested POWERED_CITIES from {player_jid}")

        # Collect responses
        for _ in game_manager.player_jids:
            msg = await self.receive(timeout=30)
            if msg and msg.body.startswith("POWERED_CITIES:"):
                try:
                    num_cities = int(msg.body.split(":")[1])
                    player_jid = str(msg.sender).split('/')[0]
                    game_manager.powered_cities[player_jid] = num_cities
                    logging.info(f"Player {player_jid} can power {num_cities} cities.")

                    # Calculate income
                    income = game_manager.city_cashback.get(num_cities, 10)  # Default to 10 if not found
                    game_manager.player_states[player_jid]['elektro'] += income

                    # Deduct resources used for powering
                    await self.consume_resources(player_jid, num_cities)

                    # Send earnings confirmation
                    earnings_msg = Message(to=player_jid)
                    earnings_msg.body = f"EARNINGS:{income}"
                    await self.send(earnings_msg)
                    logging.info(f"Player {player_jid} earned {income} Elektro.")
                except ValueError:
                    logging.error(f"Invalid POWERED_CITIES message from {msg.sender}: {msg.body}")
            else:
                logging.warning(f"No valid POWERED_CITIES message received from a player.")

        # Step 2: Resupply the resource market
        self.replenish_resources()
        logging.info("Resource market replenished.")

        # Step 3: Update the power plant market
        self.update_power_plant_market()
        logging.info("Power plant market updated.")

        # Step 4: Check for step changes
        self.check_step_change()

        # Step 5: Check for game end condition
        game_ended, winner = self.check_game_end()
        if game_ended:
            logging.info(f"Game has ended! Winner: {winner}")
            for player_jid in game_manager.player_jids:
                msg = Message(to=player_jid)
                msg.body = "GAME_END"
                msg.set_metadata("winner", winner)
                await self.send(msg)
                logging.info(f"Sent GAME_END to {player_jid} with winner: {winner}")
            await self.agent.stop()
        else:
            logging.info("Phase 5 completed. Looping back to Phase 1.")
            self.set_next_state("PHASE_1")

    async def consume_resources(self, player_jid, num_cities_powered):
        game_manager = self.agent
        player_state = game_manager.player_states[player_jid]
        power_plants = player_state['power_plants']
        resources = player_state['resources']

        consumed_resources = {'coal': 0, 'oil': 0, 'garbage': 0, 'uranium': 0}
        sorted_plants = sorted(power_plants, reverse=True)

        for plant_number in sorted_plants:
            if num_cities_powered <= 0:
                break
            plant_details = game_manager.get_power_plant_details(plant_number)
            if not plant_details:
                continue
            resource_type = plant_details['resource_type']
            resource_num = plant_details['resource_num']

            if not resource_type:
                num_cities_powered -= plant_details['capacity']
                continue

            if isinstance(resource_type, list):
                for res in resource_type:
                    if resources.get(res, 0) >= resource_num:
                        resources[res] -= resource_num
                        consumed_resources[res] += resource_num
                        num_cities_powered -= plant_details['capacity']
                        break
            else:
                if resources.get(resource_type, 0) >= resource_num:
                    resources[resource_type] -= resource_num
                    consumed_resources[resource_type] += resource_num
                    num_cities_powered -= plant_details['capacity']

        logging.info(f"Player {player_jid} consumed resources: {consumed_resources}")

    def replenish_resources(self):
        game_manager = self.agent
        number_of_players = len(game_manager.player_jids)
        step = game_manager.step
        replenishment = game_manager.resource_replenishment.get(step, {}).get(number_of_players, {})
        for resource_type, amount in replenishment.items():
            # Add resources back to the resource market
            current_quantity = game_manager.resource_market.get(resource_type, {}).get('quantity', 0)
            max_quantity = self.agent.get_resource_max_quantity(resource_type)
            new_quantity = current_quantity + amount
            if new_quantity > max_quantity:
                new_quantity = max_quantity
            game_manager.resource_market[resource_type]['quantity'] = new_quantity
            logging.info(f"Replenished {resource_type} to {new_quantity} units.")

    def update_power_plant_market(self):
        game_manager = self.agent
        step = game_manager.step

        if step in [1, 2]:
            # Remove the highest-numbered power plant from the future market and place it under the deck
            if game_manager.future_market:
                highest_plant = max(game_manager.future_market, key=lambda x: x.min_bid if isinstance(x.min_bid, int) else -1)
                game_manager.future_market.remove(highest_plant)
                game_manager.power_plant_deck.append(highest_plant)
                logging.info(f"Moved highest power plant {highest_plant.min_bid} from future market to deck.")
                # Draw a new power plant to fill the market
                game_manager.draw_power_plant()
                # Update markets
                game_manager.update_markets()
            else:
                logging.warning("Future market is empty. Cannot remove highest power plant.")

        elif step == 3:
            # Remove the lowest-numbered power plant from the current market
            game_manager.remove_lowest_power_plant()
            # Draw a new power plant to fill the market
            game_manager.draw_power_plant()
            # No need to reorder the market in Step 3
        else:
            logging.error(f"Invalid game step: {step}")

    def check_step_change(self):
        game_manager = self.agent
        number_of_players = len(game_manager.player_jids)
        step2_cities = game_manager.step_start_cities.get(number_of_players, 7)
        # Check if any player has connected enough cities to start Step 2
        max_cities_connected = max(game_manager.player_cities.values(), default=0)
        if game_manager.step == 1 and max_cities_connected >= step2_cities:
            game_manager.step = 2
            logging.info("Advancing to Step 2!")
            # Handle Step 2 start logic
            game_manager.remove_lowest_power_plant()
            game_manager.draw_power_plant()
            game_manager.update_markets()

    def check_game_end(self):
        game_manager = self.agent
        number_of_players = len(game_manager.player_jids)
        end_cities = game_manager.game_end_cities.get(number_of_players, 21)
        max_cities_connected = max(game_manager.player_cities.values(), default=0)
        if max_cities_connected >= end_cities:
            # The game ends immediately after Phase 5
            # Determine the winner based on the number of cities powered
            max_powered_cities = max(game_manager.powered_cities.values(), default=0)
            winners = [jid for jid, cities in game_manager.powered_cities.items() if cities == max_powered_cities]
            if len(winners) == 1:
                return True, winners[0]
            else:
                # Tie-breaker: player with the most Elektro
                max_elektro = max(game_manager.player_states[jid]['elektro'] for jid in winners)
                final_winners = [jid for jid in winners if game_manager.player_states[jid]['elektro'] == max_elektro]
                if len(final_winners) == 1:
                    return True, final_winners[0]
                else:
                    # If still tied, multiple winners
                    return True, ', '.join(final_winners)
        else:
            return False, None
