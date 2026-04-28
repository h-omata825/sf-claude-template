# Phase 1: 種別別 JSON 生成の注意点

## LWC（Lightning Web Component）

- `@api` プロパティ → `param_sections` の「入力プロパティ」セクション
- 発火するカスタムイベント（`dispatchEvent`） → `param_sections` の「出力イベント」セクション
- 画面項目（フォームフィールド・ボタン等） → `items`
- JS から呼び出す Apex メソッドごとにユースケースを作成 → `usecases`
- 子コンポーネント（`<c-xxx>`）を `prerequisites` に記載する
- 表示場所（Experience Cloud / 社内 / FlowScreen）を `transition` に記載する
- **吸収したモーダルがある場合**: モーダルの JS・HTML を読み、モーダルが開かれてから閉じるまでの操作フロー（開く → 確認画面表示 → ボタン押下 → 実行/キャンセル）を usecases の1エントリとして完全に展開して記述する。「モーダルを開く」1行で完結させない

---

## 画面フロー（Screen Flow）

- `<processType>Flow</processType>` かつ `<Screen>` ノードを含む場合のみ対象
- 各 `<screens>` ノードを `usecases` の1エントリとする（`<label>` がタイトル）
- `<screens>` 内の `<fields>` を `items` に記載する（FieldInputComponent → 入力、FieldOutputComponent → 表示専用）
- 入力変数（`variables` の `isInput: true`）・出力変数（`isOutput: true`）を `param_sections` に記載する

**画面フロー内のレコード操作・ロジックノードも必ず steps に含める（省略禁止）:**

| XML 要素 | node_type | 追加フィールド |
|---|---|---|
| `<recordLookups>` | process | object_ref + SOQL sub_step |
| `<recordUpdates>` / `<recordCreates>` / `<recordDeletes>` | process | object_ref + DML sub_step |
| `<decisions>` | decision | branch（条件式を detail に必ず記述） |
| `<actionCalls>` | process | calls（`<actionName>` = 呼び出す Apex クラス名） |
| `<subflows>` | process | calls（サブフローのAPI名） |

**XML ノードの具体的な読み方:**

`<recordLookups>` → SOQL sub_step:
- `<object>` → `object_ref.text`
- `<filters>` の `<field>` / `<operator>` / `<value>` → WHERE条件（全フィルターを列挙）
- `<queriedFields>` または `<outputReference>` → SELECT句
- SOQL sub_step detail 例: `"SELECT Id, Name, Memo__c\nFROM Account\nWHERE Id = {recordId}"`

`<recordUpdates>` / `<recordCreates>` → DML sub_step:
- `<object>` → `object_ref.text`
- `<inputAssignments>` の `<field>` / `<value>` → 更新フィールド（全件列挙）
- DML sub_step detail 例: `"対象: Account / 操作: UPDATE / フィールド: Memo__c={vMemo}, EditedDate__c={今日の日付}"`

`<decisions>` → decision step:
- `<rules>` の `<conditions>` を読んで条件式を日本語で detail に記述する
- `<leftValueReference>` / `<operator>` / `<rightValue>` から条件内容を読む
- **「条件分岐: [ラベル名]」だけでは禁止。必ず「何と何をどう比較しているか」を detail に書くこと**
- detail 例: `"保存ボタン押下後、入力値（vMemo）が null または空文字でないか判定"`
- `<defaultConnector>` → False側（`branch` に配置）、True側 → メインフロー続行

`<actionCalls>` → calls:
- `<actionName>` → `calls.text`（Apex の InvocableMethod クラス名）
- `<inputParameters>` → detail に渡す引数を記述
- detail 例: `"SendNotification Apex アクションを呼び出し、更新完了通知を送信する。引数: recordId, recipientId"`

---

## Aura（Lightning Aura Component）

- Controller.js のアクション（`({component, event, helper}) => {...}`）を `usecases` の1エントリとする
- `.cmp` マークアップの入力要素・ボタンを `items` に記載する
- `@AuraEnabled` Apex との連携は `usecases` 内の steps で `calls` に記述する
- `aura:attribute` の入力プロパティを `param_sections` に記載する
- `$A.get('e.*')` / `fire()` で発火するイベントを `param_sections` の出力セクションに記載する

---

## Visualforce（Visualforce Page）

- コントローラークラス（`controller="..."` 属性）を読んでアクションメソッドを特定する
- ページのアクション（`<apex:commandButton>` / `<apex:commandLink>` 等）を `usecases` の1エントリとする
- `<apex:inputField>` / `<apex:inputText>` 等の入力項目を `items` に記載する
- コントローラーの `@AuraEnabled` ではなく通常の public メソッドが対象
- 標準コントローラー使用時は `extensions` クラスを読む
- **コントローラーメソッドの steps 展開（必須）**: 各 usecase の steps はコントローラーの処理を読んで展開する。Apex と同じく Q1-Q5 決定木を全ステップに適用する
  - 他クラス・ユーティリティの呼び出し → `calls` で明示（図形が紫ボックスになる）
  - SOQL / DML → `object_ref` + sub_steps に詳細（図形がシリンダーになる）
  - 成否確認・条件分岐 → `decision` + `branch`（必ず処理ステップと分離する）
  - HTTP Callout がある場合 → `calls` で外部API名を明示
- **「図形なし」は設計ミス**: steps に `calls` / `object_ref` / `branch` が一切ない場合、コードを再読して外部呼び出しを探す
