#!/bin/bash
# =============================================================================
# sf-retrieve.sh — package.xml の生成とメタデータ取得
#
# /sf-retrieve コマンドの定型部分（package.xml生成・retrieve実行）をスクリプト化。
# 取得対象の判断（指定/標準セット/全て）は /sf-retrieve コマンド側（Claude）が行い、
# このスクリプトに mode を渡す。
#
# 使い方:
#   bash scripts/sf-retrieve.sh standard             # 標準セットで生成＋取得
#   bash scripts/sf-retrieve.sh all                   # 全量で生成＋取得
#   bash scripts/sf-retrieve.sh generate-only standard # 生成のみ（取得しない）
#   bash scripts/sf-retrieve.sh retrieve              # 既存 package.xml で取得のみ
# =============================================================================
set -euo pipefail

# --- 色付き出力 ---
info()  { echo -e "\033[1;34m[INFO]\033[0m  $*"; }
ok()    { echo -e "\033[1;32m[OK]\033[0m    $*"; }
warn()  { echo -e "\033[1;33m[WARN]\033[0m  $*"; }
error() { echo -e "\033[1;31m[ERROR]\033[0m $*"; exit 1; }

# --- 前提チェック ---
command -v sf >/dev/null 2>&1 || error "Salesforce CLI がインストールされていません"
[ -f "sfdx-project.json" ] || error "sfdx-project.json が見つかりません。SFDXプロジェクトのルートで実行してください"

# --- APIバージョン取得 ---
get_api_version() {
    # sfdx-project.json から取得を試みる
    local version
    version=$(grep -oP '"sourceApiVersion"\s*:\s*"\K[^"]+' sfdx-project.json 2>/dev/null || echo "")
    if [ -z "$version" ]; then
        version="62.0"
    fi
    echo "$version"
}

# --- 標準セットの package.xml 生成 ---
generate_standard() {
    local api_version="$1"
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
    <types><members>*</members><name>CustomSetting</name></types>
    <types><members>*</members><name>LightningComponentBundle</name></types>
    <types><members>*</members><name>FlexiPage</name></types>
    <types><members>*</members><name>Layout</name></types>
    <types><members>*</members><name>PermissionSet</name></types>
    <types><members>*</members><name>PermissionSetGroup</name></types>
    <types><members>*</members><name>Profile</name></types>
    <types><members>*</members><name>StaticResource</name></types>
    <types><members>*</members><name>EmailTemplate</name></types>
    <types><members>*</members><name>ReportType</name></types>
    <types><members>*</members><name>Report</name></types>
    <types><members>*</members><name>Dashboard</name></types>
    <types><members>*</members><name>NamedCredential</name></types>
    <types><members>*</members><name>RemoteSiteSetting</name></types>
    <types><members>*</members><name>ValidationRule</name></types>
    <version>${api_version}</version>
</Package>
XMLEOF
    ok "標準セットの package.xml を生成: manifest/package.xml (API ${api_version})"
}

# --- 全量の package.xml 生成 ---
generate_all() {
    local api_version="$1"
    info "組織のメタデータタイプを取得中..."

    local types_json
    types_json=$(sf org list metadata-types --json 2>/dev/null) || error "メタデータタイプの取得に失敗しました。組織に接続されているか確認してください"

    # メタデータタイプ名を抽出して package.xml を生成
    mkdir -p manifest

    # ヘッダー
    echo '<?xml version="1.0" encoding="UTF-8"?>' > manifest/package.xml
    echo '<Package xmlns="http://soap.sforce.com/2006/04/metadata">' >> manifest/package.xml

    # 各タイプを追加
    echo "$types_json" | grep -oP '"xmlName"\s*:\s*"\K[^"]+' | sort | while read -r type_name; do
        echo "    <types><members>*</members><name>${type_name}</name></types>" >> manifest/package.xml
    done

    # フッター
    echo "    <version>${api_version}</version>" >> manifest/package.xml
    echo '</Package>' >> manifest/package.xml

    local count
    count=$(echo "$types_json" | grep -c '"xmlName"' 2>/dev/null || echo "?")
    ok "全量の package.xml を生成: manifest/package.xml (${count}タイプ, API ${api_version})"
}

# --- メタデータ取得 ---
retrieve() {
    [ -f "manifest/package.xml" ] || error "manifest/package.xml が見つかりません。先に生成してください"

    # 接続中の組織を確認（意図しない組織からの取得を防ぐ）
    local target_org
    target_org=$(sf config get target-org --json 2>/dev/null | grep -oP '"value"\s*:\s*"\K[^"]+' | head -1 || echo "")
    if [ -z "$target_org" ]; then
        error "target-org が設定されていません。sf config set target-org <alias> で設定してください"
    fi
    info "接続中の組織: ${target_org}"

    # 未コミットの変更を確認
    if command -v git >/dev/null 2>&1 && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        local changes
        changes=$(git status --porcelain force-app/ 2>/dev/null | head -5)
        if [ -n "$changes" ]; then
            warn "force-app/ に未コミットの変更があります:"
            echo "$changes"
            echo ""
            read -p "上書きして続行しますか？ (y/N): " confirm
            [[ "$confirm" =~ ^[yY] ]] || { info "キャンセルしました"; exit 0; }
        fi
    fi

    info "メタデータを取得中..."
    sf project retrieve start --manifest manifest/package.xml --target-org "$target_org"
    ok "メタデータ取得完了 → force-app/"
}

# --- メイン ---
MODE="${1:-standard}"

API_VERSION=$(get_api_version)

case "$MODE" in
    standard)
        generate_standard "$API_VERSION"
        retrieve
        ;;
    all)
        generate_all "$API_VERSION"
        retrieve
        ;;
    generate-only)
        SUBMODE="${2:-standard}"
        case "$SUBMODE" in
            standard) generate_standard "$API_VERSION" ;;
            all)      generate_all "$API_VERSION" ;;
            *)        error "不明なモード: $SUBMODE (standard / all)" ;;
        esac
        ;;
    retrieve)
        retrieve
        ;;
    *)
        echo "使い方: bash scripts/sf-retrieve.sh <mode>"
        echo ""
        echo "  standard        標準セットで package.xml 生成 + 取得"
        echo "  all             全量で package.xml 生成 + 取得"
        echo "  generate-only   package.xml 生成のみ（standard / all）"
        echo "  retrieve        既存 package.xml で取得のみ"
        exit 1
        ;;
esac

echo ""
echo "次のステップ:"
echo "  変更確認: git diff force-app/"
echo ""
