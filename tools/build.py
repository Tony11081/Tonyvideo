"""Build team videos from a batch config.

Usage: python3 tools/build.py tools/templates/batch-1006.json [ID ...]

For each entry: writes videos/<ID>-<slug>/source.html (engine + config),
renders <ID>-<slug>.mp4 with tools/render.py, saves cover.png and 分镜.md.
"""
import json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE = os.path.join(ROOT, 'tools', 'templates', 'engine.html')
RENDER = os.path.join(ROOT, 'tools', 'render.py')


def board(cfg, total):
    """Storyboard markdown: shots, on-screen text, fact sources."""
    body = cfg.get('body', 12)
    lines = [f"# {cfg['id']} 分镜", "",
             f"- 规格：1080×1920，30 fps，{total:g} 秒；结尾卡 {body:g}–{total:g} 秒，网址停留 8 秒",
             f"- 商品链接（发布时用社媒文案 G 列带 UTM 的版本）：{cfg['url']}"]
    if cfg.get('sourceUrl'):
        lines.append(f"- 事实来源：{cfg['sourceUrl']}（社媒文案 I 列，大白已核）")
    else:
        lines.append("- 事实来源：商品页列出的尺寸（社媒文案 I 列，大白已核）")
    lines += ["", "| 镜号 | 秒 | 画面 | 屏幕文字 |", "|---|---|---|---|"]
    k = cfg['kind']
    if k == 'qa':
        lines.append(f"| 1 | 0–4 | 标签 + 问题 | {cfg['question']} |")
        lines.append(f"| 2 | 3–7 | 代码画的示意（{cfg['visual']}） | — |")
        lines.append(f"| 3 | 4.6–{body:g} | 答案逐行出现 + 来源 | {' / '.join(cfg['answer'])} · {cfg['source']} |")
    elif k == 'product':
        lines.append(f"| 1 | 0–3 | 标签 + 标题 | {cfg['title']} |")
        lines.append(f"| 2 | 2–5 | 卷尺拉出 + 列出的尺寸 | Listed overall dimensions: {cfg['dims']} |")
        lines.append(f"| 3 | 5–{body:g} | 买前检查清单逐条打勾 | {' / '.join(cfg['checks'])} |")
    elif k == 'mirror':
        lines += ["| 1 | 0–3 | 开场 | Hanging a mirror? Measure first. |",
                  "| 2 | 3–8 | 墙面 + 胶带轮廓动画 | Tape the outline on the wall |",
                  "| 3 | 8–12 | 开关、插座、门扇示意 | Check switches, outlets, door swing |",
                  f"| 4 | 12–{body:g} | 挂件问号 | Ask us about the hanging hardware |"]
    elif k == 'lavender':
        lines += ["| 1 | 0–3 | 开场 + 薰衣草示意 | Lavender seeds are slow. Here's what to expect. |",
                  "| 2 | 3–8 | 土壤剖面，种子 1/8 英寸深 | 1/8 inch deep · Cover lightly — perlite works well |",
                  "| 3 | 8–13 | 温度计 + 日历 14–21 天 | about 70°F · Germination usually begins in 14–21 days · Follow the packet's pre-treatment directions |",
                  f"| 4 | 13–{body:g} | 太阳 + 排水 | Full sun · excellent drainage |"]
    lines.append(f"| 末 | {body:g}–{total:g} | 结尾卡 | {cfg['endKicker']} · {cfg['product']} · {cfg['domain']} |")
    lines += ["", "画面全部由代码绘制：没有商品实拍、没有包装、没有他人作品；商品外观以商品页真实照片为准，发布时可在帖子里另附商品主图。"]
    return '\n'.join(lines) + '\n'


def build(cfg):
    folder = f"{cfg['id']}-{cfg['slug']}"
    out_dir = os.path.join(ROOT, 'videos', folder)
    os.makedirs(out_dir, exist_ok=True)
    html = open(ENGINE, encoding='utf-8').read()
    html = html.replace('/*CONFIG*/null/*END*/', '/*CONFIG*/' + json.dumps(cfg, ensure_ascii=False) + '/*END*/')
    src = os.path.join(out_dir, 'source.html')
    open(src, 'w', encoding='utf-8').write(html)
    mp4 = os.path.join(out_dir, folder + '.mp4')
    subprocess.run([sys.executable, RENDER, src, mp4, '30'], check=True)
    body = cfg.get('body', 12)
    total = body + cfg.get('endHold', 8)
    cover_t = 6 if cfg['kind'] != 'lavender' else 10
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', str(cover_t), '-i', mp4,
                    '-frames:v', '1', os.path.join(out_dir, 'cover.png')], check=True)
    open(os.path.join(out_dir, '分镜.md'), 'w', encoding='utf-8').write(board(cfg, total))
    return mp4


if __name__ == '__main__':
    batch = json.load(open(sys.argv[1], encoding='utf-8'))
    only = set(sys.argv[2:])
    for cfg in batch:
        if only and cfg['id'] not in only:
            continue
        print(cfg['id'], build(cfg), flush=True)
