import json, time, urllib.request, sys, os, socket, base64, struct

CDP="http://127.0.0.1:9334"

def http(path, method="GET", body=None):
    req=urllib.request.Request(CDP+path, method=method,
        data=json.dumps(body).encode() if body else None,
        headers={"Content-Type":"application/json"})
    return json.loads(urllib.request.urlopen(req,timeout=30).read().decode())

class WS:
    def __init__(self,url):
        u=url.replace("ws://",""); hp,path=u.split("/",1); host,port=hp.split(":")
        self.s=socket.create_connection((host,int(port)),timeout=120)
        key=base64.b64encode(os.urandom(16)).decode()
        self.s.send((f"GET /{path} HTTP/1.1\r\nHost: {hp}\r\nUpgrade: websocket\r\n"
            f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        buf=b""
        while b"\r\n\r\n" not in buf: buf+=self.s.recv(4096)
        self.buf=buf.split(b"\r\n\r\n",1)[1]; self.id=0
    def send(self,method,params=None):
        self.id+=1
        data=json.dumps({"id":self.id,"method":method,"params":params or {}}).encode()
        mask=os.urandom(4); n=len(data); hdr=bytearray([0x81])
        if n<126: hdr.append(0x80|n)
        elif n<65536: hdr.append(0x80|126); hdr+=struct.pack(">H",n)
        else: hdr.append(0x80|127); hdr+=struct.pack(">Q",n)
        hdr+=mask; hdr+=bytes(b^mask[i%4] for i,b in enumerate(data))
        self.s.send(bytes(hdr)); return self.id
    def _read(self,n):
        while len(self.buf)<n:
            d=self.s.recv(65536)
            if not d: raise EOFError
            self.buf+=d
        r,self.buf=self.buf[:n],self.buf[n:]; return r
    def recv(self):
        h=self._read(2); ln=h[1]&0x7F
        if ln==126: ln=struct.unpack(">H",self._read(2))[0]
        elif ln==127: ln=struct.unpack(">Q",self._read(8))[0]
        return json.loads(self._read(ln).decode())

tabs=[x for x in http("/json/list") if x["type"]=="page" or True]
if not tabs:
    print("target tab not found",file=sys.stderr); sys.exit(1)
ws=WS(tabs[0]["webSocketDebuggerUrl"])
ws.send("Runtime.enable"); ws.send("Page.enable")
time.sleep(2)

def ev(expr,awp=False):
    ws.send("Runtime.evaluate",{"expression":expr,"returnByValue":True,"awaitPromise":awp,"userGesture":True})
    while True:
        m=ws.recv()
        if m.get("id")==ws.id:
            r=m.get("result",{})
            if "exceptionDetails" in r:
                print("JSERR:",json.dumps(r["exceptionDetails"],ensure_ascii=False)[:300],file=sys.stderr)
            return r.get("result",{}).get("value")

