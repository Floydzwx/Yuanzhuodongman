"""静态校验 fanju_index.html：用页面自身的渲染口径统计条目，检查重复与栏目结构。
不依赖浏览器，直接解析 HTML + 内嵌 DATA。"""
import json
import re
import io
from collections import Counter

BASE = "E:/Artificial Intelligence/WorkBuddy/2026-10-04-13-53-12"
html = io.open(f"{BASE}/fanju_index.html", encoding="utf-8").read()

print("=" * 60)
print("1. 栏目结构")
print("=" * 60)
tabs = re.findall(r'<div class="tabs">(.*?)</div>', html, re.S)
tab_names = re.findall(r"<a href=\"#(\w+)\"[^>]*>([^<]+)</a>", tabs[0]) if tabs else []
print("导航按钮:", " | ".join(f"{n}(#{i})" for i, n in tab_names))
h2s = re.findall(r'<h2 id="(\w+)">([^<]*)', html)
print("h2 区块:", " | ".join(f"{i}={t}" for i, t in h2s))
assert "nosum2" not in html, "无汇总版栏目残留！"
print("✓ 无汇总版栏目已删除")

print()
print("=" * 60)
print("2. 重复检查（页面实际渲染口径）")
print("=" * 60)
# 番剧区：由 JS 渲染，数据在 DATA 里
m = re.search(r"const DATA = (\[.*?\]);\n", html, re.S)
DATA = json.loads(m.group(1))
entries = []  # (栏目, bv)
for w in DATA:
    # w['h'] 内含主视频卡 + 其他汇总版 + 分P，页面实际就是渲染这些链接
    for bv in re.findall(r"/video/(BV[0-9A-Za-z]+)", w["h"]):
        entries.append(("番剧", bv))

# 泡面番区：静态 HTML，边界必须用 pmList 容器（h2 之后紧跟）
pm_start = html.find('<div id="pmList">')
pm_end = html.find('<h2 id="birthday">')
pm_html = html[pm_start:pm_end]
for bv in re.findall(r"/video/(BV[0-9A-Za-z]+)", pm_html):
    entries.append(("泡面番", bv))

# 分P集 / 特别篇
for sec, name, nxt in (("birthday", "特别", "other"), ("other", "其它", None)):
    s = html.find(f'<h2 id="{sec}">')
    e = html.find(f'<h2 id="{nxt}">') if nxt else html.find("</div>\n<script>")
    chunk = html[s: e if e > 0 else len(html)]
    for bv in re.findall(r"/video/(BV[0-9A-Za-z]+)", chunk):
        entries.append((name, bv))

c = Counter(bv for _, bv in entries)
dups = {b: n for b, n in c.items() if n > 1}
print(f"页面总条目 {len(entries)} | 唯一 {len(set(c))} | 重复 {len(dups)}")
if dups:
    for b, n in list(dups.items())[:10]:
        print(f"  ✗ x{n} {b}")
else:
    print("✓ 全站无重复视频")

src = {v["bvid"] for v in json.load(open(f"{BASE}/videos_full.json", encoding="utf-8"))}
print(f"源视频 {len(src)} | 页面缺 {len(src - set(c))} | 多 {len(set(c) - src)}")

print()
print("=" * 60)
print("3. 统计栏文案检查")
print("=" * 60)
print("「总时长」列已移除:", "总时长</b>" not in html)
# 无汇总作品不应有「主视频」项
ns_works = [w for w in DATA if w["ns"]]
bad = [w["t"][:24] for w in ns_works if "主视频</b>" in w["h"].split("</div>")[0]]
print(f"无汇总番剧 {len(ns_works)} 部，其中统计栏仍含「主视频」的: {len(bad)}")
for t in bad[:5]:
    print("  ✗", t)
if not bad:
    print("✓ 无汇总番剧均不显示「主视频时长」")
ok_ns = [w["t"][:20] for w in ns_works if "总时长</b>" in w["h"]]
print(f"✓ 无汇总番剧显示总时长的: {len(ok_ns)}/{len(ns_works)}")
has_ns = [w["t"][:20] for w in DATA if not w["ns"]][:3]
print("  有汇总版示例(应含主视频):", has_ns)

print()
print("=" * 60)
print("4. 三个争议作品归属")
print("=" * 60)
C = json.load(open(f"{BASE}/classified.json", encoding="utf-8"))
for kw, label in (("租户是同班双胞胎", "收租雅柔"),
                  ("误入天才群聊", "误入天才群聊"),
                  ("你说我女儿五岁了", "刚毕业女儿五岁")):
    hit = [w for w in C["fanju"] if kw in w["main"]["title"]]
    if hit:
        w = hit[0]
        print(f"{label}: 泡面番={w.get('paomian')} 无汇总={w.get('no_summary')} "
              f"视频数={len(w['mains']) + len(w['eps'])}")
        print(f"    主视频: {w['main']['title'][:48]} ({round(w['main']['dur']/60,1)}分)")
    else:
        print(f"{label}: 未归入番剧！")

print()
print("=" * 60)
print("5. 排序规则")
print("=" * 60)
js = re.search(r"const DATA = .*?</script>", html, re.S).group(0)
for line in js.split("\n"):
    if "key==='dur'" in line or "w.ns" in line:
        print("  ", line.strip())
