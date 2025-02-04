import unittest
import json
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch
from agents.analyst_agent import AnalystAgent, create

class TestAnalystAgent(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Load configuration from settings.json (update path as necessary)
        config_path = Path("config/settings.json")
        with open(config_path, "r") as f:
            settings = json.load(f)
        
        # Get analyst-specific settings
        analyst_settings = settings["openai"]["models"]["analyst"]
        self.llm_config = {
            "name": analyst_settings["name"],
            "api_key": settings["openai"]["api_key"],
            "temperature": analyst_settings["temperature"],
            "max_tokens": analyst_settings["max_tokens"],
            "messages": analyst_settings.get("messages", [])
        }
        
        self.test_data_dir = Path("data/input")
        # Ensure you have a sample file at the given path for testing.
        self.test_file_path = str(self.test_data_dir / "SampleFileCleaner.csv")
        self.analyst = AnalystAgent(
            name="Test_Analyst",
            system_message="You are a Test Analyst Agent specialized in processing documents.",
            llm_config=self.llm_config
        )

    @patch.object(AnalystAgent, "on_messages", new_callable=AsyncMock)
    async def test_analyze_file(self, mock_on_messages):
        # Create a mock response mimicking the AutoGen response structure.
        class MockChatMessage:
            def __init__(self, content):
                self.content = content

        class MockResponse:
            def __init__(self, content):
                self.chat_message = MockChatMessage(content)
        
        # Return a JSON string as expected.
        mock_response = MockResponse('{"extracted_data": {"key": "value"}}')
        mock_on_messages.return_value = mock_response
        
        result = await self.analyst.analyze_file(self.test_file_path)
        # Check that the result has an "extracted_data" key.
        self.assertIn("extracted_data", result)
        self.assertEqual(result["extracted_data"]["extracted_data"]["key"], "value")

    @patch.object(AnalystAgent, "on_messages", new_callable=AsyncMock)
    async def test_process_file(self, mock_on_messages):
        # Create a similar mock response.
        class MockChatMessage:
            def __init__(self, content):
                self.content = content

        class MockResponse:
            def __init__(self, content):
                self.chat_message = MockChatMessage(content)
        
        mock_response = MockResponse('{"extracted_data": {"key": "value"}}')
        mock_on_messages.return_value = mock_response
        
        result = await self.analyst.process_file(self.test_file_path)
        self.assertIn("file_analysis", result)
        self.assertIn("data_quality", result)

    async def asyncTearDown(self):
        self.analyst = None

if __name__ == '__main__':
    unittest.main()
