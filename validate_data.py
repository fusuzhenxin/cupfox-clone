#!/usr/bin/env python3
import json
from collections import Counter
from pathlib import Path

path = Path(__file__).with_name("data.jsonl")
records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
counts = Counter(item.get("type") for item in records)
ids = [item.get("id") for item in records]
assert len(ids) == len(set(ids)), "data.jsonl 存在重复 ID"
movie_ids = {item["id"] for item in records if item.get("type") == "movie"}
lists = [item for item in records if item.get("type") == "list"]
posts = [item for item in records if item.get("type") == "post"]
missing = [(item["name"], mid) for item in lists for mid in item.get("movies", []) if mid not in movie_ids]
assert not missing, f"片单引用了不存在的影片: {missing[:5]}"
assert all(item.get("cover") for item in lists), "存在无封面的片单"
assert all(item.get("title") for item in (x for x in records if x.get("type") == "movie")), "存在标题缺失的影片"
assert all(item.get("title") and item.get("sections") for item in posts), "存在无正文的文章"
print("records", len(records))
print("counts", dict(counts))
print("list movie references", sum(len(item.get("movies", [])) for item in lists))
print("unique movies", len(movie_ids))
print("movies without source cover", sum(not item.get("cover") for item in records if item.get("type") == "movie"))
print("article sections", sum(len(item.get("sections", [])) for item in posts))
