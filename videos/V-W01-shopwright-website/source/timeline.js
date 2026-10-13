// Shared timeline for picture and sound. 120 BPM: one beat = 0.5 s, 48 beats = 24 s.
// Everything on screen and every sound effect is placed from these numbers,
// so the two can never drift apart.
(function (root) {
  const BPM = 120;
  const BEAT = 60 / BPM;
  const b = (beats) => beats * BEAT;

  // Real copy from openaigrowth.com (hero console demo, home sections).
  const input = [
    ["product", "Maple cake server set"],
    ["process", "Laser engraving"],
    ["options", "2 fonts · 3 woods"],
    ["unknown", "Blade steel grade"],
  ];
  const title =
    "Personalized Maple Cake Server Set, Engraved Wedding Cake Knife and Server";
  const tags = [
    "cake server set",
    "wedding cake knife",
    "engraved server",
    "maple cake server",
    "custom cake cutter",
    "bridal shower gift",
    "wedding keepsake",
    "personalized knife",
    "cake cutting set",
    "rustic wedding",
    "anniversary gift",
    "wood cake server",
    "couple name gift",
  ];
  const board = [
    ["SKILL", "Listing 文案"],
    ["TOOL", "利润计算器"],
    ["RESOURCE", "物流与追踪"],
    ["SKILL", "产品机会分析"],
    ["PAGE", "发货清单"],
    ["TOOL", "13 标签检查"],
  ];
  const library = ["原创产品方向", "15 图拍摄规划", "合作定价核算", "选品与关键词"];
  const tools = [
    "利润计算器",
    "合作定价核算",
    "标题字符检查",
    "13 标签检查",
    "AI 披露文案",
    "运费计费重",
  ];
  const pipeline = [
    "产品机会分析",
    "原创产品方向",
    "工艺审查",
    "设计系列",
    "SKU 与定制选项",
    "上架资料包",
    "15 图拍摄规划",
  ];

  // Deterministic "human" typing: each character's time from a fixed hash.
  function jitter(i) {
    const x = Math.sin(i * 12.9898 + 78.233) * 43758.5453;
    return x - Math.floor(x);
  }
  // Four input lines typed between beats 3 and 7.75.
  const typing = [];
  {
    const starts = [b(3.25), b(4.25), b(5.25), b(6.25)];
    const ends = [b(4.15), b(5.1), b(6.1), b(7.6)];
    input.forEach(([, v], line) => {
      const n = v.length;
      const span = ends[line] - starts[line];
      let acc = 0;
      const gaps = [];
      for (let i = 0; i < n; i++) {
        const g = 0.6 + jitter(line * 100 + i) * 0.8 + (v[i - 1] === " " ? 0.6 : 0);
        gaps.push(g);
        acc += g;
      }
      let t = starts[line];
      for (let i = 0; i < n; i++) {
        typing.push({ line, i, t });
        t += (gaps[i] / acc) * span;
      }
    });
  }
  const titleWords = title.split(" ");
  // Title tokens stream in over beats 9–11.5, tags pop on eighths from beat 11.5.
  const tokenTimes = titleWords.map((_, i) => b(9) + (i / titleWords.length) * b(2.5));
  const tagTimes = tags.map((_, i) => b(11.5) + i * b(0.25));

  const T = {
    BPM,
    BEAT,
    duration: b(48),
    fps: 60,
    copy: { input, title, titleWords, tags, board, library, tools, pipeline },
    typing,
    tokenTimes,
    tagTimes,
    // Scene marks (seconds).
    at: {
      hookOut: b(2.25), // the opening title lifts away; the dot leaves its period
      unfold: b(2.5), // dot stretches into the console
      unfoldEnd: b(3.0),
      barIn: b(3.0), // site label under the subtitles
      typeStart: b(3.25),
      typeEnd: b(7.6),
      drop: b(8), // dot runs down the track
      titleCard: b(8.5),
      tagsCard: b(11),
      verdict: b(15),
      validated: b(15),
      comet: b(15),
      flood: b(16), // the drop
      floodPeak: b(16) + 0.34, // frame is fully lime
      boardCards: [16.9, 17.5, 18, 18.5, 19, 19.5].map(b),
      pick: b(20.5),
      click: b(21),
      chipFly: b(21.25),
      chipLand: b(22.25),
      panTools: b(23.25),
      toolLights: [24.5, 25.5, 26.5, 27.5, 28.5, 29.5].map(b),
      panPipe: b(31.25),
      pipeNodes: [32.5, 33.5, 34.5, 35.5, 36.5, 37.5, 38.5].map(b),
      outro: b(40),
      wordmark: b(40.75),
      tagline: b(42),
      url: b(44),
      end: b(48),
    },
    // First-person lines; the lime dot is speaking.
    subtitles: [
      { from: b(3.5), to: b(8), zh: "写 Etsy 标题，只用你确认过的事实。", zhL: "写 Etsy 标题，<br>只用你确认过的事实。", en: "Etsy titles from the facts you confirm." },
      { from: b(8.5), to: b(16), zh: "按 Etsy 规则：140 字符，13 个标签。", zhL: "按 Etsy 规则：<br>140 字符，<br>13 个标签。", en: "Checked to Etsy's limits: 140 characters, 13 tags." },
      { from: b(17), to: b(23.25), zh: "你的 Etsy 工作台，模块自己选。", zhL: "你的 Etsy 工作台，<br>模块自己选。", en: "Your Etsy workbench. Pick your modules." },
      { from: b(24.25), to: b(31.25), zh: "Etsy 免费工具，不用登录。", zhL: "Etsy 免费工具，<br>不用登录。", en: "Free Etsy tools. No sign-up." },
      { from: b(32.25), to: b(40), zh: "从选品到 Etsy 上架，一条流水线。", zhL: "从选品到 Etsy 上架，<br>一条流水线。", en: "From product idea to Etsy listing." },
    ],
  };
  if (typeof module !== "undefined") module.exports = T;
  else root.T = T;
})(this);
