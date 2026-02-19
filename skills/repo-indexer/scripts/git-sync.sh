#!/bin/bash
# Deterministic git sync: checkout latest from release > main > master

set -e

# Fetch all remotes
git fetch --all --quiet

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
git checkout "$TARGET" --quiet 2>/dev/null || git checkout -b "$TARGET" "origin/$TARGET" --quiet
git pull origin "$TARGET" --quiet

echo "SYNCED: $TARGET ($(git rev-parse --short HEAD))"
