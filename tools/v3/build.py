"""Build v3 videos: render (with motion blur), soundtrack + SFX on the beat grid, mux, contact sheet.

Usage: python3 tools/v3/build.py tools/v3/<batch>.json [ID ...] [--stills]
  --stills  only render one frame per beat into a contact sheet (review before the full render)
"""
import base64, io, json, os, shutil, subprocess, sys
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENGINE = os.path.join(ROOT, 'tools', 'v3', 'engine.html')
AUDIO = os.path.join(ROOT, 'tools', 'v3', 'audio.py')
FPS, SUB = 30, 3                       # 3 subframes per frame, 180-degree shutter


def page_for(b, src):
    pg = b.new_page(viewport={'width': 1080, 'height': 1920})
    pg.goto('file://' + src)
    pg.wait_for_function('window.READY === true')
    pg.wait_for_function('document.fonts.ready.then(() => true)')
    return pg


def grab(pg, t):
    d = pg.evaluate(f'(() => {{ draw({t:.6f}); return c.toDataURL("image/png"); }})()')
    return Image.open(io.BytesIO(base64.b64decode(d.split(',')[1]))).convert('RGB')


def storyboard(cfg):
    """分镜.md: what is on screen in each 2-second bar and where every fact comes from."""
    hook = ' / '.join(h['text'] for h in cfg['hook'])
    rows = [('0–2 s', '第 0 帧商品全屏；问题逐词出现', hook)]
    if cfg['template'] == 'fit':
        m = cfg['measure']
        rows += [('2–4 s', '量尺横过真实商品', (m.get('text') or f"{m['value']} {m['unit']}") + ' · ' + m['caption']),
                 ('4–6 s', f"轮廓飞出：{cfg['scene']['type']}", cfg['scene']['caption'] + (' · ' + cfg['scene']['label'] if cfg['scene'].get('label') else '')),
                 ('6–8 s', '两条提醒 + 细节放大', ' / '.join(cfg['checks'])),
                 ('8–10 s', '主图', cfg['product'] + ' · Listed: ' + cfg['dims'])]
    else:
        for i, s in enumerate(cfg['scenes']):
            rows.append((f'{2 + 2 * i}–{4 + 2 * i} s', f"事实画面：{s['type']}", ' · '.join(v for v in (s['title'], s.get('sub'), s.get('note')) if v)))
        rows.append(('8–10 s', '主图', cfg['payoff'] + ' · ' + cfg['product']))
    rows.append(('10–16 s', '网址面板，最后回到第 0 帧（可循环）', cfg['ctaLine'] + ' ' + cfg['domain'] + ' · ' + cfg['ctaNote']))
    out = [f"# {cfg['id']} 分镜（v3，16 秒，1080×1920，30 帧，120 BPM）", '',
           f"事实出处：{cfg.get('facts', '')}", '']
    if cfg.get('source'):
        out += [f"画面来源行：{cfg['source']}", '']
    out += ['| 时间 | 画面 | 屏幕文字 |', '|---|---|---|'] + [f'| {a} | {b} | {c} |' for a, b, c in rows]
    out += ['', f"素材：{cfg.get('image')}（我方商品图）。音乐和音效：本机原创合成（{cfg['music']['style']}，seed {cfg['music']['seed']}），−14 LUFS。"]
    return '\n'.join(out) + '\n'


def build(cfg, stills=False):
    folder = f"{cfg['id']}-{cfg['slug']}"
    out_dir = os.path.join(ROOT, 'videos', folder)
    os.makedirs(out_dir, exist_ok=True)
    html = open(ENGINE, encoding='utf-8').read().replace('/*CONFIG*/null/*END*/', json.dumps(cfg, ensure_ascii=False))
    src = os.path.join(out_dir, 'source.html')
    open(src, 'w', encoding='utf-8').write(html)
    if cfg.get('image'):
        shutil.copy(os.path.join(ROOT, 'assets', 'products', cfg['image']), out_dir)
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--allow-file-access-from-files'])
        pg = page_for(b, src)
        dur = pg.evaluate('window.DURATION'); beat = 60 / cfg.get('bpm', 120)
        events = pg.evaluate('(() => { draw(0); return window.EVENTS; })()')
        if stills:
            n = int(round(dur / beat))
            ims = [grab(pg, k * beat + beat * 0.6).resize((216, 384)) for k in range(n)]
            cols = 8; rows = (n + cols - 1) // cols
            sheet = Image.new('RGB', (216 * cols, 384 * rows), 'white')
            for i, im in enumerate(ims):
                sheet.paste(im, ((i % cols) * 216, (i // cols) * 384))
            path = os.path.join(out_dir, 'contact-sheet.png'); sheet.save(path); b.close()
            return path
        silent = os.path.join(out_dir, '_silent.mp4')
        ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                               '-s', '1080x1920', '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                               '-crf', '17', '-preset', 'slow', silent], stdin=subprocess.PIPE)
        n = int(round(dur * FPS))
        for i in range(n):
            acc = np.zeros((1920, 1080, 3), np.float32)
            for k in range(SUB):
                t = (i + (k - (SUB - 1) / 2) * 0.5 / SUB) / FPS
                acc += np.asarray(grab(pg, max(0.0, min(dur - 1e-4, t))), np.float32)
            ff.stdin.write((acc / SUB).astype(np.uint8).tobytes())
        ff.stdin.close(); ff.wait(); b.close()
    evf = os.path.join(out_dir, '_events.json'); json.dump(events, open(evf, 'w'))
    wav = os.path.join(out_dir, '_audio.wav')
    m = cfg['music']
    subprocess.run([sys.executable, AUDIO, m['style'], str(cfg.get('bpm', 120)), str(cfg.get('beats', 32)), str(m['seed']), evf, wav], check=True)
    mp4 = os.path.join(out_dir, folder + '.mp4')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', silent, '-i', wav, '-map', '0:v', '-map', '1:a',
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-af', 'loudnorm=I=-14:TP=-1.5:LRA=9', '-ar', '44100',
                    '-shortest', '-movflags', '+faststart',
                    '-metadata', 'comment=Product images from our listings; original synthesized music and SFX', mp4], check=True)
    for f in (silent, wav, evf):
        os.remove(f)
    open(os.path.join(out_dir, '分镜.md'), 'w', encoding='utf-8').write(storyboard(cfg))
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', '9', '-i', mp4, '-frames:v', '1', os.path.join(out_dir, 'cover.png')], check=True)
    return mp4


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    stills = '--stills' in sys.argv
    batch = json.load(open(args[0], encoding='utf-8'))
    only = set(args[1:])
    for cfg in batch:
        if only and cfg['id'] not in only:
            continue
        print(cfg['id'], build(cfg, stills), flush=True)
