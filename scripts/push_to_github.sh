#!/usr/bin/env bash
set -euo pipefail

# Helper: create a release branch, commit, and push to origin
if [ -z "${1-}" ]; then
  echo "Usage: $0 <remote-branch-name>"
  exit 2
fi
BRANCH="$1"
git checkout -b "$BRANCH"
git add -A
git commit -m "chore: prepare diagnostics/deploy ${BRANCH}" || echo "No changes to commit"
git push -u origin "$BRANCH"
echo "Pushed branch $BRANCH. Create a PR to merge to main to trigger CI/deploy." 
