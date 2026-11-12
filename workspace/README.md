# 工作区（本地私有，不入库）

面试材料的实际输入与产物放这里；整个 `workspace/` 已被 `.gitignore` 排除（简历属个人隐私）。

## 约定

- `inbox/` — 新简历 PDF 丢这里（待处理）。
- `output/<slug>/` — 每批产物：三件套 + 简历副本。`<slug>` 命名 `<YYYYMMDD>_<批次名>`（例 `20260709_shanghai_ai`）。
  - `<slug>_guide.md`、`<slug>_scorecard.html`、`<slug>_qa_cards.html`
  - 原简历 PDF 复制进同目录，使卡片里「原始简历」本地链接可用。
- `BG/` — 首个人工样例（2026-07-09 两份测试简历及其产物），保留备参。

## 处理流程

1. 简历放进 `inbox/`。
2. 让 Claude：「用 resume-grill 技能处理 inbox 里的简历」；或按仓库 `README.zh-CN.md` 的纯脚本三步跑。
3. 打开 `output/<slug>/<slug>_qa_cards.html` 阅读/自测；打印 `..._scorecard.html`（A4）现场打分；`..._guide.md` 深挖。
4. 处理完的简历从 `inbox/` 移到对应 `output/<slug>/`，卡片里的「原始简历」链接即生效。

## 判分基调

先用「初级/应届标尺」把与在读重叠的短期经历、大量「参与」压到真实 ownership 边界。诚实降级给分：候选人主动承认「课程 demo / 没上生产 / 只做到报告层」是强信号，不扣分。同时如实肯定真实强项（见指南「亮点」区），不为对抗而对抗。
