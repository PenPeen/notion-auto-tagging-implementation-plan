"""tagger モジュールのユニットテスト"""

import json
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# src をパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tagger import BaseTagger, GeminiTagger, ClaudeTagger, create_tagger, TAG_CATEGORIES, _to_pascal_case
from utils import extract_block_text, extract_body_content


class ConcreteTagger(BaseTagger):
    """テスト用の具象Tagger"""

    def infer_tags(self, content: dict, max_tags: int = 5) -> list:
        return ["test"]


class TestBuildPrompt(unittest.TestCase):
    """_build_prompt のテスト"""

    def test_prompt_contains_max_tags(self):
        tagger = ConcreteTagger()
        content = {"Name": "テスト記事", "Content": "Pythonの基本"}
        prompt = tagger._build_prompt(content, max_tags=3)

        self.assertIn("1 and 3 tags", prompt)
        self.assertIn("テスト記事", prompt)
        self.assertIn("Pythonの基本", prompt)

    def test_prompt_contains_all_categories(self):
        tagger = ConcreteTagger()
        prompt = tagger._build_prompt({"Name": "test"})

        for category in TAG_CATEGORIES:
            self.assertIn(category, prompt)

    def test_prompt_contains_pascal_case_rule(self):
        tagger = ConcreteTagger()
        prompt = tagger._build_prompt({"Name": "test"})

        self.assertIn("PascalCase", prompt)
        self.assertIn("English", prompt)

    def test_prompt_contains_mandatory_tag_rule(self):
        tagger = ConcreteTagger()
        prompt = tagger._build_prompt({"Name": "test"})

        self.assertIn("at least 1 tag is MANDATORY", prompt)

    def test_prompt_with_existing_tags(self):
        tagger = ConcreteTagger(available_tags=["Python", "Docker", "Testing"])
        prompt = tagger._build_prompt({"Name": "test"})

        self.assertIn("Python", prompt)
        self.assertIn("Docker", prompt)
        self.assertIn("Existing Tags", prompt)
        self.assertIn("MUST prefer these over creating new ones", prompt)

    def test_prompt_forbids_generic_other_tag(self):
        tagger = ConcreteTagger()
        prompt = tagger._build_prompt({"Name": "test"})

        self.assertIn('Do NOT use generic tags like "Other"', prompt)


class TestExtractJson(unittest.TestCase):
    """_extract_json のテスト"""

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


class TestToPascalCase(unittest.TestCase):
    """_to_pascal_case のテスト"""

    def test_already_pascal_case(self):
        self.assertEqual(_to_pascal_case("Python"), "Python")
        self.assertEqual(_to_pascal_case("GitHubActions"), "GitHubActions")

    def test_lowercase(self):
        self.assertEqual(_to_pascal_case("python"), "Python")

    def test_snake_case(self):
        self.assertEqual(_to_pascal_case("github_actions"), "GithubActions")

    def test_kebab_case(self):
        self.assertEqual(_to_pascal_case("machine-learning"), "MachineLearning")

    def test_space_separated(self):
        self.assertEqual(_to_pascal_case("clean architecture"), "CleanArchitecture")

    def test_dot_separated(self):
        self.assertEqual(_to_pascal_case("next.js"), "NextJs")

    def test_empty_string(self):
        self.assertEqual(_to_pascal_case(""), "")

    def test_whitespace_only(self):
        self.assertEqual(_to_pascal_case("  "), "")


class TestNormalizeTags(unittest.TestCase):
    """_normalize_tags のテスト"""

    def test_basic_normalization(self):
        tagger = ConcreteTagger()
        result = tagger._normalize_tags(["python", "machine-learning"])
        self.assertEqual(result, ["Python", "MachineLearning"])

    def test_deduplication(self):
        tagger = ConcreteTagger()
        result = tagger._normalize_tags(["Python", "python", "PYTHON"])
        self.assertEqual(result, ["Python"])

    def test_existing_tag_preference(self):
        tagger = ConcreteTagger(available_tags=["PostgreSql", "GitHubActions"])
        result = tagger._normalize_tags(["postgresql", "githubactions"])
        self.assertEqual(result, ["PostgreSql", "GitHubActions"])

    def test_mixed_new_and_existing(self):
        tagger = ConcreteTagger(available_tags=["Python", "Docker"])
        result = tagger._normalize_tags(["python", "kubernetes"])
        self.assertEqual(result, ["Python", "Kubernetes"])


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


class TestExtractBlockText(unittest.TestCase):
    """extract_block_text のテスト"""

    def test_paragraph(self):
        block = {
            "type": "paragraph",
            "paragraph": {"rich_text": [{"plain_text": "Hello World"}]},
        }
        self.assertEqual(extract_block_text(block), "Hello World")

    def test_heading_1(self):
        block = {
            "type": "heading_1",
            "heading_1": {"rich_text": [{"plain_text": "Title"}]},
        }
        self.assertEqual(extract_block_text(block), "Title")

    def test_heading_2(self):
        block = {
            "type": "heading_2",
            "heading_2": {"rich_text": [{"plain_text": "Subtitle"}]},
        }
        self.assertEqual(extract_block_text(block), "Subtitle")

    def test_heading_3(self):
        block = {
            "type": "heading_3",
            "heading_3": {"rich_text": [{"plain_text": "Section"}]},
        }
        self.assertEqual(extract_block_text(block), "Section")

    def test_bulleted_list_item(self):
        block = {
            "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": [{"plain_text": "item 1"}]},
        }
        self.assertEqual(extract_block_text(block), "item 1")

    def test_numbered_list_item(self):
        block = {
            "type": "numbered_list_item",
            "numbered_list_item": {"rich_text": [{"plain_text": "step 1"}]},
        }
        self.assertEqual(extract_block_text(block), "step 1")

    def test_quote(self):
        block = {
            "type": "quote",
            "quote": {"rich_text": [{"plain_text": "a wise quote"}]},
        }
        self.assertEqual(extract_block_text(block), "a wise quote")

    def test_callout(self):
        block = {
            "type": "callout",
            "callout": {"rich_text": [{"plain_text": "Note: important"}]},
        }
        self.assertEqual(extract_block_text(block), "Note: important")

    def test_toggle(self):
        block = {
            "type": "toggle",
            "toggle": {"rich_text": [{"plain_text": "Details"}]},
        }
        self.assertEqual(extract_block_text(block), "Details")

    def test_to_do(self):
        block = {
            "type": "to_do",
            "to_do": {"rich_text": [{"plain_text": "Buy milk"}]},
        }
        self.assertEqual(extract_block_text(block), "Buy milk")

    def test_code_with_language(self):
        block = {
            "type": "code",
            "code": {
                "rich_text": [{"plain_text": "print('hello')"}],
                "language": "python",
            },
        }
        self.assertEqual(extract_block_text(block), "[python] print('hello')")

    def test_code_without_language(self):
        block = {
            "type": "code",
            "code": {
                "rich_text": [{"plain_text": "echo hi"}],
                "language": "",
            },
        }
        self.assertEqual(extract_block_text(block), "echo hi")

    def test_unsupported_block_type(self):
        block = {"type": "image", "image": {}}
        self.assertEqual(extract_block_text(block), "")

    def test_divider(self):
        block = {"type": "divider", "divider": {}}
        self.assertEqual(extract_block_text(block), "")

    def test_multiple_rich_text_segments(self):
        block = {
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {"plain_text": "Hello "},
                    {"plain_text": "World"},
                ]
            },
        }
        self.assertEqual(extract_block_text(block), "Hello World")

    def test_empty_rich_text(self):
        block = {
            "type": "paragraph",
            "paragraph": {"rich_text": []},
        }
        self.assertEqual(extract_block_text(block), "")


class TestExtractBodyContent(unittest.TestCase):
    """extract_body_content のテスト"""

    def test_basic_extraction(self):
        blocks = [
            {"type": "heading_1", "heading_1": {"rich_text": [{"plain_text": "Title"}]}},
            {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "Body text"}]}},
        ]
        result = extract_body_content(blocks)
        self.assertEqual(result, "Title\nBody text")

    def test_skip_unsupported_blocks(self):
        blocks = [
            {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "Before"}]}},
            {"type": "image", "image": {}},
            {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "After"}]}},
        ]
        result = extract_body_content(blocks)
        self.assertEqual(result, "Before\nAfter")

    def test_truncation(self):
        blocks = [
            {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "A" * 50}]}},
            {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "B" * 50}]}},
        ]
        result = extract_body_content(blocks, max_chars=60)
        # 最初の50文字ブロック + 改行分(1) = 51, 残り9文字分で切り詰め
        self.assertLessEqual(len(result), 60)
        self.assertTrue(result.startswith("A" * 50))

    def test_empty_blocks(self):
        blocks = [
            {"type": "paragraph", "paragraph": {"rich_text": []}},
            {"type": "divider", "divider": {}},
        ]
        result = extract_body_content(blocks)
        self.assertEqual(result, "")

    def test_empty_list(self):
        result = extract_body_content([])
        self.assertEqual(result, "")

    def test_single_block_exceeds_max(self):
        blocks = [
            {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "X" * 100}]}},
        ]
        result = extract_body_content(blocks, max_chars=30)
        self.assertEqual(len(result), 30)
        self.assertEqual(result, "X" * 30)


class TestShouldSkip(unittest.TestCase):
    """_should_skip のテスト"""

    def setUp(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
        from main import _should_skip, TAGGED_AT_BUFFER_SECONDS

        self._should_skip = _should_skip
        self.buffer = TAGGED_AT_BUFFER_SECONDS

    def test_skip_when_tagged_recently(self):
        """タグ更新直後（差が数秒）→ スキップすべき"""
        page = {
            "last_edited_time": "2026-01-31T09:00:05.000Z",
            "properties": {
                "最終タグ付け日時": {
                    "date": {"start": "2026-01-31T09:00:00+00:00"},
                },
            },
        }
        self.assertTrue(self._should_skip(page, "最終タグ付け日時"))

    def test_no_skip_when_user_edited(self):
        """ユーザー編集後（差が大きい）→ スキップしない"""
        page = {
            "last_edited_time": "2026-01-31T15:00:00.000Z",
            "properties": {
                "最終タグ付け日時": {
                    "date": {"start": "2026-01-31T09:00:00+00:00"},
                },
            },
        }
        self.assertFalse(self._should_skip(page, "最終タグ付け日時"))

    def test_no_skip_when_tagged_at_missing(self):
        """最終タグ付け日時が未設定 → スキップしない"""
        page = {
            "last_edited_time": "2026-01-31T09:00:00.000Z",
            "properties": {
                "最終タグ付け日時": {"date": None},
            },
        }
        self.assertFalse(self._should_skip(page, "最終タグ付け日時"))

    def test_no_skip_when_property_absent(self):
        """最終タグ付け日時プロパティ自体がない → スキップしない"""
        page = {
            "last_edited_time": "2026-01-31T09:00:00.000Z",
            "properties": {},
        }
        self.assertFalse(self._should_skip(page, "最終タグ付け日時"))

    def test_no_skip_at_boundary(self):
        """差がちょうど閾値以上 → スキップしない"""
        page = {
            "last_edited_time": "2026-01-31T09:05:00.000Z",
            "properties": {
                "最終タグ付け日時": {
                    "date": {"start": "2026-01-31T09:00:00+00:00"},
                },
            },
        }
        self.assertFalse(self._should_skip(page, "最終タグ付け日時"))

    def test_skip_at_just_under_boundary(self):
        """差が閾値未満 → スキップ"""
        page = {
            "last_edited_time": "2026-01-31T09:04:59.000Z",
            "properties": {
                "最終タグ付け日時": {
                    "date": {"start": "2026-01-31T09:00:00+00:00"},
                },
            },
        }
        self.assertTrue(self._should_skip(page, "最終タグ付け日時"))

    def test_no_skip_when_last_edited_time_missing(self):
        """last_edited_time がない → スキップしない"""
        page = {
            "properties": {
                "最終タグ付け日時": {
                    "date": {"start": "2026-01-31T09:00:00+00:00"},
                },
            },
        }
        self.assertFalse(self._should_skip(page, "最終タグ付け日時"))


if __name__ == "__main__":
    unittest.main()
