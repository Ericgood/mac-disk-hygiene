# Changelog

## 2026-10-27 — Xcode 构建目录与占用检查

- 02：用 `info.plist` 的 `WorkspacePath` 判断 DerivedData 是否已无人使用。
- 08 新增两条：`lsof +D` 会把检查者自己算成占用；每次构建换新 `-derivedDataPath` 导致旧目录堆积。

## 2026-10-21 — 增长监控

- 新增 `scripts/growth_watch.py`：只读增长监控，快照对比 + 超阈值 macOS 通知，避开隐私受保护目录；07 补充 launchd 用法；08 新增「缓存会再生」一条。

## 2026-10-20 — AI 编程工具卫生

- 新增 [09 AI 编程工具的长期卫生](docs/09-ai-coding-tools.md)：Claude Code / Codex 对话记录与托管 worktree 的保留机制、第 2 次压缩后自动提醒写交接的钩子示例、启动摘要跨项目串台的坑。

## 2026-10-20 — 初版

- 方法文档 01–08：诊断、安全清理、Chrome 不掉登录、git worktree 收纳规则、多会话协作清理、防膨胀规则、定期体检、踩过的坑。
- `scripts/disk-report.sh`：只读体检报告（磁盘与 swap、大目录、包管理器缓存、worktree 状态、陈旧依赖、超额安装包目录）。
- 模板：worktree 核对清单、给 AI 编程助手的磁盘卫生规则。
