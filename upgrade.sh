#!/bin/bash
# ============================================================
# テンプレートアップグレードスクリプト
#
# テンプレートリポジトリの最新版を取得し、プロジェクトの
# .claude/ 配下を更新する。プロジェクト固有ファイルは触らない。
#
# 使い方:
#   bash upgrade.sh [テンプレートURL] [タグ/ブランチ]
#
# 例:
#   bash upgrade.sh
#   bash upgrade.sh https://github.com/h-omata825/sf-claude-template.git
#   bash upgrade.sh https://github.com/h-omata825/sf-claude-template.git v1.1.0
#
# 動作:
#   1. テンプレートの最新版を一時フォルダに取得
#   2. .claude/ 配下を上書き（settings.json は除外）
#   3. 差分サマリを表示
#   4. 一時フォルダを削除
#
# 更新対象:
#   ✅ .claude/CLAUDE.md        — 共通ルール
#   ✅ .claude/agents/*.md      — エージェント定義
#   ✅ .claude/commands/*.md    — スラッシュコマンド定義
#   ✅ upgrade.sh               — このスクリプト自身
#
# 更新対象外（プロジェクト固有のため触らない）:
#   ❌ CLAUDE.md（ルート）      — プロジェクト固有ルール
#   ❌ .claude/settings.json    — 個人の権限設定
#   ❌ .mcp.json                — トークン入りの個人設定
#   ❌ docs/                    — プロジェクト資材
#   ❌ force-app/               — Salesforceメタデータ
# ============================================================

set -e

# --- 設定 ---
DEFAULT_TEMPLATE_URL="https://github.com/h-omata825/sf-claude-template.git"
TEMPLATE_URL="${1:-$DEFAULT_TEMPLATE_URL}"
TEMPLATE_REF="${2:-main}"
TMP_DIR=".claude-upgrade-tmp"

# --- カラー出力 ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# --- 前提チェック ---
if [ ! -d ".claude" ]; then
  error "このフォルダにはClaude Code設定（.claude/）が見つかりません。"
  error "プロジェクトのルートフォルダで実行してください。"
  exit 1
fi

if ! command -v git &> /dev/null; then
  error "Gitがインストールされていません。"
  exit 1
fi

# --- 一時フォルダが残っていたら削除 ---
if [ -d "$TMP_DIR" ]; then
  warn "前回の一時フォルダが残っています。削除します。"
  rm -rf "$TMP_DIR"
fi

# --- Step 1: テンプレート取得 ---
echo ""
echo "========================================"
echo "  テンプレートアップグレード"
echo "========================================"
echo ""
info "テンプレート: $TEMPLATE_URL"
info "ブランチ/タグ: $TEMPLATE_REF"
echo ""

info "[1/4] テンプレートを取得中..."
if ! git clone --depth 1 --branch "$TEMPLATE_REF" "$TEMPLATE_URL" "$TMP_DIR" 2>/dev/null; then
  error "テンプレートの取得に失敗しました。"
  error "URLを確認してください: $TEMPLATE_URL"
  error "ブランチ/タグを確認してください: $TEMPLATE_REF"
  exit 1
fi
info "  取得完了"

# --- テンプレートのバージョン表示（タグがあれば） ---
TEMPLATE_VERSION=$(cd "$TMP_DIR" && git describe --tags --exact-match 2>/dev/null || echo "(タグなし)")
info "  テンプレートバージョン: $TEMPLATE_VERSION"

# --- Step 2: 差分チェック ---
echo ""
info "[2/4] 差分を確認中..."

CHANGES=0
CHANGE_LOG=""

# .claude/CLAUDE.md
if [ -f "$TMP_DIR/.claude/CLAUDE.md" ]; then
  if ! diff -q ".claude/CLAUDE.md" "$TMP_DIR/.claude/CLAUDE.md" > /dev/null 2>&1; then
    CHANGE_LOG+="  更新: .claude/CLAUDE.md（共通ルール）\n"
    CHANGES=$((CHANGES + 1))
  fi
fi

# .claude/agents/
if [ -d "$TMP_DIR/.claude/agents" ]; then
  for f in "$TMP_DIR/.claude/agents/"*.md; do
    fname=$(basename "$f")
    if [ ! -f ".claude/agents/$fname" ]; then
      CHANGE_LOG+="  追加: .claude/agents/$fname（新規エージェント）\n"
      CHANGES=$((CHANGES + 1))
    elif ! diff -q ".claude/agents/$fname" "$f" > /dev/null 2>&1; then
      CHANGE_LOG+="  更新: .claude/agents/$fname\n"
      CHANGES=$((CHANGES + 1))
    fi
  done
  # 削除されたエージェントの検出
  for f in .claude/agents/*.md; do
    fname=$(basename "$f")
    if [ ! -f "$TMP_DIR/.claude/agents/$fname" ]; then
      CHANGE_LOG+="  削除対象: .claude/agents/$fname（テンプレートから削除済み）\n"
      CHANGES=$((CHANGES + 1))
    fi
  done
fi

# .claude/commands/
if [ -d "$TMP_DIR/.claude/commands" ]; then
  for f in "$TMP_DIR/.claude/commands/"*.md; do
    fname=$(basename "$f")
    if [ ! -f ".claude/commands/$fname" ]; then
      CHANGE_LOG+="  追加: .claude/commands/$fname（新規コマンド）\n"
      CHANGES=$((CHANGES + 1))
    elif ! diff -q ".claude/commands/$fname" "$f" > /dev/null 2>&1; then
      CHANGE_LOG+="  更新: .claude/commands/$fname\n"
      CHANGES=$((CHANGES + 1))
    fi
  done
  for f in .claude/commands/*.md; do
    fname=$(basename "$f")
    if [ ! -f "$TMP_DIR/.claude/commands/$fname" ]; then
      CHANGE_LOG+="  削除対象: .claude/commands/$fname（テンプレートから削除済み）\n"
      CHANGES=$((CHANGES + 1))
    fi
  done
fi

# upgrade.sh 自身
if [ -f "$TMP_DIR/upgrade.sh" ]; then
  if ! diff -q "upgrade.sh" "$TMP_DIR/upgrade.sh" > /dev/null 2>&1; then
    CHANGE_LOG+="  更新: upgrade.sh（アップグレードスクリプト自身）\n"
    CHANGES=$((CHANGES + 1))
  fi
fi

# --- 変更なしの場合 ---
if [ $CHANGES -eq 0 ]; then
  info "変更はありません。テンプレートは最新です。"
  rm -rf "$TMP_DIR"
  exit 0
fi

# --- 差分表示 ---
echo ""
echo -e "${YELLOW}--- 変更内容（${CHANGES}件） ---${NC}"
echo -e "$CHANGE_LOG"

# --- Step 3: 確認 ---
echo ""
info "[3/4] 上記の変更を適用しますか？"
echo ""
echo "  ※ .claude/settings.json、CLAUDE.md（ルート）、docs/ は変更されません"
echo ""
read -p "  適用する？ (y/n): " CONFIRM
echo ""

if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
  info "キャンセルしました。"
  rm -rf "$TMP_DIR"
  exit 0
fi

# --- Step 4: 適用 ---
info "[4/4] 変更を適用中..."

# .claude/CLAUDE.md
if [ -f "$TMP_DIR/.claude/CLAUDE.md" ]; then
  cp "$TMP_DIR/.claude/CLAUDE.md" ".claude/CLAUDE.md"
fi

# .claude/agents/
if [ -d "$TMP_DIR/.claude/agents" ]; then
  cp -r "$TMP_DIR/.claude/agents/"*.md ".claude/agents/"
fi

# .claude/commands/
if [ -d "$TMP_DIR/.claude/commands" ]; then
  cp -r "$TMP_DIR/.claude/commands/"*.md ".claude/commands/"
fi

# upgrade.sh
if [ -f "$TMP_DIR/upgrade.sh" ]; then
  cp "$TMP_DIR/upgrade.sh" "upgrade.sh"
fi

info "  適用完了"

# --- クリーンアップ ---
rm -rf "$TMP_DIR"

# --- 完了 ---
echo ""
echo "========================================"
echo "  アップグレード完了"
echo "========================================"
echo ""
echo "適用バージョン: $TEMPLATE_VERSION"
echo "変更件数: ${CHANGES}件"
echo ""
echo "次のステップ:"
echo "  1. 変更内容を確認:  git diff .claude/"
echo "  2. コミット:        git add .claude/ upgrade.sh"
echo "  3. プッシュ・PR:    git push → PRを作成してチームに共有"
echo ""
echo "※ settings.json に新しい設定が追加された場合は手動でマージしてください"
echo "   確認: diff .claude/settings.json $TMP_DIR/.claude/settings.json"
echo ""
