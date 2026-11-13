"""Hardware probe for per-pixel (razer) streaming. Stop govee_fx first.

    uv run python scripts/probe.py 192.168.1.50 [--count 200]

Each step streams for a few seconds; watch the curtain and note what you see.
  1. solid red / green / blue  -> checks colour order and that frames are accepted
  2. fill first N pixels      -> N=1,2,5,10,... shows how many LEDs respond
  3. single pixel walk        -> shows device pixel order (strip by strip? serpentine?)
Ctrl-C at any time restores normal mode.
"""
import argparse
import time

from functools import partial

from govee_fx import lan
from govee_fx.lan import LanDevice

BLACK, WHITE = (0, 0, 0), (255, 255, 255)


def hold(dev, pixels, secs):
    end = time.time() + secs
    while time.time() < end:
        dev.send(pixels)
        time.sleep(0.05)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ip")
    ap.add_argument("--count", type=int, default=200, help="pixels to send per frame")
    ap.add_argument("--variant", default="gradient0", choices=["gradient0", "legacy"],
                    help="0xB0 payload framing: gradient0=[0,count,RGB..] (documented), legacy=[count,RGB..]")
    ap.add_argument("--walk-only", action="store_true", help="skip colour/fill stages")
    ap.add_argument("--step", type=float, default=0.25, help="seconds per pixel in the walk")
    ap.add_argument("--hold", type=float, default=2.5)
    a = ap.parse_args()
    n = a.count
    lan.razer_frame = partial(lan.razer_frame, variant=a.variant)
    dev = LanDevice(a.ip, "razer")
    dev.start()
    time.sleep(0.5)
    try:
        for name, c in [] if a.walk_only else [("RED", (255, 0, 0)), ("GREEN", (0, 255, 0)), ("BLUE", (0, 0, 255))]:
            print(f"solid {name} ({n} px) - what colour do you see?")
            hold(dev, [c] * n, a.hold)

        for k in () if a.walk_only else (1, 2, 5, 10, 20, 50, 100, n):
            k = min(k, n)
            print(f"first {k} pixels white, rest off - how many LEDs lit?")
            hold(dev, [WHITE] * k + [BLACK] * (n - k), a.hold)

        print("single white pixel walk (0.25s each), index printed - note where it moves")
        for i in range(n):
            print(f"  pixel {i}", end="\r", flush=True)
            hold(dev, [BLACK] * i + [WHITE] + [BLACK] * (n - i - 1), a.step)
        print("\ndone")
    except KeyboardInterrupt:
        print("\ninterrupted")
    finally:
        dev.stop()


main()
