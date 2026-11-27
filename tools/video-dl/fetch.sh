#!/usr/bin/env bash
# Download videos from links (YouTube, Instagram, TikTok, Facebook...) by way
# of the video-dl GitHub Actions workflow, since this session's network cannot
# reach those sites.
#
#   tools/video-dl/fetch.sh URL [URL...]
#
# Pushes a request file, waits for the workflow to publish the result on
# refs/video-dl/<id>, then unpacks it into $VIDEO_DL_OUT/<id> (default
# /tmp/video-dl/<id>) and prints status.tsv and the video paths.
# Set GIT_TRAILERS to append lines (e.g. Co-Authored-By) to the request commit.
set -euo pipefail

[ $# -ge 1 ] || { echo "usage: $0 URL [URL...]" >&2; exit 2; }
cd "$(git rev-parse --show-toplevel)"

out_base="${VIDEO_DL_OUT:-/tmp/video-dl}"
timeout_s="${VIDEO_DL_TIMEOUT:-1800}"
id="$(date -u +%Y%m%d-%H%M%S)-$(od -An -N2 -tx1 /dev/urandom | tr -d ' \n')"
req="tools/video-dl/requests/$id.txt"
branch="$(git rev-parse --abbrev-ref HEAD)"

printf '%s\n' "$@" > "$req"
git add "$req"
msg="video-dl request $id"
[ -n "${GIT_TRAILERS:-}" ] && msg="$msg"$'\n\n'"$GIT_TRAILERS"
git commit -q -m "$msg" -- "$req"

pushed=0
for wait in 2 4 8 16; do
  if git push -q -u origin "$branch"; then pushed=1; break; fi
  echo "push failed, retrying in ${wait}s" >&2; sleep "$wait"
done
[ "$pushed" = 1 ] || { echo "could not push request $id" >&2; exit 1; }
echo "request $id pushed, waiting for the workflow..."

ref=""; waited=0
while [ "$waited" -lt "$timeout_s" ]; do
  ref=$(git ls-remote origin "refs/video-dl/$id" "refs/tags/video-dl-$id" | awk 'NR==1{print $2}')
  [ -n "$ref" ] && break
  sleep 10; waited=$((waited + 10))
done
[ -n "$ref" ] || { echo "timed out after ${timeout_s}s waiting for $id" >&2; exit 1; }

dest="$out_base/$id"
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
for v in "$dest"/*.mp4 "$dest"/*.webm "$dest"/*.mkv; do
  printf '%s\t%s\n' "$(du -h "$v" | cut -f1)" "$v"
done
