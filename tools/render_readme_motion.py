#!/usr/bin/env python3
"""Render README GIFs from SVG originals. Requires Pillow and rsvg-convert.

Run at repository root: python3 tools/render_readme_motion.py
Motion decorates the diagrams; it does not encode observations over time.
"""
from pathlib import Path
import io
import math
import subprocess
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
WIDTH = 1100
SCALE = WIDTH / 1440
FRAMES = 84
DURATION = 80
CYAN = (96, 244, 229)
BLUE = (119, 149, 255)
RED = (255, 157, 142)


def point(x, y):
    return x * SCALE, y * SCALE


def bezier(points, t):
    p = list(points)
    while len(p) > 1:
        p = [(a[0] * (1-t) + b[0] * t, a[1] * (1-t) + b[1] * t) for a, b in zip(p, p[1:])]
    return p[0]


def orbit(t, rx, ry, angle):
    a = t * math.tau
    rot = math.radians(angle)
    x, y = rx * math.cos(a), ry * math.sin(a)
    return 1060 + x * math.cos(rot) - y * math.sin(rot), 292 + x * math.sin(rot) + y * math.cos(rot)


def trail(layer, path, progress, color, length=.10, radius=3.0, intensity=1):
    draw = ImageDraw.Draw(layer)
    for j in range(35):
        t = progress - length * (1-j/34)
        if not 0 <= t <= 1:
            continue
        x, y = point(*path(t))
        r = SCALE * (radius * (.35 + .65*j/34))
        alpha = int(230 * (j/34)**1.6 * intensity)
        draw.ellipse((x-r, y-r, x+r, y+r), fill=(*color, alpha))


def render(name):
    png = subprocess.check_output(['rsvg-convert', '-w', str(WIDTH), str(ROOT/'assets'/f'{name}.svg')])
    base = Image.open(io.BytesIO(png)).convert('RGBA')
    # A common palette keeps the background and typography stable across frames.
    palette_source = Image.new('RGB', (WIDTH, base.height + 48), (5, 8, 19))
    palette_source.paste(base.convert('RGB'), (0, 0))
    pd = ImageDraw.Draw(palette_source)
    for row, color in enumerate((CYAN, BLUE, RED)):
        for x in range(WIDTH):
            mix = x / (WIDTH-1)
            c = tuple(round(5*(1-mix)+v*mix) for v in color)
            pd.line((x, base.height+row*16, x, base.height+row*16+15), fill=c)
    palette = palette_source.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    frames = []
    curves = [
        [(467,303),(502,273),(530,264)],
        [(907,266),(941,277),(970,302)],
        [(1194,404),(1260,455),(1250,542),(1160,583)],
        [(970,691),(937,719),(911,730)],
        [(530,730),(494,718),(470,696)],
        [(285,583),(181,533),(181,454),(276,407)],
    ]
    for i in range(FRAMES):
        phase = i / FRAMES
        layer = Image.new('RGBA', base.size)
        if name == 'banner':
            for offset, color, rx, ry, angle in [(0,CYAN,322,97,-28),(.5,BLUE,322,97,-28),(.2,BLUE,268,118,36)]:
                # Extend wrapping paths across the loop boundary for an unbroken tail.
                path = lambda t,rx=rx,ry=ry,angle=angle,offset=offset: orbit(t+offset,rx,ry,angle)
                trail(layer, path, phase, color, .13, 4)
                trail(layer, path, phase+1, color, .13, 4)
                if phase < .13:
                    trail(layer, lambda t,p=path:p(t-1), phase+1, color, .13, 4)
        elif name == 'research-flow':
            for j, curve in enumerate(curves):
                progress = (phase*2-j/6) % 1
                fade = min(1, progress/.12, (1-progress)/.12)
                trail(layer, lambda t,c=curve:bezier(c,t), progress, CYAN if j<3 else BLUE, .35, 4, fade)
            # Small circulating dots outside the central text.
            for offset in [0,.5]:
                trail(layer, lambda t,o=offset:(720+159*math.cos(math.tau*(t+o)),485+159*math.sin(math.tau*(t+o))), phase, BLUE,.075,2.2)
        else:
            paths = [([(125,589),(505,411)],CYAN), ([(125,589),(505,451)],BLUE),
                     ([(1134,369),(1300,317)],BLUE), ([(1134,369),(1300,404)],RED),
                     ([(1134,623),(1300,571)],BLUE), ([(1134,623),(1300,658)],RED)]
            for j,(path,color) in enumerate(paths):
                progress=(phase*2) % 1
                fade=min(1,progress/.12,(1-progress)/.15)
                trail(layer,lambda t,p=path:bezier(p,t),progress,color,.20,3,fade)
        glow=layer.filter(ImageFilter.GaussianBlur(5*SCALE))
        frame=Image.alpha_composite(Image.alpha_composite(base,glow),layer).convert('RGB')
        frames.append(frame.quantize(palette=palette,dither=Image.Dither.FLOYDSTEINBERG))
    out=ROOT/'assets'/f'{name}.gif'
    frames[0].save(out,save_all=True,append_images=frames[1:],duration=DURATION,loop=0,optimize=True,disposal=1)
    print(f'{out.name}: {out.stat().st_size/1024:.0f} KiB, {len(frames)} frames')


if __name__ == '__main__':
    for name in ('banner','research-flow','prediction-results'):
        render(name)
