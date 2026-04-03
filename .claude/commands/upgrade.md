---
description: "テンプレートリポジトリの最新版を取得し、.claude/ 配下を更新する。プロジェクト固有ファイルは触らない。"
---

assistantエージェントとして、テンプレートのアップグレードを実行してください。

## 概要

テンプレートリポジトリから最新版を取得し、プロジェクトの `.claude/` 配下（エージェント・コマンド・共通ルール）を更新する。
プロジェクト固有ファイル（`CLAUDE.md`、`docs/`、`force-app/` 等）は一切変更しない。

## ユーザー入力

$ARGUMENTS

- **引数なし** → デフォルトのテンプレートURL・mainブランチを使用
- **URLのみ** → そのURLのmainブランチを使用
- **URL + タグ/ブランチ** → 指定バージョンを使用

デフォルトURL: `https://github.com/h-omata825/sf-claude-template.git`

---

## 更新対象 / 対象外

| 対象 | 更新 |
|---|---|
| `.claude/CLAUDE.md` | ✅ 上書き |
| `.claude/agents/*.md` | ✅ 上書き（追加・更新・削除検出） |
| `.claude/commands/*.md` | ✅ 上書き（追加・更新・削除検出） |
| `.claude/settings.json` | ❌ 除外（個人設定） |
| `CLAUDE.md`（ルート） | ❌ 除外（プロジェクト固有） |
| `.mcp.json` | ❌ 除外（個人設定） |
| `docs/` | ❌ 除外（プロジェクト資材） |
| `force-app/` | ❌ 除外（Salesforceメタデータ） |

---

## 実行手順

### Step 1: 前提チェック

1. `.claude/` フォルダが存在するか確認
   - 存在しない → 「このフォルダにはClaude Code設定が見つかりません。プロジェクトのルートフォルダで実行してください」と案内して中断
2. `git --version` を実行してGitが使えるか確認
   - 使えない → 「Gitがインストールされていません」と案内して中断

### Step 2: テンプレート取得

```bash
git clone --depth 1 --branch <ブランチ/タグ> <テンプレートURL> .claude-upgrade-tmp
```

- 失敗した場合 → URLとブランチ/タグを確認するよう案内
- 一時フォルダ `.claude-upgrade-tmp` が既に存在する場合 → 先に削除してからclone

取得できたら、バージョン情報を取得:
```bash
cd .claude-upgrade-tmp && git describe --tags --exact-match 2>/dev/null || echo "タグなし"
```

### Step 3: 差分チェック

以下のファイルを1つずつ比較し、変更があるものをリストアップする:

1. **`.claude/CLAUDE.md`**: 現在のファイルとテンプレートのファイルを比較
2. **`.claude/agents/*.md`**: 各エージェントファイルを比較
   - テンプレートにあってプロジェクトにない → 「新規追加」
   - 両方にあって内容が異なる → 「更新」
   - プロジェクトにあってテンプレートにない → 「削除対象（テンプレートから削除済み）」
3. **`.claude/commands/*.md`**: 同上

比較には `diff` コマンドを使う:
```bash
diff -q .claude/agents/salesforce-dev.md .claude-upgrade-tmp/.claude/agents/salesforce-dev.md
```

### Step 4: 結果報告と確認

変更がない場合:
```
テンプレートは最新です。変更はありません。
```
→ 一時フォルダを削除して終了

変更がある場合、変更内容を一覧表示:
```
テンプレートに以下の変更があります:

  更新: .claude/CLAUDE.md（共通ルール）
  更新: .claude/agents/salesforce-dev.md
  追加: .claude/agents/new-agent.md（新規エージェント）
  更新: .claude/commands/sf-implement.md
  削除対象: .claude/commands/old-command.md（テンプレートから削除済み）

合計: X件の変更

※ 以下は変更されません:
  - CLAUDE.md（プロジェクト固有ルール）
  - .claude/settings.json（個人設定）
  - .mcp.json（個人設定）
  - docs/（プロジェクト資材）

適用しますか？
```

ユーザーが「いいえ」→ 一時フォルダを削除して終了。

### Step 5: 適用

ユーザーが「はい」の場合、以下のコマンドを順番に実行:

```bash
# 共通ルール
cp .claude-upgrade-tmp/.claude/CLAUDE.md .claude/CLAUDE.md

# エージェント（テンプレートにあるものを全てコピー）
cp .claude-upgrade-tmp/.claude/agents/*.md .claude/agents/

# コマンド（テンプレートにあるものを全てコピー）
cp .claude-upgrade-tmp/.claude/commands/*.md .claude/commands/
```

**削除対象** として検出されたファイル（テンプレートから消えたもの）がある場合:
```
以下のファイルはテンプレートから削除されています。プロジェクトからも削除しますか？
  - .claude/commands/old-command.md

（はい / いいえ / 個別に確認）
```

### Step 6: クリーンアップ

```bash
rm -rf .claude-upgrade-tmp
```

### Step 7: 完了報告

```
アップグレード完了

テンプレートバージョン: <バージョン or タグなし>
変更件数: X件

次のステップ:
  1. 変更内容を確認:  git diff .claude/
  2. コミット・PR:    変更を確認したらコミットしてPRを作成
```

---

## 注意事項

- `.claude/settings.json` はアップグレード対象外。テンプレート側で新しい権限設定が追加された場合は手動マージが必要。その場合は差分を表示して案内する:
  ```bash
  diff .claude/settings.json .claude-upgrade-tmp/.claude/settings.json
  ```
- 一時フォルダ `.claude-upgrade-tmp` はプロジェクトフォルダ内に作成されるが、処理完了後に必ず削除する
- git push / git commit は実行しない（ユーザーが手動で行う）
