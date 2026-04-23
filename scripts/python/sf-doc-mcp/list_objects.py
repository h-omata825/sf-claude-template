# -*- coding: utf-8 -*-
"""接続中の組織のオブジェクト一覧を表示する"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from connector import SalesforceConnector


def connect_via_sf_cli(alias: str) -> SalesforceConnector:
    result = subprocess.run(
        ["sf", "org", "display", "--target-org", alias, "--json"],
        capture_output=True, text=True, encoding="utf-8", timeout=30,
    )
    raw = result.stdout
    json_start = raw.find("{")
    data = json.loads(raw[json_start:])
    if data.get("status") != 0:
        print(f"[エラー] SF CLI: {data.get('message', '')}", file=sys.stderr)
        sys.exit(1)
    r = data["result"]
    return SalesforceConnector.from_session(r["accessToken"], r["instanceUrl"], r.get("username", alias))


def main():
    parser = argparse.ArgumentParser(description="Salesforce オブジェクト一覧")
    parser.add_argument("--sf-alias", required=True, help="SF CLI のエイリアス名")
    parser.add_argument("--search",   default="",    help="絞り込みキーワード")
    parser.add_argument("--limit",    type=int, default=100)
    args = parser.parse_args()

    conn = connect_via_sf_cli(args.sf_alias)
    sobjects = conn.sf.describe()["sobjects"]

    if args.search:
        kw = args.search.lower()
        sobjects = [o for o in sobjects if kw in o["name"].lower() or kw in o["label"].lower()]

    custom   = [o for o in sobjects if o["name"].endswith("__c")]
    standard = [o for o in sobjects if not o["name"].endswith("__c")]
    results  = custom + standard

    print(f"オブジェクト一覧 ({len(results)}件):")
    for o in results[:args.limit]:
        print(f"  {o['name']}  ({o['label']})")
    if len(results) > args.limit:
        print(f"  ... 他 {len(results) - args.limit} 件（--search で絞り込んでください）")


if __name__ == "__main__":
    main()
