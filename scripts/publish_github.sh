#!/usr/bin/env bash
set -euo pipefail
# Fallback for a local machine where GitHub CLI is authenticated.
# Usage: ./scripts/publish_github.sh private|public [repo-name]
VISIBILITY="${1:-private}"
NAME="${2:-media-forensics-lab}"
if [[ "$VISIBILITY" != "private" && "$VISIBILITY" != "public" ]]; then
  echo "visibility must be private or public" >&2; exit 2
fi
command -v gh >/dev/null || { echo "GitHub CLI (gh) not found" >&2; exit 2; }
FLAG="--private"; [[ "$VISIBILITY" == "public" ]] && FLAG="--public"
if [[ ! -d .git ]]; then git init -b main; fi
git add .
git commit -m "feat: Media Forensics Lab v0.2" || true
gh repo create "$NAME" "$FLAG" --source=. --remote=origin --push
