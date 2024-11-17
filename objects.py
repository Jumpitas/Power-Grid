# objects.py

import random
from rule_tables import price_table, resource_replenishment, remove_cards

class PowerPlant:
    def __init__(self, min_bid, cities, resource_type=None, resource_num=0, is_hybrid=False, is_step=False):
        if resource_type is None:
            resource_type = []
        self.min_bid = min_bid
        self.cities = cities
        self.resource_type = resource_type
        self.resource_num = resource_num
        self.is_hybrid = is_hybrid
        self.is_step = is_step
        # For resource management per power plant (optional):
        self.storage = {rtype: 0 for rtype in resource_type}
        self.available_storage = resource_num * 2 if resource_type else 0

    def __repr__(self):
        return (f"PowerPlant("
                f"min_bid={self.min_bid}, "
                f"cities={self.cities}, "
                f"resource_type={self.resource_type}, "
                f"resource_num={self.resource_num}, "
                f"is_hybrid={self.is_hybrid}, "
                f"is_step={self.is_step})")

    def store_resources(self, resource, amount):
        """Stores a given amount of a resource if space is available in the power plant's storage."""
        if resource not in self.resource_type:
            print(f"Resource type {resource} is not compatible with this power plant: {self.resource_type}")
            return False
        if amount > self.available_storage:
            print(f"Not enough storage space to store {amount} units of {resource}.")
            return False
        self.storage[resource] += amount
        self.available_storage -= amount
        return True

    def consume_resources(self):
        """
        Consumes the necessary resources from the power plant's storage to supply cities.
        Returns a dictionary of resources that should be returned to the supply.
        """
        if not self.resource_type:
            # Ecological power plants that don't need resources
            return {}
        used_resources = {rtype: 0 for rtype in self.resource_type}
        required_amount = self.resource_num

        if not self.is_hybrid:
            # Non-hybrid power plants use one type of resource
            resource_type = self.resource_type[0]
            if self.storage[resource_type] >= required_amount:
                self.storage[resource_type] -= required_amount
                self.available_storage += required_amount
                used_resources[resource_type] = required_amount
            else:
                # Not enough resources to power this plant
                return {}
        else:
            # Hybrid power plants can use any combination of resources
            for rtype in self.resource_type:
                if required_amount == 0:
                    break
                available = self.storage[rtype]
                to_use = min(available, required_amount)
                self.storage[rtype] -= to_use
                used_resources[rtype] += to_use
                self.available_storage += to_use
                required_amount -= to_use
            if required_amount > 0:
                # Not enough total resources to power this hybrid plant
                return {}
        return used_resources

class ResourceMarket:
    def __init__(self, coal=24, oil=24, garbage=24, uranium=12):
        # Maximum capacities for each resource in the market
        self.max = {"coal": 24, "oil": 24, "garbage": 24, "uranium": 12}
        # Current availability of each resource in the market
        self.in_market = {"coal": coal, "oil": oil, "garbage": garbage, "uranium": uranium}

    def __repr__(self):
        return f"ResourceMarket(in_market={self.in_market})"

    def resource_price(self, resource_type):
        """
        Returns the cost of purchasing the next unit of the given resource type.
        If the resource is unavailable, returns None.
        """
        current_amount = self.in_market.get(resource_type, 0)
        if current_amount == 0:
            return None  # No resources available
        if resource_type == "uranium":
            # Uranium has a distinct pricing structure based on the current amount
            return price_table["uranium"].get(current_amount, None)
        else:
            # For coal, oil, and garbage, pricing depends on how many units are left
            # This logic is simplified and doesn't reflect the exact increments from the original game board
            # For a more accurate reflection, you'd need to map the number of resources to specific prices
            for ranges, price in price_table[resource_type].items():
                if current_amount in ranges:
                    return price
        return None

    def purchase_resource(self, resource_type, quantity):
        """
        Attempts to purchase a certain quantity of a resource type.
        Returns the total cost if successful, or None if there aren't enough resources.
        """
        if self.in_market.get(resource_type, 0) < quantity:
            return None
        total_cost = 0
        for _ in range(quantity):
            unit_price = self.resource_price(resource_type)
            if unit_price is None:
                return None  # Not enough resources to complete the purchase
            total_cost += unit_price
            self.in_market[resource_type] -= 1
        return total_cost

    def refill_market(self, step, player_count):
        """
        Refill the market at the end of a turn based on the number of players and the current game step.
        """
        # The resource replenishment logic from rule_tables can be applied here.
        refills = resource_replenishment.get(step, {}).get(player_count, {})
        for resource, amount in refills.items():
            current_amount = self.in_market.get(resource, 0)
            max_capacity = self.max[resource]
            available_space = max_capacity - current_amount
            amount_to_add = min(available_space, amount)
            self.in_market[resource] += amount_to_add

    def add_resources_back_to_bank(self, used_resources):
        """
        Adds the used resources back to the resource bank (which can be managed if needed).
        """
        # If we are tracking the resource bank outside this class, this method can adjust that as needed.
        pass

class PowerPlantMarket:
    def __init__(self, player_count):
        self.player_count = player_count
        self.current_market = []
        self.future_market = []
        self.deck = []
        self._initialize_markets()

    def __repr__(self):
        return (f"PowerPlantMarket(\n"
                f"  current_market={self.current_market},\n"
                f"  future_market={self.future_market},\n"
                f"  deck={self.deck}\n)")

    def _initialize_markets(self):
        """
        Initializes the markets and deck based on the number of players.
        """
        # Combine power plant sets
        all_plants = power_plant_plug + power_plant_socket
        # Identify the Step 3 card as it is placed at the bottom of the deck
        step_3_card = [plant for plant in all_plants if plant.is_step]
        if step_3_card:
            step_3_card = step_3_card[0]
            all_plants.remove(step_3_card)
        else:
            step_3_card = None

        # Shuffle them
        random.shuffle(all_plants)

        # Remove cards as specified in `remove_cards` for the given number of players
        plug_to_remove, socket_to_remove = remove_cards.get(self.player_count, (0, 0))
        removed_plug = power_plant_plug[:plug_to_remove] if plug_to_remove else []
        removed_socket = power_plant_socket[:socket_to_remove] if socket_to_remove else []

        # Filter out the removed power plants from all_plants
        all_plants = [plant for plant in all_plants if plant not in removed_plug + removed_socket]

        # The initial deck arrangement:
        # - Current market: first 4 sorted by min_bid
        # - Future market: next 4 sorted by min_bid
        # - Deck: the rest sorted by min_bid
        self.current_market = sorted(all_plants[:4], key=lambda pp: pp.min_bid)
        self.future_market = sorted(all_plants[4:8], key=lambda pp: pp.min_bid)
        self.deck = sorted(all_plants[8:], key=lambda pp: pp.min_bid)

        # Insert Step 3 card at the bottom of the deck, if present
        if step_3_card:
            self.deck.append(step_3_card)

    def update_markets(self):
        """
        Ensures that the current and future markets are correctly maintained.
        """
        # Fill the current market up to 4 plants
        while len(self.current_market) < 4 and self.future_market:
            self.current_market.append(self.future_market.pop(0))
        self.current_market.sort(key=lambda pp: pp.min_bid)

        # Fill the future market up to 4 plants from the deck if needed
        while len(self.future_market) < 4 and self.deck:
            self.future_market.append(self.deck.pop(0))
        self.future_market.sort(key=lambda pp: pp.min_bid)

    def remove_plant_from_market(self, power_plant):
        """
        Removes a purchased power plant from the current or future market.
        """
        if power_plant in self.current_market:
            self.current_market.remove(power_plant)
        elif power_plant in self.future_market:
            self.future_market.remove(power_plant)
        else:
            # Possibly an error if the plant is not found
            print(f"Power plant {power_plant.min_bid} not found in current or future market.")
        self.update_markets()

    def draw_new_plant(self):
        """
        Draws a new plant from the deck to refill the future market if needed.
        """
        if self.deck:
            new_plant = self.deck.pop(0)
            self.future_market.append(new_plant)
            self.future_market.sort(key=lambda pp: pp.min_bid)


# Resource bank initialization (optional to track outside ResourceMarket)
resource_bank = {
    "coal": 24,
    "oil": 24,
    "garbage": 24,
    "uranium": 12
}


# Data initialization for demonstration
power_plant_socket = [
    # Coal Plants
    PowerPlant(20,5,["coal"],3),
    PowerPlant(25,5,["coal"],2),
    PowerPlant(31,6,["coal"],3),
    PowerPlant(36,7,["coal"],3),
    PowerPlant(42,6,["coal"],2),
    # Oil Plants
    PowerPlant(16,3,["oil"],2),
    PowerPlant(26,5,["oil"],2),
    PowerPlant(32,6,["oil"],3),
    PowerPlant(35,5,["oil"],1),
    PowerPlant(40,6,["oil"],2),
    # Garbage Plants
    PowerPlant(19,3,["garbage"],2),
    PowerPlant(24,4,["garbage"],2),
    PowerPlant(30,6,["garbage"],3),
    PowerPlant(38,7,["garbage"],3),
    # Uranium Plants
    PowerPlant(17,2,["uranium"],1),
    PowerPlant(23,3,["uranium"],1),
    PowerPlant(28,4,["uranium"],1),
    PowerPlant(34,5,["uranium"],1),
    PowerPlant(39,6,["uranium"],1),
    # Hybrid Plants
    PowerPlant(21,4,["coal","oil"],2,True),
    PowerPlant(29,4,["coal","oil"],1,True),
    PowerPlant(46,7,["coal","oil"],3,True),
    # Eco Plants
    PowerPlant(18,2),
    PowerPlant(22,2),
    PowerPlant(27,3),
    PowerPlant(33,4),
    PowerPlant(37,4),
    PowerPlant(44,5),
    # Fusion Plant
    PowerPlant(50,6),
    # Step3 Card
    PowerPlant(99,99,is_step=True)
]

power_plant_plug = [
    # Coal Plants
    PowerPlant(4,1,["coal"],2),
    PowerPlant(8,2,["coal"],3),
    PowerPlant(10,2,["coal"],2),
    PowerPlant(15,3,["coal"],2),
    # Oil Plants
    PowerPlant(3,1,["oil"],2),
    PowerPlant(7,2,["oil"],3),
    PowerPlant(9,1,["oil"],1),
    # Garbage Plants
    PowerPlant(6,1,["garbage"],1),
    PowerPlant(14,2,["garbage"],2),
    # Uranium Plants
    PowerPlant(11,2,["uranium"],1),
    # Hybrid Plants
    PowerPlant(5,1,["coal","oil"],2,True),
    PowerPlant(12,2,["coal","oil"],2,True),
    # Eco Plants
    PowerPlant(13,1)
]

# Resource bank initialization
resource_bank = {
    "coal": 24,
    "oil": 24,
    "garbage": 24,
    "uranium": 12
}
