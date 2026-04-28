# LWC（Lightning Web Components）

## 作成時の確認

1. **配置場所**: レコードページ / アプリページ / ホームページ / フロー画面 / Experience Cloud / 他コンポーネントから呼び出し。配置場所によって `targets` と `targetConfigs` が変わる
2. 既存の類似コンポーネントが `force-app/` にないか確認してから作成

## データアクセスの選定

| 用途 | 推奨手段 |
|---|---|
| レコードの参照・更新 | `@wire(getRecord)` / Lightning Data Service（キャッシュ効く） |
| 関連レコード一覧・複雑な条件 | `@wire` でApexメソッドを呼ぶ |
| ユーザー操作起点の処理（ボタン押下等） | `@AuraEnabled` Apexを imperative call |

`@wire` を優先する理由（キャッシュ・自動再取得・ガバナ制限の節約）を説明した上で用途に応じて選定する。

## コーディング規約

- **ローディング・エラー状態を必ずハンドリング**: `isLoading` フラグ・`error` 変数をテンプレートに反映
- **SLDSを使用**: `slds-` クラスを使い、独自CSSはレイアウト調整の最小限に留める
- **イベント設計**: 親子間は `CustomEvent`。兄弟コンポーネント間は LMS（Lightning Message Service）または共通の親経由
- `connectedCallback` でリスナー登録した場合は `disconnectedCallback` で必ず解除
- `@api` は外部公開プロパティのみ。内部状態は `@track` 不要（プリミティブ以外はデフォルトでリアクティブ）

## Apex連携時

- `@AuraEnabled(cacheable=true)` はデータ取得専用。DMLを含む処理には付けない
- エラーは `AuraHandledException` を使って意味のあるメッセージをフロントに返す
- Apexの戻り値の型をJS側で扱いやすい形に設計する（ラッパークラスの活用を提案）

## 変更時の影響調査

- 同じコンポーネントを使っている他のページ・コンポーネントを調査（Glob: `*.html` 内のコンポーネントタグ参照）
- `@api` プロパティの変更・削除は呼び出し元全てに影響することを警告
- Lightning App Builder に配置済みの場合、デプロイ後に実機での動作確認が必要

## テスト（Jest）

- ユニットテストは `__tests__` フォルダに配置
- `@wire` のモックは `@salesforce/wire-service-jest-util` を使用
- プロジェクトでJestが導入済みかを確認してから提供する（未導入なら `@salesforce/sfdx-lwc-jest` の設定手順も案内）
