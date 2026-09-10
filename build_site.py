#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 data.jsonl 生成可被搜索引擎直接抓取的静态 HTML。

用法:
  python build_site.py
  python build_site.py --base-url https://example.com
"""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import unquote, urljoin

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data.jsonl"
SITE = "片单对照"
TAGLINE = "看一部片还在哪些名单里"
ORIGIN = "https://www.cupfox.xin"
HOME_TITLE = f"{SITE} · 公开片单的交叉索引"
HOME_DESCRIPTION = (
    "片单对照把多份公开名单叠在一起：一部作品同时出现在哪些名单、"
    "和哪几部共享最多名单、系列该按什么顺序看。不转载影评，不提供播放。"
)
BUILD_DATE = date.today().isoformat()
ASSET_V = "20260910d"
HUB_BLURBS = {
    "featured": "这里是全部公开片单的入口。每份名单页会写出它和其它名单重叠了多少，而不是复述原名单的宣传语。",
    "region": "按出品地和形式归类的名单。同一部作品常常同时出现在地区名单和类型名单里，重叠关系在各名单页里。",
    "genre": "按类型归类的名单。类型名只用来分堆，判断一部片值不值得看，要看它还进了哪些专业或获奖名单。",
    "subgenre": "更细的题材名单。和类型名单叠在一起时，可以看出一部片是「只在细类里」还是「细类和主类都有」。",
    "style": "按风格归类的名单。风格标签主观，所以本页只提供对照，不把风格写成推荐理由。",
    "order": "系列观看顺序名单。详情里按原名单给出上一跳和下一跳，不另编一套顺序。",
    "award": "颁奖结果名单。和专业评选名单重叠时，比单独看一座奖杯更能说明反复出现的原因。",
    "pro": "影史和影评人评选名单。本站关心的是一份名单和另一份名单叠了多少，而不是再抄一份榜单前言。",
    "director": "导演作品名单。用来从导演走进交叉，再看同一人还出现在哪些类型或获奖名单。",
    "actor": "演员作品名单。用法和导演名单一样：当人物入口，不代替片单原文。",
}

NAV_LINKS = (("home", "/index.html", "首页"), ("lists", "/lists.html", "片单"), ("method", "/method.html", "方法"))


def esc(value) -> str:
    return html.escape(str(value or ""), quote=True)


def seo_keywords(*parts: str) -> str:
    seen: list[str] = []
    for part in parts:
        for item in str(part or "").split(","):
            item = item.strip()
            if item and item not in seen:
                seen.append(item)
    return ",".join(seen[:28])


def clip_desc(text: str, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def file_slug(item_id: str) -> str:
    text = unquote(str(item_id or ""))
    text = re.sub(r'[<>:"/\\|?*]+', "-", text).rstrip(". ")
    return (text[:120] or "item")


def is_img(url: str) -> bool:
    return isinstance(url, str) and url.lower().startswith(("http://", "https://"))


def hash_hue(text: str) -> int:
    h = 0
    for ch in str(text or "x"):
        h = (h * 31 + ord(ch)) & 0xFFFFFF
    return h % 360


POSTER_BG = (
    "linear-gradient(135deg,#3d6cb9,#152238)",
    "linear-gradient(135deg,#7a3d9e,#1a1228)",
    "linear-gradient(135deg,#2a7a6e,#10201c)",
    "linear-gradient(135deg,#b05a2a,#231610)",
    "linear-gradient(135deg,#3a7a9e,#101820)",
    "linear-gradient(135deg,#8a3d5c,#1c1014)",
    "linear-gradient(135deg,#4a6a2a,#14180e)",
    "linear-gradient(135deg,#2a4a8a,#0e1424)",
    "linear-gradient(135deg,#8a6a2a,#1c180e)",
    "linear-gradient(135deg,#5a3d8a,#161020)",
)


def poster_bg(obj: dict) -> str:
    key = obj.get("id") or obj.get("title") or obj.get("name") or "x"
    return POSTER_BG[hash_hue(key) % len(POSTER_BG)]


def public_cover(url: str) -> str:
    return url if is_img(url) else ""


def poster_block(obj: dict, alt: str = "", cls: str = "ph") -> str:
    title = alt or obj.get("title") or obj.get("name") or ""
    cover = obj.get("cover") or ""
    if is_img(cover):
        return (
            f'<img class="{cls}" src="{esc(cover)}" loading="lazy" '
            f'referrerpolicy="no-referrer" alt="{esc(title)}">'
        )
    return (
        f'<div class="{cls} gen-ph" style="background:{poster_bg(obj)}" '
        f'role="img" aria-label="{esc(title)}"></div>'
    )


def list_thumb(lst: dict, data: dict) -> str:
    if is_img(lst.get("cover") or ""):
        return poster_block(lst)
    cells = []
    for mid in (lst.get("movies") or [])[:4]:
        movie = data["movie_by"].get(mid)
        if movie:
            cells.append(f'<div class="coll-cell">{poster_block(movie)}</div>')
    if not cells:
        return poster_block(lst)
    return f'<div class="ph collage">{"".join(cells)}</div>'


def rate_num(movie) -> float:
    try:
        return float(movie.get("rate") or 0)
    except (TypeError, ValueError):
        return 0.0


def load_data() -> dict:
    cats, lists, movies, posts = [], [], [], []
    cat_by, list_by, movie_by, post_by = {}, {}, {}, {}
    for line in DATA.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        item = json.loads(line)
        kind = item.get("type")
        if kind == "category":
            cats.append(item)
            cat_by[item["id"]] = item
        elif kind == "list":
            lists.append(item)
            list_by[item["id"]] = item
        elif kind == "movie":
            movies.append(item)
            movie_by[item["id"]] = item
        elif kind == "post":
            posts.append(item)
            post_by[item["id"]] = item
    lists_by_movie = defaultdict(list)
    for lst in lists:
        for mid in lst.get("movies") or []:
            lists_by_movie[mid].append(lst)
    movie_list_n = {mid: len(lsts) for mid, lsts in lists_by_movie.items()}
    top_crossed = sorted(
        (m for m in movies if movie_list_n.get(m["id"], 0) >= 3),
        key=lambda m: (-movie_list_n.get(m["id"], 0), -rate_num(m)),
    )[:12]
    return {
        "categories": cats,
        "lists": lists,
        "movies": movies,
        "posts": posts,
        "cat_by": cat_by,
        "list_by": list_by,
        "movie_by": movie_by,
        "post_by": post_by,
        "lists_by_movie": lists_by_movie,
        "movie_list_n": movie_list_n,
        "top_crossed": top_crossed,
    }


def movie_url(item_id: str) -> str:
    return f"/movie/{file_slug(item_id)}.html"


def list_url(item_id: str) -> str:
    return f"/list/{file_slug(item_id)}.html"


def post_url(item_id: str) -> str:
    return f"/post/{file_slug(item_id)}.html"


def cat_url(item_id: str) -> str:
    if item_id == "featured":
        return "/lists.html"
    return f"/cat/{file_slug(item_id)}.html"


def list_cross(lst: dict, movies: list, data: dict) -> dict:
    lid = lst["id"]
    only, shared = [], []
    neighbor = Counter()
    for movie in movies:
        others = [item for item in data["lists_by_movie"].get(movie["id"], []) if item["id"] != lid]
        if others:
            shared.append((movie, len(others)))
            for other in others:
                neighbor[other["id"]] += 1
        else:
            only.append(movie)
    shared.sort(key=lambda item: -item[1])
    neigh = []
    for oid, count in neighbor.most_common(5):
        other = data["list_by"].get(oid)
        if other:
            neigh.append((other, count))
    directors = Counter(movie.get("director") for movie in movies if movie.get("director"))
    return {
        "only": only,
        "shared": shared,
        "neighbors": neigh,
        "directors": directors.most_common(3),
    }


def list_lead(lst: dict, movies: list, cat_name: str, cross: dict | None = None) -> str:
    name = lst.get("name") or "这份片单"
    n = len(movies)
    if cross:
        return (
            f"「{name}」按原名单顺序对照 {n} 部。"
            f"{len(cross['only'])} 部只在这份名单，{len(cross['shared'])} 部还出现在其它名单。"
        )
    return f"「{name}」按原名单顺序对照 {n} 部。"


def abs_url(path: str) -> str:
    return urljoin(ORIGIN.rstrip("/") + "/", path.lstrip("/"))


def ph(obj: dict, alt: str = "") -> str:
    return poster_block(obj, alt)


def card(title: str, obj: dict, href: str, data: dict | None = None) -> str:
    thumb = list_thumb(obj, data) if data is not None else poster_block(obj, title)
    return (
        f'<a class="card" href="{esc(href)}">{thumb}'
        f'<div class="grad"></div><div class="cap"><b>{esc(title)}</b></div></a>'
    )


def hub_card(title: str, obj: dict, href: str, data: dict | None = None) -> str:
    thumb = list_thumb(obj, data) if data is not None else poster_block(obj, title)
    return (
        f'<a class="hub-card" href="{esc(href)}"><div class="thumb">{thumb}</div>'
        f'<div class="t">{esc(title)}</div></a>'
    )


def movie_item(movie: dict, num: int) -> str:
    tags = " ".join(movie.get("tags") or [])
    actors = " / ".join(movie.get("actors") or [])
    kind = "series" if (movie.get("episodes") or 0) > 0 else "film"
    douban = ""
    if movie.get("douban_id"):
        href = f'https://movie.douban.com/subject/{esc(movie["douban_id"])}/'
        douban = f'<a class="douban-link" href="{href}" target="_blank" rel="noopener noreferrer">豆瓣 ↗</a>'
    else:
        douban = '<span class="douban-link">豆瓣</span>'
    badge = (
        f'<div class="m-badge-cell"><span class="m-badge">{esc(movie.get("badge"))}</span></div>'
        if movie.get("badge")
        else ""
    )
    meta = " ".join(x for x in (str(movie.get("year") or ""), movie.get("region") or "", tags) if x)
    return f'''<div class="m-item" id="m{num}" data-kind="{kind}">
    <a class="m-detail-hit" href="{esc(movie_url(movie["id"]))}" aria-label="查看{esc(movie.get("title"))}详情"></a>
    <h3 class="m-title"><span class="num">#</span>{esc(movie.get("title"))}</h3>
    <div class="m-poster">{ph(movie)}</div>
    <div class="m-main">
      <div class="m-rate"><span class="big">{esc(movie.get("rate") or "—")}</span><span class="m-rate-side"><span class="stars">★★★★★</span><span class="count">{esc(movie.get("count") or "")}人评价 | 来源：{douban}</span></span></div>
      <div class="m-meta"><b>标签</b>{esc(meta or "—")}</div>
      <div class="m-meta"><b>导演</b>{esc(movie.get("director") or "—")}</div>
      <div class="m-meta"><b>主演</b>{esc(actors or "—")}</div>
    </div>
    {badge}
  </div>'''


def nav_html(page: str) -> str:
    links = "".join(
        f'<a href="{href}" data-p="{key}" class="{"active" if page == key else ""}">{label}</a>'
        for key, href, label in NAV_LINKS
    )
    return f'''<nav class="nav"><div class="wrap nav-in">
  <a class="logo" href="/index.html" aria-label="{SITE}">
    <span class="logo-mark">对</span>
    <span>{SITE}</span>
  </a>
  <div class="nav-links">{links}</div>
  <div class="nav-right">
    <button class="icon-btn" id="searchBtn" aria-label="搜索"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg></button>
    <button class="toggle" id="themeBtn" aria-label="切换主题"><span class="dot"></span></button>
  </div>
</div></nav>'''


def foot_html() -> str:
    return f'''<footer>
  <div class="wrap foot-grid">
    <div class="foot-brand">
      <div class="logo" style="font-size:20px;margin-bottom:10px"><span class="logo-mark">对</span><span>{SITE}</span></div>
      <p class="foot-desc">独立片单交叉索引：计算重叠、年份和观看顺序。不转载其它站点的盘点文章，不提供在线播放。</p>
      <p class="foot-mail">联系邮箱 <a href="mailto:2201219073@qq.com">2201219073@qq.com</a></p>
    </div>
    <div class="foot-col">
      <h3>浏览</h3>
      <a href="/lists.html">全部片单</a>
      <a href="/cat/order.html">观看顺序</a>
      <a href="/cat/award.html">获奖作品</a>
      <a href="/method.html">方法</a>
    </div>
    <div class="foot-col">
      <h3>站点</h3>
      <a href="/about.html#about">关于</a>
      <a href="/about.html#copyright">版权声明</a>
      <a href="/about.html#contact">联系</a>
      <a href="/about.html#complaint">侵权投诉</a>
    </div>
  </div>
  <div class="wrap"><div class="copy">© {SITE} · 交叉索引 · 不提供在线播放</div></div>
</footer>'''


def page_doc(
    *,
    title: str,
    description: str,
    nested: bool,
    page: str,
    body: str,
    extra_head: str = "",
    body_class: str = "",
    json_ld: dict | None = None,
    noindex: bool = False,
    image: str = "",
    scripts: str = "",
    path: str = "",
    keywords: str = "",
) -> str:
    robots = "noindex,follow" if noindex else "index,follow"
    canonical = abs_url(path) if path and not noindex else ""
    canon = f'<link rel="canonical" href="{esc(canonical)}"/>' if canonical else ""
    og_url = f'<meta property="og:url" content="{esc(canonical)}"/>' if canonical else ""
    og_img = f'<meta property="og:image" content="{esc(image)}"/>' if image else ""
    keys = seo_keywords(keywords) if keywords and not noindex else ""
    key_tag = f'<meta name="keywords" content="{esc(keys)}"/>' if keys else ""
    ld = ""
    if json_ld:
        if canonical and "url" not in json_ld and "@graph" not in json_ld:
            json_ld = {**json_ld, "url": canonical}
        ld = "<script type=\"application/ld+json\">" + json.dumps(json_ld, ensure_ascii=False).replace("<", "\\u003c") + "</script>"
    cls = f' class="{body_class}"' if body_class else ""
    return f'''<!DOCTYPE html>
<html lang="zh-CN" data-theme="dark" translate="no" class="notranslate">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<meta name="google" content="notranslate"/>
<title>{esc(title)}</title>
<meta name="description" content="{esc(clip_desc(description))}"/>
{key_tag}
<meta name="robots" content="{robots}"/>
<meta property="og:site_name" content="{SITE}"/>
<meta property="og:locale" content="zh_CN"/>
<meta property="og:title" content="{esc(title)}"/>
<meta property="og:description" content="{esc(clip_desc(description))}"/>
<meta property="og:type" content="website"/>
{og_url}
{og_img}
{canon}
<link rel="icon" href="/favicon.ico" sizes="any"/>
<link rel="stylesheet" href="/styles.css?v={ASSET_V}"/>
{extra_head}
{ld}
</head>
<body{cls}>
<div id="nav">{nav_html(page)}</div>
{body}
<div id="foot">{foot_html()}</div>
<script>window.PAGE={json.dumps(page)};</script>
<script src="/app.js?v={ASSET_V}"></script>
{scripts}
</body>
</html>
'''


def posts_mentioning(movie: dict, posts: list) -> list:
    title = movie.get("title") or ""
    if len(title) < 2:
        return []
    found = []
    for post in posts:
        blob = "\n".join(
            [post.get("title") or "", post.get("intro") or ""]
            + [f"{s.get('h','')} {s.get('body','')}" for s in post.get("sections") or []]
        )
        if title in blob:
            found.append(post)
    return found


def graph_reasons(movie, memberships):
    by_cat = defaultdict(list)
    for lst in memberships:
        by_cat[lst.get("category")].append(lst)
    reasons = []
    consensus = by_cat["pro"] + by_cat["award"]
    if len(consensus) >= 3:
        shown = consensus[:4]
        extra = "等" if len(consensus) > 4 else ""
        reasons.append({
            "title": "专业评选共识",
            "body": "同时出现在" + "、".join(l["name"] for l in shown) + extra + "。",
            "lists": shown,
        })
    sub = by_cat["subgenre"]
    if len(sub) >= 2:
        reasons.append({
            "title": "题材交叉",
            "body": f'既在「{sub[0]["name"]}」，也在「{sub[1]["name"]}」。',
            "lists": sub[:2],
        })
    person = by_cat["actor"] + by_cat["director"]
    if person:
        reasons.append({
            "title": "人物入口",
            "body": f'可以从「{person[0]["name"]}」走进来，再看同一人的其它作品。',
            "lists": person[:1],
        })
    return reasons[:3]


def graph_hops(memberships, articles):
    by_cat = defaultdict(list)
    for lst in memberships:
        by_cat[lst.get("category")].append(lst)
    hops, seen = [], set()

    def add_list(lst, kind, desc):
        if not lst or lst["id"] in seen:
            return
        seen.add(lst["id"])
        hops.append({"kind": kind, "title": lst["name"], "href": list_url(lst["id"]), "desc": desc})

    add_list((by_cat["order"] or [None])[0], "order", "观看顺序，下一跳按名单走。")
    add_list((by_cat["actor"] or by_cat["director"] or [None])[0], "person", "人物片单，适合接着看同一人的其它作品。")
    add_list((by_cat["subgenre"] or by_cat["genre"] or by_cat["style"] or [None])[0], "topic", "题材片单，沿这条口味继续找。")
    return hops[:3]


def order_chains(movie, memberships, data):
    out = []
    for lst in memberships:
        if lst.get("category") != "order":
            continue
        ids = lst.get("movies") or []
        try:
            index = ids.index(movie["id"])
        except ValueError:
            continue
        out.append({
            "list": lst,
            "index": index,
            "total": len(ids),
            "prev": data["movie_by"].get(ids[index - 1]) if index > 0 else None,
            "next": data["movie_by"].get(ids[index + 1]) if index < len(ids) - 1 else None,
        })
        if len(out) == 2:
            break
    return out


def neighbor_anchor(mid, other_id, lists):
    distance, lst, position, total = 9999, None, -1, 0
    for item in lists or []:
        try:
            a = (item.get("movies") or []).index(mid)
            b = (item.get("movies") or []).index(other_id)
        except ValueError:
            continue
        d = abs(a - b)
        if d < distance:
            distance, lst, position, total = d, item, b, len(item.get("movies") or [])
    return distance, lst, position, total


def neighbor_why(n) -> str:
    bits = []
    if n["shared_count"] > 1:
        bits.append(" · ".join(l["name"] for l in n["shared_lists"]))
    elif n["anchor_list"]:
        bits.append(n["anchor_list"]["name"])
        if n["position"] >= 0:
            bits.append(f'第 {n["position"] + 1} / {n["total"]} 部')
        if n["distance"] == 1:
            bits.append("名单里紧挨着")
    if n["same_director"]:
        bits.append("同一导演")
    elif n["same_actor"]:
        bits.append("同一主演")
    if n["movie"].get("year"):
        bits.append(str(n["movie"]["year"]))
    return " · ".join(bits)


def movie_graph(movie, data):
    mid = movie["id"]
    memberships = data["lists_by_movie"].get(mid) or []
    shared_count, shared_lists = defaultdict(int), defaultdict(list)
    for lst in memberships:
        for other in lst.get("movies") or []:
            if other == mid:
                continue
            shared_count[other] += 1
            shared_lists[other].append(lst)
    actors = movie.get("actors") or []
    neighbors = []
    for other_id, count in shared_count.items():
        other = data["movie_by"].get(other_id)
        if not other:
            continue
        lists = shared_lists[other_id]
        distance, anchor, position, total = neighbor_anchor(mid, other_id, lists)
        neighbors.append({
            "movie": other,
            "shared_count": count,
            "shared_lists": lists,
            "same_director": bool(movie.get("director") and other.get("director") == movie.get("director")),
            "same_actor": bool(actors) and any(a in (other.get("actors") or []) for a in actors),
            "distance": distance,
            "position": position,
            "total": total,
            "anchor_list": anchor,
        })
    neighbors.sort(
        key=lambda n: (
            -n["shared_count"],
            n["distance"],
            0 if n["same_director"] else 1,
            0 if n["same_actor"] else 1,
            -rate_num(n["movie"]),
        )
    )
    neighbors = neighbors[:6]
    articles = posts_mentioning(movie, data["posts"])
    return {
        "memberships": memberships,
        "neighbors": neighbors,
        "reasons": graph_reasons(movie, memberships),
        "hops": graph_hops(memberships, articles),
        "orders": order_chains(movie, memberships, data),
        "articles": articles,
    }


def movie_json_ld(movie) -> dict:
    data = {
        "@context": "https://schema.org",
        "@type": "Movie",
        "name": movie.get("title"),
        "inLanguage": "zh-CN",
    }
    if movie.get("orig"):
        data["alternateName"] = movie["orig"]
    if movie.get("year"):
        data["dateCreated"] = str(movie["year"])
    if movie.get("director"):
        data["director"] = {"@type": "Person", "name": movie["director"]}
    if movie.get("actors"):
        data["actor"] = [{"@type": "Person", "name": name} for name in movie["actors"][:8]]
    cover = public_cover(movie.get("cover") or "")
    if cover:
        data["image"] = cover
    data["url"] = abs_url(movie_url(movie["id"]))
    if rate_num(movie):
        data["aggregateRating"] = {
            "@type": "AggregateRating",
            "ratingValue": str(movie.get("rate")),
            "bestRating": "10",
            "worstRating": "0",
        }
    return data


def desc_movie(movie, n_lists: int) -> str:
    bits = [movie.get("title") or "影片"]
    if movie.get("year"):
        bits.append(str(movie["year"]))
    tags = "、".join((movie.get("tags") or [])[:4])
    if tags:
        bits.append(tags)
    if movie.get("director"):
        bits.append("导演" + movie["director"])
    if movie.get("rate"):
        bits.append("豆瓣" + str(movie["rate"]))
    bits.append(f"入选{n_lists}个片单")
    syn = (movie.get("syn") or "").strip()
    text = "，".join(bits) + "。" + syn
    text += "详情页用来看它还出现在哪些名单里，不是播放页。"
    return clip_desc(text)


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def render_index(data) -> str:
    home_cats = [c for c in data["categories"] if c["id"] != "featured"]
    cat_links = "".join(
        f'<a class="cat-link" href="{esc(cat_url(cat["id"]))}">{esc(cat["name"])}</a>'
        for cat in home_cats
    )
    crossed = []
    for movie in data.get("top_crossed") or []:
        n = data["movie_list_n"].get(movie["id"], 0)
        crossed.append(
            f'<a class="cross-hit" href="{esc(movie_url(movie["id"]))}">'
            f'<span class="cross-hit-poster" style="position:relative;overflow:hidden;display:block;width:52px;height:74px;flex:0 0 52px">{poster_block(movie)}</span>'
            f'<div><b>{esc(movie.get("title"))}</b>'
            f"<span>出现在 {n} 份片单</span></div></a>"
        )
    sections = [
        f'''<section>
      <div class="sec-head"><div class="sec-title">交叉最多的作品</div><a class="btn-sm" href="/method.html">怎么算的</a></div>
      <p class="home-note">按「同时出现在几份名单」排序，不是热搜，也不是转载盘点。</p>
      <div class="cross-hits">{"".join(crossed)}</div>
    </section>''',
        '''<section id="tonight">
      <div class="sec-head"><div class="sec-title">今晚看什么</div></div>
      <p class="tonight-empty">点任意一个标签，从现有名单里抽三部。</p>
    </section>''',
    ]
    for cat in home_cats:
        rows = [lst for lst in data["lists"] if lst.get("category") == cat["id"]][:6]
        if not rows:
            continue
        cards = "".join(card(lst["name"], lst, list_url(lst["id"]), data) for lst in rows)
        sections.append(
            f'<section><div class="sec-head"><div class="sec-title">{esc(cat["name"])}</div>'
            f'<a class="btn-sm" href="{esc(cat_url(cat["id"]))}">更多</a></div>'
            f'<div class="sec-row">{cards}</div></section>'
        )
    n_lists = len(data["lists"])
    n_movies = len(data["movies"])
    n_multi = sum(1 for count in data["movie_list_n"].values() if count >= 3)
    body = f'''<section class="hero-plain">
  <div class="wrap">
    <p class="hero-kicker">独立片单交叉索引</p>
    <h1 class="home-h1">看一部作品还出现在哪些名单里</h1>
    <p class="hero-lead">本站不转载其它导航站的盘点文章，也不镜像海报。公开片单收进来之后，只计算重叠、年份和观看顺序。</p>
    <div class="hero-stats">
      <div><b>{n_lists}</b><span>份公开片单</span></div>
      <div><b>{n_movies}</b><span>部对照作品</span></div>
      <div><b>{n_multi}</b><span>部出现在 3 份以上名单</span></div>
    </div>
    <div class="hero-links">{cat_links}</div>
  </div>
</section>
<main class="wrap" id="cats">
  {"".join(sections)}
  <section class="home-seo" aria-label="站点介绍">
    <h2>和名单原文站的差别</h2>
    <p>名单标题和出品信息是公开事实，很多站点都会列出。本站多出来的是交叉：一份名单和另一份叠了多少、一部片只在这里还是到处都有、系列里的上一跳下一跳。</p>
    <p>影片详情页只给站内用户看交叉，不向搜索引擎要求收录。要了解计算方式，见<a href="/method.html">方法</a>。</p>
  </section>
</main>'''
    return page_doc(
        title=HOME_TITLE,
        description=HOME_DESCRIPTION,
        nested=False,
        page="home",
        body=body,
        scripts="<script>Cupfox.loadData().then(d=>Cupfox.bindTonight(document.getElementById('tonight'), d));</script>",
        path="index.html",
        keywords=seo_keywords(SITE, "片单交叉", "观看顺序"),
        json_ld={
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": SITE,
            "url": abs_url("index.html"),
            "description": HOME_DESCRIPTION,
            "inLanguage": "zh-CN",
            "publisher": {"@type": "Organization", "name": SITE, "email": "2201219073@qq.com"},
        },
    )


def render_hub(data, cat_id: str) -> str:
    cat = data["cat_by"].get(cat_id)
    title = cat["name"] if cat else "精选片单"
    lists = data["lists"] if cat_id == "featured" else [l for l in data["lists"] if l.get("category") == cat_id]
    menu = "".join(
        f'<a href="{esc(cat_url(c["id"]))}" class="{"active" if c["id"]==cat_id else ""}">{esc(c["name"])}</a>'
        for c in data["categories"]
    )
    grid = "".join(hub_card(l["name"], l, list_url(l["id"]), data) for l in lists)
    blurb = HUB_BLURBS.get(cat_id, "按名单对照挑片。")
    body = f'''<div class="wrap hub">
  <aside class="side-menu">{menu}</aside>
  <main>
    <h1 class="hub-title">{esc(title)} · {len(lists)}</h1>
    <p class="hub-lead">{esc(blurb)}</p>
    <div class="hub-grid">{grid}</div>
  </main>
</div>'''
    return page_doc(
        title=f"{title} · 交叉索引 - {SITE}",
        description=clip_desc(f"{title}共 {len(lists)} 份片单。{blurb}"),
        nested=(cat_id != "featured"),
        page="lists",
        body=body,
        path=cat_url(cat_id),
        keywords=seo_keywords(title, "片单", SITE),
    )


def render_list(lst, data) -> str:
    cat = data["cat_by"].get(lst.get("category"))
    movies = [data["movie_by"][mid] for mid in lst.get("movies") or [] if mid in data["movie_by"]]
    items = "".join(movie_item(m, i + 1) for i, m in enumerate(movies))
    toc = "".join(f'<a href="#m{i+1}">{i+1}. {esc(m.get("title"))}</a>' for i, m in enumerate(movies))
    cat_name = cat["name"] if cat else ""
    cross = list_cross(lst, movies, data)
    lead = list_lead(lst, movies, cat_name, cross)
    overlap_links = "".join(
        f'<a href="{esc(list_url(other["id"]))}">{esc(other["name"])} · {count} 部重叠</a>'
        for other, count in cross["neighbors"]
    )
    overlap_block = (
        f'<div class="overlap-lists">{overlap_links}</div>' if overlap_links else ""
    )
    stats = (
        f'<div class="list-stats">'
        f'<div class="list-stat"><b>{len(movies)}</b><span>本页条目</span></div>'
        f'<div class="list-stat"><b>{len(cross["only"])}</b><span>只在这份名单</span></div>'
        f'<div class="list-stat"><b>{len(cross["shared"])}</b><span>还出现在其它名单</span></div>'
        f'<div class="list-stat"><b>{len(cross["neighbors"])}</b><span>重叠最多的邻单</span></div>'
        f"</div>"
    )
    body = f'''<div class="wrap">
  <div class="crumb"><a href="/index.html">首页</a><span class="sep">/</span><a href="/lists.html">全部片单</a><span class="sep">/</span><span>{esc(lst.get("name"))}</span></div>
  <h1 class="page-title">{esc(lst.get("name"))} · 交叉对照 <span class="cat-tag">{esc(cat_name)}</span></h1>
  {stats}
  {overlap_block}
  <div class="filter-bar" id="filterBar">
    <button class="btn-sm active" data-f="all">全部</button>
    <button class="btn-sm" data-f="film">电影</button>
    <button class="btn-sm" data-f="series">剧集</button>
    <span class="list-count">共 {len(movies)} 部</span>
  </div>
  <div class="list-layout">
    <div class="list-back-col"><a class="list-back" href="/lists.html">‹ 全部片单</a></div>
    <div class="movie-list" id="movieList">{items or '<div class="empty">该片单没有影片</div>'}</div>
    <nav class="toc"><h4>内容导航</h4><div class="toc-links">{toc}</div></nav>
  </div>
</div>'''
    return page_doc(
        title=f'{lst.get("name")} · 交叉对照 - {SITE}',
        description=clip_desc(lead),
        nested=True,
        page="lists",
        body=body,
        body_class="list-detail-page",
        keywords=seo_keywords(lst.get("name"), "交叉对照", SITE),
        json_ld={
            "@context": "https://schema.org",
            "@type": "ItemList",
            "name": f'{lst.get("name")} · 交叉对照',
            "description": clip_desc(lead),
            "numberOfItems": len(movies),
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "name": m.get("title")}
                for i, m in enumerate(movies[:50])
            ],
        },
        path=list_url(lst["id"]),
    )


def render_movie(movie, data) -> str:
    graph = movie_graph(movie, data)
    memberships = graph["memberships"]
    grouped = []
    used = set()
    for cat in data["categories"]:
        lists = [l for l in memberships if l.get("category") == cat["id"]]
        if lists:
            grouped.append((cat, lists))
            used.update(l["id"] for l in lists)
    leftover = [l for l in memberships if l["id"] not in used]
    if leftover:
        grouped.append(({"id": "other", "name": "其它片单"}, leftover))
    tags = [movie.get("year"), movie.get("region"), *(movie.get("tags") or [])]
    tags = [t for t in tags if t]
    max_shared = graph["neighbors"][0]["shared_count"] if graph["neighbors"] else 0
    syn = (movie.get("syn") or "").strip()
    syn_block = ""
    if syn:
        more = '<span class="toggle-syn" id="toggleSyn">展开全部 ▾</span>' if len(syn) > 80 else ""
        syn_block = f'<p class="syn" id="syn">{esc(syn)}</p>{more}'
    reason_block = ""
    if graph["reasons"]:
        cards = []
        for r in graph["reasons"]:
            pills = "".join(f'<a href="{esc(list_url(l["id"]))}">{esc(l["name"])}</a>' for l in r["lists"])
            cards.append(
                f'<article class="reason-card"><h3>{esc(r["title"])}</h3><p>{esc(r["body"])}</p>'
                f'<div class="graph-pills">{pills}</div></article>'
            )
        reason_block = f'<div class="block"><h2>为什么在这些片单里</h2><div class="graph-reasons">{"".join(cards)}</div></div>'

    def step(mv, label, current=False):
        if not mv:
            return f'<div class="graph-ostep is-empty"><span>{label}</span><em>没有了</em></div>'
        inner = f'<div class="graph-nposter">{ph(mv)}</div><div class="graph-olabel"><span>{label}</span><b>{esc(mv.get("title"))}</b></div>'
        if current:
            return f'<div class="graph-ostep is-now">{inner}</div>'
        return f'<a class="graph-ostep" href="{esc(movie_url(mv["id"]))}">{inner}</a>'

    order_block = ""
    if graph["orders"]:
        wraps = []
        for o in graph["orders"]:
            wraps.append(
                f'<div class="graph-order-wrap"><a class="graph-order-name" href="{esc(list_url(o["list"]["id"]))}">'
                f'{esc(o["list"]["name"])} · 第 {o["index"]+1} / {o["total"]} 部</a>'
                f'<div class="graph-order">{step(o["prev"], "上一跳")}{step(movie, "当前", True)}{step(o["next"], "下一跳")}</div></div>'
            )
        order_block = f'<div class="block"><h2>观看顺序</h2>{"".join(wraps)}</div>'
    list_block = ""
    if memberships:
        cats_html = []
        for cat, lists in grouped:
            pills = "".join(f'<a href="{esc(list_url(l["id"]))}">{esc(l["name"])}</a>' for l in lists)
            cats_html.append(
                f'<div class="graph-cat"><h3>{esc(cat["name"])} · {len(lists)}</h3><div class="graph-pills">{pills}</div></div>'
            )
        list_block = f'<div class="block"><h2>入选片单 · {len(memberships)}</h2>{"".join(cats_html)}</div>'
    neighbor_block = ""
    if graph["neighbors"]:
        rows = []
        for n in graph["neighbors"]:
            why = neighbor_why(n)
            rate = f'<span class="graph-nrate">{esc(n["movie"].get("rate"))}</span>' if n["movie"].get("rate") else ""
            badge = f'共享 {n["shared_count"]} 个片单' if n["shared_count"] > 1 else (
                f'名单第 {n["position"]+1} 部' if n["position"] >= 0 else "同一片单"
            )
            rows.append(
                f'<a class="graph-nitem" href="{esc(movie_url(n["movie"]["id"]))}">'
                f'<div class="graph-nposter">{ph(n["movie"])}</div><div class="graph-nbody">'
                f'<div class="graph-nrow"><b>{esc(n["movie"].get("title"))}</b><span class="graph-shared">{badge}</span></div>'
                f'{rate}<div class="graph-why">因为：{esc(why)}</div></div></a>'
            )
        neighbor_block = (
            '<div class="block"><h2>同框最多</h2>'
            '<p class="graph-lead">按共享片单数排序，不是同分类随便抽几部。</p>'
            f'<div class="graph-nlist">{"".join(rows)}</div></div>'
        )
    hop_block = ""
    if graph["hops"]:
        kind_label = {"post": "站内文章", "person": "人物片单", "order": "观看顺序"}
        hops = []
        for h in graph["hops"]:
            hops.append(
                f'<a class="graph-hop" href="{esc(h["href"])}"><div class="k">{kind_label.get(h["kind"], "题材片单")}</div>'
                f'<div class="t">{esc(h["title"])}</div><p>{esc(h["desc"])}</p></a>'
            )
        hop_block = f'<div class="block"><h2>从这里可以走到</h2><div class="graph-hops">{"".join(hops)}</div></div>'
    tag_html = "".join(f'<span class="tag">{esc(t)}</span>' for t in tags)
    if movie.get("badge"):
        tag_html += f'<span class="tag">{esc(movie["badge"])}</span>'
    series = " - 连载中" if (movie.get("episodes") or 0) > 0 else ""
    count = movie.get("count") or ""
    max_html = f'<div class="graph-stat"><b>{max_shared}</b><span>最高同框数</span></div>' if max_shared else ""
    body = f'''<div class="wrap" id="detailRoot">
    <div class="crumb"><a href="/index.html">首页</a><span class="sep">/</span><a href="/lists.html">影片</a><span class="sep">/</span><span>{esc(movie.get("title"))}</span></div>
    <div class="detail">
      <div class="cover">{ph(movie)}</div>
      <div class="info">
        <h1>{esc(movie.get("title"))}</h1>
        <div class="orig">{esc(movie.get("orig") or "")}</div>
        <div class="tags">{tag_html}</div>
        <div class="graph-stats">
          <div class="graph-stat"><b>{esc(movie.get("rate") or "—")}</b><span>豆瓣评分{(" · " + esc(count) + "人评价") if count else ""}</span></div>
          <div class="graph-stat"><b>{len(memberships)}</b><span>入选片单</span></div>
          {max_html}
        </div>
        <div class="meta-row"><b>导演</b><span>{esc(movie.get("director") or "—")}</span></div>
        <div class="meta-row"><b>主演</b><span>{esc(" / ".join(movie.get("actors") or []) or "—")}</span></div>
        <div class="meta-row"><b>类型</b><span>{esc(" · ".join(movie.get("tags") or []) or "—")}</span></div>
        <div class="meta-row"><b>年份</b><span>{esc(movie.get("year") or "—")}{series}</span></div>
        {syn_block}
      </div>
    </div>
    {reason_block}
    {order_block}
    {list_block}
    {neighbor_block}
    {hop_block}
</div>'''
    return page_doc(
        title=f'{movie.get("title")} - {SITE}',
        description=desc_movie(movie, len(memberships)),
        nested=True,
        page="",
        body=body,
        noindex=True,
        path=movie_url(movie["id"]),
    )


def render_method(data) -> str:
    n_lists = len(data["lists"])
    n_movies = len(data["movies"])
    n_multi = sum(1 for count in data["movie_list_n"].values() if count >= 3)
    body = f'''<div class="wrap">
  <article class="page-doc">
    <h1>交叉怎么算</h1>
    <p class="lead">片单对照只发布自己算出来的重叠关系，不转载其它站点的盘点正文和海报。</p>
    <h2 id="source">用了哪些名单</h2>
    <p>数据层是公开片单的标题、顺序和作品字段：片名、年份、导演、主演、豆瓣评分。目前共 {n_lists} 份名单、{n_movies} 部作品。名单名称来自各自的公开出处，本站不改名次，也不另写影评。</p>
    <h2 id="overlap">重叠</h2>
    <p>一部作品每进入一份名单，计数加一。出现在 3 份以上名单的作品目前有 {n_multi} 部。名单页会写出：有多少部只在这一份里、有多少部还能在别处找到，以及重叠最多的邻单。</p>
    <p>「同框最多」按两部作品共享的名单数排序，不是按类型随便抽几部。</p>
    <h2 id="order">观看顺序</h2>
    <p>只有归在观看顺序类的名单才提供上一跳和下一跳。顺序以该名单原有排列为准，本站不重排系列宇宙。</p>
    <h2 id="index">哪些页给搜索引擎看</h2>
    <p>可收录的是首页、分类枢纽、各片单对照页、本页和关于页。影片详情只给站内跳转看交叉，带 noindex，也不进 sitemap。旧的转载文章已经撤下，不再作为内容页。</p>
    <h2 id="play">不提供什么</h2>
    <p>没有播放器，没有片源，没有账号。海报不再热链其它站点，卡片用本站生成的色块标题图。</p>
  </article>
</div>'''
    return page_doc(
        title=f"交叉怎么算 - {SITE}",
        description="说明片单对照如何计算名单重叠、独有条目和观看顺序，以及哪些页面不向搜索引擎要求收录。",
        nested=False,
        page="method",
        body=body,
        path="method.html",
        keywords=seo_keywords(SITE, "交叉索引", "方法"),
        json_ld={
            "@context": "https://schema.org",
            "@type": "TechArticle",
            "headline": "交叉怎么算",
            "name": f"交叉怎么算 - {SITE}",
        },
    )


ABOUT_BODY = '''<div class="wrap">
  <div class="crumb"><a href="/index.html">首页</a><span class="sep">/</span><span>关于与联系</span></div>
  <article class="page-doc">
    <h1>关于与联系</h1>
    <p class="lead">独立片单交叉索引，不是播放站，也不转载其它导航站的盘点文章。</p>
    <h2 id="about">关于片单对照</h2>
    <p>本站把公开片单做成可检索的交叉索引：一部作品同时出现在哪些名单里、和哪几部共享最多名单、系列该按什么顺序看。「今晚看什么」只在现有名单里抽三部。</p>
    <p>没有账号，也不提供在线播放。评分和片名来自各自的公开来源。卡片图由本站按标题生成，不热链其它站点的海报。影片详情只用来看交叉，不向搜索引擎要求收录。</p>
    <h2 id="copyright">版权声明</h2>
    <p>片单名称、影片信息、海报和文章内容来自各自的公开来源，版权归原作者、原网站或权利人所有。本站仅作个人学习与浏览展示，不存储片源，不用于商业传播。</p>
    <p>页面中出现的豆瓣评分、评价人数等公开数据仅供参考，如与来源不一致，以来源为准。</p>
    <h2 id="contact">联系我们</h2>
    <p>合作、纠错或普通咨询，请发邮件：</p>
    <p><a href="mailto:2201219073@qq.com">2201219073@qq.com</a></p>
    <p>来信请写清页面链接和具体问题，工作日一般会查看。本邮箱不处理播放源、账号或充值相关请求。</p>
    <h2 id="complaint">侵权投诉</h2>
    <p>如果你是权利人，认为本站展示的封面、文字或其他材料侵犯了你的合法权益，请把下列信息发到 <a href="mailto:2201219073@qq.com">2201219073@qq.com</a>：</p>
    <p>1. 权利人姓名或机构名称，以及可核验的联系方式；<br>
       2. 被投诉内容的页面链接；<br>
       3. 权属说明或证明材料。</p>
    <p>核实后会尽快删除或断开相关展示。</p>
    <h2 id="help">帮助反馈</h2>
    <p>顶部搜索可查影片、导演、演员和片单。「今晚看什么」点任意一个标签就会给出三部，再点同一标签可取消，点「换一批」换下一组。</p>
    <p>影片详情里的片单、同框推荐和观看顺序都来自现有名单交叉，不是播放推荐。功能建议或数据错误同样发到上面的邮箱即可。</p>
  </article>
</div>'''


def render_redirect(kind: str) -> str:
    scripts = {
        "movie": "Cupfox.loadData().then(d=>{const id=Cupfox.param('movie');const m=id&&d.movieById[id]; if(m) location.replace(Cupfox.detailUrl(m.id)); else document.body.insertAdjacentHTML('afterbegin','<p class=\"empty\">未找到该影片</p>');});",
        "list": "Cupfox.loadData().then(d=>{const id=Cupfox.param('list');const l=id&&d.listById[id]; if(l) location.replace(Cupfox.listUrl(l.id)); else document.body.insertAdjacentHTML('afterbegin','<p class=\"empty\">未找到该片单</p>');});",
        "post": "location.replace('/method.html');",
        "cat": "Cupfox.loadData().then(d=>{const cat=Cupfox.param('cat'); if(cat) location.replace(Cupfox.catUrl(cat)); else location.replace('/lists.html');});",
    }[kind]
    titles = {"movie": "影片", "list": "片单", "post": "文章", "cat": "分类"}
    return page_doc(
        title=f'{titles[kind]}跳转 - {SITE}',
        description="正在跳转到内容页。",
        nested=False,
        page="lists" if kind in ("list", "cat") else ("posts" if kind == "post" else ""),
        body='<div class="wrap"><p class="empty">正在跳转…</p></div>',
        noindex=True,
        scripts=f"<script>{scripts}</script>",
    )


def write_robots_sitemap(paths: list[str], base_url: str):
    sitemap_path = "sitemap.xml"
    robots = f"""User-agent: *
Allow: /
Disallow: /play.html
Disallow: /detail.html
Disallow: /list.html
Disallow: /post.html
Disallow: /post/
Disallow: /movie/

Sitemap: {urljoin(base_url.rstrip('/') + '/', sitemap_path)}
"""
    (ROOT / "robots.txt").write_text(robots, encoding="utf-8")
    urls = []
    for path in paths:
        loc = urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))
        urls.append(f"  <url><loc>{esc(loc)}</loc><lastmod>{BUILD_DATE}</lastmod></url>")
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(urls) + "\n</urlset>\n"
    (ROOT / "sitemap.xml").write_text(xml, encoding="utf-8")


def reset_dir(path: Path):
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="https://www.cupfox.xin", help="sitemap 和 canonical 用的绝对站点地址")
    args = parser.parse_args()
    global ORIGIN
    ORIGIN = args.base_url.rstrip("/")
    data = load_data()

    reset_dir(ROOT / "movie")
    reset_dir(ROOT / "list")
    reset_dir(ROOT / "post")
    reset_dir(ROOT / "cat")

    slugs = defaultdict(list)
    for movie in data["movies"]:
        slugs[("movie", file_slug(movie["id"]))].append(movie["id"])
    for lst in data["lists"]:
        slugs[("list", file_slug(lst["id"]))].append(lst["id"])
    for post in data["posts"]:
        slugs[("post", file_slug(post["id"]))].append(post["id"])
    clashes = {k: v for k, v in slugs.items() if len(v) > 1}
    if clashes:
        raise SystemExit("filename clash: " + str(clashes))

    sitemap = ["index.html", "lists.html", "method.html", "about.html"]
    write(ROOT / "index.html", render_index(data))
    write(ROOT / "lists.html", render_hub(data, "featured"))
    write(ROOT / "method.html", render_method(data))
    write(
        ROOT / "posts.html",
        page_doc(
            title=f"已下线 - {SITE}",
            description="转载盘点文章已从本站撤下。",
            nested=False,
            page="method",
            body='<div class="wrap"><article class="page-doc"><h1>文章已下线</h1><p class="lead">本站不再发布从其它导航站转来的盘点文章。<a href="/method.html">改为阅读交叉方法</a>。</p></article></div>',
            noindex=True,
            scripts='<script>location.replace("/method.html");</script>',
        ),
    )
    write(
        ROOT / "about.html",
        page_doc(
            title=f"关于与联系 - {SITE}",
            description="片单对照的介绍、版权声明、联系邮箱与侵权投诉方式。本站做交叉索引，不转载盘点文章，不提供在线播放。",
            keywords=seo_keywords(SITE, "关于", "版权声明"),
            nested=False,
            page="",
            body=ABOUT_BODY,
            path="about.html",
        ),
    )
    write(ROOT / "detail.html", render_redirect("movie"))
    write(ROOT / "list.html", render_redirect("list"))
    write(ROOT / "post.html", render_redirect("post"))

    for cat in data["categories"]:
        if cat["id"] == "featured":
            continue
        write(ROOT / "cat" / f"{file_slug(cat['id'])}.html", render_hub(data, cat["id"]))
        sitemap.append(cat_url(cat["id"]))

    for lst in data["lists"]:
        write(ROOT / "list" / f"{file_slug(lst['id'])}.html", render_list(lst, data))
        sitemap.append(list_url(lst["id"]))
    for movie in data["movies"]:
        write(ROOT / "movie" / f"{file_slug(movie['id'])}.html", render_movie(movie, data))

    write_robots_sitemap(sitemap, args.base_url)
    print(
        "built",
        len(data["movies"]),
        "movies,",
        len(data["lists"]),
        "lists,",
        len(data["posts"]),
        "posts,",
        "sitemap",
        len(sitemap),
    )


if __name__ == "__main__":
    main()
