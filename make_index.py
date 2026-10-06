import json, os, html, datetime

BASE="E:/Artificial Intelligence/WorkBuddy/2026-10-04-13-53-12"
vids=json.load(open(f"{BASE}/videos.json",encoding="utf-8"))
COVERS=f"{BASE}/covers"
files=set(os.listdir(COVERS))

def dur(s):
    s=int(s or 0); return f"{s//60}:{s%60:02d}" if s else "?"

vids=[v for v in vids if any(f.endswith(v["bvid"]+".jpg") or f.endswith(v["bvid"]+".png") or f.endswith(v["bvid"]+".webp") for f in files)]
vids.sort(key=lambda v:-(v.get("duration") or 0))

def find(v):
    for f in files:
        if v["bvid"] in f: return f
    return None

cards=[]
for v in vids:
    f=find(v); 
    if not f: continue
    pub=datetime.datetime.fromtimestamp(v["pubdate"]).strftime("%Y-%m-%d") if v.get("pubdate") else ""
    long_cls = "long" if (v.get("duration") or 0) > 1800 else ""
    cards.append(f'''<a class="card {long_cls}" href="https://www.bilibili.com/video/{v['bvid']}" target="_blank">
<img src="covers/{f.encode('ascii','ignore').decode() if f.isascii() else f}" loading="lazy">
<div class="meta">
<div class="dur">{dur(v['duration'])}</div>
<div class="t">{html.escape(v['title'])}</div>
<div class="s">{v.get('series','')} · {pub} · {v['bvid']}</div>
</div></a>''')

doc=f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>圆桌动漫 - 视频封面总览</title>
<style>
*{{box-sizing:border-box}}
body{{margin:0;padding:28px;background:#f5f6f8;color:#18191c;
font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif}}
h1{{font-size:24px;margin:0 0 6px}}
.sub{{color:#61666d;font-size:13px;margin-bottom:22px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(215px,1fr));gap:16px}}
.card{{position:relative;background:#fff;border-radius:10px;overflow:hidden;
text-decoration:none;color:inherit;box-shadow:0 1px 4px rgba(0,0,0,.08);transition:.18s}}
.card:hover{{transform:translateY(-3px);box-shadow:0 6px 18px rgba(0,0,0,.14)}}
.card img{{width:100%;aspect-ratio:16/10;object-fit:cover;display:block;background:#e8eaed}}
.dur{{position:absolute;right:7px;bottom:38px;background:rgba(0,0,0,.78);color:#fff;
font-size:12px;padding:2px 6px;border-radius:4px;font-variant-numeric:tabular-nums}}
.card.long .dur{{background:#d33b3b}}
.meta{{padding:9px 11px 12px}}
.t{{font-size:13.5px;line-height:1.45;font-weight:600;
display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;
height:2.9em}}
.s{{font-size:11.5px;color:#8a9099;margin-top:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
</style></head><body>
<h1>圆桌动漫 · 视频封面总览</h1>
<div class="sub">共 {len(cards)} 个视频（按时长从长到短排列）· 红底时长 = 超过 30 分钟 · 点击卡片跳转 B站</div>
<div class="grid">
{''.join(cards)}
</div></body></html>'''

open(f"{BASE}/covers_index.html","w",encoding="utf-8").write(doc)
print("index written:",len(cards),"cards")

over30=[v for v in vids if (v.get("duration") or 0)>1800]
print("超过30分钟:",len(over30))
for v in over30[:20]:
    print(" ",dur(v['duration']),v['title'][:40],v['bvid'])
