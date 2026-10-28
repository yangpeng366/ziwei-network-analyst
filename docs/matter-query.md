# 具体事项聚焦（不是传统占卜判决）

用户问「跳槽 / 感情 / 买房」时，不另起一套玄学占法，而是：

1. 关键词映射到相关宫位
2. 只打光这些宫上的承重星与忌压
3. 仍用 F1–F4 说话
4. 产出 `matter.plain` + 可粘贴 `prompt_pack`

## 映射规则

目录（类别、关键词、宫位、关注因子）唯一存放于
`packages/matter_query/catalog.json`，两端共用：

- Python 侧：`packages/matter_query/map.py`
- 静态站侧：`docs/matter.js`（同算法，由 `scripts/test-matter-mapping.py` 逐字比对）

### 打分

- 关键词按长度加权：1 字 1.0 / 2 字 1.5 / 3 字及以上 2.0（越具体越重）
- 同类别命中多个关键词，再乘覆盖系数 `1 + 0.25 × (命中数 - 1)`
- 得分最高者为**主事项**；得分 `≥ max(1.5, 主分 × 0.4)` 的其余类别算**兼看**
- 主事项与兼看的宫位取并集（上限 6 宫），关注因子取并集（上限 5 项）
- 时间问句（什么时候 / 哪年 / 近期…）补入 `F4_tempo`
- `general` 为兜底类：没有任何具体类别命中时才启用，此时 `matched=False`，
  事实卡展开十二宫交由解读方自行取用

### 多标签

一句「要不要辞职去外地发展」同时命中事业职场与外出变动，
输出为 `事业职场＋外出变动`，宫位取并集，不再只取其一。

## CLI

```powershell
python packages/hypergraph/chart2hypergraph.py fixtures/sample-chart.json --matter "今年适合跳槽吗"
```

会得到：
- `*.hypergraph.json`（含 `matter` / `prompt_pack`）
- `*.hypergraph.prompt.md`（直接复制给别的 AI）

## 回归

```powershell
python scripts/test-matter-mapping.py   # 问法语料 + 前后端一致性
python scripts/test-static-page.py      # 静态站元素 id 齐备
```

语料在 `fixtures/question-corpus.json`，改规则须同步复核。

## 护栏

- 不做吉凶判决
- 六亲/婚恋/健康参考受限
- 无本机 LLM 时，靠拼接提示包即可