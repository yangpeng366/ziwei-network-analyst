# 紫微四因子解读层（ziwei-network-analyst）

**问一件具体的事 → 拿到一段能直接粘给任意 AI 的提示词 → 让它用易学白话给你解释。**

排盘交给成熟引擎 [ziwei-doushu](https://github.com/Renhuai123/ziwei-doushu)；本仓库只做**解释层**：
不重排盘、不编断语、不下绝对命运判断。

## 在线试玩（零安装）

**[https://yangpeng366.github.io/ziwei-network-analyst/](https://yangpeng366.github.io/ziwei-network-analyst/)**

选盘 → 填「想问的事」→ 看白话与逐年曲线 → 复制提示词给任意 AI。
数据已预计算，不需要装 Python，也不需要排盘引擎。

## 怎么用

**命令行（自己的盘）**
```powershell
python scripts/ask.py --birth 1990-01-01-0-male --matter "今年适合跳槽吗"
```
产出 `out/ask.prompt.md`（直接粘给任意 AI）与 `out/ask.json`（结构化结果）。

**网页（自己的盘）**
双击 `scripts/win/start-demo.cmd` → http://127.0.0.1:8765/ 。

**Codex Skill**
装 `skill/ziwei-network-analyst`，对 agent 说「帮我看看今年跳槽是否合适」。
改了仓内 skill 需重装才生效：`pwsh -File scripts/install-skill.ps1`（装到 `%USERPROFILE%\.codex-home\skills`；`scripts/test-skill-entry.py` 会查两端是否漂移）。

**想知道哪几年该动、哪几年宜守**（可选）
```powershell
python scripts/sweep.py --birth 1990-01-01-0-male --from 2020 --to 2035 --svg out/curve.svg
```

## 提示词里带了什么

这是本项目的关键：**不让 LLM 空谈**。生成的提示词包含

| 段落 | 作用 |
|---|---|
| 用户问的事 + 事项聚焦 | 先把问题落到相关宫位 |
| **盘面事实卡** | 十二宫一览（宫名/与命宫关系/主星亮度/辅星/生年四化/自化）、四化飞入、大限、相关宫详卡（宫义）——**解释的唯一依据**。星曜只给一次，不重复铺 |
| 四因子与硬证据 | 分数、承重星@宫、忌压数值，AI 不得改 |
| 逐年推演（可选） | 宜动 / 宜守 / 冲击吃紧 |
| 怎么答 + 不要做 | 结论先行、点名宫位星曜、白话解释、给可逆小动作、不编造 |

问题命中不了关键词时，不再逐宫铺开十二张详卡，只给十二宫一览 + 一行宫义速查，交给 LLM 自行取用——省下的上下文留给真正要读的部分。

## 四个因子

| 因子 | 白话 | 问自己 |
|---|---|---|
| F1 共同体感 | 你和人连得上吗 | 关系网是协作、拉锯，还是割裂 |
| F2 承重星 | 谁在扛 | 眼下扛事的是哪几颗星、落哪一宫 |
| F3 冲击脆弱 | 哪块怕撞 | 忌压热区在哪，遇变恢复成本多大 |
| F4 节律窗口 | 在换剧本吗 | 是否靠近大限交接、结构重写期 |

详见 [docs/core-factors.md](docs/core-factors.md)。样例见 [docs/examples/README.md](docs/examples/README.md)。

## 安装

```powershell
git clone https://github.com/yangpeng366/ziwei-network-analyst.git
cd ziwei-network-analyst
```
核心功能仅需 Python 3.9+ 标准库。

要排自己的盘，再装引擎（可选）：

```powershell
git clone https://github.com/Renhuai123/ziwei-doushu.git F:\github\ziwei-doushu
cd F:\github\ziwei-doushu; npm install
$env:ZIWEI_ENGINE_ROOT = "F:\github\ziwei-doushu"
```
没有引擎也能用：`--demo` 或网页的「现成盘」。

## 目录

| 路径 | 作用 |
|---|---|
| `packages/hypergraph/` | chart → 超图 → 四因子 |
| `packages/plain_reading/` | 易学概念 → 白话 |
| `packages/matter_query/` | 事项映射、事实卡、提示包 |
| `packages/timeline/` | 逐年推演与曲线 |
| `skill/ziwei-network-analyst/` | Codex Skill |
| `web/` `docs/` | 本地演示页、文档与静态站 |

## 边界

1. 不替代排盘（因子只读引擎结果）
2. 不做绝对吉凶断言
3. 事项聚焦 = 给相关宫位打光，不是传统占卜判决
4. 六亲、婚恋、健康「参考受限」
5. 语料只引用位置作 prompt 参考，不用断语软标签反推因子分数

## 许可

本仓库 MIT；上游引擎 MIT；解读数据 CC BY 4.0；倪师原话非商用。详见 [NOTICE.md](NOTICE.md)。
与上游差异见 [docs/vs-ziwei-doushu.md](docs/vs-ziwei-doushu.md)。
