// Film A — "Etsy 卖一单 $30，到底赚多少？" (Etsy 利润计算器), 18 s.
// Shared by picture (filmA.html) and sound (music_a.py). 120 BPM, 36 beats.
// Every number is the site's own profit calculator on its default example
// (src/lib/calculator/profit.ts, defaultProfitInput, fee rates checked 2026-10-08):
//   price $25 + buyer shipping $5, bank in China, FX 7.10, withdraw 1%,
//   cost ¥40, packaging ¥5, shipping ¥70.
//   -> Etsy fees $0.20 + $1.95 + $2.25 = $4.40 (14.7%), net ¥179.94,
//      profit ¥64.94 (30.5%); with offsite ads 15%: profit ¥33.31 (15.6%).
//   Breakeven price $14.39, price for 30% margin $24.73.
(function (root) {
  const BPM = 120;
  const BEAT = 60 / BPM;
  const b = (beats) => beats * BEAT;
  const FX = 7.1;
  // Ledger rows, cut from the right end of the bar in this order.
  // usd: the slice's width in dollars on the bar; after: header amount once cut.
  const cuts = [
    { at: b(5.5), kind: "etsy", zh: "上架费", d: "listing fee", amt: "−$0.20", usd: 0.2, after: "$29.80" },
    { at: b(7), kind: "etsy", zh: "交易费", d: "6.5% × $30", amt: "−$1.95", usd: 1.95, after: "$27.85" },
    { at: b(8.5), kind: "etsy", zh: "支付处理费", d: "6.5% × $30 + $0.30", amt: "−$2.25", usd: 2.25, after: "$25.60" },
    { at: b(12.5), kind: "fx", zh: "结汇", d: "1% × $25.60", amt: "−$0.26", usd: 0.256, after: "$25.34" },
    { at: b(14.5), kind: "cost", zh: "物流", d: "shipping", amt: "−¥70.00", usd: 70 / FX, after: "¥109.94" },
    { at: b(15.5), kind: "cost", zh: "商品成本", d: "product cost", amt: "−¥40.00", usd: 40 / FX, after: "¥69.94" },
    { at: b(16.5), kind: "cost", zh: "包装", d: "packaging", amt: "−¥5.00", usd: 5 / FX, after: "¥64.94" },
  ];
  const T = {
    BPM,
    BEAT,
    duration: b(36),
    fps: 60,
    FX,
    cuts,
    profitUsd: 64.9424 / FX, // what is left on the bar
    offsiteUsd: (64.9424 - 33.3119) / FX, // offsite fee net of the smaller withdrawal
    at: {
      hookOut: b(3), // order card lifts away; the dot leaves "● 已付款"
      dotLand: b(3.6),
      barGrow: b(3.5),
      barFull: b(4.3),
      etsyBracket: b(10),
      flip: b(13.5), // USD -> CNY
      costBracket: b(17.25),
      result: b(18),
      toggleIn: b(20),
      riser: b(20),
      offsite: b(22), // the drop
      compare: b(22.5),
      outro: b(28),
      endTitle: b(28.75),
      features: [b(30), b(30.5), b(31)],
      url: b(32),
      end: b(36),
    },
    subtitles: [
      { from: b(1), to: b(4.75), zh: "我是一笔 30 美元的 Etsy 订单。", zhL: "我是一笔<br>30 美元的 Etsy 订单。", en: "I'm a $30 Etsy order." },
      { from: b(5), to: b(12.25), zh: "先交给 Etsy 4.40 美元。", zhL: "先交给 Etsy<br>4.40 美元。", en: "Etsy takes $4.40 first." },
      { from: b(12.5), to: b(18), zh: "换成人民币，再减掉成本。", zhL: "换成人民币，<br>再减掉成本。", en: "Then into yuan, minus costs." },
      { from: b(18.25), to: b(21.75), zh: "最后剩 64.94 元。", zhL: "最后剩<br>64.94 元。", en: "I end up as ¥64.94." },
      { from: b(22.25), to: b(28), zh: "要是来自站外广告，只剩 33.31。", zhL: "要是来自站外广告，<br>只剩 33.31。", en: "From an offsite ad: just ¥33.31." },
      { from: b(28.5), to: b(35.5), zh: "定价之前，先用计算器算一遍。", zhL: "定价之前，<br>先用计算器算一遍。", en: "Run the numbers before you set the price." },
    ],
  };
  if (typeof module !== "undefined") module.exports = T;
  else root.T = T;
})(this);
