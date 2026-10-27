/* 紫微四因子 · 静态站（无后端，双击 index.html 亦可运行） */
(function () {
  "use strict";
  var D = window.ZIWEI_DATA || { charts: [], matters: [] };
  var state = { chartId: null, matter: "", from: null, to: null };

  var $ = function (id) { return document.getElementById(id); };
  var esc = function (s) {
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  };

  function chart() {
    for (var i = 0; i < D.charts.length; i++) if (D.charts[i].id === state.chartId) return D.charts[i];
    return D.charts[0] || null;
  }

  /* ---------- 事项映射（与 Python 侧同口径） ---------- */
  function resolveMatter(q) {
    q = (q || "").trim();
    var best = null, bestHits = [];
    for (var i = 0; i < D.matters.length; i++) {
      var m = D.matters[i], hits = [];
      for (var j = 0; j < m.keywords.length; j++) {
        if (m.keywords[j] && q.indexOf(m.keywords[j]) >= 0) hits.push(m.keywords[j]);
      }
      if (hits.length > bestHits.length) { best = m; bestHits = hits; }
    }
    if (!best) {
      best = null;
      for (var k = 0; k < D.matters.length; k++) if (D.matters[k].id === "general") best = D.matters[k];
      bestHits = [];
    }
    return { matter: best, hits: bestHits, query: q };
  }

  function rowFor(c, year) {
    var rows = c.timeline.rows;
    for (var i = 0; i < rows.length; i++) if (rows[i].year === year) return rows[i];
    return null;
  }

  function yearState(c) {
    var range = c.timeline.range;
    var y = (c.current && c.current.year) || range[0];
    if (state.year && state.year >= range[0] && state.year <= range[1]) y = state.year;
    return y;
  }

  function matterPlain(c, focus, row) {
    var ks = (row && row.keystones) || [];
    var carriers = ks.filter(function (k) { return focus.palaces.indexOf(k.palace) >= 0; });
    var hot = (row && row.ji_hotspots) || [];
    var pressures = hot.filter(function (h) { return focus.palaces.indexOf(h.palace) >= 0; });
    var parts = [];
    parts.push("就「" + focus.label + "」看：优先宫位 " + focus.palaces.join("、") + "。" + focus.lens);
    if (carriers.length) {
      parts.push("落在本题宫位上的承重星：" + carriers.map(function (k) { return k.name + "@" + k.palace; }).join("、") + "。");
    } else {
      parts.push("本题宫位上暂未见最顶级承重星；力量可能来自邻宫或借对。");
    }
    if (pressures.length) {
      parts.push("与本题相关的忌压热区偏在：" + pressures.map(function (p) { return p.palace + "(" + p.ji_pressure + ")"; }).join("、")
        + "。宜留缓冲，不把同一处连续加压。");
    } else {
      parts.push("本题相关宫位上，活跃层忌压热区不明显；仍要看承重是否过载。");
    }
    parts.push("结论只标势能方向与可觉察点，不作吉凶判决。");
    return parts.join(" ");
  }

  /* ---------- 逐年曲线（纯 SVG） ---------- */
  function curveSvg(rows, transitions, title, from, to) {
    rows = rows.filter(function (r) { return r.year >= from && r.year <= to && r.F3 != null && r.F4 != null; });
    if (rows.length < 2) return "";
    var W = 960, H = 340, PL = 54, PR = 18, PT = 26, PB = 42;
    var xs = rows.map(function (r) { return r.year; });
    var x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs);
    var pw = W - PL - PR, ph = H - PT - PB;
    function px(y) { return x1 === x0 ? PL + pw / 2 : PL + (y - x0) / (x1 - x0) * pw; }
    function py(v) { v = Math.max(0, Math.min(1, Number(v) || 0)); return PT + (1 - v) * ph; }
    var out = [];
    out.push('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + W + ' ' + H + '" width="100%" height="' + H
      + '" role="img" aria-label="逐年因子曲线" font-family="Segoe UI, Microsoft YaHei, sans-serif">');
    out.push('<rect x="0" y="0" width="' + W + '" height="' + H + '" fill="#fffdf8"/>');
    if (title) out.push('<text x="' + PL + '" y="16" font-size="13" font-weight="600" fill="#1f2430">' + esc(title) + "</text>");
    for (var i = 0; i < 5; i++) {
      var v = i / 4, y = py(v);
      out.push('<line x1="' + PL + '" y1="' + y.toFixed(1) + '" x2="' + (W - PR) + '" y2="' + y.toFixed(1) + '" stroke="#e6e0d5"/>');
      out.push('<text x="' + (PL - 8) + '" y="' + (y + 4).toFixed(1) + '" font-size="11" fill="#5c6575" text-anchor="end">' + v.toFixed(2) + "</text>");
    }
    (transitions || []).forEach(function (t) {
      if (t.year < x0 || t.year > x1) return;
      var x = px(t.year);
      out.push('<line x1="' + x.toFixed(1) + '" y1="' + PT + '" x2="' + x.toFixed(1) + '" y2="' + (H - PB) + '" stroke="#c9a227" stroke-dasharray="4 4"/>');
      out.push('<text x="' + (x + 4).toFixed(1) + '" y="' + (PT + 12) + '" font-size="10" fill="#8a6d1f">大限交接</text>');
    });
    var step = Math.max(1, Math.ceil(rows.length / 10));
    for (var k = 0; k < rows.length; k += step) {
      out.push('<text x="' + px(rows[k].year).toFixed(1) + '" y="' + (H - PB + 16) + '" font-size="11" fill="#5c6575" text-anchor="middle">' + rows[k].year + "</text>");
    }
    [["F4", "节律窗口（换轨压力）", "#0f6a5a"], ["F3", "冲击脆弱", "#8a2f3b"]].forEach(function (s) {
      var pts = rows.map(function (r) { return px(r.year).toFixed(1) + "," + py(r[s[0]]).toFixed(1); }).join(" ");
      out.push('<polyline points="' + pts + '" fill="none" stroke="' + s[2] + '" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"/>');
      rows.forEach(function (r) {
        out.push('<circle cx="' + px(r.year).toFixed(1) + '" cy="' + py(r[s[0]]).toFixed(1) + '" r="3" fill="' + s[2] + '"/>');
      });
    });
    var lx = PL;
    [["F4 节律窗口（换轨压力）", "#0f6a5a"], ["F3 冲击脆弱", "#8a2f3b"]].forEach(function (s) {
      out.push('<rect x="' + lx + '" y="' + (H - 15) + '" width="10" height="10" rx="2" fill="' + s[1] + '"/>');
      out.push('<text x="' + (lx + 15) + '" y="' + (H - 6) + '" font-size="11" fill="#1f2430">' + esc(s[0]) + "</text>");
      lx += 20 + s[0].length * 11;
    });
    out.push("</svg>");
    return out.join("");
  }

  /* ---------- 提示包 ---------- */
  function buildPrompt(c, focus, row, plainText) {
    var L = [];
    L.push("你是命盘复杂系统分析助手。下面是已经算好的结构化结果，请只做白话翻译与情景推演。");
    L.push("硬约束：不得改分数；不得重排盘；不得下绝对命运断言；六亲仅参考受限。");
    L.push("");
    L.push("【用户想问的事】" + (focus.query || "（未指定，按整体态势）"));
    L.push("【事项归类】" + focus.matter.label);
    L.push("【事项聚焦草稿】" + plainText);
    L.push("");
    L.push("【四因子一句话】");
    L.push(c.current.one_liner || "");
    L.push("");
    L.push("【白话摘要】");
    L.push(c.current.plain.summary || "");
    var pf = c.current.plain.factors_plain || {};
    ["F1_community", "F2_keystone", "F3_fragility", "F4_tempo"].forEach(function (k) {
      if (pf[k]) L.push("- " + k + ": " + pf[k]);
    });
    L.push("");
    L.push("【逐年推演（参考，非结论）】");
    L.push("- " + c.timeline.summary);
    var ty = c.timeline.transition_years || [];
    if (ty.length) L.push("- 大限交接年：" + ty.slice(0, 8).join("、"));
    var mv = (c.timeline.move_years || []).filter(function (y) { return y >= state.from && y <= state.to; });
    if (mv.length) L.push("- 宜动窗口（贴近交接）：" + mv.slice(0, 8).join("、"));
    var hd = (c.timeline.hold_years || []).filter(function (y) { return y >= state.from && y <= state.to; });
    if (hd.length) L.push("- 相对宜守：" + hd.slice(0, 8).join("、"));
    var rk = (c.timeline.risk_years || []).filter(function (y) { return y >= state.from && y <= state.to; });
    if (rk.length) L.push("- 冲击吃紧：" + rk.slice(0, 8).join("、"));
    L.push("");
    L.push("【硬证据（勿改）】");
    var f = c.current.factors || {};
    Object.keys(f).forEach(function (k) {
      L.push("- " + k + ": score=" + f[k].score + " reading=" + f[k].reading);
    });
    if ((c.current.keystones || []).length) {
      L.push("- keystones: " + c.current.keystones.slice(0, 5).map(function (x) { return x.name + "@" + x.palace; }).join(", "));
    }
    if ((c.current.ji_fragility || []).length) {
      L.push("- ji_hotspots: " + c.current.ji_fragility.slice(0, 5).map(function (x) { return x.palace + "=" + x.ji_pressure; }).join(", "));
    }
    L.push("");
    L.push("【请你输出】");
    L.push("1. 先用大白话回答用户的具体事");
    L.push("2. 点明：相关宫位 / 承重星 / 忌压热区 / 是否靠近换轨窗口");
    L.push("3. 给 2-3 条可逆的自我觉察建议（非决策指令）");
    L.push("4. 结尾加一句免责：仅供参考，非命运断言");
    return L.join("\n");
  }

  /* ---------- 渲染 ---------- */
  function render() {
    var c = chart();
    if (!c) return;
    var y = yearState(c);
    var row = rowFor(c, y);
    var focus = resolveMatter(state.matter);
    var plainText = matterPlain(c, focus.matter, row);

    $("chart-label").textContent = c.label + " · 基准年 " + c.current.year;
    $("one-liner").textContent = c.current.one_liner || "";

    var f = c.current.factors || {};
    var order = [["F1_community", "共同体感", "f1"], ["F2_keystone", "承重星", "f2"],
                 ["F3_fragility", "冲击脆弱", "f3"], ["F4_tempo", "节律窗口", "f4"]];
    $("factors").innerHTML = order.map(function (o) {
      var it = f[o[0]] || {};
      var pct = Math.round((it.score || 0) * 100);
      return '<div class="factor ' + o[2] + '"><div class="name">' + o[1] + "</div>"
        + '<div class="score">' + Number(it.score || 0).toFixed(2) + "</div>"
        + '<div class="reading">' + esc(it.reading || "") + "</div>"
        + '<div class="bar"><span style="width:' + pct + '%"></span></div></div>';
    }).join("");

    var pf = c.current.plain.factors_plain || {};
    $("plain-summary").textContent = c.current.plain.summary || "";
    $("plain-factors").innerHTML = order.map(function (o) {
      return '<div class="plain-item"><b>' + o[1] + "</b>" + esc(pf[o[0]] || "") + "</div>";
    }).join("");
    $("plain-next").innerHTML = (c.current.plain.how_to_look_next || []).map(function (x) { return "<li>" + esc(x) + "</li>"; }).join("");

    $("matter-label").textContent = "「" + focus.matter.label + "」" + (y !== c.current.year ? "（按 " + y + " 年看）" : "");
    $("matter-plain").textContent = plainText;
    $("matter-palaces").textContent = "相关宫位：" + focus.matter.palaces.join("、")
      + (focus.hits.length ? "（命中：" + focus.hits.join("、") + "）" : "");
    $("matter-actions").innerHTML = [
      "先盯本题宫位的承重星与忌压，再看是否撞上 F4 换轨窗口。",
      "把建议落成可逆的小动作（留缓冲、分摊负荷、错峰决策），不要一次梭哈。",
      "六亲 / 婚恋 / 健康仅参考受限；重大决策请结合现实信息与专业意见。"
    ].map(function (x) { return "<li>" + esc(x) + "</li>"; }).join("");

    $("keystones").innerHTML = (c.current.keystones || []).slice(0, 5).map(function (x) {
      return "<tr><td>" + esc(x.name) + "</td><td>" + esc(x.palace || "") + "</td><td>" + x.score + "</td></tr>";
    }).join("") || '<tr><td colspan="3">无</td></tr>';
    $("frags").innerHTML = (c.current.ji_fragility || []).slice(0, 6).map(function (x) {
      return "<tr><td>" + esc(x.palace) + "</td><td>" + x.ji_pressure + "</td></tr>";
    }).join("") || '<tr><td colspan="2">无</td></tr>';

    var inRange = function (arr) {
      return (arr || []).filter(function (yy) { return yy >= state.from && yy <= state.to; });
    };
    var mv = inRange(c.timeline.move_years), hd = inRange(c.timeline.hold_years), rk = inRange(c.timeline.risk_years);
    $("curve").innerHTML = curveSvg(c.timeline.rows, c.timeline.daxian_transitions,
      "逐年推演 " + state.from + "–" + state.to, state.from, state.to);
    var tag = function (label, cls, arr) {
      return arr.length ? '<span class="tag ' + cls + '">' + label + "：" + arr.slice(0, 12).join("、") + (arr.length > 12 ? " …" : "") + "</span>" : "";
    };
    $("tags").innerHTML = tag("宜动（结构改写）", "move", mv) + tag("宜守（深耕）", "hold", hd)
      + tag("冲击吃紧", "risk", rk) + '<span class="tag">区间 ' + state.from + "–" + state.to + "</span>";
    $("tl-summary").textContent = c.timeline.summary;

    $("tl-rows").innerHTML = c.timeline.rows.filter(function (r) {
      return r.year >= state.from && r.year <= state.to;
    }).map(function (r) {
      var hot = (r.ji_hotspots || [])[0];
      var mark = mv.indexOf(r.year) >= 0 ? " ★" : (rk.indexOf(r.year) >= 0 ? " !" : "");
      return "<tr><td>" + r.year + mark + "</td><td>" + (r.age == null ? "-" : r.age) + "</td><td>"
        + esc(r.daxian_label || "-") + "</td><td>" + (r.F3 == null ? "-" : r.F3) + "</td><td>"
        + (r.F4 == null ? "-" : r.F4) + "</td><td>" + (hot ? esc(hot.palace) + "(" + hot.ji_pressure + ")" : "-") + "</td></tr>";
    }).join("");

    $("prompt").value = buildPrompt(c, focus, row, plainText);
  }

  function init() {
    if (!D.charts || !D.charts.length) {
      $("status").textContent = "数据未加载：请先运行 python scripts/build-site.py";
      return;
    }
    var sel = $("chart");
    sel.innerHTML = D.charts.map(function (c) { return '<option value="' + c.id + '">' + esc(c.label) + "</option>"; }).join("");
    state.chartId = D.charts[0].id;
    var r = D.charts[0].timeline.range;
    state.from = r[0]; state.to = r[1];
    $("yfrom").value = r[0]; $("yto").value = r[1];

    $("chips").innerHTML = ["跳槽", "感情", "身体", "换房", "合作", "钱"].map(function (t) {
      return '<span class="chip" data-q="' + t + '">' + t + "</span>";
    }).join("");
    Array.prototype.forEach.call(document.querySelectorAll(".chip"), function (chip) {
      chip.onclick = function () {
        var t = chip.getAttribute("data-q");
        var map = { "跳槽": "今年适合跳槽吗", "感情": "这段感情能长久吗", "身体": "今年身体要注意什么",
                    "换房": "什么时候适合换房", "合作": "这次合作能成吗", "钱": "今年财运如何" };
        $("matter").value = map[t] || t;
        state.matter = $("matter").value;
        render();
      };
    });

    sel.onchange = function () { state.chartId = sel.value; state.year = null; render(); };
    $("matter").oninput = function () { state.matter = this.value; render(); };
    $("yfrom").onchange = $("yto").onchange = function () {
      var a = parseInt($("yfrom").value, 10), b = parseInt($("yto").value, 10);
      if (isNaN(a) || isNaN(b)) return;
      if (a > b) { var t = a; a = b; b = t; }
      state.from = a; state.to = b; render();
    };
    $("copy").onclick = function () {
      var ta = $("prompt");
      ta.select();
      var ok = false;
      try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
      if (!ok && navigator.clipboard) { navigator.clipboard.writeText(ta.value); ok = true; }
      this.textContent = ok ? "已复制" : "请手动复制";
      var btn = this;
      setTimeout(function () { btn.textContent = "复制提示词"; }, 1400);
    };
    $("copy-plain").onclick = function () {
      var c = chart();
      var focus = resolveMatter(state.matter);
      var row = rowFor(c, yearState(c));
      var txt = matterPlain(c, focus.matter, row) + "\n\n" + c.current.plain.summary;
      var ta = $("prompt");
      ta.value = txt; ta.select();
      try { document.execCommand("copy"); } catch (e) {}
      this.textContent = "已复制";
      var btn = this;
      setTimeout(function () { btn.textContent = "只复制白话结论"; }, 1400);
    };

    render();
    $("status").textContent = "就绪 · 静态演示（数据预计算，无需安装）";
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();