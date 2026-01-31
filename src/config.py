import os
from dataclasses import dataclass, field


@dataclass
class Config:
    notion_api_key: str = ""
    notion_database_id: str = ""
    gemini_api_key: str = ""
    claude_api_key: str = ""
    llm_provider: str = "gemini"
    tag_property_name: str = "ラベル"
    content_properties: list = field(default_factory=list)
    fetch_page_body: bool = True
    body_max_chars: int = 4000

    def __post_init__(self):
        self.notion_api_key = os.getenv("NOTION_API_KEY", self.notion_api_key)
        self.notion_database_id = os.getenv("NOTION_DATABASE_ID", self.notion_database_id)
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", self.gemini_api_key)
        self.claude_api_key = os.getenv("CLAUDE_API_KEY", self.claude_api_key)
        self.llm_provider = os.getenv("LLM_PROVIDER", self.llm_provider)
        self.tag_property_name = os.getenv("TAG_PROPERTY_NAME", self.tag_property_name)
        if not self.content_properties:
            self.content_properties = os.getenv(
                "CONTENT_PROPERTIES", "タイトル"
            ).split(",")
        fetch_env = os.getenv("FETCH_PAGE_BODY", "").lower()
        if fetch_env in ("false", "0", "no"):
            self.fetch_page_body = False
        body_env = os.getenv("BODY_MAX_CHARS", "")
        if body_env:
            self.body_max_chars = int(body_env)
