# player_agent.py

import asyncio
import random  # Ensure random is imported
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message
import json

class PowerGridPlayerAgent(Agent):
    def __init__(self, jid, password, player_id):
        super().__init__(jid, password)
        self.player_id = player_id
        self.cities = []  # List of city tags where the player has built
        self.power_plants = []  # List of power plant dictionaries
        self.resources = {"coal": 0, "oil": 0, "garbage": 0, "uranium": 0}
        self.elektro = 50  # Starting money
        self.connected_cities = 0
        self.power_plant_market = []  # Latest power plant market info
        self.step = 1  # Current game step

    class ReceivePhaseBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=10)
            if msg:
                sender = str(msg.sender).split('/')[0]

                # Parse the JSON content of the message
                try:
                    data = json.loads(msg.body)
                except json.JSONDecodeError:
                    print(f"Player {self.agent.player_id} received invalid JSON.")
                    return

                phase = data.get("phase")
                action = data.get("action")

                if phase == "setup":
                    # Handle setup phase
                    player_order = data.get("player_order")
                    print(f"Player {self.agent.player_id} received setup information. Position: {player_order}")
                    # Additional setup logic if needed

                elif phase == "phase1":
                    # Handle player order notification
                    player_order = data.get("player_order")
                    print(f"Player {self.agent.player_id} is in position {player_order}")

                elif phase == "phase2":
                    if action == "choose_or_pass":
                        # Decide whether to start an auction or pass
                        power_plant_market = data.get("power_plants", [])
                        can_pass = data.get("can_pass", True)
                        self.agent.power_plant_market = power_plant_market
                        if can_pass:
                            # Decide to pass or choose a power plant
                            if self.should_pass():
                                choice_msg = Message(to=sender)
                                choice_data = {
                                    "choice": "pass"
                                }
                                choice_msg.body = json.dumps(choice_data)
                                await self.send(choice_msg)
                                print(f"Player {self.agent.player_id} decides to pass on starting an auction.")
                            else:
                                chosen_plant_number = self.choose_power_plant_to_auction(power_plant_market)
                                if chosen_plant_number is not None:
                                    choice_msg = Message(to=sender)
                                    choice_data = {
                                        "choice": "auction",
                                        "power_plant_number": chosen_plant_number
                                    }
                                    choice_msg.body = json.dumps(choice_data)
                                    await self.send(choice_msg)
                                    print(f"Player {self.agent.player_id} chooses to auction power plant {chosen_plant_number}.")
                                else:
                                    # Cannot afford any power plant, so pass
                                    choice_msg = Message(to=sender)
                                    choice_data = {
                                        "choice": "pass"
                                    }
                                    choice_msg.body = json.dumps(choice_data)
                                    await self.send(choice_msg)
                                    print(f"Player {self.agent.player_id} cannot afford any power plant and passes.")
                        else:
                            # Must choose a power plant (first round)
                            chosen_plant_number = self.choose_power_plant_to_auction(power_plant_market)
                            choice_msg = Message(to=sender)
                            choice_data = {
                                "choice": "auction",
                                "power_plant_number": chosen_plant_number
                            }
                            choice_msg.body = json.dumps(choice_data)
                            await self.send(choice_msg)
                            print(f"Player {self.agent.player_id} must auction power plant {chosen_plant_number} (first round).")

                    elif action == "initial_bid":
                        # Handle initial bid from starting player
                        base_min_bid = data.get("base_min_bid")
                        power_plant = data.get("power_plant")
                        bid_amount = self.decide_initial_bid(base_min_bid, power_plant)
                        bid_msg = Message(to=sender)
                        bid_data = {
                            "bid": bid_amount
                        }
                        bid_msg.body = json.dumps(bid_data)
                        await self.send(bid_msg)
                        print(f"Player {self.agent.player_id} places initial bid of {bid_amount} on power plant {power_plant.get('min_bid', 'unknown')}.")

                    elif action == "bid":
                        # Receive bid request
                        current_bid = data.get("current_bid", 0)
                        power_plant = data.get("power_plant", {})
                        # Decide whether to bid or pass
                        bid_amount = self.decide_bid_amount(current_bid, power_plant)
                        bid_msg = Message(to=sender)
                        bid_data = {
                            "bid": bid_amount
                        }
                        bid_msg.body = json.dumps(bid_data)
                        await self.send(bid_msg)
                        if bid_amount > current_bid:
                            print(f"Player {self.agent.player_id} bids {bid_amount} for power plant {power_plant.get('min_bid', 'unknown')}.")
                        else:
                            print(f"Player {self.agent.player_id} passes on bidding.")

                    elif action == "discard_power_plant":
                        # Player has more than 3 power plants and must discard one
                        power_plants = data.get("power_plants", [])
                        discard_number = self.choose_power_plant_to_discard(power_plants)
                        discard_msg = Message(to=sender)
                        discard_data = {
                            "discard_number": discard_number
                        }
                        discard_msg.body = json.dumps(discard_data)
                        await self.send(discard_msg)
                        print(f"Player {self.agent.player_id} discards power plant {discard_number}.")

                    elif action == "auction_result":
                        # Handle auction result
                        winner = data.get("winner")
                        power_plant = data.get("power_plant", {})
                        bid = data.get("bid", 0)
                        if winner == self.agent.jid:
                            # Add the power plant to the player's state
                            self.agent.power_plants.append(power_plant)
                            self.agent.elektro -= bid  # Deduct the bid amount
                            print(f"Player {self.agent.player_id} won the auction for power plant {power_plant.get('min_bid', '')} with bid {bid}.")
                        else:
                            print(f"Player {self.agent.player_id} observed that player {winner} won the auction for power plant {power_plant.get('min_bid', '')} with bid {bid}.")

                # Placeholder for Phase 3
                elif phase == "phase3":
                    if action == "buy_resources":
                        # Since we're skipping Phase 3, respond with no purchases
                        purchase_msg = Message(to=sender)
                        purchase_data = {
                            "purchases": {},  # No purchases
                            "total_cost": 0
                        }
                        purchase_msg.body = json.dumps(purchase_data)
                        await self.send(purchase_msg)
                        print(f"Player {self.agent.player_id} skips Phase 3 - Buy Resources.")

                # Placeholder for Phase 4
                elif phase == "phase4":
                    if action == "build_houses":
                        # Since we're skipping Phase 4, respond with no builds
                        build_msg = Message(to=sender)
                        build_data = {
                            "cities": [],  # No cities built
                            "total_cost": 0
                        }
                        build_msg.body = json.dumps(build_data)
                        await self.send(build_msg)
                        print(f"Player {self.agent.player_id} skips Phase 4 - Build Houses.")

                # Placeholder for Phase 5
                elif phase == "phase5":
                    # Phase 5 (Bureaucracy) may not require a player response
                    print(f"Player {self.agent.player_id} acknowledges Phase 5 - Bureaucracy.")

                elif phase == "game_over":
                    # Handle game over
                    winner = data.get("winner")
                    final_elektro = data.get("final_elektro")
                    if winner == self.agent.jid:
                        print(f"Player {self.agent.player_id} has won the game with {final_elektro} Elektro!")
                    else:
                        print(f"Player {self.agent.player_id} has lost. Winner: {winner} with {final_elektro} Elektro.")
                    await self.agent.stop()

                else:
                    print(f"Player {self.agent.player_id} received an unknown message: {msg.body}")
            else:
                print(f"Player {self.agent.player_id} did not receive any message.")
            await asyncio.sleep(1)  # Yield control to event loop

        # Decision-making methods
        def should_pass(self):
            # Improved logic: pass if we don't need more power plants or can't afford them
            need_power_plant = len(self.agent.power_plants) < 3
            can_afford_any = any(pp.get('min_bid', float('inf')) <= self.agent.elektro for pp in self.agent.power_plant_market)
            return not need_power_plant or not can_afford_any

        def choose_power_plant_to_auction(self, market):
            # Choose the best affordable power plant based on strategic evaluation
            if not market:
                print(f"Player {self.agent.player_id} finds no available power plants to auction.")
                return None
            # Evaluate power plants
            affordable_plants = [pp for pp in market if pp.get('min_bid', float('inf')) <= self.agent.elektro]
            if not affordable_plants:
                print(f"Player {self.agent.player_id} cannot afford any power plant.")
                return None
            # Strategy: pick the plant that provides the best ratio of cities powered per Elektro
            def plant_value(pp):
                return pp.get('cities', 0) / pp.get('min_bid', 1)
            best_plant = max(affordable_plants, key=plant_value)
            return best_plant.get('min_bid', None)

        def decide_initial_bid(self, base_min_bid, power_plant):
            # Decide the initial bid based on the value of the power plant
            plant_value = self.evaluate_power_plant(power_plant)
            # For simplicity, bid up to a certain percentage of our Elektro if the plant is valuable
            max_bid = int(self.agent.elektro * 0.6)
            bid = min(max_bid, base_min_bid)
            return bid if bid >= base_min_bid else 0

        def decide_bid_amount(self, current_bid, power_plant):
            # Decide whether to bid higher based on the plant's value and our Elektro
            plant_value = self.evaluate_power_plant(power_plant)
            max_affordable_bid = self.agent.elektro
            # Willing to bid up to the plant's evaluated value or our max affordable bid
            if current_bid < plant_value and current_bid + 1 <= max_affordable_bid:
                return current_bid + 1
            else:
                # Can't afford to bid higher or the plant isn't worth it
                return 0

        def evaluate_power_plant(self, power_plant):
            # Evaluate the power plant's worth to the agent
            cities_powered = power_plant.get('cities', 0)
            resource_types = power_plant.get('resource_type', [])
            is_eco = len(resource_types) == 0
            # Prefer eco-friendly plants
            value = cities_powered * 10
            if is_eco:
                value += 20
            return value

        def choose_power_plant_to_discard(self, power_plants):
            # Decide which power plant to discard when over the limit
            # Strategy: discard the plant with the lowest value
            if not power_plants:
                return None
            def plant_value(pp):
                return pp.get('cities', 0)
            plant_to_discard = min(power_plants, key=plant_value)
            return plant_to_discard.get('min_bid', None)

        # Placeholders for other decision-making methods (Phases 3, 4, and 5)
        # You can implement these methods when you work on these phases

    async def setup(self):
        print(f"Player {self.player_id} agent starting...")
        receive_phase_behaviour = PowerGridPlayerAgent.ReceivePhaseBehaviour()
        self.add_behaviour(receive_phase_behaviour)
