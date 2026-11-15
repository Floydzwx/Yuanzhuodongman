"""用户指定的新视频归档表（2026-11-15）。

设计要点：这 17 条视频在 classify.py 里**先被摘出、不参与自动分组**，
等原有 740 条全部分类完毕后，再按本表强制插入。这样：
  - 已有 100 部番剧的判定结果一字不变（零回归风险）
  - 新增视频完全按用户口头指定的归属，不受自动规则误判影响

用户原话：
  A1 → 「上大学之后，才发现冰山学姐是你的游戏搭子【超长电影版】」的分P
  B组 → 「重生后，我成了小富婆的电竞经理【第二季】」的分P，注意顺序
  C组 → 新番剧，单开一部作品
  D中2个 → 泡面番
  E1 → 新番剧，单开一部作品
  E2 → 「修正历史后，我成了强欲魔女的白月光【01-05】」的分P
"""
import datetime

# 已存在作品的 key（classified.json 里的 g["key"]）
K_ICE = "冰山学姐游戏搭子系列"
K_MANAGER = "小富婆电竞经理·第二季"
K_WITCH = "修正历史后我成了强欲魔女的白月光"

# 追加为分P 的视频（顺序即集号顺序，最终仍按 pubdate 排）
TARGET_EPS = {
    K_ICE: ["BV1MEHx6kEka"],                                    # A1 和冰山学姐一起旅行
    K_MANAGER: [                                                # B1~B4，顺序 14/15/16/17
        "BV1V5HD6HEgj",  # 【14】
        "BV1hrpx6SE9U",  # 【15】
        "BV19qp56XEcF",  # 【16】
        "BV1kkJQ6PEN8",  # 【17】
    ],
    K_WITCH: ["BV1LqWo6mE38"],                                  # E2【结局·上篇】
}

# 归入泡面番（作为单视频卡片，与既有泡面番一致）
PAOMIAN_BV = [
    "BV1Fmnx6fErA",   # D1 我一个修仙者，怎么飞升到魔法世界了？【泡面番】
    "BV1zoso6oEZh",   # D2 穿越后，我用导弹对付修仙者【泡面番】
]

# 新开番剧作品。
# C 组的主视频选 BV1TppR6xE5N（61:21，全系列唯一不带集号的长片，
#   且是该 IP 最早发布的合集型视频）；BV1gCxY6VE72【06-10】虽更长，
#   但带集号，属阶段性合并集，按分P 处理（与「强欲魔女12」同理）。
NEW_FANJU = [
    {
        "key": "你是说，我的两位青梅都是boss？",
        "main": "BV1TppR6xE5N",
        "eps": [
            "BV1HFnv6XEdE",  # 【01】
            "BV1eTnh6hE6P",  # 【02】
            "BV1fvxj6CEW8",  # 【03】
            "BV15Pxz6PE6i",  # 【04-05】
            "BV1gCxY6VE72",  # 【06-10】
            "BV1vg4B6PE5i",  # 【06-07】
            "BV1XMWB69Exz",  # 【08-09】
        ],
    },
    {
        "key": "退役后，我和敌对组织的宿敌结婚了",
        "main": "BV1HT4g6YE3N",
        "eps": [],
    },
]

HELD_BVIDS = (set(sum(TARGET_EPS.values(), [])) | set(PAOMIAN_BV) |
              {s["main"] for s in NEW_FANJU} |
              set(sum([s["eps"] for s in NEW_FANJU], [])))


def recompute(g):
    """按 classify.py 末尾的口径重算一部作品的聚合字段（按 bvid 去重）。"""
    m = g["main"]
    allv = {}
    for v in [m] + g.get("mains", []) + g.get("eps", []):
        allv[v["bvid"]] = v
    g["eps"].sort(key=lambda x: x.get("pubdate", 0))
    g["total_dur"] = sum(v["dur"] for v in allv.values())
    g["total_view"] = sum(v.get("view", 0) for v in allv.values())
    g["video_count"] = len(allv)
    g["main_view"] = m.get("view", 0)
    g["start_ts"] = min(v.get("pubdate", 0) for v in allv.values())
    g["latest_ts"] = max(v.get("pubdate", 0) for v in allv.values())
    g["year"] = m["date"][:4]
    g["mains_dur"] = sum(v["dur"] for v in g.get("mains", []))
    g["eps_dur"] = sum(v["dur"] for v in g["eps"])


def make_group(key, main, eps):
    """构造一个全新的番剧作品分组，字段与 classify.py 产出保持一致。"""
    main = dict(main)
    main.setdefault("rules", ["用户指定为新番剧作品"])
    eps = [dict(e) for e in eps]
    for e in eps:
        e.setdefault("rules", [])
    g = {
        "key": key,
        "base": key,
        "main": main,
        "mains": [main],
        "eps": eps,
        "no_summary": False,
        "paomian": False,
        "fanju_flag": True,
        "reasons": ["用户指定为新番剧作品"],
        "main_in_eps": False,
        "total_dur": 0, "total_view": 0, "video_count": 0,
        "main_view": 0, "start_ts": 0, "latest_ts": 0,
        "year": "", "mains_dur": 0, "eps_dur": 0,
    }
    recompute(g)
    return g


def apply_user_archive(fanju, normal, orphan, special, held):
    """就地修改各分类容器，把 held 的 17 条按指定规则插入。"""
    H = {v["bvid"]: v for v in held}
    missing = HELD_BVIDS - set(H)
    if missing:
        raise RuntimeError("归档表里有 bvid 未在主数据中找到: " + ", ".join(sorted(missing)))

    by_key = {g.get("key"): g for g in fanju}

    # 1) 追加到已存在作品的分P
    for key, bvs in TARGET_EPS.items():
        g = by_key.get(key)
        if not g:
            raise RuntimeError("找不到目标作品: " + key)
        exist = {v["bvid"] for v in g["eps"]}
        for bv in bvs:
            if bv not in exist:
                g["eps"].append(H[bv])
        recompute(g)
        print("  归档到 %-24s 分P +%d（现 %d 个视频）" %
              (key[:22], len(bvs), g["video_count"]))

    # 2) 新开番剧作品
    for spec in NEW_FANJU:
        main = H[spec["main"]]
        eps = [H[b] for b in spec["eps"]]
        g = make_group(spec["key"], main, eps)
        fanju.append(g)
        print("  新开番剧 %-22s 主视频=%s | 分P %d 个 | %d 个视频" %
              (spec["key"][:20], main["bvid"], len(eps), g["video_count"]))

    # 3) 泡面番
    for bv in PAOMIAN_BV:
        v = H[bv]
        v["paomian"] = True
        v.setdefault("rules", [])
        normal.append(v)
    print("  泡面番 +%d" % len(PAOMIAN_BV))

    # 4) 恢复排序（番剧按主视频发布时间从远到近，泡面番按发布时间）
    fanju.sort(key=lambda g: g["main"].get("pubdate", 0))
    normal.sort(key=lambda v: v.get("pubdate", 0))

    # 5) 全站唯一性校验：每个视频恰好出现一次
    seen = {}
    for g in fanju:
        for v in [g["main"]] + g.get("mains", []) + g.get("eps", []):
            seen.setdefault(v["bvid"], 0)
            seen[v["bvid"]] += 1
    # 同一作品内 main 与 mains[0] 是同一条，允许组内重复，只统计唯一集合
    ids_fanju = set()
    for g in fanju:
        ids_fanju |= {v["bvid"] for v in [g["main"]] + g.get("mains", []) + g.get("eps", [])}
    ids_rest = {v["bvid"] for v in normal} | {v["bvid"] for v in orphan} | {v["bvid"] for v in special}
    dup = ids_fanju & ids_rest
    if dup:
        raise RuntimeError("视频同时出现在番剧与其它栏目: " + ", ".join(sorted(dup)[:5]))
    print("  校验：番剧区 %d 个 bvid，其它栏目 %d 个，合计 %d" %
          (len(ids_fanju), len(ids_rest), len(ids_fanju | ids_rest)))
