# adversarial-interview · 对抗性技术面试材料生成

> An Agent Skill that turns resume PDFs into a full set of adversarial technical-interview materials (guide + printable scorecard + Q&A cards). Chinese-language output; runnable in Claude Code or any agent framework.

给定一份或多份简历 PDF，产出三件套（同目录、互相以本地相对路径链接、完全自包含）：

- **完整指南** `<slug>_guide.md` — 画像与可信度、**亮点/真实强项**、关键红旗、开场态度题、核心验伪题（每题：**从简历项目起手的提问阶梯 L1 项目切入 → L2 设计决策 → L3 硬核验伪**、期望的优质回答分点、及格线、典型露馅、追问）、补充探针。
- **现场评分卡** `<slug>_scorecard.html` — 一位候选人一页 A4，每题「强/中/露馅」勾选位 + 判分线索，可直接打印。
- **攻防卡片** `<slug>_qa_cards.html` — 标签页切换、答案一键折叠自测、亮点/红旗与每题分层阶梯分区着色、每人链到原始简历 PDF。

引擎是一个自适应多阶段工作流：读简历 → 判研（画像/强项/红旗/待拷问技术域）→ 分域拷问 → 收敛出挂靠简历项目、分层提问的核心验伪题并写答案键 → 事实核查并修正。评价均衡如实：戳穿注水的同时如实肯定真本事，很强/很弱都不硬凑、不强求优缺点对称。

## 目录结构

```
adversarial-interview/
  SKILL.md                     技能入口（开放 Agent Skills 格式：frontmatter + 指令）
  scripts/
    extract_pdf.py             简历 PDF → 文本
    analyze.js                 Claude Code 原生多智能体 Workflow 引擎
    analyze_portable.py        运行无关的参考编排（可接任意模型）+ --single 回退
    render.py                  payload.json → 三件套（零依赖、运行无关）
  templates/                   qa_cards / scorecard 的自包含 HTML 模板
  reference/
    pipeline-spec.md           运行无关的流水线契约（阶段/提示/JSON schema）
    writing-norms.md           输出写作规范
  workspace/                   本地工作区（简历与产物，均不入库）
    inbox/  output/  BG/
```

## 快速开始

**在 Claude Code 里**：把简历 PDF 放进 `workspace/inbox/`，对 Claude 说「用 adversarial-interview 技能处理 inbox 里的简历」。技能按 `SKILL.md` 执行：抽取文本 → 跑 `scripts/analyze.js` 工作流 → `render.py` 渲染到 `workspace/output/<slug>/`。

**在其它 agent 系统 / 纯脚本里**（运行无关，见 `reference/pipeline-spec.md`）：

```bash
python scripts/extract_pdf.py workspace/inbox/resume.pdf --out resumes.json
# 接入模型：ADV_LLM_PROVIDER=openai|anthropic|custom（详见 analyze_portable.py 头部）
ADV_LLM_PROVIDER=openai python scripts/analyze_portable.py --resumes resumes.json --out payload.json
python scripts/render.py payload.json workspace/output/demo demo
```

`analyze_portable.py` 只依赖一个 `call_llm(system, user, schema)` 结构化输出回调（内置 OpenAI/Anthropic 适配，或挂自己的模型）。编排能力有限时加 `--single` 单调回退（一次调用产出全部，深度略降、结构一致）。渲染层与运行时无关，任何路径产出的 `payload.json` 都能渲染。

## 隐私

简历属敏感个人信息。`workspace/`（含真实简历与生成产物）已在 `.gitignore` 中排除，发布时不会入库；`*.pdf` 另有全局兜底忽略。分享示例前请先脱敏。

## 许可与署名

MIT License，© 2026 J.C.（张锦程）。详见 `LICENSE`。
