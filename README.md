# Tonyvideo

团队视频仓库。Claude 写动画、渲染、自检后，把成片推到这里；大白审，Muse 下载后发 YouTube / Pinterest。

- `videos/Txx-标题/`：每条视频一个文件夹，内有 `.mp4` 成片、封面帧 `.png`、源码 `.html`、`分镜.md`（含事实来源）。
- `tools/render.py`：渲染脚本（HTML 画布 → MP4，需要 Python Playwright + Chromium + ffmpeg）。
- `videos/test/`：管线测试文件，不发布。

规矩：画面里不加可见的 AI 标注，文件元数据保留 AI 来源说明；不编造事实；不使用别人的角色、商标和作品。
