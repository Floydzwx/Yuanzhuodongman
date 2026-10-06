"""导出 works_index.json：每部作品 + 其包含的视频 bvid 与播放量。
Cloudflare Worker 抓取时用它把「各视频播放量」汇总成「作品播放量」。"""
import json

BASE = "E:/Artificial Intelligence/WorkBuddy/2026-10-04-13-53-12"
C = json.load(open(f"{BASE}/classified.json", encoding="utf-8"))
V = {v["bvid"]: v for v in json.load(open(f"{BASE}/videos_full.json", encoding="utf-8"))}

works = []
seen = set()


def add(key, title, vids, kind):
    vids = [b for b in vids if b not in seen and b in V]
    if not vids:
        return
    seen.update(vids)
    works.append({
        "key": key,
        "title": title,
        "kind": kind,                # fanju / paomian / birthday / other
        "bvids": vids,
        "view": sum(V[b].get("view", 0) for b in vids),
    })


for w in C["fanju"]:
    kind = "paomian" if w.get("paomian") else "fanju"
    key = w.get("base") or w.get("key") or w["main"]["title"][:30]
    add(key, w["main"]["title"], [x["bvid"] for x in w["mains"] + w["eps"]], kind)

for k, kind in (("normal", "paomian"), ("orphan", "birthday"), ("special", "other")):
    for v in C.get(k, []):
        add(f"solo-{v['bvid']}", v["title"], [v["bvid"]], kind)

out = {
    "mid": 654552,
    "up": "圆桌动漫",
    "total_videos": len(seen),
    "total_view": sum(V[b].get("view", 0) for b in seen),
    "works": works,
}
json.dump(out, open(f"{BASE}/works_index.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

print(f"作品 {len(works)} 部 | 覆盖视频 {len(seen)} 个")
from collections import Counter
print("按类型:", dict(Counter(w["kind"] for w in works)))
print(f"总播放量: {out['total_view']:,}")
print("样例:", works[0]["title"][:30], works[0]["view"], f"{len(works[0]['bvids'])} 个视频")
