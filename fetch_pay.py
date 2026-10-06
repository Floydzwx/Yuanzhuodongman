"""批量查询 740 个视频的充电标记，保存为 pay_status.json。

判据来自 x/web-interface/view 接口 data 顶层的三个字段（不是 rights）：
  is_upower_exclusive         充电专属（需充电才能看）
  is_upower_play              充电可播放
  is_chargeable_season        充电番剧相关
另外保留 rights 里的 ugc_pay/arc_pay（付费视频）。
"""
import io
import json
import os
import time
import urllib.request

BASE = "E:/Artificial Intelligence/WorkBuddy/2026-10-04-13-53-12"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def cookies():
    jar = {}
    p = f"{BASE}/cookies.txt"
    if os.path.exists(p):
        for line in io.open(p, encoding="utf-8", errors="ignore"):
            if line.startswith("#") or not line.strip():
                continue
            f = line.split("\t")
            if len(f) >= 7:
                jar[f[5]] = f[6].strip()
    return "; ".join(f"{k}={v}" for k, v in jar.items())


def fetch(bvid, tries=3):
    url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Referer": "https://www.bilibili.com/",
        "Cookie": cookies(),
    })
    for t in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            if t == tries - 1:
                return {"code": -1, "message": str(e)}
            time.sleep(1.2 * (t + 1))


def is_charged(s):
    return bool(s.get("upower_exclusive") or s.get("upower_play")
                or s.get("chargeable_season") or s.get("ugc_pay")
                or s.get("arc_pay"))


def main():
    vids = json.load(open(f"{BASE}/videos_full.json", encoding="utf-8"))
    out = {}
    if os.path.exists(f"{BASE}/pay_status.json"):
        out = json.load(open(f"{BASE}/pay_status.json", encoding="utf-8"))
    print(f"总 {len(vids)}，已查 {len(out)}")
    ok = fail = 0
    for i, v in enumerate(vids, 1):
        bv = v["bvid"]
        if bv in out and "error" not in out[bv] and "upower_exclusive" in out[bv]:
            continue
        d = fetch(bv)
        if d.get("code") == 0:
            dd = d["data"]
            r = dd.get("rights", {})
            out[bv] = {
                "upower_exclusive": int(bool(dd.get("is_upower_exclusive"))),
                "upower_play": int(bool(dd.get("is_upower_play"))),
                "upower_preview": int(bool(dd.get("is_upower_preview"))),
                "chargeable_season": int(bool(dd.get("is_chargeable_season"))),
                "ugc_pay": int(r.get("ugc_pay", 0) or 0),
                "arc_pay": int(r.get("arc_pay", 0) or 0),
            }
            ok += 1
        else:
            out[bv] = {"error": str(d.get("message", ""))[:60]}
            fail += 1
        if i % 50 == 0:
            print(f"  {i}/{len(vids)}  成功{ok} 失败{fail}")
            json.dump(out, open(f"{BASE}/pay_status.json", "w", encoding="utf-8"),
                      ensure_ascii=False)
        time.sleep(0.3)
    json.dump(out, open(f"{BASE}/pay_status.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    charged = [b for b, s in out.items() if is_charged(s)]
    print(f"\n完成：成功 {ok} 失败 {fail}")
    print(f"充电视频 {len(charged)} 个")
    V = {x["bvid"]: x for x in vids}
    for b in sorted(charged, key=lambda x: V[x].get("pubdate", 0)):
        s = out[b]
        flags = [k for k in ("upower_exclusive", "upower_play", "chargeable_season",
                              "ugc_pay", "arc_pay") if s.get(k)]
        print(f"  {V[b]['title'][:50]}")
        print(f"     {', '.join(flags)}")


if __name__ == "__main__":
    main()
