# Cupfox Clone

这是一个从 `cupfox.love` 公开页面生成数据的静态站点。浏览页在构建时写成带正文的 HTML，搜索引擎可以直接抓到片名、片单和文章，不必先跑 JavaScript。搜索和「今晚看什么」仍用 `data.jsonl` 做交互。

## 更新数据并生成页面

```powershell
python scrape_cupfox.py
python build_site.py --base-url https://www.cupfox.xin
```

抓取器读取原站 sitemap，并抓取全部公开分类、片单和文章页面。HTML 会缓存在 `.cupfox-cache/`。需要强制更新时运行 `python scrape_cupfox.py --refresh`。

`build_site.py` 会写出 `movie/`、`list/`、`post/`、`cat/` 下的内容页，以及 `sitemap.xml`、`robots.txt`。默认站点地址是 `https://www.cupfox.xin`。

## 本地预览

```powershell
python build_site.py
python -m http.server 8123 --bind 127.0.0.1
```

然后访问 `http://127.0.0.1:8123/`。不要直接双击 HTML。

## 数据格式

`data.jsonl` 每行是一个 JSON 对象，`type` 为以下之一：

- `category`: 片单分类
- `list`: 片单及其有序影片 ID
- `movie`: 影片评分、评价数、标签、导演、主演和海报
- `post`: 文章元数据、正文分节和章节图片

图片保留原始公开 URL；项目不包含真实播放源。
