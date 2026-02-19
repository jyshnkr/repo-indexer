#!/bin/sh
# Deterministic git sync: checkout latest from release > main > master

set -e

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

# Fetch all remotes
if ! git fetch --all --quiet; then
    echo "ERROR: Git fetch failed — check network connection and remote credentials."
    echo "  Verify remote: git remote -v"
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

# Checkout and pull
git checkout "$TARGET" 2>/dev/null || git checkout -b "$TARGET" "origin/$TARGET" || {
    echo "ERROR: Failed to checkout branch '$TARGET'"
    exit 1
}
git pull origin "$TARGET" --quiet

echo "SYNCED: $TARGET ($(git rev-parse --short HEAD))"
