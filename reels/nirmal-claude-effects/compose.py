#!/usr/bin/env python3
"""Builds Nirmal's reel: an animated Claude phone screen typing /effects commands,
the effect renders (renders/runA.mp4, runB.mp4), and the Comment "claude" end card.

All layout numbers are in a 720x1280 frame (the reference's size) and scaled by U.
"""
import glob, math, os, subprocess, sys, wave
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BUILD = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BUILD)
import myfx
fx = myfx.fx
FONTS = os.path.join(BUILD, '..', '..', '.claude', 'skills', 'effects', 'fonts')
SRC = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(BUILD, 'nirmal.mp4')
OUT = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else os.path.join(BUILD, 'nirmal_claude_effects.mp4')
W, H, U, FPS, T_END = 1080, 1920, 1.5, 30, 25.8
NAME = 'Nirmal'

BG, CHIP, SEG_ON = (37, 37, 34), (47, 47, 44), (73, 71, 67)
KB, KB_LINE, KEY, KEY_D, KEY_POP = (27, 27, 24), (38, 38, 35), (73, 71, 67), (52, 50, 48), (106, 104, 100)
ORANGE, ORANGE_TXT, BUBBLE, BUBBLE_TXT = (217, 119, 87), (233, 128, 95), (58, 40, 33), (240, 129, 96)
GRAY, DIM, PH, WHITE, ICON = (168, 166, 160), (126, 126, 121), (128, 126, 120), (244, 242, 238), (170, 168, 162)
CARD = (24, 368, 450, 1126)

# name, menu description, compose C, send S, full-screen F, next N, render run, source offset a
CYC = [('glass-widgets', 'frosted glass widgets around your head', 0.00, 1.00, 2.20, 3.20, 'A', 0.20),
       ('documentary', 'black and white you, stamped words', 3.20, 4.15, 5.20, 6.20, 'A', 2.80),
       ('orbit', 'your reels circle your head', 6.20, 7.15, 8.40, 9.45, 'A', 5.20),
       ('kallaway-split', 'a live chart on top, you below', 9.45, 10.20, 11.45, 12.45, 'A', 7.75),
       ('spotlight', 'kill the lights, keep you lit', 12.45, 13.20, 14.45, 15.45, 'B', 0.50),
       ('checklist', 'Claude ticks off every step', 15.45, 16.40, 17.70, 18.45, 'B', 3.10),
       ('timeline', 'Claude renders the whole edit', 18.45, 19.45, 20.70, 21.45, 'B', 5.50)]
C8, S8, STREAM, DOTS8, GROW8 = 21.45, 22.15, (22.35, 22.85), 22.9, (23.68, 23.9)
REPLY = 'Comment “claude” and I’ll send you all 36 effects'
GRID = ['glass-widgets', 'orbit', 'spotlight', 'lineup', 'shortcut-rain', 'checklist', 'timeline', 'red-collage', 'comment-box', 'cover-star',
        'headline-wall', 'phone-fan', 'rabbit-hole', 'profile-wall', 'noise', 'the-bill', 'split-headline', 'pastel-word', 'tier-list']

_fc = {}
def F(size, w=500, kind='inter'):
    k = (size, w, kind)
    if k not in _fc:
        path = {'inter': 'Inter.ttf', 'mono': 'SpaceMono-Bold.ttf', 'serif': 'PlayfairDisplay.ttf'}[kind]
        f = ImageFont.truetype(os.path.join(FONTS, path), max(6, int(round(size * U))))
        if kind == 'inter': f.set_variation_by_axes([min(32, max(14, size)), w])
        elif kind == 'serif': f.set_variation_by_axes([w])
        _fc[k] = f
    return _fc[k]


class Pen:
    """ImageDraw in 720-wide coordinates."""
    def __init__(s, im): s.im = im; s.d = ImageDraw.Draw(im)
    def rr(s, x0, y0, x1, y1, r, fill=None, outline=None, width=1):
        s.d.rounded_rectangle([x0 * U, y0 * U, x1 * U, y1 * U], r * U, fill=fill, outline=outline, width=max(1, int(width * U)))
    def t(s, x, y, txt, size, fill, w=500, kind='inter', anchor='lm'):
        s.d.text((x * U, y * U), txt, font=F(size, w, kind), fill=fill, anchor=anchor)
    def tl(s, txt, size, w=500, kind='inter'): return F(size, w, kind).getlength(txt) / U
    def line(s, pts, fill, width, caps=True):
        P = [(x * U, y * U) for x, y in pts]; wd = max(1, int(round(width * U)))
        s.d.line(P, fill=fill, width=wd, joint='curve')
        if caps:
            for x, y in (P[0], P[-1]): s.d.ellipse([x - wd / 2, y - wd / 2, x + wd / 2, y + wd / 2], fill=fill)
    def ell(s, cx, cy, r, fill=None, outline=None, width=1):
        s.d.ellipse([(cx - r) * U, (cy - r) * U, (cx + r) * U, (cy + r) * U], fill=fill, outline=outline, width=max(1, int(width * U)))


def cover(img, w, h, y_bias=0.3):
    s = max(w / img.width, h / img.height); im = img.resize((max(w, round(img.width * s)), max(h, round(img.height * s))), Image.LANCZOS)
    l, t = (im.width - w) // 2, int((im.height - h) * y_bias)
    return im.crop((l, t, l + w, t + h))


def paste_round(base, img, x, y, w, h, r):
    X, Y, Wd, Hd = round(x * U), round(y * U), max(1, round(w * U)), max(1, round(h * U))
    im = img if img.size == (Wd, Hd) else img.resize((Wd, Hd), Image.BILINEAR)
    m = Image.new('L', (Wd, Hd), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, Wd - 1, Hd - 1], max(0, int(r * U)), fill=255)
    base.paste(im, (X, Y), m)


def star(p, cx, cy, r, col=ORANGE):
    for i in range(12):
        a = i * math.pi / 6 + 0.1
        rr = r * (1.0 if i % 2 == 0 else 0.8)
        p.line([(cx + math.cos(a) * r * 0.12, cy + math.sin(a) * r * 0.12), (cx + math.cos(a) * rr, cy + math.sin(a) * rr)], col, r * 0.2)


def arrow_up(p, cx, cy, s, col, w):
    p.line([(cx, cy + s), (cx, cy - s)], col, w); p.line([(cx - s * 0.85, cy - s * 0.15), (cx, cy - s), (cx + s * 0.85, cy - s * 0.15)], col, w)


def mic(p, cx, cy, col):
    p.rr(cx - 5, cy - 12, cx + 5, cy + 4, 5, outline=col, width=2)
    p.d.arc([(cx - 10) * U, (cy - 6) * U, (cx + 10) * U, (cy + 10) * U], 10, 170, fill=col, width=int(2 * U))
    p.line([(cx, cy + 10), (cx, cy + 15)], col, 2)


# ---------- screen pieces ----------
def topbar(p):
    p.ell(60, 83, 28, fill=CHIP); p.line([(51, 79), (69, 79)], (225, 223, 218), 2.4); p.line([(51, 87), (63, 87)], (225, 223, 218), 2.4)
    p.rr(248, 56, 471, 111, 27.5, fill=CHIP); p.rr(357, 61, 466, 106, 22.5, fill=SEG_ON)
    p.t(305, 84, 'Chat', 24, (150, 148, 143), 560, anchor='mm'); p.t(411, 84, 'Code', 24, (250, 248, 244), 640, anchor='mm')
    p.ell(660, 83, 28, fill=CHIP)
    p.line([(664, 75), (652, 75), (652, 92), (669, 92), (669, 80)], (225, 223, 218), 2, caps=False)
    p.line([(659, 86), (670, 74)], (225, 223, 218), 2.2)


def composer(p, base, text, thumb, cursor_on, pressed_send=False):
    top = 542 if thumb is not None else 670
    p.rr(20, top, 700, 812, 28, fill=CHIP)
    if thumb is not None:
        paste_round(base, thumb, 40, 559, 80, 112, 10)
        p.ell(106, 572, 10, fill=(250, 250, 250)); p.line([(102.5, 568.5), (109.5, 575.5)], (20, 20, 20), 2); p.line([(109.5, 568.5), (102.5, 575.5)], (20, 20, 20), 2)
    ty = 706
    if text:
        col = ORANGE_TXT if text.startswith('/effects ') else (240, 238, 234)
        p.t(40, ty, text, 30, col, 460); cx = 40 + p.tl(text, 30, 460) + 2
    else:
        p.t(40, ty, 'Reply to Claude...', 30, PH, 460); cx = 40
    if cursor_on: p.rr(cx, ty - 17, cx + 2.4, ty + 17, 1, fill=ORANGE)
    p.line([(45, 768), (63, 768)], ICON, 2.2); p.line([(54, 759), (54, 777)], ICON, 2.2)
    p.line([(93, 762), (115, 762)], ICON, 2); p.line([(93, 774), (115, 774)], ICON, 2)
    p.ell(100, 762, 3.6, fill=CHIP, outline=ICON, width=2); p.ell(108, 774, 3.6, fill=CHIP, outline=ICON, width=2)
    mic(p, 592, 766, ICON)
    p.rr(624, 740, 680, 796, 14, fill=(190, 100, 72) if pressed_send else ORANGE)
    arrow_up(p, 652, 768, 11, (255, 255, 255), 3)


def slash_menu(p, items):
    n = len(items); top = 530 - (14 + 86 * n)
    p.rr(20, top, 700, 530, 22, fill=CHIP)
    for j, (title, sub) in enumerate(items):
        y = top + 38 + 86 * j
        p.t(46, y, title, 25, (246, 244, 240), 640); p.t(46, y + 29, sub, 18.5, (165, 163, 157), 430)


ROWS = ['qwertyuiop', 'asdfghjkl', 'zxcvbnm']
KEYS = {}
for i, ch in enumerate(ROWS[0]): KEYS[ch] = (11 + i * 70.6, 902, 73 + i * 70.6, 980)
for i, ch in enumerate(ROWS[1]): KEYS[ch] = (46 + i * 70.6, 995, 108 + i * 70.6, 1073)
for i, ch in enumerate(ROWS[2]): KEYS[ch] = (117 + i * 70.6, 1089, 179 + i * 70.6, 1167)
KEYS.update({'shift': (24, 1089, 108, 1167), 'back': (612, 1089, 696, 1167), '123': (62, 1182, 195, 1260), ' ': (204, 1182, 516, 1260), '/': (525, 1182, 658, 1260)})


def keyboard(p, sugg, pop):
    p.d.rectangle([0, 828 * U, W, H], fill=KB)
    p.d.rectangle([0, 885 * U, W, 887 * U], fill=KB_LINE)
    if sugg is not None: p.t(123, 857, f'“{sugg}”', 22, (205, 203, 198), 450, anchor='mm')
    for k, (x0, y0, x1, y1) in KEYS.items():
        dark = k in ('shift', 'back', '123', '/')
        p.rr(x0, y0, x1, y1, 9, fill=KEY_D if dark else KEY)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if len(k) == 1 and k not in ' /': p.t(cx, cy - 2, k, 31, (242, 242, 238), 420, anchor='mm')
        elif k == '/': p.t(cx, cy, '/', 25, (242, 242, 238), 420, anchor='mm')
        elif k == ' ': p.t(cx, cy, 'space', 22, (242, 242, 238), 450, anchor='mm')
        elif k == '123': p.t(cx, cy, '123', 22, (242, 242, 238), 450, anchor='mm')
        elif k == 'shift':
            p.line([(cx - 9, cy + 1), (cx, cy - 9), (cx + 9, cy + 1), (cx + 4.5, cy + 1), (cx + 4.5, cy + 8), (cx - 4.5, cy + 8), (cx - 4.5, cy + 1), (cx - 9, cy + 1)], (242, 242, 238), 1.8, caps=False)
        elif k == 'back':
            p.line([(cx - 13, cy), (cx - 6, cy - 8), (cx + 12, cy - 8), (cx + 12, cy + 8), (cx - 6, cy + 8), (cx - 13, cy)], (242, 242, 238), 1.8, caps=False)
            p.line([(cx - 1, cy - 4), (cx + 7, cy + 4)], (242, 242, 238), 1.8); p.line([(cx + 7, cy - 4), (cx - 1, cy + 4)], (242, 242, 238), 1.8)
    if pop and pop in KEYS:
        x0, y0, x1, y1 = KEYS[pop]
        p.rr(x0 - 12, y0 - 79, x1 + 12, y1, 12, fill=KEY_POP)
        p.t((x0 + x1) / 2, y0 - 30, pop, 44, (250, 250, 246), 420, anchor='mm')


def reply_bar(p):
    p.rr(20, 1177, 700, 1253, 38, fill=CHIP)
    p.line([(49, 1216), (63, 1216)], (150, 148, 143), 2); p.line([(56, 1209), (56, 1223)], (150, 148, 143), 2)
    p.t(80, 1216, 'Reply to Claude...', 29, (130, 128, 122), 450)
    mic(p, 602, 1212, (150, 148, 143))
    p.ell(661, 1214, 27, fill=(64, 63, 60)); arrow_up(p, 661, 1214, 11, (200, 198, 192), 2.8)


def sped_up(p, x1, y):
    f = F(14, kind='mono'); s = 'SPED UP'; sp = 3.2
    w = sum(f.getlength(ch) / U + sp for ch in s) - sp; x = x1 - w
    for ch in s: p.t(x, y, ch, 14, DIM, kind='mono'); x += f.getlength(ch) / U + sp


def sent_ui(p, base, cmd, effname, thumb_b, alpha=1.0):
    paste_round(base, thumb_b, 611, 133, 73, 116, 9)
    tw = p.tl(cmd, 26, 460); x1 = 684; x0 = x1 - tw - 42
    p.rr(x0, 264, x1, 313, 24.5, fill=BUBBLE); p.t(x0 + 21, 289, cmd, 26, BUBBLE_TXT, 460)
    star(p, 50, 341, 13); p.t(79, 341, f'Editing with {effname}...', 24, GRAY, 450); sped_up(p, 683, 341)
    reply_bar(p)


# ---------- media ----------
def read_all(path):
    cap = cv2.VideoCapture(path); fr = []
    while True:
        ok, f = cap.read()
        if not ok: break
        fr.append(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
    cap.release(); return fr


def still(path, t):
    cap = cv2.VideoCapture(path); cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000); ok, f = cap.read(); cap.release()
    return Image.fromarray(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))


class E: pass


def dot_reveal(img_u8, lt, d, e):
    """The skill's dot-reveal effect, run on a card-sized frame."""
    c = E(); c.H, c.W = img_u8.shape[:2]; c.img = img_u8.astype(np.float32) / 255; c.lt = lt
    e.d = d; fx.fx_dot_reveal(c, e)
    return (np.clip(c.img, 0, 1) * 255).astype(np.uint8)


def new_e():
    e = E(); e.o = {}; e.state = {}; return e


def end_card(tiles):
    im = Image.new('RGB', (W, H), (38, 36, 34)); p = Pen(im)
    p.t(360, 128, 'Comment “claude”', 58, (250, 248, 244), 720, anchor='mm')
    s = 'for all 36 Claude effects'; tw = p.tl(s, 25, 650)
    p.rr(360 - tw / 2 - 24, 180, 360 + tw / 2 + 24, 225, 8, fill=ORANGE); p.t(360, 202.5, s, 25, (35, 22, 15), 650, anchor='mm')
    for k in range(20):
        x, y = 32 + 133 * (k % 5), 259 + 230 * (k // 5)
        if k == 19:
            p.rr(x, y, x + 124, y + 218, 7, fill=(50, 35, 30), outline=(170, 95, 70), width=1.3)
            p.t(x + 62, y + 97, '+17', 40, ORANGE, 760, anchor='mm'); p.t(x + 62, y + 133, 'more effects', 18, (225, 205, 195), 520, anchor='mm')
            continue
        t = cover(tiles[k], round(124 * U), round(218 * U), 0.25).convert('RGBA')
        g = np.zeros((t.height, t.width, 4), np.uint8); ramp_ = np.clip((np.arange(t.height) - t.height * 0.78) / (t.height * 0.22), 0, 1)
        g[..., 3] = (ramp_ * 190)[:, None]; t.alpha_composite(Image.fromarray(g, 'RGBA'))
        paste_round(im, t.convert('RGB'), x, y, 124, 218, 7)
        p.ell(x + 16, y + 17, 12.5, fill=ORANGE); p.t(x + 16, y + 17.5, str(k + 1), 14, (40, 20, 10), 720, anchor='mm')
        p.t(x + 6, y + 207, '/' + GRID[k], 12.5, (250, 250, 250), kind='mono', anchor='ls')
    return im


# ---------- timeline ----------
def type_steps(C, S, name, first):
    base = [(0.05, '/', '/'), (0.17, '/e', 'e'), (0.29, '/ef', 'f'), (0.41, '/effects ', None),
            (0.53, '/effects ' + name[0], name[0]), (0.65, '/effects ' + name[:2], name[1]), (0.77, '/effects ' + name, None)]
    k = min(1.0, (S - C - 0.1) / 0.77)
    t0 = C - (0.05 if first else 0)
    return [(t0 + dt * k, txt, key) for dt, txt, key in base]


def menu_for(text, name, desc):
    if text == '/': return [('/effects', '36 video effects for your clips'), ('/init', 'set up Claude in this folder'), ('/review', 'review my latest changes')]
    if text in ('/e', '/ef'): return [('/effects', '36 video effects for your clips')]
    if text.startswith('/effects ') and 0 < len(text) - 9 < len(name): return [(name, desc)]
    return []


def main():
    os.chdir(BUILD)
    runs = {'A': read_all('renders/runA.mp4'), 'B': read_all('renders/runB.mp4')}
    sfps = 30000 / 1001
    th0 = still(SRC, 0.6)
    thumb_c = cover(th0, round(80 * U), round(112 * U), 0.15); thumb_b = cover(th0, round(73 * U), round(116 * U), 0.15)
    tiles = [Image.open(f).convert('RGB') for g in ('g1', 'g2', 'g3') for f in sorted(glob.glob(f'grid/{g}_*.png'))]
    assert len(tiles) == 19, len(tiles)
    END = end_card(tiles); END_np = np.asarray(END)
    END.save('end_card.png')
    cw, ch = round((CARD[2] - CARD[0]) * U), round((CARD[3] - CARD[1]) * U)
    E8 = (24, 293, 446, 1043); cw8, ch8 = round((E8[2] - E8[0]) * U), round((E8[3] - E8[1]) * U)
    END_small = cv2.resize(END_np, (cw8, ch8), interpolation=cv2.INTER_AREA)
    steps = [type_steps(C, S, n, i == 0) for i, (n, _, C, S, *_r) in enumerate(CYC)]
    claude_steps = [(C8 + 0.08 + 0.085 * j, 'claude'[:j + 1], 'claude'[j]) for j in range(6)]
    es = [new_e() for _ in CYC]; e8 = new_e()
    sfx = []
    for st in steps + [claude_steps]:
        for t_, _, key in st:
            if key: sfx.append(('tap', t_))
    for (_, _, C, S, Fs, N, *_r) in CYC: sfx += [('send', S), ('whoosh', Fs - 0.2)]
    sfx += [('send', S8), ('whoosh', GROW8[0])]

    def eff(cyc, t):
        name, _, C, S, Fs, N, run, a = cyc; fr = runs[run]
        return fr[min(len(fr) - 1, int(round((a + (t - S)) * sfps)))]

    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                            '-c:v', 'libx264', '-crf', '17', '-preset', 'medium', '-pix_fmt', 'yuv420p', 'video_only.mp4'], stdin=subprocess.PIPE)
    n = int(round(T_END * FPS))
    for i in range(n):
        t = i / FPS
        frame = None
        if t < C8:
            ci = max(j for j, c in enumerate(CYC) if c[2] <= t + 1e-6)
            cyc = CYC[ci]; name, desc, C, S, Fs, N, run, a = cyc
            if t >= Fs:
                frame = eff(cyc, t)
            else:
                im = Image.new('RGB', (W, H), BG); p = Pen(im); topbar(p)
                if t < S:
                    done = [s for s in steps[ci] if s[0] <= t]
                    text = done[-1][1] if done else ''
                    pop = next((k for (t_, _, k) in reversed(done) if k and t - t_ < 0.11), None)
                    menu = menu_for(text, name, desc)
                    if menu: slash_menu(p, menu)
                    composer(p, im, text, thumb_c, (int(t * 2.2) % 2 == 0) or bool(done and t - done[-1][0] < 0.4), pressed_send=S - t < 0.08)
                    word = text.split(' ')[-1].lstrip('/') if text else None
                    keyboard(p, word if text else None, pop)
                else:
                    sent_ui(p, im, '/effects ' + name, name, thumb_b)
                    g0 = Fs - 0.22
                    src = eff(cyc, t)
                    if t < g0:
                        small = cv2.resize(src, (cw, ch), interpolation=cv2.INTER_AREA)
                        if t - S < 0.85: small = dot_reveal(small, t - S, 0.85, es[ci])
                        paste_round(im, Image.fromarray(small), CARD[0], CARD[1], CARD[2] - CARD[0], CARD[3] - CARD[1], 18)
                    else:
                        q = fx.ease_inout((t - g0) / 0.22)
                        r = [CARD[j] + ((0, 0, 720, 1280)[j] - CARD[j]) * q for j in range(4)]
                        paste_round(im, Image.fromarray(src), r[0], r[1], r[2] - r[0], r[3] - r[1], 18 * (1 - q))
                frame = np.asarray(im)
        elif t >= GROW8[1]:
            frame = END_np
        else:
            im = Image.new('RGB', (W, H), BG); p = Pen(im); topbar(p)
            if t < S8:
                star(p, 360, 325, 30); p.t(360, 408, f'Evening, {NAME}', 46, WHITE, 400, kind='serif', anchor='mm')
                done = [s for s in claude_steps if s[0] <= t]; text = done[-1][1] if done else ''
                pop = next((k for (t_, _, k) in reversed(done) if t - t_ < 0.11), None)
                composer(p, im, text, None, True, pressed_send=S8 - t < 0.08)
                keyboard(p, text if text else None, pop)
            else:
                tw = p.tl('claude', 26, 500); p.rr(684 - tw - 42, 134, 684, 185, 25.5, fill=(55, 53, 49)); p.t(684 - 21, 159.5, 'claude', 26, (246, 244, 240), 500, anchor='rm')
                if t >= STREAM[0]:
                    star(p, 50, 237, 13)
                    nch = int(len(REPLY) * min(1, (t - STREAM[0]) / (STREAM[1] - STREAM[0])))
                    shown = REPLY[:nch]; line1 = 'Comment “claude” and I’ll send you all 36'
                    p.t(79, 237, shown[:len(line1)], 24, (232, 230, 225), 450)
                    if nch > len(line1): p.t(79, 270, shown[len(line1):].strip(), 24, (232, 230, 225), 450)
                if t >= DOTS8:
                    if t < GROW8[0]:
                        small = END_small if t - DOTS8 >= 0.6 else dot_reveal(END_small, t - DOTS8, 0.6, e8)
                        paste_round(im, Image.fromarray(small), E8[0], E8[1], E8[2] - E8[0], E8[3] - E8[1], 18)
                    else:
                        q = fx.ease_inout((t - GROW8[0]) / (GROW8[1] - GROW8[0]))
                        r = [E8[j] + ((0, 0, 720, 1280)[j] - E8[j]) * q for j in range(4)]
                        paste_round(im, END, r[0], r[1], r[2] - r[0], r[3] - r[1], 18 * (1 - q))
                reply_bar(p)
            frame = np.asarray(im)
        enc.stdin.write(np.ascontiguousarray(frame, dtype=np.uint8).tobytes())
        if i % 60 == 0: print(f'  {t:5.1f}s / {T_END}s', flush=True)
    enc.stdin.close(); enc.wait()
    write_sfx('sfx.wav', sfx)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', 'video_only.mp4', '-i', 'sfx.wav', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
                    '-shortest', '-movflags', '+faststart', OUT], check=True)
    print('Done:', OUT)


def write_sfx(path, events, sr=48000):
    rng = np.random.default_rng(7); out = np.zeros(int((T_END + 1) * sr), np.float32)
    def add(sig, t):
        i = int(t * sr); j = min(len(out), i + len(sig)); out[i:j] += sig[:j - i]
    for kind, t in events:
        if kind == 'tap':
            n = int(0.035 * sr); x = rng.normal(size=n).astype(np.float32); x = np.diff(np.concatenate([[0], x]))
            env = np.exp(-np.arange(n) / (0.005 * sr)); body = np.sin(2 * np.pi * 1900 * np.arange(n) / sr) * np.exp(-np.arange(n) / (0.003 * sr))
            add((x * 0.05 + body * 0.12) * env * rng.uniform(0.8, 1.1), t)
        elif kind == 'send':
            tt = np.arange(int(0.11 * sr)) / sr; f = 520 + 1100 * tt / 0.11
            add(np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-tt / 0.035) * 0.28, t)
        elif kind == 'whoosh':
            n = int(0.32 * sr); x = rng.normal(size=n).astype(np.float32)
            x = np.convolve(x, np.ones(24) / 24, 'same'); tt = np.arange(n) / n
            add(x * np.sin(np.pi * tt) ** 2 * 0.35, t)
    out = np.clip(out, -1, 1); st = (np.stack([out, out], 1) * 32767).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr); w.writeframes(st.tobytes())


if __name__ == '__main__':
    main()
