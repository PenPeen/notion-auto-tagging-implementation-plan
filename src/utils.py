"""ユーティリティモジュール"""

# extract_block_text が対応するブロックタイプ
_RICH_TEXT_BLOCK_TYPES = {
    "paragraph",
    "heading_1",
    "heading_2",
    "heading_3",
    "bulleted_list_item",
    "numbered_list_item",
    "quote",
    "callout",
    "toggle",
    "to_do",
}


def extract_block_text(block: dict) -> str:
    """単一ブロックからプレーンテキストを抽出する。

    対応ブロック:
      paragraph, heading_1/2/3, bulleted/numbered_list_item,
      quote, callout, toggle, to_do, code
    非対応ブロックは空文字を返す。
    """
    block_type = block.get("type", "")

    if block_type in _RICH_TEXT_BLOCK_TYPES:
        rich_texts = block.get(block_type, {}).get("rich_text", [])
        return "".join(rt.get("plain_text", "") for rt in rich_texts)

    if block_type == "code":
        code_data = block.get("code", {})
        rich_texts = code_data.get("rich_text", [])
        text = "".join(rt.get("plain_text", "") for rt in rich_texts)
        language = code_data.get("language", "")
        if language:
            return f"[{language}] {text}"
        return text

    return ""


def extract_body_content(blocks: list, max_chars: int = 4000) -> str:
    """ブロックリストからプレーンテキストを結合して返す。

    max_chars を超えた時点で切り詰める。
    """
    lines = []
    total = 0
    for block in blocks:
        text = extract_block_text(block)
        if not text:
            continue
        if total + len(text) > max_chars:
            remaining = max_chars - total
            if remaining > 0:
                lines.append(text[:remaining])
            break
        lines.append(text)
        total += len(text) + 1  # +1 for newline
    return "\n".join(lines)


def extract_content(page: dict, properties: list) -> dict:
    """ページから指定プロパティの内容を抽出"""
    content = {}
    props = page.get("properties", {})

    for prop_name in properties:
        if prop_name not in props:
            continue

        prop = props[prop_name]
        prop_type = prop.get("type")

        if prop_type == "title":
            content[prop_name] = "".join(
                t.get("plain_text", "") for t in prop.get("title", [])
            )
        elif prop_type == "rich_text":
            content[prop_name] = "".join(
                t.get("plain_text", "") for t in prop.get("rich_text", [])
            )
        elif prop_type == "url":
            content[prop_name] = prop.get("url", "")
        elif prop_type == "select":
            select = prop.get("select")
            if select:
                content[prop_name] = select.get("name", "")
        elif prop_type == "multi_select":
            content[prop_name] = ", ".join(
                s.get("name", "") for s in prop.get("multi_select", [])
            )

    return content
