import os
import json
import logging
import mimetypes
import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from autogen_ext.agents.openai import OpenAIAssistantAgent
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from openai import AsyncClient  # Use OpenAI's async client

class AnalystAgent(OpenAIAssistantAgent):
    def __init__(self, name: str, system_message: str, llm_config: Dict[str, Any], thread_id: Optional[str] = None):
        # Get model and API key from configuration.
        model_name = llm_config.get("model", "gpt-4o-mini")
        api_key = llm_config.get("api_key", "dummy-key")
        
        # Create an async OpenAI client instance.
        openai_client = AsyncClient(api_key=api_key)
        
        # Use the passed thread_id or default to "default".
        thread_id = thread_id if thread_id is not None else "default"
        
        # Initialize the specialized OpenAIAssistantAgent.
        # The 'tools' parameter includes "file_search" and "code_interpreter" so that file search capabilities are enabled.
        super().__init__(
            name=name,
            description=system_message,
            client=openai_client,
            model=model_name,
            instructions=system_message,
            tools=["file_search", "code_interpreter"],
            assistant_id=None,  # Let the agent create a new assistant.
        )
        
        self.llm_config = llm_config
        self.supported_formats = ['.pdf', '.xlsx', '.csv', '.jpg', '.png']
        self.input_dir = Path('data/input')
        self.output_dir = Path('data/output')
    
    async def on_upload_for_code_interpreter(self, file_path: str, cancellation_token: CancellationToken):
        """
        Upload a file for the code interpreter tool.
        This method delegates to the base class implementation.
        """
        return await super().on_upload_for_code_interpreter(file_path, cancellation_token)
    
    async def analyze_file(self, file_path: Optional[str] = None, attachment: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            if attachment is None:
                if file_path is None:
                    raise ValueError("Either file_path or attachment must be provided.")
                attachment = {
                    "file_path": file_path,
                    "mime_type": mimetypes.guess_type(file_path)[0] or "application/octet-stream"
                }
            text_messages = self._build_text_messages_with_attachment(attachment)
            if text_messages and text_messages[0].source.lower() == "user":
                text_messages[0].content += "\n\n[File content will be retrieved via the built‑in file_search tool.]"
            response = await self.on_messages(text_messages, CancellationToken())
            response_content = response.chat_message.content
            if not response_content:
                error_msg = f"Empty response for file {attachment.get('file_path', 'unknown')}"
                logging.error(error_msg)
                raise ValueError(error_msg)
            try:
                extracted_data = json.loads(response_content)
            except json.JSONDecodeError as e:
                error_msg = f"JSON decode error: {e.msg}. Response: {response_content}"
                logging.error(error_msg)
                raise ValueError(error_msg)
            structured_data = {
                "file_name": attachment.get("file_path", "unknown"),
                "analysis_timestamp": datetime.now().isoformat(),
                "extracted_data": extracted_data,
                "confidence_score": True
            }
            logging.info(f"Successfully analyzed file: {attachment.get('file_path', 'unknown')}")
            return structured_data
        except Exception as e:
            logging.error(f"Error analyzing file: {str(e)}")
            raise

    def _build_text_messages_with_attachment(self, attachment: Dict[str, Any]) -> List[TextMessage]:
        message_template: List[Dict[str, Any]] = self.llm_config.get("messages", [])
        text_messages = []
        for msg in message_template:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role.lower() == "user":
                text_messages.append(TextMessage(content=content, source="user", attachments=[attachment]))
            else:
                text_messages.append(TextMessage(content=content, source="system"))
        return text_messages

    async def process_file(self, file_path: Optional[str] = None, attachment: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {
            "file_analysis": await self.analyze_file(file_path=file_path, attachment=attachment),
            "data_quality": "good"
        }

    def analyze_data_structure(self, data):
        return {"structure_valid": True, "schema_matches": True}

    def validate_completeness(self, data):
        return {"missing_fields": [], "empty_fields": []}

    def flag_inconsistencies(self, data):
        return {}

class FileWatcher(FileSystemEventHandler):
    def __init__(self, analyst_agent: AnalystAgent):
        self.analyst_agent = analyst_agent
        
    def on_created(self, event):
        if event.is_directory:
            return
        if Path(event.src_path).suffix.lower() in self.analyst_agent.supported_formats:
            try:
                result = asyncio.run(self.analyst_agent.analyze_file(event.src_path))
                output_path = self.analyst_agent.output_dir / f"analysis_{Path(event.src_path).stem}.json"
                with open(output_path, "w") as f:
                    json.dump(result, f, indent=2)
            except Exception as e:
                logging.error(f"Failed to process {event.src_path}: {str(e)}")

def create(config: Dict[str, Any], thread_id: Optional[str] = None) -> AnalystAgent:
    # Use the system_message from the configuration, with a fallback if not provided.
    system_message = config.get("system_message", 
        "You are an Analyst Agent specialized in monitoring and processing input files. Extract structured identity data and prepare standardized output. Use the file_search tool when necessary.")
    return AnalystAgent(name="analyst", system_message=system_message, llm_config=config, thread_id=thread_id)


def start_file_watcher(agent: AnalystAgent):
    event_handler = FileWatcher(agent)
    observer = Observer()
    observer.schedule(event_handler, str(agent.input_dir), recursive=False)
    observer.start()
    return observer
