# 開発ナレッジ

スクリプト・テンプレート開発で得た技術知見を蓄積するファイル。
コンテキスト圧縮（/compact）時に自動追記される。

---

## スクリプト構成（C:\ClaudeCode\scripts\python\sf-doc-mcp\）

| スクリプト | 役割 |
|---|---|
| `generate_pptx.py` | PPTX生成エンジン（全layoutビルダー）。BUILDERS mapで拡張 |
| `generate_project_doc.py` | プロジェクト資料（概要+システム構成図+業務フロー） |
| `generate_data_model.py` | データモデル定義書PPTX |
| `generate.py` | オブジェクト項目定義書Excel（Step C） |
| `generate_feature_design.py` | 機能設計書Excel（Step D） |
| `generate_feature_list.py` | 機能一覧Excel（Step D） |
| `generate_screen_design.py` | 画面設計書Excel |
| `generate_overview.py` | システム概要書PDF（fpdf使用） |
| `scan_features.py` | force-app/スキャン・feature_ids.yml管理 |
| `diagram_gen.py` | Graphviz製図形PNG生成（処理フロー図・コンポーネント関連図・システム構成図） |
| `flowchart_utils.py` | matplotlib製フローチャートPNG生成（設計書内埋め込み用） |
| `build_template.py` | 機能設計書テンプレートExcel生成 |
| `build_feature_list_template.py` | 機能一覧テンプレートExcel生成 |
| `build_screen_template.py` | 画面設計書テンプレートExcel生成 |
| `meta_store.py` | Excelメタデータの読み書き（バージョン管理用） |
| `version_manager.py` | バージョン番号管理 |
| `fetcher.py` | SF CLI経由でメタデータ取得 |
| `connector.py` | SF組織への接続 |
| `writer.py` | Excel書き込みユーティリティ |

## generate_pptx.py のレイアウト対応表

| layout値 | ビルダー | 主な用途 |
|---|---|---|
| `cover` | `build_cover` | 表紙（自動） |
| `toc` | `_build_toc` | 目次 |
| `section` | `build_section` | セクション区切り |
| `content` | `build_content` | テキスト本文 |
| `bullets` | `build_bullets` | 箇条書き |
| `table` | `build_table` | テーブル |
| `two_column` | `build_two_column` | 2カラム |
| `diagram` | `build_diagram` | ボックス+矢印の構成図 |
| `er` | `build_er` | ERダイアグラム（クロウズフット記法） |
| `swimlane` | `build_swimlane` | スイムレーン業務フロー |
| `mermaid` | `build_mermaid_diagram` | Mermaid→PNG埋め込み |

## ハマりポイント

### generate_pptx.py
- ER図の向き判定: `toward_box_pos = (x1 < scx) if is_horiz else (y1 < scy)` — 逆にすると矢印マーカーが反転する
- swimlane の col は1始まり整数。steps の id は string と integer どちらも来る可能性あり

### generate_data_model.py
- `classify_category()` でカテゴリ名を正規表現分類。新カテゴリ名は `_CATEGORY_RULES` に追加
- `layout_hierarchical()` のオーバーフロー対策: 最大3回再試行で隣レイヤーに溢れさせる

### generate_project_doc.py
- swimlanes.json の新スキーマ（lanes/steps/transitions）と旧スキーマ（elements直接）の両方を受け付ける
- `_assign_cols()` でKahnアルゴリズムによる最長パス層化を行う

### diagram_gen.py（Graphviz）
- Graphviz バイナリは `C:/Program Files/Graphviz/bin/` — generate_basic_doc.py で os.environ["PATH"] に自動追加
- 処理フロー図: `rankdir=TB` + `rank=same` サブグラフで水平ステップ行を実現。コンポーネント名はステップノードの下に invisible ノード+invisible edge で配置
- フォント: Meiryo（MS GothicはASCII文字が狭くつぶれるため不可）
- HTML label の `STYLE="ROUNDED"` はテキストをクリップするため使用禁止。通常ノードの `shape="box", style="filled,rounded", margin="0.25,0.18"` を使う
- コンポーネント関連図: `steps` パラメータでトリガーノードを推定し呼び出し順序の矢印を表示

### flowchart_utils.py
- フォント: `C:/Windows/Fonts/YuGothR.ttc`（存在確認してからロード）
- `generate_flowchart()` の戻り値: True/False（matplotlib未インストール時False）

## テンプレート方式（B案）の概要
- 設計書はExcel雛形（.xlsx）を用意し、openpyxlで値・表・図を流し込む
- 雛形がないとレイアウトがばらつくため、`build_*_template.py` で先に雛形を生成してから使う
- openpyxlで load_workbook→save すると既存画像が消えるため、**ユーザが画像を貼るシートは分離する**

## sf-memory / project-doc コマンド

- 大本テンプレート: `C:\workspace\claude-temp`
- GFプロジェクト用: `C:\workspace\16_グリーンフィールド\gf`
- sf-memory の生成順序: カテゴリ1（組織概要+フロー+システム構成）→ カテゴリ2・3・4 並列 → 2周目横断補完
- project-doc のStep A は `generate_project_doc.py`（旧generate_flow.py・generate_project_overview.pyを統合）

## ER図レイアウトのベストプラクティス

**shapes数の現実的な上限**:
- ER ボックス 1個につき shapes 4つ（外枠・ヘッダー矩形・ヘッダーTB・フィールドTB）
- リレーション 1本につき shapes 4〜5つ（コネクタ・クロウズフット×2・ラベルbox）
- 7オブジェクト + 8リレーション ≈ 70 shapes が現実的な最小値

**過密ER図の対処法**:
1. オブジェクト分割: スライド1はコアTX7のみ、スライド2は参照先をテーブルで表示
2. 補助系・ログ系はER図でなくテーブルスライドで見せる

## generate_data_model.py の parse_index 注意点
- `## 標準オブジェクト（使用中）` は `##` レベル見出しのため、旧実装では current_h3 をリセットして**標準オブジェクトが std_objs に入らない**バグがあった
- 修正: `_active_cat()` で `##` レベルもカテゴリとして扱う + `_SKIP_H2_PATTERNS` で非オブジェクトセクションをスキップ

## diagrams.json（docs/overview/diagrams.json）の利用
- キー: `asis` / `tobe` / `system`
- 各エントリに `title` + `elements`（groups/boxes/arrows）を持つ `diagram` layout 形式
