# 逐年推演（时序曲线）

把一张盘按流年 + 大限推进，算出 F3/F4 的时间曲线，回答两个问题：

- **哪几年该动**（贴近大限交接，结构容易改写）
- **哪几年宜守**（远离交接且冲击脆弱低于自身基线）

## 怎么算

1. 按虚岁（年 − 出生年 + 1）定位当年所处大限（用 `daXians[].startAge/endAge`）
2. 设 `asOfYear`，让流年四化层生效
3. 逐年起超图、算四因子，得 F3（冲击脆弱）、F4（节律窗口）
4. 相对自身基线切三档：
   - **宜动窗口** `move_years`：距最近大限交接 ≤ 1 年
   - **宜守年份** `hold_years`：距交接 ≥ 3 年，且 F3 ≤ 本区间中位数
   - **冲击吃紧** `risk_years`：F3 ≥ max(0.62, 中位数 + 0.08)

用相对基线而非固定阈值，是为了不同盘之间不失效。

## 用法

```powershell
# CLI
python scripts/sweep.py --chart fixtures/sample-chart.json --from 2020 --to 2035
python scripts/sweep.py --birth 1990-01-01-0-male --from 2020 --to 2035 --svg out/curve.svg

# 随问事一起出提示包
python scripts/ask.py --birth 1990-01-01-0-male --matter "今年适合跳槽吗" --sweep 2020-2035
```

网页：http://127.0.0.1:8765/ 里填「逐年推演区间」。

## 产物

| 文件 | 内容 |
|---|---|
| `out/sweep.json` | 逐年四因子 + 交接年 + 宜动/宜守/吃紧年份 |
| `out/sweep.md` | 逐年表（可直接贴文档） |
| `out/curve.svg` | F3/F4 曲线（虚线标出大限交接年份） |

## 边界

- 流年只改当下张力，不改「你是谁」
- 曲线是**窗口提示**，不是吉凶判决
- 交接年是硬边界（大限表来自引擎），F3/F4 仍是模型分数