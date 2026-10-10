"""EyeGame: an endless runner you play by blinking.

Run:  python main.py              (webcam + keyboard)
      python main.py --no-camera  (keyboard only)

Controls: blink / Space / Up = jump, double blink / double-tap Space = extra jump in mid-air,
          Down = duck (fast-fall in the air),
          [ / ] = blink sensitivity, C = camera preview, P = pause, Esc = quit.
"""

from __future__ import annotations

import os
import random
import sys

import pygame

import settings as S
from entities import Coffee, LogoObstacle, Logos, MiroShape, Player, Popup
from eye_tracker import EyeTracker

os.chdir(os.path.dirname(os.path.abspath(__file__)))  # so models/ and highscore.txt land here


def load_highscore() -> int:
    try:
        with open(S.HIGHSCORE_FILE) as f:
            return int(f.read().strip() or 0)
    except (OSError, ValueError):
        return 0


def save_highscore(value: int) -> None:
    try:
        with open(S.HIGHSCORE_FILE, "w") as f:
            f.write(str(value))
    except OSError:
        pass


class Game:
    def __init__(self, use_camera: bool = True) -> None:
        pygame.init()
        pygame.display.set_caption(S.TITLE)
        self.screen = pygame.display.set_mode((S.WIDTH, S.HEIGHT))
        self.bg_layer = pygame.Surface((S.WIDTH, S.HEIGHT), pygame.SRCALPHA)  # faded scenery
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("menlo,consolas,dejavusansmono,monospace", 20, bold=True)
        self.small = pygame.font.SysFont("menlo,consolas,dejavusansmono,monospace", 14)
        self.big = pygame.font.SysFont("menlo,consolas,dejavusansmono,monospace", 34, bold=True)
        Logos.all()  # load the obstacle images now, not mid-run when the first obstacle spawns
        Coffee.load()

        self.tracker = EyeTracker() if use_camera else None
        if self.tracker:
            self.tracker.start()
        self.show_preview = True
        self.highscore = load_highscore()
        self.state = "title"  # title | play | over
        self.paused = False
        self.last_jump_key_ms = -10_000  # when Space/Up was last pressed (for double-tap)
        self.clouds = [MiroShape(random.randint(0, S.WIDTH)) for _ in range(S.N_DOODLES)]
        self.reset()

    # --- game state -------------------------------------------------------
    def reset(self) -> None:
        self.player = Player()
        self.obstacles = []
        self.speed = S.START_SPEED
        self.score = 0.0
        self.next_spawn = S.START_SPEED * 1.2  # pixels until the next obstacle
        self.ground_offset = 0.0
        self.over_timer = 0.0
        self.flash_timer = 0.0
        self.killed_by = ""
        self.coffees = []
        self.popups = []
        self.double_timer = 0.0  # seconds of double points left
        self.double_icon = None  # image of the power-up that gave the double points (for the HUD)

    def jump_pressed(self, double: bool = False) -> None:
        """Same action for a blink, Space or Up. `double` = 2nd quick blink/tap -> extra jump in mid-air."""
        if self.paused:
            return
        if self.state == "title":
            self.state = "play"
            self.player.jump()
        elif self.state == "play":
            if not self.player.jump() and double:
                self.player.extra_jump()
        elif self.state == "over" and self.over_timer > 0.6:  # small delay so the death-blink doesn't restart
            self.reset()
            self.state = "play"

    def spawn_obstacle(self) -> None:
        x = S.WIDTH + 20
        if self.score >= S.BATS_FROM_SCORE and random.random() < 0.3:
            self.obstacles.append(LogoObstacle(x, random.choice(("low", "high"))))
        else:
            self.obstacles.append(LogoObstacle(x, "ground"))
        # Gaps are measured in *time*, so they stay fair as speed grows; they also tighten a bit.
        tighten = max(0.75, 1 - (self.speed - S.START_SPEED) / 2000)
        gap_s = random.uniform(S.MIN_GAP_S, S.MAX_GAP_S) * tighten
        self.next_spawn = max(self.speed * gap_s, self.speed * S.MIN_GAP_S * 0.8)
        # Sometimes put a coffee in the middle of the gap before the next obstacle.
        if random.random() < S.COFFEE_CHANCE and not self.coffees and self.double_timer == 0:
            gap_mid = self.obstacles[-1].rect.right + self.next_spawn / 2
            self.coffees.append(Coffee(gap_mid, in_air=random.random() < S.COFFEE_AIR_CHANCE))

    # --- loop -------------------------------------------------------------
    def handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                if event.key in (pygame.K_SPACE, pygame.K_UP):
                    now = pygame.time.get_ticks()
                    double = now - self.last_jump_key_ms <= S.DOUBLE_BLINK_WINDOW_S * 1000
                    self.last_jump_key_ms = now
                    self.jump_pressed(double)
                elif event.key == pygame.K_p and self.state == "play":
                    self.paused = not self.paused
                elif event.key == pygame.K_c:
                    self.show_preview = not self.show_preview
                elif event.key == pygame.K_LEFTBRACKET and self.tracker:
                    self.tracker.adjust_sensitivity(+S.SENSITIVITY_STEP)
                elif event.key == pygame.K_RIGHTBRACKET and self.tracker:
                    self.tracker.adjust_sensitivity(-S.SENSITIVITY_STEP)
        if self.tracker:
            for ev in self.tracker.poll_events():
                if ev in ("blink", "double_blink"):
                    self.jump_pressed(double=ev == "double_blink")
        return True

    def update(self, dt: float) -> None:
        keys = pygame.key.get_pressed()
        p = self.player
        down = keys[pygame.K_DOWN]
        p.ducking = down and p.on_ground
        p.fast_fall = down and not p.on_ground

        for c in self.clouds:
            c.update(dt, self.speed if self.state == "play" else 60)
        self.clouds = [c for c in self.clouds if c.x > -100]
        while len(self.clouds) < S.N_DOODLES:
            self.clouds.append(MiroShape(S.WIDTH + random.randint(0, 300)))

        if self.state == "over":
            self.over_timer += dt
            p.splat_age += dt
            return
        if self.state == "title":
            p.update(dt)
            return

        self.speed = min(S.MAX_SPEED, self.speed + S.SPEED_GAIN * dt)
        moved = self.speed * dt
        old_hundreds = int(self.score) // 100
        self.double_timer = max(0.0, self.double_timer - dt)
        self.score += moved * S.SCORE_RATE * (2 if self.double_timer > 0 else 1)
        if int(self.score) // 100 > old_hundreds:
            self.flash_timer = 0.8
        self.flash_timer = max(0.0, self.flash_timer - dt)
        self.ground_offset = (self.ground_offset + moved) % 40

        p.update(dt)
        self.next_spawn -= moved
        if self.next_spawn <= 0:
            self.spawn_obstacle()
        for o in self.obstacles:
            o.update(dt, self.speed)
        self.obstacles = [o for o in self.obstacles if not o.offscreen]

        hb = p.hitbox()
        for c in self.coffees:
            c.update(dt, self.speed)
            if hb.colliderect(c.hitbox()):
                c.collected = True
                self.double_timer = S.DOUBLE_POINTS_S
                self.double_icon = c.image
                self.popups.append(Popup("2x POINTS!", c.rect.midtop))
        self.coffees = [c for c in self.coffees if not c.offscreen and not getattr(c, "collected", False)]
        for pu in self.popups:
            pu.update(dt)
        self.popups = [pu for pu in self.popups if not pu.done]

        hit = next((o for o in self.obstacles if hb.colliderect(o.hitbox())), None)
        if hit:
            self.killed_by = getattr(hit, "joke", "")
            if getattr(hit, "effect", None) == "poop":
                p.get_splatted()
            p.dead = True
            self.state = "over"
            self.over_timer = 0.0
            if int(self.score) > self.highscore:
                self.highscore = int(self.score)
                save_highscore(self.highscore)

    # --- drawing ----------------------------------------------------------
    def text(self, msg: str, font, color, center=None, topleft=None, topright=None) -> None:
        img = font.render(msg, True, color)
        r = img.get_rect()
        if center:
            r.center = center
        elif topleft:
            r.topleft = topleft
        elif topright:
            r.topright = topright
        self.screen.blit(img, r)

    def draw(self) -> None:
        s = self.screen
        s.fill(S.BG)
        # Background art (sun + Miró doodles) goes on its own layer, drawn faded,
        # so it reads as scenery and never gets confused with obstacles.
        bg = self.bg_layer
        bg.fill((0, 0, 0, 0))
        sx, sy = S.SUN_POS
        pygame.draw.line(bg, S.INK, (sx - S.SUN_R + 4, sy + S.SUN_R - 4), (sx - 70, sy + 50), 2)
        pygame.draw.circle(bg, S.INK, (sx - 74, sy + 53), 5)
        pygame.draw.circle(bg, S.MIRO_RED, (sx, sy), S.SUN_R)
        pygame.draw.circle(bg, S.INK, (sx, sy), S.SUN_R, 3)
        for c in self.clouds:
            c.draw(bg)
        bg.set_alpha(S.BACKGROUND_ALPHA)
        s.blit(bg, (0, 0))
        # ground with moving dashes
        pygame.draw.line(s, S.GROUND, (0, S.GROUND_Y), (S.WIDTH, S.GROUND_Y), 4)
        for x in range(-int(self.ground_offset), S.WIDTH, 40):
            pygame.draw.line(s, S.GROUND, (x, S.GROUND_Y + 8), (x + 12, S.GROUND_Y + 8), 2)
            pygame.draw.line(s, S.GROUND, (x + 22, S.GROUND_Y + 16), (x + 26, S.GROUND_Y + 16), 2)
        for o in self.obstacles:
            o.draw(s)
        for c in self.coffees:
            c.draw(s)
        self.player.draw(s)

        # score
        visible = self.flash_timer == 0 or int(self.flash_timer * 8) % 2 == 0
        score_txt = f"HI {self.highscore:05d}  " + (f"{int(self.score):05d}" if visible else "     ")
        doubled = self.double_timer > 0
        self.text(score_txt, self.font, S.PINK_DARK if doubled else S.INK, topright=(S.WIDTH - 20, 16))
        if doubled:  # coffee icon + "2x" + shrinking bar
            ic = self.double_icon
            icon = pygame.transform.smoothscale(ic, (round(ic.get_width() * 26 / ic.get_height()), 26))
            x0 = S.WIDTH - 190
            self.screen.blit(icon, (x0, 42))
            self.text(f"2x  {self.double_timer:3.1f}s", self.small, S.PINK_DARK, topleft=(x0 + 36, 46))
            bw = 140
            pygame.draw.rect(self.screen, S.CLOUD, (x0 + 36, 66, bw, 6))
            pygame.draw.rect(self.screen, S.PINK, (x0 + 36, 66, int(bw * self.double_timer / S.DOUBLE_POINTS_S), 6))
        for pu in self.popups:
            img = self.font.render(pu.text, True, S.PINK_DARK)
            img.set_alpha(int(255 * max(0.0, 1 - pu.age)))
            self.screen.blit(img, img.get_rect(center=(int(pu.x), int(pu.y))))

        self.draw_camera_hud()

        cx = S.WIDTH // 2
        if self.state == "title":
            self.text("EYEGAME", self.big, S.PINK_DARK, center=(cx, 110))
            self.text("blink (or press Space) to start and to jump", self.font, S.INK, center=(cx, 155))
            self.text("Down = duck   [ ] = blink sensitivity   C = camera   P = pause   Esc = quit",
                      self.small, S.GROUND, center=(cx, 185))
            self.text("double blink (or double-tap Space) = extra jump in mid-air",
                      self.small, S.GROUND, center=(cx, 205))
        elif self.state == "over":
            self.text("G A M E   O V E R", self.big, S.PINK_DARK, center=(cx, 100))
            if self.killed_by:
                self.text(f"cause of death: {self.killed_by}", self.font, S.INK, center=(cx, 140))
            if self.over_timer > 0.6:
                self.text("blink or press Space to play again", self.small, S.GROUND, center=(cx, 172))
        if self.paused:
            self.text("PAUSED", self.big, S.PINK_DARK, center=(cx, 120))
        pygame.display.flip()

    def draw_camera_hud(self) -> None:
        x, y = 12, 12
        t = self.tracker
        if t is None:
            self.text("keyboard mode", self.small, S.GROUND, topleft=(x, y))
            return
        if self.show_preview and t.preview is not None:
            w, h = S.PREVIEW_SIZE
            frame = pygame.image.frombuffer(t.preview.tobytes(), (w, h), "RGB")
            self.screen.blit(frame, (x, y))
            pygame.draw.rect(self.screen, S.GROUND, (x, y, w, h), 2)
            y += h + 4
        if t.status == "ready":
            dot = S.PINK if t.eyes_closed else (90, 190, 120)
            pygame.draw.circle(self.screen, dot, (x + 6, y + 8), 6)
            label = "eyes closed" if t.eyes_closed else "eyes open"
            self.text(label, self.small, S.INK, topleft=(x + 18, y))
            # blink meter: current score vs threshold
            mw = 140
            my = y + 20
            pygame.draw.rect(self.screen, S.CLOUD, (x, my, mw, 8))
            pygame.draw.rect(self.screen, S.PINK, (x, my, int(mw * min(1, t.score)), 8))
            tx = x + int(mw * t.detector.close_threshold)
            pygame.draw.line(self.screen, S.INK, (tx, my - 3), (tx, my + 11), 2)
        else:
            self.text(f"camera: {t.status}", self.small, S.GROUND, topleft=(x, y))

    def run(self) -> None:
        running = True
        while running:
            dt = min(self.clock.tick(S.FPS) / 1000, 1 / 20)  # clamp so a hiccup can't teleport things
            running = self.handle_events()
            if not self.paused:
                self.update(dt)
            self.draw()
        if self.tracker:
            self.tracker.stop()
        pygame.quit()


if __name__ == "__main__":
    Game(use_camera="--no-camera" not in sys.argv).run()
