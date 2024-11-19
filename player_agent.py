# player_agent.py

import asyncio
import json
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
from objects import PowerPlant
from game_environment import Environment

class PowerGridPlayerAgent(Agent):
    """
    PowerGridPlayerAgent represents a player in the Power Grid game.
    It manages the player's state and interacts with the game environment
    through message passing.
    """

    _attributes = [
        'houses', 'elektro', 'cities_owned', 'number_cities_owned',
        'cities_powered', 'power_plants', 'resources',
        'has_bought_power_plant', 'position', 'connected_cities'
    ]

    def __init__(self, jid, password, player_id, environment: Environment):
        """
        Initializes the PowerGridPlayerAgent.

        Args:
            jid (str): Jabber ID for the agent.
            password (str): Password for the agent.
            player_id (int): Unique identifier for the player.
            environment (Environment): The game environment instance.
        """
        super().__init__(jid, password)
        self.player_id = player_id
        self.environment = environment
        self._cache = {}
        self.get_inventory()

    def get_inventory(self):
        """
        Fetches the current inventory from the environment and updates the local cache.
        """
        inventory = self.environment.players.get(self.player_id, {})
        for attr in self._attributes:
            self._cache[attr] = inventory.get(attr, self._default_value(attr))

    def update_inventory(self):
        """
        Pushes the current local cache to the environment's inventory.
        """
        inventory = {attr: self._cache[attr] for attr in self._attributes}
        self.environment.players[self.player_id] = inventory

    def _default_value(self, attr):
        """
        Provides default values for attributes if not present in the inventory.

        Args:
            attr (str): The attribute name.

        Returns:
            Default value based on the attribute type.
        """
        defaults = {
            'houses': 0,
            'elektro': 0,
            'cities_owned': [],
            'number_cities_owned': 0,
            'cities_powered': [],
            'power_plants': [],
            'resources': {},
            'has_bought_power_plant': False,
            'position': None,
            'connected_cities': 0
        }
        return defaults.get(attr, None)

    # Property Decorators for Automatic Synchronization

    @property
    def houses(self):
        return self._cache.get('houses', 0)

    @houses.setter
    def houses(self, value):
        self._cache['houses'] = value
        self.update_inventory()

    @property
    def elektro(self):
        return self._cache.get('elektro', 0)

    @elektro.setter
    def elektro(self, value):
        self._cache['elektro'] = value
        self.update_inventory()

    @property
    def cities_owned(self):
        return self._cache.get('cities_owned', [])

    @cities_owned.setter
    def cities_owned(self, value):
        self._cache['cities_owned'] = value
        self.number_cities_owned = len(value)  # Automatically update related attribute
        self.update_inventory()

    @property
    def number_cities_owned(self):
        return self._cache.get('number_cities_owned', 0)

    @number_cities_owned.setter
    def number_cities_owned(self, value):
        self._cache['number_cities_owned'] = value
        self.update_inventory()

    @property
    def cities_powered(self):
        return self._cache.get('cities_powered', [])

    @cities_powered.setter
    def cities_powered(self, value):
        self._cache['cities_powered'] = value
        self.update_inventory()

    @property
    def power_plants(self):
        return self._cache.get('power_plants', [])

    @power_plants.setter
    def power_plants(self, value):
        self._cache['power_plants'] = value
        self.update_inventory()

    @property
    def resources(self):
        return self._cache.get('resources', {})

    @resources.setter
    def resources(self, value):
        self._cache['resources'] = value
        self.update_inventory()

    @property
    def has_bought_power_plant(self):
        return self._cache.get('has_bought_power_plant', False)

    @has_bought_power_plant.setter
    def has_bought_power_plant(self, value):
        self._cache['has_bought_power_plant'] = value
        self.update_inventory()

    @property
    def position(self):
        return self._cache.get('position', None)

    @position.setter
    def position(self, value):
        self._cache['position'] = value
        self.update_inventory()

    @property
    def connected_cities(self):
        return self._cache.get('connected_cities', 0)

    @connected_cities.setter
    def connected_cities(self, value):
        self._cache['connected_cities'] = value
        self.update_inventory()

    class ReceivePhaseBehaviour(CyclicBehaviour):
        """
        ReceivePhaseBehaviour handles incoming messages related to different game phases.
        """

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
                    self.handle_setup_phase(data)
                elif phase == "phase1":
                    self.handle_phase1(data)
                elif phase == "phase2":
                    await self.handle_phase2(data, sender)
                elif phase == "phase3":
                    await self.handle_phase3(data, sender)
                elif phase == "phase4":
                    await self.handle_phase4(data, sender)
                elif phase == "phase5":
                    self.handle_phase5()
                elif phase == "game_over":
                    await self.handle_game_over(data)
                else:
                    print(f"Player {self.agent.player_id} received an unknown message: {msg.body}")
            else:
                print(f"Player {self.agent.player_id} did not receive any message.")
            await asyncio.sleep(1)  # Yield control to event loop

        def handle_setup_phase(self, data):
            """
            Handles the setup phase by setting the player's position.

            Args:
                data (dict): The message data.
            """
            player_order = data.get("player_order")
            self.agent.position = player_order
            print(f"Player {self.agent.player_id} received setup information. Position: {player_order}")

        def handle_phase1(self, data):
            """
            Handles phase1 by updating the player's position.

            Args:
                data (dict): The message data.
            """
            player_order = data.get("player_order")
            self.agent.position = player_order
            print(f"Player {self.agent.player_id} is in position {player_order}")

        async def handle_phase2(self, data, sender):
            """
            Handles phase2 actions such as choosing to auction or pass, bidding, and discarding power plants.

            Args:
                data (dict): The message data.
                sender (str): The sender's identifier.
            """
            action = data.get("action")

            if action == "choose_or_pass":
                await self.process_choose_or_pass(data, sender)
            elif action == "initial_bid":
                await self.process_initial_bid(data, sender)
            elif action == "bid":
                await self.process_bid(data, sender)
            elif action == "discard_power_plant":
                await self.process_discard_power_plant(data, sender)
            elif action == "auction_result":
                await self.process_auction_result(data, sender)
            else:
                print(f"Player {self.agent.player_id} received an unknown action in phase2: {action}")

        async def process_choose_or_pass(self, data, sender):
            power_plant_market_data = data.get("power_plants", [])
            power_plant_market = [PowerPlant.from_dict(pp) for pp in power_plant_market_data]
            can_pass = data.get("can_pass", True)

            if can_pass:
                if self.agent.should_pass(power_plant_market):
                    choice_data = {"choice": "pass"}
                    print(f"Player {self.agent.player_id} decides to pass on starting an auction.")
                else:
                    chosen_plant_number = self.agent.choose_power_plant_to_auction(power_plant_market)
                    if chosen_plant_number is not None:
                        choice_data = {
                            "choice": "auction",
                            "power_plant_number": chosen_plant_number
                        }
                        print(f"Player {self.agent.player_id} chooses to auction power plant {chosen_plant_number}.")
                    else:
                        # Cannot afford any power plant, so pass
                        choice_data = {"choice": "pass"}
                        print(f"Player {self.agent.player_id} cannot afford any power plant and passes.")
            else:
                # Must choose a power plant (first round)
                chosen_plant_number = self.agent.choose_power_plant_to_auction(power_plant_market)
                choice_data = {
                    "choice": "auction",
                    "power_plant_number": chosen_plant_number
                }
                print(f"Player {self.agent.player_id} must auction power plant {chosen_plant_number} (first round).")

            choice_msg = Message(to=sender)
            choice_msg.body = json.dumps(choice_data)
            await self.send(choice_msg)

        async def process_initial_bid(self, data, sender):
            base_min_bid = data.get("base_min_bid")
            power_plant_data = data.get("power_plant")
            power_plant = PowerPlant.from_dict(power_plant_data) if power_plant_data else None
            bid_amount = self.agent.decide_initial_bid(base_min_bid, power_plant)

            bid_data = {"bid": bid_amount}
            bid_msg = Message(to=sender)
            bid_msg.body = json.dumps(bid_data)
            await self.send(bid_msg)
            print(
                f"Player {self.agent.player_id} places initial bid of {bid_amount} on power plant "
                f"{power_plant.min_bid if power_plant else 'unknown'}.")

        async def process_bid(self, data, sender):
            current_bid = data.get("current_bid", 0)
            power_plant_data = data.get("power_plant", {})
            power_plant = PowerPlant.from_dict(power_plant_data) if power_plant_data else None
            bid_amount = self.agent.decide_bid_amount(current_bid, power_plant)

            bid_data = {"bid": bid_amount}
            bid_msg = Message(to=sender)
            bid_msg.body = json.dumps(bid_data)
            await self.send(bid_msg)

            if bid_amount > current_bid:
                print(
                    f"Player {self.agent.player_id} bids {bid_amount} for power plant "
                    f"{power_plant.min_bid if power_plant else 'unknown'}.")
            else:
                print(f"Player {self.agent.player_id} passes on bidding.")

        async def process_discard_power_plant(self, data, sender):
            power_plants_data = data.get("power_plants", [])
            power_plants = [PowerPlant.from_dict(pp) for pp in power_plants_data]
            discard_number = self.agent.choose_power_plant_to_discard(power_plants)

            discard_data = {"discard_number": discard_number}
            discard_msg = Message(to=sender)
            discard_msg.body = json.dumps(discard_data)
            await self.send(discard_msg)
            print(f"Player {self.agent.player_id} discards power plant {discard_number}.")

        async def process_auction_result(self, data, sender):
            winner = data.get("winner")
            power_plant_data = data.get("power_plant", {})
            power_plant = PowerPlant.from_dict(power_plant_data) if power_plant_data else None
            bid = data.get("bid", 0)

            if winner == self.agent.jid:
                # Add the power plant to the player's state
                if power_plant:
                    self.agent.power_plants = self.agent.power_plants + [power_plant]
                    self.agent.elektro -= bid  # Deduct the bid amount
                    print(
                        f"Player {self.agent.player_id} won the auction for power plant "
                        f"{power_plant.min_bid} with bid {bid}.")
            else:
                print(
                    f"Player {self.agent.player_id} observed that player {winner} won the auction for power plant "
                    f"{power_plant.min_bid if power_plant else 'unknown'} with bid {bid}.")

        async def handle_phase3(self, data, sender):
            """
            Handles phase3 actions such as buying resources and processing purchase results.

            Args:
                data (dict): The message data.
                sender (str): The sender's identifier.
            """
            action = data.get("action")

            if action == "buy_resources":
                resource_market = data.get("resource_market", {})
                purchases = self.agent.decide_resources_to_buy(resource_market)

                purchase_data = {"purchases": purchases}
                purchase_msg = Message(to=sender)
                purchase_msg.body = json.dumps(purchase_data)
                await self.send(purchase_msg)
                print(f"Player {self.agent.player_id} decides to buy resources: {purchases}.")

            elif action == "purchase_result":
                purchases = data.get("purchases", {})
                total_cost = data.get("total_cost", 0)

                # Update player's resources and elektro
                new_resources = self.agent.resources.copy()
                for resource, amount in purchases.items():
                    new_resources[resource] = new_resources.get(resource, 0) + amount
                self.agent.resources = new_resources
                self.agent.elektro -= total_cost
                print(
                    f"Player {self.agent.player_id} purchased resources: {purchases} for total cost {total_cost}.")
            else:
                print(f"Player {self.agent.player_id} received an unknown action in phase3: {action}")

        async def handle_phase4(self, data, sender):
            """
            Handles phase4 actions such as building houses and processing build results.

            Args:
                data (dict): The message data.
                sender (str): The sender's identifier.
            """
            action = data.get("action")

            if action == "build_houses":
                map_status = data.get("map_status", {})
                current_step = data.get("step", 1)
                self.agent.step = current_step

                cities_to_build = self.agent.decide_cities_to_build(map_status)

                build_data = {"cities": cities_to_build}
                build_msg = Message(to=sender)
                build_msg.body = json.dumps(build_data)
                await self.send(build_msg)
                print(f"Player {self.agent.player_id} decides to build in cities: {cities_to_build}.")

            elif action == "build_result":
                cities = data.get("cities", [])
                total_cost = data.get("total_cost", 0)

                # Update player's cities
                new_cities_owned = self.agent.cities_owned + cities
                self.agent.cities_owned = new_cities_owned
                self.agent.elektro -= total_cost
                print(
                    f"Player {self.agent.player_id} built houses in cities: {cities} for total cost {total_cost}.")
            else:
                print(f"Player {self.agent.player_id} received an unknown action in phase4: {action}")

        def handle_phase5(self):
            """
            Handles phase5 (Bureaucracy).
            """
            print(f"Player {self.agent.player_id} acknowledges Phase 5 - Bureaucracy.")

        async def handle_game_over(self, data):
            """
            Handles the game over phase.

            Args:
                data (dict): The message data.
            """
            winner = data.get("winner")
            final_elektro = data.get("final_elektro")

            if winner == self.agent.jid:
                print(f"Player {self.agent.player_id} has won the game with {final_elektro} Elektro!")
            else:
                print(f"Player {self.agent.player_id} has lost. Winner: {winner} with {final_elektro} Elektro.")
            await self.agent.stop()

    # Decision-making methods are part of the PowerGridPlayerAgent class

    def should_pass(self, power_plant_market):
        """
        Decide whether to pass based on the current power plant market.

        Args:
            power_plant_market (list): List of available PowerPlant objects.

        Returns:
            bool: True if the player should pass, False otherwise.
        """
        need_power_plant = len(self.power_plants) < 3
        can_afford_any = any(pp.min_bid <= self.elektro for pp in power_plant_market)
        return not need_power_plant or not can_afford_any

    def choose_power_plant_to_auction(self, market):
        """
        Choose the best affordable power plant to auction based on strategic evaluation.

        Args:
            market (list): List of available PowerPlant objects.

        Returns:
            int or None: The min_bid of the chosen power plant, or None if no affordable plant is found.
        """
        if not market:
            print(f"Player {self.player_id} finds no available power plants to auction.")
            return None

        affordable_plants = [pp for pp in market if pp.min_bid <= self.elektro]
        if not affordable_plants:
            print(f"Player {self.player_id} cannot afford any power plant.")
            return None

        # Strategy: pick the plant that provides the best ratio of cities powered per Elektro
        best_plant = max(affordable_plants, key=lambda pp: pp.cities / pp.min_bid if pp.min_bid > 0 else 0)
        return best_plant.min_bid if hasattr(best_plant, 'min_bid') else None

    def decide_initial_bid(self, base_min_bid, power_plant):
        """
        Decide the initial bid based on the value of the power plant.

        Args:
            base_min_bid (int): The base minimum bid.
            power_plant (PowerPlant): The power plant being bid on.

        Returns:
            int: The bid amount.
        """
        plant_value = self.evaluate_power_plant(power_plant)
        max_bid = int(self.elektro * 0.6)
        bid = min(max_bid, base_min_bid)
        return bid if bid >= base_min_bid else 0

    def decide_bid_amount(self, current_bid, power_plant):
        """
        Decide whether to bid higher based on the plant's value and available Elektro.

        Args:
            current_bid (int): The current highest bid.
            power_plant (PowerPlant): The power plant being bid on.

        Returns:
            int: The new bid amount, or 0 to pass.
        """
        plant_value = self.evaluate_power_plant(power_plant)
        max_affordable_bid = self.elektro

        if current_bid < plant_value and (current_bid + 1) <= max_affordable_bid:
            return current_bid + 1
        else:
            return 0

    def evaluate_power_plant(self, power_plant):
        """
        Evaluate the power plant's worth to the agent.

        Args:
            power_plant (PowerPlant): The power plant to evaluate.

        Returns:
            int: The evaluated value of the power plant.
        """
        if not power_plant:
            return 0

        cities_powered = power_plant.cities
        resource_types = power_plant.resource_type
        is_eco = len(resource_types) == 0
        value = cities_powered * 10
        if is_eco:
            value += 20
        return value

    def choose_power_plant_to_discard(self, power_plants):
        """
        Decide which power plant to discard when over the limit.

        Args:
            power_plants (list): List of PowerPlant objects to choose from.

        Returns:
            int or None: The min_bid of the chosen power plant to discard, or None if list is empty.
        """
        if not power_plants:
            return None

        # Strategy: discard the plant with the lowest number of cities powered
        plant_to_discard = min(power_plants, key=lambda pp: pp.cities)
        return plant_to_discard.min_bid if hasattr(plant_to_discard, 'min_bid') else None

    def decide_resources_to_buy(self, resource_market):
        """
        Decide which resources to buy based on the power plants owned.

        Args:
            resource_market (dict): Available resources in the market.

        Returns:
            dict: Resources to buy with their respective amounts.
        """
        purchases = {"coal": 0, "oil": 0, "garbage": 0, "uranium": 0}
        for plant in self.power_plants:
            print("\n\nPlant being checked: ", plant)

            resource_types = plant.resource_type
            resource_needed = plant.resource_num
            is_hybrid = plant.is_hybrid

            if not resource_types or resource_needed == 0:
                continue  # Eco-friendly plant or no resources needed

            if is_hybrid:
                # Hybrid plant: buy resources in any combination
                for rtype in resource_types:
                    available = resource_market.get(rtype, 0)
                    if available > 0 and self.elektro > 0:
                        amount_to_buy = min(available, resource_needed)
                        purchases[rtype] += amount_to_buy
                        resource_needed -= amount_to_buy
                        self.elektro -= amount_to_buy * 1  # Simplified cost
                        if resource_needed <= 0:
                            break
            else:
                # Non-hybrid plant: buy required resources
                rtype = resource_types[0]
                available = resource_market.get(rtype, 0)
                if available > 0 and self.elektro > 0:
                    amount_to_buy = min(available, resource_needed)
                    purchases[rtype] += amount_to_buy
                    resource_needed -= amount_to_buy
                    self.elektro -= amount_to_buy * 1  # Simplified cost
        return purchases

    def decide_cities_to_build(self, map_status):
        """
        Decide where to build houses based on the map status.

        Args:
            map_status (dict): Current status of the map.

        Returns:
            list: List of cities to build houses in.
        """
        # Simple logic: build in the first available city not owned
        for city, data in map_status.items():
            if city not in self.cities_owned:
                return [city]
        return []

    async def setup(self):
        """
        Sets up the agent by adding the ReceivePhaseBehaviour.
        """
        print(f"Player {self.player_id} agent starting...")
        receive_phase_behaviour = self.ReceivePhaseBehaviour()
        self.add_behaviour(receive_phase_behaviour)