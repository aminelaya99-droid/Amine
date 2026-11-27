#!/usr/bin/env python3
"""YouTube research with no API key, run on a GitHub runner.

Each line of the request file is one command:

  outliers <channel> [--limit 60] [--min-ratio 3] [--tab both|videos|shorts] [--enrich 10]
  keywords <seed words...> [--gl DZ] [--hl ar] [--no-latin]
  transcript <video> [--lang ar,en]
  info <video>

<channel> is a channel URL or @handle; <video> a video URL or id.
For line n, writes <out>/<n>_<command>.md (report) and .json (raw data),
and appends "ok|error <TAB> n <TAB> line" to <out>/status.tsv.
"""
import argparse
import json
import re
import shlex
import statistics
import sys
import time
import traceback
from collections import Counter
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from yt_dlp import YoutubeDL

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"}
AR_LETTERS = "ابتثجحخدذرزسشصضطظعغفقكلمنهوي"
DZ_PREFIXES = ["كيفاش", "واش", "علاش", "وين", "كيف", "افضل", "طريقة", "اسعار"]
STOP = set("في من على الى إلى عن مع هذا هذه هو هي و يا ما لا the a an and or of to in on for with is are you your my how what why".split())


def ydl(**extra):
    opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    opts.update(extra)
    return YoutubeDL(opts)


def video_id(s):
    m = re.search(r"(?:v=|youtu\.be/|shorts/|embed/|live/)([\w-]{11})", s)
    return m.group(1) if m else s.strip()


def channel_base(s):
    s = s.strip()
    if s.startswith("@"):
        s = "https://www.youtube.com/" + s
    s = s.rstrip("/")
    return re.sub(r"/(videos|shorts|streams|featured|playlists|community)$", "", s)


def first_line(e):
    """The error as one line; youtube-transcript-api puts the cause on later lines."""
    s = " ".join(str(e).split())
    return s[:400] if s else type(e).__name__


def full_info(vid):
    with ydl() as y:
        return y.extract_info("https://www.youtube.com/watch?v=" + vid, download=False)


def fmt_int(n):
    return "-" if n is None else f"{int(n):,}"


# ---------------------------------------------------------------- outliers

def cmd_outliers(a):
    base = channel_base(a.channel)
    tabs = ["videos", "shorts"] if a.tab == "both" else [a.tab]
    data = {"channel": base, "tabs": {}}
    md = [f"# Outliers: {base}", ""]
    for tab in tabs:
        try:
            with ydl(extract_flat="in_playlist", playlistend=a.limit) as y:
                info = y.extract_info(f"{base}/{tab}", download=False)
        except Exception as e:  # tab missing or blocked
            data["tabs"][tab] = {"error": first_line(e)}
            md += [f"## {tab}", "", f"error: {first_line(e)}", ""]
            continue
        data["channel_name"] = info.get("channel") or info.get("uploader") or info.get("title")
        rows = []
        for e in info.get("entries") or []:
            if not e or not e.get("id"):
                continue
            url = (f"https://www.youtube.com/shorts/{e['id']}" if tab == "shorts"
                   else f"https://www.youtube.com/watch?v={e['id']}")
            rows.append({"id": e["id"], "title": e.get("title"), "views": e.get("view_count"),
                         "duration": e.get("duration"), "url": url})
        views = [r["views"] for r in rows if r["views"]]
        if not views:
            data["tabs"][tab] = {"videos": rows, "error": "no view counts"}
            md += [f"## {tab}", "", f"{len(rows)} videos, no view counts", ""]
            continue
        median = statistics.median(views)
        mean = statistics.mean(views)
        for r in rows:
            r["ratio"] = round(r["views"] / median, 2) if r["views"] and median else None
        outs = sorted((r for r in rows if r["ratio"] and r["ratio"] >= a.min_ratio),
                      key=lambda r: r["ratio"], reverse=True)
        for r in outs[: a.enrich]:
            try:
                fi = full_info(r["id"])
                r.update(tags=fi.get("tags") or [], upload_date=fi.get("upload_date"),
                         likes=fi.get("like_count"), comments=fi.get("comment_count"),
                         categories=fi.get("categories"),
                         description=(fi.get("description") or "")[:400])
            except Exception as e:
                r["details_error"] = first_line(e)
        words = Counter()
        for r in outs:
            for w in re.findall(r"[\w؀-ۿ]{3,}", (r["title"] or "").lower()):
                if w not in STOP:
                    words[w] += 1
        data["tabs"][tab] = {"count": len(rows), "median_views": median, "mean_views": round(mean),
                             "min_ratio": a.min_ratio, "outliers": outs, "videos": rows,
                             "outlier_title_words": words.most_common(25)}
        md += [f"## {tab}: {len(rows)} videos, median {fmt_int(median)} views, mean {fmt_int(mean)}", "",
               f"Outliers (>= {a.min_ratio}x median): {len(outs)}", "",
               "| # | x median | views | title | tags |", "|---|---|---|---|---|"]
        for i, r in enumerate(outs, 1):
            tags = ", ".join(r.get("tags") or []) or r.get("details_error", "")
            title = (r["title"] or "").replace("|", "/")
            md.append(f"| {i} | {r['ratio']} | {fmt_int(r['views'])} | [{title}]({r['url']}) | {tags[:200]} |")
        if words:
            md += ["", "Frequent words in outlier titles: "
                   + ", ".join(f"{w} ({c})" for w, c in words.most_common(25))]
        md.append("")
    if all("outliers" not in t for t in data["tabs"].values()):
        raise RuntimeError("; ".join(f"{k}: {v.get('error')}" for k, v in data["tabs"].items()))
    return data, md


# ---------------------------------------------------------------- keywords

def suggest(q, gl, hl):
    url = "https://suggestqueries.google.com/complete/search?" + urlencode(
        {"client": "firefox", "ds": "yt", "q": q, "gl": gl, "hl": hl, "ie": "utf8", "oe": "utf8"})
    with urlopen(Request(url, headers=UA), timeout=15) as r:
        return json.loads(r.read().decode("utf-8", "replace"))[1]


def cmd_keywords(a):
    seed = " ".join(a.seed)
    queries = [seed] + [f"{seed} {c}" for c in AR_LETTERS] + [f"{p} {seed}" for p in DZ_PREFIXES]
    if a.latin:
        queries += [f"{seed} {c}" for c in "abcdefghijklmnopqrstuvwxyz"]
    hits, errors = Counter(), []
    for q in queries:
        try:
            for s in suggest(q, a.gl, a.hl):
                hits[s.strip()] += 1
        except Exception as e:
            errors.append(f"{q}: {first_line(e)}")
        time.sleep(0.15)
    if not hits and errors:
        raise RuntimeError(f"all {len(errors)} autocomplete requests failed; first: {errors[0]}")
    ranked = sorted(hits.items(), key=lambda kv: (-kv[1], kv[0]))
    data = {"seed": seed, "gl": a.gl, "hl": a.hl, "queries": len(queries),
            "suggestions": [{"text": t, "hits": n} for t, n in ranked], "errors": errors}
    md = [f"# Keywords: {seed} ({a.gl}, {a.hl})", "",
          f"{len(ranked)} unique suggestions from {len(queries)} autocomplete queries"
          + (f", {len(errors)} failed" if errors else ""), ""]
    md += [f"- {t} ({n})" for t, n in ranked]
    return data, md


# ---------------------------------------------------------------- transcript

def transcript_api(vid, langs):
    from youtube_transcript_api import YouTubeTranscriptApi
    tl = YouTubeTranscriptApi().list(vid)
    try:
        t = tl.find_transcript(langs)
    except Exception:
        t = next(iter(tl))
    return t.language_code, [{"start": s.start, "dur": s.duration, "text": s.text} for s in t.fetch()]


def transcript_ytdlp(vid, langs):
    fi = full_info(vid)
    pools = [fi.get("subtitles") or {}, fi.get("automatic_captions") or {}]
    for pool in pools:
        for lang in langs + [k for k in pool if k not in langs]:
            for f in pool.get(lang) or []:
                if f.get("ext") == "json3":
                    with urlopen(Request(f["url"], headers=UA), timeout=30) as r:
                        ev = json.loads(r.read().decode("utf-8"))["events"]
                    segs = [{"start": e.get("tStartMs", 0) / 1000, "dur": e.get("dDurationMs", 0) / 1000,
                             "text": "".join(s.get("utf8", "") for s in e.get("segs", [])).strip()}
                            for e in ev if e.get("segs")]
                    return lang, [s for s in segs if s["text"]]
    raise RuntimeError("no captions on this video")


def cmd_transcript(a):
    vid = video_id(a.video)
    langs = [x.strip() for x in a.lang.split(",") if x.strip()]
    errors = []
    for name, fn in (("youtube-transcript-api", transcript_api), ("yt-dlp", transcript_ytdlp)):
        try:
            lang, segs = fn(vid, langs)
            break
        except Exception as e:
            errors.append(f"{name}: {first_line(e)}")
    else:
        raise RuntimeError(" | ".join(errors))
    text = " ".join(s["text"].replace("\n", " ") for s in segs)
    data = {"id": vid, "lang": lang, "via": name, "segments": segs, "text": text, "errors": errors}
    md = [f"# Transcript: https://youtu.be/{vid} ({lang}, via {name})", ""]
    md += [f"[{int(s['start'] // 60)}:{int(s['start'] % 60):02d}] {s['text']}" for s in segs]
    return data, md


# ---------------------------------------------------------------- info

def cmd_info(a):
    fi = full_info(video_id(a.video))
    keys = ["id", "title", "channel", "channel_url", "upload_date", "duration", "view_count",
            "like_count", "comment_count", "tags", "categories", "description", "chapters"]
    data = {k: fi.get(k) for k in keys}
    md = [f"# {data['title']}", ""]
    md += [f"- {k}: {data[k]}" for k in keys if k not in ("title", "description", "chapters")]
    md += ["", "## Description", "", data.get("description") or ""]
    return data, md


# ---------------------------------------------------------------- main

def parser():
    p = argparse.ArgumentParser(prog="research", exit_on_error=False)
    sub = p.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("outliers")
    o.add_argument("channel")
    o.add_argument("--limit", type=int, default=60)
    o.add_argument("--min-ratio", type=float, default=3.0)
    o.add_argument("--tab", choices=["both", "videos", "shorts"], default="both")
    o.add_argument("--enrich", type=int, default=10)
    k = sub.add_parser("keywords")
    k.add_argument("seed", nargs="+")
    k.add_argument("--gl", default="DZ")
    k.add_argument("--hl", default="ar")
    k.add_argument("--no-latin", dest="latin", action="store_false")
    t = sub.add_parser("transcript")
    t.add_argument("video")
    t.add_argument("--lang", default="ar,en")
    i = sub.add_parser("info")
    i.add_argument("video")
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--request-file", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cmds = {"outliers": cmd_outliers, "keywords": cmd_keywords,
            "transcript": cmd_transcript, "info": cmd_info}
    n = 0
    for line in Path(args.request_file).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        n += 1
        name = "error"
        try:
            a = parser().parse_args(shlex.split(line))
            name = a.cmd
            data, md = cmds[a.cmd](a)
            status = "ok"
        except BaseException as e:  # argparse raises SystemExit on bad input
            if isinstance(e, KeyboardInterrupt):
                raise
            data = {"error": first_line(e), "trace": traceback.format_exc()}
            md = [f"# error: {line}", "", "```", traceback.format_exc(), "```"]
            status = "error"
        (out / f"{n}_{name}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        (out / f"{n}_{name}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
        with open(out / "status.tsv", "a", encoding="utf-8") as f:
            f.write(f"{status}\t{n}\t{line}\n")
        print(f"{status}\t{n}\t{line}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
