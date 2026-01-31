"""Notion Knowledge DB 自動タグ付けシステム エントリーポイント"""

import argparse
import logging
import sys
import time

from config import Config
from notion_service import NotionDB
from tagger import create_tagger, RateLimitError
from utils import extract_content, extract_body_content

# LLMプロバイダごとのリクエスト間隔（秒）
LLM_SLEEP_INTERVALS = {
    "gemini": 4.0,   # 15 RPM → 4秒間隔
    "claude": 1.0,   # RPM余裕あり
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _infer_with_retry(tagger, content: dict, page_id: str) -> list:
    """タグ推論を1回リトライ付きで実行。429はそのまま送出。"""
    try:
        return tagger.infer_tags(content)
    except RateLimitError:
        raise
    except Exception as first_err:
        logger.warning(f"Retry for {page_id} due to: {first_err}")
        try:
            return tagger.infer_tags(content)
        except RateLimitError:
            raise
        except Exception as retry_err:
            raise retry_err from first_err


def process_records(
    records: list, notion: NotionDB, tagger, config: Config
) -> tuple:
    """レコードを処理してタグ付け"""
    success = 0
    failed = 0
    skipped = 0
    sleep_interval = LLM_SLEEP_INTERVALS.get(config.llm_provider, 4.0)

    for i, page in enumerate(records):
        page_id = page["id"]
        content = extract_content(page, config.content_properties)

        # ページ本文（ブロック）を取得してcontentにマージ
        if config.fetch_page_body:
            try:
                blocks = notion.get_page_blocks(page_id)
                body = extract_body_content(blocks, config.body_max_chars)
                if body:
                    content["body"] = body
                time.sleep(0.35)  # Notion API レート制限対策 (3 req/s)
            except Exception as e:
                logger.warning(f"Failed to fetch blocks for {page_id}: {e}")

        if not any(content.values()):
            logger.warning(f"Skip empty content: {page_id}")
            skipped += 1
            continue

        try:
            tags = _infer_with_retry(tagger, content, page_id)
            notion.update_tags(page_id, config.tag_property_name, tags)
            logger.info(f"[{i+1}/{len(records)}] Tagged: {page_id} -> {tags}")
            success += 1
        except RateLimitError as e:
            logger.error(f"Rate limit hit at record {i+1}/{len(records)}: {e}")
            logger.error("Aborting to avoid further rate limit errors.")
            failed += len(records) - i
            break
        except Exception as e:
            logger.error(f"Failed to tag {page_id}: {e}")
            failed += 1

        time.sleep(sleep_interval)

    return success, failed, skipped


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

    success, failed, skipped = process_records(records, notion, tagger, config)
    logger.info(f"Done. Success: {success}, Failed: {failed}, Skipped: {skipped}")


if __name__ == "__main__":
    main()
