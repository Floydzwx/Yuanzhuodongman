"""打包 Cloudflare Pages 静态站点到 site/ 目录。

产出结构（可直接作为 Pages 的构建输出目录）：
  site/
    index.html          主页面
    covers/*.webp       压缩后的封面
    favicon.ico         标签页图标
    up_avatar.jpg       UP 主头像
    me_avatar.jpg       制作者头像
    robots.txt
    _headers            Pages 缓存策略
    _redirects          可选跳转
"""
import json
import os
import re
import shutil

BASE = "E:/Artificial Intelligence/WorkBuddy/2026-10-04-13-53-12"
SITE = f"{BASE}/site"
os.makedirs(SITE, exist_ok=True)

# 1) 封面扩展名 jpg/png -> webp
covers_dir = f"{SITE}/covers"
if os.path.isdir(covers_dir):
    n = 0
    for f in os.listdir(covers_dir):
        if not f.lower().endswith(".webp"):
            os.remove(os.path.join(covers_dir, f))
            n += 1
    print(f"清理非 webp 封面 {n} 个")
else:
    print("错误：site/covers 不存在，请先运行 prepare_site.py")
    sys.exit(1)

# 2) 主页面：把 covers/xxx.jpg 引用改成 .webp
html = open(f"{BASE}/fanju_index.html", encoding="utf-8").read()
before = html.count(".jpg")
html = re.sub(r'(covers/[^"\'<>]+?)\.(?:jpg|jpeg|png)', r"\1.webp", html)
after = html.count(".jpg")
print(f"页面内封面引用：{before} 处 .jpg → 改为 .webp（剩余 {after} 处非 covers 的 .jpg，保留）")

# 同步 html 里的封面文件名（页面内covers 已是 webp，无需再改）
html = html.replace('src="up_avatar.jpg"', 'src="up_avatar.jpg"')  # 头像不转webp
open(f"{SITE}/index.html", "w", encoding="utf-8").write(html)
print("已写出 site/index.html")

# 3) 静态资源
for f in ("favicon.ico", "up_avatar.jpg", "me_avatar.jpg"):
    src = f"{BASE}/{f}"
    if os.path.exists(src):
        shutil.copy2(src, f"{SITE}/{f}")
        print(f"复制 {f} ({os.path.getsize(src)//1024}KB)")

# 4) robots.txt
open(f"{SITE}/robots.txt", "w", encoding="utf-8").write(
    "User-agent: *\nAllow: /\n")

# 5) _headers：给封面和页面设置缓存
open(f"{SITE}/_headers", "w", encoding="utf-8").write(
    "/covers/*\n"
    "  Cache-Control: public, max-age=31536000, immutable\n"
    "\n"
    "/*.html\n"
    "  Cache-Control: public, max-age=3600\n"
    "\n"
    "/favicon.ico\n"
    "  Cache-Control: public, max-age=604800\n"
)

# 6) _redirects：留空占位，方便以后加跳转
open(f"{SITE}/_redirects", "w", encoding="utf-8").write("# 在此配置 301 跳转，每行一条\n")

# 统计
total = 0
cnt = 0
for root, _, files in os.walk(SITE):
    for f in files:
        total += os.path.getsize(os.path.join(root, f))
        cnt += 1
print(f"\nsite/ 就绪：{cnt} 个文件，{total/1024/1024:.1f}MB")
print("其中封面：", len(os.listdir(covers_dir)), "个")
