#!/bin/bash
# Vercel "Ignored Build Step" for the personal-planner project
# (Root Directory = personal-planner).
#
# Exit 0 -> skip this build
# Exit 1 -> proceed with build
#
# Skips the build when this commit made no changes inside
# personal-planner/ (e.g. it only touched another
# project in this repo).

set -o pipefail

if ! git rev-parse HEAD^ >/dev/null 2>&1; then
  echo "No previous commit to diff against — building to be safe."
  exit 1
fi

if git diff --quiet HEAD^ HEAD -- .; then
  echo "No changes in personal-planner/ — skipping build."
  exit 0
else
  echo "Changes in personal-planner/ detected — building."
  exit 1
fi
