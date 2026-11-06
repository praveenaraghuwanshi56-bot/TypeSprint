"""Draws assets/icon.ico (a cream keycap with a 'T' on a sunset tile). Replace assets/icon.ico with your own any time."""
import pathlib
from PIL import Image, ImageDraw, ImageFont

OUT = pathlib.Path(__file__).resolve().parent.parent / "assets" / "icon.ico"
S = 512
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle((16, 16, S - 16, S - 16), radius=110, fill=(232, 150, 96, 255))        # sunset tile
d.rounded_rectangle((86, 70, S - 86, S - 110), radius=60, fill=(255, 247, 235, 255))       # keycap top
d.rounded_rectangle((86, 200, S - 86, S - 70), radius=60, fill=(255, 247, 235, 255))
d.rounded_rectangle((120, 100, S - 120, S - 150), radius=44, fill=(255, 252, 245, 255))
font = None
for name in ("arialbd.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
    try:
        font = ImageFont.truetype(name, 230); break
    except OSError:
        pass
font = font or ImageFont.load_default()
d.text((S // 2, 215), "T", font=font, fill=(43, 33, 24, 255), anchor="mm")
OUT.parent.mkdir(exist_ok=True)
img.save(OUT, sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
print("wrote", OUT)
