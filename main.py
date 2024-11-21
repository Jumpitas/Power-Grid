# main.py

import asyncio
import os

from game_manager import GameManagerAgent  # Adjusted import to match the module name
from player_agent import PowerGridPlayerAgent
from game_environment import Environment
import globals
from time import sleep

#######################  METHODS TO CREATE THE LOG  #########################
def create_log():
    """
    Creates or clears the log file named 'log.txt'.
    """
    with open("log.txt", "w") as log_file:
        # Opening in 'w' mode ensures the file is emptied if it exists.
        pass
    print("Log file 'log.txt' created or cleared.")


def update_log(message):
    """
    Appends the given string to the next line of the log file, called "log.txt".

    :argument:
        message (str): The message to append to the log file.
    """
    with open("log.txt", "a") as log_file:
        log_file.write(message + "\n")
    print(f"Message added to log: {message}")

#############################################################################
async def main():
    num_players = 3 # <- modifiable
    create_log() # reset log

    ascii_art = """\n\n\n
                 _______                                                       ______             __        __                            __                     
                /       \                                                     /      \           /  |      /  |                          /  |                    
                $$$$$$$  | ______   __   __   __   ______    ______          /$$$$$$  |  ______  $$/   ____$$ |       __    __   _______ $$/  _______    ______  
                $$ |__$$ |/      \ /  | /  | /  | /      \  /      \  ______ $$ | _$$/  /      \ /  | /    $$ |      /  |  /  | /       |/  |/       \  /      \ 
                $$    $$//$$$$$$  |$$ | $$ | $$ |/$$$$$$  |/$$$$$$  |/      |$$ |/    |/$$$$$$  |$$ |/$$$$$$$ |      $$ |  $$ |/$$$$$$$/ $$ |$$$$$$$  |/$$$$$$  |
                $$$$$$$/ $$ |  $$ |$$ | $$ | $$ |$$    $$ |$$ |  $$/ $$$$$$/ $$ |$$$$ |$$ |  $$/ $$ |$$ |  $$ |      $$ |  $$ |$$      \ $$ |$$ |  $$ |$$ |  $$ |
                $$ |     $$ \__$$ |$$ \_$$ \_$$ |$$$$$$$$/ $$ |              $$ \__$$ |$$ |      $$ |$$ \__$$ |      $$ \__$$ | $$$$$$  |$$ |$$ |  $$ |$$ \__$$ |
                $$ |     $$    $$/ $$   $$   $$/ $$       |$$ |              $$    $$/ $$ |      $$ |$$    $$ |      $$    $$/ /     $$/ $$ |$$ |  $$ |$$    $$ |
                $$/       $$$$$$/   $$$$$/$$$$/   $$$$$$$/ $$/                $$$$$$/  $$/       $$/  $$$$$$$/        $$$$$$/  $$$$$$$/  $$/ $$/   $$/  $$$$$$$ |
                                                                                                                                                       /  \__$$ |
                                                                                                                                                       $$    $$/ 
                                                                                                                                                        $$$$$$/  
                 __       __            __    __      __           ______                                   __                                                   
                /  \     /  |          /  |  /  |    /  |         /      \                                 /  |                                                  
                $$  \   /$$ | __    __ $$ | _$$ |_   $$/         /$$$$$$  |  ______    ______   _______   _$$ |_                                                 
                $$$  \ /$$$ |/  |  /  |$$ |/ $$   |  /  | ______ $$ |__$$ | /      \  /      \ /       \ / $$   |                                                
                $$$$  /$$$$ |$$ |  $$ |$$ |$$$$$$/   $$ |/      |$$    $$ |/$$$$$$  |/$$$$$$  |$$$$$$$  |$$$$$$/                                                 
                $$ $$ $$/$$ |$$ |  $$ |$$ |  $$ | __ $$ |$$$$$$/ $$$$$$$$ |$$ |  $$ |$$    $$ |$$ |  $$ |  $$ | __                                               
                $$ |$$$/ $$ |$$ \__$$ |$$ |  $$ |/  |$$ |        $$ |  $$ |$$ \__$$ |$$$$$$$$/ $$ |  $$ |  $$ |/  |                                              
                $$ | $/  $$ |$$    $$/ $$ |  $$  $$/ $$ |        $$ |  $$ |$$    $$ |$$       |$$ |  $$ |  $$  $$/                                               
                $$/      $$/  $$$$$$/  $$/    $$$$/  $$/         $$/   $$/  $$$$$$$ | $$$$$$$/ $$/   $$/    $$$$/                                                
                                                                           /  \__$$ |                                                                            
                                                                           $$    $$/                                                                             
                                                                            $$$$$$/                                                                              
                  ______                         __                                                                                                              
                 /      \                       /  |                                                                                                             
                /$$$$$$  | __    __   _______  _$$ |_     ______   _____  ____    _______                                                                        
                $$ \__$$/ /  |  /  | /       |/ $$   |   /      \ /     \/    \  /       |                                                                       
                $$      \ $$ |  $$ |/$$$$$$$/ $$$$$$/   /$$$$$$  |$$$$$$ $$$$  |/$$$$$$$/                                                                        
                 $$$$$$  |$$ |  $$ |$$      \   $$ | __ $$    $$ |$$ | $$ | $$ |$$      \                                                                        
                /  \__$$ |$$ \__$$ | $$$$$$  |  $$ |/  |$$$$$$$$/ $$ | $$ | $$ | $$$$$$  |                                                                       
                $$    $$/ $$    $$ |/     $$/   $$  $$/ $$       |$$ | $$ | $$ |/     $$/                                                                        
                 $$$$$$/   $$$$$$$ |$$$$$$$/     $$$$/   $$$$$$$/ $$/  $$/  $$/ $$$$$$$/                                                                         
                          /  \__$$ |                                                                                                                             
                          $$    $$/                                                                                                                              
                           $$$$$$/                                                                                                                               

                """

    ascii_art2 = """
        _______  _______           _______  _______         _______  _______ _________ ______              _______ __________ _        _______ 
        (  ____ )(  ___  )|\     /|(  ____ \(  ____ )       (  ____ \(  ____ )\__   __/(  __  \   |\     /|(  ____ \__   _ _/( (    /|(  ____ 
        | (    )|| (   ) || )   ( || (    \/| (    )|       | (    \/| (    )|   ) (   | (  \  )  | )   ( || (    \/   ) (   |  \  ( || (    \/
        | (____)|| |   | || | _ | || (__    | (____)| _____ | |      | (____)|   | |   | |   ) |  | |   | || (_____    | |   |   \ | || |      
        |  _____)| |   | || |( )| ||  __)   |     __)(_____)| | ____ |     __)   | |   | |   | |  | |   | |(_____  )   | |   | (\ \) || | ____ 
        | (      | |   | || || || || (      | (\ (          | | \_  )| (\ (      | |   | |   ) |  | |   | |      ) |   | |   | | \   || | \_  )
        | )      | (___) || () () || (____/\| ) \ \__       | (___) || ) \ \_____) (___| (__/  )  | (___) |/\____) |___) (___| )  \  || (___) |
        |/       (_______)(_______)(_______/|/   \__/       (_______)|/   \__/\_______/(______/   (_______)\_______)\_______/|/    )_)(_______)
                                                                                                                                               
         _______           _    __________________     _______  _______  _______  _       _________                                            
        (       )|\     /|( \   \__   __/\__   __/    (  ___  )(  ____ \(  ____ \( (    /|\__   __/                                            
        | () () || )   ( || (      ) (      ) (       | (   ) || (    \/| (    \/|  \  ( |   ) (                                               
        | || || || |   | || |      | |      | | _____ | (___) || |      | (__    |   \ | |   | |                                               
        | |(_)| || |   | || |      | |      | |(_____)|  ___  || | ____ |  __)   | (\ \) |   | |                                               
        | |   | || |   | || |      | |      | |       | (   ) || | \_  )| (      | | \   |   | |                                               
        | )   ( || (___) || (____/\| |   ___) (___    | )   ( || (___) || (____/\| )  \  |   | |                                               
        |/     \|(_______)(_______/)_(   \_______/    |/     \|(_______)(_______/|/    )_)   )_(                                               
                                                                                                                                               
         _______           _______ _________ _______  _______  _______                                                                         
        (  ____ \|\     /|(  ____ \ __   __/(  ____ \(       )(  ____ \                                                                        
        | (    \/( \   / )| (    \/   ) (   | (    \/| () () || (    \/                                                                        
        | (_____  \ (_) / | (_____    | |   | (__    | || || || (_____                                                                         
        (_____  )  \   /  (_____  )   | |   |  __)   | |(_)| |(_____  )                                                                        
              ) |   ) (         ) |   | |   | (      | |   | |      ) |                                                                        
        /\____) |   | |   /\____) |   | |   | (____/\| )   ( |/\____) |                                                                        
        \_______)   \_/   \_______)   )_(   (_______/|/     \|\_______)                                                                        
                                                                                                                                               
    """
    print(ascii_art)
    
    sleep(2.5)
    os.system("clear")


    # environment instance
    globals.environment_instance = Environment(num_players) # <- if this is globalized the rest works

    print(globals.environment_instance.players)

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