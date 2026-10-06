"""为Cloudflare Pages 准备封面图。

B 站封面原图普遍 2000x1500 / 十几MB，直接上传会让仓库体积爆炸、
Pages 部署超时。这里统一压成WebP：长边 620px、质量 72。
（页面里卡片最大显示290px 宽，620px 是 2 倍图，retina屏也够用）
"""
import os
import sys
from PIL import Image

BASE = "E:/Artificial Intelligence/WorkBuddy/2026-10-04-13-53-12"
SRC = f"{BASE}/covers"
DST = f"{BASE}/site/covers"
MAXSIDE = 620
QUALITY = 72

os.makedirs(DST, exist_ok=True)
names = [f for f in os.listdir(SRC) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]

src_total = sum(os.path.getsize(os.path.join(SRC, f)) for f in names)
ok = fail = 0
for i, f in enumerate(names, 1):
    src = os.path.join(SRC, f)
    out_name = os.path.splitext(f)[0] + ".webp"
    dst = os.path.join(DST, out_name)
    if os.path.exists(dst):
        ok += 1
        continue
    try:
        im = Image.open(src).convert("RGB")
        w, h = im.size
        if max(w, h) > MAXSIDE:
            if w >= h:
                nw, nh = MAXSIDE, max(1, round(h * MAXSIDE / w))
            else:
                nh, nw = MAXSIDE, max(1, round(w * MAXSIDE / h))
            im = im.resize((nw, nh), Image.LANCZOS)
        im.save(dst, "WEBP", quality=QUALITY, method=4)
        ok += 1
    except Exception as e:
        print("  失败:", f, e)
        fail += 1
    if i % 200 == 0:
        print(f"  {i}/{len(names)}")

dst_files = os.listdir(DST)
dst_total = sum(os.path.getsize(os.path.join(DST, f)) for f in dst_files)
print(f"封面转换完成：{ok} 成功 / {fail} 失败")
print(f"原始 {len(names)} 个 / {src_total/1024/1024:.1f}MB")
print(f"压缩后 {len(dst_files)} 个 / {dst_total/1024/1024:.1f}MB "
      f"(压缩率 {dst_total/src_total*100:.0f}%)")
