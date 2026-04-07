# 運用手順書 — Salesforce + Claude Code

日常の開発フロー・運用ルール。全メンバー対象。

---

## 全体像

```
プロジェクトリポジトリ（GitHub）
  └── project-A/
        ├── .claude/           ← 触らない（テンプレートから配布）
        ├── CLAUDE.md          ← プロジェクト固有ルール（チームで編集）
        ├── docs/              ← プロジェクト資材（充実させるほどClaude Codeが賢くなる）
        └── force-app/         ← Salesforceメタデータ
```

**基本方針**:
- `.claude/` は触らない。更新は `/upgrade` コマンドで行う
- `CLAUDE.md`（ルート）にプロジェクト固有の情報・決定事項を書き込む
- `docs/` を充実させる → Claude Codeの出力精度が向上する

---

## 1. 日常の開発フロー

### 保守案件（メイン）

現行の本番環境を壊さないことを最優先に動く。

#### 1-1. バグ・エラー対応（緊急度: 高）

本番エラーは最優先で対応する。

```
【対応フロー】
1. エラー内容・デバッグログを Claude Code に貼り付ける
   →「本番でエラーが出てる。デバッグログはこれ」
   → maintenance エージェントが自動選択

2. ログ解析・原因特定
   → Claude Codeが原因箇所・影響範囲を特定

3. 修正方針をClaude Codeに確認してから実装
   → 「この原因で、こう修正する。問題ないか？」

4. Sandboxで検証
   → sf project deploy start --target-org dev

5. 問題なければ本番対応へ（管理者の確認を経る）
```

**デバッグログの取得方法:**

```bash
# Apexクラスのデバッグログを有効化
sf apex log tail --target-org dev

# 特定のユーザーに絞る場合
sf apex log tail --target-org dev -u user@example.com
```

**よくある本番エラーのパターン:**

| エラー | Claude Codeへの伝え方 |
|---|---|
| System.LimitException（ガバナ制限） | ログ全文を貼り付け「ガバナ制限でエラーが出ている。原因と修正案を教えて」 |
| SOQL_VALIDATION_EXCEPTION | クエリ文とエラー文を貼り付け |
| フロー実行エラー | フロー名とエラーメッセージを貼り付け |
| トリガーの意図しない動作 | 「Accountを更新したら〇〇が起きた。原因を調べて」 |

#### 1-2. 保守開発（機能追加・改修）

既存機能への追加・変更。既存コードへの影響調査を必ず行う。

```
1. 依頼内容をClaude Codeに伝える
   →「〇〇に△△の機能を追加したい」
   → salesforce-dev or salesforce-architect が自動選択

2. 影響調査（重要）
   →「この変更で影響を受けるクラス・フローを調べて」
   → reviewer エージェントが依存関係を確認

3. 設計確認後に実装
   → docs/design/ に設計メモを残すと後で役立つ

4. テストクラスの更新
   → 既存テストが落ちないことを確認

5. ブランチ作成 → /git-pr でPR作成 → developにマージ
```

**保守開発でよく使うコマンド:**

| やりたいこと | コマンド |
|---|---|
| 影響のあるクラス・フロー・項目を把握したい | `/sf-analyze` で組織情報を最新化 |
| 既存オブジェクトの項目構成を確認したい | `/sf-catalog Account` |
| メタデータを取得して手元に持ってきたい | `/sf-retrieve` |
| 変更をブランチにコミット・PRを作成したい | `/git-pr` |

#### 1-3. 緊急本番修正（ホットフィックス）

本番のみに影響する緊急バグ。通常の feature/* フローを経ずに `main` から直接修正する。

```
【hotfix フロー】
1. main から hotfix/* ブランチを作成
   git checkout main
   git checkout -b hotfix/001-login-error

2. Claude Code で修正（maintenance エージェント）

3. Sandbox で動作確認

4. main へ PR → マージ（管理者承認必須）

5. develop にも同じ修正をマージ（cherry-pick or 手動）
   git checkout develop
   git cherry-pick <コミットハッシュ>
```

> **ホットフィックス原則**: 最小限の修正にとどめる。本番への影響を最小化するため、関係のないリファクタリング・整理は一切行わない。

---

### 新規案件（簡易版）

新規プロジェクトは設計 → 実装 → レビューの順で進める。

```
1. 要件をClaude Codeに伝える（salesforce-architect が設計書を作成）
2. /sf-design で設計書を生成
3. 実装（salesforce-dev）
4. コードレビュー（reviewer）
5. テスト（qa-engineer）
6. /git-pr でPR作成 → develop → main の順にマージ
```

詳細は `project-setup-guide.md` を参照。

---

## 2. CLAUDE.md の管理

### 書くと効果が高いもの

| セクション | 効果 |
|---|---|
| 命名規則 | 生成コードの命名が統一される |
| 主要オブジェクト | 関連コードを書くとき正しいAPI名で参照される |
| 過去の決定事項 | 「なぜそうなっているか」をClaude Codeが理解する |
| 注意事項・地雷 | 同じミスを繰り返さなくなる |

### 誰が書くか

| ファイル | 誰が | 頻度 |
|---|---|---|
| `CLAUDE.md`（ルート） | チームメンバー全員 | 決定事項が出たらその都度 |
| `.claude/CLAUDE.md` | 管理者（テンプレート経由） | 触らない |

---

## 3. docs/ の管理

### docs/ はプロジェクトの「記憶」

Claude Codeは作業前に `docs/` を参照する。ここが充実しているほど、プロジェクト文脈を踏まえた精度の高い出力になる。

| フォルダ | いつ更新するか | 更新方法 |
|---|---|---|
| `docs/overview/` | プロジェクト開始時・組織構成が変わったとき | `/sf-analyze` |
| `docs/requirements/` | 要件が確定・変更されたとき | `/sf-analyze` or 手動 |
| `docs/design/` | 機能設計が確定したとき | `/sf-design` |
| `docs/catalog/` | オブジェクト・項目を追加・変更したとき | `/sf-catalog` |
| `docs/data/` | データ移行・分析が必要なとき | `/sf-data` |
| `docs/minutes/` | 会議・打ち合わせのたび | 手動 |
| `docs/test/` | テスト仕様が必要なとき | 手動 |
| `docs/manuals/` | 手順書が必要なとき | 手動 |

> docs/ の更新はClaude Codeが自動では行わない。更新が必要な場合は案内してくれるので、コマンドを実行する。

---

## 4. テンプレートの更新

テンプレートが更新された場合（管理者から案内がある）、プロジェクトルートで:

```bash
bash scripts/upgrade.sh
```

差分の一覧が表示され、確認後に適用される。

```
  追加: .claude/agents/new-agent.md（新規エージェント）
  更新: .claude/CLAUDE.md（共通ルール）
  合計: 2件の変更

適用しますか？ (y/N): y
```

特定バージョンを指定する場合: `bash scripts/upgrade.sh v1.2.0`

### 更新される / されないもの

| 対象 | 更新 |
|---|---|
| `.claude/CLAUDE.md`（共通ルール） | 上書き |
| `.claude/agents/`（エージェント） | 追加・更新・削除検出 |
| `.claude/commands/`（コマンド） | 追加・更新・削除検出 |
| `scripts/`（ヘルパースクリプト） | 上書き |
| `.claude/settings.json` | 上書き（変更があれば差分表示） |
| `CLAUDE.md`（ルート） | **対象外**（プロジェクト固有） |
| `docs/` / `force-app/` / `.mcp.json` | **対象外** |

---

## 5. MCP連携（外部ツール）

### 初回設定

```
/setup-mcp
```

対話形式で接続先とトークンを入力する。

### 主なMCP

| MCP | 用途 | 優先度 |
|---|---|---|
| **GitHub** | PRレビュー・Issue管理 | 推奨 |
| Slack | Slack連携 | オプション |
| Notion | Notion連携 | オプション |

### トークンの再設定

期限切れなどで再設定が必要な場合:

```
/setup-mcp
```

「変更」を選択してトークンを更新する。

> `.mcp.json` は `.gitignore` 対象。各自で設定する必要がある。

---

## 6. 権限設定（settings.json）

以下の操作はClaude Codeから **自動ブロック** される。メンバーが意識する必要はないが、知っておくと良い。

| ブロックされる操作 | 理由 |
|---|---|
| 本番org（`*prod*`）へのデプロイ | 本番保護 |
| `.claude/` 配下の編集・書き込み | テンプレート保護 |
| `rm -rf` / `.claude` の削除 | 破壊的操作の防止 |

それ以外の操作（Sandbox等へのデプロイ、通常のファイル編集等）は自動実行される。

---

## 7. Git運用

### ブランチ戦略

```
main
  └── 本番と同期。直接コミット禁止。hotfix/* or develop からのPRのみ受け付ける

develop
  └── 開発・検証のベース。feature/* からのPRでマージ

feature/NNN-説明
  └── 機能追加・保守開発。developから分岐。/git-pr で作成

hotfix/NNN-説明
  └── 緊急本番修正。mainから分岐。mainへPR後、developにもcherry-pick
```

### 基本的な作業フロー

```bash
# 1. 最新の develop を取得
git checkout develop
git pull origin develop

# 2. feature ブランチを作成（または /git-pr コマンドで自動化）
git checkout -b feature/001-account-trigger

# 3. 作業・コミット（/git-pr で対話的に実行）
/git-pr

# 4. PR: feature/* → develop（GitHub上でマージ）

# 5. リリース時: develop → main（管理者が実施）
```

### Git管理対象

| ファイル | Git管理 | 理由 |
|---|---|---|
| `.claude/` 配下 | **対象** | テンプレート設定をチーム全員に配布 |
| `.claude/settings.json` | **対象** | 権限設定をチーム全員に強制 |
| `CLAUDE.md` / `docs/` / `force-app/` | **対象** | プロジェクト資材 |
| `.mcp.json` | **対象外** | 個人のトークン情報を含む |

### Git操作の制限

現在は `git push` / `git commit` 等にブロックはかかっていない（確認ダイアログが出る）。
チーム運用が本格化した段階で、管理者がsettings.jsonにGit操作の制限を追加する場合がある。

制限が有効化された場合:
- Claude Codeからの `git push` / `git commit` / `git reset --hard` がブロックされる
- `/git-pr` コマンドまたはターミナルから手動で実行する

---

## 関連資料

- [オンボーディングガイド](onboarding.md) — 初回セットアップ手順
- [テンプレート説明書](template-guide.md) — エージェント・コマンド・設定の詳細リファレンス
- [プロジェクトセットアップガイド](project-setup-guide.md) — 管理者向け
