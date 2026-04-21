"""
高品質図生成モジュール（graphviz + drawsvg ベース）。

diagram_utils.py / er_utils.py の matplotlib 実装を置き換える新実装。

提供関数:
  render_system_diagram(system: dict, out_path: str) -> (width_px, height_px)
  render_er_diagram(objects: list, relations: list, out_path: str) -> (width_px, height_px)
  render_swimlane(flow: dict, out_path: str) -> (width_px, height_px)

依存:
  graphviz (pip + バイナリ)  ── 全図を直接PNG出力（Cairo不要）
  Pillow                     ── PNG サイズ確認
"""
from __future__ import annotations

import os
from pathlib import Path

# ── 依存チェック ──────────────────────────────────────────────────
try:
    import graphviz as _gv
    _HAS_GV = True
except ImportError:
    _HAS_GV = False

_HAS_SVG = False  # 未使用（graphvizが全図PNG直接出力するため不要）

try:
    from PIL import Image as _PILImage
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

# Graphviz バイナリ PATH（winget インストール先）
_GV_BIN = r"C:\Program Files\Graphviz\bin"
if os.path.isdir(_GV_BIN) and _GV_BIN not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _GV_BIN + os.pathsep + os.environ.get("PATH", "")

# ── カラーパレット ────────────────────────────────────────────────
C_SF_CORE   = "#1F3864"   # Salesforce中核（濃紺）
C_SF_LABEL  = "#FFFFFF"
C_ACTOR_BG  = "#D9E1F2"   # 利用者（薄青）
C_ACTOR_FG  = "#1F3864"
C_EXT_BG    = "#E2EFDA"   # 外部システム（薄緑）
C_EXT_FG    = "#375623"
C_DS_BG     = "#FFF2CC"   # データストア（薄黄）
C_DS_FG     = "#7F6000"
C_EDGE      = "#5A5A5A"
C_LANE_HDR  = "#1F3864"
C_HDR_BLUE    = "#2E75B6"
C_STEP_BG     = "#2E75B6"
C_STEP_FG     = "#FFFFFF"
C_STEP_BORDER = "#1F3864"

FONT_JP = "MS Gothic"   # graphviz 用（Windows）
DPI     = 150


# ════════════════════════════════════════════════════════════════
# 1. システム構成図（graphviz）
# ════════════════════════════════════════════════════════════════

def render_system_diagram(system: dict, out_path: str) -> tuple[int, int]:
    """
    system.json の内容からシステム構成図 PNG を生成する。

    system スキーマ:
      core: {name, role}
      actors: [{name, count?, channels?}]
      external_systems: [{name, direction, protocol, frequency, purpose}]
      data_stores: [{name, purpose}]
    """
    if not _HAS_GV:
        raise RuntimeError("graphviz が利用できません")

    g = _gv.Digraph(
        "system",
        graph_attr={
            "bgcolor": "white",
            "rankdir": "LR",
            "splines": "polyline",
            "nodesep": "0.5",
            "ranksep": "1.2",
            "fontname": FONT_JP,
            "pad": "0.4",
            "dpi": str(DPI),
        },
    )

    core = system.get("core") or {}
    core_label = _gv_label(core.get("name", "Salesforce"), core.get("role", ""))

    # 中核 Salesforce ノード
    g.node(
        "core",
        label=core_label,
        shape="box",
        style="filled,rounded",
        fillcolor=C_SF_CORE,
        fontcolor=C_SF_LABEL,
        fontname=FONT_JP,
        fontsize="12",
        width="2.2",
        height="0.9",
        penwidth="2",
    )

    # 利用者（左）
    with g.subgraph(name="cluster_actors") as sg:
        sg.attr(rank="min", style="invis")
        for i, actor in enumerate(system.get("actors", [])[:6]):
            nid = f"actor_{i}"
            cnt = f"\n({actor['count']}名)" if actor.get("count") else ""
            sg.node(
                nid,
                label=_gv_label(actor["name"] + cnt),
                shape="ellipse",
                style="filled",
                fillcolor=C_ACTOR_BG,
                fontcolor=C_ACTOR_FG,
                fontname=FONT_JP,
                fontsize="10",
                width="1.8",
            )
            g.edge(nid, "core", color=C_EDGE, arrowsize="0.8")

    # 外部システム（右）
    with g.subgraph(name="cluster_ext") as sg:
        sg.attr(rank="max", style="invis")
        active_ext = [e for e in system.get("external_systems", []) if e.get("direction", "out") != "none"]
        for i, ext in enumerate(active_ext[:8]):
            nid = f"ext_{i}"
            proto = ext.get("protocol", "")
            freq = ext.get("frequency", "")
            edge_lbl = f"{proto}" + (f"\n{freq}" if freq else "")
            sg.node(
                nid,
                label=_gv_label(ext["name"]),
                shape="box",
                style="filled,rounded",
                fillcolor=C_EXT_BG,
                fontcolor=C_EXT_FG,
                fontname=FONT_JP,
                fontsize="10",
                width="1.8",
            )
            direction = ext.get("direction", "out")
            if direction == "in":
                g.edge(nid, "core", xlabel=edge_lbl, color=C_EDGE, arrowsize="0.8",
                       fontname=FONT_JP, fontsize="8", fontcolor=C_EDGE)
            elif direction == "both":
                g.edge("core", nid, xlabel=edge_lbl, color=C_EDGE, arrowsize="0.8",
                       dir="both", fontname=FONT_JP, fontsize="8", fontcolor=C_EDGE)
            else:
                g.edge("core", nid, xlabel=edge_lbl, color=C_EDGE, arrowsize="0.8",
                       fontname=FONT_JP, fontsize="8", fontcolor=C_EDGE)

    # データストア（下）
    for i, ds in enumerate(system.get("data_stores", [])[:4]):
        nid = f"ds_{i}"
        g.node(
            nid,
            label=_gv_label(ds["name"]),
            shape="cylinder",
            style="filled",
            fillcolor=C_DS_BG,
            fontcolor=C_DS_FG,
            fontname=FONT_JP,
            fontsize="10",
        )
        g.edge("core", nid, color=C_EDGE, arrowsize="0.8", style="dashed")

    png_bytes = g.pipe(format="png")
    with open(out_path, "wb") as f:
        f.write(png_bytes)
    if _HAS_PIL:
        return _PILImage.open(out_path).size
    return (0, 0)


def _gv_label(*lines: str) -> str:
    return "\n".join(l for l in lines if l)


# ════════════════════════════════════════════════════════════════
# 2. ER図（graphviz record ノード）
# ════════════════════════════════════════════════════════════════

def render_er_diagram(
    objects: list[dict],
    relations: list[dict],
    out_path: str,
) -> tuple[int, int]:
    """
    オブジェクト一覧と関連定義からER図PNGを生成する。

    objects: [{api, label, type}]
    relations: [{parent, child, rel, field}]
      rel: "1-N" | "N-N" | "lookup" | "master-detail"
    """
    if not _HAS_GV:
        raise RuntimeError("graphviz が利用できません")

    g = _gv.Digraph(
        "er",
        graph_attr={
            "bgcolor": "white",
            "rankdir": "TB",
            "splines": "ortho",
            "nodesep": "0.6",
            "ranksep": "1.0",
            "fontname": FONT_JP,
            "pad": "0.4",
            "dpi": str(DPI),
        },
    )

    # 関連に登場するオブジェクトAPIのみ描画（孤立ノードを除外して図を見やすく）
    related_apis: set[str] = set()
    for rel in relations:
        if not rel["parent"].isdigit() and not rel["child"].isdigit():
            related_apis.add(rel["parent"])
            related_apis.add(rel["child"])

    # objects リストから label を引く辞書
    obj_label_map = {o["api"]: (o.get("label", ""), o.get("type", "")) for o in objects}

    obj_ids = set()
    for api in sorted(related_apis):  # ソートして毎回同じ順で配置
        nid = api.replace("__c", "_c").replace("__", "_")
        obj_ids.add(api)
        lbl, kind = obj_label_map.get(api, ("", ""))
        kind_color = "#1F3864" if kind in ("カスタム", "Custom") else "#2E75B6"
        # 日本語ラベルを主表示、APIを副表示（空セルはgraphvizエラーになるため条件分岐）
        if lbl:
            label = (
                f'<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">'
                f'<TR><TD BGCOLOR="{kind_color}"><FONT COLOR="white"><B>{lbl}</B></FONT></TD></TR>'
                f'<TR><TD BGCOLOR="#D9E1F2"><FONT COLOR="#666666">{api}</FONT></TD></TR>'
                f"</TABLE>>"
            )
        else:
            label = (
                f'<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">'
                f'<TR><TD BGCOLOR="{kind_color}"><FONT COLOR="white"><B>{api}</B></FONT></TD></TR>'
                f"</TABLE>>"
            )
        g.node(
            nid,
            label=label,
            shape="none",
            fontname=FONT_JP,
            fontsize="10",
        )

    # 関連エッジ
    for rel in relations:
        parent = rel["parent"]
        child = rel["child"]
        # 数字のみのノード（表の行番号が誤混入した場合）はスキップ
        if parent.isdigit() or child.isdigit():
            continue
        pid = parent.replace("__c", "_c").replace("__", "_")
        cid = child.replace("__c", "_c").replace("__", "_")
        rel_type = rel.get("rel", "").lower()
        if "master" in rel_type or "md" in rel_type:
            arrow = "diamond"
            style = "bold"
        elif "n-n" in rel_type or "many" in rel_type:
            arrow = "crow"
            style = "dashed"
        else:
            arrow = "vee"
            style = "solid"
        field_label = rel.get("field", "")
        g.edge(
            pid, cid,
            xlabel=field_label,   # ortho splines は label 非対応のため xlabel を使用
            arrowhead=arrow,
            style=style,
            color=C_EDGE,
            fontname=FONT_JP,
            fontsize="8",
            fontcolor=C_EDGE,
        )

    png_bytes = g.pipe(format="png")
    with open(out_path, "wb") as f:
        f.write(png_bytes)
    if _HAS_PIL:
        return _PILImage.open(out_path).size
    return (0, 0)


# ════════════════════════════════════════════════════════════════
# 3. スイムレーン図（graphviz cluster subgraph 方式）
# ════════════════════════════════════════════════════════════════

# レーン背景色（薄い色でクラスター塗りつぶし）
_LANE_COLORS = ["#EEF4FB", "#F5FBF0", "#FFFBF0", "#FBF5FF", "#F8FAFD"]

# レーン → グループ マッピングルール（順番に評価、最初にマッチしたものを使用）
_LANE_GROUP_RULES: list[tuple[list[str], str]] = [
    (["お客様", "customer", "顧客", "委託企業"],                       "お客様"),
    (["salesforce", "sfdc", "experience cloud", "experiencecloud"],  "Salesforce / EC"),
    (["外部連携", "外部システム", "oproarts", "ラポート", "account engagement"], "外部連携"),
]
_DEFAULT_LANE_GROUP = "GF社"

_GROUP_FILL_COLORS = {
    "お客様":         "#D9E9F8",
    "GF社":           "#E8F5E9",
    "Salesforce / EC": "#FFF9E6",
    "外部連携":       "#F3E5F5",
}
_GROUP_ORDER = ["お客様", "GF社", "Salesforce / EC", "外部連携"]


def _lane_to_group(lane_name: str) -> str:
    lower = lane_name.lower()
    for keywords, group in _LANE_GROUP_RULES:
        if any(k in lower for k in keywords):
            return group
    return _DEFAULT_LANE_GROUP


def render_swimlane(flow: dict, out_path: str) -> tuple[int, int]:
    """
    swimlanes.json の1フローからスイムレーン図PNGを生成する。
    graphviz cluster subgraph 方式（Cairo不要）。

    flow スキーマ:
      title: str
      lanes: [{name, type}]
      steps: [{id, lane, col, label}]
      transitions: [{from, to, condition?}]
    """
    if not _HAS_GV:
        raise RuntimeError("graphviz が利用できません")

    lanes_in = flow.get("lanes", [])
    steps_in = flow.get("steps", [])
    trans_in = flow.get("transitions", [])
    title    = flow.get("title", "業務フロー")

    g = _gv.Digraph(
        "swimlane",
        graph_attr={
            "bgcolor": "white",
            "rankdir": "LR",
            "splines": "polyline",
            "nodesep": "0.4",
            "ranksep": "0.6",
            "fontname": FONT_JP,
            "pad": "0.3",
            "dpi": str(DPI),
            "label": title,
            "labelloc": "t",
            "fontsize": "14",
            "fontcolor": C_LANE_HDR,
        },
    )

    # レーンをグループ（お客様 / GF社 / Salesforce / 外部連携）に集約して描画
    from collections import defaultdict, OrderedDict

    lane_names = [l.get("name", f"Lane{i+1}") for i, l in enumerate(lanes_in)]

    # グループ → [lane_name, ...] のマッピング（順序保持）
    group_to_lanes: dict[str, list[str]] = OrderedDict()
    for lane_name in lane_names:
        grp = _lane_to_group(lane_name)
        group_to_lanes.setdefault(grp, []).append(lane_name)

    # グループ順を _GROUP_ORDER に従って並び替え
    sorted_groups = [g_name for g_name in _GROUP_ORDER if g_name in group_to_lanes]
    sorted_groups += [g_name for g_name in group_to_lanes if g_name not in sorted_groups]

    known_lanes = set(lane_names)
    lane_color_idx = 0  # レーン色の連番

    for gi, grp_name in enumerate(sorted_groups):
        grp_fill = _GROUP_FILL_COLORS.get(grp_name, "#F8FAFD")
        with g.subgraph(name=f"cluster_group_{gi}") as gg:
            gg.attr(
                label=grp_name,
                style="filled",
                fillcolor=grp_fill,
                color=C_LANE_HDR,
                penwidth="2",
                fontname=FONT_JP,
                fontcolor=C_LANE_HDR,
                fontsize="13",
            )
            for lane_name in group_to_lanes[grp_name]:
                bg = _LANE_COLORS[lane_color_idx % len(_LANE_COLORS)]
                lane_color_idx += 1
                with gg.subgraph(name=f"cluster_lane_{gi}_{lane_name[:8]}") as sg:
                    sg.attr(
                        label=lane_name,
                        style="filled",
                        fillcolor=bg,
                        color=C_LANE_HDR,
                        penwidth="1",
                        fontname=FONT_JP,
                        fontcolor=C_LANE_HDR,
                        fontsize="10",
                    )
                    for step in steps_in:
                        if str(step.get("lane", "")) == lane_name:
                            sid = str(step.get("id", ""))
                            label = str(step.get("label", "") or step.get("title", "") or step.get("name", "") or sid)
                            sg.node(
                                sid,
                                label=label,
                                shape="box",
                                style="filled,rounded",
                                fillcolor=C_STEP_BG,
                                fontcolor=C_STEP_FG,
                                fontname=FONT_JP,
                                fontsize="10",
                                width="1.6",
                                height="0.6",
                                penwidth="1.5",
                                color=C_STEP_BORDER,
                            )

    # 未分類ステップ（lane 指定なし or 未知のレーン）
    for step in steps_in:
        if str(step.get("lane", "")) not in known_lanes:
            sid = str(step.get("id", ""))
            g.node(sid, label=str(step.get("label", "") or step.get("title", "") or step.get("name", "") or sid),
                   shape="box", style="filled,rounded",
                   fillcolor=C_STEP_BG, fontcolor=C_STEP_FG,
                   fontname=FONT_JP, fontsize="10")

    # 遷移エッジ
    for t in trans_in:
        src = str(t.get("from", ""))
        dst = str(t.get("to", ""))
        cond = t.get("condition", "")
        g.edge(src, dst,
               label=cond,
               color=C_EDGE,
               fontname=FONT_JP,
               fontsize="8",
               fontcolor=C_EDGE,
               arrowsize="0.8")

    png_bytes = g.pipe(format="png")
    with open(out_path, "wb") as f:
        f.write(png_bytes)
    if _HAS_PIL:
        return _PILImage.open(out_path).size
    return (0, 0)


# ════════════════════════════════════════════════════════════════
# 4. フローチャート（graphviz）
# ════════════════════════════════════════════════════════════════

def _short_label(text: str, max_len: int = 18) -> str:
    """テキストを max_len 文字で打ち切り、超えたら末尾に…を付ける。"""
    text = (text or "").strip()
    return text if len(text) <= max_len else text[:max_len] + "…"


def _wrap_jp(text: str, width: int = 12) -> str:
    """日本語テキストを width 文字で折り返す（\\n区切り）。切り捨てしない。"""
    text = (text or "").strip()
    lines = []
    while len(text) > width:
        lines.append(text[:width])
        text = text[width:]
    if text:
        lines.append(text)
    return "\\n".join(lines)


def _wrap_name(name: str, max_per_line: int = 14) -> str:
    """CamelCase/スネークケースの長い名前を max_per_line 文字で折り返す（\\n区切り）。"""
    if len(name) <= max_per_line:
        return name
    import re
    # CamelCase を単語に分割
    words = re.sub(r'([A-Z][a-z]+)', r' \1', name).split()
    lines, cur = [], ""
    for w in words:
        if cur and len(cur) + len(w) + 1 > max_per_line:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip() if cur else w
    if cur:
        lines.append(cur)
    return "\\n".join(lines) if lines else name


def render_flowchart(steps: list[dict], out_path: str) -> tuple[int, int]:
    """
    process_steps から処理フロー図PNGを生成する。

    設計方針:
      - 図の中: 番号バッジ + 6〜8文字の一言アクション（何をするか）
      - 図の外: コンポーネント名を各ノード下に小テキストで表示（HTMLラベル使用）
      - 詳細な処理内容・分岐条件は図下の表で補完

    steps: [{step, title, description, component, branch, next:[{to, condition}]}]
    """
    if not _HAS_GV:
        raise RuntimeError("graphviz が利用できません")

    # step番号 → バッジ文字（①②…⑳、超えたら(N)）
    _BADGES = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"

    def _badge(n: int) -> str:
        return _BADGES[n - 1] if 1 <= n <= len(_BADGES) else f"({n})"

    # アクション一言: 最初の動詞句を 8 文字以内で抽出
    def _action(title: str) -> str:
        t = (title or "").strip()
        # 「〜を〜する」→「〜する」に短縮: 「する」「します」「行う」で切る
        for pat in ["を", "から", "（", "、", "，", "。"]:
            idx = t.find(pat)
            if 0 < idx <= 8:
                t = t[:idx]
                break
        return t[:8]

    g = _gv.Digraph(
        "flowchart",
        graph_attr={
            "bgcolor": "white",
            "rankdir": "LR",
            "splines": "ortho",
            "nodesep": "0.5",
            "ranksep": "0.6",
            "fontname": FONT_JP,
            "pad": "0.3",
            "dpi": "100",
            "size": "9,3!",
        },
    )
    g.attr("node", shape="none", margin="0")

    for step in steps:
        sid        = str(step.get("step", ""))
        n          = int(step.get("step", 0))
        badge      = _badge(n)
        action     = _action(step.get("title", "") or step.get("description", ""))
        component  = step.get("component", "")
        branch     = step.get("branch", "")

        if branch:
            # 分岐ステップ: ひし形風の黄色バッジ
            badge_color  = "#7F6000"
            badge_bg     = "#FFF2CC"
            badge_border = "#BF9000"
        else:
            badge_color  = "white"
            badge_bg     = C_STEP_BG
            badge_border = "#1F3864"

        # HTMLラベル: 上段=バッジ（番号+アクション）、下段=コンポーネント名（小文字・灰色）
        comp_row = (
            f'<TR><TD ALIGN="CENTER">'
            f'<FONT POINT-SIZE="7" COLOR="#666666">{component}</FONT>'
            f'</TD></TR>'
        ) if component else ""

        html = (
            f'<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="0">'
            f'<TR><TD>'
            f'<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="6" '
            f'BGCOLOR="{badge_bg}" COLOR="{badge_border}" STYLE="ROUNDED">'
            f'<TR><TD ALIGN="CENTER">'
            f'<FONT POINT-SIZE="13" COLOR="{badge_color}"><B>{badge}</B></FONT>'
            f'<BR/>'
            f'<FONT POINT-SIZE="10" COLOR="{badge_color}">{action}</FONT>'
            f'</TD></TR>'
            f'</TABLE>'
            f'</TD></TR>'
            f'{comp_row}'
            f'</TABLE>>'
        )
        g.node(sid, label=html, fontname=FONT_JP)

    has_next = any(step.get("next") for step in steps)
    if has_next:
        for step in steps:
            src = str(step.get("step", ""))
            for nxt in (step.get("next") or []):
                cond = _short_label(nxt.get("condition", ""), 8)
                g.edge(src, str(nxt["to"]), xlabel=cond,
                       color=C_EDGE, fontname=FONT_JP, fontsize="8", fontcolor=C_EDGE,
                       arrowsize="0.8")
    else:
        for i, step in enumerate(steps[:-1]):
            src = str(step.get("step", ""))
            dst = str(steps[i + 1].get("step", ""))
            g.edge(src, dst, color=C_EDGE, arrowsize="0.8")

    png_bytes = g.pipe(format="png")
    with open(out_path, "wb") as f:
        f.write(png_bytes)
    if _HAS_PIL:
        return _PILImage.open(out_path).size
    return (0, 0)


# ════════════════════════════════════════════════════════════════
# 5. コンポーネント依存図（graphviz）
# ════════════════════════════════════════════════════════════════

_COMP_COLORS: dict[str, tuple[str, str]] = {
    "Apex":    (C_SF_CORE,  C_SF_LABEL),
    "LWC":     (C_HDR_BLUE, C_SF_LABEL),
    "Flow":    ("#00B0F0",  "#000000"),
    "Trigger": ("#1F3864",  "#FFFFFF"),
    "Batch":   ("#5A5A5A",  "#FFFFFF"),
}

def render_component_diagram(
    components: list[dict],
    out_path: str,
    steps: list[dict] | None = None,
) -> tuple[int, int]:
    """
    コンポーネント一覧から依存関係図PNGを生成する。

    components: [{api_name, type, role, callees:[str]}]
    steps:      process_steps（任意）。呼び出し順序と起動元の補完に使用。

    描画ルール:
      - callees で明示された依存は矢印で描画
      - steps の component 順序から、直接呼び出し関係がないコンポーネント同士を
        順番ラベル付き矢印で補完
      - steps の trigger / 最初のステップから起動元（Flow/Trigger）を推定してノード追加
    """
    if not _HAS_GV:
        raise RuntimeError("graphviz が利用できません")

    steps = steps or []
    known = {c.get("api_name", "") for c in components}

    # steps から呼び出し順マップを構築: api_name → step番号
    step_order: dict[str, int] = {}
    for s in steps:
        comp = s.get("component", "")
        if comp and comp not in step_order:
            step_order[comp] = int(s.get("step", 0))

    # 起動元ノードを推定（最初のステップのトリガー or business_flow の actor）
    trigger_node: str | None = None
    trigger_type = "Flow"
    if steps:
        first = steps[0]
        desc = (first.get("description", "") + first.get("title", "")).lower()
        if "trigger" in desc or "triggger" in desc:
            trigger_type = "Trigger"
        elif "batch" in desc:
            trigger_type = "Batch"
        elif "lwc" in desc or "lightning" in desc:
            trigger_type = "LWC"
        trigger_node = f"[{trigger_type}]"

    # callees で参照されているコンポーネント（被呼び出し側）
    called_by: set[str] = set()
    for comp in components:
        for c in comp.get("callees", []):
            called_by.add(c)

    g = _gv.Digraph(
        "components",
        graph_attr={
            "bgcolor": "white",
            "rankdir": "LR",
            "splines": "ortho",
            "nodesep": "0.4",
            "ranksep": "0.6",
            "fontname": FONT_JP,
            "pad": "0.3",
            "dpi": "100",
            "size": "9,3!",
        },
    )

    # 起動元ノード
    if trigger_node:
        fill, fg = _COMP_COLORS.get(trigger_type, ("#00B0F0", "#000000"))
        g.node(trigger_node,
               label=trigger_node,
               shape="box", style="filled,rounded",
               fillcolor=fill, fontcolor=fg,
               fontname=FONT_JP, fontsize="10", width="1.0")

    # コンポーネントノード（名前 + 種別のみ。ロールは表に記載するため除外）
    for comp in components:
        name  = comp.get("api_name", "")
        ctype = comp.get("type", "Apex")
        fill, fg = _COMP_COLORS.get(ctype, ("#5A5A5A", "#FFFFFF"))
        lbl = f"{_wrap_name(name, 14)}\\n[{ctype}]"
        g.node(name,
               label=lbl,
               shape="box", style="filled,rounded",
               fillcolor=fill, fontcolor=fg,
               fontname=FONT_JP, fontsize="9", width="1.8")

    # callees の明示依存エッジ
    for comp in components:
        src = comp.get("api_name", "")
        for callee in comp.get("callees", []):
            if callee not in known:
                g.node(callee, label=callee,
                       shape="box", style="filled,rounded",
                       fillcolor=C_EXT_BG, fontcolor=C_EXT_FG,
                       fontname=FONT_JP, fontsize="9")
            g.edge(src, callee, color=C_EDGE, arrowsize="0.7")

    # 起動元 → 直接呼び出されていないトップレベルコンポーネントをエッジ追加
    # （step順でソートして ①②③ ラベルを付ける）
    if trigger_node:
        top_level = [
            c.get("api_name", "") for c in components
            if c.get("api_name", "") not in called_by
        ]
        top_level_sorted = sorted(top_level, key=lambda n: step_order.get(n, 999))
        for i, name in enumerate(top_level_sorted, 1):
            g.edge(trigger_node, name,
                   xlabel=f"⑤"[:1] + str(i),  # ①②③...
                   color=C_EDGE, arrowsize="0.7",
                   fontname=FONT_JP, fontsize="9", fontcolor=C_EDGE,
                   style="dashed")

    png_bytes = g.pipe(format="png")
    with open(out_path, "wb") as f:
        f.write(png_bytes)
    if _HAS_PIL:
        return _PILImage.open(out_path).size
    return (0, 0)


# ════════════════════════════════════════════════════════════════
# 6. コンポーネント×オブジェクト参照マトリクス
# ════════════════════════════════════════════════════════════════

def render_object_access_matrix(
    object_access: list[dict],
    components: list[dict],
    related_objects: list[dict],
    out_path: str,
) -> tuple[int, int]:
    """コンポーネント×オブジェクト参照マトリクス図を生成する。

    object_access: [{"component": "X", "object": "Y", "operation": "R|W|RW|INSERT"}]
    components:    [{"api_name": "X", "type": "Apex", ...}]
    related_objects: [{"api_name": "Y", "label": "Z", ...}]
    """
    if not _HAS_GV:
        raise RuntimeError("graphviz が利用できません")

    # Apex コンポーネントのみを列に使う
    apex_comps = [c for c in components if c.get("type") == "Apex"]
    comp_names = [c.get("api_name", "") for c in apex_comps]
    if not comp_names:
        comp_names = [c.get("api_name", "") for c in components]

    obj_names  = [o.get("api_name", "") for o in related_objects]
    obj_labels = {o.get("api_name", ""): o.get("label", o.get("api_name", ""))
                  for o in related_objects}

    # アクセスマトリクス構築
    matrix: dict[str, dict[str, str]] = {o: {c: "" for c in comp_names} for o in obj_names}
    for entry in object_access:
        obj  = entry.get("object", "")
        comp = entry.get("component", "")
        op   = entry.get("operation", "")
        if obj in matrix and comp in matrix[obj]:
            matrix[obj][comp] = op

    # 操作種別の色
    _OP_COLOR = {
        "R":      "#D9E1F2",
        "W":      "#FFC7CE",
        "RW":     "#FFEB9C",
        "INSERT": "#C6EFCE",
    }
    HDR_BG = "#1F3864"
    HDR_FG = "white"

    def _td(content: str, bg: str = "white", bold: bool = False, align: str = "CENTER",
            fsize: str = "9") -> str:
        inner = f"<B>{content}</B>" if bold else content
        return (f'<TD BGCOLOR="{bg}" ALIGN="{align}" '
                f'CELLPADDING="4"><FONT POINT-SIZE="{fsize}">{inner}</FONT></TD>')

    # ヘッダ行
    header_cells = [_td("オブジェクト", bg=HDR_BG, bold=True,
                        align="LEFT", fsize="9").replace(f'COLOR="{HDR_BG}"',
                        f'COLOR="{HDR_BG}"').replace("<FONT", f'<FONT COLOR="{HDR_FG}"')]
    for comp in comp_names:
        header_cells.append(
            f'<TD BGCOLOR="{HDR_BG}" ALIGN="CENTER" CELLPADDING="4">'
            f'<FONT POINT-SIZE="8" COLOR="{HDR_FG}"><B>{comp}</B></FONT></TD>'
        )
    rows = [f'<TR>{"".join(header_cells)}</TR>']

    # データ行
    for obj in obj_names:
        label = obj_labels.get(obj, obj)
        cells = [
            f'<TD BGCOLOR="#F2F2F2" ALIGN="LEFT" CELLPADDING="4">'
            f'<FONT POINT-SIZE="9"><B>{label}</B></FONT><BR/>'
            f'<FONT POINT-SIZE="7" COLOR="#666666">{obj}</FONT></TD>'
        ]
        for comp in comp_names:
            op = matrix[obj][comp]
            bg = _OP_COLOR.get(op, "white")
            if op:
                cells.append(
                    f'<TD BGCOLOR="{bg}" ALIGN="CENTER" CELLPADDING="4">'
                    f'<FONT POINT-SIZE="9"><B>{op}</B></FONT></TD>'
                )
            else:
                cells.append(
                    '<TD ALIGN="CENTER" CELLPADDING="4">'
                    '<FONT POINT-SIZE="9" COLOR="#AAAAAA">-</FONT></TD>'
                )
        rows.append(f'<TR>{"".join(cells)}</TR>')

    table_html = (
        '<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" BGCOLOR="white">'
        + "".join(rows)
        + "</TABLE>>"
    )

    g = _gv.Digraph(
        "obj_matrix",
        graph_attr={
            "bgcolor": "white",
            "fontname": FONT_JP,
            "pad": "0.3",
            "dpi": str(DPI),
        },
    )
    g.node("matrix", label=table_html, shape="none", margin="0")

    png_bytes = g.pipe(format="png")
    with open(out_path, "wb") as f:
        f.write(png_bytes)
    if _HAS_PIL:
        return _PILImage.open(out_path).size
    return (0, 0)


# ════════════════════════════════════════════════════════════════
# Excel 埋め込みヘルパー
# ════════════════════════════════════════════════════════════════

def embed_image_in_sheet(ws, img_path: str, anchor_row: int, anchor_col: int = 2,
                         max_width_px: int = 1200, dpi: int = DPI) -> int:
    """
    PNG をワークシートに埋め込み、画像の高さに合わせた行数を返す。

    anchor_row: 画像を配置する開始行
    anchor_col: 画像を配置する開始列（デフォルト=2）
    戻り値: 画像が占める行数（行高 20pt 換算）
    """
    from openpyxl.drawing.image import Image as XLImage
    from openpyxl.utils import get_column_letter

    if not _HAS_PIL:
        raise RuntimeError("Pillow が必要です")

    img = _PILImage.open(img_path)
    w_px, h_px = img.size

    # 最大幅に合わせてスケール
    scale = min(1.0, max_width_px / w_px)
    display_w = int(w_px * scale)
    display_h = int(h_px * scale)

    xl_img = XLImage(img_path)
    # EMU: 1pt = 12700 EMU, 1px@96dpi ≈ 9525 EMU
    emu_per_px = 914400 / dpi
    xl_img.width  = int(display_w * emu_per_px / 9525)
    xl_img.height = int(display_h * emu_per_px / 9525)
    xl_img.anchor = f"{get_column_letter(anchor_col)}{anchor_row}"

    ws.add_image(xl_img)

    # 行高を調整（画像高さに合わせて必要行数を確保）
    pt_per_row = 20
    pt_total   = display_h * 0.75  # px → pt 概算
    n_rows     = max(1, int(pt_total / pt_per_row) + 1)
    for r in range(anchor_row, anchor_row + n_rows):
        ws.row_dimensions[r].height = pt_per_row

    return n_rows
