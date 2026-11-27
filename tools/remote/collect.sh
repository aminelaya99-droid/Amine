#!/usr/bin/env bash
# Runner side. Copy the request files this push added under
# tools/<tool>/requests/ into <dest>.
#   BEFORE=<github.event.before> tools/remote/collect.sh <tool> <dest>
set -euo pipefail
tool=$1 dest=$2
mkdir -p "$dest"
dir="tools/$tool/requests/"
if [ -n "${BEFORE:-}" ] && [ "$BEFORE" != "0000000000000000000000000000000000000000" ] \
   && git cat-file -e "$BEFORE^{commit}" 2>/dev/null; then
  files=$(git diff --name-only --diff-filter=AM "$BEFORE" HEAD -- "$dir")
else
  files=$(git diff-tree --no-commit-id --name-only --diff-filter=AM -r HEAD -- "$dir")
fi
for f in $files; do
  case "$f" in *.txt) cp "$f" "$dest/" ;; esac
done
ls -l "$dest"
