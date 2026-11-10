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
- 同分时主事项按目录顺序取先者：事业 → 钱财 → 亲密 → 身体 → 心态 → 安家 → 外出 → 协作 → 考试 → 家庭
- `general` 为兜底类：没有任何具体类别命中时才启用，此时 `matched=False`，
  事实卡展开十二宫交由解读方自行取用

### 口语化覆盖（关键词要跟着人说话的方式走）

真实用户很少用书面词。问「要不要裸辞」「被裁了怎么办」「他是不是变心了」「睡不着怎么办」
时，目录里若没有对应口语词，就会落 `general` 兜底 —— 事实卡只能展开十二宫，解读会失焦。
所以目录同时收口语说法（裸辞 / 被裁 / 变心 / 异地恋 / 睡不着 / 摆烂 / 靠谱 / 卖房 / 攒钱…）。
新增口语词后跑 `python scripts/test-matter-mapping.py`：语料逐条核对 + 前后端逐字比对，
既保证新问法能命中，也保证旧问法不被新词误伤。

### 多标签

一句「要不要辞职去外地发展」同时命中事业职场与外出变动，
输出为 `事业职场＋外出变动`，宫位取并集，不再只取其一。

### 兜底：问法没被识别（别让用户以为“看全盘”是回答）

一个问题落到 `general`（`matched=False`）时，界面不能默默按普通类别展示。现在三处同源提示：

| 出口 | 位置 | 行为 |
| --- | --- | --- |
| Python | `matter_query/map.py` 的 `_fallback_focus` | 附带 `suggestions`（按目录顺序跳过 general、每类前 4 词）与 `hint` |
| CLI | `scripts/ask.py` | 在 `事项：整体态势` 后单独打一行 `hint`，并写入提示包 `【问法提示】` |
| 静态站 | `docs/matter.js` + `docs/app.js` | 同算法产出，渲染到 `#matter-hint`（命中具体类别时清空并隐藏） |

文案模板、分隔符、省略号、示例个数全部存在 `catalog.json` 的 `fallback_hint`，
两边只做渲染 —— 不允许各写一套字面量；`scripts/test-matter-fallback.py` 会拿真实 DOM 文本
与 CLI 输出逐字比对。

只有时间词（什么时候 / 哪年 / 近期…）而没有类别命中时，同样落 `general`，走同一提示。

### 速查表（generated，勿手改）

`docs/matter-lexicon.md` 由 `scripts/gen-matter-lexicon.py` 从同一份 catalog 生成：
每类一节（宫位 / 因子 / 镜头 / 关键词全列 / 3 条示例问法），general 单列说明兜底身份。
CI 用 `scripts/check-matter-lexicon.py` 做逐字防漂移。

## CLI

```powershell
python packages/hypergraph/chart2hypergraph.py fixtures/sample-chart.json --matter "今年适合跳槽吗"
```

会得到：
- `*.hypergraph.json`（含 `matter` / `prompt_pack`）
- `*.hypergraph.prompt.md`（直接复制给别的 AI）

## 回归

```powershell
python scripts/test-matter-mapping.py   # 问法语料 + 兜底提示字段 + 前后端一致性
python scripts/test-matter-fallback.py  # 兜底提示：CLI 与站点 DOM 文本逐字一致
python scripts/check-matter-lexicon.py  # 速查表未漂移（catalog 才是真源）
python scripts/test-static-page.py      # 静态站元素 id 齐备
```

语料在 `fixtures/question-corpus.json`，改规则须同步复核。
现有 69 条，含口语化（裸辞 / 被裁 / 变心 / 睡不着 / 摆烂 / 靠谱 / 卖房…）、时间词单独命中
（什么时候比较关键 → general 兜底 + 提示）与复合型
（基金亏损了想换工作 / 为了跳槽去外地 / 一边带娃一边想跳槽 / 睡不着又压力大…）。

## 护栏

- 不做吉凶判决
- 六亲/婚恋/健康参考受限
- 无本机 LLM 时，靠拼接提示包即可
