# CLAUDE.md — EyeGame

## Project
EyeGame is a webcam game controlled with the eyes (blinks, and later gaze direction).
It's built in Python with Pygame, using OpenCV + MediaPipe Face Mesh for eye tracking.
It builds on ideas from my OcuSense blink counter (github.com/MishkaNastia/OcuSense).

The concept and rules aren't final yet; update the **Game design** section as they firm up.

## How to work with me (teach mode)
- **I write the code; you teach and check.** Don't hand me finished solutions by default.
  Explain the concept, outline the steps, give hints or small snippets, then review what I wrote.
- Teach professor-style: structured and step by step, from basics to advanced. Say *why*, not only *how*.
- When reviewing, point to the exact lines and explain the problem. Let me fix it myself unless I ask you to.
- If I explicitly say "just write it", write it, keep it short, and explain it afterwards.
- Prefer **minimal, precise edits** over rewrites. Never restructure files I didn't ask about.
- Before a big new feature, propose a small plan (2–5 steps) and wait for my OK.

## Tech stack
- Python 3.11+
- `pygame`: game loop, rendering, input
- `opencv-python`: webcam capture
- `mediapipe`: Face Mesh landmarks for eye detection
- `numpy`
- Dependencies live in `requirements.txt`. Use a virtual env (`.venv/`).

## Structure
```
EyeGame/
├── main.py           # entry point: Game class, states (title/play/over), loop, HUD
├── settings.py       # all constants: window, physics, speed, blink thresholds
├── entities.py       # Player (OcuSense eye avatar), LogoObstacle (equation logos), Cloud
├── assets/           # avatar.png; obstacles/*.png + obstacles.json (logo id, file, joke)
├── tools/make_logos.py  # regenerates the equation logos (needs matplotlib); edit ITEMS to add jokes
├── eye_tracker.py    # webcam thread + MediaPipe Face Landmarker → "blink" events
├── models/           # face_landmarker.task, downloaded on first run (git-ignored)
└── tests/            # pytest: BlinkDetector logic
```

## Architecture rules
- **Keep eye tracking separate from the game.** `eye_tracker.py` exposes simple events/state
  (`blink`, `eyes_closed`, later `gaze_left/right`). The game never touches OpenCV or MediaPipe directly.
- Always provide a **keyboard fallback** (for example, Space = blink) so the game can be developed and tested without a webcam.
- Run the webcam read so it doesn't stall the game loop. Start simple (read once per frame).
  Move it to a thread only if FPS drops.
- Blink detection uses MediaPipe Face Landmarker **blendshapes** (`eyeBlinkLeft/Right`), with hysteresis
  plus a cooldown (`BlinkDetector`). Thresholds live in `settings.py` and can be tuned live with `[` / `]`.
  (The legacy `mp.solutions` API is gone in recent MediaPipe. Use the Tasks API.)
- Fixed target FPS (e.g. 60) via `pygame.time.Clock`. Use delta-time for movement.

## Game design
- **Art style:** inspired by Joan Miró: cream paper background, black ink lines, pure red / blue / yellow / green,
  a big red sun and floating doodles (stars, crescent moons, dots, squiggles, spirals: `MiroShape`). Palette in settings.py.
Reference: an endless side-scrolling runner in the style of the Chrome "no internet" dino game.
Use **our own character and art** (no copied sprites).

- **Core mechanic:** the player runs automatically along the ground (a natural pause = just keep running).
  **Complete blink = jump.** **Quick double blink = extra jump in mid-air** (2nd blink within 0.5 s; one per jump,
  floaty, fixed peak so it stays on screen). Jumps fire the instant the eyes close (no lag).
  The avatar blinks when it jumps. Keyboard fallback works the same way: Space = jump, double-tap Space = extra jump.
- **Obstacles:** toilet, giant textbook, flying 1/6 exam, laptop at 1%, broken chair, angry printer, eduroam router, exploding chemistry flask
  (assets/obstacles/, listed in obstacles.json with their "cause of death" joke), all drawn at the same height, on the ground; after 300 points some fly: low ones you jump
  over, high ones you run under. Crashing into one splatters the eye with poop. (The equation-joke logos were removed;
  tools/make_logos.py can bring them back with USE_EQUATION_LOGOS = True.)
- **Energy power-ups:** a coffee cup, a croissant or a Blink Mate can (S.POWERUPS) sometimes appears in a gap,
  on the ground or floating.
  Touch it = 2x points for 5 s (HUD shows a timer bar under the score).
- **Lose condition:** any collision with an obstacle → game over → blink (or Space) to restart.
- **Scoring:** the score increases with distance/time and is shown top-right as a 5-digit counter. Keep a high score (HI).
- **Levels (planned):** the game is split into levels with a finish line. Finishing a level earns points and rewards (details TBD).
- **Difficulty:** scroll speed slowly increases over time, and the gaps between obstacles shrink.
- **Physics:** gravity plus an initial jump velocity. Fixed jump arc to start (no variable jump height).
- **Blink tuning:** a blink must trigger exactly one jump. Use a debounce/cooldown so one long blink ≠ several jumps.

### Build order (steps 1–6 done; 7 partly: no sounds/calibration screen yet)
1. Pygame window, game loop, ground line, FPS clock
2. Player rectangle + gravity + jump on Space
3. Scrolling obstacles + collision → game over + restart
4. Score, high score, speed-up
5. `eye_tracker.py`: EAR blink detection, tested on its own
6. Plug blinks into the game (replace or keep Space)
7. Calibration screen, art, sounds, ducking

## Commands
```bash
# The venv lives OUTSIDE the project (keep it out of iCloud folders: iCloud offloads files and
# makes `python main.py` hang with no output). Project lives in ~/code/EyeGame, not the Desktop.
python3 -m venv ~/venvs/eyegame && source ~/venvs/eyegame/bin/activate
pip install -r requirements.txt
python main.py              # webcam + keyboard
python main.py --no-camera  # keyboard only
pytest
```

## Conventions
- PEP 8, type hints on public functions, short docstrings.
- Small commits with clear messages. Don't commit or push unless I ask.
- No webcam frames or personal recordings in git.

## Platform notes
- macOS: the terminal or IDE needs Camera permission
  (System Settings → Privacy & Security → Camera).
- MediaPipe wheels can lag behind the newest Python. If install fails, check the Python version first.
