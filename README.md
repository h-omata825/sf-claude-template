# sf-claude-template

Salesforce開発プロジェクト向け Claude Code テンプレート。

## 前提条件

| ツール | 最低バージョン | 確認コマンド |
|---|---|---|
| Git | 2.30+ | `git --version` |
| Salesforce CLI | 2.0+ (`sf` コマンド) | `sf --version` |
| Node.js | 18+ | `node --version` |
| Python | 3.10+ | `python --version` |
| Claude Code | 最新版 | `claude --version` |

## セットアップ

```bash
curl -sSL https://raw.githubusercontent.com/h-omata825/sf-claude-template/main/scripts/setup.sh | bash -s プロジェクト名
```

セットアップ後、Python ライブラリをインストールする（設計書生成機能を使う場合）:

```bash
pip install -r scripts/python/sf-doc-mcp/requirements.txt
```

詳細は `docs/template-guide.md` を参照。
