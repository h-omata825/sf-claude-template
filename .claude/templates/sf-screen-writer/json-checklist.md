# Phase 1.5: 生成 JSON のセルフレビューチェックリスト

- [ ] **usecases の網羅性**: JS のイベントハンドラーを全て usecase 化したか
- [ ] **items の網羅性**: html の全フォームフィールド・ボタンを items に記載したか
- [ ] **決定木の適用漏れ**: usecase 内 steps に Q1〜Q5 を適用したか
- [ ] **エラー処理の位置**: メインフローの末尾に独立したエラーステップが置かれていないか。エラー処理は必ず decision の branch に
- [ ] **calls フィールドの網羅性**: スケルトン JSON の `_parser_meta.apex_imports` に記録された全 Apex 呼び出しが、いずれかの usecase の steps に `calls` として存在するか
- [ ] **コントローラー呼び出しの記述**: Apex コントローラー呼び出しは `calls` + 高レベル `detail` になっているか。コントローラー内部実装を記述していないか
- [ ] **モーダル吸収**: `absorb_into` の feature のソースを読んで usecases に展開したか
- [ ] **overview の品質**: 具体的な操作・連携 Apex・オブジェクト名が含まれているか
- [ ] **type フィールドの正確性**: `"LWC"` / `"画面フロー"` / `"Aura"` / `"Visualforce"` のいずれかになっているか
- [ ] **business_context の網羅**: 各画面コンポーネントに「業務上の役割を2〜3文」で記述しているか（品質基準準拠）
- [ ] **apex_calls の網羅**: 画面が呼ぶ全 Apex メソッドを `[{name, operation: "@wire|imperative", trigger, note}]` 形式で列挙しているか（漏れなし）
- [ ] **events の網羅**: 画面で扱う全イベント（onclick / dispatch 等）を `[{event, element, handler, description, note}]` 形式で列挙しているか
