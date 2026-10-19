# mac-disk-hygiene

一份**持续更新**的 macOS 磁盘清理与「防止存储无序膨胀」方法合集，面向同时跑着很多开发项目、很多 AI 编程会话（Claude Code / Codex 等）的开发者 Mac。

核心立场只有一句话：**先看清、再确认、后清理；只清能证明可再生的东西，登录态和用户数据一律不碰。**

## 适合谁

- 硬盘 500 GB 左右，却总是只剩个位数 GB；
- 每天清一点、第二天又满；
- 机器上有几十个 git worktree、多个 Chrome 个人资料、多个 AI 会话同时在写文件；
- 吃过「清理工具一键清完，结果登录全掉 / 项目编不过」的亏。

## 目录

| 文档 | 内容 |
|---|---|
| [01 先看清空间去哪了](docs/01-diagnose.md) | APFS 各卷、swap、系统资产、模拟器、主目录分层测量 |
| [02 安全清理方法](docs/02-safe-cleanup.md) | 包管理器缓存、构建产物、旧安装包、废纸篓流程，每一项的正确命令 |
| [03 Chrome 不掉登录的瘦身法](docs/03-chrome.md) | Chrome 里到底是什么、哪些能清、为什么以前会掉登录 |
| [04 git worktree 收纳规则](docs/04-git-worktree.md) | 6 条核对规则、只允许的收法、托管 worktree 的特殊处理 |
| [05 多会话 / 多 Agent 协作清理](docs/05-multi-agent.md) | 让「负责的会话」自己核对自己收，以及如何确认对方真的执行了 |
| [06 防止无序扩张的规则](docs/06-prevention.md) | 可以直接放进 AGENTS.md / CLAUDE.md 的约束 |
| [07 定期体检](docs/07-checkup.md) | 只读体检脚本的用法和建议频率 |
| [08 踩过的坑](docs/08-pitfalls.md) | 每一条都来自真实翻车 |

脚本与模板：

- [`scripts/disk-report.sh`](scripts/disk-report.sh)：**只读**体检报告，不删任何东西。
- [`templates/worktree-review-checklist.md`](templates/worktree-review-checklist.md)：发给项目负责人 / 负责会话的核对清单模板。
- [`templates/agent-disk-rules.md`](templates/agent-disk-rules.md)：给 AI 编程助手的磁盘卫生规则，可直接引用。

## 快速开始

```bash
git clone https://github.com/Ericgood/mac-disk-hygiene.git
cd mac-disk-hygiene
bash scripts/disk-report.sh            # 默认扫描 $HOME
bash scripts/disk-report.sh ~/code     # 只扫某个代码根目录
```

报告会列出：各卷占用、swap、主目录大项、包管理器缓存、所有 git worktree 及其状态、超过 N 天未动的依赖目录、安装包目录里的包数量。**它只读，不清理。** 看完报告再按 [02](docs/02-safe-cleanup.md) 和 [04](docs/04-git-worktree.md) 逐项处理。

## 一张图记住分档

| 档 | 例子 | 怎么处理 |
|---|---|---|
| A 可直接清 | 包管理器下载缓存、长期没动的项目里的 `node_modules`/`target`/`.next`、旧安装包（保留最新 3 个） | 用官方命令，或先移废纸篓 |
| B 先问负责人 | 还挂在某个会话 / 某条分支下的 worktree、实验数据目录、固件构建目录 | 发核对清单，负责人确认后由负责人自己收 |
| C 只能本人决定 | 聊天软件的媒体文件、AI 会话历史、浏览器个人资料 | 用该 App 自带的清理入口 |
| 永远不动 | 浏览器登录态（Cookie/Local Storage/IndexedDB）、钥匙串、配置与凭据、正在开发的源码和未提交改动、构建链需要的模拟器 | — |

## 贡献

欢迎提 Issue / PR 补充新的「行之有效」的方法或新的坑。要求：

1. 写清楚**为什么安全**（清掉的东西能怎样重新生成）；
2. 写清楚**怎么验证**清对了；
3. 不要提交任何个人路径、账号、邮箱、项目名。

更新记录见 [CHANGELOG.md](CHANGELOG.md)。

## License

[MIT](LICENSE)
