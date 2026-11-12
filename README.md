# Govee FX

Design custom animations for Govee curtain lights. No dependencies beyond Python 3.10+.

```
python -m govee_fx                 # preview only -> http://localhost:8080
python -m govee_fx --ip 192.168.1.50
python -m pytest tests
```

The browser UI shows a live preview and sliders for each animation's parameters.
Settings persist in `state.json`.

## Connecting your lights
1. Govee Home app -> your curtain lights -> settings -> enable **LAN Control**.
2. Click **Scan** in the UI (or find the IP in your router) and **Connect**.
3. Optional `config.json` (all keys in `govee_fx/engine.py:DEFAULT_CONFIG`): set `cols`/`rows`
   to match your curtain, and `serpentine` / `flip_x` if the animation looks scrambled.

**Caveat:** per-pixel streaming ("razer" mode) uses the community-documented DreamView
framing and is untested on curtain lights. If it does nothing, use "Single colour" mode
(official `colorwc` command) to confirm connectivity, then tweak `govee_fx/lan.py`.

## Adding an animation
Create `govee_fx/effects/myeffect.py`, subclass `Effect`, list `params`, implement
`update(dt, p)` returning `rows x cols` of `(r,g,b)` (row 0 = top), decorate with `@register`,
and import it in `effects/__init__.py`. The UI picks up the sliders automatically.
See `effects/fire.py`.
