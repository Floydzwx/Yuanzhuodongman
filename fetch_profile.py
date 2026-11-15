"""自动获取圆桌动漫(mid=654552)的 UP 主个人数据，输出 JSON 供页面使用。

设计目标：**免配置、免登录也能跑**。
  - 粉丝数 / 关注数 / 名称 / 头像 / 签名：B 站匿名接口即可拿到
    （x/relation/stat + x/web-interface/card，只要带正常 UA 和 Referer）
  - UP 主页累计播放 / 获赞：x/space/upstat 需要登录态，本机有浏览器
    登录 cookie 时自动补；没有（如 GitHub Actions）则沿用上次的值

用法：
  python fetch_profile.py                      # 写 up_profile.json
  python fetch_profile.py --out site/profile.json   # 直接写进静态站
"""
import argparse
import datetime
import json
import os
import sys
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))  # 跨平台：脚本所在目录
MID = 654552
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
REF = f"https://space.bilibili.com/{MID}/"


def get(url, cookie=""):
    h = {"User-Agent": UA, "Referer": REF,
         "Accept": "application/json, text/plain, */*"}
    if cookie:
        h["Cookie"] = cookie
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def try_cookie():
    """本机有已登录的 Edge profile 时用它，失败返回空串（不影响匿名数据）。"""
    try:
        sys.path.insert(0, BASE)
        from bili_session import cookie_header
        return cookie_header()
    except Exception:
        return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=BASE + "/up_profile.json")
    args = ap.parse_args()

    prev = {}
    if os.path.exists(args.out):
        try:
            prev = json.load(open(args.out, encoding="utf-8"))
        except Exception:
            pass

    out = dict(prev)
    out["mid"] = MID
    out["source"] = "bilibili-api"

    # 1) 粉丝 / 关注（匿名可用）
    try:
        d = get(f"https://api.bilibili.com/x/relation/stat?vmid={MID}")
        if d.get("code") == 0 and d.get("data"):
            out["follower"] = d["data"].get("follower", out.get("follower"))
            out["following"] = d["data"].get("following", out.get("following"))
    except Exception as e:
        print("粉丝数获取失败（沿用上次值）:", e, file=sys.stderr)

    # 2) 名称 / 头像 / 签名（匿名可用）
    try:
        d = get(f"https://api.bilibili.com/x/web-interface/card?mid={MID}&photo=false")
        c = ((d.get("data") or {}).get("card") or {})
        if c:
            out["name"] = c.get("name") or out.get("name")
            out["face"] = c.get("face") or out.get("face")
            out["sign"] = c.get("sign") or out.get("sign")
            out["level"] = c.get("level") or out.get("level")
    except Exception as e:
        print("名片获取失败（沿用上次值）:", e, file=sys.stderr)

    # 3) 主页累计播放 / 获赞（需要登录态；Actions 里沿用上次值）
    cookie = try_cookie()
    if cookie:
        try:
            d = get(f"https://api.bilibili.com/x/space/upstat?mid={MID}", cookie)
            s = d.get("data") or {}
            arc = s.get("archive") or {}
            if arc.get("view"):
                out["upTotalView"] = arc["view"]
            if s.get("likes"):
                out["likes"] = s["likes"]
        except Exception as e:
            print("主页统计获取失败（沿用上次值）:", e, file=sys.stderr)

    out["updatedAt"] = datetime.datetime.now(
        datetime.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("已写入", args.out, file=sys.stderr)
    print("  粉丝:", out.get("follower"), "| 名称:", out.get("name"),
          "| 主页累计播放:", out.get("upTotalView"), "| 获赞:", out.get("likes"),
          file=sys.stderr)
    return out


if __name__ == "__main__":
    main()
