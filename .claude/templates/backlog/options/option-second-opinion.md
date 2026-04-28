# option-second-opinion

## 何をするか

parent の調査結果に引きずられない独立した原因仮説を立てる（blind second opinion）。subagent として実行することで parent context の先入観を排除する。

## 実行手順（subagent 化必須）

**このオプションは必ず `backlog-blind-second-opinion` subagent を Task ツールで起動して実行する。parent 内で直接実行してはならない（blind 性が崩れる）。**

subagent への引き渡し情報:
1. 課題 ID（Backlog issue key）
2. 課題本文の全文
3. 全コメントのテキスト
4. 関連コンポーネントのファイルパス一覧（コード内容は渡さない）
5. 以下を明示する: 「parent の調査結果・仮説は一切伝えない。あなたはこの情報だけで独立に原因仮説を立ててください」

subagent が返す内容:
- 原因仮説 3 件以上（根拠・尤度付き）
- parent の仮説と相違があれば「blind 差異」として明記

## 出力

investigation.md に追記:

## blind second-opinion 結果

| 仮説 # | 原因 | 根拠 | 推定尤度 | parent 仮説との差異 |
|---|---|---|---|---|
| 1 | ... | ... | 高/中/低 | 一致 / 相違（詳細: ...） |
