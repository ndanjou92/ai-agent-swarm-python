import asyncio
import logging
from typing import Dict, Any, Optional
from autogen_ext.agents.openai import OpenAIAssistantAgent
from autogen_core import CancellationToken
from openai import AsyncClient
from autogen_agentchat.messages import TextMessage

"""
Engineer Agent (Stub)
This agent is responsible for technical problem solving and implementation tasks.
It uses its integrated code interpreter tool to generate a CSV file, upload it,
and then returns the file metadata so that other agents can access it.
"""

class EngineerAgent(OpenAIAssistantAgent):
    def __init__(self, name: str, system_message: str, llm_config: Dict[str, Any], thread_id: Optional[str] = None):
        model_name = llm_config.get("model", "gpt-4o-mini")
        api_key = llm_config.get("api_key", "dummy-key")
        openai_client = AsyncClient(api_key=api_key)
        thread_id = thread_id if thread_id is not None else "default"
        super().__init__(
            name=name,
            description=system_message,
            client=openai_client,
            model=model_name,
            instructions=system_message,
            tools=["file_search", "code_interpreter"],
        )
        self.llm_config = llm_config
        self.file_outputs = {}  # Dictionary to track file outputs by file ID

    async def process_file_output(self, file_id: str) -> Dict[str, Any]:
        """
        Retrieve and store metadata for a file that was uploaded.
        Uses the OpenAI API to retrieve the file using its file_id.
        """
        try:
            file_data = await self.client.files.retrieve(file_id)
            self.file_outputs[file_id] = file_data
            return {
                "file_id": file_id,
                "filename": file_data.filename,
                "metadata": file_data.metadata
            }
        except Exception as e:
            logging.error("Error retrieving file: %s", e)
            raise

    async def solve_problem(self, problem_statement: str) -> Dict[str, Any]: #this might need to be removed. 
        """
        Trigger the agent's processing using the provided problem statement.
        The system prompt should instruct the agent to generate the CSV,
        upload it, and include the file ID in its response.
        """
        response = await self.on_messages(
            [TextMessage(source="user", content=problem_statement)],
            CancellationToken()
        )
        return {"solution": response.chat_message.content}

def create(config: Dict[str, Any], thread_id: Optional[str] = None) -> EngineerAgent:
    system_message = config.get(
        "system_message",
        "You are an Engineer Agent specialized in technical problem solving and implementation tasks. Generate the output CSV file, upload it, and include the file ID in your response."
    )
    return EngineerAgent(name="engineer", system_message=system_message, llm_config=config, thread_id=thread_id)
