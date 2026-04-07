#!/bin/bash
# =============================================================================
# setup-mcp.sh — .mcp.json の生成・更新
#
# /setup-mcp コマンドから呼ばれる。
#
# 使い方:
#   bash scripts/setup-mcp.sh                     # 対話モード
#   bash scripts/setup-mcp.sh github <token>       # GitHub のみ直接設定
#   bash scripts/setup-mcp.sh show                 # 現在の設定を表示
# =============================================================================
set -euo pipefail

MCP_FILE=".mcp.json"

# --- 色付き出力 ---
info()  { echo -e "\033[1;34m[INFO]\033[0m  $*"; }
ok()    { echo -e "\033[1;32m[OK]\033[0m    $*"; }
warn()  { echo -e "\033[1;33m[WARN]\033[0m  $*"; }
error() { echo -e "\033[1;31m[ERROR]\033[0m $*"; exit 1; }

# --- npx チェック ---
command -v npx >/dev/null 2>&1 || error "npx が見つかりません。Node.js をインストールしてください"

# --- 現在の設定を表示 ---
show_current() {
    if [ ! -f "$MCP_FILE" ]; then
        info ".mcp.json が存在しません"
        return 1
    fi
    echo ""
    echo "現在のMCP設定:"
    # mcpServers のキーを抽出して表示
    grep -oP '"(\w[\w-]*)":\s*\{' "$MCP_FILE" | head -20 | while read -r line; do
        name=$(echo "$line" | grep -oP '"\K[\w-]+')
        [ "$name" = "mcpServers" ] && continue
        echo "  - $name"
    done
    echo ""
    return 0
}

# --- JSON に MCP サーバーを追加する関数 ---
# 引数: サーバー名, JSON設定ブロック
add_server() {
    local name="$1"
    local config="$2"

    if [ ! -f "$MCP_FILE" ]; then
        # 新規作成
        cat > "$MCP_FILE" << EOF
{
  "mcpServers": {
    ${config}
  }
}
EOF
    else
        # 既存ファイルに追加（最後の } } の前に挿入）
        # sed で mcpServers の閉じ括弧の前に追加
        local tmp_file="${MCP_FILE}.tmp"
        # 簡易的に: 既存のmcpServersの最後のエントリの後にカンマと新エントリを追加
        python3 -c "
import json, sys
with open('$MCP_FILE', 'r') as f:
    data = json.load(f)
server_config = json.loads('{${config}}')
data.setdefault('mcpServers', {}).update(server_config)
with open('$MCP_FILE', 'w') as f:
    json.dump(data, f, indent=2)
" 2>/dev/null || {
            # python3 がなければ node で
            node -e "
const fs = require('fs');
const data = JSON.parse(fs.readFileSync('$MCP_FILE', 'utf8'));
const config = JSON.parse('{${config}}');
data.mcpServers = { ...data.mcpServers, ...config };
fs.writeFileSync('$MCP_FILE', JSON.stringify(data, null, 2));
" 2>/dev/null || {
                warn "JSON の自動マージに失敗しました。手動で $MCP_FILE を編集してください"
                return 1
            }
        }
    fi
    ok "$name を設定しました"
}

# --- GitHub 設定 ---
setup_github() {
    local token="$1"
    if [ -z "$token" ]; then
        echo ""
        echo "GitHub Personal Access Token を入力してください。"
        echo ""
        echo "取得方法:"
        echo "  1. GitHub > 右上のアイコン > Settings"
        echo "  2. 左メニュー最下部 Developer settings"
        echo "  3. Personal access tokens > Tokens (classic) > Generate new token"
        echo "  4. スコープ: repo, read:org にチェック"
        echo "  5. Generate token > トークンをコピー"
        echo ""
        read -sp "トークン: " token
        echo ""
    fi
    [ -z "$token" ] && error "トークンが入力されていません"

    local config="\"github\": {
      \"command\": \"npx\",
      \"args\": [\"-y\", \"@modelcontextprotocol/server-github\"],
      \"env\": {
        \"GITHUB_PERSONAL_ACCESS_TOKEN\": \"${token}\"
      }
    }"
    add_server "github" "$config"
}

# --- Slack 設定 ---
setup_slack() {
    echo ""
    read -sp "Slack Bot Token（xoxb- で始まるもの）: " token
    echo ""
    [ -z "$token" ] && error "トークンが入力されていません"

    local config="\"slack\": {
      \"command\": \"npx\",
      \"args\": [\"-y\", \"@anthropic/mcp-server-slack\"],
      \"env\": {
        \"SLACK_BOT_TOKEN\": \"${token}\"
      }
    }"
    add_server "slack" "$config"
}

# --- Notion 設定 ---
setup_notion() {
    echo ""
    read -sp "Notion Integration Token（ntn_ で始まるもの）: " token
    echo ""
    [ -z "$token" ] && error "トークンが入力されていません"

    local config="\"notion\": {
      \"command\": \"npx\",
      \"args\": [\"-y\", \"@notionhq/notion-mcp-server\"],
      \"env\": {
        \"OPENAPI_MCP_HEADERS\": \"{\\\\\"Authorization\\\\\": \\\\\"Bearer ${token}\\\\\", \\\\\"Notion-Version\\\\\": \\\\\"2022-06-28\\\\\"}\"
      }
    }"
    add_server "notion" "$config"
}

# --- Playwright 設定 ---
setup_playwright() {
    local config="\"playwright\": {
      \"command\": \"npx\",
      \"args\": [\"-y\", \"@anthropic/mcp-server-playwright\"]
    }"
    add_server "playwright" "$config"
}

# --- Backlog 設定 ---
setup_backlog() {
    echo ""
    read -p "Backlog ドメイン（例: yourcompany.backlog.com）: " domain
    [ -z "$domain" ] && error "ドメインが入力されていません"

    echo ""
    echo "APIキーの取得方法:"
    echo "  1. Backlog にログイン"
    echo "  2. 右上のアイコン > 個人設定"
    echo "  3. API タブ > APIキーを発行"
    echo ""
    read -sp "APIキー: " api_key
    echo ""
    [ -z "$api_key" ] && error "APIキーが入力されていません"

    local config="\"backlog\": {
      \"command\": \"npx\",
      \"args\": [\"-y\", \"backlog-mcp-server\"],
      \"env\": {
        \"BACKLOG_DOMAIN\": \"${domain}\",
        \"BACKLOG_API_KEY\": \"${api_key}\"
      }
    }"
    add_server "backlog" "$config"
}

# --- メイン ---
ACTION="${1:-}"
TOKEN="${2:-}"

case "$ACTION" in
    show)
        show_current
        exit 0
        ;;
    github)
        setup_github "$TOKEN"
        ;;
    slack)
        setup_slack
        ;;
    notion)
        setup_notion
        ;;
    playwright)
        setup_playwright
        ;;
    backlog)
        setup_backlog
        ;;
    *)
        # 対話モード
        show_current 2>/dev/null || true

        echo "セットアップするMCPを選択してください:"
        echo "  1. github     — PR・Issue管理（推奨）"
        echo "  2. slack      — Slackメッセージ送受信"
        echo "  3. notion     — Notionページ読み書き"
        echo "  4. playwright — ブラウザ操作"
        echo "  5. backlog    — Backlogチケット管理"
        echo "  6. 完了"
        echo ""

        while true; do
            read -p "番号または名前: " choice
            case "$choice" in
                1|github)     setup_github "" ;;
                2|slack)      setup_slack ;;
                3|notion)     setup_notion ;;
                4|playwright) setup_playwright ;;
                5|backlog)    setup_backlog ;;
                6|done|完了)  break ;;
                *)            warn "無効な選択です" ;;
            esac
            echo ""
            read -p "他にも追加しますか？ (y/N): " more
            [[ "$more" =~ ^[yY] ]] || break
        done
        ;;
esac

# --- 完了 ---
echo ""
show_current 2>/dev/null || true
echo "注意:"
echo "  - .mcp.json は .gitignore 対象のため Git には push されません"
echo "  - Claude Code を再起動すると設定が反映されます"
echo ""
