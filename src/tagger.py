"""LLMによるタグ推論モジュール

Gemini（無料、デフォルト）とClaude（高精度、オプション）を選択可能。
タグはPascalCase・英語統一で、9カテゴリに分類される。
"""

import json
import logging
import re
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

# タグカテゴリ定義
TAG_CATEGORIES = {
    "Language": {
        "description": "Programming languages",
        "examples": ["Python", "Go", "Ruby", "TypeScript", "Java", "Rust", "Kotlin", "Swift", "Php", "CSharp"],
    },
    "Framework": {
        "description": "Frameworks and libraries",
        "examples": ["Rails", "Django", "React", "NextJs", "Vue", "FastApi", "Spring", "Flutter", "Laravel"],
    },
    "Infrastructure": {
        "description": "Cloud and infrastructure tools",
        "examples": ["Aws", "Gcp", "Azure", "Docker", "Kubernetes", "Terraform", "Ansible", "Nginx"],
    },
    "Cicd": {
        "description": "CI/CD tools and practices",
        "examples": ["GitHubActions", "CircleCi", "Jenkins", "ArgoCD", "Tekton"],
    },
    "Database": {
        "description": "Databases and data stores",
        "examples": ["PostgreSql", "MySql", "Redis", "MongoDB", "DynamoDB", "Elasticsearch"],
    },
    "Architecture": {
        "description": "Design patterns and architectural styles",
        "examples": ["Microservices", "Serverless", "RestApi", "GraphQL", "EventDriven", "CleanArchitecture"],
    },
    "Observability": {
        "description": "Logging, metrics, and tracing",
        "examples": ["Datadog", "Grafana", "Prometheus", "OpenTelemetry", "CloudWatch", "Sentry"],
    },
    "AiMl": {
        "description": "AI and machine learning",
        "examples": ["MachineLearning", "DeepLearning", "Llm", "PyTorch", "TensorFlow", "Langchain"],
    },
    "Other": {
        "description": "Topics not covered by the above categories",
        "examples": ["Security", "Testing", "Design", "Documentation", "Performance", "Agile"],
    },
}


def _to_pascal_case(text: str) -> str:
    """文字列をPascalCaseに変換する"""
    text = text.strip()
    if not text:
        return text
    # 既にPascalCaseの場合はそのまま返す
    if re.match(r"^[A-Z][a-zA-Z0-9]*$", text):
        return text
    # スペース・ハイフン・アンダースコア・ドットで分割
    words = re.split(r"[\s\-_\.]+", text)
    return "".join(word.capitalize() for word in words if word)


class BaseTagger(ABC):
    def __init__(self, available_tags: list = None):
        self.available_tags = available_tags or []

    def _build_prompt(self, content: dict, max_tags: int = 5) -> str:
        # カテゴリ定義のフォーマット
        category_lines = []
        for cat_name, cat_info in TAG_CATEGORIES.items():
            examples = ", ".join(cat_info["examples"])
            category_lines.append(
                f"  - {cat_name}: {cat_info['description']} (e.g. {examples})"
            )
        categories_text = "\n".join(category_lines)

        # 既存タグの提示
        existing_tags_text = ""
        if self.available_tags:
            existing_tags_text = f"""
## Existing Tags (MUST prefer these over creating new ones)
{', '.join(self.available_tags)}

IMPORTANT: Always select from existing tags above when applicable.
Only create a new tag if no existing tag fits AND the topic is clearly important.
"""

        return f"""You are a technical content tagger. Analyze the content below and assign appropriate tags.

## Rules
1. Assign between 1 and {max_tags} tags (at least 1 tag is MANDATORY).
2. Tags MUST be in English and PascalCase (e.g. GitHubActions, MachineLearning, RestApi).
3. Select tags from the following categories:
{categories_text}
4. If the content does not fit Language/Framework/Infrastructure/Cicd/Database/Architecture/Observability/AiMl, use a concrete tag from the "Other" category (e.g. Security, Testing, Design).
5. Do NOT use generic tags like "Other" or "Misc" — always use a specific descriptive name.
6. Prefer broader category-level tags over highly specific ones to keep the total tag count manageable.
{existing_tags_text}
## Content
{json.dumps(content, ensure_ascii=False, indent=2)}

Respond in JSON format only:
{{"tags": ["Tag1", "Tag2"]}}"""

    def _normalize_tags(self, tags: list) -> list:
        """タグをPascalCaseに正規化し、既存タグとの表記揺れを吸収する"""
        # 既存タグの小文字マップ（高速照合用）
        existing_lower_map = {t.lower(): t for t in self.available_tags}
        normalized = []
        seen = set()
        for tag in tags:
            pascal = _to_pascal_case(tag)
            lower_key = pascal.lower()
            # 既存タグに同名（大文字小文字無視）があればそちらを採用
            if lower_key in existing_lower_map:
                pascal = existing_lower_map[lower_key]
            # 重複排除
            if lower_key not in seen:
                seen.add(lower_key)
                normalized.append(pascal)
        return normalized

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
        tags = result.get("tags", [])
        return self._normalize_tags(tags)


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
        tags = result.get("tags", [])
        return self._normalize_tags(tags)


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
