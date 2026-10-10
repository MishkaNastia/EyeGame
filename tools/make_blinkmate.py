"""Draw an original cartoon 'Blink Mate' can (blue can, gold bands, OcuSense eye mascot)."""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import sys  # usage: python tools/make_blinkmate.py assets/avatar.png assets/blinkmate.png
S = 4  # supersample
W, H = 220 * S, 380 * S
INK = (32, 28, 40, 255); BLUE = (34, 52, 140, 255); BLUE_D = (22, 34, 98, 255)
GOLD = (240, 182, 52, 255); GOLD_D = (196, 136, 30, 255); WHITE = (250, 248, 240, 255)
SILVER = (210, 214, 222, 255); SILVER_D = (150, 156, 170, 255)
img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
L, R = 22 * S, W - 22 * S; top, bot = 40 * S, H - 26 * S
ow = 6 * S
# bottom rim (behind the body)
d.ellipse((L + 8 * S, bot - 22 * S, R - 8 * S, bot + 12 * S), fill=SILVER_D, outline=INK, width=ow)
# body
d.rounded_rectangle((L, top, R, bot - 6 * S), 18 * S, fill=BLUE, outline=INK, width=ow)
# shading stripe + highlight
d.rectangle((R - 46 * S, top + 30 * S, R - 18 * S, bot - 30 * S), fill=BLUE_D)
d.rounded_rectangle((L + 22 * S, top + 40 * S, L + 38 * S, bot - 50 * S), 8 * S, fill=(90, 112, 200, 255))
# gold bands with white diamonds
def band(y0, y1):
    d.rectangle((L + ow // 2, y0, R - ow // 2, y1), fill=GOLD)
    d.line((L, y0, R, y0), fill=INK, width=3 * S); d.line((L, y1, R, y1), fill=INK, width=3 * S)
    cy = (y0 + y1) // 2; h = (y1 - y0) // 2 - 5 * S; step = 2 * h + 6 * S
    x = L + 14 * S
    while x + 2 * h < R - 10 * S:
        d.polygon([(x, cy), (x + h, cy - h), (x + 2 * h, cy), (x + h, cy + h)], fill=WHITE, outline=GOLD_D)
        x += step
band(top + 34 * S, top + 66 * S)
band(bot - 52 * S, bot - 22 * S)
# lid
d.ellipse((L - 4 * S, top - 26 * S, R + 4 * S, top + 26 * S), fill=SILVER, outline=INK, width=ow)
d.ellipse((L + 26 * S, top - 14 * S, R - 26 * S, top + 14 * S), fill=SILVER_D)
d.rounded_rectangle((W // 2 - 26 * S, top - 10 * S, W // 2 + 18 * S, top + 4 * S), 7 * S, fill=SILVER, outline=INK, width=3 * S)
# medallion with the OcuSense eye
cx, cy, r = W // 2, top + 128 * S, 54 * S
d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=GOLD, outline=INK, width=ow)
d.ellipse((cx - r + 9 * S, cy - r + 9 * S, cx + r - 9 * S, cy + r - 9 * S), fill=WHITE)
eye = Image.open(sys.argv[1]).convert("RGBA")
ew = int(1.5 * r); eye = eye.resize((ew, int(eye.height * ew / eye.width)), Image.LANCZOS)
img.alpha_composite(eye, (cx - ew // 2 - 4 * S, cy - eye.height // 2 - 2 * S))
# text
f1 = ImageFont.truetype("/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf", 46 * S)
f2 = ImageFont.truetype("/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf", 26 * S)
def ctext(y, s, f, fill, stroke):
    bw = d.textbbox((0, 0), s, font=f, stroke_width=stroke)
    d.text((W // 2 - (bw[2] - bw[0]) // 2, y), s, font=f, fill=fill, stroke_width=stroke, stroke_fill=INK)
ctext(top + 182 * S, "BLINK", f1, GOLD, 3 * S)
ctext(top + 238 * S, "MATE", f2, WHITE, 2 * S)
img = img.resize((W // S, H // S), Image.LANCZOS)
img.save(sys.argv[2])
