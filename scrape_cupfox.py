#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓取 cupfox.love 的公开页面，生成可离线使用的 data.jsonl。

用法:
  python scrape_cupfox.py                 # 抓取 sitemap 中全部公开片单和文章
  python scrape_cupfox.py --limit 5       # 只抓前 5 个内容页，便于调试
  python scrape_cupfox.py --refresh        # 忽略 HTML 缓存重新下载

脚本只读取公开 HTML 和 sitemap，不调用播放源、不提交表单，也不下载海报二进制；
图片地址保留为原站/图片 CDN URL。抓取完成后请运行 `python build_site.py` 重新生成静态页。
"""
from __future__ import annotations

import argparse
import hashlib
import html as html_lib
import json
import re
import shutil
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data.jsonl"
CACHE = ROOT / ".cupfox-cache"
HOST = "https://cupfox.love"
UA = "Mozilla/5.0 (compatible; CupfoxCloneResearch/1.0)"

CATEGORY_NAMES = {
    "精选片单": "featured",
    "地区与形式": "region",
    "类型题材": "genre",
    "细分题材": "subgenre",
    "风格元素": "style",
    "观看顺序": "order",
    "获奖作品": "award",
    "专业评选": "pro",
    "导演代表作": "director",
    "演员代表作": "actor",
}

FEATURED_POSTS = [
    "这些顶级反派让主角靠边站",
    "盘点近10年最精彩的10部悬疑片",
    "盘点史上最伟大的越狱电影",
    "盘点十大电影萌物，你想抱走哪只？",
    "每一帧都是壁纸！5部画面绝美的动画电影",
]

def clean_text(value: str) -> str:
    value = html_lib.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()

def slug_id(prefix: str, value: str) -> str:
    return prefix + "-" + urllib.parse.quote(value, safe="").lower()

def absolute_url(value: str) -> str:
    return urllib.parse.urljoin(HOST + "/", html_lib.unescape(value))

def fetch(url: str, refresh: bool = False, pause: float = 0.12) -> str:
    CACHE.mkdir(exist_ok=True)
    path_part = urllib.parse.unquote(urllib.parse.urlparse(url).path).strip("/") or "home"
    readable = re.sub(r"[^a-zA-Z0-9._-]", "_", path_part)[:100]
    key = readable + "-" + hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    path = CACHE / (key + ".html")
    if path.exists() and not refresh:
        return path.read_text(encoding="utf-8", errors="ignore")
    parsed = urllib.parse.urlsplit(url)
    encoded_url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, urllib.parse.quote(urllib.parse.unquote(parsed.path), safe="/%"), parsed.query, parsed.fragment))
    req = urllib.request.Request(encoded_url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"})
    last = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                body = response.read().decode("utf-8", errors="replace")
            path.write_text(body, encoding="utf-8")
            time.sleep(pause)
            return body
        except Exception as exc:
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"下载失败: {url}: {last}")

def sitemap_urls(refresh: bool = False) -> list[str]:
    text = fetch(HOST + "/sitemap.xml", refresh=refresh, pause=0)
    urls = [html_lib.unescape(x) for x in re.findall(r"<loc>\s*(.*?)\s*</loc>", text, flags=re.S)]
    return [urllib.parse.urljoin(HOST, urllib.parse.urlsplit(url).path) for url in urls]

def page_kind(url: str) -> str:
    path = urllib.parse.urlparse(url).path.strip("/")
    if path.startswith("list/"):
        return "list"
    if path.startswith("post/"):
        return "post"
    if path.startswith("lists/"):
        return "lists"
    if path.startswith("posts"):
        return "posts"
    return "other"

def page_name(url: str) -> str:
    path = urllib.parse.urlparse(url).path.strip("/")
    return urllib.parse.unquote(path.split("/", 1)[1]) if "/" in path else ""

def first(pattern: str, text: str, flags: int = re.S) -> str:
    match = re.search(pattern, text, flags)
    return clean_text(match.group(1)) if match else ""

def raw_first(pattern: str, text: str, flags: int = re.S) -> str:
    match = re.search(pattern, text, flags)
    return match.group(1) if match else ""

def parse_category_page(url: str, text: str) -> list[dict]:
    # 原站的分类页用 /list/<片单名> 卡片链接，图片 alt 即片单名。
    found = []
    seen = set()
    for match in re.finditer(r'<a\b[^>]*href=["\'](/list/[^"\']+)["\'][^>]*>(.*?)</a>', text, re.S | re.I):
        href, body = match.groups()
        name = first(r'<img\b[^>]*alt=["\']([^"\']+)', body, re.I) or clean_text(body)
        name = name.strip()
        if name and name not in seen:
            found.append({"name": name, "url": absolute_url(href), "cover": first(r'<img\b[^>]*src=["\']([^"\']+)', body, re.I)})
            seen.add(name)
    return found

def parse_movie_cards(text: str, list_name: str) -> list[dict]:
    # 每部影片由 <h1 id="片名"> 后面的 my-2 flex 区块组成。
    headings = list(re.finditer(r'<h1\b[^>]*id=["\']([^"\']+)["\'][^>]*>(.*?)</h1>', text, re.S | re.I))
    cards = []
    for index, heading in enumerate(headings):
        raw_title = clean_text(heading.group(2))
        if not raw_title or raw_title == list_name:
            continue
        end = headings[index + 1].start() if index + 1 < len(headings) else text.find("版权声明：", heading.end())
        end = end if end > heading.end() else min(len(text), heading.end() + 12000)
        block = text[heading.end():end]
        image = re.search(r'<img\b[^>]*src=["\']([^"\']*?/images/[^"\']+)["\'][^>]*alt=["\']([^"\']*)', block, re.S | re.I)
        if image:
            cover, alt = image.group(1), image.group(2)
        else:
            image = re.search(r'<img\b[^>]*alt=["\']([^"\']*)["\'][^>]*src=["\']([^"\']*?/images/[^"\']+)', block, re.S | re.I)
            cover, alt = (image.group(2), image.group(1)) if image else ("", "")
        title = clean_text(alt) or re.sub(r"^\d+[.、]\s*", "", raw_title)
        title = re.sub(r"^\d+\s*", "", title) if not cover else title
        if not title:
            continue
        rating = first(r'font-bold[^>]*>([0-9]+(?:\.[0-9]+)?)</div>', block, re.I)
        count = first(r'>([0-9.万千百+]+)<!--.*?-->人评价', block, re.I) or first(r'>([0-9.万千百+]+)\s*人评价', block, re.I)
        labels = raw_first(r'<span[^>]*>标签：</span>(.*?)</div>', block, re.S | re.I)
        label_values = [clean_text(x) for x in re.findall(r'<span[^>]*>(.*?)</span>', labels, re.S | re.I) if clean_text(x)]
        director = first(r'<span[^>]*>导演：</span>(.*?)</div>', block, re.I)
        actor_markup = raw_first(r'<span[^>]*>主演：</span>(.*?)</div>', block, re.S | re.I)
        actors = [clean_text(x) for x in re.findall(r'<span[^>]*>(.*?)</span>', actor_markup, re.S | re.I) if clean_text(x)]
        year = label_values[0] if label_values and re.fullmatch(r"\d{4}", label_values[0]) else ""
        region = label_values[1] if year and len(label_values) > 1 else (label_values[0] if label_values else "")
        tags = label_values[2:] if year else label_values[1:]
        badge = first(r'<img\b[^>]*alt=["\']([^"\']+)["\'][^>]*width=["\']100%', block, re.I)
        douban_id = first(r'movie\.douban\.com/subject/(\d+)', block, re.I)
        if not douban_id and cover:
            douban_id = first(r'/images/(\d+)\.', cover, re.I)
        if not any((cover, rating, year, director, actors)):
            continue
        cards.append({"title": title, "cover": absolute_url(cover) if cover else "", "rate": rating, "count": count,
                      "year": year, "region": region, "tags": tags, "director": director, "actors": actors,
                      "badge": badge, "episodes": 0, "douban_id": douban_id})
    return cards

def parse_post(url: str, text: str) -> dict:
    title = page_name(url)
    if not title:
        title = first(r'<h1[^>]*>(.*?)</h1>', text)
    author = first(r'href=["\']/author/[^"\']+["\'][^>]*>\s*([^<]+)', text, re.I) or "茶杯狐"
    date = first(r'<div[^>]*>\s*(20\d{2}[-/]\d{1,2}[-/]\d{1,2})\s*</div>', text, re.I)
    article_start = text.find('<article')
    article = text[article_start:] if article_start >= 0 else text
    header_end = article.find('<ins')
    header = article[:header_end] if header_end > 0 else article[:5000]
    tags = [clean_text(x) for x in re.findall(r'rounded-full[^>]*>\s*<span[^>]*>(.*?)</span>', header, re.S | re.I)]
    tags = list(dict.fromkeys(x for x in tags if x and x not in {"原创", author}))
    article = article[:article.find("版权声明：")] if "版权声明：" in article else article
    sections = []
    heads = list(re.finditer(r'<h1\b[^>]*id=["\']([^"\']+)["\'][^>]*>(.*?)</h1>', article, re.S | re.I))
    intro_end = heads[0].start() if heads else len(article)
    intro_markup = raw_first(r'<div\b[^>]*class=["\'][^"\']*mdx[^"\']*["\'][^>]*>\s*(.*)', article[:intro_end], re.S | re.I)
    intro = clean_text(intro_markup)
    for index, head in enumerate(heads):
        section_text = article[head.end():(heads[index + 1].start() if index + 1 < len(heads) else len(article))]
        body = clean_text(re.sub(r'<img\b[^>]*>', ' ', section_text, flags=re.I))
        images = [absolute_url(x) for x in re.findall(r'<img\b[^>]*src=["\']([^"\']+)', section_text, re.S | re.I)]
        sections.append({"h": clean_text(head.group(2)), "body": body, "images": images})
    cover = ""
    images = re.findall(r'<img\b[^>]*src=["\']([^"\']+)', article, re.S | re.I)
    if images:
        cover = absolute_url(images[0])
    return {"type": "post", "id": slug_id("post", title), "title": title, "author": author, "date": date,
            "tags": tags, "cover": cover, "intro": intro, "sections": sections, "source": url}

def build_data(refresh: bool = False, limit: int | None = None, workers: int = 6) -> list[dict]:
    urls = sitemap_urls(refresh=refresh)
    list_urls = [u for u in urls if page_kind(u) == "list"]
    post_urls = [u for u in urls if page_kind(u) == "post"]
    lists_pages = [u for u in urls if page_kind(u) == "lists"]
    if limit is not None:
        list_urls = list_urls[:limit]
        post_urls = post_urls[:limit]
    all_records: list[dict] = []
    category_lists: dict[str, list[dict]] = {k: [] for k in CATEGORY_NAMES.values()}
    list_meta: dict[str, dict] = {}
    for url in lists_pages:
        name = page_name(url)
        category_id = CATEGORY_NAMES.get(name, "featured")
        text = fetch(url, refresh=refresh)
        for item in parse_category_page(url, text):
            item["category"] = category_id
            list_meta[item["name"]] = item
            category_lists.setdefault(category_id, []).append(item)
    movies: dict[str, dict] = {}
    lists: list[dict] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        list_pages = list(pool.map(lambda value: fetch(value, refresh=refresh), list_urls))
    for index, (url, text) in enumerate(zip(list_urls, list_pages), 1):
        name = page_name(url)
        if index == 1 or index % 20 == 0 or index == len(list_urls):
            print(f"[{index}/{len(list_urls)}] 已解析片单 {name}")
        category = list_meta.get(name, {}).get("category", "featured")
        movie_ids = []
        for card in parse_movie_cards(text, name):
            mid = "movie-db" + card["douban_id"] if card.get("douban_id") else slug_id("movie", card["title"])
            if mid not in movies:
                movies[mid] = {"type": "movie", "id": mid, "title": card["title"], "orig": "", "year": card["year"],
                               "region": card["region"], "rate": card["rate"], "count": card["count"], "tags": card["tags"],
                               "director": card["director"], "actors": card["actors"], "badge": card["badge"],
                               "syn": "", "episodes": card["episodes"], "cover": card["cover"], "douban_id": card.get("douban_id", ""), "source": url}
            else:
                movie = movies[mid]
                for field in ("year", "region", "rate", "count", "tags", "director", "actors", "badge", "cover"):
                    if card.get(field) and (not movie.get(field) or field in {"cover", "rate", "count"}):
                        movie[field] = card[field]
            movie_ids.append(mid)
        meta = list_meta.get(name, {})
        lists.append({"type": "list", "id": slug_id("list", name), "name": name, "category": category,
                      "movies": movie_ids, "cover": meta.get("cover", "") or (next((movies[x]["cover"] for x in movie_ids if movies[x].get("cover")), "")),
                      "source": url})
    with ThreadPoolExecutor(max_workers=max(1, min(workers, 4))) as pool:
        post_pages = list(pool.map(lambda value: fetch(value, refresh=refresh), post_urls))
    posts = [parse_post(url, text) for url, text in zip(post_urls, post_pages)]
    featured_order = {title: index for index, title in enumerate(FEATURED_POSTS)}
    posts.sort(key=lambda post: (featured_order.get(post["title"], len(FEATURED_POSTS)), post["title"]))
    print(f"已解析文章 {len(posts)} 篇")
    categories = []
    for name, cid in CATEGORY_NAMES.items():
        categories.append({"type": "category", "id": cid, "name": name, "cover": next((x.get("cover", "") for x in category_lists.get(cid, []) if x.get("cover")), "")})
    return categories + lists + list(movies.values()) + posts

def validate(records: list[dict]) -> None:
    ids = {r["id"] for r in records}
    lists = [r for r in records if r.get("type") == "list"]
    missing = [(r["name"], mid) for r in lists for mid in r.get("movies", []) if mid not in ids]
    if missing:
        raise ValueError(f"存在失效影片引用: {missing[:5]}")
    if not lists or not any(r.get("movies") for r in lists):
        raise ValueError("没有解析到片单影片")
    for r in records:
        if r.get("type") == "movie" and not r.get("title"):
            raise ValueError("存在空影片标题")

def merge_seed(records: list[dict]) -> None:
    """保留项目早期手工补充的原名、简介和剧集数，爬虫字段优先。"""
    seed_path = ROOT / "data.seed.jsonl"
    if not seed_path.exists():
        return
    seed = [json.loads(line) for line in seed_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    by_title = {x.get("title"): x for x in seed if x.get("type") == "movie" and x.get("title")}
    for record in records:
        if record.get("type") != "movie":
            continue
        old = by_title.get(record.get("title"))
        if not old:
            continue
        for field in ("orig", "syn", "episodes"):
            if old.get(field) and not record.get(field):
                record[field] = old[field]

def save_records(records: list[dict]) -> None:
    if DATA.exists():
        backup = DATA.with_suffix(".jsonl.bak")
        shutil.copy2(DATA, backup)
    with DATA.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="忽略 HTML 缓存")
    parser.add_argument("--limit", type=int, help="限制片单和文章数量，调试用")
    parser.add_argument("--workers", type=int, default=6, help="并发下载数，默认 6")
    args = parser.parse_args()
    records = build_data(refresh=args.refresh, limit=args.limit, workers=args.workers)
    merge_seed(records)
    validate(records)
    save_records(records)
    from collections import Counter
    counts = Counter(r["type"] for r in records)
    print("完成:", dict(counts), "缓存:", CACHE)

if __name__ == "__main__":
    main()
