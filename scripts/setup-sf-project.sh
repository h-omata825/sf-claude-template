#!/bin/bash
# =============================================================================
# setup-sf-project.sh — Salesforce組織の認証とメタデータ取得
#
# setup.sh でプロジェクト作成後、このスクリプトで組織接続を行う。
# /sf-setup コマンドから呼ばれる。
#
# 使い方:
#   bash scripts/setup-sf-project.sh                    # 対話モード
#   bash scripts/setup-sf-project.sh prod               # 本番認証（alias: prod）
#   bash scripts/setup-sf-project.sh dev                # Sandbox認証（alias: dev）
#   bash scripts/setup-sf-project.sh my-alias sandbox   # カスタムalias + Sandbox
# =============================================================================
set -euo pipefail

# --- 色付き出力 ---
info()  { echo -e "\033[1;34m[INFO]\033[0m  $*"; }
ok()    { echo -e "\033[1;32m[OK]\033[0m    $*"; }
warn()  { echo -e "\033[1;33m[WARN]\033[0m  $*"; }
error() { echo -e "\033[1;31m[ERROR]\033[0m $*"; exit 1; }

# --- 前提チェック ---
command -v sf >/dev/null 2>&1 || error "Salesforce CLI がインストールされていません"

if [ ! -f "sfdx-project.json" ]; then
    error "sfdx-project.json が見つかりません。SFDXプロジェクトのルートで実行してください"
fi

# --- 引数解析 ---
ALIAS="${1:-}"
ORG_TYPE="${2:-}"

# 対話モード
if [ -z "$ALIAS" ]; then
    echo ""
    echo "接続するSalesforce組織の種別を入力してください:"
    echo "  prod     — 本番/Developer Edition（login.salesforce.com）"
    echo "  dev      — Sandbox（test.salesforce.com）"
    echo "  skip     — 後で設定する"
    echo "  その他   — カスタムエイリアス（本番として認証）"
    echo ""
    read -p "種別: " ALIAS
fi

[ -z "$ALIAS" ] && error "組織種別が指定されていません"

# skip の場合
if [ "$ALIAS" = "skip" ]; then
    info "組織認証をスキップしました。後で再実行してください"
    exit 0
fi

# 種別に応じた設定
LOGIN_URL=""
case "$ALIAS" in
    prod)
        LOGIN_URL="https://login.salesforce.com"
        ;;
    dev)
        LOGIN_URL="https://test.salesforce.com"
        ;;
    *)
        # カスタムエイリアス
        if [ "$ORG_TYPE" = "sandbox" ]; then
            LOGIN_URL="https://test.salesforce.com"
        else
            LOGIN_URL="https://login.salesforce.com"
        fi
        ;;
esac

# --- 認証 ---
info "Salesforce組織に接続中... (alias: $ALIAS)"
echo "ブラウザが開きます。Salesforceにログインしてください。"
echo ""

if [ "$LOGIN_URL" = "https://test.salesforce.com" ]; then
    sf org login web -a "$ALIAS" -r "$LOGIN_URL"
else
    sf org login web -a "$ALIAS"
fi

# --- 認証確認 ---
if sf org display -o "$ALIAS" >/dev/null 2>&1; then
    ok "認証成功"
    sf config set target-org "$ALIAS" 2>/dev/null
    ok "デフォルト組織に設定: $ALIAS"
else
    error "認証に失敗しました。もう一度実行してください"
fi

# --- メタデータ取得の確認 ---
echo ""
read -p "組織のメタデータを取得しますか？ (y/N): " retrieve
if [[ ! "$retrieve" =~ ^[yY] ]]; then
    echo ""
    echo "セットアップ完了。メタデータ取得は後で /sf-retrieve で実行できます。"
    exit 0
fi

# --- APIバージョン取得 ---
API_VERSION=$(sf org display -o "$ALIAS" --json 2>/dev/null | grep -o '"apiVersion":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "62.0")
info "APIバージョン: $API_VERSION"

# --- docs/logs フォルダの作成 ---
mkdir -p docs/logs
info "docs/logs/ フォルダを作成しました"

# --- 標準セットの package.xml を生成 ---
mkdir -p manifest
cat > manifest/package.xml << XMLEOF
<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types><members>*</members><name>ApexClass</name></types>
    <types><members>*</members><name>ApexTrigger</name></types>
    <types><members>*</members><name>ApexPage</name></types>
    <types><members>*</members><name>Flow</name></types>
    <types><members>*</members><name>CustomObject</name></types>
    <types><members>*</members><name>CustomTab</name></types>
    <types><members>*</members><name>CustomLabel</name></types>
    <types><members>*</members><name>CustomMetadata</name></types>
    <types><members>*</members><name>LightningComponentBundle</name></types>
    <types><members>*</members><name>FlexiPage</name></types>
    <types><members>*</members><name>Layout</name></types>
    <types><members>*</members><name>PermissionSet</name></types>
    <types><members>*</members><name>PermissionSetGroup</name></types>
    <types><members>*</members><name>Profile</name></types>
    <types><members>*</members><name>StaticResource</name></types>
    <types><members>*</members><name>EmailTemplate</name></types>
    <version>${API_VERSION}</version>
</Package>
XMLEOF

info "package.xml を生成しました (manifest/package.xml)"

# --- メタデータ取得 ---
info "メタデータを取得中..."
sf project retrieve start --manifest manifest/package.xml --target-org "$ALIAS"
ok "メタデータ取得完了"

echo ""
echo "=========================================="
echo "  組織セットアップ完了"
echo "=========================================="
echo ""
echo "  組織: $ALIAS"
echo "  メタデータ: force-app/ に保存済み"
echo ""
echo "  次のステップ:"
echo "    1. CLAUDE.md を編集してプロジェクト固有情報を記入"
echo "    2. /setup-mcp でGitHub連携を設定"
echo "    3. /sf-memory で組織を解析して資料を自動生成"
echo ""
