import json, re, datetime, collections, os

BASE = "E:/Artificial Intelligence/WorkBuddy/2026-10-04-13-53-12"
COVERS = f"{BASE}/covers"
d = json.load(open(f"{BASE}/videos_full.json", encoding="utf-8"))

# 充电视频 bvid 集合（由 fetch_pay.py 生成；文件不存在时视为全部非充电）
PAY_FILE = f"{BASE}/pay_status.json"
CHARGED_IDS = set()
if os.path.exists(PAY_FILE):
    _pay = json.load(open(PAY_FILE, encoding="utf-8"))
    CHARGED_IDS = {b for b, s in _pay.items()
                   if s.get("upower") or s.get("pay_preview") or s.get("upower_play")}

def safe(s, n=50):
    for c in '\\/:*?"<>|': s = s.replace(c, '_')
    return s[:n]

def fname(v):
    pic = (v.get("pic") or "").split("?")[0]
    ext = ".webp" if ".webp" in pic.lower() else (".png" if ".png" in pic.lower() else ".jpg")
    return f"{safe(v['title'])}_{v['bvid']}{ext}"

for v in d:
    s = v.get("duration")
    if isinstance(s, int): v["dur"] = s
    elif ":" in str(s or ""):
        r = 0
        for t in str(s).split(":"): r = r*60 + int(float(t))
        v["dur"] = r
    else:
        try: v["dur"] = int(float(s or 0))
        except: v["dur"] = 0
    v["date"] = datetime.datetime.fromtimestamp(v.get("pubdate") or 0).strftime("%Y-%m-%d")
    v["year"] = int(v["date"][:4])
    v["cover"] = fname(v)
    v["has_cover"] = os.path.exists(os.path.join(COVERS, v["cover"]))
    # 充电视频标记：来自 pay_status.json（fetch_pay.py 查 B 站 rights 字段所得）
    # 源数据里已有 charged 就沿用，重跑 classify 不会丢标记
    if "charged" not in v:
        v["charged"] = v["bvid"] in CHARGED_IDS

# ============ 1. 提取【】内的标记，判断是"序号"还是"别名" ============
BRACKET = re.compile(r'【([^】]*)】')

def classify_bracket(inner):
    """把【】内的标记分类。返回 (kind, val)
    kind: ep / ep_range / ep_ord / kw / alias / alias_ep
    """
    s = inner.strip()
    if not s: return None

    # ---- 分P：结尾是「P+数字」或「数字」，前面是任意作品别名 ----
    # 纯P+数字：【P2】【p6】
    m = re.fullmatch(r'[Pp]\s*(\d{1,3})', s)
    if m: return ("ep", (int(m.group(1)), None))
    # 别名 + P + 数字：我和徒弟p12 / 【誓约黑骑士P3】
    m = re.fullmatch(r'(.+?)\s*[Pp]\s*(\d{1,3})', s)
    if m: return ("alias_ep", (m.group(1), int(m.group(2))))
    # 纯数字 / 数字-数字 / 数字+数字（可有前后缀）
    m = re.fullmatch(r'(\d{1,3})(?:\s*[-–+]\s*(\d{1,3}))?(.*)', s)
    if m and m.group(1):
        a = int(m.group(1)); b = int(m.group(2)) if m.group(2) else None
        if b: return ("ep_range", (a, b))
        # 【01】【13】纯序号；【01超长电影版】这类带后缀的也算分P
        return ("ep", (a, None))
    # 别名 + 尾部两位数字：【誓约黑骑士01】
    m = re.fullmatch(r'(.+?)(\d{2})', s)
    if m and m.group(1): return ("alias_ep", (m.group(1), int(m.group(2))))
    # 第N集
    m = re.fullmatch(r'第(\d{1,3})集.*', s)
    if m: return ("ep", (int(m.group(1)), None))
    # 上中下
    if s in ("上", "中", "下", "上部", "中部", "下部"): return ("ep_ord", s)
    # 第N季（关键���而非分P）
    if re.search(r'第[一二三四五六七八九十\d]+季', s): return ("kw", s)
    # 关键词型标记（超长电影版/完结/合集/泡面番...）
    for k in ("超长电影版", "一口气看完", "完结", "合集", "全集", "泡面番"):
        if k in s: return ("kw", k)
    return ("alias", s)

def parse_title(t):
    """拆解标题：主体 + 标记列表"""
    aliases, eps, kws, ep_ord = [], [], [], []
    for inner in BRACKET.findall(t):
        r = classify_bracket(inner)
        if r is None: continue
        kind, val = r
        if kind == "ep": eps.append((val[0], val[1]))
        elif kind == "ep_range": eps.append((val[0], val[1]))
        elif kind == "ep_ord": ep_ord.append(val)
        elif kind == "alias_ep":
            aliases.append(val[0]); eps.append((val[1], None))
        elif kind == "alias": aliases.append(val)
        elif kind == "kw": kws.append(val)
    # 别名型分P 标记（无数字的篇章/批次名）：【玄薇你别后悔】【傲慢魔女篇】
    ALIAS_EP_HINT = ("你别后悔", "你别脑补", "你别害羞", "你看不见", "你追悔",
                     "魔女篇", "大佬", "小人参", "特别的")
    for _inner in BRACKET.findall(t):
        _it = _inner.strip()
        if any(h in _it for h in ALIAS_EP_HINT) and not any(ch.isdigit() for ch in _it):
            ep_ord.append(_it)
            break
    # 括号【】外裸跟的序号：【逼我重生是吧】01 / 【十日终焉】...【P9】
    for m in re.finditer(r'】\s*(\d{1,3})\b', t):
        eps.append((int(m.group(1)), None))
    m = re.search(r'】\s*(\d{1,3})\s*[-–+]\s*(\d{1,3})', t)
    if m: eps.append((int(m.group(1)), int(m.group(2))))
    # [] 和 ()
    for inner in re.findall(r'\[([^\]]*)\]', t):
        m = re.fullmatch(r'P(\d{1,3})', inner.strip(), re.I)
        if m: eps.append((int(m.group(1)), None))
    # 【】外的中文集号：第十一集来了 / 第五集来了
    for m in re.finditer(r'第([一二三四五六七八九十百零\d]+)集', t):
        cn = {"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,"十":10}
        s = m.group(1)
        if s.isdigit(): eps.append((int(s), None))
        elif s == "十": eps.append((10, None))
        elif s.startswith("十"): eps.append((10 + cn.get(s[1], 0), None))
        elif s.endswith("十"): eps.append((cn.get(s[0], 0) * 10, None))
        elif len(s) == 2 and s[0] in cn and s[1] in cn:
            eps.append((cn[s[0]] * 10 + cn[s[1]], None))
    # 主体：先剥掉 "【标记】序号" 这种粘连结构，避免残留数字进body
    t2 = re.sub(r'(【[^】]*】)\s*\d{1,3}\b', r'\1', t)
    body = BRACKET.sub('', t2)
    body = re.sub(r'\[[^\]]*\]', '', body)
    body = re.sub(r'（[^）]*）', '', body)
    body = re.sub(r'第[一二三四五六七八九十百零\d]+季', '', body)
    body = re.sub(r'第[一二三四五六七八九十百零\d]+集[^【\]]*', '', body)  # 第十一集来了…
    body = re.sub(r'第\d+集', '', body)
    body = re.sub(r'\d+-\d+', '', body)
    # 剥离"【XXNN】"被 BRACKET 误当作整体标记后残留的前缀文字
    for a in aliases:
        if a and body.startswith(a): body = body[len(a):]
    body = re.sub(r'[^一-鿿0-9A-Za-z]', '', body)
    # 【01-06】【01-11】【09-12】等区间标记 = 阶段性汇总版，非普通分P
    is_range = bool(re.search(r'【\d{1,3}\s*[-–+]\s*\d{1,3}[^】]*】', t))
    return body, aliases, eps, kws, ep_ord, is_range

for v in d:
    body, aliases, eps, kws, ep_ord, is_range = parse_title(v["title"])
    v["body"] = body
    v["is_range"] = is_range
    v["aliases"] = aliases
    v["kws"] = kws
    v["is_ep"] = bool(eps) or bool(ep_ord)
    v["eps"] = eps
    v["ep_ord"] = ep_ord

# ============ 2. 作品分组：同 IP 合并 ============
# 同一作品在不同期数/分P批次下标题措辞不同，手工归纳为同一 IP
IP_ALIAS = [
    ("每次普攻增加1点最大生命值这弓箭手也太肉了", "平A弓箭手系列"),
    # 升级就能选词条 = 弓箭手IP 的新篇章（2025-01，封面同一黑发白挑染弓箭手角色）
    ("升级就能选词条这个弓箭手无敌了", "平A弓箭手系列"),
    ("平A一下就加一点最大生命这弓箭手太肉了吧", "平A弓箭手系列"),
    ("平A一下加1点最大生命值这弓箭手无敌了", "平A弓箭手系列"),
    ("灵魂穿越到不同动漫世界而且还能共享能力", "穿越动漫世界共享能力系列"),
    ("穿越到各个动漫世界获得主角的技能还能共享能力", "穿越动漫世界共享能力系列"),
    ("只有我能听到社恐校花的心声这下被缠上了", "社恐校花心声系列"),
    ("能听到社恐校花的心声这下被缠上了", "社恐校花心声系列"),
    ("能看到邻家女生的寿命目标是让她放弃自鲨", "邻家女生寿命系列"),
    ("救下了想自鲨的女孩后发现她真的好可爱", "邻家女生寿命系列"),
    ("追了女神足足六年不同意找宝藏女孩她却急了", "宝藏女孩系列"),
    ("舔了女神足足七年却爱而不得终于遇见自己的宝藏女孩", "宝藏女孩系列"),
    ("瑶瑶你别后悔", "宝藏女孩系列"),
    ("笑笑你别后悔", "宝藏女孩系列"),
    # 宝藏女孩 / 舔女神 系列（同一IP，措辞多变）
    ("你舔了女神足足七年她却爱答不理如今终于找到自己的宝藏女孩", "宝藏女孩系列"),
    ("女神把你的好当成理所当然重来一世终于遇见了自己的宝藏女孩", "宝藏女孩系列"),
    ("不舔女神后去找了自己的宝藏女孩女神却急了", "宝藏女孩系列"),
    ("追了女神足足六年不同意找宝藏女孩她却急了", "宝藏女孩系列"),
    ("舔了女神足足七年却爱而不得终于遇见自己的宝藏女孩", "宝藏女孩系列"),
    ("舔了女神足足七年可她却把你的好当做理所当然等你找到宝藏女孩女神却急了", "宝藏女孩系列"),
    # 修正历史后：四个魔女是四部独立作品；部分集数换了标题，用 ALIAS_MAP 归位
    ("下次换我来当姐姐吧", "修正历史后我成了强欲魔女的白月光"),
    # ==== 以下为用户逐条指正后补充的归位 ====
    # 十日终焉：13 条视频（12 分P + 2 个电影版）同属一部
    ("我看到了生生不息的激荡", "十日终焉"),
    ("脑子烧穿了大结局宇宙最全预测", "十日终焉"),
    ("开局就是四场智斗现在网文质量都这么高了吗", "十日终焉"),
    ("第二集来了这次的游戏叫仓库寻道", "十日终焉"),
    ("第三集来了这次的游戏叫地牛竞技场", "十日终焉"),
    ("第四集来了这次的游戏叫人猪游戏猜概率", "十日终焉"),
    ("第五集来了这次的游戏是有奸细的人狗游戏考验信任", "十日终焉"),
    ("第六集来了这次是主线剧情揭开世界观", "十日终焉"),
    ("第七集来了这次依旧是主线剧情和楚天秋的初次交锋", "十日终焉"),
    ("第八集来了这次是最神秘的人龙游戏", "十日终焉"),
    ("第九集来了这次是和争斗有关的地鸡游戏", "十日终焉"),
    ("第十集来了这次是和团队有关的地虎游戏", "十日终焉"),
    ("第十一集来了这次是生生不息的激荡", "十日终焉"),
    # 我不是戏神：3 条同属一部
    ("体内住着一群观众不好好整乐子观众就会入侵现实", "我不是戏神"),
    ("体内的观众每天都想看我整点乐子", "我不是戏神"),
    ("神道扭曲后体内观众逼我每天盛大演出", "我不是戏神"),
    # 谋士三部曲：《这个谋士不一般》与《计谋有毒》为同IP
    ("这个谋士不一般", "谋士系列"),
    ("计谋有毒你管这叫谋士", "谋士系列"),
    ("计谋有毒这才叫谋士", "谋士系列"),
    # 校园80 / 当舔狗 → 均为《给情绪价值，我是专业的》IP
    ("校园80不好意思进去吧你", "给情绪价值我是专业的"),
    ("当舔狗就是为了赚钱", "给情绪价值我是专业的"),
    # 穿越后为了保命只能委屈女主了
    ("穿越后为了保命只能委屈女主了", "穿越后为了保命只能委屈女主了"),
    # 给室友当军师：合集版与分P版措辞不同
    ("给室友当军师结果双方军师谈上了", "给室友当军师系列"),
    ("给室友当军师结果怎么跟女方军师看对眼了", "给室友当军师系列"),
    # 也不是所有人都想重生：超长电影版 vs 分P版
    ("也不是所有人都想重生", "也不是所有人都想重生"),
    ("也不是所有人都想重生逼我重生是吧", "也不是所有人都想重生"),
    # body 中含逗号导致不一致的变体
    ("这个谋士很不一般", "谋士系列"),
    ("穿越后为了保命只能委屈女主了", "委屈女主系列"),
    # 女主你别脑补：第20集措辞不同（用「都市爽文」且标记写在末尾）
    ("穿越成了都市爽文中的反派可女主怎么这么能脑补", "女主你别脑补系列"),
    ("穿越成十恶不赦的坏蛋可这届女主怎么都这么能脑补", "女主你别脑补系列"),
    # 冰山学姐 / 冰山校花：同一部剧的两种称呼
    ("上了大学之后才发现冰山学姐是你的游戏搭子", "冰山学姐游戏搭子系列"),
    ("上大学后才发现冰山学姐是我的游戏搭子", "冰山学姐游戏搭子系列"),
    ("上大学之后才发现冰山学姐是你的游戏搭子", "冰山学姐游戏搭子系列"),
    ("我的游戏搭子居然是冰山校花", "冰山学姐游戏搭子系列"),
    # ==== 第七批修正（用户指正）====
    # 校园80：独立番剧，与「给情绪价值」无关
    ("校园80不好意思进去吧你", "校园80系列"),
    # 从长眠中醒来：首集用「青梅竹马早就已经嫁人」，后续集改叫「世界都变了」
    ("你从长眠中醒来却发现青梅竹马早就已经嫁人", "从长眠中醒来系列"),
    ("你从长眠中醒来却发现世界都变了", "从长眠中醒来系列"),
    # 重生成了（ 小）婴儿，还多了个青梅竹马 —— 同一IP 两个季度，措辞不同
    ("重生成了小婴儿还多了个青梅竹马", "重生成了婴儿系列"),
    ("重生成了婴儿还多了个青梅竹马", "重生成了婴儿系列"),
    # 捡回家系列：同一角色（银发紫瞳恶魔角），三种标题措辞
    ("下雨天被一个宠物女孩捡回了家", "捡回家系列"),
    ("被一个呆呆的女孩子捡回家了", "捡回家系列"),
    # 收租后，发现租户是同班双胞胎：有 87min【01-06】汇总版 + 14 集，属完整番剧
    ("收租后发现租户是同班双胞胎", "收租后租客雅柔系列"),
    # 关于我忘记发结局这回事儿 = 女主你别脑补 的一条分P（用户指定）
    ("关于我忘记发结局这回事儿", "女主你别脑补系列"),
    # 你十八岁生日…（"你过…这天才发现" vs "你十八岁…才发现"）
    ("你过十八岁生日这天才发现这世界上只有你是人类", "你十八岁生日才发现世界上只有你是人类"),
    ("你十八岁生日才发现世界上只有你是人类", "你十八岁生日才发现世界上只有你是人类"),
    # 00后爸爸带娃 == 上节目摆烂带娃（同一对绿发恶魔角父女；封面相似度扫描发现）
    ("00后爸爸带娃女儿哭我也跟着哭", "上节目摆烂带娃系列"),
    ("上节目摆烂带娃女儿哭了我也跟着哭", "上节目摆烂带娃系列"),
    # 注：原「系列1」已按用户要求删除—— 下列 IP 均已被 serial 规则
    # 独立判为无汇总番剧（多集但每集不足 20 分钟），不再需要指向占位系列 "1"。
    # 相关代码（IP_ALIAS 里的 "1" 映射、series_groups["1"] 提升逻辑）已一并移除。
    # 看徒弟：第12集措辞不同（"看徒弟…才知道" vs "看着徒弟…才发现"）
    ("看徒弟一点点长大逝去才知道长生是苦", "看着徒弟一点点长大逝去才发现长生是苦"),
    # 火影：完结版标题换了措辞（"穿越到火影、成了止水,带土和卡卡西的老师【完结】"），
    # 属同一部作品，应归入一起
    ("穿越到火影成了止水带土和卡卡西的老师", "穿越火影还成了止水和带土的老师"),
    # 邻家搬来个大姐姐：正文 + 【番外篇】同属一部
    ("邻家搬来个大姐姐怎么这么甜呢", "邻家大姐姐系列"),
    # 进入高中后，中二萌妹追上来了 == 校花和学神，都是我的中二小弟？
    # （封面同一角色：白银双马尾+青蓝蝴蝶结+黑发男主；212min 为真汇总版）
    ("进入高中后中二萌妹追上来了", "中二小弟系列"),
    ("校花和学神都是我的中二小弟", "中二小弟系列"),
    # ==== 以下 4 部为「无汇总版」番剧（用户指定）====
    ("我就是想被逐出宗门而已怎么就这么难呢", "逐出宗门系列"),
    ("电竞者成为最高贵职业植物大战僵尸还有这样的彩蛋", "电竞者系列"),
    ("电竞者成为最高贵职业GTA还有这样的隐藏世界观", "电竞者系列"),
    ("只有我能听到社恐校花的心声这下被缠上了", "社恐校花系列"),
    ("能听到社恐校花的心声这下被缠上了", "社恐校花系列"),
    ("邻家搬来个大姐姐怎么这么甜呢", "邻家大姐姐系列"),
    # 大臣你别脑补 == 你刚当上皇帝却发现满朝奸臣（141min超长电影版）
    # （电影版封面标题即「穿越成大秦皇帝」，两奸臣戴乌纱帽；用户指正）
    ("穿越成大秦皇帝结果发现满朝的奸臣但关键是他们怎么都这么能脑补", "大臣别脑补系列"),
    ("你刚当上皇帝却发现满朝奸臣关键是他们还特别能脑补", "大臣别脑补系列"),
    # 考官：还能这么通过考试的？/ 在魔法世界用阴间卡组 == 我一个神官，会点黑暗魔法很合理吧
    # （封面为同一黑发白挑染主角，简笔画画风，用户确认同IP）
    ("考官还能这么通过考试的", "神官黑暗魔法系列"),
    ("在魔法世界用阴间卡组考官血压上来了", "神官黑暗魔法系列"),
    # 敌人：他说的都是我的词儿啊！== 我一个神官，会点黑暗魔法很合理吧
    # （封面完全相同，仅多「P1」角标；用户确认是同一部）
    ("敌人他说的都是我的词儿啊", "神官黑暗魔法系列"),
    ("我一个神官会点黑暗魔法很合理吧", "神官黑暗魔法系列"),
    # 雨中舞剑 == 用爱感化反派后…【瑶瑶篇】
    ("雨中舞剑但真有怪兽", "用爱感化反派·瑶瑶篇"),
    # 被你捧红的女帝要杀你：独立番剧（56min 汇总 + 14min 分P）
    ("被你捧红的女帝要杀你知道真相后她追悔莫及", "女帝要杀你系列"),
    # 在世人眼里你是一个大反派 == 女帝徒弟们都以为你是个超级大反派
    # （18 个分P 2023-01~02，随后 2023-04 出144min 超长电影版，用户凭封面确认同IP）
    ("在世人眼里你是一个大反派可记忆被曝光后事情反转了", "大反派记忆曝光系列"),
    ("女帝徒弟们都以为你是个超级大反派可记忆曝光后她们都哭了", "大反派记忆曝光系列"),
]

# ==== 独立作品拆分：同一IP 下的「第二季」「雅娴篇」等属于不同番剧 ====
# 依据用户判断：各季/各篇时长相加可超过总时长且内容不重叠 -> 独立番剧
SPLIT_TOKENS = [
    # 《重生后，我成了小富婆的电竞经理》
    (("小富婆的电竞经理",), "第二季", "小富婆电竞经理·第二季"),
    # 《用爱感化反派后，她们觉醒记忆找上门了》
    (("用爱感化反派",), "雅娴篇", "用爱感化反派·雅娴篇"),
    (("用爱感化反派",), "瑶瑶篇", "用爱感化反派·瑶瑶篇"),
    # ==== 用户指定：《瑶瑶你别后悔》三部曲独立成番剧 ====
    # 原先它们混在「宝藏女孩」系列里当分P，但那是一条独立故事线
    # （女主视角的完结合集 + 两条正片），应单独成番剧。
    # 三条视频：合集版（2023-07-29）、正片（2023-06-10）、正片完结（2023-07-03）
    (("女神把你的好当成理所当然", "瑶瑶你别后悔"), "瑶瑶你别后悔", "宝藏女孩·瑶瑶你别后悔"),
]
# 分P 批次标记（属于同一季内部的分P，不应触发拆分）
BATCH_TOKENS = ("呆呆大小姐", "我独自长眠", "恋爱就是战争", "女主你别脑补",
                "怎么这么肉", "十人碎片", "誓约黑骑士", "长老你别脑补", "寄生修仙",
                "不要小看落魄魔王", "我和徒弟", "P", "p")

def split_work(v, base_key):
    """检测标题中的「第二季」「雅娴篇」等，返回独立作品 key"""
    t = v["title"]
    for keys, token, work in SPLIT_TOKENS:
        if not any(k in t for k in keys):
            continue
        if token in t:
            return work
    # 小富婆电竞经理：第二季于 2026-09 发布，【12】【13】于 2026-10 发布，
    # 属第二季的后续分P（时间上紧随第二季、且晚于第一季完结版）
    if "小富婆的电竞经理" in t:
        import datetime as _dt
        _d = _dt.datetime.fromtimestamp(v.get("pubdate") or 0)
        if _d.year == 2026 and _d.month >= 10:
            return "小富婆电竞经理·第二季"
    return base_key

ALIAS_MAP = dict(IP_ALIAS)
WITCH_NAMES = ("愤怒", "傲慢", "怠惰", "强欲")
# 【宝具之王】与【宝具之王2】是两部独立番剧
TREASURE_RE = re.compile(r'宝具之王\s*(\d*)')

# ==== 特别篇：活动/拜年/杂谈/资讯类，非叙事作品 ====
SPECIAL_KW = [
    "新春会", "拜年", "年歌舞", "连轴转", "唠唠嗑", "唠唠", "杂谈",
    "读评论", "二创", "画展", "原创画展", "BW", "情报", "导视",
    "生日", "周年", "直播回放", "挑战赛", "报告", "春晚", "波纹",
]
# 叙事作品关键词：出现这些的即使含「生日」也不是特别篇
NARRATIVE_KW = ("发现", "只有你", "这个世界", "重生", "穿越", "系统", "我成了", "白月光")

# ==== 用户指定：以下视频一律归入特别篇（资讯/短片/杂谈，不是分P）====
# 这些标题无叙事主体、时长短，属官方资讯或趣味短片，放在「分P 集」会误导。
USER_SPECIAL_TITLES = (
    "近期最离奇的失踪案",
    "要是一直能感受这温暖",
    "蚊子为什么要吸血",
    "火爆全网的治愈搞笑番",
    "沙雕番？不，这是权斗番",
    "柱训练开播",
    "斩神大结局终于来了",
    "播放近21亿，玄骨现身",
    "我独自升级动画高潮到来",
    "我们的周边上线啦",
    "悼念我独自升级漫画作者去世",
    "少女体香",
    "圆桌新番爆料",
    "凡人修仙传为什么这么好看",
    "关于《我独自升级》和其作者还有工作室",
    "26年的周边日历来啦",
)

# ==== 用户指定：以下视频不属于分P集，归入泡面番 ====
# 唯独以下几条保留在分P 集（它们是同 IP 的贺年/生日分P）。
USER_PM_FROM_ORPHAN_TITLES = tuple(
    t for t in USER_SPECIAL_TITLES
)
KEEP_IN_ORPHAN = (
    "新年快乐，但是圆桌宇宙版",
    # ==== 用户指定：以下 6 条归入分P 集 ====
    # 拜年 / 生日贺岁短片，属同 IP 的贺年分P，不是泡面番短片。
    "雅柔，生日快乐",
    "给各大女主拜年，大家一起吃年夜饭",
    "瑶瑶，生日快乐",
    "圆桌动漫的小拜年纪",
    "拜年连轴转是什么体验",
    "【拜年小单品】",
)


def _norm(t):
    """归一化标题用于精确比对：去掉空白与常见标点差异"""
    return t.replace("，", ",").replace("？", "?").replace("！", "!").strip()


_USER_SPECIAL_N = tuple(_norm(t) for t in USER_SPECIAL_TITLES)
_KEEP_ORPHAN_N = tuple(_norm(t) for t in KEEP_IN_ORPHAN)

# 注：《穿越到火影、成了止水,带土和卡卡西的老师【完结】》已由 IP_ALIAS 中的
# ("穿越到火影、成了止水,带土和卡卡西的老师" -> "穿越火影还成了止水和带土的老师")
# 归入同一 IP，无需额外规则。


def is_special(v):
    t = v["title"]
    n = _norm(t)
    # 用户指定优先：白名单直接判特别篇
    for kw in _USER_SPECIAL_N:
        if n.startswith(kw):
            return True
    # 用户指定保留：这些即便命中关键词也留在分P 集
    for kw in _KEEP_ORPHAN_N:
        if n.startswith(kw):
            return False
    # 叙事类作品豁免（例：「你十八岁生日才发现，这世界上只有你是人类」是番剧不是活动）
    if any(k in t for k in ("才发现", "只有你是人类", "只有你")) and any(
            k in t for k in ("发现", "人类", "重生", "穿越")):
        return False
    return any(k in t for k in SPECIAL_KW)

# body 为空时（标题主体全在【】内，如【十日终焉】第二集来了…），
# 退化为用【】内的作品名做分组依据
BRACKET_IP = [
    ("十日终焉", "十日终焉"),
    ("我不是戏神", "我不是戏神"),
]

def ip_of(v):
    """把同IP 的不同分支/不同措辞合并到统一 key"""
    b = v["body"]
    if is_special(v): return "特别篇"
    if not b:
        for inner in BRACKET.findall(v["title"]):
            for name, key in BRACKET_IP:
                if name in inner:
                    return key
    # 修正历史后系列：按魔女名拆成四部独立作品
    for w in WITCH_NAMES:
        if f"{w}魔女" in v["title"]:
            return f"修正历史后我成了{w}魔女的白月光"
    # 宝具之王：1 与 2 是两部独立番剧
    m = TREASURE_RE.search(v["title"])
    if m:
        num = m.group(1)
        return ("本体被困高塔我开小号偷偷拯救世界【宝具之王】" if num in ("", "1")
                else f"本体被困高塔我开小号偷偷拯救世界【宝具之王{num}】")
    if b.startswith("修正历史后"):
        return "修正历史后·其他魔女"
    base = ALIAS_MAP.get(b, b)
    # 独立作品拆分（第二季 / 雅娴篇 / 瑶瑶篇…）
    return split_work(v, base)

FANJU_MIN = 1200   # 20 分钟：低于此值的单集视为分P 片段，不足以称番剧

groups = collections.defaultdict(lambda: {"mains": [], "eps": [], "fanju_flag": False,
                                          "paomian": False, "reasons": set()})
for v in d:
    k = ip_of(v)
    g = groups[k]
    g["key"] = k
    t = v["title"]
    rs = []
    if v["dur"] > 3600: rs.append("时长>1小时")
    # 「泡面番」是UP主自己在标题里打的标签，一律以标题为准（不再按年份区分）
    is_pm_title = "泡面番" in t
    for kw in v["kws"]:
        if kw == "泡面番": continue
        rs.append(f"标题含「{kw}」")
    if is_pm_title: rs.insert(0, "标题标注泡面番")
    v["rules"] = rs
    if rs: g["fanju_flag"] = True; g["reasons"].update(rs)
    # 「泡面番」只看主视频：组内任一分P 带此标签不代表整组是泡面番
    # （如「误入天才群聊」有【泡面番】分P，但主视频是 62 分钟【01-06】合集，属番剧）
    if is_pm_title: g["pm_titled"] = True
    # 区间合集片（【01-11】【完结】）视为阶段性汇总版，进 mains 参与主视频竞争
    if v["is_ep"] and not v.get("is_range"): g["eps"].append(v)
    else: g["mains"].append(v)

# 组内若某个「带集号」的条目时长远超其他分P（如【强欲魔女12】88min vs 其余 10min），
# 说明它是独立长篇而非分P片段，应参与主视频竞争
for k, g in groups.items():
    if not g["eps"]: continue
    emax = max(e["dur"] for e in g["eps"])
    if emax < FANJU_MIN: continue
    longs = [e for e in g["eps"] if e["dur"] >= FANJU_MIN]
    for e in longs:
        g["eps"].remove(e)
        g["mains"].append(e)
        g["reasons"].add("长篇单集作汇总版")

# 规则3：一个IP 若有分P 历史，则该IP 视为番剧作品
for k, g in groups.items():
    if g["eps"]:
        g["fanju_flag"] = True
        g["reasons"].add(f"有{len(g['eps'])}个分P历史")

# ==== 关键约束：只有「非分P 且够长」的视频才能当番剧主视频 ====
# 分P 短视频（5~20分钟）即使被规则3 连带标记为番剧，也不应作为番剧本体。
# 注意：泡面番规则优先级最高，不受此时长门槛约束。
FANJU_MIN = 1200   # 20 分钟：低于此值的单集视为分P 片段，不足以称番剧

# 用户明确指定为独立番剧的短篇（虽不足 20 分钟，本身就是一部完整作品）
SHORT_FANJU = {"校园80系列", "捡回家系列"}
for k, g in list(groups.items()):
    real = [v for v in g["mains"] if v["dur"] >= FANJU_MIN]
    pm = [v for v in g["mains"] if "泡面番" in v["title"]]
    force = k in SHORT_FANJU
    # 用户指定：组内有 2 个以上带集号的视频，就是一部连载中的无汇总番剧，
    # 即使每集都不足 20 分钟（如《穿越火影…》《你和校花成为了契约者…》）。
    # 注意不能只看 eps —— 部分作品的集号视频会先落进 mains。
    serial = (len(g["eps"]) + len(g["mains"]) >= 2) and not real and not pm
    if g["fanju_flag"] and not real and not pm and not force and not serial:
        g["fanju_flag"] = False
        g["downgraded"] = True
        g["reasons"] = set()
    # 组内已有长视频（>=FANJU_MIN）作主视频时，其余短片一律归为分P
    # 例：大反派记忆曝光系列 —— 144min 电影版 + 18 个 5~10min 分P（含无集号的首集与大结局）
    if real and not pm and not force:
        short = [v for v in g["mains"] if v["dur"] < FANJU_MIN]
        if short and g["eps"]:
            g["mains"] = [v for v in g["mains"] if v["dur"] >= FANJU_MIN]
            g["eps"] = sorted(g["eps"] + short, key=lambda x: x.get("pubdate", 0))
            g["reasons"].add(f"另有 {len(short)} 个短片作分P")
    # 同IP 下多部「逐集递进」的短片（如捡回家系列 12min->44min->84min）-> 归为分P
    if force and len(g["mains"]) > 1 and not g["eps"]:
        ordered = sorted(g["mains"], key=lambda x: x.get("pubdate", 0))
        g["main"] = ordered[-1]          # 最长的一条作为主视频
        g["mains"] = [g["main"]]
        g["eps"] = ordered[:-1]          # 其余作为分P，避免与主视频重复计数
        g["multi_version"] = True
        g["reasons"].add("同IP 逐集递进发布")
    # 整组都是短片（无一条达 FANJU_MIN）-> 全部视为分P 片段
    if not real and not pm and not force and (g["mains"] or g["eps"]):
        moved = g["mains"] + g["eps"]
        g["mains"] = []
        g["eps"] = sorted(moved, key=lambda x: x.get("pubdate", 0))
        g["all_eps"] = True


# 区间片（【01-06】【03+04】）只是局部合集，不是全剧汇总版。
# 若组内存在集号更靠后的分P（如 07~14），说明该作品尚未出汇总版
#   -> 区间片降级为分P，不占主视频位，并标记 no_summary。
for k, g in groups.items():
    if not g["mains"]: continue
    def _maxep(gs):
        ns = []
        for x in gs:
            for (_a, _b) in (x.get("eps") or []):
                if _a: ns.append(_a)
                if _b: ns.append(_b)
        return max(ns) if ns else 0
    hi = _maxep(g["eps"])
    # 只处理「全部汇总候选都是区间片」的情况；
    # 若组内已有真正的汇总版（超长电影版/合集/第一季完结等），保持原样。
    rng = [v for v in g["mains"] if v.get("is_range")]
    real_sum = [v for v in g["mains"] if not v.get("is_range")
                and any(k in v["title"] for k in ("超长电影版", "合集", "完结", "一口气"))]
    if real_sum or not (rng and hi): continue
    covered = max((b for v in rng for (_a, b) in (v.get("eps") or []) if b), default=0)
    if covered and covered < hi:
        for v in rng:
            g["mains"].remove(v); g["eps"].append(v)
        g["no_summary"] = True
        g["eps"].sort(key=lambda x: x.get("pubdate", 0))
        g["mains"].sort(key=lambda x: x.get("pubdate", 0))
        if g["mains"]: g["main"] = g["mains"][0]


# 同IP 全是短片时，首集 /【大结局】等无集号条目也按发布时间补上集号
for k, g in groups.items():
    if not g.get("all_eps"): continue
    for i, v in enumerate(g["eps"], 1):
        v["is_ep"] = True
        v["ep_no"] = i
        v["eps"] = [(i, None)]

# 特别篇独立成类，不参与番剧判定
for _k, _g in groups.items():
    if _k == "特别篇":
        _g["fanju_flag"] = False
        _g["is_special"] = True


# ==== 用户指定的「无汇总版」番剧（只有分P，无汇总/合集版）====
# 必须在 fanju_flag 判定之前处理：这些组全是短片，原本会被判为非番剧。
NO_SUMMARY_IPS = {"逐出宗门系列", "电竞者系列", "社恐校花系列", "邻家大姐姐系列"}
for _k, _g in groups.items():
    if _g.get("key") in NO_SUMMARY_IPS:
        _g["no_summary"] = True
        _g["fanju_flag"] = True# 强制成为番剧

fanju = [g for g in groups.values() if g["fanju_flag"]]

# ==== 无汇总版番剧：主视频本身也放进分P 列表 ====
# 「无汇总版」= 该作品只有分P、没有汇总版/合集版。
# 用户要求主视频本身也作为一条分P 展示（这样分P 区包含全部视频）。
for _k, _g in groups.items():
    if not _g.get("no_summary") or not _g.get("mains"):
        continue
    _mains = _g["mains"]
    if not _mains:
        continue
    _mv = _mains[0]
    if _mv in _g["eps"]:
        continue
    # 保持发布时间顺序
    _g["eps"].append(_mv)
    _g["eps"].sort(key=lambda x: x.get("pubdate", 0))
    # 展示用的 main 仍指向第一个汇总候选（渲染时不再重复显示）
    _g["main"] = _mv

# ==== 用户指定：某些只有单条/少量分P的短片归入泡面番 ====
PAOMIAN_EXTRA_TITLES = (
    "觉醒天赋技能剧毒之源",
)

# ==== 用户自定义「系列」：不参与番剧判定，独立成类展示 ====
# 键为纯数字/单字符的分组视为用户系列占位名（如 "1"，用户后续会改名）
series_groups = {k: g for k, g in groups.items() if k.strip().isdigit() or (len(k.strip()) <= 2 and not any(c in k for c in "的了是我你他她"))}
# 取出用户系列1（"1"），它将按 IP 拆分为独立番剧，不作为系列展示
for k in series_groups:
    g = groups[k]
    g["is_series"] = True
    g["fanju_flag"] = False
    g["mains"].sort(key=lambda x: x.get("pubdate", 0))
    g["eps"].sort(key=lambda x: x.get("pubdate", 0))
    if g["mains"]:
        g["main"] = g["mains"][0]
    elif g["eps"]:
        g["main"] = g["eps"][0]
fanju = [g for g in groups.values() if g["fanju_flag"]]

# ==== 用户指定：某些只有单条/少量分P的短片归入泡面番 ====
PAOMIAN_EXTRA_TITLES = (
    "觉醒天赋技能剧毒之源",
)

# ==== 用户指定：这些作品虽带「泡面番」标签，但实为无汇总版番剧 ====
# 《收租后，发现租户是同班双胞胎》共 14 集，UP 主从未发布汇总版，应作无汇总番剧
FORCE_NOT_PAOMIAN = (
    "收租后，发现租户是同班双胞胎",
)

# ==== 用户指定：这些是「无汇总版」番剧 ====
# 判定依据：组内没有真正的超长电影版 / 完整汇总版，最长的也只是
# 【01-03】这类合并集（<90min），且单集分P 齐全，应作无汇总番剧。
# 怠惰魔女：最长仅 48min（【04-08】），其余 12 集均为 8~19min 的单集。
# 强欲魔女：mains 里混了 88min 的【强欲魔女12】等合并集，但不是完整汇总；
#           真正的单集是 9~11min 的 01~09，按无汇总处理。
# 对比：愤怒魔女有 226min 超长电影版、傲慢魔女有 180min，属有汇总版。
FORCE_NO_SUMMARY = (
    "怠惰魔女",
    "强欲魔女",
)

for g in fanju:
    # 强制无汇总：把 mains 里的合并集也降级成分P，统一走"取最早"逻辑
    # 注意：此处 g["base"] 要么是旧值、要么尚未赋值（下面才g["base"]=...），
    # 所以用 key / main.body /各视频标题一起判断，避免匹配不到。
    _hay = " ".join([str(g.get("base") or ""), str(g.get("key") or ""),
                     str((g.get("main") or {}).get("body") or "")] +
                    [v["title"] for v in (g["mains"] + g["eps"])])
    if any(k in _hay for k in FORCE_NO_SUMMARY):
        g["eps"] = sorted(g["mains"] + g["eps"], key=lambda x: x.get("pubdate", 0))
        g["mains"] = []
        g["no_summary"] = True
        g["reasons"] = {"用户指定为无汇总番剧"}
    if g["mains"]:
        g["mains"].sort(key=lambda x: -x["dur"])
        g["main"] = g["mains"][0]
    else:
        # 无汇总版：按用户要求，展示视频取该系列中**发布最早**的那条
        # （原逻辑取"分P中最长"，会让《怠惰魔女》选中 48min 的【04-08】
        #   而非1 月16 日首发的【01-03】）
        g["main"] = min(g["eps"], key=lambda x: x.get("pubdate", 0))
        g["eps"] = [x for x in g["eps"] if x["bvid"] != g["main"]["bvid"]]
        g["mains"] = [g["main"]]
        g["no_summary"] = True
        if not g["main"]["rules"]:
            g["main"]["rules"] = ["⚠ 无汇总版（取最早发布的一条）"]
    g["eps"].sort(key=lambda x: x.get("pubdate", 0))
    g["base"] = g.get("key") or g["main"]["body"]
    # 泡面番最终判定：只认主视频标题 + 用户指定清单
    # 组内某个分P带「泡面番」标签不足以把整组打成泡面番
    g["paomian"] = ("泡面番" in g["main"]["title"]) or \
                   any(t in g["main"]["title"] for t in PAOMIAN_EXTRA_TITLES)
    # 用户否决：该作品不是泡面番
    if any(t in g["main"]["title"] for t in FORCE_NOT_PAOMIAN):
        g["paomian"] = False
        g["reasons"] = set(x for x in g.get("reasons", set()) if x != "标题标注泡面番")
        # 用户指定为无汇总版番剧：组内没有真正的超长汇总版
        if g["main"]["dur"] < 3600 and len(g["eps"]) >= 3:
            g["no_summary"] = True
            if not g["main"]["rules"]:
                g["main"]["rules"] = ["⚠ 无汇总版（分P中最长）"]
    if g["paomian"]:
        g["reasons"] = set(g.get("reasons", set())) | {"标题标注泡面番"}

# 默认排序：发布时间从远到近（最早发布的排在最前）
fanju.sort(key=lambda g: g["main"].get("pubdate", 0))
fk = set(id(g) for g in fanju)
_sp = groups.get("特别篇", {})
special = sorted(_sp.get("mains", []) + _sp.get("eps", []), key=lambda x: x.get("pubdate", 0))
_others = [g for k, g in groups.items()
           if g not in fanju and not g.get("is_special") and k not in series_groups]
# 用户指定：剧毒之源等归入泡面番（从原分组中移除并单列）
_paomian_extra = []
for _k, _g in list(groups.items()):
    if _k in series_groups:
        continue
    _keep_m = [v for v in _g["mains"] if not any(t in v["title"] for t in PAOMIAN_EXTRA_TITLES)]
    _move = [v for v in _g["mains"] if v not in _keep_m]
    if not _move:
        continue
    _g["mains"] = _keep_m
    if _keep_m:
        _g["main"] = _keep_m[0]
    _paomian_extra += _move

normal = [v for g in _others for v in g["mains"]]
for v in normal:
    v["paomian"] = True

# ==== 用户指定：某些只有单条的作品归入泡面番（从分P 集/番剧中提取）====
for v in normal:
    v["paomian"] = True
orphan = [v for g in _others for v in g["eps"]]

# ==== 用户指定：「分P 集」里除「新年快乐，但是圆桌宇宙版」外，全部归入泡面番 ====
# 分P 集本应只放同 IP 的贺年/周年分P，其余带【01】编号但无叙事主体的短片
# 放在这里会让人误以为它们是某部番剧的正式分P。
_keep_orphan, _to_pm = [], []
for v in orphan:
    if any(v["title"].replace("，", ",").startswith(k)
           for k in ("新年快乐，但是圆桌宇宙版", "新年快乐,但圆桌宇宙版")):
        _keep_orphan.append(v)
    else:
        _to_pm.append(v)
if _to_pm:
    for v in _to_pm:
        v["paomian"] = True
    normal += _to_pm
orphan = _keep_orphan
print(f"\n分P 集：{len(orphan)} 条保留，其余 {len(_to_pm)} 条按用户指定归入泡面番")

_pm_from_orphan = [v for v in orphan
                   if "泡面番" in v["title"]
                   or any(t in v["title"] for t in PAOMIAN_EXTRA_TITLES)]
if _pm_from_orphan:
    _keep = []
    for v in orphan:
        if v in _pm_from_orphan:
            v["paomian"] = True
        else:
            _keep.append(v)
    orphan = _keep
    normal += _pm_from_orphan
normal.sort(key=lambda v: v.get("pubdate", 0))
orphan.sort(key=lambda v: v["title"])

# 为网页排序准备聚合字段
# ==== 兜底：无汇总版的主视频必须也出现在分P 列表中 ====
# （放在所有分类逻辑之后，确保每个 no_summary 组都满足）
# 追加：系列1 提升来的组不在 groups 里，需单独并入 fanju 后统一处理
for _g in fanju:
    if not _g.get("no_summary"):
        continue
    # 无汇总版：主视频本身不在 eps 里（页面已单独渲染主视频卡），
    # 若再塞进 eps 会导致同一视频出现两次。此处只保证其余 mains 都在 eps 中。
    _ep_ids = {v["bvid"] for v in _g["eps"]} | {_g["main"]["bvid"]}
    for _mv in list(_g["mains"]):
        if _mv["bvid"] in _ep_ids:
            continue
        _g["eps"].append(_mv)
        _ep_ids.add(_mv["bvid"])
    _g["eps"].sort(key=lambda x: x.get("pubdate", 0))
    # 记录主视频即首集（页面展示用，不参与渲染）
    _g["main_in_eps"] = False

# ==== 全局去重：同一作品内 mains/eps 不得出现重复 bvid ====
# 根因：主视频既作 main 又留在 mains[0]，无汇总版还会把它复制进 eps，
# 多条路径叠加后同一 BV 号会出现 2~4 次。这里按 bvid 保留首次出现。
for _g in fanju:
    _seen = set()
    _nm, _ne = [], []
    for _v in _g.get("mains", []):
        if _v["bvid"] in _seen:
            continue
        _seen.add(_v["bvid"]); _nm.append(_v)
    for _v in _g.get("eps", []):
        if _v["bvid"] in _seen:
            continue
        _seen.add(_v["bvid"]); _ne.append(_v)
    # 主视频本身只应出现在 mains（它就是主视频），从 eps 中剔除
    _ne = [v for v in _ne if v["bvid"] != _g["main"]["bvid"]]
    _g["mains"], _g["eps"] = _nm, _ne

for g in fanju:
    m = g["main"]
    g["start_ts"] = min([x.get("pubdate", 0) for x in (g["mains"] + g["eps"])] or [m.get("pubdate", 0)])
    g["year"] = m["date"][:4]
    g["latest_ts"] = max([x.get("pubdate", 0) for x in (g["mains"] + g["eps"])] or [m.get("pubdate", 0)])
    g["mains_dur"] = sum(x["dur"] for x in g["mains"])
    g["eps_dur"] = sum(x["dur"] for x in g["eps"])
    g["main_view"] = m.get("view", 0)
    g["total_view"] = g["main_view"] + sum(x.get("view", 0) for x in g["eps"])
    # 按 bvid 去重计数：main 也存在于 mains 中，直接 len(mains)+len(eps) 可能重复
    g["video_count"] = len({x["bvid"] for x in [m] + g["mains"] + g["eps"]})

# ==== 终极去重：凡是已归入番剧（含无汇总版）的视频，一律从
#      orphan(分P集) / normal(泡面番) / special 中剔除，确保全站一个视频只出现一次 ====
_used = set()
for _g in fanju:
    for _v in [_g["main"]] + _g["mains"] + _g["eps"]:
        _used.add(_v["bvid"])
_orphan_before = len(orphan)
orphan = [v for v in orphan if v["bvid"] not in _used]
normal = [v for v in normal if v["bvid"] not in _used]
special = [v for v in special if v["bvid"] not in _used]
orphan.sort(key=lambda v: v["title"])
normal.sort(key=lambda v: v.get("pubdate", 0))
special.sort(key=lambda v: v.get("pubdate", 0))
print(f"\n去重：分P集 {len(orphan)}（原 {_orphan_before}，剔除 {_orphan_before - len(orphan)} 条已归番剧）")

# ==== 归位修正：把误落在泡面番(normal) 里的用户指定视频挪到正确栏目 ====
# 起因：分组阶段 is_special 已判定过的条目会进入 special，但部分条目在
# 分组前就被 normal 抢先收走，导致「该进特别篇的进了泡面番」。
_orphan_ids = {v["bvid"] for v in orphan}
_special_ids = {v["bvid"] for v in special}
_back = []
for _v in normal:
    _n = _norm(_v["title"])
    if _v["bvid"] in _used:
        continue
    # 用户指定的资讯/短片 → 特别篇
    if any(_n.startswith(k) for k in _USER_SPECIAL_N) and _v["bvid"] not in _special_ids:
        _special_ids.add(_v["bvid"]); _back.append((_v, "special"))
    # 用户指定保留在分P 集的视频
    elif any(_n.startswith(k) for k in _KEEP_ORPHAN_N) and _v["bvid"] not in _orphan_ids:
        _orphan_ids.add(_v["bvid"]); _back.append((_v, "orphan"))
if _back:
    _moved = set(id(v) for v, _ in _back)
    normal = [v for v in normal if id(v) not in _moved]
    for _v, _to in _back:
        if _to == "special":
            special.append(_v)
        else:
            orphan.append(_v)
    print(f"归位修正：{len(_back)} 条从泡面番移出（"
          f"特别篇 {sum(1 for _, t in _back if t == 'special')}，"
          f"分P集 {sum(1 for _, t in _back if t == 'orphan')}）")
orphan.sort(key=lambda v: v["title"])
normal.sort(key=lambda v: v.get("pubdate", 0))
special.sort(key=lambda v: v.get("pubdate", 0))


series = []
for k, g in series_groups.items():
    items = sorted(g["mains"] + g["eps"], key=lambda x: x.get("pubdate", 0))
    series.append({"key": k, "items": items, "video_count": len(items),
                   "total_dur": sum(x["dur"] for x in items),
                   "total_view": sum(x.get("view", 0) for x in items)})
series.sort(key=lambda x: -x["video_count"])

series.sort(key=lambda x: -x["video_count"])

# series 可能与主数据有意重叠（如「无汇总分P」是副本），故用并集计算
_allids = set()
for _g in fanju: _allids |= {v["bvid"] for v in _g["mains"] + _g["eps"]}
_allids |= {v["bvid"] for v in normal} | {v["bvid"] for v in orphan} | {v["bvid"] for v in special}
for _x in series: _allids |= {v["bvid"] for v in _x["items"]}
# no_summary 组的 main 同时出现在 mains 里、并已复制进 eps，故按集合去重（上面已是并集）
tot = len(_allids)
print("=" * 60)
print(f"总视频 {len(d)}")
print(f"番剧作品 {len(fanju)} 部  |其中泡面番 {sum(1 for g in fanju if g['paomian'])} 部")
print(f"  汇总视频 {sum(len(g['mains']) for g in fanju)} 个")
print(f"  归组分P {sum(len(g['eps']) for g in fanju)} 个")
print(f"系列 {len(series)} | 特别篇 {len(special)} | 普通视频 {len(normal)} | 无归属分P {len(orphan)}")
print(f"校验: {tot} (应= {len(d)})")
print("=" * 60)
for g in fanju[:22]:
    m = g["main"]
    tag = "【泡面番】" if g["paomian"] else ""
    print(f'{m["dur"]//60:>4}min eps={len(g["eps"]):>2} {tag}{m["title"][:40]}')
    print(f'         {"、".join(sorted(g["reasons"]))[:70]}')

for g in fanju:
    g["reasons"] = sorted(g["reasons"])
    # 总时长/总播放必须覆盖该作品下**全部**视频：main + mains 里的其他汇总版 + eps。
    # 原来只算 main + eps，漏掉了 mains[1:]（同一 IP 的其它合集版/电影版），
    # 导致《用爱感化反派》等 32 部作品的总时长明显偏小。
    # 用 bvid 去重，避免 main 与 mains[0] 是同一条时被重复计入。
    _all = {}
    for v in [g["main"]] + g["mains"] + g["eps"]:
        _all[v["bvid"]] = v
    g["total_dur"] = sum(v["dur"] for v in _all.values())
    g["total_view"] = sum(v.get("view", 0) for v in _all.values())
    g["video_count"] = len(_all)


series = []
for k, g in series_groups.items():
    items = sorted(g["mains"] + g["eps"], key=lambda x: x.get("pubdate", 0))
    series.append({"key": k, "items": items, "video_count": len(items),
                   "total_dur": sum(x["dur"] for x in items),
                   "total_view": sum(x.get("view", 0) for x in items)})
series.sort(key=lambda x: -x["video_count"])

# ==== 用户系列1：按「去集号后的标题」识别同 IP，分组提升为独立番剧 ====
# 说明：这些作品全部只有分P、没有汇总版/合集版。
# 用户要求「像租客雅柔那样各自算一个番剧」——即组内选第一个视频作主视频，
# 标记 no_summary=True，由网页渲染成「无汇总版」标签，而非塞进一个杂烩系列。
import re as _re

def _ip_key(v):
    """去掉【】内的集号/标记，得到IP 本体名"""
    t = _re.sub(r"\u3010[^\u3011]*\u3011", "", v["title"])
    t = _re.sub(r"[，,。、：:；;！!？?\s]+", "", t)
    return t[:40]

series.sort(key=lambda x: -x["video_count"])

json.dump({"fanju": fanju, "normal": normal, "orphan": orphan, "special": special, "series": series},
          open(f"{BASE}/classified.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\nSAVED")
