from time import sleep
import random

from map_graph import BoardMap, citiesUS, edgesUS  # map class
from rule_tables import *
from objects import ResourceMarket, PowerPlantMarket

class Environment:
    def __init__(self, player_no):

        # ---------------  Full dictionaries imported ----------------
        self.city_cashback = city_cashback

        self.resource_replenishment = {} # {1: {resourceA:X, resourceB:Y}, 2: {...}}, key=step, already restrained to the player number
        for step in resource_replenishment:
            self.resource_replenishment[step] = resource_replenishment[step][player_no]

        self.price_table = price_table
        self.building_cost = building_cost

        # -------------  Dependent of the player number  -------------
        self.required_start_cities = step_start_cities[player_no]  # Number of connected cities required to start Step 2
        self.game_end_cities = game_end_cities[player_no]  # Required city ownership, uses the has_ended() of BoardMap
        self.remove_cards = remove_cards[player_no]  # This is a tuple (plug,socket)

        #--------------- Display current market state ----------------

        # From now on, follows the preparation steps order on the original order

        # 1) Map Instance
        self.map = BoardMap(citiesUS, edgesUS)  # we define the class here, that way we can update costs

        """
        if self.map:
            print("Map instance created.\n")
            sleep(1)
        """

        # falta escolher as cores das regioes que sao precisas, a subregiao do mapa



        # 2, 3) Create current available houses and elektro, current  based on number of players
        self.players = \
            {f'player{i + 1}':
                 {'houses': 22,
                  'elektro': 50,
                  'cities_owned': [],
                  'number_cities_owned': 0, # each time a new city is bought, increment
                  'cities_powered': [],
                  'power_plants': [],  # List of power plant numbers
                  'resources': {"coal": 0, "oil": 0, "garbage": 0, "uranium": 0},
        } for i in range(player_no)}

        """
        print("Players instance created.\nCurrent state: ")
        for player, stats in self.players.items():
            print(f"{player}:")
            for stat, value in stats.items():
                print(f"  {stat.capitalize()}: {value}")
            print()
        sleep(1)
        """

        # 4) Determine starting player order
        self.order_players = []
        for player in self.players:
            self.players[player]['houses'] -= 1
            self.order_players.append(player)
        random.shuffle(self.order_players)

        """
        print("Randomly generated player order: ", self.order_players)
        print("Check if houses was updated for the players: ", self.players['player1']['houses']) # should be 21
        """

        # 5) Create the Resource Market
        self.resource_market = ResourceMarket() # ver os comentarios la

        # 6) Corresponds to the resource bank variable on the objects.py

        # 7) Corresponds to the resource_replenishment variable defined above (dictionarynception)

        # 8) 9)
        self.power_plant_market = PowerPlantMarket()
        # precisa de revisao esta parte, pq nao e bem o mercado so
        # e preciso ver se a carta step3 ta bem progrmaada

env_test = Environment(3)






# falta perceber so a funcao final do rule_tables
# bfs e ou nao preciso, se for e preciso ser updated, se as cidades tem que estar ligadas
# tbm falta a selecao inicial das zonas, nao sei como querem fazer isso mas as tantas e preciso outro dict
# que ligue a zona A,B ou C (ou a cor) a uma lista das cidades
# e importante para a selecao inicial das zonas do mapa, pq acho que se forem menos players, ha menos zonas, ha menos grafo tbm
# e se for e preciso reduzir para um subgrafo que todas para toda edge (i,j) -> i, j pertencam as zonas legais
# 🤓👆