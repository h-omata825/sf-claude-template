# 01_基本設計

`/sf-doc` コマンドが生成する基本設計ドキュメント。

| ファイル | 生成元スクリプト | 用途 |
|---|---|---|
| `プロジェクト概要書.xlsx` | `generate_basic_doc.py` | プロジェクト概要・システム構成・業務フロー・ER図 |
| `オブジェクト定義書.xlsx` | `generate_object_definition.py` | オブジェクト・項目定義 |
| `機能一覧.xlsx` | `generate_feature_list.py` | 機能ID・機能名・種別・担当オブジェクト一覧 |
| `画面一覧.xlsx` | `generate_screen_list.py` | 画面名・URL・説明・関連機能一覧 |

**前提**: `/sf-memory` でカテゴリ1〜2を先に実行しておくこと（`docs/overview/org-profile.md` と `docs/catalog/` が必要）。
