# Notas:
# - resource_type é deve sempre ser lista que guarda tipos de recursos que podem ser utilizados
# - resource_num é o número total de recursos que precisam de ser consumidos para ligar
# é assumido como 0 porque para as eólicas a max_storage tem de ser automaticamente 0
# - hybrid são as que usam mais do que 1 resource
# - restrições são colocadas aos agentes na parte de possible moves


class PowerPlant:
    def __init__(self, min_bid, cities, resource_type=[], resource_num=0, is_hybrid=False, is_step=False):
        self.min_bid = min_bid
        self.cities = cities
        self.resource_type = resource_type
        self.storage = {item: 0 for item in self.resource_type}
        self.resource_num = resource_num
        self.is_hybrid = is_hybrid
        self.is_step = is_step
        self.available_storage = resource_num*2

    def store_resources(self, rtype, rnum):
        if rtype not in self.resource_type:
            print(f"Type: {rtype} incompatible with {self.resource_type}")
            return
        if rnum > self.available_storage:
            print(f"Not enough space to store {rnum} {rtype}.")
            return

        self.storage[rtype] += rnum
        self.available_storage -= rnum

    def order_resources(self, plant2, rtype): # de self para plant2
        self.storage[rtype] -= 1
        self.available_storage += 1
        plant2.storage[rtype] += 1
        plant2.available_storage -= 1

    # Nota: os resources usados voltam para o market!!!
    # power_on deve também dar return de replenish_market para 
    # repor o mercado corretamente

    def power_on(self):
        # se o nº de resources in storage for igual ao necessário
        # para ligar power então é automático
        if (sum(self.storage.values()) == self.resource_num):
            replenish_market = self.storage
            self.storage = {key: 0 for key in self.storage}
            self.available_storage += self.resource_num
            return True

        # se for maior que o necessário e não híbrido
        # (não engloba menor que necessário porque se é menor não pode ligar)
        elif not self.is_hybrid:
            replenish_market = {self.resource_type[0]: self.resource_num}
            self.storage[self.resource_type[0]] -= self.resource_num
            self.available_storage += self.resource_num
            return True


        # caso contrário, tem de ser capaz de escolher
        # a combinação de recursos que quer utilizar
        # enquanto não escolher suficientes, faz um ciclo
        else:
            replenish_market = {key: 0 for key in self.storage}
            counter = 0
            while counter < self.resource_num:
                for rtype in self.resource_type:
                    choice = int(input(f"How many of type {rtype} do you wish to consume? "))
                    replenish_market[rtype] += choice
                    self.storage[rtype] -= choice
                    counter += choice

                    if counter > self.resource_num: 
                        print("Error: Consumed more resources than needed!!! ")
                    
                    elif counter == self.resource_num:
                        return True
        return False


# Baralho de cartas originals

power_plant_deck = [
    # Coal Plants
    PowerPlant(4,1,["coal"],2),
    PowerPlant(8,2,["coal"],3),
    PowerPlant(10,2,["coal"],2),
    PowerPlant(15,3,["coal"],2),
    PowerPlant(20,5,["coal"],3),
    PowerPlant(25,5,["coal"],2),
    PowerPlant(31,6,["coal"],3),
    PowerPlant(36,7,["coal"],3),
    PowerPlant(42,6,["coal"],2),

    # Oil Plants
    PowerPlant(3,1,["oil"],2),
    PowerPlant(7,2,["oil"],3),
    PowerPlant(9,1,["oil"],1),
    PowerPlant(16,3,["oil"],2),
    PowerPlant(26,5,["oil"],2),
    PowerPlant(32,6,["oil"],3),
    PowerPlant(35,5,["oil"],1),
    PowerPlant(40,6,["oil"],2),

    # Garbage Plants
    PowerPlant(6,1,["garbage"],1),
    PowerPlant(14,2,["garbage"],2),
    PowerPlant(19,3,["garbage"],2),
    PowerPlant(24,4,["garbage"],2),
    PowerPlant(30,6,["garbage"],3),
    PowerPlant(38,7,["garbage"],3),

    # Uranium Plants
    PowerPlant(11,2,["uranium"],1),
    PowerPlant(17,2,["uranium"],1),
    PowerPlant(23,3,["uranium"],1),
    PowerPlant(28,4,["uranium"],1),
    PowerPlant(34,5,["uranium"],1),
    PowerPlant(39,6,["uranium"],1),

    # Hybrid Plants
    PowerPlant(5,1,["coal","oil"],2,True),
    PowerPlant(12,2,["coal","oil"],2,True),
    PowerPlant(21,4,["coal","oil"],2,True),
    PowerPlant(29,4,["coal","oil"],1,True),
    PowerPlant(46,7,["coal","oil"],3,True),

    # Eco Plants
    PowerPlant(13,1),
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
