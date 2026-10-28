---
name: ziwei-network-analyst
description: 回答用户关于紫微命盘的具体问题：把盘压成四因子（共同体感/承重星/冲击脆弱/节律窗口），给易学白话解释与具体事项聚焦，并产出可直接粘贴给任意 AI 的提示包。排盘走 ziwei-doushu 或 fixture，推演走 chart2hypergraph（自带 plain/matter/facts/prompt_pack）。用于紫微斗数、问事、命盘韧性、社会兴趣代理、大限窗口；不用于百科式全维批命，也不用断语软标签拟合因子。
---

# Ziwei Network Analyst

用户问一件具体的事 → 给他**能听懂、能落地**的回答。

## 核心

先读仓库 `docs/core-factors.md`。

只解释四因子：

1. F1 共同体感（社会兴趣代理）
2. F2 承重星
3. F3 冲击脆弱（活跃层：本命+当前大限+流年）
4. F4 节律窗口（大限边界，不依赖已下线的 daXian.siHua）

## 工作流

1. 收生辰 / 读 chart.json（禁止手算排盘）
2. 跑转换（有具体事就带 `--matter`，要时间线就带 `--sweep`）：

```powershell
python <repo>/scripts/ask.py --birth 1990-01-01-0-male --matter "今年适合跳槽吗"
python <repo>/scripts/sweep.py --chart <chart.json> --from 2020 --to 2035 --svg out/curve.svg
```

3. 读输出：
   - `factors`：分数与读法（硬证据）
   - `plain`：易学白话
   - `matter`：具体事项打光（宫位/承重/忌压）
   - `facts`：盘面事实卡（十二宫一览、四化飞入、相关宫详卡）——**解释的唯一依据**
   - `prompt_pack`：可直接粘给任意 AI 的 System + User
4. 回给用户时：**先给结论，再讲依据（点名宫位星曜），再给 2-3 条可逆小动作**，末尾免责
5. 若当前环境不方便跑 agent：直接把 `*.prompt.md` 交给用户去问别的 AI

## 事实回溯（硬规矩）

- 星曜、四化、年份只能取自 `facts` 里整理的盘面事实
- 关键词归类可能不全；命中不准时，LLM 可依十二宫一览自行取用其他宫
- 宫名口径不一（交友/仆役/奴仆同宫）以本盘实际名称为准
- 禁止编造古籍原文与盘上没有的星曜

## 白话 / 事项 / 提示包从哪来

- 白话：`packages/plain_reading/explain.py`
- 事项：`packages/matter_query/map.py`
- 事实卡：`packages/matter_query/facts.py`
- 提示包：`packages/matter_query/prompt_pack.py`
- 均已挂进 `chart2hypergraph.py` 与 `scripts/ask.py`
- LLM 只可润色通顺，不可改因子分数，不可改成绝对命运判断

## 护栏

- 不替代排盘
- 不输出绝对命运判断
- 具体事项 = 宫位打光，不是传统吉凶占断
- 不把 13 维/全量语料当默认依赖
- 不用断语软标签拟合四因子
- 倪师原话短引+出处，非商用
- 六亲「参考受限」

## 仓库位置

默认 `F:\github\ziwei-network-analyst`；若不存在，先找环境变量 `ZIWEI_REPO`，
或 `C:\Users\<you>\.codex-home\skills\ziwei-network-analyst` 的上级即本仓副本。