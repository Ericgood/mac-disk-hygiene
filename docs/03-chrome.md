# 03 Chrome 不掉登录的瘦身法

很多人不敢清 Chrome，是因为清过一次以后所有网站的登录全掉了。原因和解法都很明确：**登录状态和缓存放在完全不同的地方，只清缓存就不会掉登录。**

## 1. Chrome 里到底是什么

macOS 上 Chrome 的数据在两个地方：

```
~/Library/Application Support/Google/Chrome/   ← 个人资料（登录、扩展、设置）
~/Library/Caches/Google/Chrome/                ← 纯缓存
```

先只读量一下：

```bash
cd ~/Library/Application\ Support/Google/Chrome
du -sh -- * | sort -h | tail -15
du -sh ~/Library/Caches/Google/Chrome/* | sort -h | tail -10
```

典型构成（一台有十几个个人资料的机器上，总共约 20 GB）：

| 占用 | 典型大小 | 是什么 | 清了掉登录吗 |
|---|---|---|---|
| `~/Library/Caches/Google/Chrome/<资料>/Cache`、`Code Cache` | 合计 5–10 GB | 网页图片、脚本缓存 | **不会** |
| `OptGuideOnDeviceModel` | ~4 GB | Chrome 自动下载的本地 AI 模型 | **不会** |
| `<资料>/Extensions` | 每个资料几百 MB 到 2 GB | 扩展程序，**每个资料各装一份** | 不会，扩展要重装 |
| `<资料>/Service Worker`、`IndexedDB`、`Local Storage` | 合计 1–3 GB | 网站的离线数据和本地存储 | **会，不要碰** |
| `<资料>/Cookies`、`Login Data` | 很小 | 登录态、保存的密码 | **会，绝对不要碰** |

另外，登录 Cookie 是加密的，密钥存在钥匙串的「Chrome Safe Storage」里。钥匙串条目丢了，Cookie 也就解不开，同样表现为「全掉登录」。

## 2. 为什么以前会掉登录

常见原因：

- 用清理工具「一键清理浏览器」，它会清 Service Worker / CacheStorage / Local Storage，甚至整个个人资料目录；
- 在 Chrome 的「删除浏览数据」里顺手勾了「Cookie 及其他网站数据」；
- 删除或重置了某个个人资料；
- 动了钥匙串里的「Chrome Safe Storage」。

## 3. 安全清法（按收益排序，全部在 Chrome 里操作）

### ① 关掉设备端 AI 模型（约 4 GB）

地址栏输入（`chrome://` 地址只能粘贴，不能从外部点链接打开）：

```
chrome://settings/ai
```

找到 **On-device AI（设备端 AI）** 开关，关掉。Chrome 会删除 `OptGuideOnDeviceModel` 目录。影响：少数依赖本地模型的功能（如诈骗页面检测）不可用；以后想用再打开，会重新下载。

不同版本里这个开关可能在「AI innovations」或「System」下面；也可以在设置页顶部搜索「On-device」。确认状态：`chrome://on-device-internals`。

### ② 每个个人资料只清缓存（合计 5–10 GB）

```
chrome://settings/clearBrowserData
```

- 时间范围：**All time（时间不限）**
- **只勾**「Cached images and files（缓存的图片和文件）」
- **不要勾**「Cookies and other site data」「Browsing history」「Passwords and passkeys」「Site settings」「Hosted app data」
- 弹窗可以往下滚，确认下面的选项也都没勾，再点删除。

注意：**每个个人资料要分别清一次**。切换个人资料：点右上角头像 → 选中对应资料 → 在它的窗口里打开上面的地址。

### ③ 删掉不用的扩展

```
chrome://extensions
```

扩展是**按个人资料**安装的：在 A 资料里删扩展，不影响 B 资料里同名的扩展。删除后对应的扩展文件和扩展本地设置会被 Chrome 一并删掉。实测删一批不用的扩展，可以把所有资料的扩展总量从约 4 GB 降到约 2 GB。

### ④ 重启一次 Chrome

Chrome 更新后，旧版本的框架文件会留在 App 包里，重启后才清掉。

### ⑤（进阶，需要本人明确同意）退出 Chrome 后删缓存文件夹

如果资料太多、逐个点太累：先**完全退出 Chrome**，然后只删每个资料下的这两个文件夹：

```
~/Library/Caches/Google/Chrome/<资料>/Cache
~/Library/Caches/Google/Chrome/<资料>/Code Cache
```

它们只存网页缓存，不存任何登录信息。除此以外的任何 Chrome 目录都不要动。

## 4. 「同一个账号怎么有两个空间」

Chrome 的**个人资料（Profile）**和 **Google 账号**是两回事：

- 个人资料是电脑上一个独立的浏览器空间，各存一份自己的网站登录、扩展、缓存、标签页；
- Google 账号只是「登录进」某个空间，用来同步书签、密码等。

同一个 Google 账号可以登录进好几个个人资料（例如点过「添加 Chrome 个人资料」，或登录时 Chrome 提示「新建个人资料」并选了新建）。头像菜单里的显示格式是「Google 账号名 (个人资料名)」。

**要合并成一个时注意**：网站登录 Cookie **不会**通过 Google 同步。删掉哪个个人资料，哪个资料里登录过的网站就全掉了。稳妥做法：

1. 选定一个以后只用的资料；
2. 用到某个只在旧资料里登录着的网站时，在新资料里重新登录一次；
3. 两三周后确认旧资料里没有离不开的东西，再到头像菜单 → Manage Chrome Profiles 删除旧资料。

想先知道两个资料各自登录过哪些网站，可以**只读**对比两边 Cookie 数据库里的域名（不读值，值是加密的）：

```bash
cd ~/Library/Application\ Support/Google/Chrome
for p in "Default" "Profile 1"; do
  sqlite3 "file:$p/Cookies?mode=ro&immutable=1" \
    "select distinct ltrim(host_key,'.') from cookies" | sort > "/tmp/hosts_${p// /_}.txt"
done
comm -23 /tmp/hosts_Default.txt /tmp/hosts_Profile_1.txt   # 只在 Default 里有的网站
```

## 5. 绝对不要做

- 整目录清 `~/Library/Application Support/Google/Chrome` 或 `~/Library/Caches/Google`；
- 清 Service Worker / CacheStorage / IndexedDB / Local Storage；
- 在 Chrome 运行时改它的任何文件；
- 动钥匙串里的 Chrome 条目。
