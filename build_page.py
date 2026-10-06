import json, os, html, datetime

BASE = "E:/Artificial Intelligence/WorkBuddy/2026-10-04-13-53-12"
C = json.load(open(f"{BASE}/classified.json", encoding="utf-8"))
fanju = C["fanju"]; normal = C["normal"]; orphan = C.get("orphan", [])
special = C.get("special", [])
series = C.get("series", [])

def dur(s):
    """秒 -> H:MM:SS（不足1 小时则 M:SS）"""
    s = int(s or 0)
    return f"{s//3600}:{(s%3600)//60:02d}:{s%60:02d}" if s >= 3600 else (f"{s//60}:{s%60:02d}" if s else "?")


def num(n):
    n = int(n or 0)
    return f"{n/10000:.1f}万" if n >= 10000 else str(n)

def ts2date(t):
    import datetime
    return datetime.datetime.fromtimestamp(t or 0).strftime("%Y-%m-%d")

def vcard(v, cls=""):
    img = f"covers/{v['cover']}" if v.get("has_cover") else ""
    cover = f'<img src="{html.escape(img)}" alt="">' if img else '<div class="nocov">无封面</div>'
    # data-* 供前端排序使用：这三个栏目每张卡片就是一个视频
    # dur=视频本身时长（主视频时长与总时长对单视频而言是同一个值）
    ds = (f' data-dur="{v["dur"]}" data-tdur="{v["dur"]}" '
          f'data-view="{v.get("view",0)}" data-pub="{v.get("pubdate",0)}"')
    # 充电视频：左上角红标+ 卡片加 charged 类
    charged = '<div class="payflag">充电视频</div>' if v.get("charged") else ""
    ccls = cls + (" charged" if v.get("charged") else "")
    return f'''<a class="vcard {ccls}"{ds} href="https://www.bilibili.com/video/{v['bvid']}" target="_blank">
{cover}{charged}<div class="dur">{dur(v['dur'])}</div>
<div class="vm"><div class="vt">{html.escape(v['title'])}</div>
<div class="vs">{v['date']} · {num(v.get('view',0))}播放 · {v['bvid']}</div></div></a>'''

# ===== 作品数据（供前端排序） =====
# 泡面番独立成类，不混入主番剧列表
pm_works = [w for w in fanju if w.get("paomian")]
main_works = [w for w in fanju if not w.get("paomian")]
works_data = []
for w in main_works:
    m = w["main"]
    # 统一分P 列表：其他汇总版 + 分P 短视频合并，按发布时间排序
    allex = []
    for x in w["mains"][1:]:
        allex.append((x.get("pubdate", 0), vcard(x, "alt"), x))
    for e in w["eps"]:
        allex.append((e.get("pubdate", 0), vcard(e, "ep"), e))
    allex.sort(key=lambda z: z[0])
    eps = [z[1] for z in allex]
    eps_dur = sum(z[2]["dur"] for z in allex)
    ns = w.get("no_summary", False)
    # 橙色「泡面番」标签已按用户要求移除（泡面番已有独立栏位，无需重复标注）。
    # 如需恢复，把下行取消注释即可：
    # tag_pm = '<span class="tag pm">泡面番</span>' if w.get("paomian") else ""
    tag_pm = ""
    tag = tag_pm + ('<span class="tag warn">无汇总版</span>' if ns else "")
    # 充电视频红标只做在封面上（见 vcard 里的 .payflag），标题后不再重复标注。
    # 如需恢复，把下面一行取消注释即可：
    # if m.get("charged"): tag = '<span class="tag charge">充电视频</span>' + tag
    eps_html = (f'<div class="eps"><div class="ot">分P 短视频 · {len(eps)} 个 / 合计 {eps_dur//60} 分钟</div>'
                f'<div class="hscroll">{"".join(eps)}</div></div>') if eps else ""
    html_block = f'''<div class="wmain">{vcard(m,"hero")}</div>
<div class="winfo">
<h3 title="{html.escape(m['title'])}">{html.escape(m['title'])} {tag}</h3>
<div class="wstat" data-work="{html.escape(w['base'])}">
{'' if ns else f'<span><b>{dur(m["dur"])}</b> 主视频</span>'}
<span><b>{dur(w['total_dur'])}</b> 总时长</span>
<span><b>{w['video_count']}</b> 视频数</span>
<span><b>{num(w['main_view'])}</b> {'代表作播放' if ns else '主视频播放'}</span>
<span data-live="play"><b>{num(w['total_view'])}</b> 总播放</span>
<span><b>{ts2date(w['start_ts'])}</b> 首发</span>
</div>
<!-- .wbase 暂时不显示（用户要求）。代码与样式保留，后续可放别的信息。
<div class="wbase">作品归一化名：<code>{html.escape(w['base'])}</code></div>
-->
</div>'''
    works_data.append({
        "t": m["title"], "base": w["base"], "ns": ns, "pm": bool(w.get("paomian")),
        "bv": m["bvid"],
        "all": " ".join([m["title"]] + [x["title"] for x in (w["mains"] + w["eps"])]).lower(),
        "dur": m["dur"], "tdur": w["total_dur"], "cnt": w["video_count"],
        "mv": w["main_view"], "tv": w["total_view"],
        "st": w["start_ts"], "lt": w["latest_ts"], "yr": w["year"],
        "h": html_block + eps_html,
    })

pm_list = [w for w in fanju if w.get("paomian")]
# 普通视频按用户指令全部归入泡面番
_pm_normal = [v for v in normal if v.get("paomian")]
normal = [v for v in normal if not v.get("paomian")]

def _allex(w):
    out = []
    for x in w["mains"][1:]: out.append((x.get("pubdate", 0), vcard(x, "alt"), x))
    for e in w["eps"]:       out.append((e.get("pubdate", 0), vcard(e, "ep"), e))
    out.sort(key=lambda z: z[0])
    return out

def pm_card(w):
    m = w["main"]
    _al = _allex(w)
    eps = [z[1] for z in _al]
    eps_dur = sum(z[2]["dur"] for z in _al)
    eps_html = (f'<div class="eps"><div class="ot">分P 短视频 · {len(eps)} 个 / 合计 {eps_dur//60} 分钟</div>'
                f'<div class="hscroll">{"".join(eps)}</div></div>') if eps else ""
    t = html.escape(m["title"])
    bs = html.escape(w["base"])
    ns_tag = '<span class="tag warn">无汇总版</span>' if w.get("no_summary") else ""
    # 无汇总版没有「主视频」概念；总时长两者都显示
    dur_item = (f'<span><b>{dur(w["total_dur"])}</b> 总时长</span>' if w.get("no_summary")
                else f'<span><b>{dur(m["dur"])}</b> 时长</span>')
    return ('<div class="work pmbox"><div class="whead">'
            f'<div class="wmain">{vcard(m,"hero")}</div>'
            '<div class="winfo">'
            # 泡面番专属栏位，标题不再重复显示橙色「泡面番」标签（用户要求）。
            # 需要恢复时把下面这行取消注释即可。
            # f'<h3>{t} <span class="tag pm">泡面番</span>{ns_tag}</h3>'
            f'<h3 title="{t}">{t}{ns_tag}</h3>'
            '<div class="wstat">'
            f'{dur_item}'
            f'<span><b>{num(m.get("view",0))}</b> 播放</span>'
            f'<span><b>{m["date"]}</b> 发布</span>'
            '</div>'
            # .wbase 暂时不显示（用户要求）。代码与样式保留，后续可放别的信息。
            # f'<div class="wbase">作品归一化名：<code>{bs}</code></div>'
            f'</div></div>{eps_html}</div>')

def solo_pm_card(v):
    """单个泡面番（无分P的作品）"""
    t = html.escape(v["title"])
    return ('<div class="work pmbox"><div class="whead">'
            f'<div class="wmain">{vcard(v,"hero")}</div>'
            '<div class="winfo">'
            # 同上：泡面番栏位不再显示橙色标签
            # f'<h3>{t} <span class="tag pm">泡面番</span></h3>'
            f'<h3 title="{t}">{t}</h3>'
            '<div class="wstat">'
            f'<span><b>{dur(v["dur"])}</b> 时长</span>'
            f'<span><b>{num(v.get("view",0))}</b> 播放</span>'
            f'<span><b>{v["date"]}</b> 发布</span>'
            '</div>'
            '</div>'
            '</div>'
            '</div>')

pm_html = "".join(pm_card(w) for w in pm_list) + "".join(solo_pm_card(v) for v in _pm_normal)
normal_html = "".join(vcard(v) for v in normal)
# 无汇总版已全部作为独立番剧并入番剧区（带「无汇总版」标签），不再单开栏目，避免重复
orphan_html = "".join(vcard(v, "ep") for v in orphan)
special_html = "".join(vcard(v, "sp") for v in special)

# 注：原series_card / series_html 已随「系列1」删除而移除（series 恒为 0，无对应栏目）。

over60 = sum(1 for g in main_works if g["main"]["dur"] > 3600)
over30 = sum(1 for g in main_works if 1800 < g["main"]["dur"] <= 3600)
kw_only = sum(1 for g in main_works if g["main"]["dur"] <= 3600 and not g["eps"])

# ==== UP 主信息 ====
# 页头展示被收录的 UP 主（圆桌动漫），页尾展示制作者本人
UP_NAME = "圆桌动漫"
UP_URL = "https://space.bilibili.com/654552"
UP_FANS = 6016354
# 制作者（页尾名片）
ME_NAME = "如何获取确币"
ME_URL = "https://space.bilibili.com/3546856434960768?spm_id_from=333.1387.0.0"
ME_AVATAR = "me_avatar.jpg"

# ==== Cloudflare Worker 地址 ====
# 部署后把 Worker 的 https://xxx.workers.dev 地址填到这里，页面就会自动
# 从 Worker 拉取实时粉丝量与播放量汇总；留空则使用构建时的静态数据。
WORKER_API = os.environ.get("WORKER_API", "")
# 全部视频（用于统计总播放量、超1小时数量）
# 注意：videos_full.json 里存的是 duration 字符串（如 "396:28"），不是 dur 秒数
def _dur_sec(t):
    t = str(t or "")
    if ":" not in t:
        try:
            return int(t)
        except ValueError:
            return 0
    r = 0
    for seg in t.split(":"):
        try:
            r = r * 60 + int(float(seg))
        except ValueError:
            return 0
    return r

all_videos = json.load(open(f"{BASE}/videos_full.json", encoding="utf-8"))
TOTAL_VIEW = sum(v.get("view", 0) for v in all_videos)
# 视频数据截取日期（取源数据里最新的发布日，即本次抓取的截止日）
SNAP_DATE = datetime.datetime.fromtimestamp(
    max(v.get("pubdate", 0) for v in all_videos)
).strftime("%Y-%m-%d")
# 各时长区间的视频数（按全部 740 个视频统计）
OVER60_VIDEOS = sum(1 for v in all_videos if _dur_sec(v.get("duration")) > 3600)
OVER30_VIDEOS = sum(1 for v in all_videos if 1800 < _dur_sec(v.get("duration")) <= 3600)
UNDER30_VIDEOS = sum(1 for v in all_videos if _dur_sec(v.get("duration")) <= 1800)

data_json = json.dumps(works_data, ensure_ascii=False)

# 搜索索引：泡面番 + 系列（可被搜索框命中，结果显示在各自区块）
def _flat_items(cat, key, items):
    return {"cat": cat, "key": key,
            "titles": [x["title"] for x in items],
            "text": " ".join([key] + [x["title"] for x in items]).lower()}
search_extra = []
for _w in pm_list:
    search_extra.append(_flat_items("pm", "泡面番", [_w["main"]] + list(_w["eps"])))
for _v in _pm_normal:
    search_extra.append(_flat_items("pm", "泡面番", [_v]))
for _sr in series:
    search_extra.append(_flat_items("series", "系列 " + _sr["key"], _sr["items"]))
for _v in special:
    search_extra.append(_flat_items("special", "特别篇", [_v]))
extra_json = json.dumps(search_extra, ensure_ascii=False)

doc = f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<!-- 标签页图标：圆桌动漫头像（favicon.ico 由 make_favicon.py 生成） -->
<link rel="icon" href="favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="up_avatar.jpg">
<meta name="description" content="圆桌动漫全部番剧作品归档：番剧、泡面番、特别、其它分类，含分P、播放量与充电视频标记。">
<meta name="theme-color" content="#fb7299">
<title>圆桌动漫 · 番剧分类归档</title>
<style>
*{{box-sizing:border-box}}
body{{margin:0;background:#f4f5f7;color:#18191c;line-height:1.5;
font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif}}
header{{background:linear-gradient(135deg,#fb7299 0%,#ff9a6c 100%);color:#fff;padding:30px 26px}}
header h1{{margin:0 0 6px;font-size:25px}}
header p{{margin:0;opacity:.92;font-size:13.5px}}
/* 视频截取日期：跟在"封面已本地化"后面，行内高亮 */
.snapdate{{background:#fff3cd;color:#8a5a00;border:1px solid #ffe08a;
border-radius:6px;padding:1px 9px;font-size:12.5px;font-weight:600}}
.snapdate b{{color:#c47f00;font-size:13.5px;letter-spacing:.5px}}
.wrap{{max-width:1360px;margin:0 auto;padding:20px 22px 60px}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(122px,1fr));gap:11px;margin:18px0 22px}}
/* UP 主名片：仿 B 站 UP 主栏头部 */
.upcard{{display:flex;align-items:center;gap:20px;background:#fff;border:1px solid #e2e4e8;
border-radius:14px;padding:20px 24px;margin:16px 0 4px;box-shadow:0 1px 6px rgba(0,0,0,.04)}}
.upavatar{{flex:0 0 96px;width:96px;height:96px;border-radius:50%;overflow:hidden;
display:block;box-shadow:0 2px 10px rgba(0,0,0,.14);transition:transform .18s}}
.upavatar:hover{{transform:scale(1.05)}}
.upavatar img{{width:100%;height:100%;object-fit:cover;display:block}}
.upinfo{{flex:1 1 auto;min-width:0}}
.upname{{font-size:21px;font-weight:700;color:#18191c;margin-bottom:9px}}
.upname a{{color:#18191c;text-decoration:none}}
.upname a:hover{{color:#fb7299}}
.upmeta{{display:flex;flex-wrap:wrap;gap:26px;color:#61666d;font-size:13.5px}}
.upmeta b{{color:#fb7299;font-size:17px;font-weight:600;margin-right:3px}}
.upstateline{{margin-top:9px;font-size:12px;color:#9499a0}}
@media(max-width:640px){{.upcard{{flex-direction:column;text-align:center;padding:18px}}
.upmeta{{justify-content:center;gap:16px}}}}
/* 页尾制作者名片 */
.credit{{margin:40px 0 26px;padding:22px 24px;background:#fff;border:1px solid #e2e4e8;
border-radius:14px;display:flex;align-items:center;gap:18px;box-shadow:0 1px 6px rgba(0,0,0,.04)}}
.credit .upavatar{{flex:0 0 68px;width:68px;height:68px}}
.credit-t{{font-size:12.5px;color:#9499a0;letter-spacing:2px;margin-bottom:5px}}
.credit-n{{font-size:17px;font-weight:700;color:#18191c}}
.credit-n a{{color:#18191c;text-decoration:none}}
.credit-n a:hover{{color:#fb7299}}
.credit-hint{{margin-left:auto;font-size:12.5px;color:#9499a0}}
@media(max-width:640px){{.credit{{flex-direction:column;text-align:center}}
.credit-hint{{margin-left:0}}}}
.stat{{background:#fff;border-radius:10px;padding:13px 15px;box-shadow:0 1px 4px rgba(0,0,0,.07)}}
.stat b{{display:block;font-size:24px;color:#fb7299;line-height:1.2;font-variant-numeric:tabular-nums}}
.stat span{{font-size:12px;color:#61666d}}
.bar{{position:sticky;top:0;background:#fff;border-radius:11px;padding:12px 15px;margin-bottom:20px;
box-shadow:0 2px 12px rgba(0,0,0,.1);z-index:30;display:flex;gap:14px;align-items:center;flex-wrap:wrap}}
.bar .grp{{display:flex;align-items:center;gap:7px}}
.bar label{{font-size:12.5px;color:#61666d;font-weight:600}}
select,input[type=search]{{font-size:13px;padding:7px 11px;border:1px solid #dfe2e6;border-radius:8px;
background:#fff;color:#18191c;font-family:inherit;outline:none;cursor:pointer}}
select:focus,input:focus{{border-color:#fb7299}}
input[type=search]{{cursor:text;min-width:170px}}
.tabs{{display:flex;gap:6px;margin-left:auto;flex-wrap:wrap}}
.tabs a{{font-size:13px;padding:6px 12px;border-radius:7px;background:#f2f3f5;color:#18191c;
text-decoration:none;font-weight:600}}
.tabs a:hover{{background:#e8eaed}}
.tabs a.on{{background:#fb7299;color:#fff}}
.cnt{{font-size:12.5px;color:#9499a0;margin-left:auto}}
.hits{{background:#fff;border-radius:11px;padding:13px 16px;margin-bottom:14px;box-shadow:0 1px 5px rgba(0,0,0,.07);font-size:13px}}
.hits .hh{{font-weight:700;margin-bottom:8px;color:#18191c}}
.hits .hrow{{display:flex;gap:8px;align-items:baseline;margin:5px 0;flex-wrap:wrap}}
.hits .hcat{{background:#f2f3f5;border-radius:5px;padding:1px 8px;font-size:11.5px;font-weight:600;color:#61666d;flex-shrink:0}}
.hits .hitem{{color:#18191c}}
.hits .hitem a{{color:#fb7299;text-decoration:none;margin-right:10px;display:inline-block;margin-bottom:3px}}
.hits .hitem a:hover{{text-decoration:underline}}
.hits .hmore{{color:#9499a0;font-size:12px}}
h2 .cnt2{{font-size:13px;color:#9499a0;font-weight:400}}
.nohit{{padding:14px 2px}}
h2{{font-size:19px;margin:32px 0 6px;padding-left:11px;border-left:4px solid #fb7299}}
.note{{font-size:13px;color:#61666d;margin:0 0 15px;padding-left:15px}}
.work{{background:#fff;border-radius:12px;padding:17px;margin-bottom:15px;box-shadow:0 1px 5px rgba(0,0,0,.07)}}
.work.warnbox{{background:#fafbfc;border:1px dashed #d8dbe0;box-shadow:none}}
.whead{{display:flex;gap:18px;align-items:stretch}}
.wmain{{width:290px;flex:0 0 290px;min-width:0}}
.winfo{{flex:1 1 auto;min-width:0}}
.winfo h3{{margin:2px 0 10px;font-size:17px;line-height:1.45;word-break:break-word;overflow-wrap:anywhere;
max-height:5.85em;overflow:hidden;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical}}
.wstat{{display:flex;flex-wrap:nowrap;gap:7px;margin-bottom:10px;height:26px;overflow:hidden}}
.wstat span{{white-space:nowrap;flex:0 0 auto}}
.wstat span{{background:#f5f6f8;border-radius:7px;padding:4px 10px;font-size:12px;color:#61666d}}
.wstat b{{color:#18191c;font-size:13.5px;margin-right:3px;font-variant-numeric:tabular-nums}}
.wbase{{font-size:12px;color:#9499a0;height:20px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}}
.wbase code{{background:#f2f3f5;padding:1px 6px;border-radius:4px;font-size:11.5px}}
.tag{{display:inline-block;background:#ff6b35;color:#fff;border-radius:5px;padding:1px 8px;
font-size:12px;vertical-align:middle}}
/* 充电视频标志：醒目红底白字，挂在封面右上角与标题前 */
.vcard.charged .payflag,.work.charged .payflag{{display:block}}
.payflag{{display:none;position:absolute;left:0;top:0;background:#e02020;color:#fff;
font-size:11.5px;font-weight:700;padding:2px 8px;border-radius:0 0 7px 0;
z-index:3;letter-spacing:.5px;box-shadow:0 1px 4px rgba(0,0,0,.3)}}
.work.charged{{border-color:#e02020!important}}
.tag.warn{{background:#8a8f98;margin-left:4px}}
.tag.charge{{background:#e02020;margin-right:5px}}
.vgrid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(156px,1fr));gap:11px}}
.vgrid.sm{{grid-template-columns:repeat(auto-fill,minmax(138px,1fr))}}
/* 分P 横向滚动条：避免长列表把页面撑得过高 */
.hscroll{{display:flex;gap:10px;overflow-x:auto;overflow-y:hidden;height:196px;
padding:4px 2px 12px;scroll-snap-type:x proximity;
width:100%;max-width:100%;min-width:0;box-sizing:border-box}}
/* 父级必须允许收缩，否则滚动容器会被内容撑开 */
.eps,.winfo,.whead,.work{{min-width:0}}
.winfo{{overflow:hidden}}
.hscroll::-webkit-scrollbar{{height:9px}}
.hscroll::-webkit-scrollbar-track{{background:#f2f3f5;border-radius:5px}}
.hscroll::-webkit-scrollbar-thumb{{background:#c9ccd2;border-radius:5px}}
.hscroll::-webkit-scrollbar-thumb:hover{{background:#a8adb4}}
.eps .hscroll .vcard, .sbox .hscroll .vcard, .vgrid .vcard{{flex:0 0 152px;width:152px;min-width:152px;max-width:152px;scroll-snap-align:start}}
/* 固定卡片高度：内部信息超出时裁剪，避免把卡片往下挤 */
.vcard{{height:186px;display:flex;flex-direction:column}}
.vcard .vm{{flex:1 1 auto;min-height:0;overflow:hidden}}
/* 主视频卡：高度锁定，与右侧信息区顶部对齐，行高不会被标题行数挤动 */
.wmain .vcard{{height:186px;width:100%}}

.vcard{{position:relative;display:block;min-width:0;background:#fafbfc;border:1px solid #eef0f2;border-radius:9px;
overflow:hidden;text-decoration:none;color:inherit;transition:.16s}}
.vcard:hover{{border-color:#fb7299;box-shadow:0 4px 14px rgba(251,114,153,.22);transform:translateY(-2px)}}
.vcard img,.vcard .nocov{{width:100%;aspect-ratio:16/10;object-fit:cover;display:block;background:#e9ebee}}
.nocov{{display:flex;align-items:center;justify-content:center;color:#a8adb4;font-size:12px}}
.dur{{position:absolute;right:6px;top:6px;background:rgba(0,0,0,.8);color:#fff;font-size:11.5px;
padding:1.5px 6px;border-radius:4px;font-variant-numeric:tabular-nums}}
.vcard.hero .dur{{font-size:13px;padding:3px 8px;background:rgba(0,0,0,.85)}}
.vcard.ep .dur{{background:#4a7fd4}}
.vcard.alt .dur{{background:#7d5bbf}}
.vcard.sp .dur{{background:#2f9e8f}}
.work.sbox{{border:2px solid #4a7fd4;box-shadow:0 2px 10px rgba(74,127,212,.13)}}
.work.pmbox{{border:2px solid #ff6b35;box-shadow:0 2px 10px rgba(255,107,53,.13)}}
/* 搜索命中高亮：黄色描边 + 淡底，一眼看出命中了哪几张 */
.vcard.hit,.work.hit{{outline:3px solid #ffc53d;outline-offset:1px;
background:#fff8e1!important;border-radius:10px}}
.vcard.hit:hover,.work.hit:hover{{outline-color:#ff9f1a}}
.vm{{padding:7px 9px 9px;min-width:0}}
.vt{{font-size:12.5px;line-height:1.4;font-weight:600;word-break:break-word;overflow-wrap:anywhere;
display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;height:2.8em}}
.vs{{font-size:11px;color:#9499a0;margin-top:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.others,.eps{{margin-top:15px;padding-top:13px;border-top:1px dashed #e2e4e8}}
.ot{{font-size:12.5px;color:#61666d;font-weight:600;margin-bottom:9px}}
.pmcard{{display:block;background:#fff;border-radius:10px;overflow:hidden;text-decoration:none;color:inherit;
box-shadow:0 1px 5px rgba(0,0,0,.08);border:2px solid #ff6b35}}
.pmcard:hover{{transform:translateY(-2px);box-shadow:0 6px 18px rgba(255,107,53,.25)}}
.pmcard img{{width:100%;aspect-ratio:16/10;object-fit:cover;display:block}}
.pmt{{padding:8px 10px;font-size:12.5px;font-weight:600;line-height:1.4;height:2.8em;
display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}
.pms{{padding:0 10px 9px;font-size:11px;color:#9499a0}}
.hide{{display:none}}
/* ==== 兜底：卡片高度锁定（须放在最后以覆盖上面的 display:block） ==== */
.vcard{{display:flex;flex-direction:column;height:186px}}
.vcard .vm{{flex:1 1 auto;min-height:0;overflow:hidden}}
.wmain{{width:290px;flex:0 0 290px;min-width:0}}
.wmain .vcard{{height:186px;width:100%}}
.hscroll .vcard,.vgrid .vcard{{flex:0 0 152px;width:152px;min-width:152px;max-width:152px;height:186px}}
/* 信息区固定为与主视频卡等高，标题行数变化不再撑动整行容器 */
/* min-height 而非固定 height：窄屏下文字换行增多时可自然撑高，不会溢出留白 */
.winfo{{min-height:186px;display:flex;flex-direction:column;justify-content:flex-start}}
.winfo h3{{flex:0 1 auto;margin-bottom:8px}}
.wstat{{flex:0 0 26px;margin-bottom:6px}}
/* .wbase 当前不渲染，固定高度一并停用，避免信息栏底部留空。
   需要恢复时把下面这行取消注释即可。
.wbase{{flex:0 0 20px}} */
/* 关键：主视频+信息区一行，分P 区必须换行独占整行，否则会挤在右侧留出左侧空白 */
.whead{{height:auto;display:flex;flex-wrap:wrap;align-items:flex-start;gap:0 18px}}
.whead>.wmain{{flex:0 0 290px;width:290px}}
.whead>.winfo{{flex:1 1 0;min-width:0;min-height:186px}}
.whead>.eps{{flex:0 0 100%;width:100%;margin-top:15px;padding-top:13px;border-top:1px dashed #e2e4e8}}
/* 泡面番专区：一行 3 个（用户要求，否则单个太宽、向下滚动次数过多） */
#pmList{{display:grid;grid-template-columns:repeat(3,1fr);gap:13px;align-items:start}}
#pmList>.work{{margin-bottom:0}}
/* 网格内的泡面番：主视频在上、信息在下，宽度收窄后不再横排 */
#pmList .whead{{display:block;height:auto}}
#pmList .wmain{{width:100%;margin-bottom:11px}}
#pmList .wmain .vcard{{height:auto;width:100%}}
#pmList .winfo{{width:100%;height:auto!important;min-height:0!important}}
/* 标题固定 1 行：无论长短，卡片高度完全一致（超出部分省略号截断，
   鼠标悬停可通过 title 属性看到完整标题） */
#pmList .winfo h3{{font-size:13.5px;line-height:1.4;margin:0 0 8px;
height:1.4em;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
#pmList .wstat{{height:auto;flex-wrap:wrap;overflow:visible;margin-bottom:8px}}
/* #pmList .wbase{{height:auto}} —— 随.wbase 一并停用 */
#pmList .eps{{margin-top:13px;padding-top:12px}}
@media(max-width:1100px){{#pmList{{grid-template-columns:repeat(2,1fr)}}}}
@media(max-width:720px){{#pmList{{grid-template-columns:1fr}}}}
/* 平板：主视频与信息仍横排，但主视频略窄 */
@media(max-width:820px){{
.whead{{flex-direction:column}}
.wmain,.whead>.winfo{{width:100%;flex:1 1 auto}}
.bar{{position:static}}
}}
/* 窄屏适配：主视频改全宽，统计项允许换行，避免窄屏时文字被裁、空出一片 */
@media(max-width:640px){{
.wrap{{padding:0 10px}}
header{{padding:16px 12px}}
.wwork,.work{{padding:12px}}
.whead{{display:block}}
.wmain{{width:100%;flex:none;margin-bottom:11px}}
.wmain .vcard{{height:auto;width:100%}}
.winfo{{width:100%;height:auto!important;min-height:0!important}}
.winfo h3{{font-size:15.5px;max-height:none;-webkit-line-clamp:2}}
/* 关键：统计项换行显示，不再 nowrap + 裁切。
   用 !important 覆盖前面的 height:26px / nowrap（同等优先级下后写的胜，
   但前面那条是单行简写，稳妥起见强制覆盖） */
.wstat{{flex-wrap:wrap!important;height:auto!important;overflow:visible!important;gap:6px}}
.wstat span{{flex:0 0 auto;font-size:11.5px;padding:3px 8px}}
.winfo{{min-height:0!important}}
.whead>.eps{{margin-top:12px;padding-top:11px}}
.hscroll{{gap:9px}}
.hscroll .vcard,.vgrid .vcard{{flex:0 0 132px;width:132px;min-width:132px;max-width:132px;height:158px}}
.vgrid{{grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:9px}}
.stats{{grid-template-columns:repeat(auto-fit,minmax(104px,1fr));gap:8px;margin:14px 0 18px}}
.stat{{padding:11px 8px}}
.stat b{{font-size:18px}}
.stat span{{font-size:11.5px}}
h2{{font-size:17px;margin:26px 0 5px}}
.bar{{position:static;padding:11px 12px}}
.grp{{margin:7px 0}}
select,input{{width:100%}}
}}
/* 超窄屏（如 iPhone SE 竖屏 375px 以下） */
@media(max-width:400px){{
.hscroll .vcard,.vgrid .vcard{{flex:0 0 124px;width:124px;min-width:124px;max-width:124px;height:150px}}
.vgrid{{grid-template-columns:repeat(2,1fr)}}
.upmeta{{gap:12px;font-size:12.5px}}
.upmeta b{{font-size:15px}}
}}
</style></head><body>
<header>
<h1>圆桌动漫 · 番剧分类归档</h1>
<p>共 {len(all_videos)} 个视频 ｜ 封面已本地化 ｜ <span class="snapdate">视频截取日期：<b>{SNAP_DATE}</b></span></p>
</header>
<div class="wrap">
<div class="upcard">
  <a class="upavatar" href="{UP_URL}" target="_blank" rel="noopener">
    <img src="up_avatar.jpg" alt="{UP_NAME} 的头像">
  </a>
  <div class="upinfo">
    <div class="upname"><a href="{UP_URL}" target="_blank" rel="noopener">{UP_NAME}</a></div>
    <div class="upmeta">
      <span><b data-live="follower">{num(UP_FANS)}</b> 粉丝</span>
      <span><b data-live="totalview">{num(TOTAL_VIEW)}</b> 总播放</span>
      <span><b>{len(all_videos)}</b> 收录视频</span>
    </div>
    <div class="upstateline" data-live="status">静态数据</div>
  </div>
</div>
<div class="stats">
<div class="stat"><b>{len(main_works)}</b><span>番剧作品</span></div>
<div class="stat"><b>{len(pm_list)+len(_pm_normal)}</b><span>泡面番</span></div>
<div class="stat"><b>{len(orphan)}</b><span>特别</span></div>
<div class="stat"><b>{len(special)}</b><span>其它</span></div>
<div class="stat"><b>{OVER60_VIDEOS}</b><span>超1小时</span></div>
<div class="stat"><b>{OVER30_VIDEOS}</b><span>30分~1小时</span></div>
<div class="stat"><b>{UNDER30_VIDEOS}</b><span>30分钟以内</span></div>
<div class="stat"><b>{sum(len(w['eps']) for w in fanju)}</b><span>已归组分P</span></div>
</div>

<div id="hits" class="hits hide"></div>
<div class="bar">
<div class="grp"><label>排序</label>
<select id="sort">
<option value="st-desc">发布时间：最新 → 最早（默认）</option>
<option value="st-asc">发布时间：最早 → 最新</option>
<option value="dur-desc">主视频时长：长 → 短</option>
<option value="dur-asc">主视频时长：短 → 长</option>
<option value="tdur-desc">总时长：长 → 短</option>
<option value="tdur-asc">总时长：短 → 长</option>
<option value="mv-desc">主视频播放量：高 → 低</option>
<option value="tv-desc">总播放量：高 → 低</option>
<option value="cnt-desc">视频数量：多 → 少</option>
<option value="cnt-asc">视频数量：少 → 多</option>
</select></div>
<div class="grp"><label>筛选</label>
<select id="filt">
<option value="all">全部作品</option>
<option value="pm">仅泡面番</option>
<option value="nosum">仅无汇总版</option>
<option value="has">仅超1小时</option>
<option value="f1">仅30分钟以上</option>
<option value="m1">仅多分P作品</option>
</select></div>
<div class="grp"><input type="search" id="q" placeholder="搜索标题 / 作品名…"></div>
<span class="cnt" id="cnt"></span>
<div class="tabs">
<a href="#fanju" class="on">番剧</a><a href="#paomian">泡面番</a>
<a href="#birthday">特别</a><a href="#other">其它</a>
</div>
</div>

<h2 id="fanju">番剧作品<span class="cnt2">（{len(main_works)} 部）</span></h2>
<p class="note">默认按发布时间从近到远排列。排序与筛选对下方所有栏目同时生效。</p>
<div id="list"></div>
<div id="empty" class="note hide" style="padding:30px;text-align:center">没有符合条件的作品</div>

<h2 id="paomian">泡面番专区<span class="cnt2">（{len(pm_list)+len(_pm_normal)} 个）</span></h2>
<p class="note">共 {len(pm_list)+len(_pm_normal)} 部。</p>
<div id="pmList">{pm_html}</div>

<h2 id="birthday">特别<span class="cnt2">（{len(orphan)} 个）</span></h2>
<p class="note">生日、拜年特辑</p>
<div class="vgrid">{orphan_html}</div>

<h2 id="other">其它<span class="cnt2">（{len(special)} 个）</span></h2>
<div class="vgrid">{special_html}</div>

<div class="credit">
  <a class="upavatar" href="{ME_URL}" target="_blank" rel="noopener">
    <img src="{ME_AVATAR}" alt="{ME_NAME} 的头像">
  </a>
  <div>
    <div class="credit-t">制作者</div>
    <div class="credit-n"><a href="{ME_URL}" target="_blank" rel="noopener">{ME_NAME}</a></div>
  </div>
  <div class="credit-hint">点击头像或名字前往主页 →</div>
</div>

</div>
<script>
const DATA = {data_json};
const EXTRA = {extra_json};
const listEl = document.getElementById('list'), emptyEl = document.getElementById('empty'),
      cntEl = document.getElementById('cnt');
function fmtDur(s){{return s>=3600? Math.floor(s/3600)+':'+String(Math.floor(s%3600/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0') : Math.floor(s/60)+':'+String(s%60).padStart(2,'0');}}
function fmtDate(t){{const d=new Date(t*1000);return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');}}
function fmtNum(n){{return n>=10000? (n/10000).toFixed(1)+'万' : String(n);}}
function d2(n){{return String(n).padStart(2,'0');}}

// 顶部「共 N 部作品」跟随当前栏目变化：
// 番剧=作品数，泡面番/特别/其它=视频数（这些栏目一个卡片就是一个视频）
const SEC_COUNT = {{
  fanju:    {{label:'部作品', unit:'部'}},
  paomian:  {{label:'个视频', unit:'个'}},
  birthday: {{label:'个视频', unit:'个'}},
  other:    {{label:'个视频', unit:'个'}},
}};
function updateSecCount(sec, n){{
  const c = SEC_COUNT[sec];
  if(!c || !cntEl) return;
  cntEl.textContent = '共 ' + n + ' ' + c.label;
}}
// 统计某个栏目当前可见的条目数
function countVisible(sec){{
  const h2 = document.getElementById(sec);
  if(!h2) return 0;
  const scope = [];
  let n = h2.nextElementSibling;
  while(n && n.tagName !== 'H2') {{ scope.push(n); n = n.nextElementSibling; }}
  let cnt = 0;
  scope.forEach(x => {{
    if(x.classList.contains('work') || x.classList.contains('sbox')) {{ if(x.style.display!=='none') cnt++; return; }}
    if(x.classList.contains('vgrid')) {{ cnt += [...x.querySelectorAll('.vcard')].filter(c=>c.style.display!=='none').length; return; }}
    const inner = [...x.querySelectorAll(':scope > .work, :scope > .sbox')];
    if(inner.length) {{ cnt += inner.filter(c=>c.style.display!=='none').length; return; }}
    if(x.querySelector('.vcard')) {{ if(x.style.display!=='none') cnt++; }}
  }});
  return cnt;
}}
// 滚动到哪个栏目，顶部就显示那个栏目的数量
function syncSecCount(){{
  const heads = document.querySelectorAll('h2[id]');
  if(!heads.length) return;
  let cur = heads[0].id;
  const probeY = window.innerHeight * 0.3;
  heads.forEach(h => {{ if(h.getBoundingClientRect().top <= probeY) cur = h.id; }});
  if(window.pageYOffset + window.innerHeight >= document.documentElement.scrollHeight - 8)
    cur = heads[heads.length-1].id;
  // 一律按实际可见数重算：番剧区被搜索/筛选隐藏后，
  // render() 写入的数字会与可见数不一致
  if(cur === 'fanju') {{
    const vis = listEl ? [...listEl.querySelectorAll('.work')]
      .filter(c => c.style.display !== 'none').length : 0;
    updateSecCount('fanju', vis);
    return;
  }}
  updateSecCount(cur, countVisible(cur));
}}

function render(){{
  const mode = document.getElementById('sort').value;
  const [key, dir] = mode.split('-');
  const filt = document.getElementById('filt').value;
  const q = document.getElementById('q').value.trim().toLowerCase();
  let arr = DATA.slice();
  arr = arr.filter(w=>{{
    if(filt==='pm' && !w.pm) return false;
    if(filt==='nosum' && !w.ns) return false;
    if(filt==='has' && w.dur<=3600) return false;
    // 无汇总版没有「主视频」概念：按主视频时长排序/筛选时一律排除；
    // 但按总时长排序时应当纳入（总时长是有意义的）
    if(key==='dur' && w.ns) return false;
    if((filt==='has'||filt==='f1') && w.ns) return false;
    if(filt==='f1' && w.dur<=1800) return false;
    if(filt==='m1' && w.cnt<2) return false;
    if(q && !(w.all.includes(q) || w.base.toLowerCase().includes(q))) return false;
    return true;
  }});
  const sgn = dir==='asc' ? 1 : -1;
  arr.sort((a,b)=>{{
    let x=a[key], y=b[key];
    if(x===y) return a.t.localeCompare(b.t,'zh');
    return x>y ? sgn : -sgn;
  }});
  cntEl.textContent = '共 ' + arr.length + ' 部作品';
  updateSecCount('fanju', arr.length);
  listEl.innerHTML = arr.map(w=>
    '<div class="work'+(w.ns?' warnbox':'')+'"><div class="whead">'+w.h+'</div></div>').join('');
  emptyEl.classList.toggle('hide', arr.length>0);
  sortExtras(key, dir);
  renderHits(q);
  applySearchHighlight(q);
}}

// 泡面番 / 特别 / 其它 三个栏目同样参与排序。
// 这三栏每张卡片就是一个视频，故「主视频时长」与「总时长」取同一个值。
function sortExtras(key, dir){{
  const sgn = dir==='asc' ? 1 : -1;
  const attr = {{dur:'dur', tdur:'tdur', mv:'view', tv:'view', st:'pub'}}[key];
  if(!attr) return;
  // 「视频数量」对这三个栏目无意义（每栏都是单个视频），跳过避免无序抖动
  if(key==='cnt') return;
  // 泡面番专区：.work.pmbox 整体按其主视频排序
  const pmWrap = document.getElementById('pmList');
  if(pmWrap){{
    const boxes = [...pmWrap.querySelectorAll(':scope > .work')];
    boxes.sort((a,b)=>{{
      const av = +((a.querySelector('.vcard')||{{}}).dataset[attr] || 0);
      const bv = +((b.querySelector('.vcard')||{{}}).dataset[attr] || 0);
      return av===bv ? 0 : (av>bv ? sgn : -sgn);
    }});
    boxes.forEach(b => pmWrap.appendChild(b));
  }}
  // 特别 / 其它：网格内卡片重排
  ['birthday','other'].forEach(id=>{{
    const h2 = document.getElementById(id);
    if(!h2) return;
    let n = h2.nextElementSibling;
    while(n && n.tagName !== 'H2'){{
      if(n.classList.contains('vgrid')){{
        const cards = [...n.querySelectorAll('.vcard')];
        cards.sort((a,b)=>{{
          const av = +a.dataset[attr] || 0, bv2 = +b.dataset[attr] || 0;
          return av===bv2 ? 0 : (av>bv2 ? sgn : -sgn);
        }});
        cards.forEach(c => n.appendChild(c));
      }}
      n = n.nextElementSibling;
    }}
  }});
}}

// 搜索汇总面板：跨全部区块统计命中
function renderHits(q){{
  const box = document.getElementById('hits');
  if(!q) {{ box.classList.add('hide'); box.innerHTML = ''; return; }}
  const main = DATA.filter(w => w.all.includes(q) || w.base.toLowerCase().includes(q));
  const groups = {{}};
  EXTRA.forEach(g => {{
    const hits = g.titles.filter(t => t.toLowerCase().includes(q));
    if(hits.length) groups[g.cat] = (groups[g.cat] || []).concat(hits);
  }});
  const names = {{pm:'泡面番', series:'系列', special:'其它'}};
  const other = Object.entries(groups);
  let html = '<div class="hh">搜索「' + q + '」的结果：番剧 ' + main.length + ' 部';
  if(other.length) html += '，其它栏目 ' + other.reduce((a,[,v])=>a+v.length,0) + ' 个（已在下方对应栏目内筛选显示）';
  html += '</div>';
  if(main.length) {{
    html += '<div class="hrow"><span class="hcat">番剧</span><span class="hitem">';
    html += main.slice(0,20).map(w=>'<a href="https://www.bilibili.com/video/'+w.bv+'" target="_blank">'+w.t.slice(0,26)+'</a>').join('');
    if(main.length>20) html += '<span class="hmore">…另有 '+(main.length-20)+' 部</span>';
    html += '</span></div>';
  }}
  other.forEach(([cat, items]) => {{
    html += '<div class="hrow"><span class="hcat">'+names[cat]+'</span><span class="hitem">';
    html += items.slice(0,20).map(t=>'<a href="#'+cat+'">'+t.slice(0,30)+'</a>').join('');
    if(items.length>20) html += '<span class="hmore">…另有 '+(items.length-20)+' 个</span>';
    html += '</span></div>';
  }});
  box.innerHTML = html;
  box.classList.remove('hide');
}}

// 搜索时，各栏目只显示命中的条目（与番剧区行为一致）；清空搜索则全部还原
function applySearchHighlight(q){{
  // h2 与其内容是兄弟节点，故从 h2 起取「到下一个 h2 前」的所有兄弟元素作为该栏目范围
  const secs = ['paomian','birthday','other'];
  secs.forEach(id=>{{
    const h2 = document.getElementById(id);
    if(!h2) return;
    const scope = [];
    let n = h2.nextElementSibling;
    while(n && n.tagName !== 'H2') {{ scope.push(n); n = n.nextElementSibling; }}
    const sec = {{ querySelectorAll: sel => scope.flatMap(x => [...x.querySelectorAll(sel)]) }};
    // 顶层卡片 = scope 里的 .work/.sbox，以及容器内的 .vcard
    // 注意：泡面番区所有卡片包在 #pmList 里，必须下钻到卡片本身，
    // 否则会把整个 #pmList 当成 1 张卡片，命中任一关键词就全量显示。
    const topCards = [];
    scope.forEach(x => {{
      if(x.classList.contains('work') || x.classList.contains('sbox')) {{ topCards.push(x); return; }}
      if(x.classList.contains('vgrid')) {{ x.querySelectorAll('.vcard').forEach(c => topCards.push(c)); return; }}
      // 容器内直接挂着多张卡片（如 #pmList）→ 逐张收集
      const inner = [...x.querySelectorAll(':scope > .work, :scope > .sbox')];
      if(inner.length) {{ inner.forEach(c => topCards.push(c)); return; }}
      if(x.querySelector('.vcard')) {{ topCards.push(x); return; }}
    }});
    topCards.forEach(w=>{{
      if(!q) {{ w.style.display=''; w.classList.remove('hit'); return; }}
      const hit = (w.innerText||'').toLowerCase().includes(q);
      w.style.display = hit ? '' : 'none';
      // 命中项加高亮底色，方便一眼看出是哪一个
      w.classList.toggle('hit', hit);
    }});
    // 网格容器：内部全隐藏时一并隐藏，避免留下空网格
    sec.querySelectorAll('.vgrid').forEach(g=>{{
      const anyVisible = [...g.children].some(ch=>ch.style.display !== 'none');
      g.style.display = (q && !anyVisible) ? 'none' : '';
    }});
    // 栏目内的说明文字在过滤时隐藏
    scope.forEach(x=>{{
      if(x.tagName==='P' && x.classList.contains('note')) x.style.display = q ? 'none' : '';
    }});
    // 区块标题的计数
    if(h2){{
      const cntEl = h2.querySelector('.cnt2');
      if(!cntEl) return;
      if(!h2.dataset.orig) h2.dataset.orig = cntEl.textContent;
      if(q){{
        const n = topCards.filter(c=>c.style.display!=='none').length;
        cntEl.textContent = '（命中 ' + n + ' 个）';
      }} else {{
        cntEl.textContent = h2.dataset.orig;
      }}
    }}
  }});
  // 无匹配时给出提示
  ['paomian','other','birthday'].forEach(id=>{{
    const h2 = document.getElementById(id);
    if(!h2) return;
    const cards = [];
    let n = h2.nextElementSibling;
    while(n && n.tagName !== 'H2'){{
      if(n.classList.contains('work') || n.classList.contains('sbox')) cards.push(n);
      else if(n.classList.contains('vcard')) cards.push(n);
      else n.querySelectorAll('.vcard').forEach(c=>cards.push(c));
      n = n.nextElementSibling;
    }}
    const any = cards.some(c => c.style.display !== 'none');
    let tip = document.querySelector('#'+id+' ~ .nohit');
    if(q && !any){{
      if(!tip){{
        tip = document.createElement('p');
        tip.className = 'note nohit';
        h2.parentNode.insertBefore(tip, h2.nextSibling);
      }}
      tip.textContent = '「' + q + '」在本栏无匹配';
      tip.style.display = '';
    }} else if(tip) tip.style.display = 'none';
  }});
}}
['sort','filt','q'].forEach(id=>{{
  const el=document.getElementById(id);
  if(!el) return;
  el.addEventListener(id==='q'?'input':'change', render);
}});
render();

// 导航高亮 + URL 后缀跟随滚动
var _lastHash = '';
function syncNav(){{
  var links = document.querySelectorAll('.tabs a');
  var heads = document.querySelectorAll('h2[id]');
  if(!links.length || !heads.length) return;
  var cur = heads[0].id;
  var probeY = window.innerHeight * 0.3;
  for(var i=0;i<heads.length;i++){{
    if(heads[i].getBoundingClientRect().top <= probeY) cur = heads[i].id;
  }}
  if(window.pageYOffset + window.innerHeight >= document.documentElement.scrollHeight - 8)
    cur = heads[heads.length-1].id;
  for(var k=0;k<links.length;k++)
    links[k].className = (links[k].getAttribute('href') === '#' + cur) ? 'on' : '';
  // 同步地址栏后缀（replaceState 不产生历史记录，不会污染后退栈）
  if(cur !== _lastHash){{
    _lastHash = cur;
    try{{ history.replaceState(null, '', '#' + cur); }}catch(e){{}}
  }}
}}
// 点击时先点亮目标按钮，避免平滑滚动期间高亮滞后
document.querySelectorAll('.tabs a').forEach(a=>{{
  a.addEventListener('click', function(e){{
    e.preventDefault();
    var id = a.getAttribute('href').slice(1);
    document.querySelectorAll('.tabs a').forEach(x=>x.className='');
    a.className = 'on';
    _lastHash = id;                       // 防止滚动监听立刻覆盖
    try{{ history.replaceState(null, '', '#' + id); }}catch(err){{}}
    var t = document.getElementById(id);
    if(t) window.scrollTo({{top: t.offsetTop - 64, behavior: 'smooth'}});
    setTimeout(syncNav, 400);
    setTimeout(syncNav, 900);
  }});
}});
window.addEventListener('scroll', syncNav, {{passive:true}});
window.addEventListener('scroll', syncSecCount, {{passive:true}});
window.addEventListener('resize', syncNav);
window.addEventListener('load', syncNav);
setTimeout(syncNav, 200);
setTimeout(syncNav, 800);
syncNav();
syncSecCount();

// ===== 实时数据：部署到 Cloudflare 后从 Worker 拉取粉丝量与播放量汇总 =====
// 把 WORKER_API 改成你的 Worker 地址（如 https://xxx.workers.dev）即可自动生效；
// 留空则页面使用构建时的静态数据，功能不受影响。
const WORKER_API = "{WORKER_API}";
function fmtNum(n){{
  if(typeof n !== 'number' || !isFinite(n)) return n;
  if(n >= 100000000) return (n/100000000).toFixed(2).replace(/\\.?0+$/,'') + '亿';
  if(n >= 10000) return (n/10000).toFixed(1).replace(/\\.0$/,'') + '万';
  return n.toLocaleString('zh-CN');
}}
async function loadLive(){{
  if(!WORKER_API) return;
  try{{
    const r = await fetch(WORKER_API + '/api/stats', {{cache:'no-store'}});
    if(!r.ok) throw new Error('HTTP ' + r.status);
    const d = await r.json();
    // 粉丝量
    const fanEl = document.querySelector('[data-live="follower"]');
    if(fanEl && typeof d.follower === 'number') fanEl.textContent = fmtNum(d.follower);
    // 总播放量
    const tvEl = document.querySelector('[data-live="totalview"]');
    if(tvEl && typeof d.totalView === 'number') tvEl.textContent = fmtNum(d.totalView);
    // 更新每部作品的播放量（按作品 key 匹配）
    const map = {{}};
    (d.works || []).forEach(w => map[w.key] = w);
    document.querySelectorAll('[data-work]').forEach(el => {{
      const it = map[el.getAttribute('data-work')];
      if(!it) return;
      const b = el.querySelector('b');
      if(b) b.textContent = fmtNum(it.view);
    }});
    // 更新时间
    const tsEl = document.querySelector('[data-live="updated"]');
    if(tsEl && d.updatedAt){{
      const t = new Date(d.updatedAt);
      tsEl.textContent = t.getFullYear() + '-' +
        String(t.getMonth()+1).padStart(2,'0') + '-' +
        String(t.getDate()).padStart(2,'0');
    }}
    const st = document.querySelector('[data-live="status"]');
    if(st) st.textContent = '实时数据 · ' + fmtNum(d.totalVideos) + ' 个视频';
  }}catch(e){{
    const st = document.querySelector('[data-live="status"]');
    if(st) st.textContent = '静态数据（未配置或接口不可用）';
  }}
}}
if(WORKER_API) loadLive();
</script>
</body></html>'''

open(f"{BASE}/fanju_index.html", "w", encoding="utf-8").write(doc)
print("OK 番剧", len(fanju), "| 泡面番", len(pm_list), "| 分P", sum(len(w['eps']) for w in fanju),
      "| 无汇总", sum(1 for w in main_works if w.get("no_summary")), "| 普通", len(normal))
print("默认排序：发布时间最新→最早")
print("最新:", fanju[-1]['main']['date'], fanju[-1]['main']['title'][:30])
print("最早:", fanju[0]['main']['date'], fanju[0]['main']['title'][:30])
