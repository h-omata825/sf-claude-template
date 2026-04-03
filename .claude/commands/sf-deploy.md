salesforce-devエージェントとして、以下のデプロイ作業を支援してください。

## デプロイ対象・環境
$ARGUMENTS

## デプロイ前チェックリスト

### コード品質確認
- [ ] コードレビュー完了
- [ ] テストカバレッジ 75%以上（目標 90%以上）
- [ ] ローカルでのテスト実行確認

### Sandbox検証
- [ ] デプロイ対象のSandboxへの検証デプロイ完了
- [ ] Sandboxでの動作確認完了
- [ ] 関連機能のデグレ確認完了

### package.xmlの確認
- [ ] デプロイ対象コンポーネントが全て含まれているか
- [ ] 削除対象がある場合 `destructiveChanges.xml` を準備済みか
- [ ] 依存関係の順序が正しいか

### 本番デプロイ前
- [ ] リリース承認取得済み
- [ ] バックアップ / ロールバック手順の準備
- [ ] デプロイ実施時間の調整（業務時間外推奨）
- [ ] 関係者への事前連絡完了

## SF CLIコマンド参考

```bash
# 検証のみ（本番デプロイ前に必ず実施）
sf project deploy validate --manifest manifest/package.xml --target-org <alias> --test-level RunLocalTests

# 実デプロイ
sf project deploy start --manifest manifest/package.xml --target-org <alias> --test-level RunLocalTests

# デプロイ状況確認
sf project deploy report --job-id <id>

# テストのみ実行
sf apex run test --target-org <alias> --test-level RunLocalTests --result-format human
```

## 注意事項
- **本番環境へのデプロイは必ずユーザーの確認を取ってから実行する**
- 検証（validate）が成功してから実デプロイを行う
- エラーが発生した場合はロールバック手順を確認してから対処する
