# 与 ziwei-doushu 的差异与引用量

## 一句话
上游是**排盘引擎 + 语料**；本仓库是**解释层（四因子 / 白话 / 事项聚焦 / 提示包）**。差异大，源码引用很少，接口依赖很深。

## 差异有多大

| 维度 | ziwei-doushu | ziwei-network-analyst |
|---|---|---|
| 主责 | 确定性排盘、四化、大限、格局规则、解读语料 | 超图化、四因子、白话、事项打光、可粘贴 prompt |
| 语言 | TypeScript 为主 | Python 解释层 + Skill/Markdown |
| 是否含排盘算法 | 是 | 否（禁止 LLM 手算） |
| 默认产物 | chart / 解读 | factors + plain + matter + prompt_pack |
| 语料 | 可至海量 v4 | 默认不吞库；只按位置引用 |

## 引用了多少

1. **源码拷贝**：基本没有上游 `lib/` 算法文件进入本仓（非 fork 式拷贝）。
2. **接口依赖**：深依赖 `generateChart()` 输出的 JSON schema（宫、星、亮度、四化、大限/流年）。
3. **辅助脚本**：少量 `scripts/*.ts` 放在上游目录旁路调用，或本仓脚本 `cwd` 指向上游。
4. **语料**：可选下载 year-*.jsonl；本仓策略是「引用位置，不拟合分数」。
5. **许可引用**：README / NOTICE 标明 MIT + CC BY + 倪师非商用短引。

## Skill 能不能开源
能。Skill 是本仓工作流的说明书，MIT 即可；它告诉 agent「去调引擎、跑转换、先讲白话」，并不复制上游排盘实现。

## 无 Agent 时怎么用
跑转换后会生成 `.prompt.md`：把 System + User 整段粘到任意 AI 即可。本地可以完全不跑 LLM。