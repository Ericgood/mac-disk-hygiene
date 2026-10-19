#!/usr/bin/env bash
# disk-report.sh — read-only disk checkup for a developer Mac.
#
# It never deletes, moves or modifies anything. It only runs df, du, find,
# sysctl and read-only git commands (with GIT_OPTIONAL_LOCKS=0 so git does not
# refresh .git/index).
#
# Usage:
#   bash scripts/disk-report.sh [ROOT ...]      # default ROOT: $HOME
# Env:
#   STALE_DAYS=14     dependency dirs untouched for this many days are "stale"
#   KEEP_PACKAGES=3   package dirs holding more than this many installers are flagged
#   MAX_DEPTH=6       how deep to search for git repos / dependency dirs under each ROOT

set -u
export GIT_OPTIONAL_LOCKS=0
export LC_ALL=C

STALE_DAYS="${STALE_DAYS:-14}"
KEEP_PACKAGES="${KEEP_PACKAGES:-3}"
MAX_DEPTH="${MAX_DEPTH:-6}"

if [ "$#" -gt 0 ]; then ROOTS=("$@"); else ROOTS=("$HOME"); fi

section() { printf '\n== %s ==\n' "$1"; }
human_kb() { awk -v kb="$1" 'BEGIN { if (kb >= 1048576) printf "%.2f GB", kb/1048576; else printf "%.0f MB", kb/1024 }'; }
size_kb() { du -sk "$1" 2>/dev/null | cut -f1; }

report_disk() {
  section "Disk and swap"
  df -h /System/Volumes/Data 2>/dev/null | tail -1 | awk '{print "Data volume: used " $3 " / size " $2 ", available " $4 " (" $5 ")"}'
  sysctl -n vm.swapusage 2>/dev/null | sed 's/^/Swap: /'
}

report_top_dirs() {
  section "Largest entries under each root (top 15)"
  for root in "${ROOTS[@]}"; do
    echo "[$root]"
    (cd "$root" 2>/dev/null && du -skx -- * .[!.]* 2>/dev/null) | sort -rn | head -15 |
      while read -r kb name; do printf '  %10s  %s\n' "$(human_kb "$kb")" "$name"; done
  done
}

report_caches() {
  section "Package manager caches (clean with the official command)"
  local entries=(
    "$HOME/.npm/_cacache|npm cache clean --force"
    "$HOME/Library/pnpm/store|pnpm store prune"
    "$HOME/Library/Caches/pip|pip cache purge"
    "$HOME/.cache/uv|uv cache prune"
    "$HOME/Library/Caches/Homebrew|brew cleanup --prune=all"
    "$HOME/.gradle/caches|(shared by Android builds; ask before touching)"
  )
  for e in "${entries[@]}"; do
    local path="${e%%|*}" cmd="${e#*|}"
    [ -e "$path" ] || continue
    printf '  %10s  %-40s  %s\n' "$(human_kb "$(size_kb "$path")")" "${path/#$HOME/~}" "$cmd"
  done
}

find_git_repos() {
  # Prints main-worktree roots (directories whose .git is a directory, not a file).
  find "$1" -maxdepth "$MAX_DEPTH" \( -name node_modules -o -name Library -o -name .Trash -o -name .cache \
    -o -name .npm -o -name .gradle -o -name .cargo -o -name .rustup -o -name Pods -o -name DerivedData \) -prune \
    -o -type d -name .git -print -prune 2>/dev/null | sed 's#/\.git$##'
}

report_worktrees() {
  section "git worktrees (linked ones only)"
  printf '  %-9s %-6s %-6s %-11s %s\n' "SIZE" "DIRTY" "REMOTE" "LAST_TOUCH" "PATH [BRANCH]"
  local seen=""
  for root in "${ROOTS[@]}"; do
    while IFS= read -r repo; do
      git -C "$repo" worktree list --porcelain 2>/dev/null | awk '/^worktree /{print substr($0,10)}' | tail -n +2 |
        while IFS= read -r wt; do
          case "$seen" in *"|$wt|"*) continue ;; esac
          seen="$seen|$wt|"
          [ -d "$wt" ] || { printf '  %-9s %-6s %-6s %-11s %s\n' "-" "-" "-" "missing" "$wt"; continue; }
          local dirty remote branch last kb
          dirty=$([ -n "$(git -C "$wt" status --porcelain --untracked-files=all 2>/dev/null | head -1)" ] && echo yes || echo no)
          remote=$([ -n "$(git -C "$wt" branch -r --contains HEAD 2>/dev/null | head -1)" ] && echo yes || echo NO)
          branch=$(git -C "$wt" branch --show-current 2>/dev/null); branch="${branch:-detached}"
          last=$(git -C "$wt" log -1 --format=%cs 2>/dev/null)
          kb=$(size_kb "$wt")
          printf '  %-9s %-6s %-6s %-11s %s [%s]\n' "$(human_kb "${kb:-0}")" "$dirty" "$remote" "${last:--}" "${wt/#$HOME/~}" "$branch"
        done
    done < <(find_git_repos "$root")
  done
  echo "  DIRTY=yes or REMOTE=NO means: keep, or ask the owner. See docs/04-git-worktree.md."
  echo "  Also check ignored files: git -C <path> status --porcelain --ignored | grep '^!!'"
}

report_stale_deps() {
  section "Dependency / build dirs in projects untouched for ${STALE_DAYS}+ days"
  local cutoff
  cutoff=$(date -v-"${STALE_DAYS}"d +%Y-%m-%d 2>/dev/null || date -d "-${STALE_DAYS} days" +%F)
  for root in "${ROOTS[@]}"; do
    find "$root" -maxdepth "$MAX_DEPTH" \( -name .git -o -name Library -o -name .Trash \) -prune -o \
      -type d \( -name node_modules -o -name target -o -name .next -o -name .venv -o -name .turbo \) -prune -print 2>/dev/null |
      while IFS= read -r dep; do
        [ -L "$dep" ] && continue
        local project; project=$(dirname "$dep")
        # skip if the project itself had any non-dependency file change after the cutoff
        if [ -n "$(find "$project" -maxdepth 4 \( -name node_modules -o -name .git -o -name target -o -name .next \) -prune -o -type f -newermt "$cutoff" -print 2>/dev/null | head -1)" ]; then
          continue
        fi
        printf '%s\t%s\n' "$(size_kb "$dep")" "${dep/#$HOME/~}"
      done
  done | sort -rn | head -40 | while IFS=$'\t' read -r kb path; do printf '  %10s  %s\n' "$(human_kb "$kb")" "$path"; done
  echo "  Before removing: make sure nothing in it is tracked by git and no process uses the project."
}

report_packages() {
  section "Installer dirs holding more than ${KEEP_PACKAGES} packages"
  for root in "${ROOTS[@]}"; do
    find "$root" -maxdepth "$MAX_DEPTH" \( -name node_modules -o -name .git -o -name Library -o -name .Trash \) -prune -o \
      -type d \( -name dist -o -name release -o -name outputs \) -print 2>/dev/null |
      while IFS= read -r d; do
        local n
        n=$(find "$d" -maxdepth 2 -type f \( -name '*.apk' -o -name '*.aab' -o -name '*.ipa' -o -name '*.dmg' -o -name '*.hap' \) 2>/dev/null | wc -l | tr -d ' ')
        [ "$n" -gt "$KEEP_PACKAGES" ] && printf '  %4s packages  %10s  %s\n' "$n" "$(human_kb "$(size_kb "$d")")" "${d/#$HOME/~}"
      done
  done
  echo "  Keep the newest ${KEEP_PACKAGES} (plus their mapping files); move older ones to NAS / Release or the Trash."
}

echo "disk-report $(date '+%Y-%m-%d %H:%M') — read-only, nothing is changed"
report_disk
report_top_dirs
report_caches
report_worktrees
report_stale_deps
report_packages
echo
echo "Done. Nothing was deleted. Decide per item, then follow docs/02-safe-cleanup.md."
