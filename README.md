# 紫微四因子解读层（ziwei-network-analyst）

把一张紫微命盘压成 **4 个因子**，再用**大白话**讲给你听，并针对你问的那件具体事给方向。

排盘交给成熟引擎 [ziwei-doushu](https://github.com/Renhuai123/ziwei-doushu)；本仓库只做**解释层**：
不重排盘、不编断语、不下绝对命运判断。

## 在线试玩（零安装）

**[https://yangpeng366.github.io/ziwei-network-analyst/](https://yangpeng366.github.io/ziwei-network-analyst/)**

打开即用：选盘 → 填「想问的事」→ 看白话与逐年曲线 → 复制提示词给任意 AI。
数据已预计算，不需要装 Python，也不需要排盘引擎。
## 四个因子

| 因子 | 白话 | 问自己 |
|---|---|---|
| F1 共同体感 | 你和人连得上吗 | 关系网是协作、拉锯，还是割裂 |
| F2 承重星 | 谁在扛 | 眼下扛事的是哪几颗星、落哪一宫 |
| F3 冲击脆弱 | 哪块怕撞 | 忌压热区在哪，遇变恢复成本多大 |
| F4 节律窗口 | 在换剧本吗 | 是否靠近大限交接、结构重写期 |

详见 [docs/core-factors.md](docs/core-factors.md)。

## 三种用法（选一个）

### A. 网页试玩（最省事）
双击 `scripts/win/start-demo.cmd`，浏览器打开 `http://127.0.0.1:8765/`。

- 选现成盘例，或直接填公历生辰自动排盘
- 填「想问的事」（如 今年适合跳槽吗），点「分析」
- 看完白话，点「复制提示词」，粘到任意 AI 继续深聊

### B. 命令行问事
```powershell
python scripts/ask.py --birth 1990-01-01-0-male --matter "今年适合跳槽吗"
```
产出 `out/ask.prompt.md`（给任意 AI）和 `out/ask.json`（结构化结果）。

### C. 用 Codex Skill
装上 `skill/ziwei-network-analyst`，直接对 agent 说「帮我看看今年跳槽是否合适」。
agent 会先出白话，再给分数与星@宫。

## 安装

```powershell
git clone https://github.com/<you>/ziwei-network-analyst.git
cd ziwei-network-analyst
python -m pip install -r requirements.txt   # 若有；本项目仅需标准库
```

想用自己的生辰排盘，还需要排盘引擎（可选）：

```powershell
git clone https://github.com/Renhuai123/ziwei-doushu.git F:\github\ziwei-doushu
cd F:\github\ziwei-doushu; npm install
# 告诉本项目引擎在哪
$env:ZIWEI_ENGINE_ROOT = "F:\github\ziwei-doushu"
```

没有引擎也能用：`--demo` 或网页的「现成盘」。

## 目录

| 路径 | 作用 |
|---|---|
| `packages/hypergraph/` | chart → 超图 → 四因子 |
| `packages/plain_reading/` | 易学概念 → 白话 |
| `packages/matter_query/` | 事项映射 + 可粘贴提示包 |
| `packages/agent-prompts/` | agent 输出契约 |
| `skill/ziwei-network-analyst/` | Codex Skill |
| `web/` | 本地演示页 |
| `docs/` | 因子定义、事项聚焦、与上游差异 |

## 语料策略

v4 解读语料**只引用位置、作 prompt 参考**，不用断语软标签反推因子分数。
要接全库请看 [docs/retrieval-zvec-xerj.md](docs/retrieval-zvec-xerj.md)（xerj / zvec 抽样）。

## 边界

1. 不替代排盘（因子只读引擎结果）
2. 不做绝对吉凶断言
3. 事项聚焦 = 给相关宫位打光，不是传统占卜判决
4. 六亲、婚恋、健康「参考受限」
5. MVP 不做合盘对抗、全库聚类

## 许可

本仓库 MIT；上游引擎 MIT；解读数据 CC BY 4.0；倪师原话非商用。详见 [NOTICE.md](NOTICE.md)。
与上游差异见 [docs/vs-ziwei-doushu.md](docs/vs-ziwei-doushu.md)。
## 样例输出（不想跑也能先看）

见 [docs/examples/README.md](docs/examples/README.md)：
问题「今年适合跳槽吗」的白话结论、四因子表、可粘贴提示包。
### D. 逐年曲线（哪几年该动，哪几年宜守）

```powershell
python scripts/sweep.py --birth 1990-01-01-0-male --from 2020 --to 2035 --svg out/curve.svg
```

网页里填「逐年推演区间」也能出。详见 [docs/timeline.md](docs/timeline.md)。
## 给谁用

| 你想要 | 用这个 |
|---|---|
| 一句人话讲清这盘的张力 | 网页演示 / `ask.py` |
| 问一件具体的事（跳槽、感情、买房） | `--matter "..."` 事项聚焦 |
| 知道未来十年哪几年该动、哪几年宜守 | `--sweep 2020-2035` 逐年曲线 |
| 不想装任何大模型 | 直接把生成的 `.prompt.md` 粘给任意 AI |
| 想让它变成你 agent 的能力 | 装 `skill/ziwei-network-analyst` |

## 三分钟看懂输出

1. **白话摘要**：先看这盘整体的势（协作还是割裂、谁在扛、哪里怕撞、在不在换轨期）
2. **事项聚焦**：你问的那件事落在哪几个宫、承重星是谁、忌压在哪
3. **逐年曲线**：宜动（贴着大限交接）/ 宜守（远离交接且脆弱低于自身基线）/ 冲击吃紧
4. **硬证据**：分数、星@宫、忌压数值——这些不能被 AI 改
5. **提示包**：整段复制给任意 AI，它只负责翻译与情景生成