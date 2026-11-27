#!/usr/bin/env bash
# Download videos from links:  tools/video-dl/fetch.sh URL [URL...]
# See tools/remote/job.sh for how it works and the environment variables.
exec "$(dirname "$0")/../remote/job.sh" video-dl "$@"
