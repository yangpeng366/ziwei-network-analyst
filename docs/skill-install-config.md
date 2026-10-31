# Skill 安装与环境配置

## 用途

本仓的 skill 是产品入口：用户或别的 agent 显式点名 `ziwei-network-analyst` 才会加载。
仓内 `skill/ziwei-network-analyst/` 只是**源**，不复制到 Codex 的 skills 目录就不会被显式调用。

## 关键配置项

| 项 | 值 | 说明 |
|---|---|---|
| 源目录 | `F:\github\ziwei-network-analyst\skill\ziwei-network-analyst` | 仓内唯一真源，改这里 |
| 安装目标 | `%USERPROFILE%\.codex-home\skills\ziwei-network-analyst` | Codex 实际加载处 |
| 安装方式 | `pwsh -File scripts/install-skill.ps1` | 复制后逐文件 SHA-256 校验 |
| 自定义目标 | `pwsh -File scripts/install-skill.ps1 -Dest <路径>` | 目录名必须是 `ziwei-network-analyst` |
| 上游排盘引擎 | `F:\github\ziwei-doushu`（可用 `ZIWEI_ENGINE_ROOT` 覆盖） | 只有要真排盘时才需要；fixture 演示不需要 |
| 本地服务 | `python scripts/win/start-demo.cmd` → `http://127.0.0.1:8765` | 可选，静态站直接开 `docs/index.html` 亦可 |

## 默认值

- 加载 skill 后按 `SKILL.md` 工作流执行：收生辰或读 `chart.json` → `scripts/ask.py`（带 `--matter` / `--sweep`）→ 读 `factors` / `plain` / `matter` / `facts` / `prompt_pack`。
- 排盘一律走上游引擎或 `fixtures/`，**禁止手算排盘**（见 `AGENTS.md`）。
- 解释只依 `facts` 盘面事实卡；星曜只在「十二宫一览」给一次，详卡只补宫义与三方关系。

## 生效环境

- 生效：本机 Codex（`%USERPROFILE%\.codex-home` 即 `C:\Users\47037\.codex-home`）。
- 不生效：CI（GitHub runner 无 `.codex-home`，`scripts/test-skill-entry.py` 会跳过同步检查，其余检查照跑）。
- 索引类工具（xerj prefix `ziwei-rules`）需手动起节点：`xerj --data-dir D:\AI-Portable\xerj-data --port 9200`，用后即停。

## 漂移自检与回滚

- 自检：`python scripts/test-skill-entry.py` —— frontmatter、仓内路径无漂、入口命令可跑、全局安装与仓内逐文件一致。
- 漂移时：重跑 `scripts/install-skill.ps1` 覆盖安装即可。
- 回滚：删除 `%USERPROFILE%\.codex-home\skills\ziwei-network-analyst` 即回到「未装、不可显式调用」状态；仓内源码不受影响，回滚用 `git revert` 撤掉对应提交。
