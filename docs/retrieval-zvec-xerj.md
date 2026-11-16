# 检索策略：xerj + zvec

## 原则

**能检索就别猜；能抽样就别吞盘。**

## xerj（本机已装）

用途：规则、出处、设计文档、抽样 JSONL 的 BM25/hybrid。

建议 prefix：

| prefix | 内容 |
|---|---|
| `ziwei-rules` | 本仓库 docs + 证据卡 + 上游格局/四化摘要 |
| `ziwei-samples` | v4.0 按年抽样（如每年 100 盘）或结构模板库 |

起节点（auth 默认开；admin key 由 xerj 自行到 data dir 读，不必手抄到环境变量）：

```powershell
$env:PATH = "$env:LOCALAPPDATA\Programs\xerj;$env:PATH"
xerj --data-dir D:\AI-Portable\xerj-data --port 9200   # 用完即停
```

索引本仓库文档（一个 prefix 只绑一个源目录）：

```powershell
xerj autoindex D:\gitAll\ziwei-network-analyst\docs --prefix ziwei-rules
```

若报 `--prefix ziwei-rules already indexes a different folder`（历史 `F:\github\...` 路径残留），
换源目录必须显式接力，否则不会写入：

```powershell
xerj autoindex D:\gitAll\ziwei-network-analyst\docs --prefix ziwei-rules --replace-prefix
```

检索：

```powershell
xerj search --prefix ziwei-rules "忌 = 关键失效算子"
```

**实测（2026-11-16）**：`--replace-prefix` 重建后 23 files / 122 records / 2 datasets
（`ziwei-rules-docs`、`ziwei-rules-examples`）；重建前只有 7 files / 9 records，源目录还指向已不存在的
`F:\github\ziwei-network-analyst\docs`。关键句可命中：`忌 = 关键失效算子` → `core-factors.md`，
`唯一数据源 catalog.json version v2` → `matter-lexicon.md:4`。

**查询写法**：写一句原文连续片段最好命中；把多个中文词用空格拼成 OR 时弱命中会混进
`app.js` / `index.html`（score `1.00`）。看到 `1.00` 就换成原文整句重查，别当成语料缺失。

## v4.0 语料怎么用（1990 年样例已落地）

本地样例：`data/v4-sample/year-1990.jsonl`（约 742MB，gitignore）。

每行压缩字段：

| 字段 | 含义 |
|---|---|
| `k` | `YYYY-MM-DD-hour-gender` |
| `y/m/d/h/g` | 生辰 |
| `ms` | 命主星名 |
| `t` | **各主题字数**（int） |
| `c` | **各主题正文**（string） |

主题键：`overview personality love career wealth health family children move friends home spirit parents`

**正确用法**

1. 用 `y/m/d/h/g` 调上游 `generateChart()` 得结构盘
2. 本仓库算四因子
3. `c.love / c.friends / c.move` 只引用位置、作 prompt 参考（短摘+出处），**不**当 F1 回归标签

**错误用法**

- 把整段断语关键词频率当 ground truth（已实测：与 F1 Pearson 弱负相关，噪声大）
- 默认加载全量 56.6GB

## zvec（可选）

结构指纹 → 短解读。先 fixtures + 小样本。

## 与 Agent 的接口

1. 先算超图/`factors`
2. xerj 取规则证据
3. 可选：同结构 `c.*` 短摘
4. LLM 只翻译，标注 `retrieval`