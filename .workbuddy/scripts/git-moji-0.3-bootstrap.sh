#!/usr/bin/env bash
# moji-0.3 bootstrap
#   1) 盘点    2) 暂存 0.2 末期未提交改动   3) main 快进到 0.2
#   4) 新建 feat/moji-0.3 并推远端         5) 清理冗余远端分支      6) 恢复暂存 + 验收
#
# 用法（Git Bash）：
#   bash .workbuddy/scripts/git-moji-0.3-bootstrap.sh
#   只想看不动：   DRY_RUN=1 bash .workbuddy/scripts/git-moji-0.3-bootstrap.sh
#   保留远端旧分支：SKIP_CLEANUP=1 bash .workbuddy/scripts/git-moji-0.3-bootstrap.sh
#   想留合并提交：  MERGE_STYLE=noff bash .workbuddy/scripts/git-moji-0.3-bootstrap.sh

set -euo pipefail
cd "$(dirname "$0")/../.."

DRY_RUN="${DRY_RUN:-0}"
SKIP_CLEANUP="${SKIP_CLEANUP:-0}"
MERGE_STYLE="${MERGE_STYLE:-ff}"

run() {
  if [ "$DRY_RUN" = "1" ]; then
    echo "  [dry-run] $*"
  else
    echo "  \$ $*"
    "$@"
  fi
}

echo "==================== 0. 盘点 ===================="
git status -sb || true
echo "-- 本地分支 --"
git branch -vv
echo "-- 远端分支（origin）--"
git ls-remote --heads origin
echo "-- 远端标签（origin，后 6 条）--"
git ls-remote --tags origin | tail -n 6
echo "-- main..upstream-tracking 待合入提交数 --"
git rev-list --count main..upstream-tracking
echo "-- upstream-tracking..main 反向差异（应为 0，不是 0 就别自动合）--"
git rev-list --count upstream-tracking..main

echo
echo "==================== 1. 暂存 0.2 末期未提交改动 ===================="
PENDING=(notes/决策-台账.md notes/README.md tools/usb_relay.py)
if [ -n "$(git status --porcelain -- "${PENDING[@]}")" ]; then
  run git stash push -m "pre-moji-0.3: relay + notes pending" -- "${PENDING[@]}"
  STASHED=1
else
  echo "  三个文件均无改动，跳过暂存"
  STASHED=0
fi

echo
echo "==================== 2. main 合入 0.2 ===================="
run git switch main
if [ "$MERGE_STYLE" = "noff" ]; then
  run git merge --no-ff upstream-tracking -m "Merge moji-0.2: wake word, USB link, CJK font, reminder bridge"
else
  run git merge --ff-only upstream-tracking
fi
run git push origin main

echo
echo "==================== 3. 新建 feat/moji-0.3 ===================="
run git switch -c feat/moji-0.3
run git push -u origin feat/moji-0.3

echo
echo "==================== 4. 恢复暂存改动到 0.3 分支 ===================="
if [ "$STASHED" = "1" ]; then
  run git stash pop
else
  echo "  无暂存内容"
fi

echo
echo "==================== 5. 清理冗余远端分支 ===================="
if [ "$SKIP_CLEANUP" = "1" ]; then
  echo "  SKIP_CLEANUP=1，保留 origin/upstream-tracking"
else
  run git branch -d upstream-tracking
  run git push origin --delete upstream-tracking
  run git remote prune origin
fi

echo
echo "==================== 6. 验收 ===================="
echo "-- 当前分支 --"; git status -sb
echo "-- 分支列表 --"; git branch -vv
echo "-- 最近 3 条提交 --"; git log --oneline -3
if [ "$DRY_RUN" != "1" ]; then
  echo "-- main 与 origin/main 应无差异 --"
  git fetch -q origin
  git diff --stat main origin/main || true
  echo "-- main 是否包含 0.2 全部内容（应为空）--"
  git log --oneline main..upstream-tracking 2>/dev/null || echo "  upstream-tracking 已删除（正常）"
fi
echo
echo "完成。此后 0.3 的所有改动都落在 feat/moji-0.3，不要再直接提交 main。"
