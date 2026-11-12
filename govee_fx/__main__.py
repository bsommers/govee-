import argparse

from .engine import Engine, load_config
from .server import serve


def main():
    ap = argparse.ArgumentParser(description="Govee curtain light animator")
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--ip", help="device IP (overrides config)")
    ap.add_argument("--port", type=int)
    a = ap.parse_args()
    cfg = load_config(a.config)
    if a.ip:
        cfg["device_ip"] = a.ip
    if a.port:
        cfg["port"] = a.port
    print(f"Open http://localhost:{cfg['port']}  (device: {cfg['device_ip'] or 'preview only'})")
    serve(Engine(cfg), cfg["port"])


if __name__ == "__main__":
    main()
