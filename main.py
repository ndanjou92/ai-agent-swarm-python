import asyncio
import json
import logging
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.base import TaskResult
from colorama import init, Fore, Style

# Import the five agent creators.
from agents import analyst_agent, researcher_agent, engineer_agent, qa_agent, architect_agent

def setup_logging():
    logging.basicConfig(
        filename='logs/execution.log',
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)s: %(message)s'
    )
    logging.info("Logging has been set up.")

def load_config():
    with open('config/settings.json', 'r') as f:
        settings = json.load(f)
    config_dict = {}
    for agent_type, agent_config in settings['openai']['agents'].items():
        config_dict[agent_type] = {
            "model": agent_config["model"],
            "api_key": settings["openai"]["api_key"],
            "temperature": agent_config["temperature"],
            "max_tokens": agent_config["max_tokens"],
            "system_message": agent_config.get("system_message", ""),
            "messages": agent_config.get("messages", [])
        }
    return config_dict

def initialize_agents(config_dict):
    conversation_agents = [
        analyst_agent.create(config_dict["analyst"]),
        researcher_agent.create(config_dict["researcher"]),
        architect_agent.create(config_dict["architect"]),
        engineer_agent.create(config_dict["engineer"]),
        qa_agent.create(config_dict["qa"])
        
    ]
    return conversation_agents

async def main_async():
    setup_logging()
    config_dict = load_config()
    agents = initialize_agents(config_dict)
    
    # Create a model client using the global API key.
    model_client = OpenAIChatCompletionClient(
        model="gpt-4o-mini",
        api_key=config_dict["analyst"]["api_key"],
        max_turns = 20,
        max_stalls = 3,
    )
    
    # Instantiate the MagenticOneGroupChat team with all agents.
    team = MagenticOneGroupChat(agents, model_client=model_client)
    
    # Define a minimal initial message.
    initial_message = TextMessage(
        content="create a synthetic user list with 10 unique users that has a multivalued approach to detailing different access levels or entitlements for each user.",
        source="user"
    )
    
    # Run the team and print out each message with color coding.
    async for message in team.run_stream(task=initial_message):
        # Check if the yielded item is the final TaskResult.
        if isinstance(message, TaskResult):
            print("Final result:", TaskResult.stop_reason)
            break
        else:
            color = AGENT_COLORS.get(message.source.lower(), Fore.WHITE)
            print(f"{color}{message.source}: {message.content}{Style.RESET_ALL}")
    
    logging.info("MagenticOneGroupChat workflow completed.")

def main():
    asyncio.run(main_async())

if __name__ == '__main__':
    # Define colors for each agent type.
    from colorama import Fore
    AGENT_COLORS = {
        "analyst": Fore.GREEN,
        "researcher": Fore.CYAN,
        "engineer": Fore.YELLOW,
        "qa": Fore.MAGENTA,
        "architect": Fore.BLUE,
        "user": Fore.WHITE
    }
    main()
