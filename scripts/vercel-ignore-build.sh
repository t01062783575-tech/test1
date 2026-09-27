#!/bin/bash
# Vercel "Ignored Build Step" for the smartstore-automation project
# (Root Directory = repo root).
#
# Exit 0 -> skip this build
# Exit 1 -> proceed with build
#
# Skips the build when every changed file in this commit lives under
# freelancer-expense-landing/ or personal-planner/, since those folders
# are separate apps deployed as their own Vercel projects.

set -o pipefail

if ! git rev-parse HEAD^ >/dev/null 2>&1; then
  echo "No previous commit to diff against — building to be safe."
  exit 1
fi

if git diff --quiet HEAD^ HEAD -- . ':!freelancer-expense-landing' ':!personal-planner'; then
  echo "Only freelancer-expense-landing/ or personal-planner/ changed — skipping build."
  exit 0
else
  echo "Changes outside the separate app folders detected — building."
  exit 1
fi
