"""Render the student-equation jokes as sticker-style obstacle logos (PNG, transparent)."""
import io, json, os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFilter

OUT = sys.argv[1] if len(sys.argv) > 1 else "assets/obstacles"  # run from the project folder
os.makedirs(OUT, exist_ok=True)
matplotlib.rcParams["mathtext.fontset"] = "cm"

INK = (28, 26, 24); CREAM = (244, 239, 224); BLUE = (32, 69, 187)
RED = (210, 58, 32); PINK = (240, 120, 170); WHITE = (255, 255, 255)
# (id, mathtext, joke, fill, text color)
ITEMS = [
    ("integral", r"$\int_{\mathrm{hope}}^{\mathrm{despair}}\,dx$", "The exam experience", CREAM, INK),
    ("stress_limit", r"$\lim_{t\to\mathrm{deadline}}\ \mathrm{Stress}(t)=\infty$", "Deadline approaching", RED, WHITE),
    ("p_passing", r"$P(\mathrm{passing})\approx 0$", "Probability exam", BLUE, WHITE),
    ("motivation", r"$\frac{d}{dt}(\mathrm{Motivation})<0$", "Motivation disappearing", PINK, INK),
    ("deadlines_sum", r"$\sum_{i=1}^{\infty}\mathrm{Deadlines}_i$", "Infinite assignments", INK, CREAM),
    ("sleep", r"$\mathrm{Sleep}=\frac{1}{\mathrm{Exams}+1}$", "Exam season", CREAM, BLUE),
    ("happiness", r"$\nabla\mathrm{Happiness}=0$", "Optimization nightmare", BLUE, CREAM),
    ("pythagoras", r"$\mathrm{Coffee}^2+\mathrm{Stress}^2=\mathrm{EPFL}^2$", "Student Pythagoras", RED, CREAM),
    ("nan", r"$\mathrm{Grade}=\mathrm{NaN}$", "Programming disaster", INK, PINK),
    ("error404", r"$\mathrm{Error\ 404}$" + "\n" + r"$\mathrm{Knowledge\ not\ found}$", "Brain stopped working", CREAM, RED),
]

def render_text(tex, color):
    fig = plt.figure(figsize=(8, 3), dpi=200)
    fig.text(0.5, 0.5, tex, fontsize=30, ha="center", va="center", linespacing=1.3,
             color=tuple(c / 255 for c in color))
    buf = io.BytesIO(); fig.savefig(buf, format="png", transparent=True); plt.close(fig)
    im = Image.open(buf).convert("RGBA")
    return im.crop(im.getbbox())

manifest = []
for oid, tex, joke, fill, tcol in ITEMS:
    txt = render_text(tex, tcol)
    pad_x, pad_y, border, r, shadow = 44, 30, 10, 46, 12
    w, h = txt.width + 2 * pad_x + 40, txt.height + 2 * pad_y
    W, H = w + shadow, h + shadow
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((shadow, shadow, W - 1, H - 1), r, fill=INK + (255,))
    img.alpha_composite(sh)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, w - 1, h - 1), r, fill=fill + (255,), outline=INK + (255,), width=border)
    # little OcuSense-style asterisk accent in the top-right corner
    ac = RED if fill != RED else CREAM
    cx, cy, s = w - 40, 34, 14
    for dx, dy in ((s, 0), (0, s), (s * .7, s * .7), (s * .7, -s * .7)):
        d.line((cx - dx, cy - dy, cx + dx, cy + dy), fill=ac + (255,), width=6)
    img.alpha_composite(txt, (pad_x, pad_y))
    img.save(os.path.join(OUT, f"{oid}.png"))
    manifest.append({"id": oid, "file": f"{oid}.png", "joke": joke})
    print(oid, img.size)

# Hand-made image obstacles (not generated here) - kept in the manifest when regenerating.
EXTRA_OBSTACLES = [
    {"id": "toilet", "file": "toilet.png", "joke": "Grades went down the drain", "effect": "poop"},
    {"id": "textbook", "file": "textbook.png", "joke": "Crushed by the required reading"},
    {"id": "exam", "file": "exam.png", "joke": "Got a 1/6 on the exam"},
    {"id": "laptop", "file": "laptop.png", "joke": "Laptop died at 1%"},
    {"id": "chair", "file": "chair.png", "joke": "Broken auditorium chair"},
    {"id": "printer", "file": "printer.png", "joke": "Attacked by the library printer"},
    {"id": "eduroam", "file": "eduroam.png", "joke": "eduroam disconnected"},
    {"id": "chemistry", "file": "chemistry.png", "joke": "The chemistry lab exploded"},
]
# The equation logos were removed from the game; set this to True to bring them back.
USE_EQUATION_LOGOS = False
if not USE_EQUATION_LOGOS:
    manifest = []
manifest += EXTRA_OBSTACLES

with open(os.path.join(OUT, "obstacles.json"), "w") as f:
    json.dump(manifest, f, indent=2)
