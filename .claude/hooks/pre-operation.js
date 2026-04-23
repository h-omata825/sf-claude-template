// =============================================================================
// pre-operation.js — Claude Code PreToolUse hook
//
// 2つの保護レイヤを提供する:
//
// (1) 本番組織へのコマンド: ハードブロック（permissionDecision: deny）
//     sf project deploy / data ops / apex run / package / org delete を
//     --target-org *prod* / *production* で実行しようとするとブロック。
//
// (2) 共有フォルダ（UNCパス \\server\...）操作: 警告 + 会話承認
//     Bash / Write / Edit で UNC パスが検出されると deny を返し、
//     Claude がユーザーに自然言語で確認するよう指示するメッセージを返す。
//     ユーザーが OK を出したら、コマンドの先頭に APPROVED_SHARED=1 を付けて
//     再実行することで通過できる。
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

  // ---- 操作テキストの抽出 ----
  let textToCheck = '';
  if (toolName === 'Bash') {
    textToCheck = input.command || '';
  } else if (toolName === 'Write' || toolName === 'Edit' || toolName === 'MultiEdit') {
    textToCheck = input.file_path || '';
  } else {
    return;
  }

  // ---- Check 1: 本番組織コマンドのハードブロック（Bash のみ） ----
  if (toolName === 'Bash') {
    const segs = textToCheck.split(/&&|\|\||;/);
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

  // ---- Check 2: 共有フォルダ（UNCパス）への操作 ----
  // 検出条件:
  //   - Windows UNC: \\server\share\... （コマンド内に \\ が含まれる）
  //   - POSIX UNC風: //server/share/... （先頭または空白の後の //）
  const hasUncBackslash = textToCheck.indexOf('\\\\') !== -1;
  const hasUncForwardslash = /(?:^|[\s"'])\/\/[a-zA-Z0-9._-]+\/[a-zA-Z0-9._-]/.test(textToCheck);
  const hasUnc = hasUncBackslash || hasUncForwardslash;

  // 承認マーカー（Bash 用: 環境変数プレフィックス、Write/Edit 用: 承認済みフラグファイル）
  const hasBashApproval = toolName === 'Bash' && /\bAPPROVED_SHARED=1\b/.test(textToCheck);
  let hasFileApproval = false;
  if (toolName !== 'Bash') {
    try {
      const fs = require('fs');
      const os = require('os');
      const path = require('path');
      const markerPath = path.join(os.tmpdir(), 'claude-shared-approved.lock');
      if (fs.existsSync(markerPath)) {
        // 有効期限10分
        const mtime = fs.statSync(markerPath).mtime.getTime();
        if (Date.now() - mtime < 10 * 60 * 1000) {
          hasFileApproval = true;
          // 使い切り: 一度使ったら削除
          fs.unlinkSync(markerPath);
        } else {
          fs.unlinkSync(markerPath);
        }
      }
    } catch (e) {
      // 読み書き失敗は無視（承認なしとして扱う）
    }
  }

  if (hasUnc && !hasBashApproval && !hasFileApproval) {
    const opDesc = toolName === 'Bash'
      ? `Bashコマンド: ${textToCheck}`
      : `${toolName} 操作対象: ${textToCheck}`;
    const retryHint = toolName === 'Bash'
      ? 'Bashの場合: コマンドの先頭に `APPROVED_SHARED=1 ` を付けて再実行してください。\n  例: `APPROVED_SHARED=1 cp file.txt //server/share/`'
      : 'Write/Edit の場合: Claude Code のテンポラリに承認マーカーを作成してから同じツールを再実行してください。\n  例: `bash -c "touch $(node -e \\"console.log(require(\\"os\\").tmpdir())\\")/claude-shared-approved.lock"` を先に実行。\n  有効期限10分・1回使い切り。';
    const reason = [
      '[⚠️ 共有フォルダ操作の検出]',
      '',
      opDesc,
      '',
      '共有フォルダ（UNCパス）への操作は他のユーザーやネットワーク環境に影響する可能性があります。',
      '続行する前に、以下をユーザーに明示的に確認してください:',
      '  - どのパスに何の操作をするのか',
      '  - 他のユーザーへの影響範囲',
      '  - 本当に今このタイミングで実行してよいか',
      '',
      'ユーザーからの明示的なOK（「OK」「進めて」等）を受けたら、以下で再実行:',
      retryHint,
      '',
      'ユーザーがNOまたは不安を示したら、操作を中止してください。'
    ].join('\n');

    console.log(JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'PreToolUse',
        permissionDecision: 'deny',
        permissionDecisionReason: reason
      }
    }));
    return;
  }
});
