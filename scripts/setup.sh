#!/bin/bash
# =============================================================================
# setup.sh — SalesforceプロジェクトをSFDX + テンプレートで作成する
#
# 使い方（テンプレートを事前にダウンロードしなくても実行可能）:
#
#   # 新規プロジェクト（テンプレートから作成）
#   curl -sSL https://raw.githubusercontent.com/h-omata825/sf-claude-template/main/scripts/setup.sh | bash -s my-project
#   curl -sSL https://raw.githubusercontent.com/h-omata825/sf-claude-template/main/scripts/setup.sh | bash -s my-project /c/workspace
#
#   # GitHubリポジトリと連携する場合（第4引数にリポジトリURLを指定）
#   curl -sSL https://raw.githubusercontent.com/h-omata825/sf-claude-template/main/scripts/setup.sh | bash -s my-project /c/workspace "" https://github.com/your-org/project-a.git
#
# または clone 後:
#   bash scripts/setup.sh my-project /c/workspace
#   bash scripts/setup.sh my-project /c/workspace "" https://github.com/your-org/project-a.git
#
# 引数:
#   $1  プロジェクト名（必須）
#   $2  作成先パス（省略時: カレントディレクトリ）
#   $3  テンプレートURL（省略時: sf-claude-template のデフォルトブランチ）
#   $4  プロジェクトGitHubリポジトリURL（省略時: git連携はスキップ）
# =============================================================================
set -euo pipefail

# --- 設定 ---
DEFAULT_TEMPLATE_URL="https://github.com/h-omata825/sf-claude-template.git"
TEMPLATE_BRANCH="main"

# --- 色付き出力 ---
info()  { echo -e "\033[1;34m[INFO]\033[0m  $*"; }
ok()    { echo -e "\033[1;32m[OK]\033[0m    $*"; }
warn()  { echo -e "\033[1;33m[WARN]\033[0m  $*"; }
error() { echo -e "\033[1;31m[ERROR]\033[0m $*"; exit 1; }

# --- 引数 ---
PROJECT_NAME="${1:-}"
TARGET_DIR="${2:-.}"
TEMPLATE_URL="${3:-$DEFAULT_TEMPLATE_URL}"
GIT_REMOTE_URL="${4:-}"

if [ -z "$PROJECT_NAME" ]; then
    read -p "プロジェクト名を入力してください（英語）: " PROJECT_NAME
fi
[ -z "$PROJECT_NAME" ] && error "プロジェクト名が指定されていません"

PROJECT_PATH="$TARGET_DIR/$PROJECT_NAME"

# --- 前提チェック ---
command -v git >/dev/null 2>&1 || error "Git がインストールされていません"
command -v sf  >/dev/null 2>&1 || error "Salesforce CLI がインストールされていません。https://developer.salesforce.com/tools/salesforcecli からインストールしてください"

if [ -d "$PROJECT_PATH" ]; then
    error "$PROJECT_PATH は既に存在します"
fi

# --- SFDXプロジェクト作成 ---
info "SFDXプロジェクトを作成中..."
sf project generate -n "$PROJECT_NAME" -d "$TARGET_DIR" --manifest
ok "SFDXプロジェクト作成完了: $PROJECT_PATH"

# --- テンプレート取得 ---
info "テンプレートを取得中..."
TMP_DIR="$PROJECT_PATH/.claude-template-tmp"
if ! git clone --depth 1 --branch "$TEMPLATE_BRANCH" "$TEMPLATE_URL" "$TMP_DIR" 2>/dev/null; then
    error "テンプレートの取得に失敗しました。ネットワーク接続とリポジトリURLを確認してください"
fi

# --- テンプレートファイルを配置 ---
info "テンプレートを配置中..."
cp -r "$TMP_DIR/.claude" "$PROJECT_PATH/.claude"
cp "$TMP_DIR/CLAUDE.md" "$PROJECT_PATH/CLAUDE.md"
cp -r "$TMP_DIR/docs" "$PROJECT_PATH/docs"
[ -d "$TMP_DIR/scripts" ] && cp -r "$TMP_DIR/scripts" "$PROJECT_PATH/scripts"

# --- .gitignore 更新 ---
{
    echo ""
    echo "# Claude Code（トークン入り個人設定）"
    echo ".mcp.json"
} >> "$PROJECT_PATH/.gitignore"

# --- クリーンアップ ---
rm -rf "$TMP_DIR"

# --- Git 連携 ---
if [ -n "$GIT_REMOTE_URL" ]; then
    info "GitHubリポジトリと連携中..."
    cd "$PROJECT_PATH"
    git init
    git remote add origin "$GIT_REMOTE_URL"
    git add .
    git commit -m "chore: initial setup with sf-claude-template"
    git push -u origin main
    ok "GitHubリポジトリと連携完了: $GIT_REMOTE_URL"
    cd - > /dev/null
fi

# --- 完了 ---
echo ""
echo "=========================================="
echo "  セットアップ完了"
echo "=========================================="
echo ""
echo "  プロジェクト: $PROJECT_PATH"
if [ -n "$GIT_REMOTE_URL" ]; then
    echo "  Git: $GIT_REMOTE_URL"
fi
echo ""
echo "  次のステップ:"
if [ -z "$GIT_REMOTE_URL" ]; then
    echo "    0. （推奨）GitHubでリポジトリを作成して連携する:"
    echo "         cd $PROJECT_PATH"
    echo "         git init && git remote add origin <URL>"
    echo "         git add . && git commit -m 'chore: initial setup'"
    echo "         git push -u origin main"
    echo ""
fi
echo "    1. /sf-setup を実行（組織認証・メタデータ取得）"
echo "    2. CLAUDE.md を編集してプロジェクト固有情報を記入"
echo "    3. /setup-mcp を実行してGitHub連携を設定"
echo ""

# --- VSCode で開く ---
if command -v code >/dev/null 2>&1; then
    code "$PROJECT_PATH"
else
    info "VSCode CLI が見つかりません。手動で開いてください: $PROJECT_PATH"
fi
