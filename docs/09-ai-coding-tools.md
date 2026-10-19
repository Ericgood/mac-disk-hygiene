# 09 AI 编程工具的长期卫生（Claude Code / Codex）

AI 编程工具用久了，会在三个地方悄悄长大：**对话记录**、**托管的 worktree**、**单个超长对话本身**。前两个占磁盘，第三个让对话越来越容易丢细节、跨会话协作也更容易出错。预防比事后补救便宜得多。

## 1. 先量一下

```bash
# Claude Code
du -sh ~/.claude/projects                              # 对话记录（按项目分目录，未压缩 .jsonl）
find ~/.claude/projects -name '*.jsonl' -size +100M -exec ls -lh {} \; | sort -k5 -h | tail
find ~ -maxdepth 4 -type d -path '*/.claude/worktrees' -exec du -sh {} \; 2>/dev/null

# Codex
du -sh ~/.codex/sessions ~/.codex/archived_sessions ~/.codex/worktrees
find ~/.codex/sessions -name '*.jsonl' -size +200M | wc -l    # 还没压缩的大对话
```

经验数字：

- Codex 会把空闲 / 归档的对话压缩成 `.jsonl.zst`，体积降一个数量级；**还在用的超长对话**是未压缩的，单个可以到 2–3 GB。
- Claude Code 的对话记录不压缩，单个长对话常见几百 MB。

## 2. 对话记录：靠工具自己的保留机制，不手删

- **Codex**：在 App 里把已经换新的老对话「归档」，它会压缩；不要手删 `~/.codex/sessions`。
- **Claude Code**：`~/.claude/settings.json` 里的 `cleanupPeriodDays` 控制多久没活动的对话在启动时被清掉（不设时有默认值）。想长期保留历史就显式设一个更大的值；磁盘紧张就设小一点。**这是一个取舍，由本人决定**，不要替用户改。

## 3. 托管 worktree：用 App 的生命周期设置

Claude 桌面版（Code 标签页）有两项设置，可以让 worktree 不再无限堆积：

| 设置 | 作用 | 建议 |
|---|---|---|
| PR 关闭时自动归档会话 | PR 合并或关闭后归档会话，同时收掉它的 worktree | 打开 |
| 归档不活跃的会话（天数） | N 天没有活动的会话自动归档；有未提交改动的 worktree 会保留 | 14 或 30 天 |

另外「设置 › 本机 › 存储」里可以看到 worktree、对话记录、缓存各占多少，并可按 30/60/90 天清理不活跃会话的 worktree。

注意：归档有时只把 worktree 切成 detached HEAD 而不删目录，见 [04](04-git-worktree.md#3-托管-worktree-的一个坑)。

## 4. 超长对话：自动提醒「写交接、开新对话」

单个对话被自动压缩（compaction）两三次以后，早期的细节就开始丢。与其等出错，不如用钩子在第 2 次压缩后自动提醒。

Claude Code 的 `SessionStart` 钩子在压缩后会以 `source: "compact"` 再触发一次，而且它的标准输出会进入模型上下文，所以可以用它来计数并提醒：

```js
// ~/.claude/hooks/compaction-handoff.js（示意）
const fs = require('fs'), path = require('path'), os = require('os');
let raw = ''; process.stdin.on('data', c => raw += c); process.stdin.on('end', () => {
  const input = (() => { try { return JSON.parse(raw); } catch { return {}; } })();
  if (input.source !== 'compact' || !input.session_id) return;
  const file = path.join(os.homedir(), '.claude', 'compaction-counts.json');
  const counts = (() => { try { return JSON.parse(fs.readFileSync(file, 'utf8')); } catch { return {}; } })();
  const count = ((counts[input.session_id] || {}).count || 0) + 1;
  fs.writeFileSync(file, JSON.stringify({ ...counts, [input.session_id]: { count, last: new Date().toISOString() } }));
  if (count >= 2) {
    console.log(`[对话长度提醒] 本对话已压缩 ${count} 次。当前这一步收尾时：` +
      '把交接写进项目文档（目标、进度、下一步、坑、相关分支/worktree/产物、待决定事项），' +
      '再提醒用户开新对话并给出第一句话。不要打断正在进行的操作。');
  }
});
```

在 `~/.claude/settings.json` 注册：

```json
{ "hooks": { "SessionStart": [ { "matcher": "compact",
  "hooks": [ { "type": "command", "command": "node ~/.claude/hooks/compaction-handoff.js" } ] } ] } }
```

Codex 没有同等的钩子时，就把同样的要求写进 `AGENTS.md`（见 [`templates/agent-disk-rules.md`](../templates/agent-disk-rules.md) 第 8 条）。

## 5. 会话启动时注入「上次摘要」的坑

有些钩子套件会在每次启动时，把「最近一次会话的摘要」注入上下文。如果它只按修改时间取最新文件、不区分项目，**A 项目的新对话会被塞进 B 项目的进度**，模型可能据此做出完全无关的判断。

修法：摘要文件名里带上项目标识，启动时只注入同一项目的摘要；压缩后（`source: "compact"`）是同一个对话在继续，不要再注入任何「上次摘要」。

## 6. 跨会话消息：送达 ≠ 执行

用跨会话工具给另一个 AI 会话派活时，务必回头看对方的会话记录确认它真的开始做了。详见 [05](05-multi-agent.md#3-送达不等于执行了)。

## 7. 一页检查清单

- [ ] 每周看一次 `~/.claude/projects`、`~/.codex/sessions` 的体积和最大的几个对话；
- [ ] 已换新的老对话在 App 里归档；
- [ ] 打开「PR 关闭自动归档」，设置「不活跃 N 天自动归档」；
- [ ] 第 2 次压缩后自动提醒写交接、开新对话；
- [ ] 启动摘要只注入同一项目的；
- [ ] 派给其他会话的活，确认对方真的开始执行。
