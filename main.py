import asyncio
import json
import logging
import uuid
import mimetypes
import openai
from pathlib import Path
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
import autogen
from agents import analyst_agent, researcher_agent, engineer_agent, qa_agent, pm_agent
from colorama import init, Fore, Style

# Initialize colorama for colored terminal output.
init(autoreset=True)

# Define colors for each agent type.
AGENT_COLORS = {
    "analyst": Fore.GREEN,
    "researcher": Fore.CYAN,
    "engineer": Fore.YELLOW,
    "qa": Fore.MAGENTA,
    "pm": Fore.BLUE,
    "user": Fore.WHITE
}

# Common thread ID that will be shared across all agents.
SHARED_THREAD_ID = str(uuid.uuid4())

def setup_logging():
    logging.basicConfig(
        filename='logs/execution.log',
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)s: %(message)s'
    )
    logging.info("Logging has been set up.")

def load_config():
    """
    Load configuration from a JSON file.
    This file should contain your OpenAI API key and an 'agents' object with settings for each agent.
    """
    with open('config/settings.json', 'r') as f:
        settings = json.load(f)
    config_dict = {}
    # Expect settings under openai.agents
    for agent_type, agent_config in settings['openai']['agents'].items():
        config_dict[agent_type] = {
            "model": agent_config["model"],
            "api_key": settings["openai"]["api_key"],
            "temperature": agent_config["temperature"],
            "max_tokens": agent_config["max_tokens"],
            "system_message": agent_config.get("system_message", ""),  # Added here
            "messages": agent_config.get("messages", [])
        }
    human_intervention_enabled = settings.get("human_intervention", True)
    return config_dict, human_intervention_enabled


def initialize_agents(config_dict):
    """
    Create a user proxy agent (for human intervention) and initialize each conversation agent.
    Each agent's create() function accepts a 'thread_id' parameter so that they share the same conversation context.
    The agents are stored in a list in the order: Analyst, Researcher, Engineer, QA, PM.
    """
    user_proxy = autogen.UserProxyAgent(
        name="User_Proxy",
        human_input_mode="TERMINATE",
        max_consecutive_auto_reply=10,
        code_execution_config={"work_dir": "data/output", "use_docker": False}
    )
    conversation_agents = [
        analyst_agent.create(config_dict["analyst"]),
        researcher_agent.create(config_dict["researcher"]),
        engineer_agent.create(config_dict["engineer"]),
        qa_agent.create(config_dict["qa"]),
        pm_agent.create(config_dict["pm"])
    ]
    # Convert list to dict for easier routing by role.
    agents = {
        "analyst": conversation_agents[0],
        "researcher": conversation_agents[1],
        "engineer": conversation_agents[2],
        "qa": conversation_agents[3],
        "pm": conversation_agents[4]
    }
    return agents, user_proxy

async def prompt_for_human_intervention(timeout: int = 10) -> TextMessage:
    """
    Prompt for human intervention if agents appear stuck.
    """
    prompt = f"\nAgents seem stuck. You have {timeout} seconds to provide intervention (or press Enter to skip): "
    try:
        intervention = await asyncio.wait_for(asyncio.to_thread(input, prompt), timeout=timeout)
    except asyncio.TimeoutError:
        intervention = ""
    if intervention.strip():
        return TextMessage(content=intervention.strip(), source="user")
    return None

async def sequential_team_workflow_with_routing(agents: dict, initial_message: TextMessage,
                                                  human_intervention_enabled: bool, rounds: int = 1) -> list:
    """
    Orchestrate a sequential team workflow with dynamic routing.
    
    Flow:
      1. Analyst responds.
      2. Researcher responds.
      3. Engineer responds.
      4. QA responds.
         - If QA's response (expected as JSON) indicates validation failure,
           route the conversation back to the designated agents.
      5. PM responds.
    
    Each agent's response is appended to the conversation history.
    Human intervention may be inserted between turns.
    """
    conversation_history = [initial_message]
    logging.info("Starting sequential team workflow among agents.")
    
    # Define the workflow order.
    workflow_order = ["analyst", "researcher", "engineer", "qa", "pm"]
    
    for round_num in range(rounds):
        print(f"\n=== Round {round_num+1} ===")
        for role in workflow_order:
            agent = agents[role]
            response = await agent.on_messages(conversation_history, CancellationToken())
            msg = response.chat_message
            conversation_history.append(msg)
            color = AGENT_COLORS.get(msg.source.lower(), Fore.WHITE)
            print(f"{color}{msg.source}: {msg.content}{Style.RESET_ALL}")
            # If it's the engineer's turn, insert an explicit instruction.
            if role == "engineer":
                engineer_instruction = TextMessage(
                    source="user",
                    content="Based on the previous discussion, please generate the CSV file. Determine the best representation for this data that can be uploads into Sailpoint, create the file, and provide the download link."
                )
                conversation_history.append(engineer_instruction)
                print(f"{Fore.WHITE}User: {engineer_instruction.content}{Style.RESET_ALL}")
            # After QA's turn, check for validation issues.
            if role == "qa":
                try:
                    qa_data = json.loads(msg.content)
                except Exception as e:
                    logging.error("QA response is not valid JSON: %s", e)
                    qa_data = {"validation_status": "PASS"}
                if qa_data.get("validation_status", "PASS").upper() == "FAIL":
                    recheck_list = qa_data.get("recheck", [])
                    logging.info(f"QA flagged failure. Recheck list: {recheck_list}")
                    routing_message = TextMessage(
                        content="QA detected an issue. Please re-assess your output based on the QA feedback.",
                        source="user"
                    )
                    conversation_history.append(routing_message)
                    print(f"{Fore.WHITE}User: {routing_message.content}{Style.RESET_ALL}")
                    for target_role in recheck_list:
                        if target_role in agents:
                            target_agent = agents[target_role]
                            recheck_response = await target_agent.on_messages(conversation_history, CancellationToken())
                            recheck_msg = recheck_response.chat_message
                            conversation_history.append(recheck_msg)
                            color = AGENT_COLORS.get(recheck_msg.source.lower(), Fore.WHITE)
                            print(f"{color}{recheck_msg.source}: {recheck_msg.content}{Style.RESET_ALL}")
                        else:
                            logging.warning(f"Recheck requested for unknown agent: {target_role}")
            # Human intervention after each agent turn.
            if human_intervention_enabled:
                intervention_message = await prompt_for_human_intervention(timeout=10)
                if intervention_message:
                    conversation_history.append(intervention_message)
                    color = AGENT_COLORS.get(intervention_message.source.lower(), Fore.WHITE)
                    print(f"{color}{intervention_message.source}: {intervention_message.content}{Style.RESET_ALL}")
                    logging.info("Human intervention added to conversation.")
    return conversation_history

async def main_async():
    setup_logging()
    config_dict, human_intervention_enabled = load_config()
    agents, user_proxy = initialize_agents(config_dict)
    
    # Look for a local file in the data/input directory.
    input_dir = Path("data/input")
    file_path = None
    for file in input_dir.iterdir():
        if file.is_file() and file.suffix.lower() in ['.pdf', '.xlsx', '.csv', '.jpg', '.png']:
            file_path = str(file.resolve())
            logging.info(f"Found file {file.name} for processing.")
            break

    cancellation_token = CancellationToken()
    additional_context = ""
    attachment = None
    if file_path:
        # Upload the file using on_upload_for_code_interpreter via the Analyst agent.
        await agents["analyst"].on_upload_for_code_interpreter(file_path, cancellation_token)
        file_reference = Path(file_path).name
        additional_context = f" Analyze this document: {{file_search: '{file_reference}'}}"
        attachment = {
            "file_path": file_path,
            "mime_type": mimetypes.guess_type(file_reference)[0] or "application/octet-stream"
        }

    initial_context = (
        "Please analyze the attached file for identity management data. "
        "Extract structured fields such as Username/Email, First Name, Last Name, Department, Role, "
        "and access details." + additional_context
    )
    
    if attachment:
        initial_message = TextMessage(
            content=initial_context,
            source="user",
            attachments=[attachment]
        )
    else:
        initial_message = TextMessage(
            content=initial_context,
            source="user"
        )
    
    conversation = await sequential_team_workflow_with_routing(
        agents, initial_message, human_intervention_enabled, rounds=1
    )
    logging.info("Sequential team workflow completed.")
    
    print("\nFinal conversation:")
    for msg in conversation:
        color = AGENT_COLORS.get(msg.source.lower(), Fore.WHITE)
        print(f"{color}{msg.source}: {msg.content}{Style.RESET_ALL}")

def main():
    asyncio.run(main_async())

if __name__ == '__main__':
    main()
