# Notion Knowledge DB 自動タグ付けシステム

Notion データベースの各レコードに対し、LLM（Gemini / Claude）を使用して自動でタグを付与するシステム。

## 機能

- **初回実行**: データベースの全レコードにタグを自動付与
- **差分実行**: 指定時間内に更新されたレコードのみ処理
- **LLM選択**: Gemini（無料）と Claude（高精度）を切り替え可能
- **既存タグ活用**: DB内の既存タグをLLMに渡し、タグの一貫性を維持
- **GitHub Actions**: 定期実行（毎日JST 3:00）・手動実行に対応

## 処理フロー

```
Notion API (データ取得) → LLM (タグ推論) → Notion API (タグ更新)
```

## セットアップ

### 1. Notion Integration の準備

1. [Notion Integrations](https://www.notion.so/my-integrations) でInternal Integrationを作成
2. 対象データベースで「...」→「接続」→ 作成したIntegrationを追加
3. データベースのURLからDatabase IDを取得
   ```
   https://www.notion.so/<DATABASE_ID>?v=xxx
   ```

### 2. GitHub Secrets の設定

リポジトリの Settings → Secrets and variables → Actions で以下を設定:

| Secret名 | 説明 | 必須 |
|----------|------|------|
| `NOTION_API_KEY` | Notion Integration のAPIキー | Yes |
| `NOTION_DATABASE_ID` | 対象データベースのID | Yes |
| `GEMINI_API_KEY` | Google AI Studio のAPIキー | 定期実行時 |
| `CLAUDE_API_KEY` | Anthropic のAPIキー | Claude使用時 |

### 3. 実行

GitHub Actions の「Run workflow」から手動実行:

| パラメータ | 選択肢 | 説明 |
|-----------|--------|------|
| mode | `initial` | 全レコード処理（初回） |
|  | `incremental` | 24時間以内の更新分のみ（デフォルト） |
| llm | `gemini` | Gemini API（無料、デフォルト） |
|  | `claude` | Claude API（高精度） |

定期実行は毎日 JST 3:00 に `incremental` + `gemini` で自動実行されます。

## 環境変数

GitHub Secrets 経由で以下の環境変数が設定されます:

| 変数名 | デフォルト | 説明 |
|--------|-----------|------|
| `NOTION_API_KEY` | - | Notion APIキー |
| `NOTION_DATABASE_ID` | - | 対象データベースID |
| `GEMINI_API_KEY` | - | Gemini APIキー |
| `CLAUDE_API_KEY` | - | Claude APIキー（オプション） |
| `TAG_PROPERTY_NAME` | `Tags` | タグ用プロパティ名 |
| `CONTENT_PROPERTIES` | `Name,Content` | タグ推論に使うプロパティ名（カンマ区切り） |

## ディレクトリ構成

```
├── src/
│   ├── __init__.py
│   ├── main.py              # エントリーポイント
│   ├── notion_service.py    # Notion API操作
│   ├── tagger.py            # LLMタグ推論（Gemini/Claude）
│   ├── config.py            # 設定管理
│   └── utils.py             # ユーティリティ
├── tests/
│   └── test_tagger.py
├── .github/workflows/
│   └── auto-tag.yml         # GitHub Actions ワークフロー
├── requirements.txt
├── Dockerfile
└── README.md
```

## 技術スタック

| コンポーネント | 技術 |
|--------------|------|
| 言語 | Python 3.11+ |
| Notion連携 | notion-client (Notion API 2025-09-03) |
| AI (デフォルト) | google-generativeai (Gemini) |
| AI (オプション) | anthropic (Claude) |
| CI/CD | GitHub Actions |

## ライセンス

MIT
