# render.py  用法: python3 render.py /abs/video.html /abs/out.mp4 [fps]
import sys, subprocess, base64
from playwright.sync_api import sync_playwright
html, out = sys.argv[1], sys.argv[2]
fps = int(sys.argv[3]) if len(sys.argv) > 3 else 30
with sync_playwright() as p:
    b = p.chromium.launch(args=['--allow-file-access-from-files'])  # local product images
    pg = b.new_page()
    pg.goto('file://' + html)
    pg.wait_for_function('document.fonts.ready.then(() => true)')
    pg.wait_for_function('window.READY !== false')  # 页面加载素材时先设 READY=false，加载完设 true
    w, h = pg.evaluate('[c.width, c.height]')
    pg.set_viewport_size({'width': w, 'height': h})
    n = int(pg.evaluate('window.DURATION') * fps)
    ff = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', str(fps),
                           '-i', '-', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18',
                           '-movflags', '+faststart',
                           '-metadata', 'comment=Contains AI-generated imagery', out], stdin=subprocess.PIPE)
    for i in range(n):
        d = pg.evaluate(f'(() => {{ draw({i}/{fps}); return c.toDataURL("image/png"); }})()')
        ff.stdin.write(base64.b64decode(d.split(',')[1]))
    ff.stdin.close(); ff.wait(); b.close()
print('frames', n)
