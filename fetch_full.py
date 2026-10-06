import json, time, sys, hashlib, urllib.parse
exec(open("E:/Artificial Intelligence/WorkBuddy/2026-10-04-13-53-12/cdp_lib.py",encoding="utf-8").read().split('print("URL:')[0])

MIXIN=[46,47,18,2,53,8,23,32,15,50,10,31,58,3,45,35,27,43,5,49,33,9,42,19,29,28,14,39,12,38,41,13,37,48,7,16,24,55,40,61,26,17,0,1,60,51,30,4,22,25,54,21,56,59,6,63,57,62,11,36,20,34,44,52]

nav=json.loads(ev("fetch('https://api.bilibili.com/x/web-interface/nav',{credentials:'include'}).then(r=>r.text())",True))
w=nav["data"]["wbi_img"]
raw=w["img_url"].split("/")[-1].split(".")[0]+w["sub_url"].split("/")[-1].split(".")[0]
key="".join([raw[i] for i in MIXIN])[:32]
print("LOGIN:",nav["data"].get("isLogin"),"uname:",nav["data"].get("uname"),file=sys.stderr)

def sign(p):
    p=dict(p); p["wts"]=int(time.time())
    q=urllib.parse.urlencode(sorted(p.items()))
    p["w_rid"]=hashlib.md5((q+key).encode()).hexdigest()
    return urllib.parse.urlencode(p)

def api(u):
    r=ev("fetch(%s,{credentials:'include',headers:{'Referer':'https://space.bilibili.com/654552/upload/video'}}).then(r=>r.text()).catch(e=>JSON.stringify({err:''+e.message}))"%json.dumps(u),True)
    try: return json.loads(r)
    except Exception: return {"code":-1,"message":(r or "")[:200]}

u="https://api.bilibili.com/x/space/wbi/arc/search?"+sign({"mid":"654552","pn":1,"ps":50,"order":"pubdate","index":1,"platform":"web","web_location":"1550101"})
d=api(u)
print("PROBE code:",d.get("code"),d.get("message"),"count:",d.get("data",{}).get("page",{}).get("count") if d.get("data") else None,file=sys.stderr)
if d.get("code")!=0:
    print(json.dumps(d)[:400],file=sys.stderr); sys.exit(1)

allv=[]; pn=1; total=None
while pn<=40:
    d=api("https://api.bilibili.com/x/space/wbi/arc/search?"+sign({"mid":"654552","pn":pn,"ps":50,"order":"pubdate","index":1,"platform":"web","web_location":"1550101"}))
    if d.get("code")!=0:
        print("page",pn,"err",d.get("code"),d.get("message"),file=sys.stderr); break
    vl=d["data"]["list"]["vlist"]; total=d["data"]["page"]["count"]
    if not vl: break
    for v in vl:
        allv.append({"bvid":v["bvid"],"aid":v.get("aid",0),"title":v.get("title",""),
            "pic":v.get("pic",""),"duration":v.get("length",0),
            "pubdate":v.get("created",0),"view":v.get("play",0),
            "danmaku":v.get("video_review",0),"like":v.get("like",0),
            "series":v.get("subtitle",{}).get("", "") if isinstance(v.get("subtitle"),dict) else ""})
    print(f"page {pn}/{total} got={len(allv)}",file=sys.stderr)
    if pn>=total: break
    pn+=1; time.sleep(1.5)

json.dump(allv,open("E:/Artificial Intelligence/WorkBuddy/2026-10-04-13-53-12/videos_full.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
print("SAVED",len(allv),"of",total,file=sys.stderr)
