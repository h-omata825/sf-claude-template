# /git-pr — ブランチ作成・コミット・プッシュ・PR作成

変更内容をブランチにコミット・プッシュし、`develop` へのプルリクエストを作成する対話型フロー。

---

## Step 1: 変更確認

`git status` と `git diff --stat` を実行し、変更内容をユーザーに提示する。

変更がなければ「コミットする変更がありません」と伝えて終了する。

---

## Step 2: ブランチ選択

以下を実行して現状を把握する:

```bash
git branch --show-current
git branch -a
```

ユーザーに以下の選択肢を **番号付きリスト** で提示する:

**【新規ブランチ】（3案）**
- `feature/NNN` の連番で提案（既存 `feature/NNN` の最大番号 + 1, +2, +3）
- NNNは3桁ゼロ埋め（例: `001`, `002`）
- 変更内容から推測した説明サフィックスを付ける（例: `feature/003-claude-md-update`）

**【既存ブランチ】**
- `feature/*` など既存ブランチを番号付きで表示（最大10件）

**【カスタム】**
- 自由にブランチ名を入力

ユーザーの選択に従い、ブランチを作成または切り替える:
- 新規: `git checkout -b <ブランチ名>`
- 既存（ローカル）: `git checkout <ブランチ名>`
- 既存（リモートのみ）: `git checkout -b <ブランチ名> origin/<ブランチ名>`

---

## Step 3: コミットするファイルの選択

変更ファイルを番号付きで一覧表示し、ユーザーに確認する:

```
変更ファイル:
  1. CLAUDE.md
  2. docs/requirements/requirements.md
  3. docs/catalog/account.md

  a. すべてをコミット
  番号指定（例: 1,3）で個別選択
```

ユーザーの選択に従い `git add` を実行する。

---

## Step 4: コミットメッセージ

変更内容からコミットメッセージを提案する（Conventional Commits形式推奨）:

```
例: docs: CLAUDE.md に命名規則を追加
例: feat: Account オブジェクト定義書を作成
```

ユーザーに確認・修正してもらい、`git commit -m "メッセージ"` を実行する。

---

## Step 5: プッシュ

```bash
git push -u origin <ブランチ名>
```

---

## Step 6: PR作成

まず `gh` CLI の有無を確認する:

```bash
command -v gh
```

**gh がある場合:**

ターゲットブランチを確認する（`develop` が存在すれば `develop`、なければ `main`）。

既存PRの重複チェック:
```bash
gh pr list --head <ブランチ名>
```

PRタイトルと本文をユーザーに確認してから作成:
- タイトル: 変更内容から提案（空白ならコミットメッセージを使用）
- 本文: 変更ファイルと変更概要を自動生成してユーザーに確認

```bash
gh pr create --title "<タイトル>" --body "<本文>" --base <ターゲット> --head <ブランチ名>
```

**gh がない場合:**

GitHubのPR作成URLを案内する:
```
https://github.com/<owner>/<repo>/compare/<ターゲット>...<ブランチ名>
```

---

## 完了後

PR作成後、PRのURLをユーザーに伝える。
