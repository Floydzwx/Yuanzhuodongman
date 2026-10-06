"""自检：校验 classify.py 的 IP_ALIAS 映射 key 是否都能命中真实 body。
失效映射 = 拼写与实际 body 不一致（这类 bug 极难肉眼发现）。"""
import json, re, sys

BASE = "E:/Artificial Intelligence/WorkBuddy/2026-10-04-13-53-12"
d = json.load(open(f"{BASE}/videos_full.json", encoding="utf-8"))
src = open(f"{BASE}/classify.py", encoding="utf-8").read()
ns = {}
exec(compile(src.split("groups = collections.defaultdict")[0], "x", "exec"), ns)
pt, ALIAS = ns["parse_title"], ns["ALIAS_MAP"]

bodies = {}
for v in d:
    bodies.setdefault(pt(v["title"])[0], []).append(v)

# BRACKET_IP / SPLIT_TOKENS 等走其他通道的 key 属于预期冗余
bypass = set()
for name, key in ns.get("BRACKET_IP", []):
    bypass.add(key)
for _keys, _token, work in ns.get("SPLIT_TOKENS", []):
    bypass.add(work)
# 别名标记类（出现在【】内被剥离，不是 body）
bypass |= {"瑶瑶你别后悔", "笑笑你别后悔", "也不是所有人都想重生逼我重生是吧"}
# 十日终焉系列：body 为空走 BRACKET_IP 兜底，这些 key 属预期冗余
bypass |= {k for k in ALIAS if "集来了" in k}

dead = [k for k in ALIAS if k not in bodies and k not in bypass]
print(f"映射表 {len(ALIAS)} 条，命中 {len(ALIAS)-len(dead)} 条，失效 {len(dead)} 条（豁免 {len(bypass)} 条）")
if dead:
    print("\n失效映射（key 与实际 body 不符）：")
    for k in dead:
        # 找最接近的真实 body
        cand = min(bodies, key=lambda b: abs(len(b)-len(k)) +
                   sum(1 for x, y in zip(b, k) if x != y)) if bodies else ""
        print(f"  ✗ key: {k}")
        print(f"    最接近: {cand}")
    sys.exit(1)
print("全部命中 ✓")
