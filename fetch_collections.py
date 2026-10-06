import json, time, sys, urllib.request, os, socket, base64, struct

CDP = "http://127.0.0.1:9333"
MID = "654552"
def http(p):
    return json.loads(urllib.request.urlopen(CDP+p, timeout=30).read().decode())

class WS:
    def __init__(s_,u):
        u=u.replace("ws://","");hp,pa=u.split("/",1);h,po=hp.split(":")
        s_.s=socket.create_connection((h,int(po)),timeout=180)
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

# 拉合集/系列列表
JS = """(async () => {
  const mid = MID;
  const out = {seasons: [], series: []};
  let pn = 1, total = 99;
  while (pn <= 20 && total > 0) {
    const r = await fetch(`https://api.bilibili.com/x/polymer/web-space/seasons_series_list?mid=${mid}&page_num=${pn}&page_size=20`, {credentials:'include'});
    const j = await r.json();
    if (j.code !== 0) { out.err = j.code + ' ' + j.message; break; }
    const il = j.data?.items_lists || {};
    total = (j.data?.page?.total ?? 0);
    for (const s of (il.seasons_list || [])) out.seasons.push(s);
    for (const s of (il.series_list || [])) out.series.push(s);
    if (!total) break;
    pn++;
  }
  out.total = total;
  return JSON.stringify(out);
})()""".replace("MID", MID)

print("=== 合集/系列列表 ===", file=sys.stderr)
res = ev(JS)
try:
    lst = json.loads(res)
except Exception as e:
    print("parse fail:", res[:200] if res else res, file=sys.stderr); sys.exit(1)
print("err:", lst.get("err"), "| total:", lst.get("total"), file=sys.stderr)
print(f"合集(season) {len(lst['seasons'])} 个, 系列(series) {len(lst['series'])} 个", file=sys.stderr)
print("第一个合集原始字段:", json.dumps(lst["seasons"][0], ensure_ascii=False)[:400] if lst["seasons"] else "none", file=sys.stderr)

json.dump(lst, open("seasons_series.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
print("saved seasons_series.json", file=sys.stderr)
