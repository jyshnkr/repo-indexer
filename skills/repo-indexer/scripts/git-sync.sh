#!/bin/sh
# Deterministic git sync: checkout latest from release > main > master

set -eu

# Warn if the script fails mid-operation, leaving the repo in an unexpected state
_ORIG_BRANCH=""
_on_error() {
    _exit_code=$?
    if [ "$_exit_code" -ne 0 ]; then
        echo "" >&2
        echo "WARNING: git-sync exited with an error (code $_exit_code)." >&2
        if [ -n "$_ORIG_BRANCH" ]; then
            _current="$(git symbolic-ref --short HEAD 2>/dev/null || echo "DETACHED")"
            if [ "$_current" != "$_ORIG_BRANCH" ]; then
                echo "  Repository may be on branch '$_current' instead of '$_ORIG_BRANCH'." >&2
                echo "  Run: git checkout $_ORIG_BRANCH" >&2
            fi
        fi
    fi
}
trap '_on_error' EXIT

# Check for active rebase or merge
if [ -d "$(git rev-parse --git-dir)/rebase-merge" ] || [ -d "$(git rev-parse --git-dir)/rebase-apply" ]; then
    echo "ERROR: Rebase in progress. Complete or abort it first."
    exit 1
fi
if [ -f "$(git rev-parse --git-dir)/MERGE_HEAD" ]; then
    echo "ERROR: Merge in progress. Complete or abort it first."
    exit 1
fi

# Check for detached HEAD
if ! git symbolic-ref HEAD >/dev/null 2>&1; then
    echo "ERROR: Repository is in detached HEAD state."
    echo "  Fix: git checkout main  (replace 'main' with your branch name)"
    echo "  Or:  git switch -"
    exit 1
fi

# Safe to capture now — HEAD is confirmed to be a branch
_ORIG_BRANCH="$(git symbolic-ref --short HEAD)"

# Check for dirty working tree
if ! git diff --quiet || ! git diff --cached --quiet; then
    echo "ERROR: Working tree has uncommitted changes. Stash or commit before syncing."
    exit 1
fi

# Check remote exists
if ! git remote get-url origin >/dev/null 2>&1; then
    echo "ERROR: No remote 'origin' configured."
    exit 1
fi

# Fetch from origin only (do not fetch from untrusted remotes)
if ! git fetch origin --quiet; then
    echo "ERROR: Git fetch failed — check network connection and remote credentials."
    echo "  Verify remote: git remote get-url origin"
    exit 1
fi

# Determine target branch (priority: release > main > master)
TARGET=""
for branch in release main master; do
    if git show-ref --verify --quiet "refs/remotes/origin/$branch" 2>/dev/null; then
        TARGET="$branch"
        break
    fi
done

if [ -z "$TARGET" ]; then
    echo "ERROR: No release/main/master branch found"
    exit 1
fi

# Checkout and pull (fast-forward only — refuse merges from untrusted remote)
git checkout "$TARGET" 2>/dev/null || git checkout -b "$TARGET" "origin/$TARGET" || {
    echo "ERROR: Failed to checkout branch '$TARGET'"
    exit 1
}
if ! git pull origin "$TARGET" --ff-only --quiet; then
    echo "ERROR: Fast-forward pull failed — local '$TARGET' has diverged from origin."
    echo "  Fix: git reset --hard origin/$TARGET  (WARNING: discards local commits)"
    echo "  Or:  git rebase origin/$TARGET"
    exit 1
fi

echo "SYNCED: $TARGET ($(git rev-parse --short HEAD))"
