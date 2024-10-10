# player_agent.py

import asyncio
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import random
import json
from objects import PowerPlant
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for detailed logs
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class ReceivePhaseBehaviour(CyclicBehaviour):
    async def run(self):
        try:
            msg = await self.receive(timeout=10)
            if msg:
                sender = str(msg.sender).split('/')[0]
                logging.info(f"Player {self.agent.player_id} received message from {sender}: {msg.body}")

                if msg.body == "REQUEST_CITIES":
                    # Send the number of connected cities back to the Game Manager
                    response = Message(to=sender)
                    response.body = f"CITIES:{len(self.agent.houses)}"
                    await self.send(response)
                    logging.info(f"Player {self.agent.player_id} sent CITIES:{len(self.agent.houses)} to {sender}")

                elif msg.body == "REQUEST_POWER":
                    # Calculate how many cities the player can power
                    num_powered_cities = self.calculate_powered_cities()
                    # Remove used resources
                    self.consume_resources(num_powered_cities)
                    # Send response to Game Manager
                    response = Message(to=sender)
                    response.body = f"POWERED_CITIES:{num_powered_cities}"
                    await self.send(response)
                    logging.info(f"Player {self.agent.player_id} sent POWERED_CITIES:{num_powered_cities} to {sender}")

                elif msg.body.startswith("REQUEST_HIGHEST_PLANT"):
                    # Handle the request for the highest power plant
                    if self.agent.power_plants:
                        highest_plant = max(plant.min_bid for plant in self.agent.power_plants)
                    else:
                        highest_plant = 0  # No power plants owned

                    # Send response to Game Manager
                    response = Message(to=sender)
                    response.body = f"HIGHEST_PLANT:{highest_plant}"
                    await self.send(response)
                    logging.info(f"Player {self.agent.player_id} sent HIGHEST_PLANT:{highest_plant} to {sender}")

                elif msg.body.startswith("EARNINGS:"):
                    # Update player's money
                    try:
                        income = int(msg.body.split(":", 1)[1])
                        self.agent.elektro += income
                        print(f"Player {self.agent.player_id} received income: {income}. Total Elektro: {self.agent.elektro}")
                        logging.info(f"Player {self.agent.player_id} updated Elektro to {self.agent.elektro}")
                    except (IndexError, ValueError) as e:
                        logging.error(f"Player {self.agent.player_id} received malformed EARNINGS message: {msg.body} | Error: {e}")

                elif msg.body.startswith("PHASE_1:"):
                    # Handle player order notification
                    player_order = msg.get_metadata("player_order")
                    if player_order:
                        try:
                            player_order = int(player_order)
                            print(f"Player {self.agent.player_id} is in position {player_order}")
                            logging.info(f"Player {self.agent.player_id} is in position {player_order}")
                        except ValueError as e:
                            logging.error(f"Player {self.agent.player_id} received invalid 'player_order' metadata: {player_order} | Error: {e}")
                    else:
                        logging.warning(f"Player {self.agent.player_id} received PHASE_1 message without 'player_order' metadata.")

                elif msg.body.startswith("PHASE_2:"):
                    # Receive the power plant market
                    try:
                        market_info_json = msg.body.split(":", 1)[1]
                        power_plant_market = json.loads(market_info_json)
                        if not isinstance(power_plant_market, list):
                            raise ValueError("Power plant market data is not a list.")
                        self.agent.power_plant_market = power_plant_market
                        logging.info(f"Player {self.agent.player_id} updated power plant market: {power_plant_market}")
                        # Decide which power plant to auction
                        chosen_plant = self.choose_power_plant(power_plant_market)
                        if chosen_plant is not None:
                            # Send choice to Game Manager
                            choice_msg = Message(to="gamemanager@localhost")
                            choice_msg.body = f"AUCTION:{chosen_plant}"
                            await self.send(choice_msg)
                            logging.info(f"Player {self.agent.player_id} chose plant {chosen_plant} to auction")
                        else:
                            logging.info(f"Player {self.agent.player_id} did not choose any plant to auction.")
                    except (IndexError, ValueError, json.JSONDecodeError) as e:
                        logging.error(f"Player {self.agent.player_id} encountered an error processing PHASE_2 message: {e}")

                elif msg.body == "CHOOSE_PLANT":
                    # Decide which power plant to auction
                    chosen_plant = self.choose_power_plant(self.agent.power_plant_market)
                    if chosen_plant is not None:
                        # Send choice to Game Manager
                        choice_msg = Message(to="gamemanager@localhost")
                        choice_msg.body = f"AUCTION:{chosen_plant}"
                        await self.send(choice_msg)
                        logging.info(f"Player {self.agent.player_id} chose plant {chosen_plant} to auction")
                    else:
                        logging.info(f"Player {self.agent.player_id} did not choose any plant to auction.")

                elif msg.body.startswith("BID_REQUEST:"):
                    # Handle bid request with potential parameters
                    parts = msg.body.split(":")
                    if len(parts) >= 3:
                        try:
                            plant_number = int(parts[1])
                            current_bid = int(parts[2])
                            bid_amount = self.decide_bid_amount(current_bid)
                            if bid_amount > 0:
                                bid_msg = Message(to="gamemanager@localhost")
                                bid_msg.body = f"BID:{bid_amount}"
                                await self.send(bid_msg)
                                print(f"Player {self.agent.player_id} sent bid: {bid_amount}")
                                logging.info(f"Player {self.agent.player_id} sent BID:{bid_amount} to gamemanager@localhost")
                            else:
                                logging.info(f"Player {self.agent.player_id} decided to pass on bidding for plant {plant_number}")
                        except ValueError as e:
                            print(f"Player {self.agent.player_id} received malformed BID_REQUEST message: {msg.body}")
                            logging.error(f"Player {self.agent.player_id} received malformed BID_REQUEST message: {msg.body} | Error: {e}")
                    else:
                        print(f"Player {self.agent.player_id} received malformed BID_REQUEST message: {msg.body}")
                        logging.error(f"Player {self.agent.player_id} received malformed BID_REQUEST message: {msg.body}")

                elif msg.body.startswith("PHASE_3:"):
                    # Receive resource market info
                    try:
                        resource_market_json = msg.body.split(":", 1)[1]
                        resource_market = json.loads(resource_market_json)
                        if not isinstance(resource_market, dict):
                            raise ValueError("Resource market data is not a dictionary.")
                        # Decide which resources to buy
                        resources_to_buy = self.decide_resources_to_buy(resource_market)
                        # Send purchase to Game Manager
                        purchase_msg = Message(to="gamemanager@localhost")
                        purchase_msg.body = f"BUY_RESOURCES:{json.dumps(resources_to_buy)}"
                        await self.send(purchase_msg)
                        print(f"Player {self.agent.player_id} is buying resources: {resources_to_buy}")
                        logging.info(f"Player {self.agent.player_id} sent BUY_RESOURCES:{resources_to_buy} to gamemanager@localhost")
                    except (IndexError, ValueError, json.JSONDecodeError) as e:
                        logging.error(f"Player {self.agent.player_id} encountered an error processing PHASE_3 message: {e}")

                elif msg.body.startswith("PHASE_4:"):
                    # Handle building houses
                    try:
                        map_info_json = msg.body.split(":", 1)[1]
                        map_status = json.loads(map_info_json)
                        if not isinstance(map_status, dict):
                            raise ValueError("Map status data is not a dictionary.")
                        # Attempt to get 'step' metadata if present
                        step_metadata = msg.get_metadata("step")
                        if step_metadata:
                            try:
                                current_step = int(step_metadata)
                                self.agent.step = current_step
                            except ValueError as e:
                                logging.error(f"Player {self.agent.player_id} received invalid 'step' metadata: {step_metadata} | Error: {e}")
                        else:
                            # Handle missing 'step' metadata gracefully
                            current_step = self.agent.step  # Keep current step
                            logging.warning(f"Player {self.agent.player_id} did not receive 'step' metadata in PHASE_4 message.")

                        # Decide where to build
                        cities_to_build = self.decide_cities_to_build(map_status)

                        # Validate that cities_to_build is a list
                        if not isinstance(cities_to_build, list):
                            logging.error(f"Player {self.agent.player_id} tried to send BUILD_HOUSES with non-list data: {cities_to_build}")
                            cities_to_build = []  # Fallback to empty list

                        # Send building action to Game Manager
                        build_msg = Message(to="gamemanager@localhost")
                        build_msg.body = f"BUILD_HOUSES:{json.dumps(cities_to_build)}"
                        await self.send(build_msg)
                        print(f"Player {self.agent.player_id} is building houses in: {cities_to_build}")
                        logging.info(f"Player {self.agent.player_id} sent BUILD_HOUSES:{cities_to_build} to gamemanager@localhost")
                    except (IndexError, ValueError, json.JSONDecodeError) as e:
                        logging.error(f"Player {self.agent.player_id} encountered an error processing PHASE_4 message: {e}")

                elif msg.body.startswith("AUCTION_WIN:"):
                    # Handle auction win
                    parts = msg.body.split(":")
                    if len(parts) >= 3:
                        try:
                            plant_number = int(parts[1])
                            bid_amount = int(parts[2])
                            # Find the plant details from the market
                            for plant in self.agent.power_plant_market:
                                if plant['min_bid'] == plant_number:
                                    try:
                                        new_plant = PowerPlant(**plant)
                                        self.agent.power_plants.append(new_plant)
                                        logging.info(f"Player {self.agent.player_id} acquired PowerPlant: {new_plant.to_dict()}")
                                    except TypeError as e:
                                        print(f"Player {self.agent.player_id} failed to create PowerPlant: {e}")
                                        logging.error(f"Player {self.agent.player_id} failed to create PowerPlant: {e}")
                                    break
                            else:
                                logging.error(f"Player {self.agent.player_id} did not find PowerPlant {plant_number} in the market.")
                            print(f"Player {self.agent.player_id} won auction for plant {plant_number} with bid {bid_amount}")
                            logging.info(f"Player {self.agent.player_id} won auction for plant {plant_number} with bid {bid_amount}")
                        except ValueError as e:
                            print(f"Player {self.agent.player_id} received malformed AUCTION_WIN message: {msg.body}")
                            logging.error(f"Player {self.agent.player_id} received malformed AUCTION_WIN message: {msg.body} | Error: {e}")
                    else:
                        print(f"Player {self.agent.player_id} received malformed AUCTION_WIN message: {msg.body}")
                        logging.error(f"Player {self.agent.player_id} received malformed AUCTION_WIN message: {msg.body}")

                elif msg.body.startswith("PURCHASE_CONFIRMED:"):
                    # Handle purchase confirmation
                    parts = msg.body.split(":")
                    if len(parts) >= 3:
                        try:
                            resource_type = parts[1]
                            amount = int(parts[2])
                            self.agent.resources[resource_type] += amount
                            print(f"Player {self.agent.player_id} successfully purchased {amount} {resource_type}")
                            logging.info(f"Player {self.agent.player_id} successfully purchased {amount} {resource_type}")
                        except (ValueError, IndexError) as e:
                            print(f"Player {self.agent.player_id} received malformed PURCHASE_CONFIRMED message: {msg.body}")
                            logging.error(f"Player {self.agent.player_id} received malformed PURCHASE_CONFIRMED message: {msg.body} | Error: {e}")
                    else:
                        print(f"Player {self.agent.player_id} received malformed PURCHASE_CONFIRMED message: {msg.body}")
                        logging.error(f"Player {self.agent.player_id} received malformed PURCHASE_CONFIRMED message: {msg.body}")

                elif msg.body.startswith("PURCHASE_FAILED:"):
                    # Handle purchase failure
                    parts = msg.body.split(":")
                    if len(parts) >= 3:
                        try:
                            resource_type = parts[1]
                            reason = parts[2]
                            print(f"Player {self.agent.player_id} failed to purchase {resource_type}: {reason}")
                            logging.info(f"Player {self.agent.player_id} failed to purchase {resource_type}: {reason}")
                        except IndexError as e:
                            print(f"Player {self.agent.player_id} received malformed PURCHASE_FAILED message: {msg.body}")
                            logging.error(f"Player {self.agent.player_id} received malformed PURCHASE_FAILED message: {msg.body} | Error: {e}")
                    else:
                        print(f"Player {self.agent.player_id} received malformed PURCHASE_FAILED message: {msg.body}")
                        logging.error(f"Player {self.agent.player_id} received malformed PURCHASE_FAILED message: {msg.body}")

                elif msg.body.startswith("BUILD_CONFIRMED:"):
                    # Handle build confirmation
                    parts = msg.body.split(":")
                    if len(parts) >= 2:
                        try:
                            city = parts[1]
                            self.agent.houses.append(city)
                            print(f"Player {self.agent.player_id} successfully built in {city}")
                            logging.info(f"Player {self.agent.player_id} successfully built in {city}")
                        except IndexError as e:
                            print(f"Player {self.agent.player_id} received malformed BUILD_CONFIRMED message: {msg.body}")
                            logging.error(f"Player {self.agent.player_id} received malformed BUILD_CONFIRMED message: {msg.body} | Error: {e}")
                    else:
                        print(f"Player {self.agent.player_id} received malformed BUILD_CONFIRMED message: {msg.body}")
                        logging.error(f"Player {self.agent.player_id} received malformed BUILD_CONFIRMED message: {msg.body}")

                elif msg.body.startswith("BUILD_FAILED:"):
                    # Handle build failure
                    parts = msg.body.split(":")
                    if len(parts) >= 3:
                        try:
                            city = parts[1]
                            reason = parts[2]
                            print(f"Player {self.agent.player_id} failed to build in {city}: {reason}")
                            logging.info(f"Player {self.agent.player_id} failed to build in {city}: {reason}")
                        except IndexError as e:
                            print(f"Player {self.agent.player_id} received malformed BUILD_FAILED message: {msg.body}")
                            logging.error(f"Player {self.agent.player_id} received malformed BUILD_FAILED message: {msg.body} | Error: {e}")
                    else:
                        print(f"Player {self.agent.player_id} received malformed BUILD_FAILED message: {msg.body}")
                        logging.error(f"Player {self.agent.player_id} received malformed BUILD_FAILED message: {msg.body}")

                elif msg.body == "GAME_END":
                    winner = msg.get_metadata("winner")
                    if winner and winner == self.agent.jid:
                        print(f"Player {self.agent.player_id} has won the game!")
                        logging.info(f"Player {self.agent.player_id} has won the game!")
                    elif winner:
                        print(f"Player {self.agent.player_id} has lost. Winner: {winner}")
                        logging.info(f"Player {self.agent.player_id} has lost. Winner: {winner}")
                    else:
                        print(f"Player {self.agent.player_id} received GAME_END message without winner metadata.")
                        logging.warning(f"Player {self.agent.player_id} received GAME_END message without winner metadata.")
                    await self.agent.stop()

                else:
                    print(f"Player {self.agent.player_id} received an unknown message: {msg.body}")
                    logging.warning(f"Player {self.agent.player_id} received an unknown message: {msg.body}")
        except Exception as e:
            print(f"Player {self.agent.player_id} encountered an error: {e}")
            logging.error(f"Player {self.agent.player_id} encountered an error: {e}")
        await asyncio.sleep(1)  # Yield control to event loop

    def choose_power_plant(self, market):
        # Simple strategy: choose the cheapest power plant
        if market:
            # Convert market data to PowerPlant instances
            available_plants = []
            for plant_data in market:
                try:
                    plant = PowerPlant(**plant_data)
                    available_plants.append(plant)
                except TypeError as e:
                    print(f"Player {self.agent.player_id} failed to create PowerPlant from data {plant_data}: {e}")
                    logging.error(f"Player {self.agent.player_id} failed to create PowerPlant from data {plant_data}: {e}")
            # Filter out plants the player cannot afford
            affordable_plants = [plant for plant in available_plants if plant.min_bid is not None and plant.min_bid <= self.agent.elektro]
            if affordable_plants:
                # Choose the plant with the lowest min_bid
                chosen_plant = min(affordable_plants, key=lambda plant: plant.min_bid)
                return chosen_plant.min_bid
        return None  # No plant chosen

    def decide_bid_amount(self, current_bid):
        # Simple strategy: bid current bid + 1, up to a maximum
        max_bid = self.agent.elektro  # Do not bid more than available money
        next_bid = current_bid + 1
        if next_bid <= max_bid:
            return next_bid
        else:
            # Cannot bid more, pass (return 0 or some indicator)
            return 0  # Indicate that the agent passes

    def decide_resources_to_buy(self, resource_market):
        # Strategy: Buy resources needed to power as many cities as possible
        resources_needed = {}
        total_needed = {}
        # Calculate storage capacity
        for plant in self.agent.power_plants:
            plant_details = plant  # Assuming plant is a PowerPlant instance
            resource_types = plant_details.resource_type
            if plant_details.resource_num > 0:
                for resource in resource_types:
                    capacity = plant_details.resource_num * 2
                    current_storage = getattr(plant, 'storage', {}).get(resource, 0)
                    needed = capacity - current_storage
                    if needed > 0:
                        total_needed[resource] = total_needed.get(resource, 0) + needed
        # Purchase resources based on market availability and prices
        for resource, needed_amount in total_needed.items():
            if resource not in resource_market:
                continue  # Invalid resource
            available = resource_market[resource]['quantity']
            price = resource_market[resource]['price']
            affordable_amount = min(needed_amount, available)
            # Check if the agent has enough money
            total_cost = price * affordable_amount
            if self.agent.elektro >= total_cost:
                self.agent.elektro -= total_cost
                self.agent.resources[resource] += affordable_amount
                resources_needed[resource] = affordable_amount
            else:
                # Buy as much as possible with remaining money
                max_affordable = self.agent.elektro // price
                if max_affordable > 0:
                    self.agent.elektro -= max_affordable * price
                    self.agent.resources[resource] += max_affordable
                    resources_needed[resource] = max_affordable
        logging.debug(f"Player {self.agent.player_id} decided to buy resources: {resources_needed}")
        return resources_needed

    def decide_cities_to_build(self, map_status):
        # Simple strategy: Build in the cheapest adjacent city
        cities_to_build = []
        if not self.agent.houses:
            # If the agent has no houses, choose a starting city
            # For simplicity, pick a random city that is unowned
            available_cities = [city for city, data in map_status.items() if not data['owners']]
            if available_cities:
                starting_city = random.choice(available_cities)
                cities_to_build.append(starting_city)
        else:
            # Find adjacent cities
            possible_cities = set()
            for city in self.agent.houses:
                # Assuming 'connections' is a dict with adjacent_city: cost
                connections = map_status.get(city, {}).get('connections', {})
                for adjacent_city, cost in connections.items():
                    if adjacent_city not in self.agent.houses:
                        possible_cities.add((adjacent_city, cost))
            # Sort possible cities by connection cost
            possible_cities = sorted(possible_cities, key=lambda x: x[1])
            # Attempt to build in the cheapest city
            for city, cost in possible_cities:
                building_cost = self.get_building_cost(city, map_status)
                total_cost = cost + building_cost
                if self.agent.elektro >= total_cost:
                    self.agent.elektro -= total_cost
                    cities_to_build.append(city)
                    break  # Build in one city for now
        logging.debug(f"Player {self.agent.player_id} decided to build in: {cities_to_build}")
        return cities_to_build

    def get_building_cost(self, city, map_status):
        # Determine building cost based on occupancy
        occupancy = len(map_status[city]['owners'])
        if occupancy == 0:
            return 10
        elif occupancy == 1:
            return 15
        elif occupancy == 2:
            return 20
        else:
            return float('inf')  # Cannot build if city is full

    def calculate_powered_cities(self):
        total_powered_cities = 0
        remaining_cities = len(self.agent.houses)
        # Sort power plants by min_bid descending to prioritize higher capacity
        for plant in sorted(self.agent.power_plants, key=lambda x: x.min_bid, reverse=True):
            if remaining_cities <= 0:
                break
            if plant.power_on():
                capacity = min(plant.capacity, remaining_cities)
                total_powered_cities += capacity
                remaining_cities -= capacity
        return total_powered_cities

    def consume_resources(self, num_cities_powered):
        remaining_cities = num_cities_powered
        for plant in sorted(self.agent.power_plants, key=lambda x: x.min_bid, reverse=True):
            if remaining_cities <= 0:
                break
            if plant.power_on():
                capacity = min(plant.capacity, remaining_cities)
                remaining_cities -= capacity
                # Resources have already been consumed in power_on()

class PowerGridPlayerAgent(Agent):
    def __init__(self, jid, password, player_id):
        super().__init__(jid, password)
        self.player_id = player_id
        self.houses = []  # List of city tags where the player has houses
        self.power_plants = []  # List of PowerPlant instances
        self.resources = {"coal": 0, "oil": 0, "garbage": 0, "uranium": 0}
        self.elektro = 50  # Starting money
        self.connected_cities = 0
        self.power_plant_market = []  # Latest power plant market info
        self.step = 1  # Current game step
        self.current_bid = 0  # Current bid in an auction

    async def setup(self):
        print(f"Player {self.player_id} agent starting...")
        receive_phase_behaviour = ReceivePhaseBehaviour()
        self.add_behaviour(receive_phase_behaviour)
        logging.info(f"Player {self.player_id} added ReceivePhaseBehaviour")
