// =============================================================================
// pre-operation.js — Claude Code PreToolUse hook
//
// 2つの保護レイヤを提供する:
//
// (1) 本番組織へのコマンド: ハードブロック（permissionDecision: deny）
//     sf project deploy / data ops / apex run / package / org delete を
//     --target-org *prod* / *production* で実行しようとするとブロック。
//
// (2) G:\共有ドライブ（Google Drive マウント）への破壊的操作: ハードブロック
//     Bash: rm / rmdir / del / mv / cp -f / > リダイレクト等の破壊的コマンドを検出
//     Write / Edit / MultiEdit: file_path が共有ドライブ配下なら一律ブロック
// =============================================================================

let buf = '';
process.stdin.on('data', c => buf += c);
process.stdin.on('end', () => {
  let d;
  try {
    d = JSON.parse(buf);
  } catch (e) {
    // パース失敗時は通過させる（hook エラーで全操作ブロックを避ける）
    return;
  }

  const toolName = d.tool_name || '';
  const input = d.tool_input || {};

  // ---- Check 1: 本番組織コマンドのハードブロック（Bash のみ） ----
  if (toolName === 'Bash') {
    const command = input.command || '';
    const segs = command.split(/&&|\|\||;/);
    const prodBlocked = segs.some(s => {
      const t = s.trim();
      return /^sf\s+(project\s+deploy|data\s+(upsert|delete|update|create|import|bulk)|apex\s+run|package\s+(install|uninstall)|org\s+delete)/i.test(t)
          && /--target-org\s+\S*(prod|production)/i.test(t);
    });
    if (prodBlocked) {
      console.log(JSON.stringify({
        hookSpecificOutput: {
          hookEventName: 'PreToolUse',
          permissionDecision: 'deny',
          permissionDecisionReason: '[HARD-BLOCK] 本番組織への変更操作はブロックされています。'
        }
      }));
      return;
    }
  }

  // ---- Check 2: G:\共有ドライブ への破壊的操作のハードブロック ----
  // 検出パターン: G:\共有ドライブ\... / G:\Shared drives\... （大小文字・スラッシュ両対応）
  const sharedDriveRe = /g:[\\\/](?:共有ドライブ|shared\s+drives)[\\\/]/i;

  if (toolName === 'Bash') {
    const command = input.command || '';
    if (sharedDriveRe.test(command)) {
      // rm / rmdir / del / mv / > リダイレクト 等の破壊的パターン
      const destructiveRe = /\b(rm|rmdir|del|erase|mv|truncate)\b|Remove-Item|Move-Item|Copy-Item\s.*-[Ff]orce|\bcp\s.*-[fF]\b|copy\s+\/[Yy]|\bsed\s.*-i\b|\bawk\s.*-i\s+inplace\b|>[^=]|>>/i;
      if (destructiveRe.test(command)) {
        console.log(JSON.stringify({
          hookSpecificOutput: {
            hookEventName: 'PreToolUse',
            permissionDecision: 'deny',
            permissionDecisionReason: '[HARD-BLOCK] G:\\共有ドライブ への破壊的操作はブロックされています。\n対象コマンド: ' + command
          }
        }));
        return;
      }
    }
  } else if (toolName === 'Write' || toolName === 'Edit' || toolName === 'MultiEdit') {
    const filePath = input.file_path || '';
    if (sharedDriveRe.test(filePath)) {
      console.log(JSON.stringify({
        hookSpecificOutput: {
          hookEventName: 'PreToolUse',
          permissionDecision: 'deny',
          permissionDecisionReason: '[HARD-BLOCK] G:\\共有ドライブ への書き込み操作はブロックされています。\n対象パス: ' + filePath
        }
      }));
      return;
    }
  }
});
