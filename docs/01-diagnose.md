# 01 先看清空间去哪了

清理之前先测量。很多「怎么清都不够」其实是没看清账本：一块 500 GB 的盘，在你动手之前就有几十 GB 是系统和工具链的固定开销。

## 1. 先看 APFS 各卷，而不是只看 Finder

```bash
df -h / /System/Volumes/Data
diskutil apfs list | grep -E "Name:|Role|Capacity Consumed"
```

一块 macOS 系统盘通常是一个 APFS 容器，里面分好几个卷，共享同一份空间：

| 卷 | 典型大小 | 说明 |
|---|---|---|
| System | ~12 GB | 只读系统，动不了 |
| Preboot | ~9 GB | 启动相关，动不了 |
| Recovery | ~3 GB | 恢复系统，动不了 |
| VM | 视 swap 而定，常见 5–25 GB | **swap 和睡眠镜像**，见下文 |
| Data | 剩下全部 | 你的所有文件、App、缓存都在这里 |

另外，如果装了 iOS 模拟器运行时，会看到一个单独挂载的「iOS xx Simulator」卷（十几 GB），它的镜像文件也占用 Data 卷空间。

## 2. swap：「空间突然没了」的隐形大头

```bash
sysctl vm.swapusage
```

内存不够时 macOS 会把内存写到磁盘上的 swap 文件。同时开着很多 IDE、AI 会话、Gradle/Kotlin 守护进程、浏览器标签时，swap 可以在一小时内涨好几个 GB。

**特征**：可用空间短时间内大幅下降，但 `du` 找不到哪个目录变大了。

**对策**：不是删文件，而是减少同时常驻的重进程（见 [06 防止无序扩张](06-prevention.md)）。重启后 swap 会归零。

## 3. 系统托管的大目录

```bash
sudo du -sh /System/Library/AssetsV2 /Library/Developer/CoreSimulator /private/var/folders 2>/dev/null
```

- `/System/Library/AssetsV2`：系统下载的资产（语言模型、字体、语音等），十几 GB 很常见，由系统管理，不要手删。
- `/Library/Developer/CoreSimulator`：模拟器运行时。**本地编译 iOS 项目时可能需要它**，见 [08 踩过的坑](08-pitfalls.md)。
- `/private/var/folders`：系统和 App 的临时目录，交给系统。

没有 `sudo` 时，Data 卷里会有几十 GB 是「看不到细节」的系统数据，这是正常的。

## 4. 主目录分层测量

```bash
cd ~
du -skx -- * .[!.]* 2>/dev/null | sort -rn | head -30 | awk '{printf "%7.1f GB  %s\n", $1/1048576, $2}'
```

然后对最大的几个往下钻一层，重点看：

```bash
du -sh ~/Library/{"Application Support",Containers,Caches,Developer}/* 2>/dev/null | sort -h | tail -20
```

开发者 Mac 上常见的大头（量级参考，不是你的数字）：

| 区域 | 常见量级 | 归类 |
|---|---|---|
| 聊天软件容器（如 `Containers/<聊天App>`） | 20–40 GB | C 档：用 App 自带清理 |
| 浏览器个人资料 + 缓存 | 10–20 GB | 见 [03 Chrome](03-chrome.md) |
| AI 编程工具目录（会话记录、托管 worktree） | 10–50 GB | B/C 档 |
| 各项目的 `node_modules` / `target` / `build` / `.next` | 几十 GB | A 档（长期不动的）/ B 档（活跃的） |
| Xcode（DerivedData、Archives、DeviceSupport） | 5–20 GB | 部分 A 档，部分要问 |
| 鸿蒙 / Android SDK、Gradle 缓存 | 5–15 GB | 工具链，谨慎 |

## 5. 找「今天突然涨的」

```bash
# 列出最近 2 小时内有写入的大目录（按需调整路径和时间）
find ~ -xdev -type f -newermt "$(date -v-2H '+%Y-%m-%dT%H:%M:%S')" -size +50M 2>/dev/null | head -50
```

构建产物（尤其 Rust 的 `target/debug`、Android 的 `build/intermediates`）可以在一天里从几 GB 涨到 20 GB。找到后**先找负责这个项目的人或会话**，而不是直接删（见 [05](05-multi-agent.md)）。

## 6. 记账

每次清理前后各记一次：

```bash
df -k /System/Volumes/Data | tail -1
sysctl vm.swapusage
```

只把「本次删除动作」带来的变化算作收益；swap 波动、后台进程写入不要算进去，否则会误判哪种方法有效。
