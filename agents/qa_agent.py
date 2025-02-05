import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core import CancellationToken

class QAAgent(AssistantAgent):
    def __init__(self, config: dict):
        model = config["model"]
        api_key = config["api_key"]
        system_message = config["system_message"]
        model_client = OpenAIChatCompletionClient(model=model, api_key=api_key)
        super().__init__(name="qa", system_message=system_message, model_client=model_client)
        self.config = config

def create(config: dict) -> QAAgent:
    return QAAgent(config)
