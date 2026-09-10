/* ===== 片单对照 · 共享脚本 ===== */
'use strict';

const PALETTES = [
  "linear-gradient(135deg,#ff9a8b,#ff6a88)","linear-gradient(135deg,#5b86e5,#36d1dc)",
  "linear-gradient(135deg,#f7971e,#ffd200)","linear-gradient(135deg,#11998e,#38ef7d)",
  "linear-gradient(135deg,#8e2de2,#4a00e0)","linear-gradient(135deg,#232526,#414345)",
  "linear-gradient(135deg,#fc466b,#3f5efb)","linear-gradient(135deg,#ee9ca7,#ffdde1)",
  "linear-gradient(135deg,#0f2027,#2c5364)","linear-gradient(135deg,#ff705b,#c94b8f)"
];
const palette = i => PALETTES[((i%PALETTES.length)+PALETTES.length)%PALETTES.length];

/* ---------- SVG 海报生成（不依赖外部图片，看起来像照片） ---------- */
function hashHue(str){
  let h=0; for(let i=0;i<str.length;i++) h=(h*31+str.charCodeAt(i))&0xffffff;
  return h%360;
}
function esc(s){ return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function svgURI(svg){ return 'data:image/svg+xml;utf8,'+encodeURIComponent(svg); }

function wrapLines(text, maxLen){
  const lines=[]; let line='';
  for(const ch of String(text||'')){
    if(line.length>=maxLen){lines.push(line); line='';}
    line+=ch;
  }
  if(line) lines.push(line);
  if(!lines.length) lines.push(' ');
  return lines;
}

function posterSvg(m, w=300, h=450){
  const hue=hashHue(m.id||m.title||'x');
  const c1=`hsl(${hue},62%,22%)`, c2=`hsl(${(hue+50)%360},55%,10%)`, glow=`hsl(${(hue+25)%360},85%,58%)`;
  const titleLines=wrapLines(m.title, 7);
  const sub=esc((m.director?m.director+' · ':'')+(m.year||''));
  const rate=esc(m.rate||'');
  const fs=Math.min(30, Math.max(17, w/(titleLines[0].length>5?7:5)));
  const startY=h*0.42 - (titleLines.length-1)*(fs*1.1)/2;
  const textEls=titleLines.map((t,i)=>{
    const y=startY + i*(fs*1.15);
    return `<text x="${w/2}" y="${y}" text-anchor="middle" fill="#fff" font-size="${fs}" font-weight="800" font-family="PingFang SC, Microsoft YaHei, sans-serif">${esc(t)}</text>`;
  }).join('');
  const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">
    <defs>
      <linearGradient id="bg-${m.id}" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="${c1}"/><stop offset="100%" stop-color="${c2}"/></linearGradient>
      <radialGradient id="gl-${m.id}" cx="0.7" cy="0.25" r="0.7"><stop offset="0%" stop-color="${glow}" stop-opacity="0.28"/><stop offset="100%" stop-color="transparent" stop-opacity="0"/></radialGradient>
    </defs>
    <rect width="${w}" height="${h}" fill="url(#bg-${m.id})"/>
    <rect width="${w}" height="${h}" fill="url(#gl-${m.id})"/>
    <circle cx="${w*0.78}" cy="${h*0.18}" r="${w*0.22}" fill="${glow}" opacity="0.14"/>
    <line x1="${w*0.12}" y1="${h*0.66}" x2="${w*0.88}" y2="${h*0.66}" stroke="#fff" stroke-opacity="0.08" stroke-width="1"/>
    ${textEls}
    <text x="${w/2}" y="${h*0.75}" text-anchor="middle" fill="#aaa" font-size="${Math.max(11,w*0.042)}" font-family="PingFang SC, Microsoft YaHei, sans-serif">${sub}</text>
    <text x="${w-14}" y="34" text-anchor="end" fill="#4c8dff" font-size="22" font-weight="800" font-family="Arial, sans-serif">${rate}</text>
  </svg>`;
  return svgURI(svg);
}

function postCoverSvg(p, w=800, h=450){
  const hue=hashHue(p.id||p.title||'x');
  const c1=`hsl(${hue},55%,20%)`, c2=`hsl(${(hue+60)%360},50%,12%)`, glow=`hsl(${(hue+30)%360},80%,55%)`;
  const titleLines=wrapLines(p.title, 14);
  const fs=Math.min(34, Math.max(20, w/(titleLines[0].length>10?18:12)));
  const startY=h*0.45 - (titleLines.length-1)*(fs*1.1)/2;
  const textEls=titleLines.map((t,i)=>`<text x="${w/2}" y="${startY+i*(fs*1.15)}" text-anchor="middle" fill="#fff" font-size="${fs}" font-weight="800" font-family="PingFang SC, Microsoft YaHei, sans-serif">${esc(t)}</text>`).join('');
  const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">
    <defs>
      <linearGradient id="pc-${p.id}" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="${c1}"/><stop offset="100%" stop-color="${c2}"/></linearGradient>
      <radialGradient id="pg-${p.id}" cx="0.7" cy="0.2" r="0.8"><stop offset="0%" stop-color="${glow}" stop-opacity="0.25"/><stop offset="100%" stop-color="transparent" stop-opacity="0"/></radialGradient>
    </defs>
    <rect width="${w}" height="${h}" fill="url(#pc-${p.id})"/>
    <rect width="${w}" height="${h}" fill="url(#pg-${p.id})"/>
    <circle cx="${w*0.85}" cy="${h*0.25}" r="${h*0.25}" fill="${glow}" opacity="0.12"/>
    ${textEls}
    <text x="${w/2}" y="${h*0.78}" text-anchor="middle" fill="#bbb" font-size="14" font-family="PingFang SC, Microsoft YaHei, sans-serif">${esc((p.author?p.author+' · ':'')+(p.date||''))}</text>
  </svg>`;
  return svgURI(svg);
}

function collageHtml(list, cls='ph'){
  const ids=(list.movies||[]).slice(0,4);
  const cells=ids.map(mid=>{
    const m=_dataCache?.movieById?.[mid];
    return m ? `<div class="coll-cell" style="background-image:url('${posterSvg(m,150,225)}')"></div>` : '';
  }).join('');
  return `<div class="${cls} collage">${cells || '<div class="coll-cell" style="background:'+palette(hashHue(list.id))+'"></div>'}</div>`;
}

/* ---------- 真实图片优先，SVG 兜底 ---------- */
function isSourceHost(url){
  try{
    const host=new URL(url).hostname;
    return /(^|\.)(cupfox\.love|zhimg\.com|zhihu\.com|biliimg\.com)$/i.test(host);
  }catch(e){ return true; }
}
function isImg(s){ return typeof s==='string' && /^https?:\/\//i.test(s) && !isSourceHost(s); }
function phFor(obj, w, h, kind){
  const cover = obj && obj.cover;
  if(isImg(cover)){
    return `<img class="ph" src="${esc(cover)}" loading="lazy" referrerpolicy="no-referrer" alt="${esc(obj.title||obj.name||'')}">`;
  }
  const svg = (kind==='post') ? postCoverSvg(obj,w,h) : posterSvg(obj,w,h);
  return `<div class="ph" style="background-image:url('${svg}')"></div>`;
}

/* ---------- 导航 / 页脚 / 搜索弹窗 ---------- */
const LOGO = `<a class="logo" href="/index.html" aria-label="片单对照">
  <span class="logo-mark">对</span>
  <span>片单对照</span>
</a>`;

const NAV = `<nav class="nav"><div class="wrap nav-in">
  ${LOGO}
  <div class="nav-links">
    <a href="/index.html" data-p="home">首页</a>
    <a href="/lists.html" data-p="lists">片单</a>
    <a href="/method.html" data-p="method">方法</a>
  </div>
  <div class="nav-right">
    <button class="icon-btn" id="searchBtn" aria-label="搜索"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg></button>
    <button class="toggle" id="themeBtn" aria-label="切换主题"><span class="dot"></span></button>
  </div>
</div></nav>`;

const FOOT = `<footer>
  <div class="wrap foot-grid">
    <div class="foot-brand">
      <div class="logo" style="font-size:20px;margin-bottom:10px"><span class="logo-mark">对</span><span>片单对照</span></div>
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
  <div class="wrap"><div class="copy">© 片单对照 · 交叉索引 · 不提供在线播放</div></div>
</footer>`;

const MODAL = `<div class="modal" id="modal"><div class="search-box">
  <input id="searchInput" placeholder="搜索影片、导演、演员或片单…" autocomplete="off" />
  <div class="hot"><span>豆瓣高分</span><span>奥斯卡</span><span>国产剧</span><span>美剧</span><span>韩剧</span><span>悬疑电影</span><span>科幻电影</span><span>日漫</span><span>宫崎骏</span></div>
  <div class="results" id="searchResults"></div>
</div></div>`;

const BACK_TOP = `<button class="back-top" id="backTop" type="button" aria-label="回到顶部" title="回到顶部">
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <path d="m18 15-6-6-6 6"/>
  </svg>
</button>`;

/* ---------- 数据加载 ---------- */
let _dataPromise = null;
let _dataCache = null;
function loadData(){
  if(_dataPromise) return _dataPromise;
  _dataPromise = fetch('/data.jsonl').then(r=>{
    if(!r.ok) throw new Error('data.jsonl 加载失败: '+r.status);
    return r.text();
  }).then(text=>{
    const cats=[], lists=[], movies=[], posts=[];
    const movieById={}, listById={}, postById={}, catById={};
    text.split(/\r?\n/).forEach(line=>{
      line=line.trim(); if(!line) return;
      let o; try{ o=JSON.parse(line); }catch(e){ return; }
      if(o.type==='category'){ cats.push(o); catById[o.id]=o; }
      else if(o.type==='list'){ lists.push(o); listById[o.id]=o; }
      else if(o.type==='movie'){ movies.push(o); movieById[o.id]=o; }
      else if(o.type==='post'){ posts.push(o); postById[o.id]=o; }
    });
    const listsByMovieId={};
    lists.forEach(list=>{
      (list.movies||[]).forEach(mid=>{
        (listsByMovieId[mid]||(listsByMovieId[mid]=[])).push(list);
      });
    });
    _dataCache={ categories:cats, lists, movies, posts, catById, listById, movieById, postById, listsByMovieId };
    return _dataCache;
  });
  return _dataPromise;
}

function rateNum(m){
  const n=parseFloat(m && m.rate);
  return Number.isFinite(n) ? n : 0;
}

function postsMentioning(movie, posts){
  const title=movie && movie.title;
  if(!title || title.length<2) return [];
  return (posts||[]).filter(p=>{
    const blob=[p.title, p.intro, ...(p.sections||[]).flatMap(s=>[s.h, s.body])].join('\n');
    return blob.includes(title);
  });
}

function graphReasons(movie, memberships){
  const byCat={};
  memberships.forEach(list=>{ (byCat[list.category]||(byCat[list.category]=[])).push(list); });
  const reasons=[];
  const consensus=[...(byCat.pro||[]), ...(byCat.award||[])];
  if(consensus.length>=3){
    const shown=consensus.slice(0,4);
    reasons.push({
      title:'专业评选共识',
      body:`同时出现在${shown.map(l=>l.name).join('、')}${consensus.length>4?'等':''}。`,
      lists:shown
    });
  }
  const sub=byCat.subgenre||[];
  if(sub.length>=2){
    reasons.push({
      title:'题材交叉',
      body:`既在「${sub[0].name}」，也在「${sub[1].name}」。`,
      lists:sub.slice(0,2)
    });
  }
  const person=[...(byCat.actor||[]), ...(byCat.director||[])];
  if(person.length){
    reasons.push({
      title:'人物入口',
      body:`可以从「${person[0].name}」走进来，再看同一人的其它作品。`,
      lists:person.slice(0,1)
    });
  }
  return reasons.slice(0,3);
}

function graphHops(memberships, articles){
  const byCat={};
  memberships.forEach(list=>{ (byCat[list.category]||(byCat[list.category]=[])).push(list); });
  const hops=[];
  const seen=new Set();
  function addList(list, kind, desc){
    if(!list || seen.has(list.id)) return;
    seen.add(list.id);
    hops.push({ kind, title:list.name, href:listUrl(list.id), desc });
  }
  addList((byCat.order||[])[0], 'order', '观看顺序，下一跳按名单走。');
  addList((byCat.actor||[])[0]||(byCat.director||[])[0], 'person', '人物片单，适合接着看同一人的其它作品。');
  addList((byCat.subgenre||[])[0]||(byCat.genre||[])[0]||(byCat.style||[])[0], 'topic', '题材片单，沿这条口味继续找。');
  return hops.slice(0,3);
}

function orderChains(movie, memberships, data){
  return memberships.filter(list=>list.category==='order').map(list=>{
    const ids=list.movies||[];
    const index=ids.indexOf(movie.id);
    if(index<0) return null;
    return {
      list,
      index,
      total:ids.length,
      prev:index>0 ? data.movieById[ids[index-1]] : null,
      next:index<ids.length-1 ? data.movieById[ids[index+1]] : null
    };
  }).filter(Boolean).slice(0,2);
}

function neighborAnchor(id, otherId, lists){
  let distance=9999, list=null, position=-1, total=0;
  (lists||[]).forEach(item=>{
    const a=(item.movies||[]).indexOf(id);
    const b=(item.movies||[]).indexOf(otherId);
    if(a<0 || b<0) return;
    const d=Math.abs(a-b);
    if(d<distance){ distance=d; list=item; position=b; total=(item.movies||[]).length; }
  });
  return { distance, list, position, total };
}

function neighborWhy(n){
  const bits=[];
  if(n.sharedCount>1){
    bits.push((n.sharedLists||[]).map(l=>l.name).join(' · '));
  }else if(n.anchorList){
    bits.push(n.anchorList.name);
    if(n.position>=0) bits.push(`第 ${n.position+1} / ${n.total} 部`);
    if(n.distance===1) bits.push('名单里紧挨着');
  }
  if(n.sameDirector) bits.push('同一导演');
  else if(n.sameActor) bits.push('同一主演');
  if(n.movie.year) bits.push(n.movie.year);
  return bits.join(' · ');
}

function movieGraph(id, data){
  const movie=data.movieById[id];
  const memberships=data.listsByMovieId[id]||[];
  const sharedCount=Object.create(null);
  const sharedLists=Object.create(null);
  memberships.forEach(list=>{
    (list.movies||[]).forEach(mid=>{
      if(mid===id) return;
      sharedCount[mid]=(sharedCount[mid]||0)+1;
      (sharedLists[mid]||(sharedLists[mid]=[])).push(list);
    });
  });
  const actors=movie.actors||[];
  const neighbors=Object.keys(sharedCount).map(mid=>{
    const other=data.movieById[mid];
    if(!other) return null;
    const lists=sharedLists[mid];
    const sameDirector=!!(movie.director && other.director===movie.director);
    const sameActor=actors.length>0 && (other.actors||[]).some(a=>actors.includes(a));
    const anchor=neighborAnchor(id, mid, lists);
    return {
      movie:other,
      sharedCount:sharedCount[mid],
      sharedLists:lists,
      sameDirector,
      sameActor,
      distance:anchor.distance,
      position:anchor.position,
      total:anchor.total,
      anchorList:anchor.list
    };
  }).filter(Boolean)
    .sort((a,b)=>
      b.sharedCount-a.sharedCount ||
      a.distance-b.distance ||
      (b.sameDirector?1:0)-(a.sameDirector?1:0) ||
      (b.sameActor?1:0)-(a.sameActor?1:0) ||
      rateNum(b.movie)-rateNum(a.movie)
    )
    .slice(0,6);
  const articles=postsMentioning(movie, data.posts);
  return {
    memberships,
    neighbors,
    reasons:graphReasons(movie, memberships),
    hops:graphHops(memberships, articles),
    orders:orderChains(movie, memberships, data),
    articles
  };
}

/* ---------- URL 帮助 ---------- */
function fileSlug(id){
  let text=String(id||'');
  try{ text=decodeURIComponent(text); }catch(e){}
  return text.replace(/[<>:"/\\|?*]+/g,'-').replace(/[. ]+$/,'').slice(0,120)||'item';
}
function param(name){ return new URLSearchParams(location.search).get(name); }
const listUrl  = id => `/list/${fileSlug(id)}.html`;
const detailUrl= id => `/movie/${fileSlug(id)}.html`;
const postUrl  = id => `/post/${fileSlug(id)}.html`;
const catUrl   = id => id==='featured' ? '/lists.html' : `/cat/${fileSlug(id)}.html`;

/* ---------- 渲染 helper ---------- */
function card(title, obj, href, opts={}){
  const cap = opts.cap===false ? '' : `<div class="grad"></div><div class="cap"><b>${title}</b></div>`;
  const below = opts.below ? `<div class="card-title-below">${title}</div>` : '';
  let bg='';
  if(obj && obj.type==='list'){
    bg = isImg(obj.cover) ? `<img class="ph" src="${esc(obj.cover)}" loading="lazy" referrerpolicy="no-referrer" alt="${esc(obj.name||'')}">` : collageHtml(obj,'ph');
  }else if(obj && obj.type==='movie'){
    bg=phFor(obj,400,250,'movie');
  }else if(obj && obj.type==='post'){
    bg=phFor(obj,400,250,'post');
  }else{
    bg=`<div class="ph" style="background:${palette(typeof obj==='number'?obj:0)}"></div>`;
  }
  return `<a class="card" href="${href}">${bg}${cap}</a>${below}`;
}
function hubCard(title, obj, href){
  let bg='';
  if(obj && obj.type==='list'){
    bg = isImg(obj.cover) ? `<div class="thumb"><img class="thumb-img" src="${esc(obj.cover)}" loading="lazy" referrerpolicy="no-referrer" alt="${esc(obj.name||'')}"></div>` : collageHtml(obj,'thumb');
  }else if(obj && obj.type==='post'){
    bg=`<div class="thumb">${phFor(obj,300,400,'post')}</div>`;
  }else{
    bg=`<div class="thumb"><div class="ph" style="background:${palette(typeof obj==='number'?obj:0)}"></div></div>`;
  }
  return `<a class="hub-card" href="${href}">${bg}<div class="t">${title}</div></a>`;
}
function movieItem(m, num){
  const stars = '★★★★★';
  const tags = (m.tags||[]).join(' ');
  const actors = (m.actors||[]).join(' / ');
  const detailHref = detailUrl(m.id);
  const doubanHref = m.douban_id ? `https://movie.douban.com/subject/${encodeURIComponent(m.douban_id)}/` : '';
  const douban = doubanHref
    ? `<a class="douban-link" href="${doubanHref}" target="_blank" rel="noopener noreferrer">豆瓣 ↗</a>`
    : '<span class="douban-link">豆瓣</span>';
  return `<div class="m-item" id="m${num}">
    <a class="m-detail-hit" href="${esc(detailHref)}" aria-label="查看${esc(m.title)}详情"></a>
    <h3 class="m-title"><span class="num">#</span>${m.title}</h3>
    <div class="m-poster">${phFor(m,280,420,'movie')}</div>
    <div class="m-main">
      <div class="m-rate"><span class="big">${m.rate||'—'}</span><span class="m-rate-side"><span class="stars">${stars}</span><span class="count">${m.count||''}人评价 | 来源：${douban}</span></span></div>
      <div class="m-meta"><b>标签</b>${[m.year,m.region,tags].filter(Boolean).join(' ')||'—'}</div>
      <div class="m-meta"><b>导演</b>${m.director||'—'}</div>
      <div class="m-meta"><b>主演</b>${actors||'—'}</div>
    </div>
    ${m.badge?`<div class="m-badge-cell"><span class="m-badge">${m.badge}</span></div>`:''}
  </div>`;
}
function toc(items){ return `<nav class="toc"><h4>内容导航</h4><div class="toc-links">${items.map((t,i)=>`<a href="#m${i+1}">${i+1}. ${t}</a>`).join('')}</div></nav>`; }
function tocArticle(items){ return `<nav class="toc"><h4>内容导航</h4><div class="toc-links">${items.map((t,i)=>`<a href="#p${i+1}">${i+1}. ${t}</a>`).join('')}</div></nav>`; }

/* ---------- 搜索 ---------- */
function runSearch(q, data){
  q=q.trim().toLowerCase();
  if(!q) return {movies:[],lists:[],posts:[]};
  const inStr=(s)=> (s||'').toLowerCase().includes(q);
  const movies = data.movies.filter(m=> inStr(m.title)||inStr(m.orig)||inStr(m.director)||(m.actors||[]).some(inStr)||(m.tags||[]).some(inStr)).slice(0,8);
  const lists = data.lists.filter(l=> inStr(l.name)||inStr(l.desc)).slice(0,6);
  const posts = data.posts.filter(p=> inStr(p.title)||(p.tags||[]).some(inStr)).slice(0,6);
  return {movies,lists,posts};
}
function renderSearch(q, data){
  const box=document.getElementById('searchResults');
  if(!box) return;
  if(!q.trim()){ box.innerHTML=''; return; }
  const {movies,lists}=runSearch(q,data);
  let html='';
  if(movies.length){ html+='<div class="res-group"><span class="res-k">影片</span>'+movies.map(m=>`<a class="res" href="${detailUrl(m.id)}">${m.title} <em>${m.rate||''}</em></a>`).join('')+'</div>'; }
  if(lists.length){ html+='<div class="res-group"><span class="res-k">片单</span>'+lists.map(l=>`<a class="res" href="${listUrl(l.id)}">${l.name}</a>`).join('')+'</div>'; }
  box.innerHTML = html || '<div class="res-empty">没有找到相关结果</div>';
  box.querySelectorAll('a.res').forEach(a=>a.addEventListener('click',()=>closeModal()));
}
function closeModal(){ document.getElementById('modal')?.classList.remove('open'); }

/* ---------- 初始化壳 ---------- */
function initChrome(){
  const p = window.PAGE || 'home';
  const navEl=document.getElementById('nav');
  if(navEl){
    if(!navEl.querySelector('.nav')) navEl.innerHTML=NAV;
    navEl.querySelector(`[data-p="${p}"]`)?.classList.add('active');
  }
  const footEl=document.getElementById('foot');
  if(footEl && !footEl.querySelector('footer')) footEl.innerHTML=FOOT;
  if(!document.getElementById('modal')) document.body.insertAdjacentHTML('beforeend',MODAL);
  if(!document.getElementById('backTop')) document.body.insertAdjacentHTML('beforeend',BACK_TOP);

  // 主题持久化
  const root=document.documentElement;
  const saved=localStorage.getItem('cf-theme');
  if(saved) root.setAttribute('data-theme', saved);
  document.getElementById('themeBtn')?.addEventListener('click',()=>{
    const isLight=root.getAttribute('data-theme')==='light';
    root.setAttribute('data-theme', isLight?'dark':'light');
    localStorage.setItem('cf-theme', isLight?'dark':'light');
  });

  // 搜索
  const modal=document.getElementById('modal');
  const input=document.getElementById('searchInput');
  document.getElementById('searchBtn')?.addEventListener('click',()=>{ modal.classList.add('open'); setTimeout(()=>input.focus(),30); });
  modal.onclick=e=>{ if(e.target===modal) closeModal(); };
  document.addEventListener('keydown',e=>{ if(e.key==='Escape') closeModal(); });
  input.addEventListener('input',()=>{ loadData().then(d=>renderSearch(input.value,d)); });
  // 热词点击
  modal.querySelectorAll('.hot span').forEach(s=>s.addEventListener('click',()=>{ input.value=s.textContent; loadData().then(d=>renderSearch(input.value,d)); }));

  // 长片单和文章页的回顶入口
  const backTop=document.getElementById('backTop');
  const syncBackTop=()=>backTop.classList.toggle('show', window.scrollY>520);
  backTop.addEventListener('click',()=>window.scrollTo({top:0,behavior:'smooth'}));
  window.addEventListener('scroll',syncBackTop,{passive:true});
  syncBackTop();

  const filterBar=document.getElementById('filterBar');
  if(filterBar){
    filterBar.addEventListener('click', e=>{
      const btn=e.target.closest('[data-f]');
      if(!btn) return;
      const key=btn.dataset.f;
      filterBar.querySelectorAll('[data-f]').forEach(x=>x.classList.toggle('active', x===btn));
      document.querySelectorAll('#movieList .m-item').forEach(item=>{
        item.hidden = !(key==='all' || item.dataset.kind===key);
      });
    });
  }
  const tg=document.getElementById('toggleSyn'), syn=document.getElementById('syn');
  if(tg && syn) tg.onclick=()=>{ const o=syn.classList.toggle('open'); tg.textContent=o?'收起 ▴':'展开全部 ▾'; };
}

const TONIGHT_MOODS={
  brain:{ label:'烧脑', keys:['悬疑','烧脑','推理','科幻','谜'] },
  heal:{ label:'治愈', keys:['治愈','温情','爱情','动画','纪录','家庭','文艺'] },
  thrill:{ label:'刺激', keys:['动作','犯罪','恐怖','战争','冒险','惊悚'] },
  easy:{ label:'不想动脑子', keys:['喜剧','搞笑','萌','歌舞','轻松'] }
};

function isCnRegion(movie){
  return /中国|大陆|香港|台湾|内地|澳门/.test(movie && movie.region || '');
}

function inOrderList(movieId, data){
  return (data.listsByMovieId[movieId]||[]).some(list=>list.category==='order');
}

function moodKeysHit(text, keys){
  return keys.some(key=>(text||'').includes(key));
}

function pickDiverse(ranked, n){
  const out=[], seen=new Set(), used=new Set();
  function fill(allowDup){
    ranked.forEach(item=>{
      if(out.length>=n) return;
      if(seen.has(item.movie.id)) return;
      const listId=item.matchingLists[0] && item.matchingLists[0].id;
      if(!allowDup && listId && used.has(listId)) return;
      seen.add(item.movie.id);
      if(listId) used.add(listId);
      out.push(item);
    });
  }
  fill(false);
  fill(true);
  return out;
}

const TONIGHT_EXTRAS={
  film:{ label:'一部电影' },
  binge:{ label:'可以连看' },
  high:{ label:'只看高分' },
  noSeries:{ label:'避开系列' },
  cn:{ label:'国产' },
  foreign:{ label:'外语' }
};

function tonightExtraOk(movie, extra, data){
  if(!extra) return true;
  if(extra==='film') return movie.episodes<=0;
  if(extra==='binge') return movie.episodes>0 || inOrderList(movie.id, data);
  if(extra==='high') return rateNum(movie)>=8.5;
  if(extra==='noSeries') return movie.episodes<=0 && !inOrderList(movie.id, data);
  if(extra==='cn') return isCnRegion(movie);
  if(extra==='foreign') return !isCnRegion(movie);
  return true;
}

function tonightPicks(opts, data, offset){
  const mood=TONIGHT_MOODS[opts.mood];
  if(!mood && !opts.extra) return { picks:[], total:0 };
  const keys=mood ? mood.keys : [];
  const ranked=[];
  (data.movies||[]).forEach(movie=>{
    if(!tonightExtraOk(movie, opts.extra, data)) return;
    const lists=data.listsByMovieId[movie.id]||[];
    const matchingLists=mood ? lists.filter(list=>moodKeysHit(list.name, keys)) : lists.slice(0,2);
    const hitTags=mood ? (movie.tags||[]).filter(tag=>moodKeysHit(tag, keys)) : [];
    if(mood && !matchingLists.length && !hitTags.length) return;
    let score=rateNum(movie)*12 + matchingLists.length*15;
    if(hitTags.length) score+=8;
    score+=Math.min(8, lists.length);
    ranked.push({ movie, matchingLists, hitTags, score });
  });
  ranked.sort((a,b)=>b.score-a.score || rateNum(b.movie)-rateNum(a.movie));
  const start=((offset||0)%Math.max(ranked.length,1));
  const rotated=ranked.slice(start).concat(ranked.slice(0,start));
  const extraLabel=TONIGHT_EXTRAS[opts.extra] && TONIGHT_EXTRAS[opts.extra].label;
  const picks=pickDiverse(rotated, 3).map(item=>{
    let reason='';
    if(item.matchingLists.length){
      const names=item.matchingLists.slice(0,2).map(list=>list.name);
      reason=`因为在「${names.join('」和「')}」里`;
    }else if(item.hitTags.length){
      reason=`因为标签有「${item.hitTags.slice(0,2).join(' / ')}」`;
    }else if(extraLabel){
      reason=`因为选了「${extraLabel}」`;
    }
    if(item.movie.rate) reason+=`，豆瓣 ${item.movie.rate}`;
    return { movie:item.movie, lists:item.matchingLists.slice(0,2), reason };
  });
  return { picks, total:ranked.length };
}

function bindTonight(root, data){
  if(!root) return;
  const state={ mood:'', extra:'', offset:0 };

  function chip(label, on, extra){
    return `<button type="button" class="btn-sm ${on?'active':''}" ${extra}>${label}</button>`;
  }

  function render(){
    const hasQuery=!!(state.mood || state.extra);
    const result=hasQuery ? tonightPicks(state, data, state.offset) : { picks:[], total:0 };
    const shuffle=result.total>3
      ? `<button type="button" class="btn-sm" data-k="shuffle">换一批</button>`
      : '';
    let body='';
    if(!hasQuery){
      body='<p class="tonight-empty">点任意一个标签，给你三部今晚能看的。</p>';
    }else if(!result.picks.length){
      body='<p class="tonight-empty">这个组合暂时没有，换一个标签。</p>';
    }else{
      body=`<div class="tonight-picks">${result.picks.map(item=>`
        <a class="tonight-pick" href="${detailUrl(item.movie.id)}">
          <div class="tonight-poster">${phFor(item.movie,120,180,'movie')}</div>
          <div class="tonight-meta">
            <b>${esc(item.movie.title)}</b>
            ${item.movie.rate?`<span class="tonight-rate">${esc(item.movie.rate)}</span>`:''}
            <p class="tonight-why">${esc(item.reason)}</p>
          </div>
        </a>`).join('')}</div>`;
    }

    root.innerHTML=`
      <div class="sec-head">
        <div class="sec-title">今晚看什么</div>
        ${shuffle}
      </div>
      <div class="tonight-filters">
        ${Object.keys(TONIGHT_MOODS).map(id=>chip(TONIGHT_MOODS[id].label, state.mood===id, `data-k="mood" data-v="${id}"`)).join('')}
        <span class="tonight-sep"></span>
        ${Object.keys(TONIGHT_EXTRAS).map(id=>chip(TONIGHT_EXTRAS[id].label, state.extra===id, `data-k="extra" data-v="${id}"`)).join('')}
      </div>
      ${body}`;
  }

  root.addEventListener('click', e=>{
    const btn=e.target.closest('[data-k]');
    if(!btn) return;
    e.preventDefault();
    const key=btn.dataset.k, value=btn.dataset.v;
    if(key==='mood') state.mood=state.mood===value?'':value;
    else if(key==='extra') state.extra=state.extra===value?'':value;
    else if(key==='shuffle') state.offset+=3;
    else return;
    if(key!=='shuffle') state.offset=0;
    render();
  });

  render();
}

function bindHero(root, posts){
  if(!root) return;
  root.classList.add('hero-carousel');
  if(!root.querySelector('.hero-big') && posts && posts.length){
    const made=posts.slice(0,8);
    const arrow=`<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>`;
    root.innerHTML=made.map((p,n)=>`
        <a class="hero-big${n===0?' is-on':''}" href="${postUrl(p.id)}">
          ${phFor(p,800,500,'post')}
          <div class="grad"></div>
          <div class="cap"><h2>${esc(p.title)}</h2><p>编辑精选 · ${esc((p.tags||[]).join(' / ')||'影视盘点')}</p></div>
        </a>`).join('')+(made.length>1?`
        <button type="button" class="hero-arrow hero-prev" data-d="-1" aria-label="上一篇">${arrow}</button>
        <button type="button" class="hero-arrow hero-next" data-d="1" aria-label="下一篇">${arrow}</button>
        <div class="hero-dots">${made.map((_,n)=>`<button type="button" class="${n===0?'on':''}" data-i="${n}" aria-label="第 ${n+1} 篇"></button>`).join('')}</div>`:'');
  }
  const total=root.querySelectorAll('.hero-big').length;
  if(total<2) return;
  let index=Math.max(0, [...root.querySelectorAll('.hero-big')].findIndex(el=>el.classList.contains('is-on')));
  let timer=null;
  const paint=()=>{
    root.querySelectorAll('.hero-big').forEach((el,n)=>el.classList.toggle('is-on', n===index));
    root.querySelectorAll('.hero-dots button').forEach((el,n)=>el.classList.toggle('on', n===index));
  };
  const go=n=>{
    index=(n+total)%total;
    paint();
  };
  const stop=()=>{ if(timer){ clearInterval(timer); timer=null; } };
  const play=()=>{
    stop();
    if(window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    timer=setInterval(()=>go(index+1), 5200);
  };
  root.addEventListener('click', e=>{
    const btn=e.target.closest('[data-d],[data-i]');
    if(!btn) return;
    e.preventDefault();
    if(btn.dataset.d) go(index+(+btn.dataset.d));
    else go(+btn.dataset.i);
    play();
  });
  root.addEventListener('mouseenter', stop);
  root.addEventListener('mouseleave', play);
  document.addEventListener('visibilitychange', ()=>{ document.hidden ? stop() : play(); });
  play();
}

window.Cupfox={ loadData, param, listUrl, detailUrl, postUrl, catUrl, palette, posterSvg, postCoverSvg, collageHtml, phFor, isImg, card, hubCard, movieItem, toc, tocArticle, runSearch, initChrome, esc, movieGraph, neighborWhy, bindTonight, bindHero };

/* 脚本置于 body 末尾，#nav 已存在，直接初始化 */
initChrome();
