from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

def call_agent():
    model = GoogleModel('gemini-1.5-flash')
    agent = Agent(model)
    return agent.run_sync('Where does "hello world" come from?')
