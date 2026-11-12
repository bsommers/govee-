import json
import threading
import time
from pathlib import Path

from .effects import REGISTRY

DEFAULT_CONFIG = {
    "cols": 20,          # number of vertical strips
    "rows": 10,          # LEDs per strip (preview/animation resolution)
    "fps": 30,
    "brightness": 1.0,
    "device_ip": "",     # empty => preview only
    "device_mode": "razer",   # "razer" (per-pixel) or "color" (average colour)
    "serpentine": False,      # every other strip runs bottom->top
    "flip_x": False,
    "port": 8080,
}


def load_config(path="config.json"):
    cfg = dict(DEFAULT_CONFIG)
    p = Path(path)
    if p.exists():
        cfg.update(json.loads(p.read_text()))
    return cfg


def device_order(frame, cfg):
    """Map frame[row][col] (row 0 = top) to the flat pixel list the device expects:
    strip by strip, each strip top->bottom (optionally serpentine)."""
    cols, rows = cfg["cols"], cfg["rows"]
    xs = range(cols - 1, -1, -1) if cfg["flip_x"] else range(cols)
    out = []
    for i, x in enumerate(xs):
        ys = range(rows)
        if cfg["serpentine"] and i % 2:
            ys = reversed(ys)
        out.extend(frame[y][x] for y in ys)
    return out


class Engine:
    def __init__(self, cfg, state_path="state.json"):
        self.cfg = cfg
        self.state_path = Path(state_path)
        self.lock = threading.Lock()
        self.device = None
        self.frame = [[(0, 0, 0)] * cfg["cols"] for _ in range(cfg["rows"])]
        self.running = True
        self.effect_name = "fire"
        self.params = {n: c.defaults() for n, c in REGISTRY.items()}
        self.brightness = cfg["brightness"]
        self._load_state()
        self.effect = REGISTRY[self.effect_name](cfg["cols"], cfg["rows"])
        self.set_device(cfg["device_ip"], cfg["device_mode"])

    # ---- state -------------------------------------------------------
    def _load_state(self):
        try:
            s = json.loads(self.state_path.read_text())
            if s.get("effect") in REGISTRY:
                self.effect_name = s["effect"]
            for n, vals in s.get("params", {}).items():
                if n in self.params:
                    self.params[n].update(self._clean(n, vals))
            self.brightness = float(s.get("brightness", self.brightness))
        except (OSError, ValueError):
            pass

    def _save_state(self):
        try:
            self.state_path.write_text(json.dumps(
                {"effect": self.effect_name, "params": self.params, "brightness": self.brightness}, indent=2))
        except OSError:
            pass

    def _clean(self, effect, vals):
        spec = {p.key: p for p in REGISTRY[effect].params}
        return {k: spec[k].clean(v) for k, v in vals.items() if k in spec}

    def snapshot(self):
        with self.lock:
            return {
                "effect": self.effect_name,
                "params": dict(self.params[self.effect_name]),
                "brightness": self.brightness,
                "effects": [c.schema() for c in REGISTRY.values()],
                "grid": {"cols": self.cfg["cols"], "rows": self.cfg["rows"]},
                "device": {"ip": self.cfg["device_ip"], "mode": self.cfg["device_mode"]},
            }

    # ---- control -----------------------------------------------------
    def set_params(self, vals):
        with self.lock:
            self.params[self.effect_name].update(self._clean(self.effect_name, vals))
            if "brightness" in vals:
                self.brightness = max(0.0, min(1.0, float(vals["brightness"])))
        self._save_state()

    def set_effect(self, name):
        if name not in REGISTRY:
            return
        with self.lock:
            self.effect_name = name
            self.effect = REGISTRY[name](self.cfg["cols"], self.cfg["rows"])
        self._save_state()

    def set_device(self, ip, mode="razer"):
        from .lan import LanDevice
        with self.lock:
            if self.device:
                self.device.stop()
            self.cfg["device_ip"], self.cfg["device_mode"] = ip, mode
            self.device = LanDevice(ip, mode) if ip else None
            if self.device:
                self.device.start()

    # ---- loop --------------------------------------------------------
    def run(self):
        last = time.perf_counter()
        period = 1.0 / self.cfg["fps"]
        while self.running:
            now = time.perf_counter()
            dt, last = min(now - last, 0.25), now
            with self.lock:
                frame = self.effect.update(dt, self.params[self.effect_name])
                k = self.brightness
                frame = [[(int(r * k), int(g * k), int(b * k)) for r, g, b in row] for row in frame]
                self.frame = frame
                dev = self.device
            if dev:
                try:
                    dev.send(device_order(frame, self.cfg))
                except OSError:
                    pass
            time.sleep(max(0.0, period - (time.perf_counter() - now)))

    def stop(self):
        self.running = False
        if self.device:
            self.device.stop()
