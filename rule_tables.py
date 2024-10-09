# rule_tables.py

# Income table: Elektro earned based on the number of cities powered
city_cashback = {
    0: 10, 1: 22, 2: 33, 3: 44, 4: 54,
    5: 64, 6: 73, 7: 82, 8: 90, 9: 98,
    10: 105, 11: 112, 12: 118, 13: 124,
    14: 129, 15: 134, 16: 138, 17: 142,
    18: 145, 19: 148, 20: 150
}

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
    },
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
    6: 14,
}

# Maximum resource quantities in the market
resource_max_quantities = {
    'coal': 24,
    'oil': 24,
    'garbage': 24,
    'uranium': 12,
}

# Building cost table: Cost to build a house based on the current step
building_cost = {
    1: 10,  # Step 1
    2: 15,  # Step 2
    3: 20,  # Step 3
}
