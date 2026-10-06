"""用单合集完整接口拉取每个 season 的全部视频。
seasons_series_list 的 archives 字段是折叠的（meta.total=14 但只给 6 条），
必须改用 x/polymer/web-space/seasons_archives_list?season_id=... 分页拉全。
"""
import json, time, sys, urllib.request, os, socket, base64, struct

CDP = "http://127.0.0.1:9333"
MID = "654552"
def http(p):
    return json.loads(urllib.request.urlopen(CDP+p, timeout=30).read().decode())

class WS:
    def __init__(s_,u):
        u=u.replace("ws://","");hp,pa=u.split("/",1);h,po=hp.split(":")
        s_.s=socket.create_connection((h,int(po)),timeout=240)
        k=base64.b64encode(os.urandom(16)).decode()
        s_.s.send((f"GET /{pa} HTTP/1.1\r\nHost: {hp}\r\nUpgrade: websocket\r\n"
                   f"Connection: Upgrade\r\nSec-WebSocket-Key: {k}\r\n"
                   f"Sec-WebSocket-Version: 13\r\n\r\n").encode())
        b=b""
        while b"\r\n\r\n" not in b: b+=s_.s.recv(4096)
        s_.buf=b.split(b"\r\n\r\n",1)[1];s_.id=0
    def send(s_,m,p=None):
        s_.id+=1
        d=json.dumps({"id":s_.id,"method":m,"params":p or {}}).encode()
        mk=os.urandom(4);n=len(d);h=bytearray([0x81])
        if n<126: h.append(0x80|n)
        elif n<65536: h.append(0x80|126);h+=struct.pack(">H",n)
        else: h.append(0x80|127);h+=struct.pack(">Q",n)
        h+=mk;h+=bytes(b^mk[i%4] for i,b in enumerate(d))
        s_.s.send(bytes(h));return s_.id
    def _r(s_,n):
        while len(s_.buf)<n:
            d=s_.s.recv(65536)
            if not d: raise EOFError
            s_.buf+=d
        r,s_.buf=s_.buf[:n],s_.buf[n:];return r
    def recv(s_):
        h=s_._r(2);ln=h[1]&0x7F
        if ln==126: ln=struct.unpack(">H",s_._r(2))[0]
        elif ln==127: ln=struct.unpack(">Q",s_._r(8))[0]
        return json.loads(s_._r(ln).decode())

tabs=[x for x in http("/json/list") if x["type"]=="page"]
if not tabs: print("no tab", file=sys.stderr); sys.exit(1)
ws=WS(tabs[0]["webSocketDebuggerUrl"])
ws.send("Runtime.enable"); ws.send("Page.enable")
ws.send("Page.navigate",{"url":f"https://space.bilibili.com/{MID}/lists"})
t0=time.time()
while time.time()-t0<50:
    try:
        m=ws.recv()
        if m.get("method")=="Page.loadEventFired": break
    except EOFError: break
time.sleep(7)

def ev(e, awp=True):
    ws.send("Runtime.evaluate",{"expression":e,"returnByValue":True,"awaitPromise":awp})
    while True:
        m=ws.recv()
        if m.get("id")==ws.id:
            r=m.get("result",{})
            if "exceptionDetails" in r:
                print("JSERR",json.dumps(r["exceptionDetails"],ensure_ascii=False)[:300],file=sys.stderr)
                return None
            return r.get("result",{}).get("value")

ss = json.load(open("seasons_series.json", encoding="utf-8"))
seasons = []
for s in ss["seasons"]:
    m = s.get("meta", {})
    sid = m.get("season_id")
    if sid: seasons.append({"sid": sid, "name": m.get("name",""), "total": m.get("total", 0)})

print("待拉取合集:", len(seasons), file=sys.stderr)

JS = """(async () => {
  const sid = SID, mid = MID;
  const out = [];
  let pn = 1;
  while (pn <= 30) {
    const u = `https://api.bilibili.com/x/polymer/web-space/seasons_archives_list`
            + `?mid=${mid}&season_id=${sid}&sort_reverse=false&page_num=${pn}&page_size=30`;
    const r = await fetch(u, {credentials:'include'});
    const j = await r.json();
    if (j.code !== 0) return JSON.stringify({err: j.code+' '+j.message, list: out});
    const arc = j.data?.archives || [];
    out.push(...arc);
    const total = j.data?.page?.total ?? 0;
    if (out.length >= total || arc.length === 0) break;
    pn++;
    await new Promise(r2=>setTimeout(r2, 320));
  }
  return JSON.stringify({list: out});
})()"""

results = {}
for i, s in enumerate(seasons, 1):
    js = JS.replace("SID", str(s["sid"])).replace("MID", MID)
    raw = ev(js)
    if not raw:
        print(f"  [{i}/{len(seasons)}] {s['name'][:30]} -> JSERR", file=sys.stderr)
        results[str(s["sid"])] = {"list": [], "err": "jserr"}
        continue
    try:
        j = json.loads(raw)
    except Exception:
        results[str(s["sid"])] = {"list": [], "err": "parse"}
        continue
    lst = j.get("list", [])
    err = j.get("err")
    flag = "" if not err else f"  ERR:{err}"
    if len(lst) != s["total"]:
        flag += f"  ⚠ 应为{s['total']}"
    print(f"  [{i}/{len(seasons)}] {s['name'][:34]:<36} 取到 {len(lst):>2} / 声明 {s['total']:>2}{flag}", file=sys.stderr)
    results[str(s["sid"])] = {"name": s["name"], "list": lst, "err": err}
    time.sleep(0.25)

json.dump(results, open("seasons_full.json", "w", encoding="utf-8"), ensure_ascii=False)
tot = sum(len(v.get("list", [])) for v in results.values())
uniq = {a["bvid"] for v in results.values() for a in v.get("list", [])}
print(f"\n合计抓到 {tot} 条 (去重 {len(uniq)})，已存seasons_full.json", file=sys.stderr)
