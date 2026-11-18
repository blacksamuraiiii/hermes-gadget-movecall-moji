"""生成 512x512 专家头像（纯标准库，无第三方依赖）。

设计：深色 PCB 背景 + 圆形 LCD 屏 + 金色 GPIO 焊盘 + 青色呼吸光晕。
用 2x 超采样（1024）后盒式降采样到 512，得到抗锯齿。
"""

import math
import struct
import zlib
from pathlib import Path

SS = 2
SIZE = 512
W = SIZE * SS

BG_TOP = (11, 18, 24)
BG_BOT = (19, 34, 46)
BOARD = (23, 40, 53)
BOARD_EDGE = (37, 63, 79)
PAD = (231, 184, 75)
PAD_DARK = (150, 112, 38)
RING = (45, 212, 191)
SCREEN = (7, 26, 28)
FACE = (125, 249, 230)
GLOW = (45, 212, 191)

px = bytearray(W * W * 3)


def put(x, y, c):
    if 0 <= x < W and 0 <= y < W:
        i = (y * W + x) * 3
        px[i] = c[0]
        px[i + 1] = c[1]
        px[i + 2] = c[2]


def blend(x, y, c, a):
    if not (0 <= x < W and 0 <= y < W):
        return
    i = (y * W + x) * 3
    px[i] = int(px[i] * (1 - a) + c[0] * a)
    px[i + 1] = int(px[i + 1] * (1 - a) + c[1] * a)
    px[i + 2] = int(px[i + 2] * (1 - a) + c[2] * a)


# ---------- 背景渐变 ----------
for y in range(W):
    t = y / (W - 1)
    c = tuple(int(BG_TOP[k] * (1 - t) + BG_BOT[k] * t) for k in range(3))
    row = bytes(c) * W
    px[y * W * 3:(y + 1) * W * 3] = row

# ---------- 背景细网格 ----------
step = 16 * SS
for y in range(0, W, step):
    for x in range(0, W, step):
        blend(x, y, (60, 92, 110), 0.18)


# ---------- 工具：圆角矩形 / 圆 / 圆环 ----------
def round_rect(cx, cy, hw, hh, r, color, alpha=1.0):
    x0, x1 = int(cx - hw - 2), int(cx + hw + 2)
    y0, y1 = int(cy - hh - 2), int(cy + hh + 2)
    for y in range(max(0, y0), min(W, y1)):
        for x in range(max(0, x0), min(W, x1)):
            dx = abs(x - cx) - (hw - r)
            dy = abs(y - cy) - (hh - r)
            if dx <= 0 and dy <= 0:
                d = -min(-dx, -dy)
            else:
                d = math.hypot(max(dx, 0), max(dy, 0))
            if d <= r:
                if alpha >= 1.0:
                    put(x, y, color)
                else:
                    blend(x, y, color, alpha)


def disc(cx, cy, rad, color, alpha=1.0, inner=None):
    x0, x1 = int(cx - rad - 2), int(cx + rad + 2)
    y0, y1 = int(cy - rad - 2), int(cy + rad + 2)
    for y in range(max(0, y0), min(W, y1)):
        for x in range(max(0, x0), min(W, x1)):
            d = math.hypot(x - cx, y - cy)
            if d <= rad:
                if inner is not None and d < inner:
                    continue
                if alpha >= 1.0:
                    put(x, y, color)
                else:
                    blend(x, y, color, alpha)


def glow(cx, cy, rad, color):
    x0, x1 = int(cx - rad), int(cx + rad)
    y0, y1 = int(cy - rad), int(cy + rad)
    for y in range(max(0, y0), min(W, y1)):
        for x in range(max(0, x0), min(W, x1)):
            d = math.hypot(x - cx, y - cy)
            if d < rad:
                a = (1 - d / rad) ** 3 * 0.5
                blend(x, y, color, a)


def line(x0, y0, x1, y1, color, width=1):
    n = int(max(abs(x1 - x0), abs(y1 - y0))) * 2 + 1
    for i in range(n + 1):
        t = i / n
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t
        for oy in range(-width // 2, width // 2 + 1):
            for ox in range(-width // 2, width // 2 + 1):
                if ox * ox + oy * oy <= (width / 2) ** 2:
                    put(int(x) + ox, int(y) + oy, color)


def arc(cx, cy, rad, a0, a1, color, width=2):
    steps = int(rad * abs(a1 - a0)) + 1
    for i in range(steps + 1):
        a = a0 + (a1 - a0) * i / steps
        x = cx + math.cos(a) * rad
        y = cy + math.sin(a) * rad
        for oy in range(-width, width + 1):
            for ox in range(-width, width + 1):
                if ox * ox + oy * oy <= width * width:
                    put(int(x) + ox, int(y) + oy, color)


C = W // 2
BOARD_HW = int(W * 0.33)
BOARD_HH = int(W * 0.33)
RADIUS = int(W * 0.055)

# ---------- 板子投影 ----------
round_rect(C + 6, C + 10, BOARD_HW, BOARD_HH, RADIUS, (0, 0, 0), 0.35)

# ---------- 主板 ----------
round_rect(C, C, BOARD_HW, BOARD_HH, RADIUS, BOARD)
round_rect(C, C, BOARD_HW, BOARD_HH, RADIUS, BOARD_EDGE, 0.0)
# 边框：外圈画环
round_rect(C, C, BOARD_HW, BOARD_HH, RADIUS, BOARD_EDGE)
round_rect(C, C, BOARD_HW - 3, BOARD_HH - 3, RADIUS - 2, BOARD)

# ---------- GPIO 焊盘（左右各 6 个） ----------
pad_w = int(W * 0.045)
pad_h = int(W * 0.022)
gap = int(W * 0.052)
top = C - int(gap * 2.5)
for i in range(6):
    y = top + i * gap
    round_rect(C - BOARD_HW - pad_w // 2 + 2, y, pad_w // 2, pad_h // 2, 3, PAD)
    round_rect(C + BOARD_HW + pad_w // 2 - 2, y, pad_w // 2, pad_h // 2, 3, PAD)

# ---------- 屏幕光晕 ----------
glow(C, C - int(W * 0.02), int(W * 0.30), GLOW)

# ---------- 圆形屏幕 ----------
scr = int(W * 0.165)
disc(C, C - int(W * 0.02), scr, RING)
disc(C, C - int(W * 0.02), scr - int(W * 0.012), SCREEN)

# ---------- 表情 ----------
cx, cy = C, C - int(W * 0.02)
eye_r = int(W * 0.014)
disc(cx - int(scr * 0.38), cy - int(scr * 0.18), eye_r, FACE)
disc(cx + int(scr * 0.38), cy - int(scr * 0.18), eye_r, FACE)
arc(cx, cy + int(scr * 0.05), int(scr * 0.45), 0.35, math.pi - 0.35, FACE, max(2, int(W * 0.006)))

# ---------- 屏幕内圈压暗（在表情之前绘制，避免盖住脸） ----------

# ---------- 走线装饰 ----------
line(C - BOARD_HW + int(W * 0.02), C + int(BOARD_HH * 0.62),
     C - int(W * 0.12), C + int(BOARD_HH * 0.62), PAD_DARK, max(1, int(W * 0.003)))
line(C + int(W * 0.12), C + int(BOARD_HH * 0.62),
     C + BOARD_HW - int(W * 0.02), C + int(BOARD_HH * 0.62), PAD_DARK, max(1, int(W * 0.003)))
line(C - int(W * 0.12), C + int(BOARD_HH * 0.62),
     C - int(W * 0.12), C + int(BOARD_HH * 0.30), PAD_DARK, max(1, int(W * 0.003)))
line(C + int(W * 0.12), C + int(BOARD_HH * 0.62),
     C + int(W * 0.12), C + int(BOARD_HH * 0.30), PAD_DARK, max(1, int(W * 0.003)))

# ---------- 四角螺丝 ----------
screw_r = int(W * 0.011)
for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
    disc(C + sx * (BOARD_HW - int(W * 0.028)),
         C + sy * (BOARD_HH - int(W * 0.028)), screw_r, (12, 22, 30))
    disc(C + sx * (BOARD_HW - int(W * 0.028)),
         C + sy * (BOARD_HH - int(W * 0.028)), screw_r - 2, (90, 120, 138))

# ---------- 降采样 ----------
out = bytearray(SIZE * SIZE * 3)
for y in range(SIZE):
    for x in range(SIZE):
        r = g = b = 0
        for dy in range(SS):
            for dx in range(SS):
                i = ((y * SS + dy) * W + (x * SS + dx)) * 3
                r += px[i]
                g += px[i + 1]
                b += px[i + 2]
        n = SS * SS
        o = (y * SIZE + x) * 3
        out[o] = r // n
        out[o + 1] = g // n
        out[o + 2] = b // n

# ---------- 编码 PNG ----------
raw = b"".join(b"\x00" + bytes(out[y * SIZE * 3:(y + 1) * SIZE * 3]) for y in range(SIZE))


def chunk(tag, data):
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


png = (b"\x89PNG\r\n\x1a\n"
       + chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 2, 0, 0, 0))
       + chunk(b"IDAT", zlib.compress(raw, 9))
       + chunk(b"IEND", b""))

dest = Path(sys.argv[1]) if (sys := __import__("sys")).argv[1:] else Path("expert.png")
dest.parent.mkdir(parents=True, exist_ok=True)
dest.write_bytes(png)
print(f"written {dest} ({len(png)} bytes)")
