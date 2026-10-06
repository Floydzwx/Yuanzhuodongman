"""把 pay_status.json 的充电标记注入 classified.json 与 videos_full.json，
使 build_page.py 能读到 v['charged']。幂等，可反复运行。"""
import json

BASE = "E:/Artificial Intelligence/WorkBuddy/2026-10-04-13-53-12"
pay = json.load(open(f"{BASE}/pay_status.json", encoding="utf-8"))


def is_charged(s):
    """与 fetch_pay.py 的判据保持一致"""
    return bool(s.get("upower_exclusive") or s.get("upower_play")
                or s.get("chargeable_season") or s.get("ugc_pay")
                or s.get("arc_pay"))


charged_ids = {b for b, s in pay.items() if is_charged(s)}
print(f"pay_status 记录 {len(pay)} 条，充电视频 {len(charged_ids)} 个")

# 1) 注入 videos_full.json（源数据，后续重新 classify 也能继承）
V = json.load(open(f"{BASE}/videos_full.json", encoding="utf-8"))
n = 0
for v in V:
    c = v["bvid"] in charged_ids
    if v.get("charged") != c:
        v["charged"] = c
    n += 1
json.dump(V, open(f"{BASE}/videos_full.json", "w", encoding="utf-8"),
          ensure_ascii=False)
print(f"videos_full.json: {n} 条，已标记 charged {sum(1 for v in V if v.get('charged'))} 条")

# 2) 注入 classified.json（build_page.py 直接读它）
C = json.load(open(f"{BASE}/classified.json", encoding="utf-8"))


def mark(v):
    c = v["bvid"] in charged_ids
    v["charged"] = c
    return c


total = 0
for w in C["fanju"]:
    for v in [w["main"]] + w["mains"] + w["eps"]:
        mark(v)
    total += 1
for k in ("normal", "orphan", "special"):
    for v in C.get(k, []):
        mark(v)
json.dump(C, open(f"{BASE}/classified.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(f"classified.json: {total} 部番剧已更新")
