# Notas:
# - resource_type é deve sempre ser lista que guarda tipos de recursos que podem ser utilizados
# - resource_num é o número total de recursos que precisam de ser consumidos para ligar
# é assumido como 0 porque para as eólicas a max_storage tem de ser automaticamente 0
# - hybrid são as que usam mais do que 1 resource
# - restrições são colocadas aos agentes na parte de possible moves

import random

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
    # power_on deve também dar return de replenish_bank para 
    # repor o resource bank corretamente (nº de peças available importa)

    def power_on(self):
        # se o nº de resources in storage for igual ao necessário
        # para ligar power então é automático
        if (sum(self.storage.values()) == self.resource_num):
            replenish_bank = self.storage
            self.storage = {key: 0 for key in self.storage}
            self.available_storage += self.resource_num
            return replenish_bank

        # se for maior que o necessário e não híbrido
        # (não engloba menor que necessário porque se é menor não pode ligar)
        elif not self.is_hybrid:
            replenish_bank = {self.resource_type[0]: self.resource_num}
            self.storage[self.resource_type[0]] -= self.resource_num
            self.available_storage += self.resource_num
            return replenish_bank


        # caso contrário, tem de ser capaz de escolher
        # a combinação de recursos que quer utilizar
        # enquanto não escolher suficientes, faz um ciclo
        else:
            replenish_bank = {key: 0 for key in self.storage}
            counter = 0
            while counter < self.resource_num:
                for rtype in self.resource_type:
                    choice = int(input(f"How many of type {rtype} do you wish to consume? "))
                    replenish_bank[rtype] += choice
                    self.storage[rtype] -= choice
                    counter += choice

                    if counter > self.resource_num: 
                        print("Error: Consumed more resources than needed!!! ")
                    
                    elif counter == self.resource_num:
                        return replenish_bank
        return None


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
            return True
        return False
    
    def refill_market(self, step, nplayer):
        fillup = resource_replenishment[step][nplayer]
        for rtype, rnum in fillup:
            # há >= peças do que necessário e espaço disponível para o fazer
            if (resource_bank[rtype] >= rnum) and (self.in_market[rtype] + rnum <= self.max[rtype]):
                resource_bank[rtype] -= rnum
                self.in_market[rtype] += rnum
            # há >= peças do que necessário mas espaço menor do que o replenish
            elif (resource_bank[rtype] >= rnum):
                diff = self.max[rtype] - self.in_market[rtype]
                resource_bank[rtype] -= diff
                self.in_market[rtype] += diff
            # há <= peças do que necessário mas espaço suficiente para o replenish
            elif (self.in_market[rtype] + rnum <= self.max[rtype]):
                self.in_market[rtype] += resource_bank[rtype]
                resource_bank[rtype] = 0

    # refill das pecinhas
    def refill_bank(self, refill):
        for rtype, rnum in refill:
            resource_bank[rtype] += rnum


class PowerPlantMarket:
    def __init__(self):
        self.plug = power_plant_plug
        self.socket = power_plant_socket
        self.market = []
        self.deck = []
        #random.shuffle(self.deck)

    def setup(self, nplayers):
        # 8 in rulebook
        random.shuffle(self.plug)
        self.market = self.plug[:8]
        self.plug = self.plug[8:]
        self.market.sort(key=lambda plant: plant.min_bid)
        plug_card = [self.plug.pop()]

        # 9 in rulebook
        set_aside = remove_cards[nplayers]
        step3 = [self.socket.pop()]
        random.shuffle(self.socket)
        box = self.plug[:set_aside[0]] + self.socket[:set_aside[1]]
        self.plug = self.plug[set_aside[0]:]
        self.socket = self.socket[set_aside[1]:]

        # agora que vai deixar de haver separação, distinguir cartas usando back_of_card
        # topo do deck é index 0 e bottom é -1
        self.deck = self.socket + self.plug
        random.shuffle(self.deck)
        self.deck = plug_card + self.deck + step3

