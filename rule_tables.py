# rule_tables.py

# Income table: Elektro earned based on the number of cities powered
city_cashback=[10,22,33,44,54,
               64,73,82,90,98,
               105,112,118,124,
               129,134,138,142,
               145,148,150]

# Resource replenishment table: Resources added to the market at the end of each turn
# Step: {Number of Players: {Resource: Amount}}
resource_replenishment = {
    1: {  # Step 1
        2: {'coal': 3, 'oil': 2, 'garbage': 1, 'uranium': 1},
        3: {'coal': 4, 'oil': 2, 'garbage': 1, 'uranium': 1},
        4: {'coal': 5, 'oil': 3, 'garbage': 2, 'uranium': 1},
        5: {'coal': 5, 'oil': 4, 'garbage': 3, 'uranium': 2},
        6: {'coal': 7, 'oil': 5, 'garbage': 3, 'uranium': 2},
    },
    2: {  # Step 2
        2: {'coal': 4, 'oil': 2, 'garbage': 2, 'uranium': 1},
        3: {'coal': 5, 'oil': 3, 'garbage': 3, 'uranium': 2},
        4: {'coal': 6, 'oil': 4, 'garbage': 3, 'uranium': 3},
        5: {'coal': 7, 'oil': 5, 'garbage': 5, 'uranium': 3},
        6: {'coal': 9, 'oil': 6, 'garbage': 5, 'uranium': 3},
    },
    3: {  # Step 3
        2: {'coal': 3, 'oil': 4, 'garbage': 3, 'uranium': 1},
        3: {'coal': 4, 'oil': 5, 'garbage': 4, 'uranium': 2},
        4: {'coal': 5, 'oil': 6, 'garbage': 5, 'uranium': 3},
        5: {'coal': 6, 'oil': 7, 'garbage': 6, 'uranium': 4},
        6: {'coal': 7, 'oil': 9, 'garbage': 6, 'uranium': 5},
    }
}


price_table = {
    "uranium": {1:16, 2:14, 3:12, 4:10, 
                  5:8, 6:7, 7:6, 8:5, 
                  9:4, 10:3, 11:2, 12:1},
    
    ("coal","oil","garbage"): {
        (1,2,3): 8,
        (4,5,6): 7,
        (7,8,9): 6,
        (10,11,12): 5,
        (13,14,15): 4,
        (16,17,18): 3,
        (19,20,21): 2,
        (22,23,24): 1
    }
}

# Number of connected cities required to start Step 2
step_start_cities = {
    2: 10,
    3: 7,
    4: 7,
    5: 7,
    6: 6,
}

# Number of connected cities required to end the game
game_end_cities = {
    2: 21,
    3: 17,
    4: 17,
    5: 15,
    6: 14
}


# Building cost table: Cost to build a house based on the current step
building_cost = {
    1: 10,  # Step 1
    2: 15,  # Step 2
    3: 20  # Step 3
}


remove_cards = {
    # Number of players: (plug,socket)
    2: (1,5),
    3: (2,6),
    4: (1,3),
    5: (0,0),
    6: (0,0)
}

def back_of_card(plant):
    if 3 <= plant.min_bid <= 15: return "plug"
    return "socket"