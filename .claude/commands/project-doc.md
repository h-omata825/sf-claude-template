オブジェクト項目定義書（Salesforce）を会話形式で作成します。
スクリプトは `c:\ClaudeCode\scripts\python\sf-doc-mcp\` にあります。

**選択肢は必ず AskUserQuestion ツールで提示する（クリック選択）。テキスト入力は名前・パス等の自由記述のみ。**

---

## Step 1: 接続先の選択

まずカレントディレクトリの `.sf/config.json` から target-org を取得する:
```bash
python -c "
import json, pathlib, sys
p = pathlib.Path('.sf/config.json')
if p.exists():
    d = json.loads(p.read_text(encoding='utf-8'))
    print(d.get('target-org', ''))
"
```

**target-org が取得できた場合:**
その1件だけを AskUserQuestion で提示（その他で手動入力も可能）:
- label: "{alias}（このプロジェクトのデフォルト組織）" description: ".sf/config.json で設定されている組織"
- label: "その他" description: "別の組織のエイリアスを手動入力"

**target-org が取得できなかった場合:**
「このフォルダにはSalesforce組織が設定されていません。ブラウザでログインします」と伝え、以下を実行:
```bash
sf org login web --alias _doc-tmp
```
ブラウザが開くのでログインしてもらう。完了後 `SF_ALIAS=_doc-tmp` として控える。
（生成完了後に `sf org logout --target-org _doc-tmp --no-prompt` で一時エイリアスを削除する）

---

## Step 2: 作成者名

テキストで聞く:
```
作成者名を入力してください（改版履歴・表紙に表示されます）:
```

---

## Step 3: 出力フォルダ

テキストで聞く:
```
定義書の出力先フォルダパスを入力してください:
```

---

## Step 4: 新規 or 更新の自動判定

Glob でフォルダ内の `オブジェクト項目定義書_v*.xlsx` を確認する。

**既存ファイルがある場合:**
ファイル名を表示したあと、AskUserQuestion でバージョン種別を選択:
- label: "マイナー更新（vX.Y → vX.Y+1）"、description: "変更箇所を赤字表示"
- label: "メジャー更新（vX.Y → vX+1.0）"、description: "赤字をリセットして黒字化"

**既存ファイルがない場合:**
「新規作成モード（v1.0）で進めます」と表示してStep 5へ。

---

## Step 5: システム名称

**新規作成の場合のみ** AskUserQuestion で聞く:
- label: "スキップ" description: "システム名称なしで作成"
- label: "入力する" description: "システム名称を指定する"（Otherで自由入力）

「入力する」または Other が選ばれた場合はテキストで入力してもらう。
更新の場合はこのステップをスキップ（前回の値を自動引き継ぎ）。

---

## Step 6: 対象オブジェクトの選択

**新規作成の場合:**
テキストで入力してもらう:
```
対象オブジェクトを入力してください（API名またはラベル名、複数可）:
（例: Account 取引先責任者 Opportunity__c）
```

**更新の場合:**
まず既存ファイルから前回のオブジェクト一覧を取得する:
```bash
python -c "
import sys
sys.path.insert(0, r'c:\ClaudeCode\scripts\python\sf-doc-mcp')
from meta_store import read_meta
m = read_meta(r'{既存ファイルのフルパス}')
if m:
    print(' '.join(m.get('objects', {}).keys()))
"
```

取得した一覧（例: `Account Opportunity Contact Knowledge__kav`）を表示したうえで、AskUserQuestion で選択:
- label: "既存と同じ（{オブジェクト一覧}）" description: "前回と同じオブジェクトで再生成"
- label: "既存＋追加" description: "既存オブジェクトに追加して生成"
- label: "全て指定し直す" description: "1から対象を指定する"

**「既存と同じ」選択時:** 前回のオブジェクトリストをそのまま使う。
**「既存＋追加」選択時:** テキストで追加オブジェクトを入力してもらい、既存リストに結合する。
**「全て指定し直す」選択時:** テキストで全オブジェクトを入力してもらう。

区切り文字は何でもOK（スペース・カンマ・全角スペース等）。
入力内容を `--objects` に渡す（generate.py 内で名前解決する）。

**スペルチェック:** オブジェクト名に明らかなタイポ（例: Oppotunity → Opportunity）があれば、生成前に確認を取る。

---

## Step 7: 確認して生成

設定内容を表示し、AskUserQuestion で確認:
- label: "生成する"、description: "定義書の生成を開始する"
- label: "キャンセル"、description: "中止する"

「生成する」が選ばれたら Bash で実行:

**SF CLI エイリアスで接続する場合（target-org あり）:**
```bash
python c:\ClaudeCode\scripts\python\sf-doc-mcp\generate.py \
  --sf-alias {SF_ALIAS} \
  --objects {オブジェクトリスト} \
  --output-dir "{出力フォルダ}" \
  --author "{作成者名}" \
  --system-name "{システム名称}" \
  --source-file "{既存ファイルのフルパス（新規は省略）}" \
  --version-increment {minor または major}
```

**username/password で接続する場合（target-org なし）:**
```bash
python c:\ClaudeCode\scripts\python\sf-doc-mcp\generate.py \
  --username {SF_USERNAME} \
  --password {SF_PASSWORD} \
  --security-token {SF_TOKEN} \
  --domain {login または test} \
  --objects {オブジェクトリスト} \
  --output-dir "{出力フォルダ}" \
  --author "{作成者名}" \
  --system-name "{システム名称}" \
  --source-file "{既存ファイルのフルパス（新規は省略）}" \
  --version-increment {minor または major}
```

---

## Step 8: 完了案内

出力パスを表示する。

ブラウザログインを使った場合（SF_ALIAS=_doc-tmp）は後処理として実行:
```bash
sf org logout --target-org _doc-tmp --no-prompt
```

内容について質問があれば対応する。
