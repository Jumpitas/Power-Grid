from map_graph import BoardMap, citiesUS, edgesUS  # map class
from rule_tables import *


class Environment:
    def __init__(self, player_no):
        self.map = BoardMap(citiesUS, edgesUS)  # we define the class here

        # ---------------  Full dictionaries imported ----------------
        self.city_cashback = city_cashback
        self.resource_replenishment = resource_replenishment
        self.price_table = price_table
        self.building_cost = building_cost

        # -------------  Dependent of the player number  -------------
        self.required_start_cities = step_start_cities[player_no]  # Number of connected cities required to start Step 2
        self.game_end_cities = game_end_cities[player_no]  # Required city ownership, uses the has_ended() of BoardMap
        self.remove_cards = remove_cards[player_no]  # This is a tuple (plug,socket)

        # falta perceber so a funcao final do rule_tables
        # bfs e ou nao preciso, se for e preciso ser updated, se as cidades tem que estar ligadas
        # tbm falta a selecao inicial das zonas, nao sei como querem fazer isso mas as tantas e preciso outro dict
        # que ligue a zona A,B ou C (ou a cor) a uma lista das cidades
        # e importante para a selecao inicial das zonas do mapa, pq acho que se forem menos players, ha menos zonas, ha menos grafo tbm
        # e se for e preciso reduzir para um subgrafo que todas para toda edge (i,j) -> i, j pertencam as zonas legais
        # 🤓👆
