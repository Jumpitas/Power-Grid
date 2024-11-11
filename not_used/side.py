import json

async def handle_auction_for_player(self, player):
            # Send the current power plant market to the player
            current_market_info = [self.serialize_power_plant(pp) for pp in self.environment.power_plant_market.market[:4]]
            msg = Message(to=player["jid"])
            msg.body = json.dumps({
                "phase": "phase2",
                "action": "choose_or_pass",
                "power_plants": current_market_info
            })
            await self.send(msg)

            # Wait for player's response
            response = await self.receive(timeout=30)
            if response and str(response.sender).split('/')[0] == player["jid"]:
                data = json.loads(response.body)
                if data.get("action") == "pass":
                    player["has_bought_power_plant"] = True
                elif data.get("action") == "choose":
                    chosen_number = data.get("power_plant_number")
                    chosen_plant = self.get_power_plant_by_number(chosen_number)
                    if chosen_plant:
                        await self.conduct_auction(chosen_plant, player)
                    else:
                        print(f"Invalid power plant number chosen by {player['jid']}")
                else:
                    print(f"Invalid action received from {player['jid']}")
            else:
                print(f"No response from {player['jid']} in auction phase.")


async def conduct_auction(self, power_plant, starting_player):
            active_players = [p for p in self.get_players_in_order() if not p["has_bought_power_plant"]]
            current_bid = power_plant.min_bid  # Minimum bid is the power plant's min_bid
            highest_bidder = starting_player
            bidding_active = True

            while bidding_active and len(active_players) > 1:
                for player in active_players:
                    if player["jid"] == highest_bidder["jid"]:
                        continue  # Skip the highest bidder's turn

                    msg = Message(to=player["jid"])
                    msg.body = json.dumps({
                        "phase": "phase2",
                        "action": "bid",
                        "current_bid": current_bid,
                        "power_plant": self.serialize_power_plant(power_plant)
                    })
                    await self.send(msg)

                    # Wait for player's bid
                    response = await self.receive(timeout=15)
                    if response and str(response.sender).split('/')[0] == player["jid"]:
                        data = json.loads(response.body)
                        bid = data.get("bid", 0)
                        if bid > current_bid and bid <= player["elektro"]:
                            current_bid = bid
                            highest_bidder = player
                        else:
                            # Player passes
                            active_players.remove(player)
                    else:
                        print(f"No response or invalid bid from {player['jid']}.")
                        active_players.remove(player)

                if len(active_players) <= 1:
                    bidding_active = False

            # Highest bidder buys the power plant
            highest_bidder["elektro"] -= current_bid

            # Can only have 3 !!!
            highest_bidder["power_plants"].append(power_plant)
            highest_bidder["has_bought_power_plant"] = True
            # Remove the power plant from the market
            self.environment.power_plant_market.market.remove(power_plant)
            # Draw a new power plant from the deck to replace it
            if self.environment.power_plant_market.deck:
                new_plant = self.environment.power_plant_market.deck.pop(0)
                self.environment.power_plant_market.market.append(new_plant)
                # Re-sort the market
                self.environment.power_plant_market.market.sort(key=lambda pp: pp.min_bid)

            # Notify players of the auction result
            for p in self.players.values():
                msg = Message(to=p["jid"])
                msg.body = json.dumps({
                    "phase": "phase2",
                    "action": "auction_result",
                    "winner": highest_bidder["jid"],
                    "power_plant": self.serialize_power_plant(power_plant),
                    "bid": current_bid
                })
                await self.send(msg)