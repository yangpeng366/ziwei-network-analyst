/* 用最小 DOM 桩真跑一遍 docs/app.js，取渲染后的 #matter-hint 文本（离线、无浏览器、无网络）。
   目标：证明静态站「问法没被识别」不是只写进代码，而是真的渲染到 DOM 文本上。 */
"use strict";
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.resolve(__dirname, "..");
const query = process.argv[2] || "";

function El(id) {
  this.id = id;
  this.textContent = "";
  this.innerHTML = "";
  this.value = "";
  this.attrs = {};
  this.style = {};
  this.onchange = null;
  this.oninput = null;
  this.onclick = null;
}
El.prototype.setAttribute = function (k, v) { this.attrs[k] = String(v); };
El.prototype.removeAttribute = function (k) { delete this.attrs[k]; };
El.prototype.hasAttribute = function (k) {
  return Object.prototype.hasOwnProperty.call(this.attrs, k);
};
El.prototype.getAttribute = function (k) {
  if (k === "data-q") return null;
  return Object.prototype.hasOwnProperty.call(this.attrs, k) ? this.attrs[k] : null;
};
El.prototype.select = function () {};
El.prototype.addEventListener = function () {};

const els = {};
function el(id) {
  if (!els[id]) els[id] = new El(id);
  return els[id];
}

global.window = global;
global.self = global;
global.document = {
  readyState: "complete",
  getElementById: el,
  querySelectorAll: function () { return []; },
  addEventListener: function () {},
  execCommand: function () { return true; }
};

function run(rel) {
  vm.runInThisContext(fs.readFileSync(path.join(ROOT, rel), "utf8"), { filename: rel });
}

run("docs/data/charts.js");
run("docs/matter.js");
run("docs/app.js");

/* app.js 把 oninput 挂在 #matter 上：赋值 + 触发即走完整 render() */
const input = el("matter");
input.value = query;
if (typeof input.oninput === "function") input.oninput.call(input);

const hintEl = el("matter-hint");
process.stdout.write(JSON.stringify({
  query: query,
  hint: hintEl.textContent,
  hidden: hintEl.hasAttribute("hidden"),
  label: el("matter-label").textContent,
  promptHasHint: String(el("prompt").value || "").indexOf("【问法提示】") >= 0
}));
