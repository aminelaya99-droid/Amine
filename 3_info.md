# error: info https://youtu.be/Rcg2LwVhL_w

```
Traceback (most recent call last):
  File "/opt/hostedtoolcache/Python/3.12.16/x64/lib/python3.12/site-packages/yt_dlp/YoutubeDL.py", line 1728, in wrapper
    return func(self, *args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.16/x64/lib/python3.12/site-packages/yt_dlp/YoutubeDL.py", line 1863, in __extract_info
    ie_result = ie.extract(url)
                ^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.16/x64/lib/python3.12/site-packages/yt_dlp/extractor/common.py", line 764, in extract
    ie_result = self._real_extract(url)
                ^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.16/x64/lib/python3.12/site-packages/yt_dlp/extractor/youtube/_video.py", line 4103, in _real_extract
    self.raise_no_formats(reason, expected=True)
  File "/opt/hostedtoolcache/Python/3.12.16/x64/lib/python3.12/site-packages/yt_dlp/extractor/common.py", line 1271, in raise_no_formats
    raise ExtractorError(msg, expected=expected, video_id=video_id)
yt_dlp.utils.ExtractorError: [youtube] Rcg2LwVhL_w: Sign in to confirm you’re not a bot. This helps protect our community. Use --cookies-from-browser or --cookies for the authentication. See  https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp  for how to manually pass cookies. Also see  https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies  for tips on effectively exporting YouTube cookies

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/home/runner/work/Amine/Amine/tools/yt-research/research.py", line 274, in main
    data, md = cmds[a.cmd](a)
               ^^^^^^^^^^^^^^
  File "/home/runner/work/Amine/Amine/tools/yt-research/research.py", line 221, in cmd_info
    fi = full_info(video_id(a.video))
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/runner/work/Amine/Amine/tools/yt-research/research.py", line 62, in full_info
    return y.extract_info("https://www.youtube.com/watch?v=" + vid, download=False)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.16/x64/lib/python3.12/site-packages/yt_dlp/YoutubeDL.py", line 1717, in extract_info
    return self.__extract_info(url, self.get_info_extractor(key), download, extra_info, process)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.12.16/x64/lib/python3.12/site-packages/yt_dlp/YoutubeDL.py", line 1746, in wrapper
    self.report_error(str(e), e.format_traceback())
  File "/opt/hostedtoolcache/Python/3.12.16/x64/lib/python3.12/site-packages/yt_dlp/YoutubeDL.py", line 1162, in report_error
    self.trouble(f'{self._format_err("ERROR:", self.Styles.ERROR)} {message}', *args, **kwargs)
  File "/opt/hostedtoolcache/Python/3.12.16/x64/lib/python3.12/site-packages/yt_dlp/YoutubeDL.py", line 1100, in trouble
    raise DownloadError(message, exc_info if exc_info and exc_info[0] else sys.exc_info())
yt_dlp.utils.DownloadError: ERROR: [youtube] Rcg2LwVhL_w: Sign in to confirm you’re not a bot. This helps protect our community. Use --cookies-from-browser or --cookies for the authentication. See  https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp  for how to manually pass cookies. Also see  https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies  for tips on effectively exporting YouTube cookies

```
