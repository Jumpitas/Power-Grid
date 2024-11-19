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

import networkx as nx
import logging

class BoardMap:
    def __init__(self, cities, links):
        self.nodes = cities
        self.edges = links
        self.step = 2  # Varies with the game phases

        self.map = nx.Graph()

        # Each node is added here
        for code, city_name in cities.items():
            self.map.add_node(code, owners=[])

        # Add edges with weights (cost A -> B)
        self.map.add_weighted_edges_from(links)

    def update_owner(self, player_jid, city_tag, max_occupancy=2):
        """
        Updates the owner of a city based on the provided city tag and player ID.

        :param player_jid: The JID of the player.
        :param city_tag: The 3-letter tag of the city.
        :param max_occupancy: Maximum number of owners per city.
        :return: 0 if successful, 1 otherwise.
        """
        if city_tag not in self.map:
            logging.error(f"City with tag '{city_tag}' not found.")
            return 1

        owners = self.map.nodes[city_tag].get('owners', [])
        if len(owners) >= max_occupancy:
            logging.error("City has reached maximum occupancy.")
            return 1

        if player_jid in owners:
            logging.info(f"Player {player_jid} already owns city {city_tag}.")
            return 0

        owners.append(player_jid)
        self.map.nodes[city_tag]['owners'] = owners
        logging.info(f"Player {player_jid} now owns city {city_tag}.")
        return 0

    def remove_owner(self, player_jid, city_tag):
        """
        Removes a player's ownership from a city.

        :param player_jid: The JID of the player.
        :param city_tag: The 3-letter tag of the city.
        :return: 0 if successful, 1 otherwise.
        """
        if city_tag not in self.map:
            logging.error(f"City with tag '{city_tag}' not found.")
            return 1

        owners = self.map.nodes[city_tag].get('owners', [])
        if player_jid in owners:
            owners.remove(player_jid)
            self.map.nodes[city_tag]['owners'] = owners
            logging.info(f"Player {player_jid} removed ownership from city {city_tag}.")
            return 0
        else:
            logging.error(f"Player {player_jid} does not own city {city_tag}.")
            return 1

    def get_current_owners(self, tag):
        """
        Returns the current owners of a given city.

        :param tag: The city 3-letter tag.
        :return: List of owners.
        """
        if tag in self.map.nodes:
            return self.map.nodes[tag].get('owners', [])
        else:
            logging.error(f"City with tag '{tag}' not found.")
            return []

    def is_connected(self, player_jid, new_city):
        """
        Check if the new_city can be connected to the player's existing network.

        :param player_jid: The JID of the player.
        :param new_city: The 3-letter tag of the city to connect.
        :return: True if connected, False otherwise.
        """
        # Get all cities owned by the player
        player_cities = [city for city, data in self.map.nodes(data=True) if player_jid in data.get('owners', [])]

        if not player_cities:
            # Player has no cities; can connect anywhere
            return True

        # Check if there's a path from new_city to any of the player's cities
        for owned_city in player_cities:
            if nx.has_path(self.map, new_city, owned_city):
                return True
        return False

    def get_connection_cost(self, player_jid, new_city):
        """
        Calculate the minimum connection cost to connect new_city to the player's existing network.

        :param player_jid: The JID of the player.
        :param new_city: The 3-letter tag of the city to connect.
        :return: Minimum connection cost or float('inf') if no connection exists.
        """
        player_cities = [city for city, data in self.map.nodes(data=True) if player_jid in data.get('owners', [])]

        if not player_cities:
            # Player has no cities; connection cost is 0
            return 0

        min_cost = float('inf')
        for owned_city in player_cities:
            try:
                path = nx.shortest_path(self.map, source=new_city, target=owned_city, weight='weight')
                cost = self.calculate_path_cost(path)
                if cost < min_cost:
                    min_cost = cost
            except nx.NetworkXNoPath:
                continue

        return min_cost if min_cost != float('inf') else float('inf')

    def calculate_path_cost(self, path):
        """
        Calculate the total cost of a given path.

        :param path: List of city tags representing the path.
        :return: Total cost as integer.
        """
        total_cost = 0
        for i in range(len(path) - 1):
            edge_data = self.map.get_edge_data(path[i], path[i + 1])
            if edge_data and 'weight' in edge_data:
                total_cost += edge_data['weight']
            else:
                logging.error(f"Missing weight for edge {path[i]} - {path[i + 1]}.")
                return float('inf')
        return total_cost

    def get_status(self):
        """
        Returns the current status of the map, including city ownership.

        :return: A dictionary with city tags as keys and lists of owners as values.
        """
        status = {}
        for city in self.map.nodes:
            status[city] = self.get_current_owners(city)
        return status

    def get_all_players(self):
        """
        Returns a dictionary with all players as keys and 0 as the initial value.

        :return: Dictionary {player_jid: 0, ...}
        """
        players = {}
        for city in self.map.nodes:
            owners = self.get_current_owners(city)
            for owner in owners:
                if owner not in players:
                    players[owner] = 0
        return players

    def count_player_cities(self):
        """
        Returns a dictionary with each player as the key and the number of cities they own as the value.

        :return: Dictionary {player_jid: city_count, ...}
        """
        player_city_count = self.get_all_players()

        # Iterate over all cities in the map
        for city in self.map.nodes:
            owners = self.get_current_owners(city)
            for owner in owners:
                if owner in player_city_count:
                    player_city_count[owner] += 1

        return player_city_count

    def has_ended(self, required_cities):
        """
        Checks if the game has ended.

        :param required_cities: The number of cities required for the game to end, varies with the number of players.
        :return: Tuple (Boolean indicating if the game ended, Winning player's JID or empty string).
        """
        player_city_count = self.count_player_cities()

        for player, count in player_city_count.items():
            if count >= required_cities:
                logging.info(f"Game has ended. Winner: {player} with {count} cities.")
                return True, player
        return False, ""

    def is_city_available(self, city_tag, step):
        """
        Check if a city is available for building.
        A city is available if:
        - It exists in the map.
        - Its occupancy is less than the step limit.
        """
        if city_tag not in self.map.nodes:
            logging.error(f"City with tag '{city_tag}' not found.")
            return False

        owners = self.map.nodes[city_tag].get('owners', [])
        return len(owners) <= 2