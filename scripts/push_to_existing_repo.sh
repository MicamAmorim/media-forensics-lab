#!/usr/bin/env bash
set -euo pipefail
REPO_URL="${1:-https://github.com/MicamAmorim/media-forensics-lab.git}"
BRANCH="${2:-main}"
if [[ ! -d .git ]]; then
  git init -b "$BRANCH"
fi

git config user.name "${GIT_AUTHOR_NAME:-Miqueias Amorim}"
git config user.email "${GIT_AUTHOR_EMAIL:-you@example.com}"

git add .
if git diff --cached --quiet; then
  echo "Nothing to commit."
else
  git commit -m "feat: Media Forensics Lab v0.2"
fi

if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "$REPO_URL"
else
  git remote add origin "$REPO_URL"
fi

git push -u origin "$BRANCH"
