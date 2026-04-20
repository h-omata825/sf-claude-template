# 03_プログラム設計

`/sf-design` → `[2] プログラム設計` が生成するドキュメント。

コンポーネント種別ごとにサブフォルダに出力される。

| フォルダ | 対象 | ファイル名パターン |
|---|---|---|
| `Apex/` | Apexクラス・トリガーハンドラ | `{ClassName}_設計書.xlsx` |
| `Batch/` | バッチApex・スケジュールジョブ | `{ClassName}_設計書.xlsx` |
| `Flow/` | Screen Flow / AutoLaunched Flow | `{FlowApiName}_設計書.xlsx` |
| `LWC/` | Lightning Web Component | `{ComponentName}_設計書.xlsx` |
| `Visualforce/` | Visualforce Page / Component | `{Name}_設計書.xlsx` |
| `Aura/` | Aura Component | `{Name}_設計書.xlsx` |

**前提**: `/sf-retrieve` でforce-app/が最新化されていること。
