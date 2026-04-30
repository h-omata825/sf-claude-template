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
command -v python3 >/dev/null 2>&1 || error "python3 がインストールされていません"

# --- APIバージョン取得 ---
get_api_version() {
    local version
    version=$(grep -oP '"sourceApiVersion"\s*:\s*"\K[^"]+' sfdx-project.json 2>/dev/null || echo "")
    if [ -z "$version" ]; then
        version="62.0"
    fi
    echo "$version"
}

# --- 標準セット package.xml 生成 ---
#
# Entity expansion limit (1000) 対策:
#   manifest/package.xml               ... 軽い type まとめ（wildcard）
#   manifest/package-{TYPE}.xml        ... 重い type 独立（ApexClass/Layout/Profile/FlexiPage）
#   manifest/package-CustomObject-N.xml ... CustomObject を 100 件ずつ分割（動的生成）
generate_standard() {
    local api_version="$1"
    local target_org="$2"
    mkdir -p manifest

    # 軽い type まとめ（wildcard）
    cat > manifest/package.xml << XMLEOF
<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types><members>*</members><name>ApexTrigger</name></types>
    <types><members>*</members><name>ApexPage</name></types>
    <types><members>*</members><name>Flow</name></types>
    <types><members>*</members><name>CustomTab</name></types>
    <types><members>*</members><name>CustomLabel</name></types>
    <types><members>*</members><name>CustomMetadata</name></types>
    <types><members>*</members><name>LightningComponentBundle</name></types>
    <types><members>*</members><name>PermissionSet</name></types>
    <types><members>*</members><name>PermissionSetGroup</name></types>
    <types><members>*</members><name>StaticResource</name></types>
    <types><members>*</members><name>EmailTemplate</name></types>
    <types><members>*</members><name>ReportType</name></types>
    <types><members>*</members><name>NamedCredential</name></types>
    <types><members>*</members><name>RemoteSiteSetting</name></types>
    <types><members>*</members><name>ValidationRule</name></types>
    <version>${api_version}</version>
</Package>
XMLEOF

    # 重い type は独立バッチ（wildcard）
    for TYPE in ApexClass Layout Profile FlexiPage; do
        cat > "manifest/package-${TYPE}.xml" << XMLEOF
<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types><members>*</members><name>${TYPE}</name></types>
    <version>${api_version}</version>
</Package>
XMLEOF
    done

    # CustomObject は件数が多いため 100 件ずつ分割して生成
    info "CustomObject 一覧を取得中（${target_org}）..."
    local objects_json
    objects_json=$(sf org list metadata --metadata-type CustomObject --target-org "$target_org" --json 2>/dev/null) || {
        warn "CustomObject 一覧の取得に失敗しました。manifest/package-CustomObject-1.xml に wildcard を使用します"
        cat > "manifest/package-CustomObject-1.xml" << XMLEOF
<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types><members>*</members><name>CustomObject</name></types>
    <version>${api_version}</version>
</Package>
XMLEOF
        return
    }

    local n_batches
    n_batches=$(python3 - "${api_version}" << PYEOF
import json, math, sys

api_version = sys.argv[1]
data = json.loads("""${objects_json}""")
objects = sorted([r['fullName'] for r in data.get('result', [])])

BATCH_SIZE = 100
n_batches = math.ceil(len(objects) / BATCH_SIZE)

for i in range(n_batches):
    batch = objects[i*BATCH_SIZE:(i+1)*BATCH_SIZE]
    members = '\n'.join([f'        <members>{o}</members>' for o in batch])
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
{members}
        <name>CustomObject</name>
    </types>
    <version>{api_version}</version>
</Package>"""
    fname = f"manifest/package-CustomObject-{i+1}.xml"
    with open(fname, 'w', encoding='utf-8') as f:
        f.write(xml)

print(n_batches)
PYEOF
)

    ok "標準セット package.xml を生成 (API ${api_version})"
    ok "  軽い type: manifest/package.xml"
    ok "  重い type: manifest/package-{ApexClass,Layout,Profile,FlexiPage}.xml"
    ok "  CustomObject: manifest/package-CustomObject-1.xml 〜 ${n_batches}.xml (${n_batches} バッチ)"
}

# --- 全量の package.xml 生成 ---
generate_all() {
    local api_version="$1"
    info "組織のメタデータタイプを取得中..."

    local types_json
    types_json=$(sf org list metadata-types --json 2>/dev/null) || error "メタデータタイプの取得に失敗しました。組織に接続されているか確認してください"

    mkdir -p manifest

    echo '<?xml version="1.0" encoding="UTF-8"?>' > manifest/package.xml
    echo '<Package xmlns="http://soap.sforce.com/2006/04/metadata">' >> manifest/package.xml

    echo "$types_json" | grep -oP '"xmlName"\s*:\s*"\K[^"]+' | sort | while read -r type_name; do
        echo "    <types><members>*</members><name>${type_name}</name></types>" >> manifest/package.xml
    done

    echo "    <version>${api_version}</version>" >> manifest/package.xml
    echo '</Package>' >> manifest/package.xml

    local count
    count=$(echo "$types_json" | grep -c '"xmlName"' 2>/dev/null || echo "?")
    ok "全量の package.xml を生成: manifest/package.xml (${count}タイプ, API ${api_version})"
}

# --- 接続組織の確認 ---
get_target_org() {
    local target_org
    target_org=$(sf config get target-org --json 2>/dev/null | grep -oP '"value"\s*:\s*"\K[^"]+' | head -1 || echo "")
    if [ -z "$target_org" ]; then
        error "target-org が設定されていません。sf config set target-org <alias> で設定してください"
    fi
    echo "$target_org"
}

# --- 未コミット変更の確認 ---
check_uncommitted() {
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
}

# --- 単一バッチ取得（失敗時に CustomObject バッチは 1 件ずつリトライ）---
retrieve_manifest() {
    local manifest="$1"
    local target_org="$2"
    local label="$3"

    if sf project retrieve start --manifest "$manifest" --target-org "$target_org" 2>&1; then
        return 0
    fi

    # CustomObject バッチが Entity expansion で失敗した場合: 1 件ずつリトライ
    if [[ "$manifest" == *"CustomObject"* ]]; then
        warn "[${label}] Entity expansion 超過。オブジェクトを 1 件ずつ取得します..."
        local skipped=()
        while IFS= read -r obj; do
            cat > /tmp/sf-retrieve-single.xml << XMLEOF
<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types><members>${obj}</members><name>CustomObject</name></types>
    <version>$(get_api_version)</version>
</Package>
XMLEOF
            if ! sf project retrieve start --manifest /tmp/sf-retrieve-single.xml --target-org "$target_org" 2>&1; then
                warn "  スキップ: ${obj}（Entity expansion 超過 — フィールド数が多すぎます）"
                skipped+=("$obj")
            fi
        done < <(grep -oP '(?<=<members>)[^<]+' "$manifest")

        if [ ${#skipped[@]} -gt 0 ]; then
            warn "[${label}] 以下のオブジェクトはスキップしました（手動取得が必要です）:"
            for s in "${skipped[@]}"; do warn "  - ${s}"; done
        fi
        return 0
    fi

    # その他の type は失敗をそのまま上位に伝播
    return 1
}

# --- 標準取得（複数バッチ）---
retrieve_standard() {
    local target_org="$1"
    info "接続中の組織: ${target_org}"
    check_uncommitted

    local batch=0
    local manifests=()

    # 軽い type まとめ
    manifests+=("manifest/package.xml")
    # 重い type 独立
    for TYPE in ApexClass Layout Profile FlexiPage; do
        manifests+=("manifest/package-${TYPE}.xml")
    done
    # CustomObject 分割バッチ
    for f in manifest/package-CustomObject-*.xml; do
        [ -f "$f" ] && manifests+=("$f")
    done

    local total=${#manifests[@]}

    for manifest in "${manifests[@]}"; do
        batch=$((batch + 1))
        local label
        label=$(basename "$manifest" .xml | sed 's/package-//')
        info "[バッチ${batch}/${total}] ${label} を取得中..."
        retrieve_manifest "$manifest" "$target_org" "$label"
        ok "[バッチ${batch}/${total}] 完了"
    done

    ok "メタデータ取得完了 → force-app/ （計 ${total} バッチ）"
}

# --- 単一 package.xml 取得 ---
retrieve() {
    [ -f "manifest/package.xml" ] || error "manifest/package.xml が見つかりません。先に生成してください"

    local target_org
    target_org=$(get_target_org)
    info "接続中の組織: ${target_org}"
    check_uncommitted

    info "メタデータを取得中..."
    sf project retrieve start --manifest manifest/package.xml --target-org "$target_org"
    ok "メタデータ取得完了 → force-app/"
}

# --- メイン ---
MODE="${1:-standard}"
API_VERSION=$(get_api_version)

case "$MODE" in
    standard)
        TARGET_ORG=$(get_target_org)
        generate_standard "$API_VERSION" "$TARGET_ORG"
        retrieve_standard "$TARGET_ORG"
        ;;
    all)
        generate_all "$API_VERSION"
        retrieve
        ;;
    generate-only)
        SUBMODE="${2:-standard}"
        case "$SUBMODE" in
            standard)
                TARGET_ORG=$(get_target_org)
                generate_standard "$API_VERSION" "$TARGET_ORG"
                ;;
            all)
                generate_all "$API_VERSION"
                ;;
            *)
                error "不明なモード: $SUBMODE (standard / all)"
                ;;
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
