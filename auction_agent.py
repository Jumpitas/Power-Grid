"""
O auction agent interage com os players todos.

- o jogador que esta no seu turno, escolhe uma planta do available market
    - se for preciso, esse available market e recebido pelo auction agent
    - outra opcao e o player dizer a planta, e o auction -> market_manager

- depois por ordem, o player tem direito a 2 acoes (continua ate haver n-1 passes seguidos, n=num de jogadores):
    - raise the bid (no minimo 1 elektro)
    - passar (nao podem voltar a daar bet nesta ronda de bidding, precisam de uma flag ou assim)

- no fim existe um bid_winner, um amount de elektros que pagou e a planta que comprou

- esse player fica marcado ate ao fim da ronda, tendo em conta que so pode voltar a comprar na prox ronad

- e preciso comunicar com o mercado
    - e preciso remover a planta em questao e sacar outra do deck
    - o market e ordenado???????????

- regras adicionais que chateiam bue
    - um jogador so pode ter 3 plantas no max, tem a opcao de, se comprar outra, descartar uma das atuais
    - !!!!!!!!!!!!!!!!step 3, nao sei como functiona!!!!!!!!!!!!!!!!!!
"""

import spade
from spade.behaviour import CyclicBehaviour
from spade.message import Message


class AuctionAgent(spade.agent.Agent):
    class AuctionBehaviour(CyclicBehaviour):
        async def run(self):
            # Wait for the first player to choose a plant
            print("Waiting for the first player to choose a plant...")
            msg = await self.receive(timeout=30)  # Receive the plant choice from the first player
            if msg:
                selected_plant = msg.body
                print(f"Received plant choice: {selected_plant} from {msg.sender}")

                # Transmit the message containing the chosen plant to all players
                for player in self.agent.players:
                    broadcast_msg = Message(to=player)
                    broadcast_msg.body = f"Plant chosen: {selected_plant}"
                    await self.send(broadcast_msg)
                    print(f"Broadcasted plant choice to {player}")
            else:
                print("No plant was chosen.")

            # os players vao ter que fazer a sua decisao com base na planta escolhida


            # 2. Receive bids from players, auction logic here, bidding strategy on the agent
            players_passed = 0
            highest_bid = 0
            current_winner = None
            while players_passed < len(self.agent.players) - 1: # numero de players, porque assim se forem 6 e passarem 5, ganha o que sobra (trivialmente)
                msg = await self.receive(timeout=10)  # Wait for a player's response
                if msg:
                    action = msg.body.split(":") # a acao transmitida pelo player vai ser uma string tipo
                    # "bid:10" ou "pass:99", algo assim acho que fazia sentido e englobaba o importante
                    player = msg.sender

                    if action[0] == "bid":
                        bid_amount = int(action[1])
                        if bid_amount > highest_bid:
                            highest_bid = bid_amount
                            current_winner = player
                        players_passed = 0  # Reset pass count
                    elif action[0] == "pass":
                        players_passed += 1 # acaba se chega aqui n-1 vezes, se ohuver n-1 "bid actions"

            # 3. Declare winner and update market
            if current_winner:
                msg = Message(to=current_winner)
                msg.body = f"{str(current_winner)} won the auction with {highest_bid} Elektros."
                await self.send(msg)
                self.agent.market_manager.remove_plant(self.agent.current_plant)
                # Mark the player as having purchased a plant this round

    async def setup(self):
        print("Auction Agent started.")
        # self.market_manager = e preciso definir isto fs
        self.players = ["player1@localhost", "player2@localhost"] # todos os players
        """
        b = self.AuctionBehaviour()
        self.add_behaviour(b)
        """