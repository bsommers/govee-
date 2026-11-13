"""Night sky: sparse, slowly twinkling stars plus occasional shooting stars.

Stars sit at fixed cells and fade in and out on their own slow cycles in
white, grey and bluish tints. Every so often a shooting star streaks across
the sky leaving a short fading tail.
"""
import math
import random

from .base import Effect, Param, register

# (r, g, b) tints for stars at full brightness
STAR_COLORS = [
    (255, 255, 255), (255, 255, 255), (235, 240, 255),   # whites
    (150, 150, 160), (120, 125, 140),                    # greys
    (150, 185, 255), (110, 150, 255), (170, 210, 255),   # bluish
]
SKY = (0, 0, 4)


class _Shooter:
    def __init__(self, w, h, speed):
        # enter from the top edge or a side edge, travel diagonally downward
        self.dir = random.choice((-1, 1))
        self.x = random.uniform(0, w - 1) if w > 1 else 0.0
        self.y = -1.0
        self.vx = self.dir * random.uniform(0.4, 1.0) * speed
        self.vy = random.uniform(0.8, 1.2) * speed
        self.tail = random.uniform(2.5, 4.5)
        self.color = random.choice(STAR_COLORS[:3] + STAR_COLORS[5:])

    def step(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt

    def alive(self, w, h):
        return self.y - self.tail < h and -self.tail < self.x < w + self.tail


@register
class NightSky(Effect):
    name = "nightsky"
    label = "Night sky"
    params = [
        Param("stars", "Star density", 0.12, 0.02, 0.5, 0.01),
        Param("twinkle", "Twinkle speed", 0.4, 0.1, 2.0, 0.05),
        Param("shooting", "Max shooting stars at once", 3, 1, 7, 1),
        Param("frequency", "Shooting star frequency", 0.15, 0.0, 1.0, 0.01),
        Param("glow", "Sky glow", 0.3, 0.0, 1.0, 0.01),
    ]

    def __init__(self, width, height):
        super().__init__(width, height)
        self.stars = {}   # (x, y) -> [phase, rate, color]
        self.shooters = []
        self.t = 0.0
        self._density = None

    def _seed(self, density):
        self._density = density
        cells = [(x, y) for y in range(self.h) for x in range(self.w)]
        n = max(1, round(len(cells) * density))
        old = self.stars
        self.stars = {}
        for c in random.sample(cells, min(n, len(cells))):
            self.stars[c] = old.get(c) or [
                random.uniform(0, math.tau),
                random.uniform(0.5, 1.5),           # per-star rate multiplier
                random.choice(STAR_COLORS),
            ]

    def update(self, dt, p):
        if p["stars"] != self._density:
            self._seed(p["stars"])
        self.t += dt

        # spawn: average one star per (8 / frequency) seconds, capped at `shooting`
        limit = int(p["shooting"])
        if p["frequency"] > 0 and len(self.shooters) < limit:
            if random.random() < dt * p["frequency"] / 3.0:
                self.shooters.append(_Shooter(self.w, self.h, random.uniform(6, 11)))
        for s in self.shooters:
            s.step(dt)
        self.shooters = [s for s in self.shooters if s.alive(self.w, self.h)]

        g = p["glow"]
        base = (int(SKY[0] + 6 * g), int(SKY[1] + 8 * g), int(SKY[2] + 22 * g))
        buf = [[list(base) for _ in range(self.w)] for _ in range(self.h)]

        for (x, y), (phase, rate, col) in self.stars.items():
            # slow cycle (~3-8 s) with a mostly-dim, briefly-bright profile
            v = 0.5 + 0.5 * math.sin(phase + self.t * p["twinkle"] * rate)
            b = 0.12 + 0.88 * v ** 3
            px = buf[y][x]
            for c in range(3):
                px[c] = min(255, px[c] + col[c] * b)

        for s in self.shooters:
            for i in range(int(s.tail * 2) + 1):
                d = i / 2.0
                fade = (1 - d / s.tail)
                if fade <= 0:
                    break
                n = math.hypot(s.vx, s.vy) or 1.0
                x = round(s.x - s.vx / n * d)
                y = round(s.y - s.vy / n * d)
                if 0 <= x < self.w and 0 <= y < self.h:
                    px = buf[y][x]
                    k = fade ** 1.5
                    for c in range(3):
                        px[c] = min(255, px[c] + s.color[c] * k)

        return [[(int(r), int(g_), int(b_)) for r, g_, b_ in row] for row in buf]
