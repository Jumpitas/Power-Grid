# Recap

## Summary of the game

In this chapter we explain how the game flow actually works, to clarify some of the rules. This can be used as a map to guide all the steps of the project.

The game is **played over several rounds**. **Each round of the game has five phases**. In each phase, all players take their actions
in the order specified for the phase before the game continues to the next phase. The five phases are:

1. **Determine Player Order:** This is quite simple, as the order is based on number of cities descending essentially, which can be accessed in the **game_manager**, in the method `determine_player_order()`;
   
2. **Auction Power Plants:** This is the phase in which a given player chooses a powerplant to bid on, and then, there is a interaction between the manager and all the players (as a normal auction), to get and send all the bids, choices in either passing or no, etc. It takes is consideration that a player can only buy a powerplant per round, and the elektro ($) balance on his inventory;

3. **Buy Resources:** Players **can buy resources of different types**, those being used to supply the power plants, which latter feed energy to the cities owned;

4. **Build Houses:** Choose cities of the map graph, to build on. The map is updated accordingly, the inventory as well, and we can keep track of all important aspects of the game by carefully reviewing the logs;
   
5. **Bureaucracy:** The players finally allocate the energy to their cities, getting revenue (in elektro $) which can be later used to buy more resources and powerplants.

## Environment

The environment has a lot of different elements, as referenced in the presentation, so this is a more in-depth explanation of those.

- **Map Graph**: The map is built using the *NetworkX* Module for graph building. All the nodes and edges were "hand-written" to accurately represent the US version of the map. The map belongs to the `BoardMap` of the **map_graph.py** script.

- **Power Plant Market**: This is a very important aspect of the game flow. This is an instance of the class `PowerPlantMarket` defined on the script **objects.py** and it **contains the current market**, the **future market**, and the **size of the deck**. Each Market by itself contains 3 powerplants, which are themselves individual objects, defined in the same file, on the class `PowerPlant`. Each PowerPlant has many attributes, the most important being the number of cities that they can power, and the type of resources to supply them.

- **Resource Market**: Again, another object, this one holds the current market, and the class `ResourceMarket` contains the methods to replenish after they are bought.

- **Player's Inventory**: We decided to put the **player's inventory on the environment**, and each player can have access and change their own, due to the following: **in real life, each person's resources, powerplants and cities owned are placed publicly on the board**, and every other player can see it and make decisions influenced by that. For that reason, for the environment to fulfill the function of board, we proceeded as described.

- **Other Variables**: This game has A LOT of rules, and different gimmicks which make the implementation way harder than it should. In the files **objects.py** and **rule_tables** lie a lot of dictionaries that store different varlestiables, defined for different players. For example, in the **objects.py** file, there is a dictionary `resource_replenishment` which has all the possibilities for each player number, and each step.

## Simplifications

After the conversation with the teacher **António Castro**, we followed his adviced and made some simplifications that we considered not to affect the **MAS interactions**, but only complicate the game logic.

- **Step**: The step, in the original game, is a rule, that is triggered by some events, and change some rules regarding the **amounts** of replenishments, costs of building_costs, etc. The **objective of the step is to accelerate the game** and there is a point to be made regarding the decision-making strategy for the players (if experienced). For that reason, we decided to fully remove the step, but **nevertheless, most of the required implementation for the step to work is made**. The step is always set to 2.

- **Discount Token**: Quote from the **Recharged-Rules**: "First, the players place the discount token on the smallest power plant in the current market. The minimum bid for this power plant is reduced to 1 Elektro regardless of the actual number of the power plant." It does not affect the game that much, and was being quite a problem on the development of the phase 2.

- **Cash**: The game has physical cash, but we **simplified to not perform exchanges**, and the current balance being an integer attribute of the inventory.

- **Color zones**: In the beggining of the game, the **players agree on a subset of the map to play**, considering the color of the region the cities are in. The city vertices of the graph, when handwritten, were already split into different color zones, but **we decided to go always with the full map**, since it only makes the map larger, and not affect the playability.

## Instructions to run the code

- To get the live status of the game, corresponding to the environment, phase, etc, there is a UI available on running main.py.

- Guarantee that the venv has the pandas module, and spade dependencies. To run on the VM, after installing pandas, just:
    - open a terminal
    - activate the corresponding venv, using `pyenv activate env_name`
    - For the UI to be formatted, the terminal window should be Full Screen, 16:9, 1920:1080
    - run main.py (python3 main.py)

- To read the log, there is a file being generated with the run of the script, called 'log.txt'
    - To get the live updates corresponding to all the actions of the agents from the log file, run the following bash script
    - `while true; do clear; cat log.txt ; sleep 1; done`


