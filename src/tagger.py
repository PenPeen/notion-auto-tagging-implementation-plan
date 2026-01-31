"""LLMによるタグ推論モジュール

Gemini（無料、デフォルト）とClaude（高精度、オプション）を選択可能。
"""

import json
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseTagger(ABC):
    def __init__(self, available_tags: list = None):
        self.available_tags = available_tags or []

    def _build_prompt(self, content: dict, max_tags: int = 5) -> str:
        tag_instruction = ""
        if self.available_tags:
            tag_instruction = f"""
既存タグから選択してください（必要なら新規タグも可）:
{', '.join(self.available_tags)}
"""
        return f"""以下のコンテンツに適切なタグを{max_tags}個以内で付けてください。

{tag_instruction}

コンテンツ:
{json.dumps(content, ensure_ascii=False, indent=2)}

JSON形式で回答してください:
{{"tags": ["タグ1", "タグ2", ...]}}"""

    @abstractmethod
    def infer_tags(self, content: dict, max_tags: int = 5) -> list:
        pass

    @staticmethod
    def _extract_json(text: str) -> dict:
        """LLMレスポンスからJSONを抽出"""
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return json.loads(text.strip())


class GeminiTagger(BaseTagger):
    """Gemini API（無料）"""

    def __init__(self, api_key: str, available_tags: list = None):
        super().__init__(available_tags)
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    def infer_tags(self, content: dict, max_tags: int = 5) -> list:
        prompt = self._build_prompt(content, max_tags)
        response = self.model.generate_content(prompt)
        result = self._extract_json(response.text)
        return result.get("tags", [])


class ClaudeTagger(BaseTagger):
    """Claude API（高精度）"""

    def __init__(self, api_key: str, available_tags: list = None):
        super().__init__(available_tags)
        import anthropic

        self.client = anthropic.Anthropic(api_key=api_key)

    def infer_tags(self, content: dict, max_tags: int = 5) -> list:
        prompt = self._build_prompt(content, max_tags)

        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text
        result = self._extract_json(text)
        return result.get("tags", [])


def create_tagger(provider: str, config, available_tags: list = None) -> BaseTagger:
    """LLMプロバイダーに応じたTaggerを生成"""
    if provider == "claude":
        if not config.claude_api_key:
            raise ValueError("CLAUDE_API_KEY is not set")
        return ClaudeTagger(config.claude_api_key, available_tags)
    else:  # デフォルト: gemini
        if not config.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not set")
        return GeminiTagger(config.gemini_api_key, available_tags)
