#!/usr/bin/env python3
"""
extract_lwc_skeleton.py

LWC JavaScript ソースを静的解析し、generate_screen_design.py 互換の
スケルトン JSON を生成する。

主な抽出内容:
  - @salesforce/apex インポート → calls フィールド（機械的に確定）
  - @wire デコレータ → ワイヤーアダプターのユースケース
  - handle* / connectedCallback → イベントハンドラのユースケース
  - プライベートメソッド経由の呼び出しも 3 段階まで追跡

エージェントは title / detail / overview / items のみ補完する。
calls フィールドは上書きしないこと（機械的に確定済み）。

Usage:
  python extract_lwc_skeleton.py --input myComponent.js [--output skeleton.json]
  python extract_lwc_skeleton.py --input myComponent.js  # stdout
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path


# ─── 正規表現 ────────────────────────────────────────────────────────────────

# import apexAlias from '@salesforce/apex/ClassName.methodName';
_RE_APEX_IMPORT = re.compile(
    r"import\s+(\w+)\s+from\s+['\"]@salesforce/apex/(\w+)\.(\w+)['\"]",
    re.I,
)

# @wire(apexAlias)  or  @wire(apexAlias, { ... })
_RE_WIRE = re.compile(
    r'@wire\s*\(\s*(\w+)(?:\s*,[^)]+)?\s*\)',
    re.I,
)

# クラスのメソッド定義（通常関数・アロー関数）
# 例: handleSave() { ... }  /  getData = async (id) => { ... }
_RE_METHOD = re.compile(
    r'(?:^|\n)[ \t]+'           # インデント（クラスのメンバーは必ずインデント）
    r'(?:async\s+)?'             # 任意の async
    r'(\w+)'                     # メソッド名
    r'\s*(?:=\s*(?:async\s+)?(?:\([^)]*\)|\w+)\s*=>|\([^)]*\)\s*)\{',  # 引数 + {
    re.I,
)

# connectedCallback / renderedCallback
_RE_LIFECYCLE = re.compile(
    r'(?:^|\n)[ \t]*(connectedCallback|renderedCallback)\s*\(\s*\)\s*\{',
    re.I,
)

# ある本体の中で呼ばれているメソッド: this.xxx( または単独の xxx(
_RE_CALL = re.compile(r'(?:this\.)?(\w+)\s*\(', re.I)


# ─── ユーティリティ ──────────────────────────────────────────────────────────

def strip_comments(code: str) -> str:
    """JS コメントを除去（文字列内は保持）。"""
    out, i = [], 0
    in_str, sc = False, ''
    while i < len(code):
        c = code[i]
        if in_str:
            out.append(c)
            if c == '\\' and i + 1 < len(code):
                i += 1
                out.append(code[i])
            elif c == sc:
                in_str = False
        elif c in ('"', "'", '`'):
            in_str, sc = True, c
            out.append(c)
        elif code[i:i + 2] == '//':
            while i < len(code) and code[i] != '\n':
                i += 1
            continue
        elif code[i:i + 2] == '/*':
            i += 2
            while i < len(code) and code[i:i + 2] != '*/':
                if code[i] == '\n':
                    out.append('\n')
                i += 1
            i += 2
            continue
        else:
            out.append(c)
        i += 1
    return ''.join(out)


def balanced_end(code: str, pos: int) -> int:
    """pos 位置の '{' に対応する '}' のインデックスを返す。"""
    depth = 0
    in_str, sc = False, ''
    i = pos
    while i < len(code):
        c = code[i]
        if in_str:
            if c == '\\':
                i += 1
            elif c == sc:
                in_str = False
        elif c in ('"', "'", '`'):
            in_str, sc = True, c
        elif c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return len(code) - 1


def extract_body(code: str, match_start: int) -> str:
    """マッチ位置以降の最初の '{...}' ブロックを取得する。"""
    brace_pos = code.find('{', match_start)
    if brace_pos < 0:
        return ''
    end = balanced_end(code, brace_pos)
    return code[brace_pos + 1:end]


def calls_text(class_name: str, method_name: str) -> str:
    """フロー図の calls.text 用に 20 文字以内に整形する。"""
    full = f"{class_name}.{method_name}"
    if len(full) <= 20:
        return full
    # クラス名を短縮して試みる（メソッド名を優先して残す）
    max_cls = 20 - 1 - len(method_name)  # '.' を引く
    if max_cls >= 4:
        return f"{class_name[:max_cls]}.{method_name}"
    return full[:17] + '...'


# ─── メソッドマップ構築 ───────────────────────────────────────────────────────

def build_method_map(clean: str) -> dict[str, str]:
    """クラス内の全メソッド名 → 本体文字列 のマップを返す。"""
    method_map: dict[str, str] = {}

    # lifecycle も含めて全メソッド定義を検出
    for m in re.finditer(
        r'(?:^|\n)[ \t]+'
        r'(?:(?:get|set)\s+)?'    # getter/setter
        r'(?:async\s+)?'
        r'(\w+)'
        r'\s*(?:=\s*(?:async\s+)?(?:\([^)]*\)|\w+)\s*=>|\([^)]*\)\s*)\{',
        clean, re.I,
    ):
        name = m.group(1)
        # JS キーワードを除外
        if name.lower() in ('if', 'for', 'while', 'switch', 'catch', 'return'):
            continue
        brace = clean.find('{', m.start())
        if brace < 0:
            continue
        end = balanced_end(clean, brace)
        body = clean[brace + 1:end]
        method_map[name] = body

    return method_map


def direct_apex_calls(body: str, apex_imports: dict[str, tuple[str, str]]) -> list[str]:
    """本体内で直接呼ばれている Apex エイリアス名を返す（重複除去・出現順）。"""
    seen: set[str] = set()
    result: list[str] = []
    for m in _RE_CALL.finditer(body):
        name = m.group(1)
        if name in apex_imports and name not in seen:
            seen.add(name)
            result.append(name)
    return result


def direct_local_calls(body: str, method_map: dict[str, str]) -> list[str]:
    """本体内で直接呼ばれているローカルメソッド名を返す（重複除去・出現順）。"""
    seen: set[str] = set()
    result: list[str] = []
    for m in _RE_CALL.finditer(body):
        name = m.group(1)
        if name in method_map and name not in seen:
            seen.add(name)
            result.append(name)
    return result


def resolve_apex_calls(
    body: str,
    apex_imports: dict[str, tuple[str, str]],
    method_map: dict[str, str],
    max_depth: int = 3,
    _visited: frozenset[str] | None = None,
) -> list[str]:
    """本体から推移的に呼ばれる全 Apex エイリアスを返す（プライベートメソッド経由を含む）。"""
    if _visited is None:
        _visited = frozenset()

    seen: set[str] = set()
    result: list[str] = []

    # 直接 Apex 呼び出し
    for alias in direct_apex_calls(body, apex_imports):
        if alias not in seen:
            seen.add(alias)
            result.append(alias)

    # ローカルメソッド経由（最大 max_depth まで）
    if max_depth > 0:
        for local_name in direct_local_calls(body, method_map):
            if local_name in _visited:
                continue
            local_body = method_map[local_name]
            sub_calls = resolve_apex_calls(
                local_body, apex_imports, method_map,
                max_depth - 1, _visited | {local_name},
            )
            for alias in sub_calls:
                if alias not in seen:
                    seen.add(alias)
                    result.append(alias)

    return result


# ─── ステップ生成 ─────────────────────────────────────────────────────────────

def make_apex_step(alias: str, apex_imports: dict[str, tuple[str, str]], step_no: int) -> dict:
    """Apex 呼び出しステップ（calls 確定済み）を生成する。"""
    cls, mth = apex_imports[alias]
    return {
        'no': step_no,
        'title': '',          # エージェントが補完
        'detail': '',         # エージェントが補完
        'node_type': 'process',
        'calls': {'text': calls_text(cls, mth)},
        'object_ref': None,
        'branch': {
            'text': '',
            'node_type': 'error',
            'label': 'エラー時',
        },
        'sub_steps': [],
    }


def make_placeholder_step(step_no: int) -> dict:
    """エージェントが title/detail を補完するプレースホルダーステップ。"""
    return {
        'no': step_no,
        'title': '',
        'detail': '',
        'node_type': 'process',
        'calls': None,
        'object_ref': None,
        'branch': None,
        'sub_steps': [],
    }


# ─── メイン解析 ───────────────────────────────────────────────────────────────

def parse_lwc(code: str, component_name: str) -> dict:
    clean = strip_comments(code)

    # ── Apex インポートの収集 ─────────────────────────────────────────────
    # alias → (ClassName, methodName)
    apex_imports: dict[str, tuple[str, str]] = {}
    for m in _RE_APEX_IMPORT.finditer(clean):
        alias = m.group(1)
        cls = m.group(2)
        mth = m.group(3)
        apex_imports[alias] = (cls, mth)

    # ── クラスのメソッドマップを構築 ─────────────────────────────────────
    method_map = build_method_map(clean)

    # ── @wire で使われているエイリアスを記録 ──────────────────────────────
    wire_aliases: set[str] = set()
    for m in _RE_WIRE.finditer(clean):
        alias = m.group(1)
        if alias in apex_imports:
            wire_aliases.add(alias)

    usecases: list[dict] = []
    uc_no = 1

    # ── connectedCallback / renderedCallback ──────────────────────────────
    for m in _RE_LIFECYCLE.finditer(clean):
        func_name = m.group(1)
        body = extract_body(clean, m.start())
        apex_in_body = resolve_apex_calls(body, apex_imports, method_map)
        # wire で呼ばれるものは別ユースケースで扱う
        apex_in_body = [a for a in apex_in_body if a not in wire_aliases]

        if func_name == 'renderedCallback' and not apex_in_body:
            continue  # Apex 呼び出しのない renderedCallback は省略

        steps: list[dict] = []
        step_no = 1
        steps.append(make_placeholder_step(step_no))
        step_no += 1
        for alias in apex_in_body:
            steps.append(make_apex_step(alias, apex_imports, step_no))
            step_no += 1

        usecases.append({
            'no': uc_no,
            'title': '初期表示' if func_name == 'connectedCallback' else '再レンダリング時',
            'trigger': 'ページロード',
            'steps': steps,
        })
        uc_no += 1

    # ── @wire ユースケース ───────────────────────────────────────────────
    for alias in wire_aliases:
        cls, mth = apex_imports[alias]
        steps = [make_apex_step(alias, apex_imports, 1)]
        usecases.append({
            'no': uc_no,
            'title': f'{mth}（ワイヤー）',
            'trigger': 'レコードID変更 / コンポーネント初期化',
            'steps': steps,
        })
        uc_no += 1

    # ── handle* イベントハンドラ ─────────────────────────────────────────
    seen_methods: set[str] = set()
    for m in _RE_METHOD.finditer(clean):
        func_name = m.group(1)
        if not func_name.startswith('handle') and not func_name.startswith('Handle'):
            continue
        if func_name in seen_methods:
            continue
        seen_methods.add(func_name)

        body = extract_body(clean, m.start())
        apex_in_body = resolve_apex_calls(body, apex_imports, method_map)

        steps: list[dict] = []
        step_no = 1
        steps.append(make_placeholder_step(step_no))
        step_no += 1
        for alias in apex_in_body:
            steps.append(make_apex_step(alias, apex_imports, step_no))
            step_no += 1

        usecases.append({
            'no': uc_no,
            'title': func_name,
            'trigger': 'ボタンクリック / イベント発火',
            'steps': steps,
        })
        uc_no += 1

    # ── フォールバック ───────────────────────────────────────────────────
    if not usecases and apex_imports:
        steps = []
        for i, alias in enumerate(apex_imports):
            steps.append(make_apex_step(alias, apex_imports, i + 1))
        usecases.append({
            'no': 1,
            'title': '',
            'trigger': '',
            'steps': steps,
        })
    elif not usecases:
        usecases.append({
            'no': 1,
            'title': '',
            'trigger': '',
            'steps': [make_placeholder_step(1)],
        })

    return {
        'type': 'LWC',
        'api_name': component_name,
        'name': '',
        'project_name': '',
        'system_name': '',
        'author': '',
        'version': '1.0',
        'date': '',
        'purpose': '',
        'overview': '',
        'features': [],
        'prerequisites': '',
        'transition': '',
        'items': [],
        'usecases': usecases,
        'param_sections': [],
        'revision_history': [],
        '_parser_meta': {
            'apex_imports': {
                alias: f"{cls}.{mth}"
                for alias, (cls, mth) in apex_imports.items()
            },
            'wire_aliases': list(wire_aliases),
            'usecase_count': len(usecases),
            'note': (
                'calls フィールドは機械的に確定済み。'
                'エージェントは title / detail / overview / items のみ補完すること。'
            ),
        },
    }


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description='LWC JS → スケルトン JSON')
    ap.add_argument('--input', '-i', required=True, help='入力 .js ファイル')
    ap.add_argument('--output', '-o', help='出力 JSON ファイル（省略時 stdout）')
    args = ap.parse_args()

    path = Path(args.input)
    component_name = path.stem
    try:
        code = path.read_text(encoding='utf-8')
    except FileNotFoundError:
        print(f"[ERROR] ファイルが見つかりません: {path}", file=sys.stderr)
        sys.exit(1)
    except PermissionError:
        print(f"[ERROR] ファイルへのアクセス権がありません: {path}", file=sys.stderr)
        sys.exit(1)
    result = parse_lwc(code, component_name)
    out = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        Path(args.output).write_text(out, encoding='utf-8')
        meta = result['_parser_meta']
        print(
            f"[OK] {args.output}  "
            f"apex_imports={len(meta['apex_imports'])}  "
            f"usecases={meta['usecase_count']}",
            file=sys.stderr,
        )
    else:
        print(out)


if __name__ == '__main__':
    main()
