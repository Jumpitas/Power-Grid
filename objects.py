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

    '''
    def __repr__(self):
        return (f"PowerPlant("
                f"min_bid={self.min_bid}, "
                f"cities={self.cities}, "
                f"resource_type={self.resource_type}, "
                f"resource_num={self.resource_num}, "
                f"is_hybrid={self.is_hybrid}, "
                f"is_step={self.is_step})")
    '''

    def __repr__(self):
        #return (f"Price: {self.min_bid}, Powering Capacity: {self.cities}, Resource Type: {self.resource_type}")
        return (f"({self.min_bid}$,{self.cities}cap,{self.resource_type})") # price, capacity, type

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

    def to_dict(self):
        """
        Serializes the PowerPlant object to a dictionary.
        """
        return {
            'min_bid': self.min_bid,
            'cities': self.cities,
            'resource_type': self.resource_type,
            'resource_num': self.resource_num,
            'is_hybrid': self.is_hybrid,
            'is_step': self.is_step
            # Optionally, include storage and available_storage if needed
        }

    @staticmethod
    def from_dict(data):
        """
        Deserializes a dictionary to a PowerPlant object.
        """
        return PowerPlant(
            min_bid=data.get('min_bid', 0),
            cities=data.get('cities', 0),
            resource_type=data.get('resource_type', []),
            resource_num=data.get('resource_num', 0),
            is_hybrid=data.get('is_hybrid', False),
            is_step=data.get('is_step', False)
        )

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
        def format_powerplant(pp):
            # Format each PowerPlant's details as a readable string
            resource_str = ", ".join(pp.resource_type)  # Combine the resources into a single string
            return (f"  Min Bid: {pp.min_bid}, "
                    f"Cities: {pp.cities}, "
                    f"Resources: {resource_str}, "
                    f"Resource Num: {pp.resource_num}, "
                    f"Hybrid: {pp.is_hybrid}, "
                    f"Step: {pp.is_step}")

        # Format current market and future market
        current_market_str = "\n".join([format_powerplant(pp) for pp in self.current_market])
        future_market_str = "\n".join([format_powerplant(pp) for pp in self.future_market])

        # formatted string representation
        return (f"Current Market:\n{current_market_str},\n\n"
                f"Future Market:\n{future_market_str},\n\n"
                f"Deck Size: {len(self.deck)}")

    def _initialize_markets(self):
        """
        Initializes the Current Market and Future Market with the lowest min_bid power plants.
        """
        # Combine power plant sets
        all_plants = power_plant_plug + power_plant_socket

        # Shuffle them to ensure randomness before sorting
        random.shuffle(all_plants)

        # Remove power plants based on player count as per game rules
        plug_to_remove, socket_to_remove = remove_cards.get(self.player_count, (0, 0))
        removed_plug = power_plant_plug[:plug_to_remove] if plug_to_remove else []
        removed_socket = power_plant_socket[:socket_to_remove] if socket_to_remove else []

        # Filter out the removed power plants
        all_plants = [plant for plant in all_plants if plant not in removed_plug + removed_socket]

        # Sort all_plants ascendingly by min_bid
        all_plants_sorted = sorted(all_plants, key=lambda pp: pp.min_bid)

        # Assign the first 4 to Current Market
        self.current_market = all_plants_sorted[:4]

        # Assign the next 4 to Future Market
        self.future_market = all_plants_sorted[4:8]

        # Assign the remaining to Deck
        self.deck = all_plants_sorted[8:]

        #print(f"Initial Current Market: {self.current_market}")
        #print(f"Initial Future Market: {self.future_market}")
        #print(f"Deck has {len(self.deck)} power plants.")

    def update_markets(self):
        """
        Replenishes the Current and Future Markets from the Deck when needed.
        """
        # Fill Current Market up to 4 plants
        while len(self.current_market) < 4 and self.future_market:
            self.current_market.append(self.future_market.pop(0))
        self.current_market.sort(key=lambda pp: pp.min_bid)

        # Fill Future Market up to 4 plants
        while len(self.future_market) < 4 and self.deck:
            self.future_market.append(self.deck.pop(0))
        self.future_market.sort(key=lambda pp: pp.min_bid)

    def remove_plant_from_market(self, power_plant):
        """
        Removes a purchased power plant from the Current or Future Market.
        """
        if power_plant in self.current_market:
            self.current_market.remove(power_plant)
        elif power_plant in self.future_market:
            self.future_market.remove(power_plant)
        else:
            print(f"Power plant with min_bid {power_plant.min_bid} not found in Current or Future Market.")
            return

        # Replenish the markets
        self.update_markets()

    def draw_new_plant(self):
        """
        Draws a new power plant from the Deck to replenish the Future Market.
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


