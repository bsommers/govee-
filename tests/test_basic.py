import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from govee_fx.effects import REGISTRY
from govee_fx.lan import razer_packet, razer_frame
from govee_fx.engine import device_order


def run(params, w=20, h=10, secs=3):
    fx = REGISTRY["fire"](w, h)
    p = {**fx.defaults(), **params}
    for _ in range(secs * 30):
        f = fx.update(1 / 30, p)
    return f


def lum(f, rows=None):
    rows = f if rows is None else f[rows]
    return sum(sum(px) for r in rows for px in r)


def test_frame_shape():
    f = run({})
    assert len(f) == 10 and len(f[0]) == 20 and len(f[0][0]) == 3


def test_fire_is_bottom_heavy():
    f = run({})
    assert lum(f[5:]) > lum(f[:5])


def test_size_controls_height():
    assert lum(run({"size": 1.0})) > lum(run({"size": 0.2}))


def test_intensity_controls_brightness():
    assert lum(run({"intensity": 1.0})) > lum(run({"intensity": 0.1}))


def test_razer_enable_matches_known_packet():
    assert razer_packet(0xB1, b"\x01").hex() == "bb0001b1010a"
    assert razer_frame([(1, 2, 3)])[-1] == 0xBB ^ 0 ^ 4 ^ 0xB0 ^ 1 ^ 1 ^ 2 ^ 3


def test_device_order_serpentine():
    cfg = dict(cols=2, rows=2, serpentine=True, flip_x=False)
    frame = [[1, 2], [3, 4]]
    assert device_order(frame, cfg) == [1, 3, 4, 2]
