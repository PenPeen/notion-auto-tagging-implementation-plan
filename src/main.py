"""Notion Knowledge DB 自動タグ付けシステム エントリーポイント"""

import argparse
import logging
import sys
import time

from config import Config
from notion_service import NotionDB
from tagger import create_tagger
from utils import extract_content

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def process_records(records: list, notion: NotionDB, tagger, config: Config):
    """レコードを処理してタグ付け"""
    success = 0
    failed = 0

    for i, page in enumerate(records):
        page_id = page["id"]
        content = extract_content(page, config.content_properties)

        if not any(content.values()):
            logger.warning(f"Skip empty content: {page_id}")
            continue

        try:
            tags = tagger.infer_tags(content)
            notion.update_tags(page_id, config.tag_property_name, tags)
            logger.info(f"[{i+1}/{len(records)}] Tagged: {page_id} -> {tags}")
            success += 1
        except Exception as e:
            logger.error(f"Failed to tag {page_id}: {e}")
            failed += 1

        # APIレートリミット対策
        time.sleep(0.5)

    return success, failed


def main():
    parser = argparse.ArgumentParser(
        description="Notion Knowledge DB 自動タグ付けシステム"
    )
    parser.add_argument(
        "--mode",
        choices=["initial", "incremental"],
        default="incremental",
        help="実行モード（初回: initial, 差分: incremental）",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="更新対象の時間範囲（時間）",
    )
    parser.add_argument(
        "--llm",
        choices=["gemini", "claude"],
        default=None,
        help="使用するLLM（デフォルト: 環境変数 or gemini）",
    )
    args = parser.parse_args()

    config = Config()

    if args.llm:
        config.llm_provider = args.llm

    if not config.notion_api_key or not config.notion_database_id:
        logger.error("NOTION_API_KEY and NOTION_DATABASE_ID are required")
        sys.exit(1)

    notion = NotionDB(config.notion_api_key, config.notion_database_id)

    # 既存タグを取得してTaggerに渡す（タグの一貫性向上）
    existing_tags = []
    try:
        existing_tags = notion.get_existing_tags(config.tag_property_name)
        logger.info(f"Existing tags: {len(existing_tags)} tags found")
    except Exception as e:
        logger.warning(f"Failed to fetch existing tags: {e}")

    tagger = create_tagger(config.llm_provider, config, existing_tags)
    logger.info(f"Using LLM: {config.llm_provider}")

    if args.mode == "initial":
        logger.info("Initial mode: Processing all records")
        records = notion.get_all_records()
    else:
        logger.info(
            f"Incremental mode: Processing records updated in last {args.hours}h"
        )
        records = notion.get_recently_updated(args.hours)

    logger.info(f"Found {len(records)} records to process")

    if not records:
        logger.info("No records to process. Done.")
        return

    success, failed = process_records(records, notion, tagger, config)
    logger.info(f"Done. Success: {success}, Failed: {failed}")


if __name__ == "__main__":
    main()
