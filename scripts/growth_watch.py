#!/usr/bin/env python3
"""Read-only disk growth watcher.

Every run: measures free space, swap and the size of a fixed allowlist of
directories, saves a snapshot, compares it with the previous run and with the
snapshot closest to 24 hours ago, writes a Markdown report and, when a
threshold is crossed, shows a macOS notification.

It never deletes, moves or modifies anything outside its own data folder.
It deliberately does not scan locations that need extra macOS privacy
permissions (other apps' containers, Desktop, Documents, Downloads, Mail,
Messages, iPhone backups) so that it never triggers permission prompts.
Growth there shows up as "unexplained" (free-space drop not covered by the
measured directories).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

HOME = Path.home()
DATA_DIR = Path(os.environ.get("GROWTH_WATCH_DIR", HOME / ".local" / "state" / "growth-watch"))
SNAP_DIR = DATA_DIR / "snapshots"
REPORT = DATA_DIR / "最新报告.md"
ALERT_LOG = DATA_DIR / "alerts.log"

KEEP_DAYS = 14
FREE_ALERT_GB = 20.0          # alert when free space falls below this
DROP_ALERT_GB = 5.0           # alert when free space drops this much since the previous run
DIR_GROWTH_ALERT_GB = 3.0     # alert when one directory grows this much within ~24 h
REPORT_TOP = 15
MIN_REPORT_KB = 10 * 1024     # ignore changes smaller than 10 MB in the report

# Home entries never scanned (privacy-protected or handled elsewhere).
HOME_SKIP = {"Library", "Desktop", "Documents", "Downloads", "Movies", "Music",
             "Pictures", "Public", ".Trash", "Applications"}
# Application Support entries never scanned (Apple privacy-protected data).
APPSUPPORT_SKIP_PREFIX = ("com.apple.",)
APPSUPPORT_SKIP = {"AddressBook", "CallHistoryDB", "CallHistoryTransactions", "Knowledge",
                   "FaceTime", "MobileSync", "CloudDocs", "iCloud", "Safari", "Messages",
                   "FileProvider", "Accounts", "DifferentialPrivacy"}

# (parent directory, depth-1 children to measure)
EXPAND = [
    HOME / ".codex",
    HOME / ".claude",
    HOME / ".local" / "share",
    HOME / ".cache",
    HOME / "Library" / "Caches",
    HOME / "Library" / "Developer" / "Xcode",
]
# Single directories measured as a whole.
SINGLE = [
    HOME / "Library" / "HarmonyOS",
    HOME / "Library" / "Android",
    HOME / "Library" / "pnpm",
    HOME / "Library" / "Containers" / "com.apple.CoreDevice.CoreDeviceService",
]


def run(cmd: list[str]) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=1800).stdout


def du_kb(path: Path) -> int | None:
    out = run(["nice", "-n", "19", "du", "-skx", str(path)])
    try:
        return int(out.split()[0])
    except (IndexError, ValueError):
        return None


def free_kb() -> int:
    line = run(["df", "-k", "/System/Volumes/Data"]).strip().splitlines()[-1].split()
    return int(line[3])


def swap_mb() -> float | None:
    out = run(["sysctl", "-n", "vm.swapusage"])
    for part in out.split("  "):
        if part.strip().startswith("used"):
            return float(part.split("=")[1].strip().rstrip("M"))
    return None


def children(parent: Path) -> list[Path]:
    try:
        return [p for p in parent.iterdir() if not p.is_symlink()]
    except OSError:
        return []


def targets() -> list[Path]:
    paths = [p for p in children(HOME) if p.name not in HOME_SKIP]
    appsupport = HOME / "Library" / "Application Support"
    paths += [p for p in children(appsupport)
              if p.name not in APPSUPPORT_SKIP and not p.name.startswith(APPSUPPORT_SKIP_PREFIX)]
    for parent in EXPAND:
        paths += children(parent)
    paths += [p for p in SINGLE if p.exists()]
    return sorted(set(paths))


def take_snapshot() -> dict:
    sizes = {}
    for p in targets():
        kb = du_kb(p)
        if kb is not None:
            sizes[str(p).replace(str(HOME), "~", 1)] = kb
    return {"time": datetime.now().isoformat(timespec="seconds"),
            "free_kb": free_kb(), "swap_mb": swap_mb(), "sizes": sizes}


def load_snapshots() -> list[dict]:
    snaps = []
    for f in sorted(SNAP_DIR.glob("*.json")):
        try:
            snaps.append(json.loads(f.read_text()))
        except (OSError, ValueError):
            continue
    return snaps


def closest(snaps: list[dict], target_time: datetime) -> dict | None:
    best = None
    for s in snaps:
        t = datetime.fromisoformat(s["time"])
        if best is None or abs(t - target_time) < abs(datetime.fromisoformat(best["time"]) - target_time):
            best = s
    return best


def growth(old: dict, new: dict) -> list[tuple[int, str, int]]:
    rows = []
    for path, kb in new["sizes"].items():
        delta = kb - old["sizes"].get(path, 0)
        if delta != 0:
            rows.append((delta, path, kb))
    return sorted(rows, reverse=True)


def gb(kb: float) -> float:
    return kb / 1048576


def notify(title: str, message: str) -> None:
    script = f'display notification {json.dumps(message)} with title {json.dumps(title)}'
    subprocess.run(["osascript", "-e", script], capture_output=True)
    with ALERT_LOG.open("a") as fh:
        fh.write(f"{datetime.now().isoformat(timespec='seconds')} {title}: {message}\n")


def section(lines: list[str], title: str, old: dict, new: dict) -> tuple[list, float]:
    lines.append(f"\n## {title}（对比 {old['time']}）\n")
    free_delta = gb(new["free_kb"] - old["free_kb"])
    rows = growth(old, new)
    measured = gb(sum(d for d, _, _ in rows))
    lines.append(f"- 可用空间变化：{free_delta:+.2f} GB")
    lines.append(f"- 已统计目录合计变化：{measured:+.2f} GB")
    lines.append(f"- 未统计区域（App 容器、系统、swap 等）大约：{-free_delta - measured:+.2f} GB\n")
    lines.append("| 变化 | 现在 | 目录 |")
    lines.append("|---|---|---|")
    for delta, path, kb in [r for r in rows if r[0] >= MIN_REPORT_KB][:REPORT_TOP]:
        lines.append(f"| +{gb(delta):.2f} GB | {gb(kb):.2f} GB | `{path}` |")
    shrunk = [r for r in rows if r[0] <= -MIN_REPORT_KB][-5:]
    if shrunk:
        lines.append("\n变小的：" + "，".join(f"`{p}` {gb(d):.2f} GB" for d, p, _ in shrunk))
    return rows, free_delta


def main() -> int:
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    history = load_snapshots()
    snap = take_snapshot()
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    (SNAP_DIR / f"{stamp}.json").write_text(json.dumps(snap, ensure_ascii=False))

    cutoff = time.time() - KEEP_DAYS * 86400
    for f in SNAP_DIR.glob("*.json"):
        if f.stat().st_mtime < cutoff:
            f.unlink()

    lines = [f"# 空间增长报告 {snap['time']}\n",
             f"- 可用空间：**{gb(snap['free_kb']):.1f} GB**",
             f"- swap 已用：{(snap['swap_mb'] or 0) / 1024:.1f} GB",
             f"- 已统计目录数：{len(snap['sizes'])}（不含微信等 App 容器、桌面、文稿、下载）"]
    alerts = []
    free_now = gb(snap["free_kb"])
    if free_now < FREE_ALERT_GB:
        alerts.append(f"可用空间只剩 {free_now:.1f} GB")

    if history:
        _, free_delta = section(lines, "和上一次比", history[-1], snap)
        if -free_delta >= DROP_ALERT_GB:
            alerts.append(f"距上次少了 {-free_delta:.1f} GB")
        day_ago = closest(history, datetime.now() - timedelta(hours=24))
        if day_ago is not None and day_ago is not history[-1]:
            rows, _ = section(lines, "和约 24 小时前比", day_ago, snap)
            big = [(d, p) for d, p, _ in rows if gb(d) >= DIR_GROWTH_ALERT_GB]
            alerts += [f"{p} 一天涨了 {gb(d):.1f} GB" for d, p in big[:3]]
    else:
        lines.append("\n首次运行，已建立基线；下次运行起开始对比。")

    if alerts:
        lines.insert(1, "\n> ⚠️ " + "；".join(alerts) + "\n")
        notify("磁盘空间提醒", "；".join(alerts)[:200])
    REPORT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
