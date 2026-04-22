#!/bin/bash
# =============================================================================
# setup.sh — SalesforceプロジェクトをSFDX + テンプレートで作成する
#
# 使い方（テンプレートを事前にダウンロードしなくても実行可能）:
#
#   # 新規プロジェクト（sf-claude-template から作成）
#   curl -sSL https://raw.githubusercontent.com/h-omata825/sf-claude-template/main/scripts/setup.sh | bash -s my-project
#   curl -sSL https://raw.githubusercontent.com/h-omata825/sf-claude-template/main/scripts/setup.sh | bash -s my-project /c/workspace
#
#   # 既存プロジェクトに参加（プロジェクトリポジトリをソースに指定 → Git連携も自動設定）
#   curl -sSL https://raw.githubusercontent.com/h-omata825/sf-claude-template/main/scripts/setup.sh | bash -s my-project /c/workspace https://github.com/your-org/project-a.git
#
# または clone 後:
#   bash scripts/setup.sh my-project /c/workspace
#   bash scripts/setup.sh my-project /c/workspace https://github.com/your-org/project-a.git
#
# 引数:
#   $1  プロジェクト名（必須）
#   $2  作成先パス（省略時: カレントディレクトリ）
#   $3  プロジェクトリポジトリURL（省略時: sf-claude-template から作成、Git連携はスキップ）
#       ※ 指定した場合はそのリポジトリをソースとし、Git remote も自動設定する
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
PROJECT_REPO_URL="${3:-}"  # 指定時: ソース兼Git remote。省略時: sf-claude-template から作成

# $3 が指定された場合はそこをソースに、なければデフォルトテンプレートを使用
TEMPLATE_URL="${PROJECT_REPO_URL:-$DEFAULT_TEMPLATE_URL}"

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
if [ -d "$TMP_DIR/scripts" ]; then
    mkdir -p "$PROJECT_PATH/scripts"
    cp -r "$TMP_DIR/scripts/." "$PROJECT_PATH/scripts/"
fi

# --- .gitignore 更新 ---
{
    echo ""
    echo "# Claude Code（トークン入り個人設定）"
    echo ".mcp.json"
} >> "$PROJECT_PATH/.gitignore"

# --- クリーンアップ ---
rm -rf "$TMP_DIR"

# --- Git 連携（$3 指定時のみ） ---
if [ -n "$PROJECT_REPO_URL" ]; then
    info "GitHubリポジトリと連携中..."
    cd "$PROJECT_PATH"
    git init
    git remote add origin "$PROJECT_REPO_URL"
    git add .
    git commit -m "chore: initial setup with sf-claude-template"
    git push -u origin main
    ok "GitHubリポジトリと連携完了: $PROJECT_REPO_URL"
    cd - > /dev/null
fi

# --- 完了 ---
echo ""
echo "=========================================="
echo "  セットアップ完了"
echo "=========================================="
echo ""
echo "  プロジェクト: $PROJECT_PATH"
if [ -n "$PROJECT_REPO_URL" ]; then
    echo "  Git: $PROJECT_REPO_URL"
fi
echo ""
echo "  次のステップ:"
# docs/ に .md ファイルがあるかで初期セットアップ／メンバーセットアップを判定
DOC_COUNT=$(find "$PROJECT_PATH/docs" -name "*.md" -type f 2>/dev/null | wc -l)

if [ "$DOC_COUNT" -gt 0 ]; then
    # --- メンバーセットアップ（プロジェクトテンプレートから作成）---
    echo "    組織情報・設計書はプロジェクトテンプレートに含まれています。"
    echo ""
    echo "    1. /sf-setup   — Sandbox組織を認証する"
    echo "    2. CLAUDE.md   — 担当者名・Sandbox alias 等を記入する"
    echo "    3. /setup-mcp  — 外部ツール連携を設定する（任意: Backlog・Notion・GitHub 等）"
else
    # --- 初期セットアップ（テンプレートから新規作成）---
    if [ -z "$PROJECT_REPO_URL" ]; then
        echo "    0. GitHubでリポジトリを作成して連携する:"
        echo "         cd $PROJECT_PATH"
        echo "         git init && git remote add origin <URL>"
        echo "         git add . && git commit -m 'chore: initial setup'"
        echo "         git push -u origin main"
        echo ""
    fi
    echo "    1. /sf-setup    — 本番組織を認証する ★記憶形成は本番接続を推奨"
    echo "    2. /sf-retrieve — メタデータを取得する（force-app/ に展開）"
    echo "    3. /sf-memory   — 組織情報を収集しドキュメントを生成する（docs/ に出力）"
    echo "    4. /sf-doc      — 設計書・定義書を生成する"
    echo "    5. CLAUDE.md    — プロジェクト固有情報を記入する"
    echo "    6. /setup-mcp   — 外部ツール連携を設定する（任意）"
    echo ""
    echo "    ※ 初期セットアップ完了後、プロジェクトリポジトリをチームメンバーに配布してください"
fi
echo ""

# --- VSCode で開く ---
if command -v code >/dev/null 2>&1; then
    code "$PROJECT_PATH"
    # Windows の場合、起動直後に最大化する（画面サイズに合わせる）
    if [[ "${OSTYPE:-}" == "msys"* ]] || [[ "${OSTYPE:-}" == "cygwin"* ]] || [[ -n "${WINDIR:-}" ]]; then
        PROJECT_BASENAME=$(basename "$PROJECT_PATH")
        powershell.exe -NoProfile -Command "
            Start-Sleep -Seconds 3
            Add-Type -TypeDefinition '
                using System;
                using System.Runtime.InteropServices;
                public class WindowHelper {
                    [DllImport(\"user32.dll\")] public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow);
                }
            ' -ErrorAction SilentlyContinue
            \$procs = Get-Process 'Code' -ErrorAction SilentlyContinue | Where-Object { \$_.MainWindowTitle -like '*${PROJECT_BASENAME}*' } | Sort-Object StartTime -Descending
            if (\$procs) { [WindowHelper]::ShowWindowAsync(\$procs[0].MainWindowHandle, 3) | Out-Null }
        " 2>/dev/null &
    fi
else
    info "VSCode CLI が見つかりません。手動で開いてください: $PROJECT_PATH"
fi
