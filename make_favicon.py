"""生成 favicon：把圆桌动漫头像切成带圆角的正方形，导出多尺寸 ico + png。
浏览器标签页、书签、快捷方式都会用它。"""
from PIL import Image, ImageDraw

SRC = "E:/Artificial Intelligence/WorkBuddy/2026-10-04-13-53-12/up_avatar.jpg"
OUT = "E:/Artificial Intelligence/WorkBuddy/2026-10-04-13-53-12/favicon.ico"
PNG = "E:/Artificial Intelligence/WorkBuddy/2026-10-04-13-53-12/favicon.png"

im = Image.open(SRC).convert("RGB")
# 居中裁成正方形
w, h = im.size
side = min(w, h)
im = im.crop(((w - side) // 2, (h - side) // 2,
              (w - side) // 2 + side, (h - side) // 2 + side))

# 生成 512 主图（带圆角，favicon 里圆角更好看）
S = 512
big = im.resize((S, S), Image.LANCZOS)
mask = Image.new("L", (S * 4, S * 4), 0)
ImageDraw.Draw(mask).ellipse((0, 0, S * 4 - 1, S * 4 - 1), fill=255)
mask = mask.resize((S, S), Image.LANCZOS)
rgba = big.convert("RGBA")
rgba.putalpha(mask)
rgba.save(PNG, "PNG")

# 多尺寸 ico：16/32/48/64/128/256
# favicon 会被浏览器高频缓存，必须压到很小（几 KB）
ico = rgba.resize((256, 256), Image.LANCZOS)
ico.save(OUT, format="ICO",
         sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
# ico 本身支持多帧，这里统一量化到 256 色以压缩体积

print(f"已生成 {OUT}")
print(f"已生成 {PNG}")
