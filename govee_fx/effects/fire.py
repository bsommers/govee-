"""Fire: a cellular-automaton flame (Fire2012-style, extended to 2D).

Heat is injected along the bottom edge, drifts upward while averaging with
its neighbours, and cools as it rises. Colours come from a heat palette.
"""
import random

from .base import Effect, Param, register

PALETTES = {
    "classic": [(0, 0, 0), (110, 0, 0), (255, 50, 0), (255, 150, 0), (255, 225, 70), (255, 255, 210)],
    "blue":    [(0, 0, 0), (0, 0, 90), (0, 60, 255), (0, 170, 255), (140, 230, 255), (240, 255, 255)],
    "green":   [(0, 0, 0), (0, 70, 0), (0, 200, 20), (120, 255, 40), (210, 255, 130), (250, 255, 220)],
    "purple":  [(0, 0, 0), (60, 0, 80), (160, 0, 255), (255, 60, 220), (255, 160, 240), (255, 240, 255)],
}


def build_lut(stops, n=256):
    lut = []
    seg = len(stops) - 1
    for i in range(n):
        t = i / (n - 1) * seg
        k = min(int(t), seg - 1)
        f = t - k
        a, b = stops[k], stops[k + 1]
        lut.append(tuple(int(a[c] + (b[c] - a[c]) * f) for c in range(3)))
    return lut


LUTS = {name: build_lut(stops) for name, stops in PALETTES.items()}
BASE_STEP_HZ = 24.0


@register
class Fire(Effect):
    name = "fire"
    label = "Fire"
    params = [
        Param("speed", "Speed", 1.0, 0.1, 4.0, 0.05),
        Param("size", "Size (flame height)", 0.6, 0.1, 1.0, 0.01),
        Param("intensity", "Intensity", 0.7, 0.0, 1.0, 0.01),
        Param("palette", "Palette", "classic", choices=list(PALETTES)),
    ]

    def __init__(self, width, height):
        super().__init__(width, height)
        # heat[0] is the BOTTOM row
        self.heat = [[0.0] * width for _ in range(height)]
        self.acc = 0.0

    def _step(self, size, intensity):
        w, h, heat = self.w, self.h, self.heat
        max_cool = 2.0 / (h * max(size, 0.05))
        for row in heat:
            for x in range(w):
                row[x] = max(0.0, row[x] - random.random() * max_cool)
        # rise + diffuse (top-down so we read last step's lower rows)
        for y in range(h - 1, 0, -1):
            below, below2 = heat[y - 1], heat[max(y - 2, 0)]
            row = heat[y]
            for x in range(w):
                l, r = below[max(x - 1, 0)], below[min(x + 1, w - 1)]
                row[x] = (below[x] * 2 + l + r + below2[x]) / 5.0
        # ignite the base
        spark_p = 0.15 + 0.7 * intensity
        base = 0.35 + 0.5 * intensity
        for x in range(w):
            heat[0][x] = max(heat[0][x] * 0.5, base * (0.6 + 0.4 * random.random()))
            if random.random() < spark_p:
                heat[0][x] = min(1.0, heat[0][x] + 0.4 + 0.6 * random.random())

    def update(self, dt, p):
        self.acc += dt * BASE_STEP_HZ * p["speed"]
        steps = min(int(self.acc), 8)
        self.acc -= int(self.acc)
        for _ in range(steps):
            self._step(p["size"], p["intensity"])
        lut = LUTS[p["palette"]]
        gain = 0.7 + 0.6 * p["intensity"]
        frame = []
        for y in range(self.h - 1, -1, -1):  # top row first
            frame.append([lut[min(255, int(v * gain * 255))] for v in self.heat[y]])
        return frame
