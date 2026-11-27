#!/usr/bin/env bash
# Session side. Run a job on a GitHub runner, since this session's network
# cannot reach YouTube, Instagram, TikTok and the like.
#
#   tools/remote/job.sh <tool> <request line> [<request line>...]
#
# Writes the lines to tools/<tool>/requests/<id>.txt and pushes it, which
# triggers .github/workflows/<tool>.yml. Waits for the workflow to publish
# refs/<tool>/<id>, unpacks it into $REMOTE_OUT/<tool>/<id> (default
# /tmp/remote-jobs), joins split files, and prints status.tsv and the files.
# Set GIT_TRAILERS to append lines (e.g. Co-Authored-By) to the request commit.
set -euo pipefail

[ $# -ge 2 ] || { echo "usage: $0 <tool> <request line> [...]" >&2; exit 2; }
tool=$1; shift
cd "$(git rev-parse --show-toplevel)"
[ -d "tools/$tool/requests" ] || { echo "unknown tool: $tool" >&2; exit 2; }

out_base="${REMOTE_OUT:-/tmp/remote-jobs}"
timeout_s="${REMOTE_TIMEOUT:-1800}"
id="$(date -u +%Y%m%d-%H%M%S)-$(od -An -N2 -tx1 /dev/urandom | tr -d ' \n')"
req="tools/$tool/requests/$id.txt"
branch="$(git rev-parse --abbrev-ref HEAD)"

printf '%s\n' "$@" > "$req"
git add "$req"
msg="$tool request $id"
[ -n "${GIT_TRAILERS:-}" ] && msg="$msg"$'\n\n'"$GIT_TRAILERS"
git commit -q -m "$msg" -- "$req"

pushed=0
for wait in 2 4 8 16; do
  if git push -q -u origin "$branch"; then pushed=1; break; fi
  echo "push failed, retrying in ${wait}s" >&2; sleep "$wait"
done
[ "$pushed" = 1 ] || { echo "could not push request $id" >&2; exit 1; }
echo "request $tool/$id pushed, waiting for the workflow..."

ref=""; waited=0
while [ "$waited" -lt "$timeout_s" ]; do
  ref=$(git ls-remote origin "refs/$tool/$id" "refs/tags/$tool-$id" | awk 'NR==1{print $2}')
  [ -n "$ref" ] && break
  sleep 10; waited=$((waited + 10))
done
[ -n "$ref" ] || { echo "timed out after ${timeout_s}s waiting for $tool/$id" >&2; exit 1; }

dest="$out_base/$tool/$id"
mkdir -p "$dest"
git fetch -q --depth=1 origin "$ref"
git archive FETCH_HEAD | tar -x -C "$dest"

shopt -s nullglob
for first in "$dest"/*.part000; do
  base="${first%.part000}"
  cat "$base".part* > "$base" && rm -f "$base".part*
done

echo "== $dest"
cat "$dest/status.tsv" 2>/dev/null || echo "(no status.tsv)"
for f in "$dest"/*; do
  printf '%s\t%s\n' "$(du -h "$f" | cut -f1)" "$f"
done
