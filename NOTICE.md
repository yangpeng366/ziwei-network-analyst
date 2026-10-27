# NOTICE

## 本仓库（ziwei-network-analyst）
- License: MIT
- Copyright: 2026 yangpeng366
- 内容：四因子解释层、白话层、事项聚焦、可粘贴提示包、Codex Skill

## 上游引擎依赖（不内嵌源码）
- 项目：[Renhuai123/ziwei-doushu](https://github.com/Renhuai123/ziwei-doushu)
- License: MIT（代码）
- 关系：运行时调用 `generateChart()` / 使用其输出的 chart.json
- **本仓库几乎不 vendoring 上游源码**；差异在「解释层」而非「排盘引擎」

## 解读语料（可选，默认不入库）
- 上游 v4 解读数据：CC BY 4.0（以 DATASET-LICENSE 为准）
- 本项目策略：只引用位置、作 prompt 参考；不把断语软标签拟合进四因子
- 若分发抽样语料，须保留 CC BY 署名

## 倪师等传统文本
- 仅允许短引 + 出处
- 非商用；不作绝对命运断言

## Skill 开源口径
- `skill/ziwei-network-analyst` 可随本仓库 MIT 开源
- Skill 是工作流说明书 + 护栏，不是排盘算法副本