# resume-grill · 简历拷打

[中文](README.md) | [English](README.en.md)

根据简历制作技术面试指南、可打印评分卡和可折叠问答卡片。问题按项目组织成连贯主题，追问与原问题放在一起，每问紧邻可口述的示范回答，判分提示单列。研究与高级技术岗位重点讨论问题意义、路线选择、取舍与证据，具体上下文用于支撑判断。支持Claude Code及其他agent框架，输出语言默认跟随简历。

> 展示一份**完全脱敏**的示例简历（虚构「张三」，某 Agent / AI Infra 岗，2 年经验）跑出的真实三件套——[指南文档](examples/agent_engineer_demo/agent_engineer_demo_guide.md)、[评分卡](examples/agent_engineer_demo/agent_engineer_demo_scorecard.html)、[攻防卡片](examples/agent_engineer_demo/agent_engineer_demo_qa_cards.html)（html 用浏览器打开）。
>



## 快速开始

**1. 装一次**——一条命令，跨平台，无需 PowerShell：

```
python scripts/install.py
```

自动装进检测到的 agent（Claude Code / Codex …）。改完技能后重跑一次即可。

**2. 用**——装完新开一个会话，把简历 PDF **直接拖进对话**，说一句「拷打这份简历」即可（多份就都拖进来）。Agent 会自动把文件纳入工作区、跑完流水线，并**直接回给你三件套的本地链接**，不用翻文件夹。

产物在 `workspace/output/<slug>/`：`_qa_cards.html`（阅读/自测）、`_scorecard.html`（A4 打印现场打分）、`_guide.md`（深挖）。



## 产物说明

三件套写进同一目录，互相以本地相对路径链接、完全自包含（可直接 `file://` 打开）：

- **完整指南** `<slug>_guide.md`：画像、真实强项、待确认事项及项目主题。每个主题包含分层问题、逐问示范回答和本主题追问，最后单列判分依据。
- **现场评分卡** `<slug>_scorecard.html`：限时模式每人一页A4，点击评分后本地保存；全面审查模式允许跨页。
- **问答卡片** `<slug>_qa_cards.html`：按候选人切换，逐问折叠答案；技术追问留在所属主题，折叠答案后仍可看见问题。

流程为简历研判、分域选题、主题与示范回答撰写、核查及修订。核查同时覆盖技术准确性、问题衔接、逐问回答与事实边界。不同且有依据的路线同样可以得分。合作安排与材料确认独立列出。

以下截图及链接示例来自旧版，用于展示历史格式；新生成材料使用主题内追问和逐问示范回答。

![ScreenShot_cn1](./DEMO/ScreenShot_cn1.png)

![ScreenShot_cn2](./DEMO/ScreenShot_cn2.png)



## 多语言

产物语言默认自动判定，与简历一致——中文简历出中文、英文简历出英文，连评分卡与卡片的界面文案也随之本地化。想强制某种语言：让 Claude「用英文输出」，或纯脚本加 `--lang en`（值为 `zh`/`en`/ISO 码/`auto`）。界面壳内置中英两套；指定其它语言时正文用该语言、界面文案回退英文（新增一门语言只需给 `scripts/render.py` 的 `LABELS` 加一条目）。



## 面试时长与全面审查

可指定面试时长，未指定时默认60分钟。下表是覆盖量参考；讨论质量优先于问完所有问题，未问部分留空。

| 时长 | 核心题 | 深度变化 |
| --- | --- | --- |
| 30 分钟 | 3 题（每题 ≈7′） | 暖场阶梯只留 1 级、答案键写精不写多 |
| 60 分钟 | 6 题（≈8′） | 默认 |
| 90分钟 | 约9个主题（约8分钟） | 增加路线比较与证据讨论，追问仍归属原主题 |

**全面审查（ultra）**：说一句「全面审查这份简历」「彻底排查一遍」「找出所有疑点」，它就不设时间盒、不设题数上限，把简历里每一处可能被追问的地方都挖出来——每条红旗、每个没有基线的百分比、每处「参与/负责」的 ownership 模糊、每个只写在技能栏却无项目佐证的术语、每段时间线重叠、每个被包装成「系统」的课程项目。通常 12-24 题，宁多勿漏；但只针对简历里**真实存在**的疑点，不编造。面试官拿它逐条深挖；候选人拿攻防卡片的折叠自测逐题过一遍，面试前把窟窿补上。切换判据是「要不要穷尽」，不是谁在用。



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

建议移除简历中的任何个人信息——以规避API服务商所带来的任何泄露风险。`workspace/`（含简历与生成产物）已在 `.gitignore` 中排除，`*.pdf` 另有全局兜底忽略，发布时不会入库。



## 许可

MIT License
