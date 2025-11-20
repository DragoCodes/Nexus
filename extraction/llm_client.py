"""
LLM client wrapper with optional mock responses and retry logic.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from extraction.prompts import create_messages

try:
    import google.generativeai as genai
except ImportError:  # pragma: no cover
    genai = None

load_dotenv()


class LLMClient:
    def __init__(
        self,
        model: str = "gemini-2.5-flash",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        mock_responses: Optional[List[Dict]] = None,
        temperature: float = 0.2,
    ):
        self.model = model
        self.temperature = temperature
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.base_url = base_url  # Not used for Gemini, but kept for compatibility
        self.mock_lookup = {
            item["article_id"]: item for item in (mock_responses or [])
        }

        if self.api_key and genai:
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(model_name=self.model)
        else:
            self.client = None

    @classmethod
    def from_mock_file(cls, mock_path: str) -> "LLMClient":
        mock_path = Path(mock_path)
        if mock_path.exists():
            with open(mock_path, encoding="utf-8") as handle:
                data = json.load(handle)
        else:
            data = []
        return cls(mock_responses=data)

    def can_call_api(self) -> bool:
        return self.client is not None

    def generate(self, article_id: str, article_text: str) -> str:
        if self.mock_lookup:
            payload = self.mock_lookup.get(article_id) or next(
                iter(self.mock_lookup.values())
            )
            return json.dumps(payload["triples"])
        if not self.can_call_api():
            raise RuntimeError(
                "LLM API unavailable. Provide GEMINI_API_KEY or use mock responses."
            )
        messages = create_messages(article_text)
        return self._call_gemini(messages)

    def _messages_to_prompt(self, messages: List[Dict]) -> str:
        """
        Convert OpenAI-style messages format to a single prompt string for Gemini.
        Combines system and user messages into a coherent prompt.
        """
        system_content = ""
        user_content = ""
        
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system":
                system_content = content
            elif role == "user":
                user_content = content
        
        # Combine system instructions with user request
        if system_content and user_content:
            return f"{system_content}\n\n{user_content}"
        elif system_content:
            return system_content
        elif user_content:
            return user_content
        else:
            return ""

    @retry(wait=wait_exponential(multiplier=2, min=2, max=20), stop=stop_after_attempt(3))
    def _call_gemini(self, messages):
        # Convert messages to a single prompt string
        prompt = self._messages_to_prompt(messages)
        
        # Generate content with Gemini
        generation_config = genai.types.GenerationConfig(
            temperature=self.temperature,
        )
        response = self.client.generate_content(
            prompt,
            generation_config=generation_config,
        )
        
        # Handle response - check if text is available
        if hasattr(response, 'text') and response.text:
            content = response.text
        else:
            # Handle cases where response might be blocked or empty
            raise RuntimeError(
                f"Gemini API returned empty or blocked response. "
                f"Response: {response}"
            )
        return content.strip()
