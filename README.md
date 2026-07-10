# resume-grill · 简历拷打

> 一个 Agent Skill：喂进一份或多份简历 PDF，产出「面试指南 + 可打印评分卡 + 攻防卡片」三件套。提问从简历里的真实项目起手、层层加压，答案键经事实核查。**产物语言自动跟随简历**（中文简历出中文、英文简历出英文），可在 Claude Code 或任意 agent 框架里跑。

评价均衡如实：戳穿注水的同时也如实肯定真本事，很强/很弱都不硬凑、不强求优缺点对称。







## 你会得到什么

三件套写进同一目录，互相以本地相对路径链接、完全自包含（可直接 `file://` 打开）：

- **完整指南** `<slug>_guide.md` — 画像与可信度、真实亮点、关键红旗、开场态度题，以及每道核心验伪题的「L1 项目切入 → L2 设计决策 → L3 硬核验伪」提问阶梯、期望的优质回答（分点）、及格线、典型露馅、追问。
- **现场评分卡** `<slug>_scorecard.html` — 一位候选人一页 A4，每题「强/中/露馅」勾选位 + 判分线索，直接打印现场用。
- **攻防卡片** `<slug>_qa_cards.html` — 按候选人切标签，答案一键折叠自测，亮点/红旗与分层阶梯分区着色，每人链回原始简历 PDF。

引擎是一个自适应多阶段工作流：读简历 → 判研（画像/强项/红旗/待拷问技术域）→ 分域拷问 → 收敛出挂靠简历项目、分层提问的核心验伪题并写答案键 → 事实核查并修正。对任意岗位/简历都适用，无需为每份简历重写题目。

## 看看效果

`examples/agent_engineer_demo/` 是一份**完全脱敏**的示例简历（虚构「张三」，某 Agent / AI Infra 岗，2 年经验）跑出的真实三件套——[指南](examples/agent_engineer_demo/agent_engineer_demo_guide.md)、[评分卡](examples/agent_engineer_demo/agent_engineer_demo_scorecard.html)、[攻防卡片](examples/agent_engineer_demo/agent_engineer_demo_qa_cards.html)（html 用浏览器打开）。它戳中的点，例如：

> **关键红旗**：「Agent 开发工程师（2 年）」注水——真实全职工程仅一段约 8 个月，其余两段都落在硕士就读窗口内（兼职/暑期实习）；「2 年」是把在校经历拼进去凑的。
>
> **技能栈与项目对不上**：技能列了 Redis、ClickHouse，但三个项目实际出现的库是 PostgreSQL、InfluxDB——是真在生产用过还是「了解过」需当场戳穿。

核心验伪题从简历项目起手、分层加压，例如围绕其 LLM 网关经历：

> **L1 项目切入** → 一个请求从进入网关到返回上游响应经过哪些环节，哪几块是你写的？
> **L2 设计决策** → 用户级限流你限的是 QPS 还是 Token 预算？计数落在 Redis 还是 Postgres？
> **L3 硬核验伪** → 流式转发下 Token Usage 怎么算准并计费（OpenAI 流默认不带 usage、客户端中途断连、非兼容 provider 不给 usage 各怎么处理）？成本怎么按请求当时价格算、不被后来的调价追溯改写？
>
> 每题附「期望的优质回答（分点）→ 及格线 → 典型露馅 → 追问」，答案键经事实核查阶段修正。

## 快速开始

**1. 装一次**——一条命令，跨平台，无需 PowerShell：
```
python scripts/install.py
```
自动装进检测到的 agent（Claude Code / Codex …）。改完技能后重跑一次即可。

**2. 用**——装完新开一个会话，把简历 PDF **直接拖进对话**，说一句「拷打这份简历」即可（多份就都拖进来）。Agent 会自动把文件纳入工作区、跑完流水线，并**直接回给你三件套的本地链接**，不用翻文件夹。

产物在 `workspace/output/<slug>/`：`_qa_cards.html`（阅读/自测）、`_scorecard.html`（A4 打印现场打分）、`_guide.md`（深挖）。

## 装到哪个 agent（Codex / Claude Code / 其它）

`SKILL.md` 是跨 agent 通用标准，同一个技能目录在多种 agent 里都能直接识别、按描述模糊触发。`install.py` 默认装进所有检测到的 agent，也可指定：

| 命令 | 目标 |
| --- | --- |
| `python scripts/install.py` | 自动：所有检测到的 agent |
| `python scripts/install.py --claude` | `~/.claude/skills/resume-grill`（Claude Code / Claude.ai / Agent SDK） |
| `python scripts/install.py --codex` | `~/.codex/skills/resume-grill`（Codex CLI） |
| `python scripts/install.py --all` | 上述全部 |
| `python scripts/install.py --target <dir>` | 任意 agent 的 skills 目录 |

装完在该 agent 里新开会话，凭描述模糊触发（「拷打这份简历」等）。不支持 skills 的框架：走下面的纯脚本三步。

## 多语言

产物语言默认自动判定，与简历一致——中文简历出中文、英文简历出英文，连评分卡与卡片的界面文案也随之本地化。想强制某种语言：让 Claude「用英文输出」，或纯脚本加 `--lang en`（值为 `zh`/`en`/ISO 码/`auto`）。界面壳内置中英两套；指定其它语言时正文用该语言、界面文案回退英文（新增一门语言只需给 `scripts/render.py` 的 `LABELS` 加一条目）。

## 纯脚本 / 任意框架（无 skills 支持时）

分析逻辑与 Claude Code 的 Workflow 运行时解耦，纯脚本三步即可，产物结构完全一致：

```bash
python scripts/extract_pdf.py workspace/inbox/resume.pdf --out resumes.json
# 接入模型：RG_LLM_PROVIDER=openai|anthropic|custom（详见 analyze_portable.py 头部）
RG_LLM_PROVIDER=openai python scripts/analyze_portable.py --resumes resumes.json --out payload.json
python scripts/render.py payload.json workspace/output/demo demo
```

`analyze_portable.py` 只依赖一个 `call_llm(system, user, schema)` 结构化输出回调（内置 OpenAI/Anthropic 适配，或挂自己的模型）；编排能力有限时加 `--single` 单次调用产出全部（深度略降、结构一致）。四阶段契约（阶段/提示/JSON schema）全在 `reference/pipeline-spec.md`，任何能做结构化输出的框架都能照它实现。渲染层（`render.py` + 模板）零依赖、与运行时无关，任何路径产出的 `payload.json` 都能渲染。

## 项目结构

```
resume-grill/
  SKILL.md                     技能入口（开放 Agent Skills 格式：frontmatter + 指令）
  scripts/
    extract_pdf.py             简历 PDF → 文本
    analyze.js                 Claude Code 原生多智能体 Workflow 引擎
    analyze_portable.py        运行无关的参考编排（可接任意模型）+ --single 回退
    render.py                  payload.json → 三件套（零依赖、含界面文案 i18n）
    install.py                 跨平台安装到各 agent 的 skills 目录（Claude Code / Codex …）
  templates/                   qa_cards / scorecard 的自包含 HTML 模板
  reference/
    pipeline-spec.md           运行无关的流水线契约（阶段/提示/JSON schema/输出语言）
    writing-norms.md           输出写作规范（按语言分别生效）
  workspace/                   本地工作区（简历与产物，均不入库）
    inbox/  output/  BG/
```

## 隐私

简历属敏感个人信息。`workspace/`（含简历与生成产物）已在 `.gitignore` 中排除，`*.pdf` 另有全局兜底忽略——发布时不会入库。分享示例前请先脱敏。

## 许可与署名

MIT License，© 2026 J.C.。详见 `LICENSE`。
