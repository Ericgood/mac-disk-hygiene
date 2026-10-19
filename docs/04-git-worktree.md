# 04 git worktree 收纳规则

AI 编程助手很爱开 worktree：每个任务一个，每个都装一份 `node_modules`、跑一次构建。几周下来几十个副本、几十 GB 很常见。但 worktree 里也最容易藏着**只存在本地**的东西，收错一个就是真丢数据。

## 1. 6 条核对规则（任何一条不满足就保留）

1. **没人在用**：没有会话把它当工作目录，没有进程占用。
   ```bash
   lsof +D <worktree> 2>/dev/null | head
   ```
2. **没有未提交内容**：
   ```bash
   git -C <worktree> status --porcelain --untracked-files=all
   ```
   必须为空。注意要加 `--untracked-files=all`，否则未跟踪的目录只显示成一行，容易看漏。
3. **提交都在远端**：
   ```bash
   git -C <worktree> branch -r --contains HEAD
   ```
   有输出才算。没有的话再看内容是否以 cherry-pick 方式进了主线：`git cherry origin/main HEAD` 全是 `-` 才算。
4. **没有本地独有材料**：这是最容易漏的一条。`git status` 默认**不显示被忽略的文件**，而 `.env`、凭据、签名文件、日志、验收截图恰恰都在 `.gitignore` 里。
   ```bash
   git -C <worktree> status --porcelain --ignored | grep '^!!'
   ```
   去掉可再生的（`node_modules`、`.next`、`.turbo`、`.ruff_cache`、`.mypy_cache`、`__pycache__`、`build`、`dist`、`target`、`tsconfig.tsbuildinfo`、`next-env.d.ts` 等），剩下的一律视为本地独有材料：先确认已另存或确实不需要，拿不准就保留。
5. **没有被引用**：交接文档、构建脚本、其他 worktree 的软链接没有指向这个路径（例如某个固件构建脚本把 SDK 软链到另一个 worktree 里）。
6. **近期没活动**：最近 3 天内有文件改动的，视为活跃，保留。
   ```bash
   find <worktree> -not -path '*/node_modules/*' -not -path '*/.git/*' -type f -newermt "$(date -v-3d +%F)" | head -1
   ```

**不确定就保留。**

## 2. 只允许的收法

| 类型 | 怎么收 |
|---|---|
| 手建 worktree | `git worktree remove <路径>`，**不带** `--force` |
| AI 工具托管的 worktree（如 `~/.codex/worktrees/...`、`<repo>/.claude/worktrees/...`） | 优先用该工具自己的流程（归档会话 / 删除 worktree）；工具没提供时，才用不带 `--force` 的 `git worktree remove` |

禁止：

- `rm -rf` 删 worktree 目录；
- `git worktree remove --force`；
- 用「移废纸篓 + `git worktree prune`」代替 `git worktree remove`；
- 删分支、改远端、动主工作区。

`git worktree remove` 本身就是一道保险：工作区有修改或未跟踪文件时它会拒绝执行。被忽略的文件它会一并删除，所以第 4 条必须事先查。

**分支保留**：收掉 worktree 不删分支，以后需要时 `git worktree add <路径> <分支>` 随时能重新检出。

## 3. 托管 worktree 的一个坑

有的 AI 编程 App 归档会话时，只把 worktree 切成 detached HEAD，并不删除目录；App 自己也不认为留下了东西，它的「丢弃保留副本」功能会报告无事可做。这时：

1. 再按第 1 节核对一遍（尤其确认没有进程占用、没有未提交内容）；
2. 用不带 `--force` 的 `git worktree remove` 收掉；
3. 确认分支仍在：`git branch --list <分支名>`。

## 4. 收之前留底

每收一个，记一行审计：

```json
{"time":"…","path":"…","branch":"…","head":"<sha>","kb":123456,"status":"removed","branch_kept":"yes"}
```

有了 `head` 和分支，任何时候都能恢复同样的工作区。

## 5. 限额

每个仓库同时最多 3 个活跃 worktree；任务合并或放弃后，由**开它的那个会话**负责收掉。见 [06 防止无序扩张](06-prevention.md)。
