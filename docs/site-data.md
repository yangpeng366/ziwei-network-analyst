# 静态站数据与缺盘纪律

`docs/data/charts.js` 由 `scripts/build_site.py` 生成，`scripts/check-site-drift.py` 校验它与代码生成结果一致。
两份脚本共用 `build_site.CHARTS` 这一份盘清单，也是「缺 fixture 怎么办」的唯一判据。

## 两类 fixture

| 类别 | 声明 | 缺失时的行为 |
|---|---|---|
| 仓内必需 | `ChartSpec(..., required=True)`（默认），如 `sample` | 构建打红：`BUILD FAIL`，退出 1，**不覆盖** `charts.js`；drift 校验同样打红 |
| 本地私有 | `ChartSpec(..., required=False)`，如 `real-a` / `real-b` | 显式 `WARN` 打到 stderr，并写进产物顶层 `missing_charts`；构建继续，退出 0 |

本地私有盘指 `fixtures/real-1990/`：真实生盘不入仓（`.gitignore` 已排除），因此 CI 上必然缺失，
不能把「CI 没有真实盘」当成构建失败，否则规则永远在喊狼来了。

## 关键判据

- **不再静默 skip**：以前缺盘只打印 `skip (missing)` 然后继续，站点少盘仍报 OK。
  现在缺盘要么打红，要么落进 `missing_charts`，产物里能直接看出少了哪张盘、为什么。
- **少盘可 diff**：`missing_charts` 参与 drift 比对。`charts.js` 曾经带真实盘、后来被重新生成成少盘，
  漂移校验会点名（先报「图表集合不一致」，再报「顶层字段 missing_charts」）。
- **路径不进产物**：`missing_charts[].path` 用仓内相对路径（`fixtures/...`），不写机器盘符。

## 命令

```powershell
python scripts/build_site.py                  # 缺仓内必需盘 -> 打红退出 1，不写 charts.js
python scripts/build_site.py --strict         # 本地私有盘也缺 -> 打红（本地全量站构建用）
python scripts/build_site.py --allow-missing  # 显式放行缺盘（产物不完整；WARN 仍在）
python scripts/build_site.py --selftest       # 负例自测：缺必需盘必打红、缺本地盘必入 missing_charts
python scripts/check-site-drift.py            # 缺必需盘先打红；一致 -> OK
python scripts/check-site-drift.py --selftest # 漂移/缺盘留痕/格式负例自测
```

CI 按默认口径跑：`build_site.py` + `--selftest` + `check-site-drift.py` + `--selftest`。

本地有 `fixtures/real-1990/` 时，默认构建会把真实盘写进 `charts.js`（`missing_charts` 变空）：

- 想本地看三盘全量站：跑 `build_site.py --strict`，只看不提交；
- **不要提交这份本地产物**：发布站与仓都是公开的，真实生辰不该进公开 `charts.js`；
  提交了 CI 也会按预期报漂移（CI 上没有真实盘），这就是缺盘留痕在起作用。

## 回滚

`charts.js` 是生成物，回滚只需 `git checkout -- docs/data/charts.js` 或重新跑 `build_site.py`，不要手改。
