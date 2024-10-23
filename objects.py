# objects.py

class PowerPlant:
    def __init__(self, min_bid, cities=None, resource_type=[], resource_num=0, is_hybrid=False, capacity=None, name=None):
        self.min_bid = min_bid
        self.cities = cities if cities is not None else capacity
        self.resource_type = resource_type
        self.storage = {item: 0 for item in self.resource_type}
        self.resource_num = resource_num
        self.is_hybrid = is_hybrid
        self.available_storage = resource_num * 2
        self.capacity = capacity if capacity is not None else self.cities
        self.name = name

    def store_resources(self, rtype, rnum):
        if rtype not in self.resource_type:
            print(f"Type: {rtype} incompatible with {self.resource_type}")
            return
        if rnum > self.available_storage:
            print(f"Not enough space to store {rnum} {rtype}.")
            return

        self.storage[rtype] += rnum
        self.available_storage -= rnum

    def to_dict(self):
        return {
            'min_bid': self.min_bid,
            'resource_type': self.resource_type,
            'resource_num': self.resource_num,
            'capacity': self.capacity,
            'is_hybrid': self.is_hybrid,
            'name': self.name
        }

    def order_resources(self, plant2, rtype):  # from self to plant2
        self.storage[rtype] -= 1
        self.available_storage += 1
        plant2.storage[rtype] += 1
        plant2.available_storage -= 1

    # Note: resources used are returned to the market!!!
    # power_on should also return replenish_market to
    # replenish the market correctly

    def power_on(self):
        if sum(self.storage.values()) < self.resource_num:
            return False  # Not enough resources

        if not self.is_hybrid:
            resource = self.resource_type[0]
            if self.storage[resource] >= self.resource_num:
                self.storage[resource] -= self.resource_num
                self.available_storage += self.resource_num
                return True
            else:
                return False  # Not enough resources of the required type

        else:
            # Hybrid plant: choose resources to consume
            consumed = {}
            remaining_needed = self.resource_num
            for resource in self.resource_type:
                available = self.storage.get(resource, 0)
                to_consume = min(available, remaining_needed)
                consumed[resource] = to_consume
                remaining_needed -= to_consume
                if remaining_needed == 0:
                    break

            if remaining_needed > 0:
                return False  # Not enough resources

            # Consume the resources
            for resource, amount in consumed.items():
                self.storage[resource] -= amount
                self.available_storage += amount

<<<<<<< Updated upstream
=======
# Baralho de cartas original

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


# Resources só são repostas se houver suficientes no "Resource Bank"
# resource bank representa o número de peças de madeira disponíveis
# só é possível repôr o market se existirem peças suficientes

from rule_tables import price_table, resource_replenishment, remove_cards

resource_bank = {
    "coal": 24,
    "oil": 24,
    "garbage": 24,
    "uranium": 12
}


class ResourceMarket:
    def __init__(self, coal, oil, garbage, uranium):
        self.max = {"coal": 24,"oil": 24,
                    "garbage": 24,"uranium": 12} 
        # quantidades atuais de recursos no mercado
        self.in_market = {"coal":coal, "oil":oil,
                          "garbage":garbage, "uranium":uranium}

    def resource_price(self, rtype):
        # Se não houver disponível
        if self.in_market[rtype]==0: return None

        if rtype == "uranium": return price_table[rtype][self.in_market["uranium"]]
        else: 
            for key, price in price_table[rtype].items():
                if self.in_market[str(rtype)] in key:
                    return price
                
    # restrição de agente: só compra se tiver dinheiro e puder guardar
    def purchase_batch(self, rtype, rnum):
        if self.in_market[rtype] >= rnum:
            self.in_market[rtype] -= rnum
>>>>>>> Stashed changes
            return True


# Initialize the deck of power plants
power_plant_deck = [
    # Coal Plants
    PowerPlant(min_bid=4, cities=1, resource_type=["coal"], resource_num=2),
    PowerPlant(min_bid=8, cities=2, resource_type=["coal"], resource_num=3),
    PowerPlant(min_bid=10, cities=2, resource_type=["coal"], resource_num=2),
    PowerPlant(min_bid=15, cities=3, resource_type=["coal"], resource_num=2),
    PowerPlant(min_bid=20, cities=5, resource_type=["coal"], resource_num=3),
    PowerPlant(min_bid=25, cities=5, resource_type=["coal"], resource_num=2),
    PowerPlant(min_bid=31, cities=6, resource_type=["coal"], resource_num=3),
    PowerPlant(min_bid=36, cities=7, resource_type=["coal"], resource_num=3),
    PowerPlant(min_bid=42, cities=6, resource_type=["coal"], resource_num=2),

    # Oil Plants
    PowerPlant(min_bid=3, cities=1, resource_type=["oil"], resource_num=2),
    PowerPlant(min_bid=7, cities=2, resource_type=["oil"], resource_num=3),
    PowerPlant(min_bid=9, cities=1, resource_type=["oil"], resource_num=1),
    PowerPlant(min_bid=16, cities=3, resource_type=["oil"], resource_num=2),
    PowerPlant(min_bid=26, cities=5, resource_type=["oil"], resource_num=2),
    PowerPlant(min_bid=32, cities=6, resource_type=["oil"], resource_num=3),
    PowerPlant(min_bid=35, cities=5, resource_type=["oil"], resource_num=1),
    PowerPlant(min_bid=40, cities=6, resource_type=["oil"], resource_num=2),

    # Garbage Plants
    PowerPlant(min_bid=6, cities=1, resource_type=["garbage"], resource_num=1),
    PowerPlant(min_bid=14, cities=2, resource_type=["garbage"], resource_num=2),
    PowerPlant(min_bid=19, cities=3, resource_type=["garbage"], resource_num=2),
    PowerPlant(min_bid=24, cities=4, resource_type=["garbage"], resource_num=2),
    PowerPlant(min_bid=30, cities=6, resource_type=["garbage"], resource_num=3),
    PowerPlant(min_bid=38, cities=7, resource_type=["garbage"], resource_num=3),

    # Uranium Plants
    PowerPlant(min_bid=11, cities=2, resource_type=["uranium"], resource_num=1),
    PowerPlant(min_bid=17, cities=2, resource_type=["uranium"], resource_num=1),
    PowerPlant(min_bid=23, cities=3, resource_type=["uranium"], resource_num=1),
    PowerPlant(min_bid=28, cities=4, resource_type=["uranium"], resource_num=1),
    PowerPlant(min_bid=34, cities=5, resource_type=["uranium"], resource_num=1),
    PowerPlant(min_bid=39, cities=6, resource_type=["uranium"], resource_num=1),

    # Hybrid Plants
    PowerPlant(min_bid=5, cities=1, resource_type=["coal", "oil"], resource_num=2, is_hybrid=True),
    PowerPlant(min_bid=12, cities=2, resource_type=["coal", "oil"], resource_num=2, is_hybrid=True),
    PowerPlant(min_bid=21, cities=4, resource_type=["coal", "oil"], resource_num=2, is_hybrid=True),
    PowerPlant(min_bid=29, cities=4, resource_type=["coal", "oil"], resource_num=1, is_hybrid=True),
    PowerPlant(min_bid=46, cities=7, resource_type=["coal", "oil"], resource_num=3, is_hybrid=True),

    # Eco Plants
    PowerPlant(min_bid=13, cities=1),
    PowerPlant(min_bid=18, cities=2),
    PowerPlant(min_bid=22, cities=2),
    PowerPlant(min_bid=27, cities=3),
    PowerPlant(min_bid=33, cities=4),
    PowerPlant(min_bid=37, cities=4),
    PowerPlant(min_bid=44, cities=5),

    # Fusion Plant
    PowerPlant(min_bid=50, cities=6)
]
