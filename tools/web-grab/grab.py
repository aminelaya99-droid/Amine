#!/usr/bin/env python3
"""Pull the product photos out of a product page, run on a GitHub runner.

Each line of the request file is one command:

  images <page-url> [--max 15] [--min-side 600]
  file <direct-url>

`images` reads the page HTML and collects image URLs from og:image,
JSON-LD, <img> attributes and any image link in inline scripts (Magento,
Shopify, eBay and AliExpress galleries all end up there), asks the CDN for
the largest size where it can, downloads them, drops icons, small images and
duplicates, and saves the rest as <n>_NN.jpg (JPEG, longest side <= 2000 px,
under 3 MB). `file` saves one URL as is.

Writes <out>/index.tsv (file, width, height, source url) and status.tsv.
"""
import argparse
import hashlib
import html
import io
import json
import re
import shlex
import sys
import traceback
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from PIL import Image

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/131.0 Safari/537.36",
      "Accept-Language": "en-US,en;q=0.9"}
IMG_EXT = r"(?:jpe?g|png|webp)"
URL_RE = re.compile(r"https?://[^\s\"'<>()\\]+?\." + IMG_EXT + r"(?:\?[^\s\"'<>\\]*)?", re.I)
SKIP = re.compile(r"logo|icon|sprite|favicon|avatar|badge|payment|flag|banner|placeholder|loading|"
                  r"/static/version|\.svg|1x1|pixel", re.I)
MAX_BYTES = 3_000_000


def fetch(url, timeout=30):
    with urlopen(Request(url, headers=UA), timeout=timeout) as r:
        return r.read(), r.headers.get_content_type()


def biggest(url):
    """Ask well-known CDNs for their largest rendition."""
    u = re.sub(r"/s-l\d+\.", "/s-l1600.", url)                       # eBay
    u = re.sub(r"(\.(?:jpe?g|png|webp))_\d+x\d+[^/]*$", r"\1", u, flags=re.I)  # AliExpress / alicdn
    u = re.sub(r"_(?:\d+x\d*|\d*x\d+)(?=\.(?:jpe?g|png|webp))", "", u, flags=re.I)  # Shopify
    u = re.sub(r"/cache/[0-9a-f]{32}/", "/", u)                      # Magento resized cache
    if re.search(r"[?&](?:[\w.-]*resize|w|h|width|height|size)=", u, re.I):
        u = u.split("?", 1)[0]                                       # resize query (EdgeOne, imgix...)
    return u


def candidates(page_url, body):
    text = body.decode("utf-8", "replace")
    flat = html.unescape(text).replace("\\/", "/")
    found = []

    def push(u):
        if not u:
            return
        u = urljoin(page_url, html.unescape(u.strip()))
        if u.startswith("//"):
            u = "https:" + u
        if urlparse(u).scheme in ("http", "https") and not SKIP.search(u):
            found.append(biggest(u))

    for m in re.finditer(r'<meta[^>]+(?:property|name)=["\'](?:og:image|twitter:image)[^"\']*["\'][^>]*>', text, re.I):
        c = re.search(r'content=["\']([^"\']+)', m.group(0))
        push(c and c.group(1))
    for m in re.finditer(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', text, re.I | re.S):
        try:
            data = json.loads(m.group(1))
        except Exception:
            continue
        stack = [data]
        while stack:
            d = stack.pop()
            if isinstance(d, list):
                stack.extend(d)
            elif isinstance(d, dict):
                img = d.get("image")
                for i in (img if isinstance(img, list) else [img]):
                    push(i.get("url") if isinstance(i, dict) else i)
                stack.extend(v for v in d.values() if isinstance(v, (list, dict)))
    for m in re.finditer(r"<img\b[^>]*>", text, re.I):
        tag = m.group(0)
        for attr in ("data-zoom-image", "data-large", "data-full", "data-src", "data-original", "src"):
            a = re.search(attr + r'=["\']([^"\']+)', tag, re.I)
            if a:
                push(a.group(1))
                break
        ss = re.search(r'srcset=["\']([^"\']+)', tag, re.I)
        if ss:
            push(ss.group(1).split(",")[-1].strip().split(" ")[0])
    for u in URL_RE.findall(flat):
        push(u)
    seen, out = set(), []
    for u in found:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def save_jpeg(raw, path):
    im = Image.open(io.BytesIO(raw))
    im.load()
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        im = bg
    else:
        im = im.convert("RGB")
    im.thumbnail((2000, 2000))
    for q in (92, 85, 78, 70):
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=q, optimize=True)
        if buf.tell() <= MAX_BYTES:
            break
    path.write_bytes(buf.getvalue())
    return im.size


def cmd_images(a, out, n, index):
    body, _ = fetch(a.url)
    urls = candidates(a.url, body)
    kept, seen_hash, tried = 0, set(), 0
    for u in urls:
        if kept >= a.max or tried >= 60:
            break
        tried += 1
        try:
            raw, ctype = fetch(u)
            im = Image.open(io.BytesIO(raw))
            if min(im.size) < a.min_side:
                continue
            h = hashlib.sha1(im.convert("L").resize((16, 16)).tobytes()).hexdigest()
            if h in seen_hash:
                continue
            seen_hash.add(h)
            kept += 1
            name = f"{n}_{kept:02d}.jpg"
            w, hgt = save_jpeg(raw, out / name)
            index.append(f"{name}\t{w}\t{hgt}\t{u}")
        except Exception:
            continue
    if not kept:
        raise RuntimeError(f"no image of at least {a.min_side}px among {len(urls)} candidates on the page")
    return f"{kept} images from {len(urls)} candidates"


def cmd_file(a, out, n, index):
    raw, _ = fetch(a.url)
    name = f"{n}_01.jpg"
    w, h = save_jpeg(raw, out / name)
    index.append(f"{name}\t{w}\t{h}\t{a.url}")
    return "1 image"


def parser():
    p = argparse.ArgumentParser(prog="grab", exit_on_error=False)
    sub = p.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("images")
    i.add_argument("url")
    i.add_argument("--max", type=int, default=15)
    i.add_argument("--min-side", type=int, default=600)
    f = sub.add_parser("file")
    f.add_argument("url")
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--request-file", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    index, n = [], 0
    for line in Path(args.request_file).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        n += 1
        try:
            a = parser().parse_args(shlex.split(line))
            note = {"images": cmd_images, "file": cmd_file}[a.cmd](a, out, n, index)
            status = "ok"
        except BaseException as e:
            if isinstance(e, KeyboardInterrupt):
                raise
            note = " ".join(str(e).split())[:300] or type(e).__name__
            (out / f"{n}_error.txt").write_text(traceback.format_exc(), encoding="utf-8")
            status = "error"
        with open(out / "status.tsv", "a", encoding="utf-8") as fh:
            fh.write(f"{status}\t{n}\t{line}\t{note}\n")
        print(f"{status}\t{n}\t{line}\t{note}", flush=True)
    (out / "index.tsv").write_text("\n".join(index) + ("\n" if index else ""), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
