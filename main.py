# main.py

import asyncio
from game_manager_agent import GameManagerAgent
from player_agent import PowerGridPlayerAgent

async def main():
    # Define player JIDs and passwords
    player1_jid = "player1@localhost"
    player1_passwd = "player1password"
    player2_jid = "player2@localhost"
    player2_passwd = "player2password"

    # Create player agents
    player1 = PowerGridPlayerAgent(player1_jid, player1_passwd, player_id=1)
    player2 = PowerGridPlayerAgent(player2_jid, player2_passwd, player_id=2)

    # Start player agents
    await player1.start()
    print(f"Player {player1.player_id} started.")
    await player2.start()
    print(f"Player {player2.player_id} started.")

    # Create game manager agent
    gamemanager_jid = "gamemanager@localhost"
    gamemanager_passwd = "gamemanagerpassword"
    player_jids = [player1_jid, player2_jid]

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
        await player1.stop()
        print(f"Player {player1.player_id} stopped.")
        await player2.stop()
        print(f"Player {player2.player_id} stopped.")
        await gamemanager.stop()
        print("Game manager stopped.")
        print("Agents stopped. Game over.")

if __name__ == "__main__":
    asyncio.run(main())
