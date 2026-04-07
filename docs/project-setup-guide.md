# 管理者向け運用ガイド（暫定版）

テンプレートの管理・プロジェクトのセットアップ・チームへの展開を行う管理者向けの手順書。

> **暫定版**: Git運用ルール・ブランチ戦略等、未決定事項は決定後に更新する。

---

## 目次

1. [管理者の責任範囲](#1-管理者の責任範囲)
2. [新規プロジェクトの立ち上げ](#2-新規プロジェクトの立ち上げ)
3. [チームへの展開](#3-チームへの展開)
4. [テンプレートの管理・更新](#4-テンプレートの管理更新)
5. [権限設定の管理](#5-権限設定の管理)
6. [Git運用の設計（未決定）](#6-git運用の設計未決定)
7. [運用チェックリスト](#7-運用チェックリスト)

---

## 1. 管理者の責任範囲

| 責任 | 内容 | メンバーの責任範囲 |
|---|---|---|
| テンプレート管理 | エージェント・コマンド・共通ルールの追加・修正 | `/upgrade` で受け取るだけ |
| プロジェクト立ち上げ | GitHubリポジトリ作成・初回push | `git clone` で参加 |
| 権限設定 | `settings.json` の管理・Git制限の有効化判断 | 設定に従う |
| Git運用ルール | ブランチ戦略・PRルールの策定 | ルールに従う |
| SF組織管理 | 組織の準備・メンバーのアカウント発行 | `sf org login` で認証 |

メンバーの日常手順は [オンボーディングガイド](onboarding.md) / [運用手順書](operations.md) を参照。

---

## 2. 新規プロジェクトの立ち上げ

### 2-1. プロジェクト作成

`setup.sh` でプロジェクトを作成する。ソースURLの指定有無で新規・既存を使い分ける。

```bash
# 新規プロジェクト（テンプレートから作成）
curl -sSL https://raw.githubusercontent.com/h-omata825/sf-claude-template/develop/scripts/setup.sh | bash -s <プロジェクト名> <作成先パス>

# 既存プロジェクトを別環境で再セットアップ
curl -sSL https://raw.githubusercontent.com/h-omata825/sf-claude-template/develop/scripts/setup.sh | bash -s <プロジェクト名> <作成先パス> <プロジェクトリポジトリURL>
```

#### 実行例

```bash
curl -sSL https://raw.githubusercontent.com/h-omata825/sf-claude-template/develop/scripts/setup.sh | bash -s project-a /c/workspace
```

### 2-2. SF組織に接続

```bash
cd /c/workspace/project-a
code .
```

VSCodeのClaude Codeパネルから:

```
/setup-sf-project
```

対話形式で組織種別（prod / dev）を選択し、ブラウザでSalesforceにログイン。

### 2-3. CLAUDE.md の初期設定

`CLAUDE.md`（ルート）をプロジェクト固有情報に書き換える。

| セクション | 記入内容 | 優先度 |
|---|---|---|
| Salesforce組織情報 | org alias（dev / prod）・環境URL | **必須** |
| 命名規則 | プレフィックス・命名パターン | **必須** |
| 権限設計ルール | 標準プロファイル禁止等のルール | 推奨 |
| 主要カスタムオブジェクト | セットアップ時点で把握しているもの | 推奨 |

### 2-4. 組織情報の資料化

```
/sf-analyze
```

`docs/overview/org-profile.md`（組織プロフィール）と `docs/requirements/requirements.md`（要件定義書の雛形）が自動生成される。

### 2-5. GitHubにpush

```bash
git init
git add .
git commit -m "Initial setup"
git remote add origin <GitHubリポジトリURL>
git push -u origin main
```

---

## 3. チームへの展開

### メンバーに共有するもの

| 情報 | 共有方法 |
|---|---|
| GitHubリポジトリURL | Slack / メール等 |
| Salesforce組織のURL | 管理者からアカウント発行と合わせて案内 |
| [オンボーディングガイド](onboarding.md) | リポジトリ内またはリンク共有 |

### メンバーがやること（管理者は見守るだけ）

```
1. git clone <リポジトリURL>
2. sf org login web -a dev -r https://test.salesforce.com
3. sf config set target-org dev
4. code .  （VSCodeで開く）
5. 動作確認
```

詳細は [オンボーディングガイド](onboarding.md) に全て記載済み。

---

## 4. テンプレートの管理・更新

### テンプレートリポジトリの構成

```
sf-claude-template（GitHub）
├── .claude/
│   ├── CLAUDE.md           ← 共通ルール
│   ├── settings.json       ← 権限設定
│   ├── agents/             ← エージェント定義（10体）
│   └── commands/           ← コマンド定義（8個）
├── scripts/
│   ├── setup.sh            ← 新規プロジェクト作成
│   ├── upgrade.sh          ← テンプレート更新
│   ├── setup-sf-project.sh ← SF組織認証
│   ├── setup-mcp.sh        ← MCP設定
│   └── sf-package.sh       ← メタデータ取得
├── docs/                   ← ドキュメントテンプレート
├── CLAUDE.md               ← プロジェクト固有ルールの雛形
└── README.md
```

### テンプレートを更新した場合のフロー

```
1. テンプレートリポジトリで変更をコミット・push
2. 各プロジェクトリポジトリで upgrade.sh を実行
   → bash scripts/upgrade.sh
3. 変更内容を確認して適用
4. git commit → PR → マージ
5. メンバーは git pull で受け取る
```

#### 誰がupgradeを実行するか

| パターン | メリット | デメリット |
|---|---|---|
| 管理者が実行してPR | 管理者が変更内容を把握 | 管理者の手間 |
| メンバーが各自実行 | 管理者の負担軽減 | 統一性の担保が必要 |

**推奨**: 管理者が1回実行 → PR → メンバーは `git pull` で受け取る。

### テンプレートのバージョン管理

`.claude/VERSION` にバージョンを記載する（upgrade.sh が自動で表示）。
タグを打つとバージョン指定でのupgradeが可能になる。

```bash
# テンプレートリポジトリ側
git tag v1.1.0
git push origin v1.1.0

# プロジェクト側
bash scripts/upgrade.sh v1.1.0
```

---

## 5. 権限設定の管理

### 現在の設定（テスト中モード）

`settings.json` で以下が自動ブロックされている:

| ブロック対象 | 理由 |
|---|---|
| 本番org（`*prod*`）へのデプロイ | 本番保護 |
| `.claude/` 配下の編集・書き込み | テンプレート保護 |
| `rm -rf` / `.claude` の削除 | 破壊的操作防止 |

### Git操作の制限（実運用時に有効化）

`settings.json` の `__pending.git_workflow` に以下が定義済み:

```json
"Bash(git push*)",
"Bash(git commit*)",
"Bash(git reset --hard*)",
"Bash(git branch -D*)",
"Bash(git branch -d main*)",
"Bash(git branch -d develop*)"
```

**有効化の手順**:

1. テンプレートリポジトリの `settings.json` を編集
2. `__pending.git_workflow.rules` の内容を `permissions.deny` に追加
3. テンプレートをcommit → push
4. 各プロジェクトで `bash scripts/upgrade.sh` を実行

**有効化の判断基準**: PR運用を開始するタイミング。少人数で試行中は無効のままでOK。

有効化後はClaude Codeからの `git push` / `git commit` 等がブロックされ、メンバーはターミナルから手動で実行する。

---

## 6. Git運用の設計（未決定）

> このセクションはチームのGit運用ルールが決まり次第、更新する。

### 検討事項

| 項目 | 選択肢 | 現状 |
|---|---|---|
| ブランチ戦略 | main直接 / main+feature / main+develop+feature | 未決定 |
| PR必須化 | あり / なし | 未決定（settings.jsonでの強制は準備済み） |
| コミットルール | Conventional Commits等 | 未決定 |
| マージ方法 | Merge / Squash / Rebase | 未決定 |

### 段階的導入の案

```
Phase 1（試行期間）:
  main直接コミット。Git制限なし。
  管理者がテンプレート更新時にPRを作る練習。

Phase 2（チーム開発開始）:
  feature/* ブランチ + PR必須。
  settings.jsonのgit_workflowを有効化。

Phase 3（安定運用）:
  main + develop + feature/* の3層。
  CIでテスト自動実行。
```

---

## 7. 運用チェックリスト

### プロジェクト立ち上げ時

- [ ] `setup.sh` でプロジェクト作成
- [ ] `/setup-sf-project` でSF組織認証
- [ ] `CLAUDE.md` にプロジェクト固有情報を記入
- [ ] `/sf-analyze` で組織情報を資料化
- [ ] GitHubリポジトリを作成し初回push
- [ ] メンバーにリポジトリURLとSF組織情報を共有
- [ ] メンバーのオンボーディング完了を確認

### テンプレート更新時

- [ ] テンプレートリポジトリで変更をcommit → push
- [ ] 代表プロジェクトで `bash scripts/upgrade.sh` を実行して動作確認
- [ ] 各プロジェクトでupgradeを実行（管理者 or メンバーに依頼）
- [ ] 変更内容をチームに案内

### 定期確認

- [ ] `settings.json` の権限設定が意図通りか
- [ ] メンバーのSF認証が有効か（期限切れの確認）
- [ ] `docs/` が最新か（`/sf-analyze` / `/sf-catalog` の再実行を検討）

---

## 関連資料

- [オンボーディングガイド](onboarding.md) — メンバー向け初回セットアップ
- [運用手順書](operations.md) — メンバー向け日常フロー
- [テンプレート説明書](template-guide.md) — エージェント・コマンドの詳細リファレンス
