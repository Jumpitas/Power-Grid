# main.py

import asyncio
from manager_idea import GameManagerAgent  # Adjusted import to match the module name
from player_agent import PowerGridPlayerAgent
from game_environment import Environment


async def main():
    num_players = 2 # <- modifiable

    # environment instance
    global environment_instance
    environment_instance = Environment(num_players)

    if not (2 <= num_players <= 6):
        raise ValueError("Number of players must be between 2 and 6.")

    # define ids, passwords based on the number of players
    players = []
    for i in range(1, num_players + 1):
        player_jid = f"player{i}@localhost"
        player_passwd = f"player{i}password"
        player = PowerGridPlayerAgent(player_jid, player_passwd, player_id=i)
        players.append(player)

    # start the player agents
    for player in players:
        await player.start()
        print(f"Player {player.player_id} started.")

    # Create and start game manager agent
    gamemanager_jid = "gamemanager@localhost"
    gamemanager_passwd = "gamemanagerpassword"
    player_jids = [f"player{i}@localhost" for i in range(1, num_players + 1)]

    gamemanager = GameManagerAgent(gamemanager_jid, gamemanager_passwd, player_jids)
    await gamemanager.start()
    print("Game manager started.")

    print("All agents started. Game is running.")

    try:
        # Keep the main coroutine running as long as the game manager is alive
        while gamemanager.is_alive():
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nGame interrupted by user.")
    finally:
        # Gracefully stop all agents
        for player in players:
            await player.stop()
            print(f"Player {player.player_id} stopped.")
        await gamemanager.stop()
        print("Game manager stopped.")
        print("Agents stopped. Game over.")

if __name__ == "__main__":
    asyncio.run(main())