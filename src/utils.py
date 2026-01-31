"""ユーティリティモジュール"""


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
