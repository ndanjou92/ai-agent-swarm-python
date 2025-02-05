import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core import CancellationToken
from autogen_agentchat.messages import TextMessage

class AnalystAgent(AssistantAgent):
    def __init__(self, config: dict):
        # Extract configuration values.
        model = config["model"]
        api_key = config["api_key"]
        system_message = config["system_message"]
        # Build the model client.
        model_client = OpenAIChatCompletionClient(model=model, api_key=api_key)
        # Initialize the base AssistantAgent.
        super().__init__(name="analyst", system_message=system_message, model_client=model_client)
        self.config = config

def create(config: dict) -> AnalystAgent:
    return AnalystAgent(config)
