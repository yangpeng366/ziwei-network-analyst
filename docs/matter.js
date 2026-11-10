/* 事项映射：与 Python 侧 packages/matter_query/map.py 同口径。
   规则与阈值必须两边一致，改一处要同步改另一处（scripts/test-matter-mapping.py 会做一致性校验）。 */
(function (root, factory) {
  "use strict";
  var api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.ZiweiMatter = api;
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  var MAX_PALACES = 6;
  var MAX_FACTORS = 5;
  var MAX_SECONDARY = 2;
  var MIN_SECONDARY_SCORE = 1.5;
  var SECONDARY_RATIO = 0.4;
  var LABEL_SEP = "＋";
  var GENERAL_ID = "general";
  var MAX_SUGGESTIONS_PER_CLASS = 4;

  /* 关键词越具体权重越高：1 字 1.0 / 2 字 1.5 / 3 字及以上 2.0 */
  function kwWeight(k) {
    var n = k.length;
    if (n <= 1) return 1.0;
    if (n === 2) return 1.5;
    return 2.0;
  }

  function scoreCategory(cat, q) {
    var hits = [];
    var kws = cat.keywords || [];
    for (var i = 0; i < kws.length; i++) {
      if (kws[i] && q.indexOf(kws[i]) >= 0) hits.push(kws[i]);
    }
    if (!hits.length) return { score: 0, hits: hits };
    var base = 0;
    for (var j = 0; j < hits.length; j++) base += kwWeight(hits[j]);
    return { score: base * (1.0 + 0.25 * (hits.length - 1)), hits: hits };
  }

  function generalCat(matters) {
    for (var i = 0; i < matters.length; i++) if (matters[i].id === GENERAL_ID) return matters[i];
    return matters[matters.length - 1];
  }

  /* 兜底时可试的说法：按目录顺序（跳过 general），每类取前 4 个关键词，原序 */
  function matterSuggestions(matters) {
    var out = [];
    for (var i = 0; i < matters.length; i++) {
      if (matters[i].fallback) continue;
      var kws = [];
      var src = matters[i].keywords || [];
      for (var j = 0; j < src.length && kws.length < MAX_SUGGESTIONS_PER_CLASS; j++) {
        if (src[j]) kws.push(src[j]);
      }
      if (kws.length) out.push({ matter_id: matters[i].id, label: matters[i].label, keywords: kws });
    }
    return out;
  }

  /* 提示文案：模板/分隔符/省略号全部来自 catalog.json 的 fallback_hint，与 Python 同源 */
  function fallbackHint(suggestions, hintCfg) {
    var cfg = hintCfg || {};
    var flat = [];
    for (var i = 0; i < suggestions.length; i++) {
      var kws = suggestions[i].keywords || [];
      for (var j = 0; j < kws.length; j++) flat.push(kws[j]);
    }
    if (!flat.length) return "";
    var limit = cfg.max_examples || flat.length;
    var shown = flat.slice(0, limit);
    var body = shown.join(cfg.separator || " / ");
    if (shown.length < flat.length) body += (cfg.ellipsis || "");
    return String(cfg.template || "{examples}").replace("{examples}", body);
  }

  function fallbackFocus(matters, query, hintCfg) {
    var cat = generalCat(matters);
    var suggestions = matterSuggestions(matters);
    return {
      query: query,
      matched: false,
      matter_id: cat.id,
      matter_ids: [cat.id],
      label: cat.label,
      labels: [cat.label],
      secondary_labels: [],
      palaces: (cat.palaces || []).slice(),
      focus_factors: (cat.focus_factors || []).slice(),
      lens: cat.lens,
      hit_keywords: [],
      suggestions: suggestions,
      hint: fallbackHint(suggestions, hintCfg)
    };
  }

  /* 返回 { query, matched, matter_id, matter_ids, label, labels, secondary_labels,
             palaces, focus_factors, lens, hit_keywords,
             suggestions, hint }（与 Python 侧字段一致；后两项仅兜底时出现） */
  function resolveMatter(matters, timeKeywords, text, hintCfg) {
    matters = matters || [];
    timeKeywords = timeKeywords || [];
    var q = (text || "").trim();
    if (!q) return fallbackFocus(matters, q, hintCfg);

    var scored = [];
    for (var i = 0; i < matters.length; i++) {
      if (matters[i].fallback) continue;
      var r = scoreCategory(matters[i], q);
      if (r.score > 0) scored.push({ idx: i, cat: matters[i], score: r.score, hits: r.hits });
    }
    if (!scored.length) return fallbackFocus(matters, q, hintCfg);

    scored.sort(function (a, b) { return (b.score - a.score) || (a.idx - b.idx); });
    var primary = scored[0];
    var threshold = Math.max(MIN_SECONDARY_SCORE, primary.score * SECONDARY_RATIO);
    var secondaries = [];
    for (var k = 1; k < scored.length && secondaries.length < MAX_SECONDARY; k++) {
      if (scored[k].score >= threshold) secondaries.push(scored[k]);
    }

    var ordered = [primary].concat(secondaries);

    var palaces = [];
    var factors = [];
    var labels = [];
    var hitKeywords = [];
    for (var m = 0; m < ordered.length; m++) {
      var ps = ordered[m].cat.palaces || [];
      for (var p = 0; p < ps.length; p++) {
        if (palaces.indexOf(ps[p]) < 0) palaces.push(ps[p]);
      }
      var fs = ordered[m].cat.focus_factors || [];
      for (var f = 0; f < fs.length; f++) {
        if (factors.indexOf(fs[f]) < 0) factors.push(fs[f]);
      }
      labels.push(ordered[m].cat.label);
      var hs = ordered[m].hits;
      for (var h = 0; h < hs.length; h++) {
        if (hitKeywords.indexOf(hs[h]) < 0) hitKeywords.push(hs[h]);
      }
    }
    palaces = palaces.slice(0, MAX_PALACES);

    var isTime = false;
    for (var t = 0; t < timeKeywords.length; t++) {
      if (timeKeywords[t] && q.indexOf(timeKeywords[t]) >= 0) { isTime = true; break; }
    }
    if (isTime && factors.indexOf("F4_tempo") < 0) factors.push("F4_tempo");
    factors = factors.slice(0, MAX_FACTORS);

    var lens = primary.cat.lens;
    for (var s = 0; s < secondaries.length; s++) {
      lens += " 同时看「" + secondaries[s].cat.label + "」：" + secondaries[s].cat.lens;
    }

    return {
      query: q,
      matched: true,
      matter_id: primary.cat.id,
      matter_ids: ordered.map(function (o) { return o.cat.id; }),
      label: labels.length === 1 ? labels[0] : labels.join(LABEL_SEP),
      labels: labels,
      secondary_labels: labels.slice(1),
      palaces: palaces,
      focus_factors: factors,
      lens: lens,
      hit_keywords: hitKeywords
    };
  }

  return {
    resolveMatter: resolveMatter,
    matterSuggestions: matterSuggestions,
    fallbackHint: fallbackHint,
    kwWeight: kwWeight,
    scoreCategory: scoreCategory
  };
});