#!/bin/sh
# Publish the todo list to GitHub Pages (served from main) straight after an ingest.
#
# Agreed 2026-10-12 (Simon): merge to main and push every time we ingest, so the team's
# list is never stale. Before this, the daily filing cron closed rows only on this
# machine and the public list lagged by 1,067 papers, which people kept downloading.
#
# Commits ONLY the published todo-list files (never anything else in the working tree,
# staged or not), then updates main WITHOUT touching the working tree:
#   * main is an ancestor of HEAD -> plain fast-forward push of HEAD to main;
#   * otherwise -> `git merge-tree` builds the merge in the object store, `commit-tree`
#     makes the merge commit on top of origin/main, and that is pushed. A conflict
#     pushes nothing and exits 1 with the conflicting paths in the log.
# Also pushes the current branch to its own remote branch.
#
#   sh scripts/publish_todo_list.sh "data(queue): 12 papers filed from the drop folders"
set -e
cd "/media/simon/data/Documents/Si Work/PostDoc Work/EEA/2025/Data Panel"
MSG="${1:-data(queue): todo list updated after ingest}"
PATHS="docs/papers_data.json docs/closed_access docs/acquisition/remaining_papers.html"
BRANCH=$(git rev-parse --abbrev-ref HEAD)

git add -- $PATHS
if git diff --cached --quiet -- $PATHS; then
  echo "publish: nothing changed in the todo list"
else
  # --only: commit these paths alone, whatever else the index holds
  git commit --quiet --only -m "$MSG

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- $PATHS
  echo "publish: committed $(git rev-parse --short HEAD) on $BRANCH"
fi

git fetch --quiet origin main
if git merge-base --is-ancestor origin/main HEAD; then
  git push --quiet origin "HEAD:main"
  echo "publish: main fast-forwarded to $(git rev-parse --short HEAD)"
else
  if ! TREE=$(git merge-tree --write-tree origin/main HEAD); then
    echo "publish: FAILED, $BRANCH conflicts with main; nothing pushed:"
    echo "$TREE"
    exit 1
  fi
  MERGE=$(git commit-tree "$TREE" -p origin/main -p HEAD -m "Merge $BRANCH into main: $MSG")
  git push --quiet origin "$MERGE:refs/heads/main"
  echo "publish: main updated with merge $(git rev-parse --short "$MERGE")"
fi
git push --quiet origin "HEAD:refs/heads/$BRANCH" || echo "publish: WARNING, branch push failed (main is published)"
git fetch --quiet origin main:main 2>/dev/null || true
echo "publish: DONE $(date '+%Y-%m-%d %H:%M:%S %Z')"
