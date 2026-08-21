#!/bin/bash
# Vercel "Ignored Build Step" for the freelancer-expense-landing project
# (Root Directory = freelancer-expense-landing).
#
# Exit 0 -> skip this build
# Exit 1 -> proceed with build
#
# Skips the build when this commit made no changes inside
# freelancer-expense-landing/ (e.g. it only touched the unrelated
# smartstore-automation project at the repo root).

set -o pipefail

if ! git rev-parse HEAD^ >/dev/null 2>&1; then
  echo "No previous commit to diff against — building to be safe."
  exit 1
fi

if git diff --quiet HEAD^ HEAD -- .; then
  echo "No changes in freelancer-expense-landing/ — skipping build."
  exit 0
else
  echo "Changes in freelancer-expense-landing/ detected — building."
  exit 1
fi
