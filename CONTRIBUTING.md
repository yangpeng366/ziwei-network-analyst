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

- [ ] 没有硬编码 `F:\` 之外的机器路径（引擎路径请走 `ZIWEI_ENGINE_ROOT`）
- [ ] 新增文件 UTF-8 无 BOM
- [ ] 演示页仍能出白话与提示包
- [ ] README 的用法与实际命令一致

## 代码布局

- `packages/hypergraph/chart2hypergraph.py`：chart→超图→因子（纯函数，无 IO）
- `packages/plain_reading/explain.py`：白话生成
- `packages/matter_query/map.py`：事项→宫位
- `packages/matter_query/prompt_pack.py`：可粘贴提示包
- `web/server.py`：本地演示页

## 提交信息

中文或英文均可，动词开头，说明「改了什么行为」而非「改了哪些文件」。