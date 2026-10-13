// V-W03 — launch-film cut of the Shopwright site film. 30 s, 80 BPM (beat = 0.75 s), 40 beats, 24 fps.
// Shared by picture (filmK.html) and sound (music_k.py).
// All copy and numbers are from openaigrowth.com and its source (see 分镜.md).
(function (root) {
  const BPM = 80, BEAT = 60 / BPM, b = (x) => x * BEAT;
  const shots = [
    ["open", 0, 5], ["name", 5, 11], ["title", 11, 16], ["tags", 16, 20],
    ["profit", 20, 26], ["pipe", 26, 31], ["montage", 31, 33], ["end", 33, 40],
  ].map(([id, s, e]) => ({ id, t0: b(s), t1: b(e) }));
  const title = "Personalized Maple Cake Server Set, Engraved Wedding Cake Knife and Server";
  const tags = ["cake server set", "wedding cake knife", "engraved server", "maple cake server", "custom cake cutter", "bridal shower gift",
    "wedding keepsake", "personalized knife", "cake cutting set", "rustic wedding", "anniversary gift", "wood cake server", "couple name gift"];
  const FX = 7.1;
  // Slices of the $30 order, cut from the right (site calculator default example).
  const cuts = [
    { kind: "etsy", usd: 0.2, after: "$29.80", lab: "上架费 $0.20" },
    { kind: "etsy", usd: 1.95, after: "$27.85", lab: "交易费 $1.95" },
    { kind: "etsy", usd: 2.25, after: "$25.60", lab: "支付处理 $2.25" },
    { kind: "fx", usd: 0.256, after: "¥179.94", lab: "结汇 1%" },
    { kind: "cost", usd: 70 / FX, after: "¥109.94", lab: "物流 ¥70" },
    { kind: "cost", usd: 40 / FX, after: "¥69.94", lab: "商品 ¥40" },
    { kind: "cost", usd: 5 / FX, after: "¥64.94", lab: "包装 ¥5" },
  ];
  const cutTimes = [20.8, 21.3, 21.8, 22.6, 23.3, 23.8, 24.3].map(b);
  const typeT0 = b(11.9), typeT1 = b(15.2);
  const tagTimes = tags.map((_, i) => b(16.6) + i * b(0.2));
  const pipeTimes = [26.6, 27.2, 27.8, 28.4, 29.0, 29.6, 30.2].map(b);
  const T = {
    BPM, BEAT, fps: 24, duration: b(40), shots, FX,
    copy: { title, tags, cuts, pipeline: ["产品机会分析", "原创产品方向", "工艺审查", "设计系列", "SKU 与定制选项", "上架资料包", "15 图拍摄规划"],
      board: [["SKILL", "Listing 文案"], ["TOOL", "利润计算器"], ["RESOURCE", "物流与追踪"], ["SKILL", "产品机会分析"], ["PAGE", "发货清单"], ["TOOL", "13 标签检查"]],
      tools: ["利润计算器", "合作定价核算", "标题字符检查", "13 标签检查", "AI 披露文案", "运费计费重"] },
    typeT0, typeT1, tagTimes, cutTimes, pipeTimes,
    at: {
      dotOn: b(0.6), nameSweep: b(5), nameSweepEnd: b(7.6), nameEyebrow: b(7.4), nameSub: b(8.1),
      chapter: { title: b(11), tags: b(16), profit: b(20), pipe: b(26) },
      result: b(24.6), flashes: [b(31), b(31.5), b(32)], silence: b(32.5), hit: b(33),
      endLand: b(34.3), endLine: b(35.2), url: b(36.4), end: b(40),
    },
    subtitles: [
      { from: b(1.2), to: b(4.8), zh: "开一家 Etsy 店，<br>要做的事太多了。", en: "Running an Etsy shop means a hundred small jobs." },
      { from: b(11.6), to: b(15.8), zh: "写 Etsy 标题，只用你确认过的事实。", en: "Etsy titles from the facts you confirm." },
      { from: b(16.4), to: b(19.8), zh: "按 Etsy 上限：13 个标签。", en: "Up to Etsy's limit: 13 tags." },
      { from: b(20.6), to: b(25.8), zh: "每一笔费用都算清，最后剩 64.94 元。", en: "Every fee counted. I end up as ¥64.94." },
      { from: b(26.4), to: b(30.8), zh: "从选品到 Etsy 上架，一条流水线。", en: "From product idea to Etsy listing." },
    ],
  };
  if (typeof module !== "undefined") module.exports = T; else root.T = T;
})(this);
