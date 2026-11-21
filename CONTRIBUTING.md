# 参与 Ziwei Network Analyst

感谢参与。本项目定位是**解释层**：确定性算因子，LLM 只做翻译。

## 规矩（不可破）

1. **不重排盘**：星曜位置、亮度、四化、大限只信 `ziwei-doushu` 引擎输出或 `fixtures/`。
2. **不拟合软标签**：禁止用解读语料的断语软标签去调四因子权重。
3. **不绝对断言**：只写势能方向、风险带宽、可干预点。
4. **不改分数**：LLM 只能润色措辞，不能改 `score` / `reading`。
5. **语料只引用位置**：短摘 + 出处；倪师原话非商用。
6. **六亲参考受限**：不作为唯一依据。

## 改因子后必跑

```powershell
python scripts/test-f1-regression.py
```

它会校验 高协作 > 样本 > 低协作 的排序。挂了不要提交。

## 提交前自检

```powershell
python scripts/check-no-abs-paths.py            # 禁盘符硬编码 + 每个 .ps1 均 dot-source repo-paths.ps1 + 文档正文（docs/、skill/、仓根 *.md）禁绝对路径
python scripts/check-no-abs-paths.py --selftest # 规则自身的负例自测（负例打红 / 围栏放行 / 白名单放行 / URL 不误判）
python scripts/check-matter-lexicon.py            # 速查表与 catalog 生成结果逐字一致（改词/多行/少行会打红并点名行号）
python scripts/check-matter-lexicon.py --selftest # 负例自测（CRLF 只归一、BOM/改词/多行/末尾空行必红）
python scripts/check-site-drift.py                # 静态站数据与生成结果一致（集合/顺序/字段/顶层字段/缺盘留痕）
python scripts/check-site-drift.py --selftest     # 负例自测（格式异常必红，BOM/无分号/空白变体放行）
python scripts/build_site.py --selftest           # 缺盘纪律自测（缺仓内必需盘必红，缺本地私有盘必入 missing_charts）
```

缺 fixture 不再静默 skip：仓内必需盘缺了构建直接打红且不写 `charts.js`；本地私有盘（`fixtures/real-1990/`，
不入仓）缺了会显式 WARN 并记进产物顶层 `missing_charts`，让少盘可 diff。细则见 `docs/site-data.md`。

改了任一 `check-*.py` 的规则（正则 / 放行口 / 扫描范围 / 比对口径）必须跑对应 `--selftest`，CI 也会跑。
只在真实文件上「看着没报错」不算验证——规则被改成永远 OK 也是没报错。

- [ ] 没有硬编码机器路径：仓库内路径由脚本自身位置派生，引擎路径请走 `ZIWEI_ENGINE_ROOT`
- [ ] PowerShell 脚本先 `. (Join-Path $PSScriptRoot 'lib\repo-paths.ps1')` 取 `$RepoRoot` / `$EngineRoot`，不写盘符
- [ ] `.ps1` 只写 ASCII（Windows PowerShell 5.1 把无 BOM 文件按 ANSI 解码，中文会解析失败；要写中文请落到 `.md`）
- [ ] 新增文件 UTF-8 无 BOM
- [ ] 演示页仍能出白话与提示包
- [ ] README 的用法与实际命令一致

## 代码布局

- `packages/hypergraph/chart2hypergraph.py`：chart→超图→因子（纯函数，无 IO）
- `packages/plain_reading/explain.py`：白话生成
- `packages/matter_query/map.py`：事项→宫位
- `packages/matter_query/prompt_pack.py`：可粘贴提示包
- `scripts/lib/repo-paths.ps1`：仓根 / 引擎根的单一派生点（`$RepoRoot`、`$EngineRoot`、`Assert-EngineRoot`）
- `web/server.py`：本地演示页

## 提交信息

中文或英文均可，动词开头，说明「改了什么行为」而非「改了哪些文件」。