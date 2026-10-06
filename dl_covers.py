import json, os, urllib.request, concurrent.futures, sys, time

OUT="E:/Artificial Intelligence/WorkBuddy/2026-10-04-13-53-12/covers"
os.makedirs(OUT, exist_ok=True)
vids=json.load(open("E:/Artificial Intelligence/WorkBuddy/2026-10-04-13-53-12/videos_full.json",encoding="utf-8"))
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def safe(s,n=60):
    for c in '\\/:*?"<>|': s=s.replace(c,'_')
    return s[:n]

def dl(v):
    pic=v.get("pic") or ""
    if not pic: return (v["bvid"],"NOPIC","")
    if pic.startswith("//"): pic="https:"+pic
    pic=pic.split("?")[0]
    if not pic.startswith("http"): pic="https://"+pic
    ext=".jpg"
    if ".png" in pic.lower(): ext=".png"
    elif ".jpeg" in pic.lower() or ".jpg" in pic.lower(): ext=".jpg"
    elif ".webp" in pic.lower(): ext=".webp"
    path=os.path.join(OUT, f"{safe(v['title'],50)}_{v['bvid']}{ext}")
    if os.path.exists(path) and os.path.getsize(path)>1000: return (v["bvid"],"OK",path)
    for attempt in range(3):
        try:
            req=urllib.request.Request(pic, headers={"User-Agent":UA,"Referer":"https://www.bilibili.com/","Accept":"image/avif,image/webp,image/*,*/*"})
            data=urllib.request.urlopen(req,timeout=30).read()
            if len(data)>800:
                open(path,"wb").write(data)
                return (v["bvid"],"OK",path)
        except Exception as e:
            time.sleep(1.2*(attempt+1))
    return (v["bvid"],"FAIL",pic)

ok=fail=nopic=0; fails=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
    for bv,st,path in ex.map(dl, vids):
        if st=="OK": ok+=1
        elif st=="FAIL": fail+=1; fails.append(bv)
        else: nopic+=1

print(f"总数 {len(vids)} | 成功 {ok} | 失败 {fail} | 无封面 {nopic}")
if fails: print("失败BV:", ", ".join(fails[:30]))
