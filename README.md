# Ziwei Network Analyst

把紫微命盘压成 **4 个核心因素** 来解释——对标「普遍权重子空间」：少即是核。

> 排盘靠代码，因子靠图论，说话靠检索，决策留给人。

## 四因子

| 因子 | 含义 |
|---|---|
| F1 共同体感 | 阿德勒社会兴趣的盘面代理：关系子图协作还是割裂 |
| F2 承重星 | 谁在扛系统（关键种 / d·s） |
| F3 冲击脆弱 | 忌路径热区与风险带宽 |
| F4 节律窗口 | 大限是否接近结构重写 |

详见 [docs/core-factors.md](docs/core-factors.md)。

## 快速开始

```powershell
python F:\github\ziwei-network-analyst\packages\hypergraph\chart2hypergraph.py F:\github\ziwei-network-analyst\fixtures\sample-chart.json
```

看输出里的 `factors.one_liner`。

## 布局

| 路径 | 作用 |
|---|---|
| `packages/hypergraph/` | chart→超图→四因子 |
| `packages/agent-prompts/` | 四因子解释契约 |
| `skill/ziwei-network-analyst/` | Codex Skill |
| `docs/core-factors.md` | 收束决策 SSOT |
| `fixtures/` | 演示盘 |

## 检索（不吞 56GB）

- xerj：规则/出处/docs（prefix `ziwei-rules`）
- zvec：可选，结构指纹 + 抽样断语
- 见 [docs/retrieval-zvec-xerj.md](docs/retrieval-zvec-xerj.md)

## 边界

1. 不替代 `ziwei-doushu` 排盘
2. 不做绝对断语
3. MVP 不做合盘对抗、全库聚类、论文展览

## 许可

本仓库 MIT；上游引擎 MIT；解读数据 CC BY 4.0；倪师原话非商用。

## 具体事项 + 无 Agent 用法

```powershell
python packages/hypergraph/chart2hypergraph.py fixtures/sample-chart.json --matter "今年适合跳槽吗"
```

会生成：
- `*.hypergraph.json`（含 `matter` / `prompt_pack`）
- `*.hypergraph.prompt.md`（复制给任意 AI）

与上游差异见 [docs/vs-ziwei-doushu.md](docs/vs-ziwei-doushu.md)；许可说明见 [NOTICE.md](NOTICE.md)。