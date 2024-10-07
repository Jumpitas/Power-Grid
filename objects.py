# Notas:
# - resource_type é uma lista que guarda tipos de recursos que podem ser utilizados
# - resource_num é o número total de recursos que podem ser consumidos de cada vez
# é assumido como 0 porque para as eólicas a max_storage tem de ser automaticamente 0
# - hybrid são as que usam mais do que 1 resource, eco são as eólicas que não usam resource


class PowerPlant:
    def __init__(self, price, resource_type=[], resource_num=0, is_hybrid=False, is_eco=False):
        self.price = price
        self.resource_type = resource_type
        self.in_storage = {}
        for item in self.resource_type: 
            self.in_storage[item]=0
        self.resource_num = resource_num
        self.is_hybrid = is_hybrid
        #self.is_eco = is_eco
        #self.max_storage = resource_num[1]*2
        self.available_storage = resource_num[1]*2
        

    def store_resources(self, type, num):
        if (type not in self.resource_type): 
            print(f"Type: {type} incompatible with {self.resource_type}")
            return
        if (num > self.available_storage): 
            print(f"Not enough space to store {num} {type}.")
            return

        self.in_storage[type] += num
        self.available_storage -= num

    
        

        

        





