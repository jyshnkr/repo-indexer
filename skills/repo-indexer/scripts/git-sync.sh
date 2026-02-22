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
    _available=$(git remote 2>/dev/null)
    if [ -n "$_available" ]; then
        echo "  Available remotes: $(echo "$_available" | tr '\n' ' ')"
    fi
    echo "  Fix: git remote add origin <url>"
    exit 1
fi

# Detect and handle shallow clones before fetching
if git rev-parse --is-shallow-repository 2>/dev/null | grep -q "true"; then
    echo "NOTE: Shallow clone detected — attempting to unshallow."
    if ! git fetch --unshallow --quiet 2>/dev/null; then
        echo "WARNING: Could not unshallow (network or server may not support it). Continuing."
    fi
fi

# Fetch from origin only (do not fetch from untrusted remotes)
_origin_url="$(git remote get-url origin 2>/dev/null)"
_fetch_err=""
if ! _fetch_err=$(git fetch origin --quiet 2>&1); then
    echo "ERROR: Git fetch failed — check network connection and remote credentials."
    echo "  Remote URL: $_origin_url"
    if [ -n "$_fetch_err" ]; then
        echo "  Details: $_fetch_err"
    fi
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
# Try checkout quietly; on failure try creating a tracking branch; capture stderr for diagnostics
_checkout_err=$(git checkout "$TARGET" 2>&1) || _checkout_err=$(git checkout -b "$TARGET" "origin/$TARGET" 2>&1) || {
    echo "ERROR: Failed to checkout branch '$TARGET'" >&2
    echo "  Details: $_checkout_err" >&2
    exit 1
}
if ! git pull origin "$TARGET" --ff-only --quiet; then
    echo "ERROR: Fast-forward pull failed — local '$TARGET' has diverged from origin."
    echo "  Fix: git reset --hard origin/$TARGET  (WARNING: discards local commits)"
    echo "  Or:  git rebase origin/$TARGET"
    exit 1
fi

echo "SYNCED: $TARGET ($(git rev-parse --short HEAD))"
