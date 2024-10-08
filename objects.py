# Notas:
# - resource_type é deve sempre ser lista que guarda tipos de recursos que podem ser utilizados
# - resource_num é o número total de recursos que precisam de ser consumidos para ligar
# é assumido como 0 porque para as eólicas a max_storage tem de ser automaticamente 0
# - hybrid são as que usam mais do que 1 resource
# - restrições são colocadas aos agentes na parte de possible moves


class PowerPlant:
    def __init__(self, min_bid, cities, resource_type, resource_num=0, is_hybrid=False):
        self.min_bid = min_bid
        self.cities = cities
        self.resource_type = resource_type
        self.storage = {item: 0 for item in self.resource_type}
        self.resource_num = resource_num
        self.is_hybrid = is_hybrid
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
