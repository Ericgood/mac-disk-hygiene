# 02 安全清理方法

每一项都写了：**为什么安全**、**正确命令**、**怎么验证**。原则：

- 优先用工具自己的官方清理命令，而不是 `rm -rf`；
- 按明确列出的路径逐项处理，**不做整目录扫荡**（尤其不要扫 `~/Library/Caches/*`、`~/Library/Logs/*`）；
- 需要删目录时先移到废纸篓，确认没问题再由本人清空；
- 每次动手前后记 `df`，见 [01](01-diagnose.md#6-记账)。

## 1. 包管理器下载缓存（A 档）

| 工具 | 命令 | 备注 |
|---|---|---|
| npm | `npm cache clean --force` | 只清 `~/.npm/_cacache`。**不会**动 `~/.npm/_npx`（npx 拉下来的 MCP/CLI 工具），这个目录别手删 |
| pip | `pip cache purge` | |
| pnpm | `pnpm store prune` | 只删没被任何项目引用的包 |
| Homebrew | `brew cleanup --prune=all -n` 先看，再去掉 `-n` | 注意它也会删旧版本的已安装公式 |
| uv | `uv cache prune` | |

**验证**：清理前后 `du -sh` 对应目录；`ls ~/.npm/_npx | wc -l` 前后一致。

**清理前**：确认当前没有 `npm install` / `pip install` 在跑：

```bash
pgrep -fl "npm (install|ci)|pnpm install|yarn install|pip install"
```

## 2. 构建产物

### Rust：只清 debug，不碰正在运行的 release

```bash
cd <项目>/src-tauri   # 或 Cargo.toml 所在目录
cargo clean --profile dev
```

`target/debug` 里的 `deps`、`incremental` 一天能涨十几 GB。`--profile dev` 只清 debug，`target/release` 和交叉编译目标目录不动——如果有 App 正是从 release 产物里启动的，这一点很重要。

**清理前**：`pgrep -fl "cargo|rustc"` 确认没有在编译。

### Android：只清中间产物，保留安装包和 mapping

可清：`app/build/intermediates`、`app/build/tmp`、`.gradle`（项目级）。
保留：`app/build/outputs`（APK/AAB、mapping 文件）。

活跃项目让负责人用 `./gradlew clean`；长期不动的项目可按 A 档处理。构建完不用时 `./gradlew --stop` 关掉守护进程。

### Node / Next.js

`node_modules`、`.next`、`.turbo`：**仅对 14 天以上没有提交、也没有任何文件改动的项目**直接清。判断方法：

```bash
git -C <项目> log -1 --format=%ci
find <项目> -not -path '*/node_modules/*' -not -path '*/.git/*' -type f -newermt "$(date -v-14d +%F)" | head -1
```

跳过条件（满足任一就不清）：

- 目录里有被 git 跟踪的文件（`git ls-files <目录> | head -1` 有输出）；
- 是符号链接（可能是多个副本共享的依赖）；
- 有进程正在用这个项目。

### Xcode

| 目录 | 能否清 | 说明 |
|---|---|---|
| `DerivedData/*/Index.noindex`、`SDKStatCaches.noindex`、`CompilationCache.noindex`、`Build/Intermediates.noindex/XCBuildData` | 通常可以 | 纯缓存 |
| `DerivedData/*/Build/Products`、`.dSYM` | 先问 | 可能还被后续构建、调试、符号化用到 |
| `Archives` | 先问 | 是发版存档 |
| 模拟器运行时 | **不要动** | 本地编译可能依赖，见 [08](08-pitfalls.md) |

判断 `DerivedData/<工程名>-<哈希>` 是不是没人用了：读它的 `info.plist` 里的 `WorkspacePath`（`/usr/libexec/PlistBuddy -c 'Print :WorkspacePath' info.plist`）。对应工程已经不存在，或目录很久没改动，就可以删；Xcode 正开着的工程对应的那个先别动。工程目录里自定义的 `build-*` 构建目录见 [08 第 16 条](08-pitfalls.md)。

## 3. 旧安装包：每个目录只留最新 3 个

`dist/`、`release/` 之类放安装包的目录，按修改时间只保留最新 3 个（以及对应的 mapping / 符号文件）：

```bash
cd <dist目录>
ls -t *.apk | tail -n +4          # 先看会删哪些
ls -t *.apk | tail -n +4 | while read -r f; do mv "$f" ~/.Trash/; done
```

**前提**：安装包没有被 git 跟踪（`git ls-files dist | grep -c '\.apk$'` 为 0），且当前设备上装的那个版本在保留之列。需要长期保留的发版包放 NAS 或 Release，不堆在本机。

## 4. 废纸篓流程

1. 删除动作一律先移到 `~/.Trash/<批次名>_<日期>/`，同时写一行审计记录（原路径、目标路径、字节数）；
2. 观察一段时间，确认没有项目报错；
3. **由本人**在 Finder 里清空废纸篓。

注意：**移进废纸篓不释放空间**，清空后才释放。别把「已移废纸篓」当成「已腾出空间」。

## 5. 被各 App 自己管理的大头，用 App 自带入口

| 对象 | 入口 |
|---|---|
| 浏览器 | 见 [03 Chrome](03-chrome.md) |
| 聊天软件媒体 | App 内「存储空间管理」，按时间清视频/文件 |
| 办公 / IM 客户端缓存 | App 设置里的「清除缓存」 |
| AI 编程工具的会话记录 | 在 App 里归档旧会话（多数会自动压缩空闲会话），不要手删其数据目录 |
| AI 编程工具托管的 worktree | 用 App 自己的清理 / 归档流程，见 [04](04-git-worktree.md) |

## 6. 清完怎么证明清对了

- `df` 前后对比，只记本次动作的收益；
- 被清项目里关键产物（APK、release 包、正在运行的 App）仍在；
- 相关 git 仓库 `HEAD`、分支、未提交改动不变；
- 受保护目录（浏览器、钥匙串、AI 工具配置）未被触碰。
