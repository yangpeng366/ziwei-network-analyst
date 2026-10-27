---
name: ziwei-network-analyst
description: 用四核心因素解释紫微命盘（共同体感/承重星/冲击脆弱/节律窗口），并自动给出易学白话版；支持具体事项聚焦，并可在无 LLM 时只拼接可粘贴提示包。排盘走 ziwei-doushu 或 fixture，推演走 chart2hypergraph（自带 plain/matter/prompt_pack）。用于紫微斗数、命盘韧性、社会兴趣代理、大限窗口、具体事询问；不用于百科式全维批命，也不用断语软标签拟合因子。
---

# Ziwei Network Analyst

抓低维核心，不铺散。对用户默认先出**白话版**。若用户问具体事，先出**事项聚焦**。

## 核心

先读仓库 `docs/core-factors.md`。

只解释四因子：

1. F1 共同体感（社会兴趣代理；宫名含交友/仆役/夫妻/迁移）
2. F2 承重星
3. F3 冲击脆弱（活跃层：本命+当前大限+流年）
4. F4 节律窗口（大限边界，不依赖已下线的 daXian.siHua）

## 工作流

1. 收生辰 / 读 chart.json（禁止手算排盘）
2. 跑转换（有具体事就带 `--matter`）：

```powershell
python F:\github\ziwei-network-analyst\packages\hypergraph\chart2hypergraph.py <chart.json> --matter "今年适合跳槽吗"
```

3. 读输出 JSON：
   - `factors`：分数与读法（硬证据）
   - `plain`：易学白话
   - `matter`：具体事项打光（宫位/承重/忌压）
   - `prompt_pack`：无本机 LLM 时，把 `user`（或 `.prompt.md`）粘到任意 AI
4. 对用户回复顺序：
   - 有事项：先 `matter.plain`
   - 再 `plain.summary` + 四段白话
   - 再补分数/星@宫/忌压
   - 最后可觉察建议
5. 若当前环境不方便跑 agent：直接把 `*.hypergraph.prompt.md` 交给用户去问别的 AI
6. xerj/zvec 只为因子补出处；**语料只引用位置、作 prompt 参考**

改因子权重前先跑：

- `python F:\github\ziwei-network-analyst\scripts\test-f1-regression.py`

## 白话 / 事项 / 提示包从哪来

- 白话：`packages/plain_reading/explain.py`
- 事项：`packages/matter_query/map.py`
- 提示包：`packages/matter_query/prompt_pack.py`
- 均已挂进 `chart2hypergraph.py`，默认写出 `.prompt.md`
- LLM 只可润色通顺，不可改因子分数，不可改成绝对命运判断

## 护栏

- 不替代排盘
- 不输出绝对命运判断
- 具体事项 = 宫位打光，不是传统吉凶占断
- 不把 13 维/全量语料当默认依赖
- 不用断语软标签拟合四因子
- 倪师原话短引+出处，非商用
- 六亲「参考受限」