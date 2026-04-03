#!/bin/bash
# ============================================================
# Salesforce + Claude Code プロジェクトセットアップ
#
# 使い方:
#   bash setup.sh <プロジェクト名> [出力先]
#
# 例:
#   bash setup.sh myProject
#   bash setup.sh myProject C:/workspace/08_Myproject
#
# 動作:
#   1. sf project generate でSFDXプロジェクトを作成
#   2. Claude Codeテンプレート（.claude/ CLAUDE.md docs/）を自動配置
#   3. .gitignore を更新
# ============================================================

set -e

# --- テンプレートの場所（このスクリプト自身の隣） ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# --- 引数チェック ---
if [ -z "$1" ]; then
  echo ""
  echo "使い方: bash setup.sh <プロジェクト名> [出力先ディレクトリ]"
  echo ""
  echo "例:"
  echo "  bash setup.sh myProject"
  echo "  bash setup.sh myProject C:/workspace/08_Myproject"
  echo ""
  exit 1
fi

PROJECT_NAME="$1"
OUTPUT_DIR="${2:-.}"
PROJECT_PATH="$OUTPUT_DIR/$PROJECT_NAME"

# --- 既存チェック ---
if [ -d "$PROJECT_PATH" ]; then
  echo "エラー: $PROJECT_PATH は既に存在します"
  exit 1
fi

# --- Step 1: SFDXプロジェクト作成 ---
echo ""
echo "[1/3] SFDXプロジェクトを作成中..."
sf project generate -n "$PROJECT_NAME" -d "$OUTPUT_DIR" --manifest
echo "  完了: $PROJECT_PATH"

# --- Step 2: テンプレート配置 ---
echo ""
echo "[2/3] Claude Codeテンプレートを配置中..."

cp -r "$SCRIPT_DIR/.claude" "$PROJECT_PATH/.claude"
cp "$SCRIPT_DIR/CLAUDE.md" "$PROJECT_PATH/CLAUDE.md"
cp -r "$SCRIPT_DIR/docs" "$PROJECT_PATH/docs"
cp "$SCRIPT_DIR/.mcp.json.example" "$PROJECT_PATH/.mcp.json.example"
cp "$SCRIPT_DIR/upgrade.sh" "$PROJECT_PATH/upgrade.sh"

echo "  .claude/          → コピー完了"
echo "  CLAUDE.md         → コピー完了"
echo "  docs/             → コピー完了"
echo "  .mcp.json.example → コピー完了"
echo "  upgrade.sh        → コピー完了"

# --- Step 3: .gitignore 更新 ---
echo ""
echo "[3/3] .gitignore を更新中..."
if [ -f "$PROJECT_PATH/.gitignore" ]; then
  cat >> "$PROJECT_PATH/.gitignore" << 'GITIGNORE'

# Claude Code（個人設定）
.claude/settings.json
.mcp.json
GITIGNORE
  echo "  .gitignore に個人設定の除外を追記しました"
fi

# --- 完了 ---
echo ""
echo "==============================="
echo "  セットアップ完了"
echo "==============================="
echo ""
echo "プロジェクト: $PROJECT_PATH"
echo ""
echo "次のステップ:"
echo "  1. cd $PROJECT_PATH"
echo "  2. code ."
echo "  3. CLAUDE.md を開いてプロジェクト情報を記入"
echo "  4. sf org login web -a <エイリアス>"
echo "  5. Claude Codeで /setup-mcp を実行（MCP連携を使う場合）"
echo ""
