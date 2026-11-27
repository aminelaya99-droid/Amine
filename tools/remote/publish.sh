#!/usr/bin/env bash
# Runner side. Publish each <out-root>/<id>/ directory as a commit on
# refs/<tool>/<id> (tag <tool>-<id> if the ref is refused), then delete
# results of this tool older than 24h.
#   tools/remote/publish.sh <tool> <out-root>
set -euo pipefail
shopt -s nullglob
tool=$1 root=$2
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

for d in "$root"/*/; do
  id=$(basename "$d")
  export GIT_INDEX_FILE="$RUNNER_TEMP/index-$tool-$id"
  rm -f "$GIT_INDEX_FILE"
  for p in "$d"*; do
    [ -f "$p" ] || continue
    blob=$(git hash-object -w "$p")
    git update-index --add --cacheinfo 100644 "$blob" "$(basename "$p")"
  done
  tree=$(git write-tree)
  commit=$(echo "$tool $id" | git commit-tree "$tree")
  unset GIT_INDEX_FILE
  git push -q origin "$commit:refs/$tool/$id" \
    || git push -q origin "$commit:refs/tags/$tool-$id"
  echo "published $tool/$id -> $commit"
done

now=$(date -u +%s)
git ls-remote origin "refs/$tool/*" "refs/tags/$tool-*" | while read -r _ ref; do
  id=${ref##*/}; id=${id#"$tool"-}
  t=$(date -u -d "${id:0:8} ${id:9:2}:${id:11:2}:${id:13:2}" +%s 2>/dev/null) || continue
  if [ $((now - t)) -gt 86400 ]; then
    git push -q origin ":$ref" && echo "deleted $ref" || true
  fi
done
