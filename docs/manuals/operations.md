# 運用手順書 — Salesforce Development OS

テンプレートを使ったプロジェクト運用の定義書。
テンプレート管理・プロジェクトライフサイクル・アップグレード・ロール定義を規定する。

---

## 目次

1. [運用モデル概要](#1-運用モデル概要)
2. [ロールと責務](#2-ロールと責務)
3. [新規プロジェクト作成](#3-新規プロジェクト作成)
4. [日常の開発フロー](#4-日常の開発フロー)
5. [CLAUDE.md の管理](#5-claudemd-の管理)
6. [テンプレートのアップグレード](#6-テンプレートのアップグレード)
7. [プロジェクト資材の管理](#7-プロジェクト資材の管理)
8. [MCP連携の管理](#8-mcp連携の管理)
9. [運用モデル案の比較](#9-運用モデル案の比較)

---

## 1. 運用モデル概要

### 構成図

```
テンプレートリポジトリ（GitHub）
  └── sf-claude-template          ← 共通テンプレート（管理者がメンテ）
        ├── .claude/              ← エージェント・コマンド・共通ルール
        ├── CLAUDE.md             ← プロジェクト固有ルールの雛形
        ├── docs/                 ← ドキュメントテンプレート
        └── setup.sh / setup-sf-project.md

プロジェクトリポジトリ（GitHub）
  └── project-A/                  ← テンプレートからコピーして作成
        ├── .claude/              ← テンプレートからコピー（原則そのまま）
        ├── CLAUDE.md             ← プロジェクト固有に編集
        ├── docs/                 ← プロジェクト資材を蓄積
        ├── force-app/            ← Salesforceメタデータ（SFDX生成）
        └── manifest/             ← package.xml（SFDX生成）
```

### 基本方針

| 方針 | 内容 |
|---|---|
| **テンプレートは一元管理** | 1つのリポジトリでテンプレートを管理。全プロジェクト共通 |
| **プロジェクトはテンプレートからコピー** | コピー後は独立したリポジトリとして運用 |
| **共通ルール(.claude/)は原則変更しない** | 変更はテンプレート側で行い、プロジェクトに配布 |
| **プロジェクト固有ルール(CLAUDE.md)はプロジェクトで管理** | PM/メンバーが編集 |
| **メンバーは同一環境で作業** | 同じプロジェクトの全員が同じCLAUDE.md・エージェント・コマンドを使う |

---

## 2. ロールと責務

### テンプレート管理者

テンプレートリポジトリの管理責任者（1〜2名）。

| 責務 | 内容 |
|---|---|
| テンプレートのメンテ | エージェント・コマンド・共通ルールの改善・追加 |
| アップグレード告知 | 更新内容をチームに周知し、適用を促す |
| PRレビュー | メンバーからのテンプレート改善PRをレビュー |
| オンボーディング支援 | 新規メンバーの環境構築をサポート |

### PM / プロジェクトリード

プロジェクトリポジトリの管理者。

| 責務 | 内容 |
|---|---|
| プロジェクト作成 | テンプレートからプロジェクトリポジトリを作成 |
| CLAUDE.md管理 | プロジェクト固有ルール・命名規則・組織情報を記載・更新 |
| docs/管理 | 要件定義書・設計書・議事録のレビュー・承認 |
| テンプレートアップグレード適用 | 新バージョンのテンプレートをプロジェクトに適用 |

### プロジェクトメンバー

| 責務 | 内容 |
|---|---|
| 環境セットアップ | オンボーディングガイドに沿って環境構築 |
| 日常開発 | エージェント・コマンドを活用して開発 |
| フィードバック | `/feedback` で気づき・決定事項を記録 |
| CLAUDE.md更新提案 | 命名規則変更・注意事項追加などをPRで提案 |
| テンプレート改善提案 | 共通ルール・エージェントの改善をテンプレートリポジトリにPRで提案 |

---

## 3. 新規プロジェクト作成

### 手順（PM/プロジェクトリード向け）

#### 方法1: セットアップコマンド（推奨）

Claude Codeで以下を実行:
```
/setup-sf-project
```

対話形式で必要情報を入力すると、SFDXプロジェクト作成・テンプレート配置・組織認証が一括で行われる。

#### 方法2: setup.sh（CLI）

```bash
bash setup.sh <プロジェクト名> <作成先パス>
# 例: bash setup.sh CaseManagement C:/workspace
```

#### 方法3: 手動セットアップ

```bash
# 1. SFDXプロジェクト作成
sf project generate -n <プロジェクト名> -d <作成先> --manifest

# 2. テンプレートを取得
git clone <テンプレートURL> .claude-template-tmp

# 3. テンプレートファイルをコピー
cp -r .claude-template-tmp/.claude .claude
cp .claude-template-tmp/CLAUDE.md CLAUDE.md
cp -r .claude-template-tmp/docs docs
cp .claude-template-tmp/.mcp.json .mcp.json

# 4. 一時フォルダを削除
rm -rf .claude-template-tmp

# 5. .gitignore に追記
echo ".claude/settings.json" >> .gitignore
```

### 作成後のチェックリスト

- [ ] `CLAUDE.md` のプロジェクト情報を記入（組織情報・命名規則・主要オブジェクト）
- [ ] Salesforce組織に認証し、デフォルト組織を設定
- [ ] GitHubにリポジトリを作成し、初回pushを行う
- [ ] メンバーをリポジトリに招待
- [ ] `.mcp.json` の利用有無を決定し、不要なMCPは `"disabled": true` のままにする

---

## 4. 日常の開発フロー

### ブランチ戦略

```
main（本番）
  └── develop（開発統合）
        ├── feature/PROJ-001-xxx   ← 機能開発
        ├── bugfix/PROJ-002-xxx    ← バグ修正
        └── hotfix/PROJ-003-xxx    ← 緊急修正（mainから分岐）
```

| ブランチ | 作成元 | マージ先 | 用途 |
|---|---|---|---|
| `main` | — | — | 本番環境と同期。直接pushしない |
| `develop` | `main` | `main` | 開発統合。リリース時にmainへマージ |
| `feature/*` | `develop` | `develop` | 機能開発・設定変更 |
| `bugfix/*` | `develop` | `develop` | バグ修正 |
| `hotfix/*` | `main` | `main` + `develop` | 緊急の本番修正 |

### 開発サイクル

```
1. ブランチ作成
   git checkout -b feature/PROJ-001-account-trigger develop

2. Claude Codeで開発
   /sf-implement Account更新時に関連Contactを更新するトリガー

3. レビュー依頼前にセルフレビュー
   /sf-review force-app/main/default/triggers/AccountTrigger.trigger

4. コミット・プッシュ・PR作成
   git add . && git commit -m "feat: Account更新時のContact同期トリガー"
   git push -u origin feature/PROJ-001-account-trigger
   → GitHubでPR作成

5. レビュー・マージ
   → レビュアーがClaude Codeで /sf-review してもOK

6. developにマージ後、Sandbox検証
   sf project deploy start -x manifest/package.xml -o dev

7. リリース時: develop → main → 本番デプロイ
   /sf-deploy 本番デプロイ
```

### Claude Codeの使い分け

| やりたいこと | 使うもの |
|---|---|
| 新機能の実装 | `/sf-implement [内容]` |
| バグ調査・修正 | `/sf-debug [症状]` |
| コードレビュー | `/sf-review [対象]` |
| デプロイ支援 | `/sf-deploy [環境]` |
| 決定事項の記録 | `/feedback [内容]` |
| 資料の保存 | `/save-doc` |
| 上記以外 | 自然言語で直接依頼 → 自動でエージェント選択 |

---

## 5. CLAUDE.md の管理

### 2つの CLAUDE.md の役割分担

| ファイル | 管理者 | 編集頻度 | 内容 |
|---|---|---|---|
| `.claude/CLAUDE.md` | テンプレート管理者 | 低（テンプレート更新時のみ） | 共通ルール・品質基準・エージェント選択 |
| `CLAUDE.md`（ルート） | PM / メンバー | 中〜高 | プロジェクト固有ルール・命名規則・決定事項 |

### ルートCLAUDE.md の更新フロー

#### 方法1: `/feedback` コマンドで記録（推奨・手軽）

```
/feedback 受注オブジェクトはOpportunityを流用することに決定。新規オブジェクトは作らない。
```

→ `CLAUDE.md` の「過去の判断・決定事項」セクションに自動追記される。

#### 方法2: PRで更新（正式な変更）

命名規則変更・注意事項追加など、チーム全体に影響する変更はPRで行う。

```
1. メンバーがブランチを作成
   git checkout -b docs/update-naming-convention

2. CLAUDE.md を編集

3. PRを作成し、PMがレビュー・マージ
```

### 更新すべきタイミング

| タイミング | 更新内容 | 誰が |
|---|---|---|
| プロジェクト開始時 | 組織情報・命名規則・主要オブジェクト | PM |
| 設計決定時 | 判断・決定事項を追記 | 担当者（`/feedback`） |
| ハマりポイント発見時 | 注意事項・地雷を追記 | 発見者（`/feedback`） |
| 新メンバー参加時 | 不足している前提知識を追記 | PM / メンバー |
| スプリント振り返り時 | ルール・規約の見直し | チーム |

---

## 6. テンプレートのアップグレード

テンプレートが更新された場合、既存プロジェクトに変更を取り込む手順。

### アップグレード対象

| 対象 | 頻度 | 方法 |
|---|---|---|
| `.claude/agents/*.md` | テンプレート更新時 | ファイル上書き |
| `.claude/commands/*.md` | テンプレート更新時 | ファイル上書き |
| `.claude/CLAUDE.md` | テンプレート更新時 | ファイル上書き |
| `.claude/settings.json` | テンプレート更新時 | マージ（個人設定を保持） |
| `CLAUDE.md`（ルート） | **対象外** | プロジェクト固有のため触らない |
| `docs/` | **対象外** | プロジェクト資材のため触らない |

### アップグレード手順

#### 方法A: 手動コピー（シンプル・確実）

```bash
# 1. テンプレートの最新版を取得
git clone <テンプレートURL> .claude-template-tmp

# 2. .claude/ 配下を上書き（settings.json以外）
cp -r .claude-template-tmp/.claude/agents/ .claude/agents/
cp -r .claude-template-tmp/.claude/commands/ .claude/commands/
cp .claude-template-tmp/.claude/CLAUDE.md .claude/CLAUDE.md

# 3. settings.json は差分確認してから手動マージ
diff .claude/settings.json .claude-template-tmp/.claude/settings.json

# 4. 一時フォルダ削除
rm -rf .claude-template-tmp

# 5. コミット
git add .claude/
git commit -m "chore: Claude Codeテンプレートをv1.x.xに更新"
```

#### 方法B: アップグレードスクリプト（自動化案）

> **TODO**: 今後、`upgrade.sh` を用意して自動化する想定。
> スクリプトの仕様案:
> ```bash
> bash upgrade.sh <テンプレートURL> [バージョンタグ]
> ```
> - テンプレートを取得し、`.claude/` 配下を上書き
> - `settings.json` は差分を表示して確認を求める
> - 変更内容をサマリー表示

#### 方法C: Git Subtreeで管理（上級・検討中）

`.claude/` をGit Subtreeとして管理し、テンプレートリポジトリの変更を `git subtree pull` で取り込む方式。

```bash
# 初回設定
git subtree add --prefix=.claude <テンプレートURL> main --squash

# アップグレード時
git subtree pull --prefix=.claude <テンプレートURL> main --squash
```

**メリット**: Git操作だけで完結、履歴が追える
**デメリット**: チームのGitスキルが必要、コンフリクト対応が必要

### バージョン管理

テンプレートリポジトリではGitタグでバージョンを管理する:

```bash
git tag -a v1.0.0 -m "初期リリース"
git tag -a v1.1.0 -m "reviewerエージェント改善、sf-analyzeコマンド追加"
```

変更履歴は `docs/changelog.md`（テンプレートリポジトリ側）に記録する。

### アップグレード通知フロー

```
1. テンプレート管理者がテンプレートを更新・タグ付け
2. 変更内容をSlack/メール等でチームに周知
3. 各プロジェクトのPMがアップグレード要否を判断
4. PMがアップグレードを実施し、PRでチームに通知
```

---

## 7. プロジェクト資材の管理

### docs/ フォルダの運用

| フォルダ | 内容 | 生成方法 | 更新タイミング |
|---|---|---|---|
| `docs/overview/` | 組織プロフィール | `/sf-analyze` | 初回・組織変更時 |
| `docs/requirements/` | 要件定義書 | `/sf-analyze` or 手動 | 要件変更時 |
| `docs/design/` | 設計書 | 手動 or エージェント | 設計変更時 |
| `docs/catalog/` | オブジェクト・項目定義書 | `/sf-analyze` | メタデータ変更時 |
| `docs/data/` | データ分析 | エージェント | 必要時 |
| `docs/test/` | テスト仕様 | 手動 or エージェント | テスト計画時 |
| `docs/minutes/` | 議事録 | 手動 or エージェント | 会議後 |
| `docs/manuals/` | 手順書・マニュアル | 手動 or エージェント | 必要時 |
| `docs/changelog.md` | 変更履歴 | 自動追記 | コマンド実行時 |

### ドキュメント作成のベストプラクティス

- コマンドで生成できるもの（`/sf-analyze` 等）は積極的にコマンドを使う
- 生成後のレビュー・修正は必ず人が行う
- 議事録は会議直後に整理する（Claude Codeに生メモを貼り付けて整理させる）
- 設計変更時は `CLAUDE.md` の関連セクションも更新する

---

## 8. MCP連携の管理

### MCP有効化の判断

| MCP | 有効化の目安 | 注意 |
|---|---|---|
| GitHub | GitHubでソース管理する場合 | PRレビュー連携等に便利 |
| Slack | チーム通知を自動化したい場合 | Bot権限の範囲に注意 |
| Google Drive | 資料をDriveで管理する場合 | OAuth設定が必要 |
| Notion | ナレッジをNotionで管理する場合 | Integration Token |
| Playwright | UI自動テストを行う場合 | ブラウザ環境が必要 |

### トークン管理

- `.mcp.json` に直接トークンを書くのは**非推奨**（Git管理されるため）
- 推奨: 環境変数に切り出す
  ```json
  "env": {
    "GITHUB_PERSONAL_ACCESS_TOKEN": "$GITHUB_TOKEN"
  }
  ```
- 各メンバーが自分の `.env` または OS環境変数で設定

---

## 9. 運用モデル案の比較

テンプレート管理と更新の運用モデルとして、3つの案を比較する。
チームの規模・スキル・運用負荷に応じて選択する。

### 案A: PM集中管理型（小〜中規模向け・推奨）

```
テンプレート管理者 → テンプレートリポジトリを更新
                ↓ 周知
PM/リード       → プロジェクトにアップグレードを適用（手動コピー）
                → CLAUDE.md をメンテ
メンバー        → /feedback でフィードバック
                → CLAUDE.md更新のPRを出すことも可
```

**メリット**: シンプル。PMが品質をコントロールしやすい
**デメリット**: PMの負荷が集中する。PMがボトルネックになりうる
**向いている**: プロジェクト数が少ない、PMが技術に明るい

### 案B: メンバー自律型（中〜大規模向け）

```
テンプレート管理者 → テンプレートリポジトリを更新
                ↓ 周知
メンバー        → テンプレートアップグレードのPRを作成
                → CLAUDE.md更新のPRを作成
PMリード        → PRをレビュー・マージ
```

**メリット**: PMの負荷分散。メンバーの当事者意識が高まる
**デメリット**: PRレビュー負荷。CLAUDE.mdの品質にばらつきが出うる
**向いている**: メンバーのGitスキルが高い、自律的なチーム

### 案C: 自動配布型（大規模・将来構想）

```
テンプレート管理者 → テンプレートリポジトリを更新・タグ付け
                ↓ CI/CD（GitHub Actions等）
各プロジェクト   → 自動でPRが作成される
PM              → PRをレビュー・マージ
```

**メリット**: 配布の手間ゼロ。全プロジェクトに確実に届く
**デメリット**: CI/CDの構築・メンテが必要。コンフリクト対応が発生する
**向いている**: プロジェクト数が多い、DevOps体制がある

### 推奨: まずは案Aで開始 → 必要に応じて案Bへ移行

1. **初期**: PM集中管理型で運用開始。テンプレート管理者 = PM を兼任でもOK
2. **安定期**: メンバーが慣れたら、CLAUDE.md更新はメンバーPR方式に移行
3. **拡大期**: プロジェクト数が増えたら、アップグレードスクリプトの自動化 or CI/CDを検討

---

## 付録: 運用チェックリスト

### プロジェクト開始時

- [ ] テンプレートから新規プロジェクトを作成
- [ ] `CLAUDE.md` にプロジェクト情報を記入
- [ ] GitHubリポジトリを作成・メンバー招待
- [ ] Salesforce組織認証の完了を全員確認
- [ ] MCP連携の要否を決定

### スプリントごと

- [ ] `CLAUDE.md` の「決定事項」「注意事項」を更新（必要なら）
- [ ] `docs/` の資材を最新化
- [ ] テンプレートの新バージョンがないか確認

### リリース時

- [ ] `/sf-deploy` でデプロイ前チェックを実施
- [ ] `docs/changelog.md` に変更内容を記録
- [ ] 必要に応じてメタデータのバックアップ

### 四半期ごと（テンプレート管理者）

- [ ] エージェント・コマンドの改善・追加を検討
- [ ] チームからのフィードバックをテンプレートに反映
- [ ] バージョンタグを付けてリリース
- [ ] 全プロジェクトへのアップグレードを周知
