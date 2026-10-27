# AGENTS.md

本仓库给 coding agent 用。

## 必守

1. 排盘计算不得由 LLM 臆造；对接上游 `generateChart()` 或使用 `fixtures/`。
2. 输出断语必须可回溯：星曜位置 + 四化路径 + 规则/文献出处。
3. 文件一律 UTF-8 无 BOM。
4. 先改 `packages/hypergraph` 的确定性层，再动语义层。
5. 禁止把「吉凶绝对句」写进默认输出模板。

## 推荐工作流

1. 用 fixture 或上游引擎拿到 `chart.json`
2. `python packages/hypergraph/chart2hypergraph.py chart.json`
3. 把超图摘要喂给 Agent 提示词（`packages/agent-prompts/`）
4. 用 Skill `ziwei-network-analyst` 约束解释层

## 上游锚点

- 引擎入口：`lib/ziwei/algorithm.ts` → `generateChart()`
- 类型：`lib/ziwei/types.ts` → `ZiweiChart` / `Palace` / `Star`
- 四化：`lib/ziwei/sihua.ts`
- 格局：`lib/ziwei/patterns.ts`