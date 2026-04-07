#!/bin/bash
# =============================================================================
# upgrade.sh — テンプレートリポジトリから .claude/ 配下を更新する
#
# 使い方:
#   bash scripts/upgrade.sh                      # develop ブランチの最新版
#   bash scripts/upgrade.sh v1.2.0               # 指定タグ/ブランチ
#   bash scripts/upgrade.sh develop <URL>        # 別リポジトリ
# =============================================================================
set -euo pipefail

# --- 設定 ---
DEFAULT_URL="https://github.com/h-omata825/sf-claude-template.git"
DEFAULT_BRANCH="main"
VERSION_FILE=".claude/VERSION"
TMP_DIR=".claude-upgrade-tmp"

BRANCH="${1:-$DEFAULT_BRANCH}"
URL="${2:-$DEFAULT_URL}"

# --- 色付き出力 ---
info()  { echo -e "\033[1;34m[INFO]\033[0m  $*"; }
ok()    { echo -e "\033[1;32m[OK]\033[0m    $*"; }
warn()  { echo -e "\033[1;33m[WARN]\033[0m  $*"; }
error() { echo -e "\033[1;31m[ERROR]\033[0m $*"; exit 1; }

# --- 前提チェック ---
command -v git >/dev/null 2>&1 || error "Git がインストールされていません"
[ -d ".claude" ] || error ".claude/ が見つかりません。プロジェクトのルートで実行してください"

# --- 現在のバージョン取得 ---
CURRENT_VERSION="不明"
if [ -f "$VERSION_FILE" ]; then
    CURRENT_VERSION=$(cat "$VERSION_FILE" | tr -d '[:space:]')
fi
info "現在のバージョン: $CURRENT_VERSION"

# --- 一時フォルダのクリーンアップ ---
if [ -d "$TMP_DIR" ]; then
    warn "前回の一時フォルダが残っています。削除します"
    rm -rf "$TMP_DIR"
fi

# --- テンプレート取得 ---
info "テンプレートを取得中... (${URL} @ ${BRANCH})"
if ! git clone --depth 1 --branch "$BRANCH" "$URL" "$TMP_DIR" 2>/dev/null; then
    error "テンプレートの取得に失敗しました。URL とブランチ/タグを確認してください"
fi

# --- テンプレートのバージョン取得 ---
TEMPLATE_VERSION="不明"
if [ -f "$TMP_DIR/$VERSION_FILE" ]; then
    TEMPLATE_VERSION=$(cat "$TMP_DIR/$VERSION_FILE" | tr -d '[:space:]')
fi

# タグ情報も取得
TEMPLATE_TAG=$(cd "$TMP_DIR" && git describe --tags --exact-match 2>/dev/null || echo "タグなし")
info "テンプレートバージョン: $TEMPLATE_VERSION (${TEMPLATE_TAG})"

# --- 差分チェック ---
CHANGES=()
ADDITIONS=()
DELETIONS=()

# README.md
if [ -f "$TMP_DIR/README.md" ]; then
    if ! diff -q "README.md" "$TMP_DIR/README.md" >/dev/null 2>&1; then
        CHANGES+=("README.md（テンプレート説明）")
    fi
fi

# .claude/CLAUDE.md
if [ -f "$TMP_DIR/.claude/CLAUDE.md" ]; then
    if ! diff -q ".claude/CLAUDE.md" "$TMP_DIR/.claude/CLAUDE.md" >/dev/null 2>&1; then
        CHANGES+=(".claude/CLAUDE.md（共通ルール）")
    fi
fi

# .claude/settings.json
if [ -f "$TMP_DIR/.claude/settings.json" ]; then
    if ! diff -q ".claude/settings.json" "$TMP_DIR/.claude/settings.json" >/dev/null 2>&1; then
        CHANGES+=(".claude/settings.json（権限設定）")
    fi
fi

# .claude/VERSION
if [ -f "$TMP_DIR/$VERSION_FILE" ]; then
    if ! diff -q "$VERSION_FILE" "$TMP_DIR/$VERSION_FILE" >/dev/null 2>&1; then
        CHANGES+=("$VERSION_FILE")
    fi
fi

# エージェント
for f in "$TMP_DIR"/.claude/agents/*.md; do
    [ -f "$f" ] || continue
    name=$(basename "$f")
    if [ ! -f ".claude/agents/$name" ]; then
        ADDITIONS+=(".claude/agents/$name（新規エージェント）")
    elif ! diff -q ".claude/agents/$name" "$f" >/dev/null 2>&1; then
        CHANGES+=(".claude/agents/$name")
    fi
done
for f in .claude/agents/*.md; do
    [ -f "$f" ] || continue
    name=$(basename "$f")
    if [ ! -f "$TMP_DIR/.claude/agents/$name" ]; then
        DELETIONS+=(".claude/agents/$name（テンプレートから削除済み）")
    fi
done

# コマンド
for f in "$TMP_DIR"/.claude/commands/*.md; do
    [ -f "$f" ] || continue
    name=$(basename "$f")
    if [ ! -f ".claude/commands/$name" ]; then
        ADDITIONS+=(".claude/commands/$name（新規コマンド）")
    elif ! diff -q ".claude/commands/$name" "$f" >/dev/null 2>&1; then
        CHANGES+=(".claude/commands/$name")
    fi
done
for f in .claude/commands/*.md; do
    [ -f "$f" ] || continue
    name=$(basename "$f")
    if [ ! -f "$TMP_DIR/.claude/commands/$name" ]; then
        DELETIONS+=(".claude/commands/$name（テンプレートから削除済み）")
    fi
done

# スクリプト
if [ -d "$TMP_DIR/scripts" ]; then
    for f in "$TMP_DIR"/scripts/*; do
        [ -f "$f" ] || continue
        name=$(basename "$f")
        if [ ! -f "scripts/$name" ]; then
            ADDITIONS+=("scripts/$name（新規スクリプト）")
        elif ! diff -q "scripts/$name" "$f" >/dev/null 2>&1; then
            CHANGES+=("scripts/$name")
        fi
    done
fi

# --- 結果判定 ---
TOTAL=$(( ${#CHANGES[@]} + ${#ADDITIONS[@]} + ${#DELETIONS[@]} ))

if [ "$TOTAL" -eq 0 ]; then
    ok "テンプレートは最新です。変更はありません。"
    rm -rf "$TMP_DIR"
    exit 0
fi

# --- 変更内容の表示 ---
echo ""
echo "=========================================="
echo "  テンプレートに以下の変更があります"
echo "=========================================="
echo ""

for item in "${ADDITIONS[@]+"${ADDITIONS[@]}"}"; do
    echo -e "  \033[1;32m追加:\033[0m $item"
done
for item in "${CHANGES[@]+"${CHANGES[@]}"}"; do
    echo -e "  \033[1;33m更新:\033[0m $item"
done
for item in "${DELETIONS[@]+"${DELETIONS[@]}"}"; do
    echo -e "  \033[1;31m削除対象:\033[0m $item"
done

echo ""
echo "  合計: ${TOTAL}件の変更"
echo ""
echo "  ※ 以下は変更されません:"
echo "    - CLAUDE.md（プロジェクト固有ルール）"
echo "    - .mcp.json（個人設定）"
echo "    - docs/（プロジェクト資材）"
echo "    - force-app/（Salesforceメタデータ）"
echo ""

# --- 確認 ---
read -p "適用しますか？ (y/N): " confirm
if [[ ! "$confirm" =~ ^[yY] ]]; then
    info "キャンセルしました"
    rm -rf "$TMP_DIR"
    exit 0
fi

# --- 適用 ---
info "適用中..."

# README.md
[ -f "$TMP_DIR/README.md" ] && cp "$TMP_DIR/README.md" README.md

# 共通ルール
[ -f "$TMP_DIR/.claude/CLAUDE.md" ] && cp "$TMP_DIR/.claude/CLAUDE.md" .claude/CLAUDE.md

# settings.json
[ -f "$TMP_DIR/.claude/settings.json" ] && cp "$TMP_DIR/.claude/settings.json" .claude/settings.json

# VERSION
[ -f "$TMP_DIR/$VERSION_FILE" ] && cp "$TMP_DIR/$VERSION_FILE" "$VERSION_FILE"

# エージェント
for f in "$TMP_DIR"/.claude/agents/*.md; do
    [ -f "$f" ] || continue
    cp "$f" .claude/agents/
done

# コマンド
for f in "$TMP_DIR"/.claude/commands/*.md; do
    [ -f "$f" ] || continue
    cp "$f" .claude/commands/
done

# スクリプト
if [ -d "$TMP_DIR/scripts" ]; then
    mkdir -p scripts
    for f in "$TMP_DIR"/scripts/*; do
        [ -f "$f" ] || continue
        cp "$f" scripts/
    done
fi

# --- 削除対象の処理 ---
if [ ${#DELETIONS[@]} -gt 0 ]; then
    echo ""
    warn "以下のファイルはテンプレートから削除されています:"
    for item in "${DELETIONS[@]}"; do
        echo "    - $item"
    done
    read -p "プロジェクトからも削除しますか？ (y/N): " del_confirm
    if [[ "$del_confirm" =~ ^[yY] ]]; then
        for item in "${DELETIONS[@]}"; do
            filepath=$(echo "$item" | sed 's/（.*//') # 説明部分を除去
            if [ -f "$filepath" ]; then
                rm "$filepath"
                ok "削除: $filepath"
            fi
        done
    fi
fi

# --- クリーンアップ ---
rm -rf "$TMP_DIR"

# --- Git 自動コミット・プッシュ ---
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    COMMIT_MSG="chore: upgrade template to ${TEMPLATE_VERSION}"

    # 変更をステージング
    git add .claude/ scripts/ README.md 2>/dev/null || true

    # コミット（変更がある場合のみ）
    if ! git diff --cached --quiet; then
        CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

        # develop ブランチ以外の場合は develop に切り替え
        if [ "$CURRENT_BRANCH" != "develop" ]; then
            warn "現在のブランチ: ${CURRENT_BRANCH}。develop に切り替えてコミットします"
            git stash 2>/dev/null || true
            git checkout develop
            git add .claude/ scripts/ README.md 2>/dev/null || true
        fi

        git commit -m "$COMMIT_MSG"
        ok "コミット: $COMMIT_MSG"

        # develop へ push
        git push origin develop
        ok "push: origin/develop"

        # main へマージ・push
        git checkout main
        git merge develop --no-edit
        git push origin main
        ok "push: origin/main"

        # develop に戻る
        git checkout develop
    else
        info "Git: コミット対象の変更なし（スキップ）"
    fi
else
    info "Git リポジトリ未設定。Git 操作はスキップしました"
fi

# --- 完了報告 ---
echo ""
echo "=========================================="
echo "  アップグレード完了"
echo "=========================================="
echo ""
echo "  バージョン: $CURRENT_VERSION → $TEMPLATE_VERSION"
echo "  ソース: $URL @ $BRANCH"
echo "  変更件数: ${TOTAL}件"
echo ""
