---
description: "セッション開始時に実行する。Gitから最新版を取得し、テンプレートバージョンを確認する。"
---

## Step 1: 現在の状態確認

```bash
git branch --show-current
git status --short
```

未コミットの変更がある場合は一覧を表示して警告する。

## Step 2: 最新版取得

```bash
git pull origin $(git branch --show-current)
```

結果を表示する。「Already up to date.」なら最新と伝える。

## Step 3: テンプレートバージョン確認

```bash
cat .claude/VERSION 2>/dev/null || echo "不明"
```

表示するだけでよい。バージョンが古い可能性がある場合は `bash scripts/upgrade.sh` の実行を提案する。

## 完了報告

```
同期完了。

  ブランチ: <現在のブランチ名>
  状態: 最新 / X件の変更を取得
  テンプレート: v<バージョン>
```

未コミットの変更がある場合: `/git-pr` でブランチに保存してPRを作成できると案内する。
