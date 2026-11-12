"""Govee LAN API (UDP) helpers.

Enable "LAN Control" for the device in the Govee Home app first.
 - discovery: multicast 239.255.255.250:4001, replies arrive on :4002
 - control:   unicast to device port 4003

Two output modes:
 * "razer"  - per-pixel streaming (the DreamView/Razer protocol). Needed for
              real animations. Support depends on model/firmware; the framing
              here follows community reverse-engineering and is UNVERIFIED on
              curtain lights - see README.
 * "color"  - the documented colorwc command with the frame's average colour.
              Reliable but single-colour only; handy for checking connectivity.
"""
import base64
import json
import socket
import time

MCAST = ("239.255.255.250", 4001)
CONTROL_PORT = 4003


def discover(timeout=2.0):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", 4002))
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    mreq = socket.inet_aton(MCAST[0]) + socket.inet_aton("0.0.0.0")
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    sock.settimeout(0.3)
    msg = json.dumps({"msg": {"cmd": "scan", "data": {"account_topic": "reserve"}}}).encode()
    sock.sendto(msg, MCAST)
    found, end = {}, time.time() + timeout
    while time.time() < end:
        try:
            data, _ = sock.recvfrom(4096)
            d = json.loads(data)["msg"]["data"]
            found[d["ip"]] = d
        except (socket.timeout, KeyError, ValueError):
            continue
    sock.close()
    return list(found.values())


def _xor(bs):
    c = 0
    for b in bs:
        c ^= b
    return c


def razer_packet(command: int, payload: bytes) -> bytes:
    """BB | len(2, big-endian, payload only) | command | payload | xor-checksum."""
    body = bytes([0xBB]) + len(payload).to_bytes(2, "big") + bytes([command]) + payload
    return body + bytes([_xor(body)])


def razer_frame(pixels) -> bytes:
    """pixels: flat list of (r,g,b) in device order."""
    return razer_packet(0xB0, bytes([len(pixels)]) + b"".join(bytes(p) for p in pixels))


class LanDevice:
    def __init__(self, ip, mode="razer"):
        self.ip, self.mode = ip, mode
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._last_color = 0.0

    def _send(self, obj):
        self.sock.sendto(json.dumps(obj).encode(), (self.ip, CONTROL_PORT))

    def _razer(self, raw: bytes):
        self._send({"msg": {"cmd": "razer", "data": {"pt": base64.b64encode(raw).decode()}}})

    def start(self):
        self._send({"msg": {"cmd": "turn", "data": {"value": 1}}})
        if self.mode == "razer":
            self._razer(bytes.fromhex("bb0001b1010a"))

    def stop(self):
        if self.mode == "razer":
            self._razer(bytes.fromhex("bb0001b1000b"))

    def send(self, pixels):
        if self.mode == "razer":
            self._razer(razer_frame(pixels))
        else:  # throttled single colour
            now = time.time()
            if now - self._last_color < 0.25:
                return
            self._last_color = now
            n = max(len(pixels), 1)
            r, g, b = (sum(p[i] for p in pixels) // n for i in range(3))
            self._send({"msg": {"cmd": "colorwc", "data": {"color": {"r": r, "g": g, "b": b}, "colorTemInKelvin": 0}}})
