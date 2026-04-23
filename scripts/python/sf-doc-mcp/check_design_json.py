"""
設計書 JSON の品質チェックスクリプト。

Phase 1.5 でエージェントが呼び出し、JSON を機械的に検証する。
エラー（構造的に必ず間違い）と警告（要確認）に分けて報告する。

Usage:
    python check_design_json.py --input design.json --type feature|screen

終了コード:
    0: エラーなし（警告のみは 0）
    1: エラーあり（エージェントは修正してから再チェックすること）
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

# Windows cp932 環境で絵文字・日本語の print が UnicodeEncodeError にならないよう UTF-8 を強制する。
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def check_feature(data: dict) -> tuple[list[str], list[str]]:
    """機能設計書（Apex/Flow/Integration）のチェック。"""
    errors: list[str] = []
    warnings: list[str] = []

    steps = data.get("steps", [])

    for i, step in enumerate(steps):
        label = f"steps[{i}] (no={step.get('no', '?')}, title={step.get('title', '?')!r})"
        ntype = step.get("node_type", "process")
        branch = step.get("branch")
        calls = step.get("calls")
        obj = step.get("object_ref")

        # 禁止された node_type: "object" の使用
        if ntype == "object":
            errors.append(
                f"{label}: node_type='object' は禁止。"
                "node_type='process' + object_ref に変更すること。"
            )

        # エラーステップがメインフローに独立して存在している
        if ntype == "error":
            errors.append(
                f"{label}: node_type='error' がメインフローに存在。"
                "エラー処理は decision ステップの branch に置くこと。"
            )

        # decision なのに branch がない
        if ntype == "decision" and not branch:
            errors.append(
                f"{label}: node_type='decision' だが branch が未設定。"
                "条件分岐には必ず branch を付与すること。"
            )

        # calls テキストが長すぎる
        if calls:
            calls_text = calls if isinstance(calls, str) else calls.get("text", "")
            if len(calls_text) > 20:
                warnings.append(
                    f"{label}: calls.text が20文字超 ({len(calls_text)}文字)。"
                    "フロー図で見切れる可能性がある。略称を検討すること。"
                )

        # タイトルが長すぎる
        title = step.get("title", "")
        if len(title) > 20:
            warnings.append(
                f"{label}: title が20文字超 ({len(title)}文字)。"
                "フロー図の図形内で折り返しが多くなる。短縮を検討すること。"
            )

        # sub_steps の SOQL/DML チェック
        for sub in step.get("sub_steps", []):
            sub_label = f"  sub_steps (title={sub.get('title', '?')!r})"
            if sub.get("title") in ("SOQL", "DML") and not sub.get("detail"):
                warnings.append(
                    f"{sub_label}: SOQL/DML の detail が空。クエリ・DML 内容を記載すること。"
                )

    # steps が空
    if not steps:
        warnings.append("steps が空。処理内容が記述されていない。")

    # overview が短すぎる
    overview = data.get("overview", "")
    if isinstance(overview, str) and len(overview) < 20:
        warnings.append(f"overview が短すぎる ({len(overview)}文字)。具体的なオブジェクト名・処理内容を含めること。")

    return errors, warnings


def check_screen(data: dict) -> tuple[list[str], list[str]]:
    """画面設計書（LWC/画面フロー/Aura/Visualforce）のチェック。"""
    errors: list[str] = []
    warnings: list[str] = []

    usecases = data.get("usecases", [])

    if not usecases:
        warnings.append("usecases が空。ユースケースが記述されていない。")

    for ui, uc in enumerate(usecases):
        uc_label = f"usecases[{ui}] (title={uc.get('title', '?')!r})"
        steps = uc.get("steps", [])

        has_calls = False

        for i, step in enumerate(steps):
            label = f"  {uc_label} > steps[{i}] (no={step.get('no', '?')}, title={step.get('title', '?')!r})"
            ntype = step.get("node_type", "process")
            branch = step.get("branch")
            calls = step.get("calls")

            # 禁止された node_type: "object" の使用
            if ntype == "object":
                errors.append(
                    f"{label}: node_type='object' は禁止。"
                    "node_type='process' + object_ref に変更すること。"
                )

            # エラーステップがメインフローに独立して存在している
            if ntype == "error":
                errors.append(
                    f"{label}: node_type='error' がメインフローに存在。"
                    "エラー処理は decision ステップの branch に置くこと。"
                )

            # decision なのに branch がない
            if ntype == "decision" and not branch:
                errors.append(
                    f"{label}: node_type='decision' だが branch が未設定。"
                    "条件分岐には必ず branch を付与すること。"
                )

            # calls テキストが長すぎる
            if calls:
                has_calls = True
                calls_text = calls if isinstance(calls, str) else calls.get("text", "")
                if len(calls_text) > 20:
                    warnings.append(
                        f"{label}: calls.text が20文字超 ({len(calls_text)}文字)。略称を検討すること。"
                    )

            # タイトルが長すぎる
            title = step.get("title", "")
            if len(title) > 20:
                warnings.append(
                    f"{label}: title が20文字超 ({len(title)}文字)。フロー図で折り返しが多くなる。"
                )

        # Apex を呼ぶユースケースなのに calls がない（ヒューリスティック）
        uc_title = uc.get("title", "")
        if not has_calls and steps and any(
            kw in uc_title for kw in ("保存", "登録", "更新", "削除", "取得", "呼び出し", "実行")
        ):
            warnings.append(
                f"{uc_label}: Apex 呼び出しが想定されるユースケースだが calls が未設定。"
                "コントローラー呼び出しには calls フィールドを付与すること。"
            )

    # items チェック
    items = data.get("items", [])
    if not items:
        warnings.append("items が空。画面項目定義が記述されていない。")

    return errors, warnings


def main():
    parser = argparse.ArgumentParser(description="設計書 JSON 品質チェック")
    parser.add_argument("--input", required=True, help="チェック対象の JSON ファイル")
    parser.add_argument("--type", choices=["feature", "screen"], default="feature",
                        help="設計書の種別（feature: 機能設計書 / screen: 画面設計書）")
    args = parser.parse_args()

    path = Path(args.input)
    if not path.exists():
        print(f"[ERROR] ファイルが見つかりません: {path}", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON パースエラー: {e}", file=sys.stderr)
        sys.exit(1)

    if args.type == "screen":
        errors, warnings = check_screen(data)
    else:
        errors, warnings = check_feature(data)

    name = data.get("name", path.stem)
    print(f"\n=== 設計書チェック結果: {name} ===")

    if errors:
        print(f"\n❌ ERROR ({len(errors)}件) — 修正してから Excel 生成すること:")
        for e in errors:
            print(f"  • {e}")

    if warnings:
        print(f"\n⚠️  WARNING ({len(warnings)}件) — 要確認（問題なければ続行可）:")
        for w in warnings:
            print(f"  • {w}")

    if not errors and not warnings:
        print("\n✅ 問題なし。Phase 2 へ進んでよい。")
    elif not errors:
        print("\n✅ エラーなし。警告を確認して問題なければ Phase 2 へ進んでよい。")
    else:
        print("\n❌ エラーあり。上記を修正してから再チェックすること。")
        sys.exit(1)


if __name__ == "__main__":
    main()
