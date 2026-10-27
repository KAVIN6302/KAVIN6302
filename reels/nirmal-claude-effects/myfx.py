"""Custom looks for Nirmal's reel, registered on top of the effects skill's fx.py.

Adds: documentary, kallaway-split, studio timeline ("Claude renders it"),
and a few patches so nothing shows the original creator's name or numbers.
Usage is identical to fx.py:  python myfx.py --plan plan.json in.mp4 out.mp4
"""
import inspect, math, os, sys
SK = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '.claude', 'skills', 'effects', 'scripts')
sys.path.insert(0, SK)
import fx
from fx import *  # noqa: F401,F403  (helpers: place, comp, text_img, font, glass, ...)
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFilter

NAME, FULL, HANDLE = 'Nirmal', 'NIRMAL ALFRED', '@nirmalalfred_official'
TOP = os.environ.get('TOP_VIEWS', '839K')


# ---------- patches on the stock effects ----------
def _patch(fn_name, pairs):
    src = inspect.getsource(getattr(fx, fn_name))
    for a, b in pairs:
        assert a in src, (fn_name, a)
        src = src.replace(a, b)
    exec(compile(src, f'<patched {fn_name}>', 'exec'), fx.__dict__)


def fit_big(d, S, s):
    """Stat-tile number that always fits the 300px tile (e.g. 839K)."""
    size = S * 0.44
    while size > 10 and font('uib', size).getlength(s) > S * 0.84: size *= 0.94
    d.text((S * 0.08, S * 0.2 + (S * 0.44 - size) * 0.55), s, font=font('uib', size), fill=(255, 255, 255, 255))
fx.fit_big = fit_big

_patch('glass_widgets_v2', [
    ("d.text((S * 0.08, S * 0.2), e.o.get('text', '38'), font=font('uib', S * 0.44), fill=white + (255,))", "fit_big(d, S, e.o.get('text', '38'))"),
    ("'197K', font=font('anton'", "e.o.get('top', '197K'), font=font('anton'"),
])
_patch('fx_headline_wall', [("'@vibha.in.progress  ·  ' + meta) if meta else '@vibha.in.progress'",
                             "e.o.get('handle', '@you') + '  ·  ' + meta) if meta else e.o.get('handle', '@you')")])
_patch('fx_checklist', [("al * clamp(c.lt / 0.12), guard=True)", "al * clamp(c.lt / 0.12))")])  # card sits under the chin; don't cut its title
fx.EFFECTS['checklist'] = (fx.fx_checklist, fx.EFFECTS['checklist'][1])
fx.EFFECTS['glass-widgets'] = (fx.fx_glass_widgets, fx.EFFECTS['glass-widgets'][1])
fx.EFFECTS['headline-wall'] = (fx.fx_headline_wall, fx.EFFECTS['headline-wall'][1])


# ---------- shared bits ----------
PINK, ORANGE_, CREAM_BG = (236, 72, 140), (217, 119, 87), (238, 233, 224)


def vgrad(w, h, top, bot):
    t = np.linspace(0, 1, int(h), dtype=np.float32)[:, None, None]
    return (np.float32(top) * (1 - t) + np.float32(bot) * t) / 255 * np.ones((1, int(w), 1), np.float32)


def hgrad_pill(w, h, r, a, b, alpha=255):
    w, h = int(w), int(h)
    t = np.linspace(0, 1, w, dtype=np.float32)[None, :, None]
    fill = (np.float32(a) * (1 - t) + np.float32(b) * t) * np.ones((h, 1, 1), np.float32)
    im = Image.fromarray(np.concatenate([fill, np.full((h, w, 1), alpha, np.float32)], 2).astype(np.uint8), 'RGBA')
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], int(r), fill=alpha); im.putalpha(m)
    return im


def spaced(s, size, kind, fill, spacing):
    f = font(kind, size); w = int(sum(f.getlength(ch) + spacing for ch in s)) + 4
    im = Image.new('RGBA', (w, int(size * 1.4)), (0, 0, 0, 0)); d = ImageDraw.Draw(im); x = 0
    for ch in s:
        col = fill(ch) if callable(fill) else fill
        d.text((x, size * 0.15), ch, font=f, fill=col + (255,)); x += f.getlength(ch) + spacing
    return im


def warp(img, s, tx, ty, W, H, border=cv2.BORDER_REPLICATE):
    M = np.float32([[s, 0, tx], [0, s, ty]])
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=border)


_paper = {}
def paper(W, H, u, kind):
    k = (W, H, kind)
    if k not in _paper:
        bg = np.ones((H, W, 3), np.float32) * np.float32(CREAM_BG) / 255
        step = int(24 * u)
        if kind == 'grid':
            for x in range(0, W, step): bg[:, x:x + max(1, int(u))] *= 0.955
            for y in range(0, H, step): bg[y:y + max(1, int(u)), :] *= 0.955
        else:
            for y in range(step // 2, H, step):
                for x in range(step // 2, W, step): cv2.circle(bg, (x, y), max(1, int(1.2 * u)), (0.85, 0.83, 0.79), -1)
        _paper[k] = bg
    return _paper[k]


def split_layout(c, e, panel, kind):
    """A panel on top, you in a rounded card below — your head pops out over the card's top edge."""
    W, H = c.W, c.H; u = W / 720; k = ease_out(c.lt / 0.35)
    orig = c.img.copy()
    top = 650 * u; x0, x1 = 28 * u, W - 28 * u; r = 40 * u
    s = cached(e, 'sc', lambda: clamp(W * 0.21 / max(c.fw, 1), 0.95, 1.7))
    tx = W / 2 - s * c.fx; ty = top + 70 * u - s * c.fy
    vid = warp(c.img, s, tx, ty, W, H); m = warp(c.m, s, tx, ty, W, H, cv2.BORDER_CONSTANT)
    out = paper(W, H, u, kind).copy()
    lay = Image.new('RGBA', (W, int(top)), (0, 0, 0, 0)); panel(lay, u)
    pa = to_np(lay); dy = int(-(1 - k) * top * 0.5)
    L = pa[-dy:] if dy < 0 else pa
    h_ = L.shape[0]; a = L[..., 3:4] * k
    out[:h_] = out[:h_] * (1 - a) + L[..., :3] * a
    cm = cached(e, 'cm', lambda: np.asarray(rrect(x1 - x0, H - top + r, r, (255, 255, 255, 255)).split()[3], np.float32)[:int(H - top), :int(x1 - x0)] / 255)
    reg = out[int(top):int(top) + cm.shape[0], int(x0):int(x0) + cm.shape[1]]
    reg[:] = reg * (1 - cm[..., None]) + vid[int(top):int(top) + cm.shape[0], int(x0):int(x0) + cm.shape[1]] * cm[..., None]
    band = int(top) - int(160 * u)
    pm = m[band:int(top), :, None] * np.linspace(0.0, 1.0, int(top) - band, dtype=np.float32)[:, None, None].clip(0, 1) ** 0.15
    out[band:int(top)] = out[band:int(top)] * (1 - pm) + vid[band:int(top)] * pm
    c.img = orig * (1 - k) + out * k
    c.m = m * k + c.m * (1 - k)


# ---------- kallaway-split: a live chart on top, you below ----------
@effect('kallaway-split', 'a live chart on top, you below')
def fx_kallaway_split(c, e):
    vals = [float(v) for v in e.o.get('vals', '839|596|528|353|213|166|158').split('|')]
    labs = e.o.get('labels', 'Reel 1|Reel 2|Reel 3|Reel 4|Reel 5|Reel 6|Reel 7').split('|')
    vmax = float(e.o.get('axis', 1000)); ticks = 4

    def panel(lay, u):
        d = ImageDraw.Draw(lay); ink = (20, 20, 22, 255); red = (200, 85, 61, 255)
        d.text((44 * u, 82 * u), e.o.get('title', 'My top 7 reels'), font=font('bold', 30 * u), fill=ink)
        d.text((44 * u, 138 * u), 'by', font=font('bold', 34 * u), fill=ink)
        d.text((44 * u + font('bold', 34 * u).getlength('by ') , 132 * u), 'views', font=font('serif', 46 * u), fill=red)
        d.rectangle([42 * u, 182 * u, 212 * u, 186 * u], fill=red)
        gy0, gy1, gx0, gx1 = 246 * u, 546 * u, 90 * u, 684 * u
        for j in range(ticks + 1):
            y = gy1 - (gy1 - gy0) * j / ticks
            d.line([(gx0, y), (gx1, y)], fill=(0, 0, 0, 40), width=max(1, int(u)))
            v_ = vmax * j / ticks; lab = '0' if j == 0 else (f'{v_ / 1000:g}M' if v_ >= 1000 else f'{int(v_)}K')
            d.text((74 * u, y), lab, font=font('mono', 14 * u), fill=(120, 116, 110, 255), anchor='rm')
        avg = sum(vals) / len(vals); ya = gy1 - (gy1 - gy0) * avg / vmax
        for xx in np.arange(gx0, gx1 - 90 * u, 14 * u): d.line([(xx, ya), (xx + 7 * u, ya)], fill=(214, 72, 72, 200), width=max(1, int(1.5 * u)))
        d.text((gx1, ya - 12 * u), f'avg {int(round(avg))}K', font=font('mono', 15 * u), fill=(232, 150, 160, 255), anchor='rm')
        for j, v in enumerate(vals):
            q = ease_out((c.lt - 0.15 - 0.06 * j) / 0.45)
            cx = 129 * u + 85 * u * j; bw = 53 * u; hh = (gy1 - gy0) * v / vmax * q
            if hh > 1:
                d.rounded_rectangle([cx - bw / 2, gy1 - hh, cx + bw / 2, gy1], 5 * u, fill=((242, 196, 109) if j == 0 else (200, 85, 61)) + (255,))
                num = f'{int(round(v * q))}K'
                d.text((cx, gy1 - hh - 6 * u), num, font=font('anton', (36 if j == 0 else 26) * u), fill=ink, anchor='md')
            d.text((cx, 566 * u), labs[j % len(labs)], font=font('uib', 15 * u), fill=(60, 58, 56, 255), anchor='mm')
    split_layout(c, e, panel, 'grid')


# ---------- studio timeline: "Claude renders it" ----------
def studio_timeline(c, e):
    W = c.W; u = W / 720; p = 0.04 + 0.95 * ease_inout(c.lt / max(0.5, e.d))
    thumb = np_thumb(c, int(100 * u), int(176 * u))
    cards = e.cards

    def panel(lay, u):
        d = ImageDraw.Draw(lay)
        f1, f2 = font('uib', 44 * u), font('serif', 50 * u); a, b = 'Claude', ' renders it'
        tw = f1.getlength(a) + f2.getlength(b); x = (W - tw) / 2
        d.text((x, 90 * u), a, font=f1, fill=(22, 20, 20, 255), anchor='lm')
        d.text((x + f1.getlength(a), 92 * u), b, font=f2, fill=ORANGE_ + (255,), anchor='lm')
        X0, Y0, X1, Y1 = 35 * u, 133 * u, 685 * u, 558 * u
        sh = Image.new('RGBA', lay.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle([X0, Y0 + 8 * u, X1, Y1 + 8 * u], 18 * u, fill=(40, 20, 40, 90))
        lay.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14 * u)))
        d.rounded_rectangle([X0, Y0, X1, Y1], 18 * u, fill=(44, 26, 47, 255), outline=(150, 110, 150, 255), width=max(1, int(1.5 * u)))
        for j, col in enumerate([(242, 150, 100), (236, 90, 150), (170, 160, 175)]):
            d.ellipse([(51 + 14 * j) * u, 148 * u, (59 + 14 * j) * u, 156 * u], fill=col + (255,))
        d.text((103 * u, 152 * u), 'CLAUDITING · RENDER', font=font('mono', 14 * u), fill=(242, 170, 120, 255), anchor='lm')
        d.text((669 * u, 152 * u), '4K · 30FPS', font=font('mono', 14 * u), fill=(242, 170, 120, 255), anchor='rm')
        t = thumb.convert('RGBA'); m = Image.new('L', t.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, t.width - 1, t.height - 1], int(8 * u), fill=255); t.putalpha(m)
        lay.alpha_composite(t, (int(49 * u), int(181 * u)))
        tc = f'0:{int(c.t):02d} / 0:{int(e.o.get("clip_len", 10)):02d}'
        d.rounded_rectangle([55 * u, 330 * u, 128 * u, 350 * u], 4 * u, fill=(0, 0, 0, 190))
        d.text((91 * u, 340 * u), tc, font=font('mono', 10 * u), fill=(242, 190, 150, 255), anchor='mm')
        rows = [('cut', 'pauses removed'), ('captions', 'words synced'), ('grade', 'dusk · face lift'), ('effects', '36 loaded'), ('sound', 'soft UI pops')]
        for j, (l, rt) in enumerate(rows):
            y = (196 + 33.2 * j) * u
            d.rounded_rectangle([165 * u, y - 14 * u, 670 * u, y + 14 * u], 6 * u, fill=(62, 40, 66, 255))
            d.text((173 * u, y), l, font=font('mono', 14 * u), fill=(205, 185, 205, 255), anchor='lm')
            if c.lt > 0.08 + 0.1 * j:
                d.text((661 * u, y), rt, font=font('mono', 14 * u), fill=(240, 230, 235, 255), anchor='rm')
                tw2 = font('mono', 14 * u).getlength(rt); tx = 661 * u - tw2 - 26 * u
                tick(d, tx, y - 7 * u, 14 * u, (242, 160, 100, 255), int(2.5 * u))
        d.rounded_rectangle([165 * u, 350 * u, 670 * u, 356 * u], 3 * u, fill=(70, 50, 75, 255))
        lay.alpha_composite(hgrad_pill(max(2, 505 * u * min(1, p + 0.1)), 6 * u, 3 * u, (236, 100, 150), (242, 160, 110)), (int(165 * u), int(350 * u)))
        for j, l in enumerate(['V1 TAKE', 'CAPTIONS', 'GRADE', 'SFX']):
            d.text((49 * u, (389 + 39 * j) * u), l, font=font('mono', 11 * u), fill=(205, 185, 205, 255), anchor='lm')
        fw = (670 - 127) / 8
        for j in range(8):
            th = np_thumb_pil(cards[j % len(cards)], int(fw * u - 3 * u), int(32 * u))
            lay.alpha_composite(th, (int((127 + fw * j) * u), int(373 * u)))
        for a_, b_, txt in [(137, 300, 'one clip'), (311, 431, '36 effects'), (442, 605, 'zero apps')]:
            pill = hgrad_pill((b_ - a_) * u, 24 * u, 5 * u, (238, 120, 160), (242, 165, 120)); lay.alpha_composite(pill, (int(a_ * u), int(416 * u)))
            d.text(((a_ + 9) * u, 428 * u), txt, font=font('mono', 11 * u), fill=(60, 20, 40, 255), anchor='lm')
        for a_, b_, txt, ca, cb in [(137, 387, 'dusk base', (80, 40, 110), (230, 110, 160)), (398, 616, 'moody · face lift', (236, 120, 150), (242, 165, 120))]:
            pill = hgrad_pill((b_ - a_) * u, 24 * u, 5 * u, ca, cb); lay.alpha_composite(pill, (int(a_ * u), int(455 * u)))
            d.text(((a_ + 9) * u, 467 * u), txt, font=font('mono', 11 * u), fill=(255, 240, 245, 255) if a_ == 137 else (60, 20, 40, 255), anchor='lm')
        rng = np.random.default_rng(3)
        for j, xx in enumerate(np.arange(130, 668, 5.2)):
            amp = (3 + 11 * rng.random() * (0.6 + 0.4 * math.sin(j * 0.4))) * u
            d.line([(xx * u, 506 * u - amp), (xx * u, 506 * u + amp)], fill=(205, 175, 205, 255), width=max(1, int(1.6 * u)))
        ph = (127 + (670 - 127) * p) * u
        d.line([(ph, 368 * u), (ph, 525 * u)], fill=(240, 90, 150, 255), width=max(2, int(2.5 * u)))
        d.rounded_rectangle([49 * u, 535 * u, 585 * u, 543 * u], 4 * u, fill=(70, 50, 75, 255))
        lay.alpha_composite(hgrad_pill(max(2, 536 * u * p), 8 * u, 4 * u, (236, 100, 150), (242, 160, 110)), (int(49 * u), int(535 * u)))
        d.text((650 * u, 540 * u), f'{int(p * 100)}%', font=font('uib', 24 * u), fill=(255, 190, 170, 255), anchor='mm')
    split_layout(c, e, panel, 'dots')
fx.studio_timeline = studio_timeline


# ---------- documentary: black-and-white you, stamped words ----------
@effect('documentary', 'black and white you, stamped words')
def fx_documentary(c, e):
    W, H = c.W, c.H; u = W / 720; k = ramp(c, e, 0.12, 0)
    s = float(e.o.get('scale', 0.8)); ty = H * 0.935 - s * H; tx = W * 0.34 - s * c.fx
    c.img = warp(c.img, s, tx, ty, W, H, cv2.BORDER_CONSTANT); c.m = warp(c.m, s, tx, ty, W, H, cv2.BORDER_CONSTANT)
    c.fx, c.fy, c.fw = s * c.fx + tx, s * c.fy + ty, s * c.fw
    ex = tx + s * W  # soften the hard right edge of the shrunk frame
    c.m = c.m * np.clip((ex - np.arange(W, dtype=np.float32)) / (60 * u), 0, 1)[None, :]
    bw = grade(c.img, 'bw'); bw = np.clip(bw * 1.05 + 0.02, 0, 1)
    bg = cached(e, 'bg', lambda: _doc_bg(W, H, u))
    m = c.m[..., None]
    out = bg * (1 - m) + bw * m
    # pink sun behind the head
    sun = cached(e, 'sun', lambda: _sun(int(210 * u)))
    cx, cy = c.fx + 10 * u, c.fy - 40 * u
    oimg = c.img; c.img = out
    place(c, sun, cx, cy, 0.85 + 0.15 * ease_out(c.lt / 0.4), alpha=1.0, behind=True)
    ring = Image.new('RGBA', (int(420 * u), int(420 * u)), (0, 0, 0, 0)); ImageDraw.Draw(ring).ellipse([2, 2, ring.width - 3, ring.height - 3], outline=(255, 150, 190, 150), width=max(1, int(1.3 * u)))
    place(c, ring, cx, cy, 1.0, alpha=1.0, behind=True)
    big = cached(e, 'big', lambda: _outline_word('DAY', int(190 * u)))
    place(c, big, W - big.width / 2 + 30 * u, 1110 * u, alpha=0.5, behind=True)
    big2 = cached(e, 'big2', lambda: _outline_word('EVERY', int(150 * u)))
    place(c, big2, W - big2.width / 2 + 120 * u, 930 * u, alpha=0.32, behind=True)
    out = c.img * np.clip(1 - (np.arange(H, dtype=np.float32)[:, None, None] - H * 0.74) / (H * 0.2), 0.22, 1)
    c.img = oimg * (1 - k) + out * k
    al = fade(c, e, 0.12)
    tag = cached(e, 'tag', lambda: spaced(e.o.get('series', 'A NON-TECHNICAL AI SERIES · DAILY'), 17 * u, 'montb',
                                          lambda ch: (236, 205, 220), 2.6 * u))
    comp(c, tag, 42 * u, 106 * u, al * clamp(c.lt / 0.15), guard=True)
    lines = [('ONE ', 'CLIP.'), ('36 ', 'EFFECTS.'), ('ZERO ', 'APPS.')]
    pinks = {0: 1, 1: None, 2: 0}
    for j, (a, b) in enumerate(lines):
        im = cached(e, ('ln', j), lambda: _two_tone(a, b, int(64 * u), pinks[j]))
        kk = clamp((c.lt - 0.15 - 0.12 * j) / 0.14)
        if kk > 0: place(c, im, 380 * u + im.width / 2, (306 + 80 * j) * u, 1.35 - 0.35 * ease_out(kk), 0, kk * al, guard=True)
    sl = ease_out((c.lt - 0.25) / 0.3)
    nb = cached(e, 'nb', lambda: _name_bar(FULL, u))
    comp(c, nb, -nb.width * (1 - sl), 1013 * u, al)
    hd = cached(e, 'hd', lambda: text_img(e.o.get('handle', HANDLE), 18 * u, 'mont', (215, 210, 215)))
    comp(c, hd, 36 * u, 1072 * u, al * sl, guard=True)
    # follow button + cursor
    at = e.d - 0.45; on = c.lt >= at; bw_, bh_ = 253 * u, 68 * u
    btn = rrect(bw_, bh_, 14 * u, ((255, 255, 255) if on else (10, 149, 246)) + (255,)); bd = ImageDraw.Draw(btn)
    bd.text((bw_ / 2, bh_ / 2), 'Following' if on else 'Follow', font=font('uib', 30 * u), fill=((20, 20, 22) if on else (255, 255, 255)) + (255,), anchor='mm')
    sq = 1 - 0.1 * math.sin(math.pi * clamp((c.lt - at) / 0.25)) if on else 1
    pk = pop(c, 0.35, 0.3)
    if pk > 0: place(c, shadowed(btn, 10, 5, 100), 520 * u, 754 * u, (0.6 + 0.4 * pk) * sq, 0, al, guard=True)
    cur = cached(e, 'cur', lambda: cursor(44 * u))
    q = ease_inout((c.lt - 0.45) / max(0.2, at - 0.55))
    cxp, cyp = 700 * u + (578 * u - 700 * u) * q, 1000 * u + (770 * u - 1000 * u) * q
    if c.lt > 0.45: comp(c, cur, cxp, cyp, al * clamp((c.lt - 0.45) / 0.1))
    bar = int(86 * u); c.img[:bar] *= 0.0; c.img[int(1192 * u):] *= 0.0


def _doc_bg(W, H, u):
    bg = vgrad(W, H, (16, 10, 16), (46, 14, 36))
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    g = np.exp(-(((xx - W * 0.62) / (W * 0.55)) ** 2 + ((yy - H * 0.55) / (H * 0.35)) ** 2))[..., None]
    bg = np.clip(bg + g * np.float32([0.16, 0.02, 0.10]), 0, 1)
    step = int(40 * u)
    for x in range(0, W, step): bg[:, x:x + 1] += 0.015
    for y in range(0, H, step): bg[y:y + 1] += 0.015
    return np.clip(bg, 0, 1)


def _sun(r):
    s = int(r * 2.6); im = Image.new('RGBA', (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c0 = s / 2
    glow = Image.new('RGBA', (s, s), (0, 0, 0, 0)); ImageDraw.Draw(glow).ellipse([c0 - r * 1.1, c0 - r * 1.1, c0 + r * 1.1, c0 + r * 1.1], fill=(236, 72, 140, 170))
    im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(r * 0.22)))
    yy, xx = np.mgrid[0:s, 0:s].astype(np.float32); dd = np.sqrt((xx - c0) ** 2 + (yy - c0) ** 2) / r
    col = np.float32([236, 72, 140]) * (1 - 0.25 * np.clip(dd, 0, 1))[..., None] + np.float32([30, 0, 20]) * np.clip(dd, 0, 1)[..., None]
    a = (np.clip((1 - dd) * r, 0, 1) * 255)[..., None]
    disc = Image.fromarray(np.concatenate([np.clip(col, 0, 255), a], 2).astype(np.uint8), 'RGBA')
    im.alpha_composite(disc)
    return im


def _outline_word(s, size):
    f = font('anton', size); bb = f.getbbox(s); im = Image.new('RGBA', (bb[2] + 20, bb[3] + 20), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((10 - bb[0], 10), s, font=f, fill=(0, 0, 0, 0), stroke_width=max(1, size // 70), stroke_fill=(120, 80, 110, 255))
    return im


def _two_tone(a, b, size, pink_idx):
    f = font('anton', size); w = int(f.getlength(a) + f.getlength(b)) + 12
    im = Image.new('RGBA', (w, int(size * 1.35)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    cols = [(244, 240, 236), (244, 240, 236)]
    if pink_idx is not None: cols[pink_idx] = (255, 110, 170)
    d.text((4, size * 0.1), a, font=f, fill=cols[0] + (255,)); d.text((4 + f.getlength(a), size * 0.1), b, font=f, fill=cols[1] + (255,))
    return shadowed(im, 8, 4, 120)


def _name_bar(name, u):
    t = spaced(name, 25 * u, 'montb', (255, 255, 255), 1.4 * u)
    w = max(int(395 * u), t.width + int(70 * u)); h = int(47 * u)
    im = Image.new('RGBA', (w, h), (225, 70, 130, 255)); im.alpha_composite(t, (int(40 * u), int((h - t.height) / 2 + 2 * u)))
    return im


if __name__ == '__main__':
    fx.main()
