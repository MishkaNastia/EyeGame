"""Game objects: the eyeball runner, obstacles, clouds. Drawn with shapes, no image files."""

from __future__ import annotations

import json
import math
import os
import random

import pygame

import settings as S


class Player:
    """The runner: the OcuSense eye (assets/avatar.png) on little legs. It blinks when it jumps."""

    def __init__(self) -> None:
        self.x = S.PLAYER_X
        self.y = 0.0  # height above ground (0 = on ground, positive = up)
        self.vy = 0.0  # vertical velocity (negative = going up, in screen terms)
        self.ducking = False
        self.fast_fall = False
        self.blink_t = 0.0  # seconds left of the avatar's own jump-blink
        self.extra = False  # used the mid-air extra jump (floaty until landing)
        self.anim_t = 0.0
        self.dead = False
        self.splat = None  # poop splatter (set by get_splatted when you crash into the toilet)
        self.splat_age = 0.0  # seconds since the splat, drives the animation

    @property
    def on_ground(self) -> bool:
        return self.y <= 0 and self.vy >= 0

    def jump(self) -> bool:
        if self.on_ground and not self.dead:
            self.vy = S.JUMP_VELOCITY
            self.blink_t = S.AVATAR_BLINK_S
            return True
        return False

    def extra_jump(self) -> bool:
        """One more jump in mid-air (double blink). Aims for a fixed peak so it stays on screen."""
        if self.on_ground or self.extra or self.dead:
            return False
        self.extra = True
        g = S.GRAVITY * S.EXTRA_GRAVITY_SCALE
        self.vy = -math.sqrt(2 * g * max(0.0, S.EXTRA_JUMP_APEX - self.y))  # v^2 = 2*g*h
        self.blink_t = S.AVATAR_BLINK_S
        return True

    def update(self, dt: float) -> None:
        self.anim_t += dt
        self.blink_t = max(0.0, self.blink_t - dt)
        if self.fast_fall:
            g = S.FAST_FALL_GRAVITY
        elif self.extra:
            g = S.GRAVITY * S.EXTRA_GRAVITY_SCALE
        else:
            g = S.GRAVITY
        self.vy += g * dt
        self.y -= self.vy * dt
        if self.y <= 0:
            self.y = 0
            self.vy = 0
            self.extra = False

    # Geometry -----------------------------------------------------------
    def _load_avatar(self) -> None:
        """Load assets/avatar.png (the OcuSense eye) once and split it into
        the eye part and the asterisk part, so the eye can blink on its own."""
        if hasattr(Player, "_eye_img"):
            return
        img = pygame.image.load(S.AVATAR_PATH).convert_alpha()
        w = S.AVATAR_WIDTH
        h = round(img.get_height() * w / img.get_width())
        img = pygame.transform.smoothscale(img, (w, h))
        split = round(h * S.AVATAR_EYE_TOP)  # rows above this = asterisk, below = eye
        Player._spark_img = img.subsurface((0, 0, w, split)).copy()
        Player._eye_img = img.subsurface((0, split, w, h - split)).copy()

    def _eye_rect(self) -> pygame.Rect:
        """Where the eye part of the avatar is drawn (feet go under it)."""
        self._load_avatar()
        w, h = self._eye_img.get_size()
        if self.ducking and self.on_ground:
            w, h = int(w * 1.15), int(h * 0.6)
        r = pygame.Rect(0, 0, w, h)
        r.midbottom = (self.x, S.GROUND_Y - S.LEG_LEN - int(self.y))
        return r

    def hitbox(self) -> pygame.Rect:
        r = self._eye_rect()
        # Slightly smaller than the drawing so near-misses feel fair.
        return pygame.Rect(r.x + 8, r.y + 4, r.width - 16, r.height - 4 + S.LEG_LEN)

    def get_splatted(self) -> None:
        """Crashed into the toilet: cover the eye in poop. Positions are relative to the eye centre."""
        eye = self._eye_rect()
        rnd = random.Random()
        self.splat = {
            # big blobs over the eye: (dx, dy, radius, colour)
            "blobs": [(rnd.uniform(-0.42, 0.42) * eye.width, rnd.uniform(-0.38, 0.38) * eye.height,
                       rnd.randint(6, 12), rnd.choice(S.POOP_COLORS)) for _ in range(11)],
            # drips that slowly run down: (dx, max length, width)
            "drips": [(rnd.uniform(-0.35, 0.35) * eye.width, rnd.randint(10, 22), rnd.randint(4, 6)) for _ in range(4)],
            # flying flecks: (vx, vy, radius)
            "flecks": [(rnd.uniform(-260, 260), rnd.uniform(-420, -80), rnd.randint(2, 4)) for _ in range(14)],
        }
        self.splat_age = 0.0

    def _draw_splat(self, surf: pygame.Surface, eye: pygame.Rect) -> None:
        t = self.splat_age
        cx, cy = eye.center
        grow = min(1.0, t / 0.12) * (1 + 0.25 * max(0.0, 1 - t / 0.25))  # pops in with a little overshoot
        dark = S.POOP_COLORS[0]
        for dx, length, w in self.splat["drips"]:
            L = length * min(1.0, t / 1.2)  # drips run down over ~1 s
            x, y0 = int(cx + dx), int(cy + eye.height * 0.2)
            pygame.draw.line(surf, dark, (x, y0), (x, y0 + int(L)), w)
            pygame.draw.circle(surf, dark, (x, y0 + int(L)), w // 2 + 1)
        for dx, dy, r, col in self.splat["blobs"]:
            rr = max(1, int(r * grow))
            pos = (int(cx + dx), int(cy + dy))
            pygame.draw.circle(surf, col, pos, rr)
            pygame.draw.circle(surf, S.POOP_SHINE, (pos[0] - rr // 3, pos[1] - rr // 3), max(1, rr // 4))
        for vx, vy, r in self.splat["flecks"]:
            x = cx + vx * t
            y = min(S.GROUND_Y - r, cy + vy * t + 0.5 * S.GRAVITY * t * t)  # fly, then land on the ground
            pygame.draw.circle(surf, dark, (int(x), int(y)), r)

    def draw(self, surf: pygame.Surface) -> None:
        eye = self._eye_rect()
        foot_y = S.GROUND_Y - int(self.y) - 1
        # legs
        swing = math.sin(self.anim_t * 22) * 6 if (self.on_ground and not self.dead) else 4
        for side, phase in ((-9, 1), (9, -1)):
            fx = eye.centerx + side + swing * phase
            pygame.draw.line(surf, S.INK, (eye.centerx + side, eye.bottom - 4), (fx, foot_y), 4)
            pygame.draw.line(surf, S.INK, (fx, foot_y), (fx + 6, foot_y), 4)
        # eye: squash it flat when blinking or dead, so the avatar blinks with you
        if (self.dead and not self.splat) or self.blink_t > 0:
            closed = pygame.transform.smoothscale(self._eye_img, (eye.width, max(4, eye.height // 5)))
            surf.blit(closed, closed.get_rect(center=eye.center))
        else:
            surf.blit(pygame.transform.smoothscale(self._eye_img, eye.size), eye)
        # asterisk sparkle sits above the eye, spinning when dead
        spark = self._spark_img
        if self.dead:
            spark = pygame.transform.rotate(spark, 30)
        surf.blit(spark, spark.get_rect(bottomright=(eye.right, eye.top + 2)))
        if self.splat:
            self._draw_splat(surf, eye)


class Obstacle:
    """Base class: something that scrolls left and kills on contact."""

    def __init__(self, x: float) -> None:
        self.x = x
        self.rect = pygame.Rect(0, 0, 10, 10)

    def update(self, dt: float, speed: float) -> None:
        self.x -= speed * dt

    @property
    def offscreen(self) -> bool:
        return self.x + self.rect.width < -20

    def hitbox(self) -> pygame.Rect:
        return self.rect.inflate(-6, -6)

    def draw(self, surf: pygame.Surface) -> None:  # pragma: no cover - visual
        raise NotImplementedError


class Logos:
    """Loads the equation logos once: assets/obstacles/*.png + obstacles.json (id, file, joke)."""

    _items: list[dict] | None = None

    @classmethod
    def all(cls) -> list[dict]:
        if cls._items is None:
            with open(os.path.join(S.OBSTACLE_DIR, "obstacles.json")) as f:
                items = json.load(f)
            for it in items:
                it["image"] = pygame.image.load(os.path.join(S.OBSTACLE_DIR, it["file"])).convert_alpha()
            cls._items = items
        return cls._items

    @classmethod
    def pick(cls, allow_wide: bool) -> dict:
        items = [it for it in cls.all() if allow_wide or it["id"] not in S.FLY_ONLY_LOGOS]
        return random.choice(items)


def _fit(img: pygame.Surface, max_w: int, max_h: int) -> pygame.Surface:
    """Scale an image down to fit inside max_w x max_h, keeping its proportions."""
    k = min(max_w / img.get_width(), max_h / img.get_height())
    return pygame.transform.smoothscale(img, (round(img.get_width() * k), round(img.get_height() * k)))


class LogoObstacle(Obstacle):
    """An equation logo. kind = "ground" (jump over), "low" (flying low: jump over)
    or "high" (flying high: run under it, don't jump!)."""

    def __init__(self, x: float, kind: str = "ground") -> None:
        super().__init__(x)
        self.kind = kind
        logo = Logos.pick(allow_wide=kind == "high")
        self.joke = logo["joke"]
        self.effect = logo.get("effect")  # e.g. "poop" for the toilet
        max_w, max_h = S.LOGO_BOX[kind]
        self.image = _fit(logo["image"], max_w, max_h)
        w, h = self.image.get_size()
        if kind == "ground":
            self.bottom = S.GROUND_Y
        elif kind == "low":
            self.bottom = S.GROUND_Y - S.LOW_FLY_GAP
        else:
            self.bottom = S.GROUND_Y - S.HIGH_FLY_BOTTOM
        self.t = random.random() * 10
        self.rect = pygame.Rect(int(x), self.bottom - h, w, h)

    def update(self, dt: float, speed: float) -> None:
        flying = self.kind != "ground"
        super().update(dt * (1.1 if flying else 1.0), speed)  # flyers drift a bit faster
        self.t += dt
        bob = round(math.sin(self.t * 5) * 3) if flying else 0
        self.rect.x = int(self.x)
        self.rect.bottom = self.bottom + bob

    def hitbox(self) -> pygame.Rect:
        # ignore the rounded corners and the drop shadow
        return self.rect.inflate(-10, -8).move(-2, -2)

    def draw(self, surf: pygame.Surface) -> None:
        surf.blit(self.image, self.rect)


class Coffee:
    """Energy power-up (coffee, croissant or Blink Mate, see S.POWERUPS): touch it (run or jump into it)
    for double points. Doesn't hurt."""

    _imgs: dict[str, pygame.Surface] = {}

    @classmethod
    def load(cls) -> dict[str, pygame.Surface]:
        if not cls._imgs:
            for kind, (path, height) in S.POWERUPS.items():
                cls._imgs[kind] = _fit(pygame.image.load(path).convert_alpha(), 200, height)
        return cls._imgs

    def __init__(self, x: float, in_air: bool) -> None:
        self.kind = random.choice(list(S.POWERUPS))
        self.image = Coffee.load()[self.kind]
        self.x = x
        self.bottom = S.GROUND_Y - (S.COFFEE_AIR_HEIGHT if in_air else 0)
        self.t = random.random() * 10
        self.rect = self.image.get_rect(bottomleft=(int(x), self.bottom))

    def update(self, dt: float, speed: float) -> None:
        self.x -= speed * dt
        self.t += dt
        self.rect.x = int(self.x)
        self.rect.bottom = self.bottom + round(math.sin(self.t * 6) * 4)  # gentle bob

    @property
    def offscreen(self) -> bool:
        return self.rect.right < -20

    def hitbox(self) -> pygame.Rect:
        return self.rect.inflate(-6, -6)

    def draw(self, surf: pygame.Surface) -> None:
        surf.blit(self.image, self.rect)


class Popup:
    """Floating text like "2x POINTS!" that rises and fades."""

    def __init__(self, text: str, pos: tuple[int, int]) -> None:
        self.text, self.x, self.y, self.age = text, pos[0], pos[1], 0.0

    def update(self, dt: float) -> None:
        self.age += dt
        self.y -= 50 * dt

    @property
    def done(self) -> bool:
        return self.age > 1.0


class MiroShape:
    """Background doodle in the style of Joan Miró: stars, crescent moons, coloured dots,
    squiggles and spirals drifting slowly across the sky (parallax)."""

    KINDS = ("star", "star", "moon", "dot", "dot", "squiggle", "spiral")

    def __init__(self, x: float) -> None:
        self.x = x
        # high in the sky only: never at the height of obstacles or power-ups
        self.y = random.randint(24, 120)
        self.kind = random.choice(self.KINDS)
        self.size = random.randint(9, 20)
        self.color = random.choice(S.MIRO_COLORS)
        self.parallax = random.uniform(0.12, 0.3)
        self.angle = random.uniform(0, math.pi)
        self.spin = random.uniform(-0.6, 0.6)

    def update(self, dt: float, speed: float) -> None:
        self.x -= speed * self.parallax * dt
        self.angle += self.spin * dt

    def draw(self, surf: pygame.Surface) -> None:
        x, y, r, ink = int(self.x), self.y, self.size, S.INK
        if self.kind == "star":  # Miró's black asterisk-star
            for i in range(4):
                a = self.angle + i * math.pi / 4
                dx, dy = math.cos(a) * r, math.sin(a) * r
                pygame.draw.line(surf, ink, (x - dx, y - dy), (x + dx, y + dy), 3)
        elif self.kind == "moon":  # crescent: coloured disc with a paper-coloured bite
            pygame.draw.circle(surf, self.color, (x, y), r)
            pygame.draw.circle(surf, ink, (x, y), r, 2)
            pygame.draw.circle(surf, S.BG, (x + r // 2, y - r // 3), r - 2)
        elif self.kind == "dot":
            pygame.draw.circle(surf, self.color, (x, y), r // 2 + 3)
            pygame.draw.circle(surf, ink, (x, y), r // 2 + 3, 2)
        elif self.kind == "squiggle":
            pts = [(x + i * 4, y + math.sin(self.angle * 3 + i * 0.8) * 5) for i in range(r)]
            pygame.draw.lines(surf, ink, False, pts, 3)
        else:  # spiral
            pts = [(x + math.cos(t * 0.5 + self.angle) * t * 0.9, y + math.sin(t * 0.5 + self.angle) * t * 0.9)
                   for t in range(0, r + 6)]
            pygame.draw.lines(surf, ink, False, pts, 2)
