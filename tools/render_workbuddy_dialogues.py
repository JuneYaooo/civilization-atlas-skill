#!/usr/bin/env python3
"""Encode reviewed WorkBuddy screenshots into GIF previews and pausable videos.

Requires Pillow and ffmpeg. Input: CASE/NNN.jpg, in display order.
No UI content is generated: labels are placed outside the original screenshot.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageStat

CASES = {'housing': '买房 · 现在买还是再等等', 'ai': '学习 · AI 时代该学什么',
         'restaurant': '开店 · 冲击来时怎样留退路'}

def distinct(paths):
    kept, previous = [], None
    for path in paths:
        with Image.open(path) as image:
            if image.size != (1200, 800):
                raise ValueError(f'Unexpected capture size: {path.name}')
            # Ignore animated window chrome when dropping repeated bottom frames.
            body = image.convert('RGB').crop((218, 56, 975, 623))
        if previous is not None:
            delta = sum(ImageStat.Stat(ImageChops.difference(body, previous)).mean) / 3
            if delta < 0.5:
                continue
        kept.append(path)
        previous = body
    return kept

def compose(path, label, index, count, font_path):
    with Image.open(path) as source:
        image = Image.new('RGB', (1200, 880), '#101923')
        image.paste(source.convert('RGB'), (0, 80))
    draw = ImageDraw.Draw(image)
    title = ImageFont.truetype(font_path, 25)
    caption = ImageFont.truetype(font_path, 16)
    draw.text((24, 10), label, font=title, fill='#eef5fb')
    draw.text((24, 46), '真实截图序列 · 提问 / 初答 / 追加复核 · 初答错误见后续纠正', font=caption, fill='#b6c8d8')
    draw.text((1095, 27), f'{index+1:02d}/{count:02d}', font=title, fill='#71dbd0')
    draw.rectangle((0, 76, round(1200 * (index+1)/count), 79), fill='#71dbd0')
    return image

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--font', default='/System/Library/Fonts/Hiragino Sans GB.ttc')
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        parser.error('Input and output must differ')
    manifest = {'capture_month': '2026-10', 'kind': 'ordered_screenshot_sequence',
                'scope': 'Visible dialogue from initial question through final review; collapsed tool logs and separate reports excluded.',
                'cases': {}}
    for case, label in CASES.items():
        paths = distinct(sorted((args.input/case).glob('*.jpg')))
        if len(paths) < 2:
            raise ValueError(f'Not enough captures: {case}')
        output = args.output/case
        frames = output/'frames'
        frames.mkdir(parents=True, exist_ok=True)
        info = []
        gif_frames = []
        durations = [4000 if i in (0, len(paths)-1) else 2200 for i in range(len(paths))]
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            sequence = []
            for i, path in enumerate(paths):
                dst = frames/f'{i:03}.jpg'
                shutil.copyfile(path, dst)
                info.append({'file': f'frames/{dst.name}', 'sha256': hashlib.sha256(dst.read_bytes()).hexdigest()})
                composite = compose(path, label, i, len(paths), args.font)
                composite.save(temp/f'{i:03}.png')
                gif_frames.append(composite.resize((960, 704), Image.Resampling.LANCZOS).quantize(colors=128, method=Image.Quantize.MEDIANCUT))
                sequence.extend([f"file '{i:03}.png'", f'duration {8 if i in (0,len(paths)-1) else 6}'])
            sequence.append(f"file '{len(paths)-1:03}.png'")
            (temp/'frames.txt').write_text('\n'.join(sequence)+'\n')
            gif_frames[0].save(output/'dialogue.gif', save_all=True, append_images=gif_frames[1:],
                               duration=durations, loop=0, optimize=True, disposal=2)
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0',
                            '-i',str(temp/'frames.txt'),'-vf','fps=10','-c:v','libx264','-crf','19',
                            '-pix_fmt','yuv420p','-t',str(6*len(paths)+4),'-movflags','+faststart',str(output/'dialogue.mp4')], check=True)
        manifest['cases'][case] = {'title':label,'frame_count':len(paths),
            'gif_duration_seconds':sum(durations)/1000,'video_nominal_seconds':6*len(paths)+4,
            'frames':info}
        print(case, len(paths), 'frames', flush=True)
    (args.output/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')

if __name__ == '__main__':
    main()
