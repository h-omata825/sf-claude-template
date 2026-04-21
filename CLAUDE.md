# [プロジェクト名] - プロジェクト固有ルール

> このファイルをプロジェクトフォルダの直下に「CLAUDE.md」として配置する。
> `.claude/CLAUDE.md`（共通ルール）に追加・上書きされる形で読み込まれる。
> 不要なセクションは削除してよい。共通ルールで十分なセクションは記載不要。

---

## Salesforce組織情報

| 環境 | org alias | 用途 |
|---|---|---|
| 開発 | `project-dev` | 開発・動作確認 |
| ステージング | `project-stg` | テスト・検証 |
| 本番 | `project-prod` | 本番（デプロイ時は必ず確認） |

デフォルトorg: `project-dev`

---

## 命名規則

| 対象 | ルール | 例 |
|---|---|---|
| カスタムオブジェクト | `PREFIX_` プレフィックス | `PROJ_Order__c` |
| カスタム項目 | `PREFIX_` プレフィックス | `PROJ_Status__c` |
| Apexクラス | `PREFIX` プレフィックス | `PROJOrderService` |
| LWCコンポーネント | camelCase | `projOrderList` |
| フロー | 種別_機能名 | `Screen_OrderCreate` |
| 権限セット | `PREFIX_` プレフィックス | `PROJ_SalesUser` |

---

## 権限設計ルール

- 標準プロファイルは編集禁止。権限セットで対応する
- （プロジェクト固有の権限ルールをここに記載）

---

## 主要カスタムオブジェクト

| オブジェクト名 | API名 | 概要 |
|---|---|---|
| | | |

---

## プロジェクト資材

| 資材 | 場所 | 生成コマンド | 備考 |
|---|---|---|---|
| 組織プロフィール・要件定義 | `docs/overview/` `docs/requirements/` | `/sf-memory` | 組織概要・用語集・AS-IS/TO-BE・要件一覧 |
| オブジェクト・項目定義書（Markdown） | `docs/catalog/` | `/sf-memory` | オブジェクト・項目構成・権限。Claude記憶形成用 |
| オブジェクト・項目定義書（Excel/PowerPoint） | `docs/` 任意 | `/sf-doc` | 正式な成果物として提出・共有するための定義書 |
| 機能設計書 | `docs/design/{種別}/` | `/sf-memory` | apex/flow/batch/lwc/integration/config |
| データ統計・マスタ | `docs/data/` | `/sf-memory` | マスタデータ・テンプレート・統計・品質 |
| 変更履歴 | `docs/logs/changelog.md` | 自動 | コマンド実行時に自動追記 |
| 対応履歴・判断記録 | `docs/decisions.md` | 自動 | 保守・開発の判断根拠。`/backlog` 完了時に自動追記 |
| package.xml | `manifest/package.xml` | `/sf-retrieve` | standard / all / 個別指定の3モード |

---

## 過去の判断・決定事項

<!-- 判明した設計判断・確定事項を手動で記載する -->
<!-- 例: 2026-04-01: 受注オブジェクトはOpportunityを流用することに決定 -->

---

## 注意事項・地雷

<!-- 触る前に知っておくべきこと、過去にハマったことを記載 -->
<!-- 例: 2026-04-01: AccountトリガーはXXXと競合するため、条件チェックが必要 -->

---

## プロジェクト固有の品質基準

<!-- 共通ルール（.claude/CLAUDE.md）を上書きしたい場合のみ記載 -->
<!-- 例: テストカバレッジ目標を95%以上とする -->
