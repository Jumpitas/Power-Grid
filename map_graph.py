import networkx as nx

MapUS = nx.Graph()

cities = {
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
    "ATL": "Atlanta",
    "NRF": "Norfolk",
}

edges = [

    ("SEA", "POR", 3),    # Seattle to Portland
    ("SEA", "BIL", 9),  # Seattle to Billings
    ("SEA", "BOI", 12),   # Seattle to Boise
    ("POR", "BOI", 13),   # Portland to Boise
    ("POR", "SFO", 24),  # Portland to San Francisco
    ("BIL", "CHE", 9),  # Billings to Cheyenne
    ("BIL", "BOI", 12),   # Billings to Boise
    ("BIL", "FRG", 17),  # Billings to Fargo
    ("BIL", "MIN", 18),  # Billings to Minneapolis
    ("BOI", "", ),  # Billings to ............................. (verificado, SEA POR BIL, acrescentado para continuar a seguir tipo queue de BFS,  BOI-SFO-CHE-FRG-MIN









    ("CHE", "DEN", 8),    # Cheyenne to Denver
    ("DEN", "OMA", 13),   # Denver to Omaha


    ("SFO", "LVG", 9),    # San Francisco to Las Vegas
    ("SFO", "LAX", 9),    # San Francisco to Los Angeles
    ("LAX", "LVG", 9),    # Los Angeles to Las Vegas
    ("LAX", "SDG", 3),    # Los Angeles to San Diego
    ("LVG", "SLC", 12),   # Las Vegas to Salt Lake City
    ("SLC", "DEN", 21),   # Salt Lake City to Denver
    ("PHX", "LVG", 14),   # Phoenix to Las Vegas
    ("PHX", "SDG", 16),   # Phoenix to San Diego
    ("PHX", "SFE", 27),   # Phoenix to Santa Fe
    ("SFE", "DEN", 13),   # Santa Fe to Denver

    # Red region
    ("KSC", "STL", 12),   # Kansas City to St. Louis
    ("KSC", "OKC", 13),   # Kansas City to Oklahoma City
    ("OKC", "DAL", 8),    # Oklahoma City to Dallas
    ("DAL", "HOU", 7),    # Dallas to Houston
    ("DAL", "OKC", 13),   # Dallas to Oklahoma City
    ("HOU", "NOA", 12),   # Houston to New Orleans
    ("NOA", "MEM", 16),   # New Orleans to Memphis
    ("MEM", "BHM", 14),   # Memphis to Birmingham

    # Yellow region
    ("DUL", "FRG", 16),   # Duluth to Fargo
    ("DUL", "MIN", 10),   # Duluth to Minneapolis
    ("MIN", "CHI", 18),   # Minneapolis to Chicago
    ("CHI", "STL", 10),   # Chicago to St. Louis
    ("STL", "CIN", 8),    # St. Louis to Cincinnati
    ("CIN", "KNX", 7),    # Cincinnati to Knoxville

    # Orange region
    ("WAS", "PHI", 4),    # Washington to Philadelphia
    ("PHI", "NYC", 6),    # Philadelphia to New York
    ("NYC", "BUF", 8),    # New York to Buffalo
    ("BUF", "DET", 9),    # Buffalo to Detroit
    ("DET", "CHI", 9),    # Detroit to Chicago
    ("BUF", "PIT", 7),    # Buffalo to Pittsburgh
    ("PIT", "PHI", 10),   # Pittsburgh to Philadelphia
    ("PHI", "BOS", 9),    # Philadelphia to Boston

    # Green region
    ("RAL", "NRF", 4),    # Raleigh to Norfolk
    ("RAL", "ATL", 12),   # Raleigh to Atlanta
    ("RAL", "SAV", 8),    # Raleigh to Savannah
    ("SAV", "JAX", 4),    # Savannah to Jacksonville
    ("SAV", "ATL", 7),    # Savannah to Atlanta
    ("JAX", "TMP", 4),    # Jacksonville to Tampa
    ("TMP", "MIA", 5),    # Tampa to Miami
]
