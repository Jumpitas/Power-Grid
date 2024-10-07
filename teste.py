import asyncio
from spade.agent import Agent
from spade.behaviour import OneShotBehaviour


class TestAgent(Agent):
    class TestBehaviour(OneShotBehaviour):
        async def run(self):
            print(f"Hello World! I am agent {self.agent.jid}")
            await self.agent.stop()

    async def setup(self):
        print(f"Agent {self.jid} starting...")
        b = self.TestBehaviour()
        self.add_behaviour(b)


if __name__ == "__main__":
    async def main():
        # Set your agent's JID and password
        jid = "agent1@localhost"
        password = "your_password"

        # Initialize the agent
        test_agent = TestAgent(jid, password)

        # Start the agent
        await test_agent.start()

        # Keep the agent alive until it stops
        while test_agent.is_alive():
            try:
                await asyncio.sleep(1)
            except KeyboardInterrupt:
                await test_agent.stop()
                break
        print("Agent finished")


    # Run the asyncio event loop
    asyncio.run(main())
