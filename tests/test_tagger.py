"""tagger モジュールのユニットテスト"""

import json
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# src をパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tagger import BaseTagger, GeminiTagger, ClaudeTagger, create_tagger


class ConcreteTagger(BaseTagger):
    """テスト用の具象Tagger"""

    def infer_tags(self, content: dict, max_tags: int = 5) -> list:
        return ["test"]


class TestBaseTagger(unittest.TestCase):
    def test_build_prompt_without_existing_tags(self):
        tagger = ConcreteTagger()
        content = {"Name": "テスト記事", "Content": "Pythonの基本"}
        prompt = tagger._build_prompt(content, max_tags=3)

        self.assertIn("3個以内", prompt)
        self.assertIn("テスト記事", prompt)
        self.assertIn("Pythonの基本", prompt)

    def test_build_prompt_with_existing_tags(self):
        tagger = ConcreteTagger(available_tags=["Python", "JavaScript", "設計"])
        content = {"Name": "テスト"}
        prompt = tagger._build_prompt(content)

        self.assertIn("Python", prompt)
        self.assertIn("JavaScript", prompt)
        self.assertIn("既存タグから選択", prompt)

    def test_extract_json_plain(self):
        text = '{"tags": ["Python", "API"]}'
        result = BaseTagger._extract_json(text)
        self.assertEqual(result["tags"], ["Python", "API"])

    def test_extract_json_with_code_block(self):
        text = '```json\n{"tags": ["Python", "API"]}\n```'
        result = BaseTagger._extract_json(text)
        self.assertEqual(result["tags"], ["Python", "API"])

    def test_extract_json_with_generic_code_block(self):
        text = '```\n{"tags": ["Go"]}\n```'
        result = BaseTagger._extract_json(text)
        self.assertEqual(result["tags"], ["Go"])

    def test_extract_json_invalid(self):
        with self.assertRaises(json.JSONDecodeError):
            BaseTagger._extract_json("not json at all")


class TestCreateTagger(unittest.TestCase):
    def test_create_gemini_tagger(self):
        config = MagicMock()
        config.gemini_api_key = "test-key"

        with patch("tagger.GeminiTagger.__init__", return_value=None):
            tagger = create_tagger("gemini", config)
            self.assertIsInstance(tagger, GeminiTagger)

    def test_create_claude_tagger(self):
        config = MagicMock()
        config.claude_api_key = "test-key"

        with patch("tagger.ClaudeTagger.__init__", return_value=None):
            tagger = create_tagger("claude", config)
            self.assertIsInstance(tagger, ClaudeTagger)

    def test_create_tagger_missing_gemini_key(self):
        config = MagicMock()
        config.gemini_api_key = ""

        with self.assertRaises(ValueError):
            create_tagger("gemini", config)

    def test_create_tagger_missing_claude_key(self):
        config = MagicMock()
        config.claude_api_key = ""

        with self.assertRaises(ValueError):
            create_tagger("claude", config)

    def test_create_tagger_with_available_tags(self):
        config = MagicMock()
        config.gemini_api_key = "test-key"
        tags = ["Python", "Go"]

        with patch("tagger.GeminiTagger.__init__", return_value=None):
            tagger = create_tagger("gemini", config, available_tags=tags)
            self.assertIsInstance(tagger, GeminiTagger)


class TestExtractContent(unittest.TestCase):
    """utils.extract_content のテスト"""

    def test_extract_title_and_rich_text(self):
        from utils import extract_content

        page = {
            "properties": {
                "Name": {
                    "type": "title",
                    "title": [{"plain_text": "テスト記事"}],
                },
                "Content": {
                    "type": "rich_text",
                    "rich_text": [{"plain_text": "本文テキスト"}],
                },
            }
        }
        result = extract_content(page, ["Name", "Content"])
        self.assertEqual(result["Name"], "テスト記事")
        self.assertEqual(result["Content"], "本文テキスト")

    def test_extract_missing_property(self):
        from utils import extract_content

        page = {"properties": {}}
        result = extract_content(page, ["Name"])
        self.assertEqual(result, {})

    def test_extract_url_property(self):
        from utils import extract_content

        page = {
            "properties": {
                "URL": {"type": "url", "url": "https://example.com"},
            }
        }
        result = extract_content(page, ["URL"])
        self.assertEqual(result["URL"], "https://example.com")

    def test_extract_select_property(self):
        from utils import extract_content

        page = {
            "properties": {
                "Category": {
                    "type": "select",
                    "select": {"name": "技術"},
                },
            }
        }
        result = extract_content(page, ["Category"])
        self.assertEqual(result["Category"], "技術")


if __name__ == "__main__":
    unittest.main()
