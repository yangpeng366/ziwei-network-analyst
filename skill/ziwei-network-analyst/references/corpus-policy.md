# 语料与校准口径

## 总原则

**语料只引用位置、作 prompt 参考。**

不把 v4 断语当监督信号，不拟合 F1–F4。

## 用

- 上游 `generateChart(y,m,d,h,g)` 得结构盘（真源）
- v4 行：用 `k` / 生辰键定位「哪张盘、哪一段」；`c`=正文，`t`=字数
- Agent 需要旁证时：按位置引用短摘入 prompt（带宫位/星曜/四化路径），可走 xerj/zvec 抽样
- `c.love / c.friends / c.move` 仅作位置参考材料或人工抽查

## 不用

- 不用断语关键词或「一句话定调」软标签拟合四因子（1990×36 盘 Pearson 弱/负相关，已弃）
- 不默认加载全量 56.6GB
- 不允许「语料怎么说 → 改因子分数」

## 回归

```powershell
python F:\github\ziwei-network-analyst\scripts\test-f1-regression.py
python F:\github\ziwei-network-analyst\scripts\inspect-real-distribution.py
```

合成盘期望：`community-high > sample > community-low`。
读法阈值：`≥0.55` 协作 / `≥0.35` 拉锯 / 其余割裂。