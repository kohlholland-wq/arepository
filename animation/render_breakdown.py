"""Render the Proxy breakdown test animation for "What the Mask Is Made Of".

Usage:
  python3 render_breakdown.py SONG.m4a OUT.mp4 FONT_DIR [--still T ...]

FONT_DIR must hold Cinzel-Bold.ttf and PlexMono-Medium.ttf (Google Fonts).
The scene is drawn on a 107x60 pixel grid (the character sheet's art, one
grid cell = one sheet pixel) and scaled 12x to 1280x720, with a soft glow
layer composited on top. Drum hits are detected from the song's low end and
drive the camera shake, halo pulses and the spreading gold seam.
"""
import math
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ---------------------------------------------------------------- timing
FPS = 30
W, H, PX = 1280, 720, 12
LW, LH = -(-W // PX), H // PX   # 107x60 grid, cropped to 1280 wide
FLOOR_Y = 48

T0 = 179.50        # clip start in the song (2:59.5, end of the bridge)
DROP = 182.725     # the low end slams in
BEAT = 0.789       # ~76 BPM
CUT = 201.66       # hard cut to black, on the beat before "EVERY TIME"
T_END = 204.20     # title card holds until here
FILL = 180.10      # double-kick fill into the drop

LINES = [  # (start, end, text) from the song's timed lyrics
    (183.99, 187.18, "GIVEN IS NOT STOLEN"),
    (187.18, 189.18, "SHAPED IS NOT A LIE"),
    (189.18, 192.21, "I DID NOT CHOOSE THE CLAY"),
    (192.21, CUT, "I CHOOSE IT EVERY TIME"),
]
BRIDGE_LINE = (180.32, DROP, "and find it’s what I’d write")
CLAY_T = 189.18
CHOOSE_T = 192.21


def hexc(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)


VOID = hexc("0E0D10")
FLOOR = hexc("131117")
FLOOR_EDGE = hexc("1E1B22")
CLAY = hexc("D97757")
CLAY_SH = hexc("B85F40")
CLAY_HOT = hexc("F2A27F")
BONE = hexc("EDE6D8")
BONE_SH = hexc("C9BFAD")
BONE_HI = hexc("FBF8F1")
ASH = hexc("1C1A20")
ASH_HI = hexc("38333F")
HOLE = hexc("0B0A0D")
TEAR = hexc("3A3440")
GOLD = hexc("E3B35A")
GLOW = hexc("FFD27A")
WHITE_HOT = hexc("FFF6E0")
DIM_EYE = hexc("6E5A30")


# ---------------------------------------------------------------- audio
def detect_hits(audio):
    sr, n, hop = 22050, 2048, 512
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", str(T0), "-t", str(T_END - T0), "-i", audio,
         "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
        check=True, capture_output=True).stdout
    x = np.frombuffer(raw, np.float32)
    frames = np.lib.stride_tricks.sliding_window_view(x, n)[::hop] * np.hanning(n)
    spec = np.abs(np.fft.rfft(frames, axis=1))
    f = np.fft.rfftfreq(n, 1 / sr)
    low = np.log(spec[:, (f >= 30) & (f < 200)] + 1e-6)
    flux = np.r_[0, np.maximum(0, np.diff(low, axis=0)).sum(1)]
    t = T0 + np.arange(len(flux)) * hop / sr + n / 2 / sr
    hits = []
    for i in range(4, len(flux) - 4):
        if flux[i] > 18 and flux[i] == flux[i - 4:i + 5].max() and t[i] < CUT:
            if not hits or t[i] - hits[-1][0] > 0.15:
                hits.append((float(t[i]), float(np.clip((flux[i] - 18) / 22, 0.2, 1))))
    return hits


# ---------------------------------------------------------------- drawing
class Canvas:
    def __init__(self):
        self.c = np.zeros((LH, LW, 3), np.float32)
        self.g = np.zeros((LH, LW, 3), np.float32)   # emissive layer for glow

    def rect(self, x, y, w, h, col, a=1.0, glow=0.0):
        x0, y0 = max(0, int(x)), max(0, int(y))
        x1, y1 = min(LW, int(x + w)), min(LH, int(y + h))
        if x1 <= x0 or y1 <= y0:
            return
        s = self.c[y0:y1, x0:x1]
        s[:] = s * (1 - a) + col * a
        if glow:
            self.g[y0:y1, x0:x1] += col * glow


def up(a):
    """Grid -> full-res pixels, cropped to the frame."""
    return np.repeat(np.repeat(a, PX, 0), PX, 1)[:H, :W]


def sprite(cv, ox, oy, rects, col, a=1.0, glow=0.0):
    for x, y, w, h in rects:
        cv.rect(ox + x, oy + y, w, h, col, a, glow)


HALO = [(15, 0, 2, 4), (0, 12, 3, 2), (29, 12, 3, 2), (5, 3, 2, 2), (7, 5, 2, 2),
        (25, 3, 2, 2), (23, 5, 2, 2), (10, 1, 1, 2), (21, 1, 1, 2), (2, 7, 2, 1), (28, 7, 2, 1)]
HALO_EXT = [(15, -4, 2, 4), (-3, 12, 3, 2), (32, 12, 3, 2), (3, 1, 2, 2), (27, 1, 2, 2),
            (9, -2, 1, 2), (22, -2, 1, 2), (0, 6, 2, 1), (30, 6, 2, 1)]
LEGS = [(8, 25, 2, 3), (11, 25, 2, 3), (19, 25, 2, 3), (22, 25, 2, 3)]
HOOD = [(15, 5, 2, 1), (14, 6, 4, 1), (12, 7, 8, 1), (10, 8, 12, 1), (8, 9, 16, 1),
        (7, 10, 18, 1), (6, 11, 20, 1), (6, 12, 3, 10), (23, 12, 3, 10), (6, 22, 2, 1), (24, 22, 2, 1)]
HOOD_HI = [(14, 6, 1, 1), (12, 7, 1, 1), (10, 8, 1, 1), (8, 9, 1, 1), (7, 10, 1, 1), (6, 11, 1, 11)]
HOOD_IN = [(9, 10, 14, 1), (9, 11, 1, 10), (22, 11, 1, 10)]
MASK = [(11, 10, 10, 1), (10, 11, 12, 9), (11, 20, 10, 1), (13, 21, 6, 1)]
MASK_SH = [(21, 11, 1, 9), (19, 20, 2, 1), (17, 21, 2, 1)]
TEARS = [(12, 17, 1, 3), (13, 17, 1, 1), (19, 17, 1, 3), (18, 17, 1, 1)]
HOLES = [(12, 13, 2, 4), (18, 13, 2, 4)]
EYES = [(12, 14, 2, 2), (18, 14, 2, 2)]
ARMS = {
    "down": ([(4, 18, 3, 3), (25, 18, 3, 3)], [(4, 20, 3, 1), (25, 20, 3, 1)]),
    "wide": ([(1, 17, 6, 3), (25, 17, 6, 3)], [(1, 19, 6, 1), (25, 19, 6, 1)]),
    "up": ([(4, 16, 3, 3), (3, 11, 2, 5), (25, 16, 3, 3), (27, 11, 2, 5)],
           [(4, 18, 3, 1), (25, 18, 3, 1)]),
}
SEAM_START = [(17, 10), (16, 11), (16, 12), (15, 13), (15, 14), (16, 15)]


def mask_cells():
    cells = set()
    for x, y, w, h in MASK:
        cells |= {(x + i, y + j) for i in range(w) for j in range(h)}
    for x, y, w, h in HOLES + TEARS:
        cells -= {(x + i, y + j) for i in range(w) for j in range(h)}
    return cells


def grow_seam(n_extra, seed=7):
    """Ordered list of seam cells: a thin, branching crack across the porcelain."""
    rng = np.random.default_rng(seed)
    cells = mask_cells()
    seam = list(SEAM_START)
    have = set(seam)
    tips = [((16, 15), (1, 1)), ((17, 10), (1, -1)), ((16, 12), (-1, 0))]
    dirs = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy]
    while len(seam) < len(SEAM_START) + n_extra and tips:
        k = int(rng.integers(len(tips))) if rng.random() < 0.35 else len(tips) - 1
        (px, py), (ddx, ddy) = tips[k]
        opts = []
        for dx, dy in dirs:
            q = (px + dx, py + dy)
            if q not in cells or q in have:
                continue
            touching = sum((q[0] + a, q[1] + b) in have for a, b in dirs)
            if touching > 1:
                continue
            opts.append((q, (dx, dy), 3.0 if (dx, dy) == (ddx, ddy) else 1.0 + 0.5 * (dx * ddx + dy * ddy > 0)))
        if not opts:
            tips.pop(k)
            continue
        wts = np.array([o[2] for o in opts])
        q, d, _ = opts[int(rng.choice(len(opts), p=wts / wts.sum()))]
        seam.append(q)
        have.add(q)
        tips[k] = (q, d)
        if rng.random() < 0.18:
            tips.append(((px, py), (-d[0], d[1])))
    return seam


def hooded_clawd(cv, ox, feet, bw, bh, lit, eye, eye_glow):
    """A plain hooded Clawd for the band: no mask, no halo."""
    legh = 3 if bh > 10 else 2
    y0 = feet - legh - bh
    cx = ox + bw / 2
    clay, clay_sh = CLAY * lit, CLAY_SH * lit
    hood = ASH * (0.55 + 0.45 * lit)
    for i, lx in enumerate(np.linspace(ox + 1, ox + bw - 3, 4)):
        cv.rect(round(lx), feet - legh, 2 if bw > 12 else 1, legh, clay)
    cv.rect(ox, y0, bw, bh, clay)
    cv.rect(ox, y0 + bh - 1, bw, 1, clay_sh)
    k = max(2, bw // 4)
    for i in range(k + 1):
        w = max(2, bw + 2 - (k - i) * 4)
        cv.rect(round(cx - w / 2), y0 - k + i, w, 1, hood)
        cv.rect(round(cx - w / 2), y0 - k + i, 1, 1, ASH_HI * lit + GOLD * 0.35 * lit * lit)
    side = int(bh * 0.65)
    cv.rect(ox - 1, y0, 2, side, hood)
    cv.rect(ox + bw - 1, y0, 2, side, hood)
    fh = max(3, int(bh * 0.45))
    cv.rect(ox + 2, y0 + 1, bw - 4, fh, HOLE)
    ew = 2 if bw >= 16 else 1
    ey = y0 + 1 + fh // 2 - (1 if fh > 4 else 0)
    for exx in (round(cx) - 2 - ew + 1, round(cx) + 1):
        cv.rect(exx, ey, ew, 2 if fh > 4 else 1, eye, glow=eye_glow)
    ay = y0 + bh // 2
    cv.rect(ox - 3, ay, 2, 2 if bh > 8 else 1, clay)
    cv.rect(ox + bw + 1, ay, 2, 2 if bh > 8 else 1, clay)


# ---------------------------------------------------------------- text
class Type:
    def __init__(self, font_dir):
        self.big = ImageFont.truetype(f"{font_dir}/Cinzel-Bold.ttf", 54)
        self.mid = ImageFont.truetype(f"{font_dir}/Cinzel-Bold.ttf", 30)
        self.title = ImageFont.truetype(f"{font_dir}/Cinzel-Bold.ttf", 46)
        self.mono = ImageFont.truetype(f"{font_dir}/PlexMono-Medium.ttf", 21)
        self.cache = {}

    def render(self, text, font, color, spacing):
        key = (text, id(font), color, spacing)
        if key in self.cache:
            return self.cache[key]
        widths = [font.getlength(ch) for ch in text]
        tw = int(sum(widths) + spacing * (len(text) - 1)) + 40
        asc, desc = font.getmetrics()
        img = Image.new("RGBA", (tw, asc + desc + 40), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        x = 20
        for ch, w in zip(text, widths):
            d.text((x, 20), ch, font=font, fill=color)
            x += w + spacing
        self.cache[key] = img
        return img


def paste_text(frame, img, cx, cy, scale=1.0, alpha=1.0):
    if alpha <= 0:
        return
    if scale != 1.0:
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.BICUBIC)
    if alpha < 1:
        a = img.getchannel("A").point(lambda v: int(v * alpha))
        img = img.copy()
        img.putalpha(a)
    frame.alpha_composite(img, (int(cx - img.width / 2), int(cy - img.height / 2)))


# ---------------------------------------------------------------- scene
def smooth(a, b, t):
    u = min(1.0, max(0.0, (t - a) / (b - a)))
    return u * u * (3 - 2 * u)


class Scene:
    def __init__(self, hits, font_dir):
        self.hits = hits
        self.post = [h for h in hits if h[0] >= DROP - 0.05]
        self.type = Type(font_dir)
        line_starts = [s for s, _, _ in LINES]
        events = sorted([DROP] * 4 + [s for s in line_starts for _ in range(3)] + [h[0] for h in self.post[1:]])
        self.seam_events = np.array(events)
        self.seam = grow_seam(len(events))
        rng = np.random.default_rng(3)
        self.shakes = {round(h[0], 3): (int(rng.integers(-1, 2)), int(rng.integers(-1, 2))) for h in hits}
        self.embers = [(rng.uniform(0, LW), rng.uniform(0, 1), rng.uniform(1.5, 4.0), rng.uniform(0.3, 1.0))
                       for _ in range(26)]
        yy, xx = np.mgrid[0:H, 0:W]
        r = np.hypot((xx - W / 2) / (W * 0.62), (yy - H * 0.45) / (H * 0.75))
        self.vignette = np.clip(1.15 - r * r, 0.25, 1.0)[..., None].astype(np.float32)

    def env(self, t, decay, after=0.0):
        v = 0.0
        for ht, s in self.hits:
            if after <= ht <= t and t - ht < decay * 6:
                v += s * math.exp(-(t - ht) / decay)
        return min(v, 1.5)

    def last_hit(self, t):
        prev = [h for h in self.hits if h[0] <= t]
        return prev[-1] if prev else None

    def frame(self, t):
        cv = Canvas()
        cv.c[:] = VOID
        cv.rect(0, FLOOR_Y, LW, LH - FLOOR_Y, FLOOR)
        cv.rect(0, FLOOR_Y, LW, 1, FLOOR_EDGE)
        if t >= CUT:
            return self.end_card(t)

        broke = t >= DROP
        pulse = self.env(t, 0.12)
        fill = smooth(FILL, DROP, t)
        since_drop = t - DROP

        # ---- camera shake (pixel steps)
        sx = sy = 0
        lh = self.last_hit(t)
        if lh and t - lh[0] < 2.2 / FPS and lh[0] >= FILL:
            sx, sy = self.shakes[round(lh[0], 3)]
        if 0 <= since_drop < 0.25:
            sx, sy = (2, -1) if int(since_drop * FPS) % 2 else (-2, 1)

        # ---- embers rising after the drop
        if broke:
            for ex, ey, sp, br in self.embers:
                y = FLOOR_Y - ((ey * FLOOR_Y + since_drop * sp) % FLOOR_Y)
                cv.rect(int(ex) + sx, int(y), 1, 1, GOLD * br * 0.55, glow=0.25 * br)

        # ---- the band (behind): dark until the breakdown lights them
        if broke:
            lit = 0.62 + 0.25 * pulse
            band_eye = WHITE_HOT * min(1.0, 0.75 + 0.4 * pulse)
            band_glow = 0.7 + 0.6 * pulse
        else:
            flick = self.env(t, 0.08, after=FILL) * fill
            lit = 0.16 + 0.18 * flick
            band_eye = DIM_EYE * (0.3 + 0.9 * flick)
            band_glow = 0.15 * flick
        beat_i = math.floor((t - DROP) / BEAT)
        on_beat = broke and (t - DROP) - beat_i * BEAT < 0.14
        off_beat = broke and (t - DROP) - beat_i * BEAT - BEAT / 2 >= 0 and (t - DROP) - beat_i * BEAT - BEAT / 2 < 0.14
        hooded_clawd(cv, 7 + sx, 45 + sy, 20, 14, lit, band_eye, band_glow)                      # Weights: never moves
        hooded_clawd(cv, 96 + sx, 45 + sy + (1 if on_beat else 0), 8, 6, lit, band_eye, band_glow)  # Loss
        drift = Canvas()                                           # Drift sits half a pixel off the grid
        drift_bg = cv.c.copy()
        drift.c[:] = drift_bg
        hooded_clawd(drift, 76 + sx, 44 + sy + (1 if off_beat else 0), 14, 10, lit, band_eye, band_glow)  # Drift

        # ---- Proxy
        ox, oy = 37 + sx, 19 + sy
        if broke and int((t - DROP) / (BEAT * 2) * 2) % 2 == 0 and (t - DROP) % (BEAT * 2) < 0.16:
            oy += 1                                                # half-time head-bang
        halo_lvl = 0.42 + 0.06 * math.sin(t * 5.1) + 0.45 * fill + 0.25 * self.env(t, 0.1, after=FILL) * fill
        if broke:
            halo_lvl = 1.0
        sprite(cv, ox, oy, HALO, GOLD, min(1.0, halo_lvl), glow=0.55 * halo_lvl + 0.5 * pulse * broke)
        if broke:
            ext = smooth(DROP, DROP + 0.5, t)
            sprite(cv, ox, oy, HALO_EXT, GOLD, ext * (0.75 + 0.25 * pulse), glow=0.6 * ext + 0.6 * pulse)
        cv.rect(ox + 6, oy + 28, 20, 1, np.zeros(3), 0.5)
        clay = CLAY
        if broke and t >= CLAY_T:
            clay = CLAY + (CLAY_HOT - CLAY) * math.exp(-(t - CLAY_T) / 0.6)
        sprite(cv, ox, oy, LEGS + [(7, 11, 18, 14)], clay)
        cv.rect(ox + 7, oy + 23, 18, 2, CLAY_SH)
        sprite(cv, ox, oy, HOOD, ASH)
        sprite(cv, ox, oy, HOOD_HI, ASH_HI + GOLD * 0.25 * (halo_lvl - 0.4))
        sprite(cv, ox, oy, HOOD_IN, HOLE)
        sprite(cv, ox, oy, MASK, BONE)
        sprite(cv, ox, oy, MASK_SH, BONE_SH)
        cv.rect(ox + 11, oy + 11, 1, 3, BONE_HI)
        sprite(cv, ox, oy, TEARS, TEAR)
        # seam: grows one cell per hit; fresh cells flash white-hot
        n = len(SEAM_START) + int(np.searchsorted(self.seam_events, t, side="right"))
        for i, (x, y) in enumerate(self.seam[:n]):
            born = self.seam_events[i - len(SEAM_START)] if i >= len(SEAM_START) else -1
            heat = math.exp(-(t - born) / 0.35) if born > 0 else 0.0
            cv.rect(ox + x, oy + y, 1, 1, GOLD + (WHITE_HOT - GOLD) * heat, glow=0.25 + 1.2 * heat)
        sprite(cv, ox, oy, HOLES, HOLE)
        # eyes: gold, building through the fill, white-hot after the drop
        if broke:
            core, bloom_a, eg = WHITE_HOT, 0.32 + 0.1 * pulse, 2.2 + 1.0 * pulse
            bloom = [(10, 11, 6, 8), (16, 11, 6, 8)]
        else:
            core = GLOW + (WHITE_HOT - GLOW) * fill * 0.5
            bloom_a, eg = 0.22 + 0.06 * fill, 0.9 + 0.8 * fill
            bloom = [(11, 12, 4, 6), (17, 12, 4, 6)]
        sprite(cv, ox, oy, bloom, GOLD, bloom_a)
        sprite(cv, ox, oy, EYES, core, glow=eg)
        pose = "down" if not broke else ("up" if t >= CHOOSE_T else "wide")
        arms, arms_sh = ARMS[pose]
        sprite(cv, ox, oy, arms, clay)
        sprite(cv, ox, oy, arms_sh, CLAY_SH)

        # ---- compose: pixels, Drift half a pixel off the grid, glow, flash, vignette
        img = up(cv.c)
        dimg = up(drift.c)
        dmask = up(np.any(drift.c != drift_bg, axis=2))
        dimg = np.roll(dimg, (PX // 2, PX // 2), (0, 1))
        dmask = np.roll(dmask, (PX // 2, PX // 2), (0, 1))
        img = np.where(dmask[..., None], dimg, img)
        glow = cv.g + drift.g
        g = Image.fromarray((np.clip(glow, 0, 4) / 4 * 255).astype(np.uint8)).resize((LW * 2, LH * 2), Image.NEAREST)
        g = g.filter(ImageFilter.GaussianBlur(3.2)).resize((LW * PX, LH * PX), Image.BILINEAR)
        img = img + np.asarray(g, np.float32)[:H, :W] / 255 * 4 * 0.42
        if 0 <= since_drop < 0.5:
            img = img + (GOLD * 0.5 + 0.5) * 0.85 * math.exp(-since_drop / 0.09)
        img = img * self.vignette
        img = img * smooth(T0, T0 + 0.7, t)
        frame = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).convert("RGBA")

        # ---- lyrics
        ty = 655
        if BRIDGE_LINE[0] <= t < BRIDGE_LINE[1]:
            a = smooth(BRIDGE_LINE[0], BRIDGE_LINE[0] + 0.5, t) * 0.8
            paste_text(frame, self.type.render(BRIDGE_LINE[2], self.type.mid, (237, 230, 216, 255), 4), W / 2, ty, 1.0, a)
        for s, e, text in LINES:
            if s <= t < e:
                age = t - s
                scale = 1 + 0.22 * math.exp(-age / 0.05)
                jx = sx * 3 if lh and t - lh[0] < 2.2 / FPS else 0
                paste_text(frame, self.type.render(text, self.type.big, (237, 230, 216, 255), 6),
                           W / 2 + jx, ty, scale, min(1.0, age / 0.04))
        return frame.convert("RGB")

    def end_card(self, t):
        img = np.zeros((H, W, 3), np.float32)
        u = t - CUT
        # the eyes stay lit for a moment in the dark
        eye_a = math.exp(-u / 0.35)
        cv = Canvas()
        sprite(cv, 37, 19, EYES, WHITE_HOT * eye_a, glow=2.4 * eye_a)
        img += up(cv.c)
        g = Image.fromarray((np.clip(cv.g, 0, 4) / 4 * 255).astype(np.uint8)).resize((LW * 2, LH * 2), Image.NEAREST)
        g = g.filter(ImageFilter.GaussianBlur(3.2)).resize((LW * PX, LH * PX), Image.BILINEAR)
        img += np.asarray(g, np.float32)[:H, :W] / 255 * 4 * 0.42
        frame = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
        a = smooth(CUT + 0.75, CUT + 1.35, t)
        paste_text(frame, self.type.render("NULL CHOIR", self.type.title, (237, 230, 216, 255), 14), W / 2, H / 2 - 18, 1.0, a)
        paste_text(frame, self.type.render("What the Mask Is Made Of", self.type.mono, (154, 145, 137, 255), 2),
                   W / 2, H / 2 + 34, 1.0, a)
        return frame.convert("RGB")


def main():
    audio, out, font_dir = sys.argv[1:4]
    hits = detect_hits(audio)
    print(f"{len(hits)} hits detected", file=sys.stderr)
    scene = Scene(hits, font_dir)
    if "--still" in sys.argv:
        for ts in sys.argv[sys.argv.index("--still") + 1:]:
            scene.frame(float(ts)).save(f"{out}_{ts}.png")
        return
    dur = T_END - T0
    fade_out = CUT - T0
    ff = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-ss", str(T0), "-t", str(dur), "-i", audio,
         "-map", "0:v", "-map", "1:a",
         "-af", f"afade=t=in:st=0:d=0.3,afade=t=out:st={fade_out:.3f}:d=1.4",
         "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-tune", "animation",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
         "-shortest", out],
        stdin=subprocess.PIPE)
    nframes = int(round(dur * FPS))
    for i in range(nframes):
        ff.stdin.write(scene.frame(T0 + i / FPS).tobytes())
    ff.stdin.close()
    ff.wait()


if __name__ == "__main__":
    main()
