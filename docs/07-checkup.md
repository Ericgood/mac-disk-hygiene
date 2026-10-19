# 07 定期体检

清理最怕「平时不管，满了才救火」。建议每周跑一次只读体检，先看报告、本人确认、再动手。

## 用法

```bash
bash scripts/disk-report.sh                 # 扫描 $HOME
bash scripts/disk-report.sh ~/code ~/work   # 只扫指定代码根目录
STALE_DAYS=30 bash scripts/disk-report.sh   # 依赖目录「多久没动算陈旧」，默认 14 天
KEEP_PACKAGES=3 bash scripts/disk-report.sh # 安装包目录保留数，默认 3
```

脚本**只读**：只用 `df`、`du`、`find`、`git status`、`git worktree list` 这类命令，不删、不移、不改任何文件。所有 git 命令都带 `GIT_OPTIONAL_LOCKS=0`，避免顺手刷新 `.git/index`。

## 报告内容

1. **磁盘与 swap**：Data 卷已用 / 可用、swap 用量。
2. **主目录大项**：前 15 个最大的目录。
3. **包管理器缓存**：npm、pnpm、pip、uv、Homebrew、Gradle 缓存各多大，附对应官方清理命令。
4. **git worktree 盘点**：扫描路径下所有仓库的 worktree，每个显示大小、分支、是否有未提交改动、HEAD 是否在远端、最近修改时间。
5. **陈旧依赖目录**：超过 `STALE_DAYS` 天未改动的项目里的 `node_modules`、`target`、`.next`、`build`、`.venv`。
6. **安装包目录**：`dist/` 里 `.apk/.aab/.ipa/.dmg/.zip` 超过 `KEEP_PACKAGES` 个的目录。

## 建议节奏

| 频率 | 做什么 |
|---|---|
| 每周 | 跑体检；清包管理器缓存；处理超额的安装包目录 |
| 每个任务结束 | 收掉本任务开的 worktree，清本任务的 `.localtmp/` |
| 每月 | 浏览器各个人资料只清缓存；检查扩展；聊天软件清 3 个月前的视频和文件 |
| 每个大阶段结束 | 长对话换新，旧对话归档 |

## 定时运行（可选）

用 launchd 每周一早上生成报告到文件，而不是自动清理：

```xml
<!-- ~/Library/LaunchAgents/local.disk-report.plist -->
<plist version="1.0"><dict>
  <key>Label</key><string>local.disk-report</string>
  <key>ProgramArguments</key><array>
    <string>/bin/bash</string>
    <string>-c</string>
    <string>bash /path/to/mac-disk-hygiene/scripts/disk-report.sh > "$HOME/Desktop/disk-report-$(date +%F).txt" 2>&1</string>
  </array>
  <key>StartCalendarInterval</key><dict>
    <key>Weekday</key><integer>1</integer><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer>
  </dict>
</dict></plist>
```

```bash
launchctl load ~/Library/LaunchAgents/local.disk-report.plist
```

**不要**把「自动删除」放进定时任务。清理永远需要本人看过报告再确认。
