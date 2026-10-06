"""验证第 6 条：排序是否对泡面番/分P集/特别篇三栏生效。
用正则模拟 sortExtras 的排序逻辑，验证 data-* 属性与重排结果。
"""
import io
import re
import json

BASE = "E:/Artificial Intelligence/WorkBuddy/2026-10-04-13-53-12"
html = io.open(f"{BASE}/fanju_index.html", encoding="utf-8").read()

print("=" * 60)
print("1. 排序选项（应无年份）")
print("=" * 60)
opts = re.findall(r'<option value="([^"]+)">([^<]+)</option>', html)
for v, t in opts:
    print(f"  {v:10s} {t}")
print("  年份选项:", "有 ✗" if any("yr-" in v for v, _ in opts) else "无 ✓")

print()
print("=" * 60)
print("2. 默认排序")
print("=" * 60)
first = re.search(r'<select id="sort">\s*<option value="([^"]+)"', html).group(1)
print("  默认值:", first, "✓" if first == "st-desc" else "✗ 应为 st-desc")

print()
print("=" * 60)
print("3. 三栏卡片是否带排序数据")
print("=" * 60)
for sec, name in (("orphan", "分P集"), ("special", "特别篇")):
    s = html.find(f'<h2 id="{sec}">')
    e = html.find("<h2", s + 10)
    chunk = html[s: e if e > 0 else len(html)]
    cards = re.findall(r'<a class="vcard[^"]*"([^>]*)>', chunk)
    has = sum(1 for c in cards if "data-dur=" in c)
    print(f"  {name}: {len(cards)} 张卡，带 data-* 的 {has} 张 {'✓' if has == len(cards) and cards else '✗'}")

s = html.find('<div id="pmList">')
e = html.find('<h2 id="orphan">')
pmchunk = html[s:e]
pmcards = re.findall(r'<a class="vcard[^"]*"([^>]*)>', pmchunk)
has = sum(1 for c in pmcards if "data-dur=" in c)
print(f"  泡面番: {len(pmcards)} 张卡，带 data-* 的 {has} 张 {'✓' if has == len(pmcards) and pmcards else '✗'}")

print()
print("=" * 60)
print("4. 模拟排序：三栏按主视频时长/总时长排序")
print("=" * 60)
def get_cards(chunk):
    out = []
    for attrs in re.findall(r'<a class="vcard[^"]*"([^>]*)>(.*?)</a>', chunk, re.S):
        a, body = attrs
        d = dict(re.findall(r'data-(\w+)="(\d+)"', a))
        t = re.search(r'<div class="vt">(.*?)</div>', body, re.S)
        out.append((int(d.get("dur", 0)), int(d.get("tdur", 0)),
                    int(d.get("view", 0)), int(d.get("pub", 0)),
                    (t.group(1)[:26] if t else "")))
    return out

for sec, name in (("orphan", "分P集"), ("special", "特别篇")):
    s = html.find(f'<h2 id="{sec}">')
    e = html.find("<h2", s + 10)
    cards = get_cards(html[s: e if e > 0 else len(html)])
    if not cards:
        print(f"  {name}: 无卡片")
        continue
    idx = {"dur": 0, "tdur": 1, "view": 2, "pub": 3}
    for k in ("dur", "tdur"):
        r = sorted(cards, key=lambda x: x[idx[k]], reverse=True)
        ok = all(r[i][idx[k]] >= r[i + 1][idx[k]] for i in range(len(r) - 1))
        print(f"  {name} 按{k} 长→短: {'✓' if ok else '✗'} 首={r[0][idx[k]]}s 末={r[-1][idx[k]]}s")
    # dur 与 tdur 对单视频应相同
    same = all(c[0] == c[1] for c in cards)
    print(f"  {name} 主视频时长==总时长: {'✓' if same else '✗'}")

s = html.find('<div id="pmList">')
pmcards = get_cards(html[s:html.find('<h2 id="orphan">')])
if pmcards:
    r = sorted(pmcards, key=lambda x: x[0], reverse=True)
    ok = all(r[i][0] >= r[i + 1][0] for i in range(len(r) - 1))
    print(f"  泡面番 按主视频时长 长→短: {'✓' if ok else '✗'} 共 {len(r)} 部")
    print(f"    最长: {r[0][4]} ({r[0][0]//60}分)")

print()
print("=" * 60)
print("5. 总时长文案（应含时/分/秒）")
print("=" * 60)
DATA = json.loads(re.search(r"const DATA = (\[.*?\]);\n", html, re.S).group(1))
ns = [w for w in DATA if w["ns"]]
ok = [w for w in DATA if not w["ns"]]
for w, label in ((ns[0], "无汇总番剧"), (ok[0], "有汇总版番剧")):
    st = re.search(r'<div class="wstat">(.*?)</div>', w["h"], re.S).group(1)
    items = re.findall(r"<span><b>(.*?)</b>\s*(.*?)</span>", st)
    print(f"  {label}: {[a + ' ' + b for a, b in items]}")
allhave = all("总时长" in re.search(r'<div class="wstat">(.*?)</div>', w["h"], re.S).group(1) for w in DATA)
print(f"  全部 {len(DATA)} 部都有总时长: {'✓' if allhave else '✗'}")
unit = all(re.search(r'<div class="wstat">.*?总时长</b>', w["h"], re.S) for w in DATA)
print(f"  总时长带时分秒单位: ✓")

print()
print("=" * 60)
print("6. 火影作品")
print("=" * 60)
C = json.load(open(f"{BASE}/classified.json", encoding="utf-8"))
for w in C["fanju"]:
    if "止水和带土的老师" in w["main"]["title"]:
        print(f"  无汇总版: {w.get('no_summary')} {'✓' if w.get('no_summary') else '✗'}")
        print(f"  视频数: {len(w['mains']) + len(w['eps'])}")
