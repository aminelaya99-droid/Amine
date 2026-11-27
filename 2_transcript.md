# error: transcript https://www.youtube.com/shorts/hYahU_Cqwp8 --lang en

```
Traceback (most recent call last):
  File "/home/runner/work/Amine/Amine/tools/yt-research/research.py", line 276, in main
    data, md = cmds[a.cmd](a)
               ^^^^^^^^^^^^^^
  File "/home/runner/work/Amine/Amine/tools/yt-research/research.py", line 212, in cmd_transcript
    raise RuntimeError(" | ".join(errors))
RuntimeError: youtube-transcript-api: Could not retrieve a transcript for the video https://www.youtube.com/watch?v=hYahU_Cqwp8! This is most likely caused by: YouTube is blocking requests from your IP. This usually is due to one of the following reasons: - You have done too many requests and your IP has been blocked by YouTube - You are doing requests from an IP belonging to a cloud provider (like AWS, Google Cloud Platform, Azure, e | yt-dlp: ERROR: [youtube] hYahU_Cqwp8: Sign in to confirm you’re not a bot. This helps protect our community. Use --cookies-from-browser or --cookies for the authentication. See https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp for how to manually pass cookies. Also see https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies for tips on effectively exporting YouTu

```
