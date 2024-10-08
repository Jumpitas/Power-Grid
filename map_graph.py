import networkx as nx
import logging
from collections import deque # for graph search

# Configure logging
logging.basicConfig(level=logging.INFO)

citiesUS = {
    # Dark-Blue region
    "SEA": "Seattle",
    "POR": "Portland",
    "BOI": "Boise",
    "BIL": "Billings",
    "CHE": "Cheyenne",
    "DEN": "Denver",
    "OMA": "Omaha",

    # Light-Blue region
    "SFO": "San Francisco",
    "LVG": "Las Vegas",
    "LAX": "Los Angeles",
    "SLC": "Salt Lake City",
    "PHX": "Phoenix",
    "SDG": "San Diego",
    "SFE": "Santa Fe",

    # Red region
    "KSC": "Kansas City",
    "OKC": "Oklahoma City",
    "DAL": "Dallas",
    "HOU": "Houston",
    "NOA": "New Orleans",
    "MEM": "Memphis",
    "BHM": "Birmingham",

    # Yellow region
    "DUL": "Duluth",
    "FRG": "Fargo",
    "MIN": "Minneapolis",
    "CHI": "Chicago",
    "STL": "St. Louis",
    "CIN": "Cincinnati",
    "KNX": "Knoxville",

    # Orange region
    "WAS": "Washington",
    "NYC": "New York",
    "BUF": "Buffalo",
    "DET": "Detroit",
    "PHI": "Philadelphia",
    "BOS": "Boston",
    "PIT": "Pittsburgh",

    # Green region
    "RAL": "Raleigh",
    "MIA": "Miami",
    "TMP": "Tampa",
    "SAV": "Savannah",
    "JAX": "Jacksonville",
    "ATA": "Atlanta",
    "NRF": "Norfolk",
}

edgesUS = [
    ("SEA", "POR", 3),
    ("SEA", "BIL", 9),
    ("SEA", "BOI", 12),
    ("POR", "BOI", 13),
    ("POR", "SFO", 24),
    ("BIL", "CHE", 9),
    ("BIL", "BOI", 12),
    ("BIL", "FRG", 17),
    ("BIL", "MIN", 18),
    ("BOI", "SFO", 23),
    ("BOI", "SLC", 8),
    ("BOI", "CHE", 24),
    ("SFO", "SLC", 27),
    ("SFO", "LVG", 14),
    ("SFO", "LAX", 9),
    ("CHE", "MIN", 18),
    ("CHE", "OMA", 14),
    ("CHE", "DEN", 0),
    ("SLC", "LAX", 18),
    ("SLC", "SFE", 28),
    ("LAX", "LVG", 9),
    ("LAX", "SDG", 3),
    ("SDG", "LVG", 9),
    ("SDG", "PHX", 14),
    ("PHX", "LVG", 15),
    ("LVG", "SFE", 27),
    ("PHX", "SFE", 18),
    ("FRG", "DUL", 6),
    ("FRG", "MIN", 6),
    ("DUL", "MIN", 5),
    ("MIN", "OMA", 8),
    ("KSC", "OMA", 5),
    ("KSC", "DEN", 16),
    ("DEN", "SFE", 13),
    ("KSC", "SFE", 16),
    ("OKC", "SFE", 15),
    ("DAL", "SFE", 16),
    ("HOU", "SFE", 21),
    ("HOU", "DAL", 5),
    ("DAL", "OKC", 3),
    ("KSC", "OKC", 8),
    ("MEM", "STL", 7),
    ("MEM", "KSC", 12),
    ("MEM", "OKC", 14),
    ("MEM", "NOA", 7),
    ("MEM", "BHM", 6),
    ("MEM", "DAL", 12),
    ("NOA", "DAL", 12),
    ("HOU", "NOA", 8),
    ("CHI", "DUL", 12),
    ("CHI", "MIN", 8),
    ("CHI", "OMA", 13),
    ("CHI", "KSC", 8),
    ("CHI", "STL", 10),
    ("CHI", "CIN", 7),
    ("CHI", "DET", 7),
    ("DET", "DUL", 15),
    ("STL", "KSC", 6),
    ("STL", "CIN", 12),
    ("STL", "ATA", 12),
    ("BHM", "NOA", 11),
    ("JAX", "NOA", 16),
    ("DET", "BUF", 7),
    ("DET", "PIT", 6),
    ("DET", "CIN", 4),
    ("PIT", "CIN", 7),
    ("RAL", "CIN", 15),
    ("KNX", "CIN", 6),
    ("KNX", "ATA", 5),
    ("MIA", "TMP", 4),
    ("JAX", "TMP", 4),
    ("BHM", "JAX", 9),
    ("SAV", "JAX", 0),
    ("SAV", "ATA", 7),
    ("SAV", "RAL", 7),
    ("ATA", "RAL", 7),
    ("ATA", "BHM", 3),
    ("PIT", "RAL", 7),
    ("PIT", "BUF", 7),
    ("NYC", "BUF", 8),
    ("WAS", "PIT", 6),
    ("WAS", "PHI", 3),
    ("WAS", "NRF", 5),
    ("RAL", "NRF", 3),
    ("PHI", "NYC", 0),
    ("BOS", "NYC", 3),
]

class BoardMap:
    """
    This class stores the board data related to the map:
    - 'cities' is sa dictionary that maps a city TAG to its name
    - 'links' is a list of all the connections between 2 different tags
    - 'map' is the graph variable, it stores in each node:
        - city tag (code)
        - current owner (owner)
    """
    def __init__(self, cities, links):
        self.cities = cities
        self.links = links

        self.map = nx.Graph()

        # Each node is added here
        for code, city_name in cities.items():
            self.map.add_node(code, owner="")  # 'owner' initialized to an empty string, to be updated later

        # Add edges with weights (cost A -> B)
        self.map.add_weighted_edges_from(links)

    def city_name(self, tag):
        """
        Returns the name of the city.

        :param tag: the city 3-letter tag
        :return: city name string
        """
        if tag not in self.cities:
            logging.error(f"City with tag '{tag}' not found.")
            return None

        return self.cities[tag]

    def get_owner(self, tag):
        """
        Returns the current owner of a given city.

        :param tag: the city 3-letter tag
        :return: current owner of that city
        """
        if tag in self.map.nodes:
            return self.map.nodes[tag].get('owner', "") # returns owner else ""
        else:
            logging.error(f"City with tag '{tag}' not found.")
            return None

    def update_owner(self, player, tag):
        """
        Updates the owner of a city based on the provided city tag and player ID.

        :param player: the ID of the player who will now own the city
        :param tag: the 3-letter tag of the city
        :return: 0 or 1 if no errors occur, or something goes wrong respectively
        """
        if tag in self.map.nodes:
            self.map.nodes[tag]['owner'] = player
            return 0
        else:
            logging.error("Tag not found.")
            return 1

    def available_path(self, tag):
        """
        Finds the available path from a given city using Breadth-First Search.
        From the tag, looks for the current owner and checks the network for cities owned by the same player reachable by some path.

        :param tag: The 3-letter tag of the city
        :return:
        - A tuple containing:
          - The owner of the city
          - The size of the path (if the land isn't owned, return 0)
          - A list of the nodes visited (whose owner is the one who owns the tag on the call). Useful to keep track for better performance.
        """
        owner = self.get_owner(tag)

        if owner == "":
            return owner, 0, [tag]

        # BFS, using deque for efficiency
        visited_set = set()
        queue = deque([tag])
        path_size = 1

        visited_in_this_iteration = [tag]
        while queue:
            current_city = queue.popleft()  # first element of the deque
            if current_city not in visited_set:
                visited_set.add(current_city) # add to visited, but only increment path_size if the city's owner is the same

                # Add neighbors to the queue if they are owned by the same player
                for neighbor in self.map.neighbors(current_city): # networkX method
                    # print(neighbor)
                    if self.map.nodes[neighbor]['owner'] == owner and neighbor not in visited_set:
                        queue.append(neighbor)
                        visited_in_this_iteration.append(neighbor)
                        path_size += 1

        return owner, path_size, visited_in_this_iteration

    def has_ended(self, r):
        """
        A method helpful to determine if the game ended, returning who won if and only if it finds a connected subgraph with (at least) r nodes, all belonging to the same person.
        :param r: the required path size to end, since it varies with the amount of players selected
        :return:
        - A tuple containing:
          - If the game has ended (True or False)
          - The winner (empty string if no one won)
        """
        highest_path_size = -1
        highest_path_owner = ""

        visited = dict.fromkeys(self.cities.keys(), False)

        for k in visited.keys():
            if not visited[k]: # If that city has not been searched
                o, size, l = self.available_path(k)
                if size > highest_path_size:
                    highest_path_size = size
                    highest_path_owner = o
                for x in l:
                    visited[x] = True

        if highest_path_size == -1:
            logging.error("Either the game didn't start or something went wrong.")
            return False, ""
        else:
            if highest_path_size >= r:
                 return True, highest_path_owner
            else:
                return False, "" # someone might not win


'''
# test get_owner method
game = BoardMap(citiesUS, edgesUS)
game.update_owner('player1', 'ATA')
print(game.get_owner('ATA'))
'''

# test the BFS
game = BoardMap(citiesUS, edgesUS)
game.update_owner('player1', 'ATA')
game.update_owner('player1', 'KNX')
game.update_owner('player1', 'SAV')


print(game.available_path('ATA'))
print(game.has_ended(4))
