# 具体事项聚焦（不是传统占卜判决）

用户问「跳槽 / 感情 / 买房」时，不另起一套玄学占法，而是：

1. 关键词映射到相关宫位
2. 只打光这些宫上的承重星与忌压
3. 仍用 F1–F4 说话
4. 产出 `matter.plain` + 可粘贴 `prompt_pack`

## CLI

```powershell
python packages/hypergraph/chart2hypergraph.py fixtures/sample-chart.json --matter "今年适合跳槽吗"
```

会得到：
- `*.hypergraph.json`（含 `matter` / `prompt_pack`）
- `*.hypergraph.prompt.md`（直接复制给别的 AI）

## 护栏
- 不做吉凶判决
- 六亲/婚恋/健康参考受限
- 无本机 LLM 时，靠拼接提示包即可