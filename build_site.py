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
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote, urljoin

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data.jsonl"
SITE = "茶杯狐"
TAGLINE = "片荒剧荒就来茶杯狐"
ORIGIN = "https://www.cupfox.xin"
SITE_KEYWORDS = (
    "茶杯狐,Cupfox,电影推荐,电视剧推荐,高分电影,豆瓣高分,IMDB高分,"
    "奥斯卡最佳影片,今晚看什么,片单,片荒,国产剧,美剧推荐,日剧,韩剧,"
    "动漫推荐,纪录片,悬疑电影,科幻电影,经典电影,观看顺序"
)
HOME_TITLE = f"{SITE} - 电影电视剧推荐与高分片单 | {TAGLINE}"
HOME_DESCRIPTION = (
    "茶杯狐是电影电视剧推荐与高分片单站。收录豆瓣高分、IMDB、奥斯卡最佳影片、"
    "国产剧、美剧、日剧、韩剧、动漫和纪录片名单，按类型、导演、演员和观看顺序挑片，解决片荒。不提供在线播放。"
)
HUB_BLURBS = {
    "featured": "精选电影电视剧片单，覆盖豆瓣高分、IMDB、奥斯卡、类型题材与观看顺序。",
    "region": "按地区与形式挑片：国产剧、美剧、日剧、韩剧、港剧、台剧、纪录片和动漫。",
    "genre": "按类型挑电影：动作、喜剧、科幻、悬疑、爱情、恐怖、动画、战争、犯罪。",
    "subgenre": "更细的口味片单：功夫、公路、青春校园、美食、穿越、监狱、机器人。",
    "style": "按风格找片：暴力美学、哥特、废土、表现主义、新现实主义。",
    "order": "系列观看顺序：漫威、DC、名侦探柯南等，先看哪一部不用猜。",
    "award": "奥斯卡最佳影片、最佳导演、最佳演员等获奖作品名单。",
    "pro": "AFI、Letterboxd 等专业评选片单，按共识挑高分电影。",
    "director": "导演代表作片单，从导演入口走进他们最值得看的作品。",
    "actor": "演员代表作片单，按主演找下一部值得看的电影电视剧。",
}

NAV_LINKS = (("home", "index.html", "首页"), ("lists", "lists.html", "片单"), ("posts", "posts.html", "文章"))


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
    }


def movie_url(item_id: str) -> str:
    return f"movie/{file_slug(item_id)}.html"


def list_url(item_id: str) -> str:
    return f"list/{file_slug(item_id)}.html"


def post_url(item_id: str) -> str:
    return f"post/{file_slug(item_id)}.html"


def cat_url(item_id: str) -> str:
    if item_id == "featured":
        return "lists.html"
    return f"cat/{file_slug(item_id)}.html"


def abs_url(path: str) -> str:
    return urljoin(ORIGIN.rstrip("/") + "/", path.lstrip("/"))


def ph(obj: dict, alt: str = "") -> str:
    title = alt or obj.get("title") or obj.get("name") or ""
    cover = obj.get("cover") or ""
    if is_img(cover):
        return (
            f'<img class="ph" src="{esc(cover)}" loading="lazy" '
            f'referrerpolicy="no-referrer" alt="{esc(title)}">'
        )
    return f'<div class="ph" role="img" aria-label="{esc(title)}"></div>'


def card(title: str, obj: dict, href: str) -> str:
    return (
        f'<a class="card" href="{esc(href)}">{ph(obj, title)}'
        f'<div class="grad"></div><div class="cap"><b>{esc(title)}</b></div></a>'
    )


def hub_card(title: str, obj: dict, href: str) -> str:
    return (
        f'<a class="hub-card" href="{esc(href)}"><div class="thumb">{ph(obj, title)}</div>'
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
  <a class="logo" href="index.html" aria-label="{SITE}">
    <img src="logo.png" width="32" height="32" alt="{SITE}">
    <span><span style="color:#ff705b;font-weight:900">Cupfox</span> {SITE}</span>
  </a>
  <div class="nav-links">{links}</div>
  <div class="nav-right">
    <button class="icon-btn" id="searchBtn" aria-label="搜索"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg></button>
    <button class="toggle" id="themeBtn" aria-label="切换主题"><span class="dot"></span></button>
  </div>
</div></nav>'''


def foot_html() -> str:
    return '''<footer>
  <div class="wrap foot-grid">
    <div class="foot-brand">
      <div class="logo" style="font-size:20px;margin-bottom:10px"><img src="logo.png" width="28" height="28" alt="茶杯狐"><span><span style="color:#ff705b;font-weight:900">Cupfox</span> 茶杯狐</span></div>
      <p class="foot-desc">茶杯狐是电影电视剧推荐与高分片单导航站。收录豆瓣高分、IMDB 高分、奥斯卡最佳影片、国产剧、美剧、日剧、韩剧、动漫和纪录片名单，按类型、导演、演员和观看顺序帮你解决片荒、挑今晚看什么。本站展示公开片单与编辑文章，不提供在线播放。</p>
      <p class="foot-mail">联系邮箱 <a href="mailto:2201219073@qq.com">2201219073@qq.com</a></p>
    </div>
    <div class="foot-col">
      <h3>热门分类</h3>
      <a href="lists.html">精选片单</a>
      <a href="cat/genre.html">类型题材</a>
      <a href="cat/region.html">国产剧 / 美剧 / 日韩</a>
      <a href="cat/award.html">奥斯卡获奖作品</a>
      <a href="cat/order.html">系列观看顺序</a>
      <a href="cat/director.html">导演代表作</a>
      <a href="cat/actor.html">演员代表作</a>
      <a href="posts.html">影视盘点文章</a>
    </div>
    <div class="foot-col">
      <h3>高分片单</h3>
      <a href="list/list-豆瓣高分国产剧推荐.html">豆瓣高分国产剧</a>
      <a href="list/list-豆瓣高分美剧推荐.html">豆瓣高分美剧</a>
      <a href="list/list-豆瓣高分韩剧推荐.html">豆瓣高分韩剧</a>
      <a href="list/list-豆瓣高分日剧推荐.html">豆瓣高分日剧</a>
      <a href="list/list-imdb高分欧美剧推荐.html">IMDB高分欧美剧</a>
      <a href="list/list-历届奥斯卡最佳影片.html">奥斯卡最佳影片</a>
      <a href="list/list-经典悬疑电影推荐.html">悬疑电影推荐</a>
      <a href="list/list-经典科幻电影推荐.html">科幻电影推荐</a>
    </div>
    <div class="foot-col">
      <h3>站点与帮助</h3>
      <a href="index.html">首页 · 今晚看什么</a>
      <a href="about.html#about">关于茶杯狐</a>
      <a href="about.html#copyright">版权声明</a>
      <a href="about.html#contact">联系我们</a>
      <a href="about.html#complaint">侵权投诉</a>
      <a href="about.html#help">帮助反馈</a>
    </div>
  </div>
  <div class="wrap">
    <div class="foot-keys" aria-label="热门搜索">
      <a href="index.html">电影推荐</a>
      <a href="index.html">电视剧推荐</a>
      <a href="index.html">今晚看什么</a>
      <a href="lists.html">高分片单</a>
      <a href="list/list-豆瓣高分国产剧推荐.html">豆瓣高分</a>
      <a href="list/list-imdb高分欧美剧推荐.html">IMDB高分</a>
      <a href="list/list-历届奥斯卡最佳影片.html">奥斯卡</a>
      <a href="list/list-大陆经典电影推荐.html">国产电影</a>
      <a href="list/list-经典动作电影推荐.html">动作电影</a>
      <a href="list/list-经典喜剧电影推荐.html">喜剧电影</a>
      <a href="list/list-经典爱情电影推荐.html">爱情电影</a>
      <a href="list/list-经典恐怖电影推荐.html">恐怖电影</a>
      <a href="list/list-经典动画电影推荐.html">动画电影</a>
      <a href="list/list-经典纪录片电影推荐.html">纪录片</a>
      <a href="list/list-豆瓣高分国漫推荐.html">国漫推荐</a>
      <a href="list/list-豆瓣高分日漫推荐.html">日漫推荐</a>
      <a href="cat/order.html">观看顺序</a>
      <a href="posts.html">影视盘点</a>
    </div>
    <div class="copy">© Cupfox 茶杯狐 · 公开影视片单与文章的本地归档展示 · 电影推荐 / 电视剧推荐 / 高分片单 · 不提供在线播放</div>
  </div>
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
    base = "../" if nested else "./"
    robots = "noindex,follow" if noindex else "index,follow"
    canonical = abs_url(path) if path and not noindex else ""
    canon = f'<link rel="canonical" href="{esc(canonical)}"/>' if canonical else ""
    og_url = f'<meta property="og:url" content="{esc(canonical)}"/>' if canonical else ""
    og_img = f'<meta property="og:image" content="{esc(image)}"/>' if image else ""
    keys = seo_keywords(keywords or (SITE_KEYWORDS if not noindex else ""))
    key_tag = f'<meta name="keywords" content="{esc(keys)}"/>' if keys and not noindex else ""
    ld = ""
    if json_ld:
        if canonical and "url" not in json_ld and "@graph" not in json_ld:
            json_ld = {**json_ld, "url": canonical}
        ld = "<script type=\"application/ld+json\">" + json.dumps(json_ld, ensure_ascii=False).replace("<", "\\u003c") + "</script>"
    cls = f' class="{body_class}"' if body_class else ""
    return f'''<!DOCTYPE html>
<html lang="zh-CN" data-theme="dark">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<base href="{base}"/>
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
<link rel="icon" href="favicon.ico" sizes="any"/>
<link rel="icon" type="image/png" href="logo.png"/>
<link rel="apple-touch-icon" href="logo.png"/>
<link rel="stylesheet" href="styles.css"/>
{extra_head}
{ld}
</head>
<body{cls}>
<div id="nav">{nav_html(page)}</div>
{body}
<div id="foot">{foot_html()}</div>
<script>window.PAGE={json.dumps(page)};</script>
<script src="app.js"></script>
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
    if articles:
        return hops[:2] + [{
            "kind": "post",
            "title": articles[0]["title"],
            "href": post_url(articles[0]["id"]),
            "desc": "站内文章提到了这部片。",
        }]
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
    if is_img(movie.get("cover") or ""):
        data["image"] = movie["cover"]
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
    title = movie.get("title") or "这部影片"
    text += f"{title}电影推荐，可对照豆瓣评分与站内高分片单继续挑片。"
    return clip_desc(text)


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def render_index(data) -> str:
    posts = data["posts"][:8]
    slides = []
    for i, post in enumerate(posts):
        tags = " / ".join(post.get("tags") or []) or "影视盘点"
        on = " is-on" if i == 0 else ""
        slides.append(
            f'<a class="hero-big{on}" href="{esc(post_url(post["id"]))}">{ph(post)}'
            f'<div class="grad"></div><div class="cap"><h2>{esc(post.get("title"))}</h2>'
            f"<p>编辑精选 · {esc(tags)}</p></div></a>"
        )
    arrows = ""
    if len(posts) > 1:
        arrows = (
            '<button type="button" class="hero-arrow hero-prev" data-d="-1" aria-label="上一篇">'
            '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg></button>'
            '<button type="button" class="hero-arrow hero-next" data-d="1" aria-label="下一篇">'
            '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg></button>'
            '<div class="hero-dots">'
            + "".join(
                f'<button type="button" class="{"on" if i == 0 else ""}" data-i="{i}" aria-label="第 {i+1} 篇"></button>'
                for i in range(len(posts))
            )
            + "</div>"
        )
    home_cats = [c for c in data["categories"] if c["id"] != "featured"]
    cat_tiles = []
    for i, cat in enumerate(home_cats):
        if is_img(cat.get("cover") or ""):
            img = f'<img class="ph" src="{esc(cat["cover"])}" loading="lazy" referrerpolicy="no-referrer" alt="{esc(cat["name"])}">'
        else:
            img = '<div class="ph"></div>'
        cat_tiles.append(f'<a class="cat" href="{esc(cat_url(cat["id"]))}">{img}<b>{esc(cat["name"])}</b></a>')
    sections = [
        '''<section id="tonight">
      <div class="sec-head"><div class="sec-title">今晚看什么</div></div>
      <p class="tonight-empty">点任意一个标签，给你三部今晚能看的。</p>
    </section>'''
    ]
    for cat in home_cats:
        rows = [l for l in data["lists"] if l.get("category") == cat["id"]][:6]
        if not rows:
            continue
        cards = "".join(card(l["name"], l, list_url(l["id"])) for l in rows)
        sections.append(
            f'<section><div class="sec-head"><div class="sec-title">{esc(cat["name"])}</div>'
            f'<a class="btn-sm" href="{esc(cat_url(cat["id"]))}">更多</a></div>'
            f'<div class="sec-row">{cards}</div></section>'
        )
    cover = posts[0].get("cover") if posts else ""
    body = f'''<section><div class="wrap">
  <div class="hero-split">
    <div id="heroBig" class="hero-carousel">{"".join(slides)}{arrows}</div>
    <div class="hero-cats" id="heroCats">{"".join(cat_tiles)}</div>
  </div>
</div></section>
<main class="wrap" id="cats">
  <h1 class="home-h1">茶杯狐 · 电影电视剧推荐与高分片单</h1>
  {"".join(sections)}
  <section class="home-seo" aria-label="站点介绍">
    <h2>片荒剧荒就来茶杯狐</h2>
    <p>想找电影推荐、电视剧推荐或今晚看什么时，先看豆瓣高分、IMDB 高分和奥斯卡最佳影片，再按动作、喜剧、科幻、悬疑、爱情、动画这些类型往下翻。国产剧、美剧、日剧、韩剧、港剧、纪录片、国漫和日漫都做成了片单；系列作品还有观看顺序，导演和演员也能从代表作入口进去。</p>
    <p>每部影片会标出它还出现在哪些名单里，方便顺着高分片单继续挑，而不是只看一个评分。茶杯狐只做公开片单与文章的本地展示，不提供在线播放。</p>
    <div class="home-seo-links">
      <a href="list/list-豆瓣高分国产剧推荐.html">豆瓣高分国产剧</a>
      <a href="list/list-豆瓣高分美剧推荐.html">豆瓣高分美剧</a>
      <a href="list/list-豆瓣高分韩剧推荐.html">豆瓣高分韩剧</a>
      <a href="list/list-历届奥斯卡最佳影片.html">奥斯卡最佳影片</a>
      <a href="list/list-经典悬疑电影推荐.html">悬疑电影</a>
      <a href="list/list-经典科幻电影推荐.html">科幻电影</a>
      <a href="cat/order.html">观看顺序</a>
      <a href="posts.html">影视盘点</a>
    </div>
  </section>
</main>'''
    return page_doc(
        title=HOME_TITLE,
        description=HOME_DESCRIPTION,
        nested=False,
        page="home",
        body=body,
        image=cover if is_img(cover or "") else "",
        scripts="<script>Cupfox.loadData().then(d=>{Cupfox.bindTonight(document.getElementById('tonight'), d);Cupfox.bindHero(document.getElementById('heroBig'), d.posts);});</script>",
        path="index.html",
        keywords=SITE_KEYWORDS,
        json_ld={
            "@context": "https://schema.org",
            "@graph": [
                {
                    "@type": "WebSite",
                    "name": SITE,
                    "alternateName": ["Cupfox", "茶杯狐电影推荐"],
                    "url": abs_url("index.html"),
                    "description": HOME_DESCRIPTION,
                    "inLanguage": "zh-CN",
                    "publisher": {"@type": "Organization", "name": SITE, "email": "2201219073@qq.com"},
                },
                {
                    "@type": "ItemList",
                    "name": "茶杯狐热门片单",
                    "itemListElement": [
                        {"@type": "ListItem", "position": 1, "name": "豆瓣高分国产剧推荐", "url": abs_url("list/list-豆瓣高分国产剧推荐.html")},
                        {"@type": "ListItem", "position": 2, "name": "豆瓣高分美剧推荐", "url": abs_url("list/list-豆瓣高分美剧推荐.html")},
                        {"@type": "ListItem", "position": 3, "name": "历届奥斯卡最佳影片", "url": abs_url("list/list-历届奥斯卡最佳影片.html")},
                        {"@type": "ListItem", "position": 4, "name": "经典悬疑电影推荐", "url": abs_url("list/list-经典悬疑电影推荐.html")},
                    ],
                },
            ],
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
    grid = "".join(hub_card(l["name"], l, list_url(l["id"])) for l in lists)
    body = f'''<div class="wrap hub">
  <aside class="side-menu">{menu}</aside>
  <main>
    <h1 class="hub-title">{esc(title)} · {len(lists)} 份电影电视剧片单</h1>
    <div class="hub-grid">{grid}</div>
  </main>
</div>'''
    blurb = HUB_BLURBS.get(cat_id, "按名单挑电影电视剧。")
    return page_doc(
        title=f"{title} - 电影电视剧推荐片单 | {SITE}",
        description=clip_desc(f"{title}共{len(lists)}份片单。{blurb}适合片荒时按高分名单挑今晚看什么。"),
        nested=(cat_id != "featured"),
        page="lists",
        body=body,
        path=cat_url(cat_id),
        keywords=seo_keywords(title, "电影推荐,电视剧推荐,高分片单,今晚看什么", SITE_KEYWORDS),
    )


def render_list(lst, data) -> str:
    cat = data["cat_by"].get(lst.get("category"))
    movies = [data["movie_by"][mid] for mid in lst.get("movies") or [] if mid in data["movie_by"]]
    items = "".join(movie_item(m, i + 1) for i, m in enumerate(movies))
    toc = "".join(f'<a href="#m{i+1}">{i+1}. {esc(m.get("title"))}</a>' for i, m in enumerate(movies))
    names = "、".join(m.get("title") or "" for m in movies[:8])
    cat_name = cat["name"] if cat else ""
    body = f'''<div class="wrap">
  <div class="crumb"><a href="index.html">首页</a><span class="sep">/</span><a href="lists.html">全部片单</a><span class="sep">/</span><span>{esc(lst.get("name"))}</span></div>
  <h1 class="page-title">{esc(lst.get("name"))} <span class="cat-tag">{esc(cat_name)}</span></h1>
  <div class="filter-bar" id="filterBar">
    <button class="btn-sm active" data-f="all">全部</button>
    <button class="btn-sm" data-f="film">电影</button>
    <button class="btn-sm" data-f="series">剧集</button>
    <span class="list-count">共 {len(movies)} 部</span>
  </div>
  <div class="list-layout">
    <div class="list-back-col"><a class="list-back" href="lists.html">‹ 全部片单</a></div>
    <div class="movie-list" id="movieList">{items or '<div class="empty">该片单没有影片</div>'}</div>
    <nav class="toc"><h4>内容导航</h4><div class="toc-links">{toc}</div></nav>
  </div>
</div>'''
    return page_doc(
        title=f'{lst.get("name")} - 电影电视剧推荐 | {SITE}',
        description=clip_desc(
            f'{lst.get("name")}（{cat_name}）共{len(movies)}部电影电视剧推荐。'
            + (f"{names}。" if names else "")
            + "含豆瓣评分、导演主演，适合片荒时按名单挑片。"
        ),
        nested=True,
        page="lists",
        body=body,
        body_class="list-detail-page",
        image=lst.get("cover") if is_img(lst.get("cover") or "") else "",
        keywords=seo_keywords(lst.get("name"), cat_name, names.replace("、", ","), "片单,电影推荐,电视剧推荐,豆瓣高分"),
        json_ld={
            "@context": "https://schema.org",
            "@type": "ItemList",
            "name": lst.get("name"),
            "numberOfItems": len(movies),
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "name": m.get("title"), "url": abs_url(movie_url(m["id"]))}
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
    <div class="crumb"><a href="index.html">首页</a><span class="sep">/</span><a href="lists.html">影片</a><span class="sep">/</span><span>{esc(movie.get("title"))}</span></div>
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
        image=movie.get("cover") if is_img(movie.get("cover") or "") else "",
        json_ld=movie_json_ld(movie),
        path=movie_url(movie["id"]),
        keywords=seo_keywords(
            movie.get("title"),
            movie.get("orig"),
            movie.get("director"),
            ",".join((movie.get("actors") or [])[:4]),
            ",".join(movie.get("tags") or []),
            "电影推荐,豆瓣评分,高分片单",
        ),
    )


def render_posts(data) -> str:
    grid = "".join(hub_card(p["title"], p, post_url(p["id"])) for p in data["posts"])
    body = f'''<div class="wrap">
    <h1 class="hub-title" style="padding-top:20px">影视盘点文章 · 电影电视剧推荐</h1>
  <div class="hub-grid" style="--side-w:auto">{grid}</div>
</div>'''
    return page_doc(
        title=f"影视盘点文章 - 电影电视剧推荐 | {SITE}",
        description="茶杯狐影视盘点与预告：高分国产剧、悬疑电影、动画电影、奥斯卡和院线看点，帮你决定今晚看什么。",
        nested=False,
        page="posts",
        body=body,
        path="posts.html",
        keywords=seo_keywords("影视盘点,电影推荐,国产剧,悬疑电影,动画电影,奥斯卡", SITE_KEYWORDS),
    )


def render_post(post) -> str:
    sections = post.get("sections") or []
    body_parts = []
    for i, sec in enumerate(sections):
        images = "".join(
            f'<figure><img src="{esc(src)}" loading="lazy" referrerpolicy="no-referrer" alt="{esc(sec.get("h"))}">'
            f'<figcaption>{esc(sec.get("h"))}{(" · " + str(n+1)) if len(sec.get("images") or [])>1 else ""}</figcaption></figure>'
            for n, src in enumerate(sec.get("images") or [])
        )
        body_parts.append(
            f'<h2 id="p{i+1}">{esc(sec.get("h"))}</h2><p>{esc(sec.get("body"))}</p>'
            f'<div class="section-images">{images}</div>'
        )
    toc = "".join(f'<a href="#p{i+1}">{i+1}. {esc(s.get("h"))}</a>' for i, s in enumerate(sections))
    tags = "".join(f'<span class="tag">{esc(t)}</span>' for t in post.get("tags") or [])
    cover = ""
    if is_img(post.get("cover") or ""):
        cover = f'<figure style="margin:16px 0 24px"><div class="ph" style="background-image:url(\'{esc(post["cover"])}\');aspect-ratio:16/9"></div></figure>'
    intro = f'<p class="intro">{esc(post.get("intro"))}</p>' if post.get("intro") else ""
    article = f'''<div class="wrap">
  <div class="crumb"><a href="posts.html">全部文章</a><span class="sep">/</span><span>{esc(post.get("title"))}</span></div>
  <div class="article-wrap">
    <article class="article">
      <h1>{esc(post.get("title"))}</h1>
      <div class="meta-row"><span class="tag">原创</span><span class="tag">{esc(post.get("author"))}</span>
        <span class="tag">{esc(post.get("date"))}</span>{tags}</div>
      {intro}{cover}{"".join(body_parts)}
    </article>
    <nav class="toc"><h4>内容导航</h4><div class="toc-links">{toc}</div></nav>
  </div>
</div>'''
    desc = clip_desc(
        (post.get("intro") or post.get("title") or "")
        + "茶杯狐影视盘点，电影电视剧推荐与今晚看什么参考。"
    )
    return page_doc(
        title=f'{post.get("title")} - {SITE}',
        description=desc,
        nested=True,
        page="posts",
        body=article,
        image=post.get("cover") if is_img(post.get("cover") or "") else "",
        json_ld={"@context": "https://schema.org", "@type": "Article", "headline": post.get("title"), "author": post.get("author"), "datePublished": post.get("date")},
        path=post_url(post["id"]),
        keywords=seo_keywords(post.get("title"), ",".join(post.get("tags") or []), "影视盘点,电影推荐,今晚看什么"),
    )


ABOUT_BODY = '''<div class="wrap">
  <div class="crumb"><a href="index.html">首页</a><span class="sep">/</span><span>关于与联系</span></div>
  <article class="page-doc">
    <h1>关于与联系</h1>
    <p class="lead">电影电视剧推荐与高分片单导航，片荒时用来挑片，不是播放站。</p>
    <h2 id="about">关于茶杯狐</h2>
    <p>本站把公开的影视片单和编辑文章做成可检索的本地展示：按豆瓣高分、奥斯卡、类型题材和观看顺序逛名单，按共现关系看一部片还出现在哪些单子里，并用「今晚看什么」在几个标签里给出三部今晚能看的。</p>
    <p>站点没有账号，也不提供在线播放。海报和正文保留原公开来源，方便对照查阅。</p>
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
        "post": "Cupfox.loadData().then(d=>{const id=Cupfox.param('post');const p=id&&d.postById[id]; if(p) location.replace(Cupfox.postUrl(p.id)); else document.body.insertAdjacentHTML('afterbegin','<p class=\"empty\">未找到该文章</p>');});",
        "cat": "Cupfox.loadData().then(d=>{const cat=Cupfox.param('cat'); if(cat) location.replace(Cupfox.catUrl(cat)); else location.replace('lists.html');});",
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

Sitemap: {urljoin(base_url.rstrip('/') + '/', sitemap_path)}
"""
    (ROOT / "robots.txt").write_text(robots, encoding="utf-8")
    urls = []
    for path in paths:
        loc = urljoin(base_url.rstrip("/") + "/", path)
        urls.append(f"  <url><loc>{esc(loc)}</loc></url>")
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

    sitemap = ["index.html", "lists.html", "posts.html", "about.html"]
    write(ROOT / "index.html", render_index(data))
    write(ROOT / "lists.html", render_hub(data, "featured"))
    write(ROOT / "posts.html", render_posts(data))
    write(
        ROOT / "about.html",
        page_doc(
            title=f"关于与联系 - {SITE}",
            description="茶杯狐介绍：电影电视剧推荐与高分片单导航站，版权声明、联系邮箱与侵权投诉方式。不提供在线播放。",
            keywords=seo_keywords("茶杯狐,关于茶杯狐,版权声明", SITE_KEYWORDS),
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
    for post in data["posts"]:
        write(ROOT / "post" / f"{file_slug(post['id'])}.html", render_post(post))
        sitemap.append(post_url(post["id"]))
    for movie in data["movies"]:
        write(ROOT / "movie" / f"{file_slug(movie['id'])}.html", render_movie(movie, data))
        sitemap.append(movie_url(movie["id"]))

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
