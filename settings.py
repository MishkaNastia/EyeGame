"""All tunable constants for EyeGame in one place."""

# --- Window ---
WIDTH, HEIGHT = 960, 360
FPS = 60
TITLE = "EyeGame"
GROUND_Y = 290  # y-coordinate of the ground line

# --- Colors: Joan Miró-inspired (cream paper, black ink, pure red / blue / yellow / green) ---
BG = (243, 236, 216)  # cream paper
INK = (22, 20, 20)  # black ink
GROUND = (22, 20, 20)
PINK = (244, 192, 28)  # accent (meters, bars): Miró yellow   (name kept from the old pink theme)
PINK_DARK = (206, 38, 30)  # titles, popups, doubled score: Miró red
WHITE = (255, 255, 255)
IRIS = (90, 160, 210)
ROCK = (150, 120, 140)
BAT = (95, 70, 110)
CLOUD = (226, 216, 190)  # empty part of meters
MIRO_RED = (206, 38, 30)
MIRO_BLUE = (28, 62, 160)
MIRO_YELLOW = (244, 192, 28)
MIRO_GREEN = (34, 128, 76)
MIRO_COLORS = [MIRO_RED, MIRO_BLUE, MIRO_YELLOW, MIRO_GREEN]
SUN_POS, SUN_R = (840, 150), 28  # the big red Miró sun in the sky
N_DOODLES = 9  # Miró doodles floating in the sky
BACKGROUND_ALPHA = 70  # 0-255: how strongly the sun + doodles show (low = faded, stays in the background)
POOP_COLORS = [(92, 58, 28), (122, 78, 38), (106, 68, 32), (140, 92, 48)]  # first = darkest (drips)
POOP_SHINE = (176, 128, 80)

# --- Player (pixels, seconds) ---
PLAYER_X = 90
AVATAR_PATH = "assets/avatar.png"  # OcuSense eye, cut out of OcuSense-icon.png
AVATAR_WIDTH = 76
AVATAR_EYE_TOP = 0.337  # fraction of the avatar height where the asterisk ends and the eye starts
EYE_RADIUS = 24  # used for obstacle sizing
LEG_LEN = 14
GRAVITY = 2600.0  # px/s^2
FAST_FALL_GRAVITY = 6000.0  # when holding Down in the air
JUMP_VELOCITY = -900.0  # px/s  -> apex ~155 px, airtime ~0.69 s
# Extra jump (double blink, in mid-air): aims for a fixed peak so it stays on screen, and is floatier.
EXTRA_JUMP_APEX = 210  # px above ground
EXTRA_GRAVITY_SCALE = 0.6
AVATAR_BLINK_S = 0.15  # the avatar's eye shuts this long when it jumps

# --- World speed / difficulty ---
START_SPEED = 420.0  # px/s
SPEED_GAIN = 20.0  # px/s added per second of play
MAX_SPEED = 1100.0
MIN_GAP_S = 0.85  # minimum time between obstacles (seconds of travel)
MAX_GAP_S = 1.8
BATS_FROM_SCORE = 300  # flying obstacles appear after this score

# --- Energy power-ups (coffee, croissant): touch one for double points ---
POWERUPS = {  # kind: (image, height in px); one is picked at random each time
    "coffee": ("assets/coffee.png", 48),  # all power-ups share the same height
    "croissant": ("assets/croissant.png", 48),
    "blinkmate": ("assets/blinkmate.png", 48),  # our own "Blink Mate" can (tools/make_blinkmate.py)
}
COFFEE_CHANCE = 0.18  # chance that a power-up appears in the gap after an obstacle
COFFEE_AIR_HEIGHT = 105  # px above ground for a floating coffee (jump to grab it)
COFFEE_AIR_CHANCE = 0.5  # floating vs on the ground
DOUBLE_POINTS_S = 5.0

# --- Equation-logo obstacles (assets/obstacles, made by tools/make_logos.py) ---
OBSTACLE_DIR = "assets/obstacles"
# max (width, height) per kind. The width cap is generous, so every object ends up the SAME HEIGHT.
LOGO_BOX = {"ground": (110, 56), "low": (110, 44), "high": (110, 44)}
FLY_ONLY_LOGOS = {"stress_limit", "pythagoras"}  # too wide to jump: only used as high flyers
LOW_FLY_GAP = 14  # px between the ground and a low flyer
HIGH_FLY_BOTTOM = 82  # px above the ground of a high flyer's bottom edge (run under it)
SCORE_RATE = 1 / 40  # points per pixel travelled (~10 pts/s at start)

# --- Eye tracking ---
CAMERA_INDEX = 0
# Blink score = mean of MediaPipe "eyeBlinkLeft" / "eyeBlinkRight" (0 = open, 1 = closed).
# Hysteresis: eyes count as CLOSED above CLOSE_THRESHOLD, OPEN again below OPEN_THRESHOLD.
CLOSE_THRESHOLD = 0.45
OPEN_GAP = 0.15  # OPEN_THRESHOLD = CLOSE_THRESHOLD - OPEN_GAP
BLINK_COOLDOWN_S = 0.1  # one blink can't trigger two jumps (short, so a quick double blink still counts)
DOUBLE_BLINK_WINDOW_S = 0.5  # 2nd blink (or Space tap) within this time of the 1st = extra jump
SENSITIVITY_STEP = 0.05  # [ and ] keys change CLOSE_THRESHOLD by this much
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/latest/face_landmarker.task"
)
MODEL_PATH = "models/face_landmarker.task"
PREVIEW_SIZE = (160, 120)

HIGHSCORE_FILE = "highscore.txt"
