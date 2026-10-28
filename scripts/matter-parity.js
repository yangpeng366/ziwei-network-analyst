/* 用 docs/matter.js 跑一遍语料，输出 JSON 供 Python 侧比对（前后端一致性校验）。 */
"use strict";
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const read = (p) => JSON.parse(fs.readFileSync(path.join(ROOT, p), "utf8"));
const catalog = read("packages/matter_query/catalog.json");
const corpus = read("fixtures/question-corpus.json");
const matter = require(path.join(ROOT, "docs/matter.js"));

const out = corpus.cases.map((c) => {
  const f = matter.resolveMatter(catalog.categories, catalog.time_keywords, c.q);
  return {
    q: c.q,
    matched: f.matched,
    matter_id: f.matter_id,
    matter_ids: f.matter_ids,
    label: f.label,
    palaces: f.palaces,
    focus_factors: f.focus_factors,
    lens: f.lens,
    hit_keywords: f.hit_keywords,
  };
});
process.stdout.write(JSON.stringify(out));