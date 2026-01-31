"""Notion API操作モジュール

notion-clientパッケージとの名前衝突を避けるため、
notion_client.pyではなくnotion_service.pyとしている。
"""

from notion_client import Client
from datetime import datetime, timedelta, timezone


class NotionDB:
    def __init__(self, api_key: str, database_id: str):
        self.client = Client(auth=api_key)
        self.database_id = database_id

    def get_all_records(self) -> list:
        """全レコード取得（初回実行用）"""
        results = []
        cursor = None

        while True:
            response = self.client.databases.query(
                database_id=self.database_id,
                start_cursor=cursor,
            )
            results.extend(response["results"])

            if not response["has_more"]:
                break
            cursor = response["next_cursor"]

        return results

    def get_recently_updated(self, hours: int = 24) -> list:
        """指定時間内に更新されたレコード取得"""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        results = []
        cursor = None

        while True:
            response = self.client.databases.query(
                database_id=self.database_id,
                filter={
                    "timestamp": "last_edited_time",
                    "last_edited_time": {
                        "after": cutoff.isoformat(),
                    },
                },
                start_cursor=cursor,
            )
            results.extend(response["results"])

            if not response["has_more"]:
                break
            cursor = response["next_cursor"]

        return results

    def get_existing_tags(self, tag_property: str) -> list:
        """DBの既存タグ一覧を取得"""
        db_info = self.client.databases.retrieve(database_id=self.database_id)
        prop = db_info.get("properties", {}).get(tag_property, {})
        options = prop.get("multi_select", {}).get("options", [])
        return [opt["name"] for opt in options]

    def get_page_blocks(self, page_id: str) -> list:
        """ページ直下のブロック一覧を取得（1階層のみ）"""
        results = []
        cursor = None

        while True:
            response = self.client.blocks.children.list(
                block_id=page_id,
                start_cursor=cursor,
            )
            results.extend(response["results"])

            if not response["has_more"]:
                break
            cursor = response["next_cursor"]

        return results

    def update_tags(self, page_id: str, tag_property: str, tags: list):
        """タグを更新"""
        self.client.pages.update(
            page_id=page_id,
            properties={
                tag_property: {
                    "multi_select": [{"name": tag} for tag in tags],
                },
            },
        )
