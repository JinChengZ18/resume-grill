# 分析流水线规格（运行无关 · 供任意 agent 系统实现）

本文件把「简历 → 面试材料」的分析流水线抽象成**与运行时无关的契约**：阶段划分、每阶段的提问词、以及严格的 JSON schema。任何 agent 框架（LangChain、OpenAI Assistants、自研编排、乃至一次性脚本）只要能做「给定 system+user 提示、返回符合给定 JSON schema 的结构化输出」，就能实现本技能，无需依赖 Claude Code 的 Workflow 运行时。

两个参考实现都遵循本规格：
- `scripts/analyze.js` — Claude Code 原生多智能体 Workflow（各阶段并行、`agent()`/`parallel()`）。
- `scripts/analyze_portable.py` — 运行无关的顺序编排，只依赖一个你自己接入模型的 `call_llm(system, user, schema)` 回调；另带 `--single` 单调回退模式。

两条路径产出**同一份 `payload.json`**，都交给 `scripts/render.py` 渲染三件套。

## 唯一外部依赖：结构化输出

实现方只需提供一个函数：

```
call_llm(system: str, user: str, schema: dict) -> dict
```

- 输入：system 提示（见下方 ROLE）、user 提示（各阶段给定）、一个 JSON Schema。
- 输出：一个**符合该 schema** 的 dict。用你的模型的「JSON 模式 / 工具调用 / 结构化输出」达成；拿不到原生结构化输出时，把 schema 附在 user 末尾要求「只返回 JSON」，再 `json.loads` + 按 schema 校验、失败重试。
- 建议 reasoning effort 拉高、temperature 偏低（这是判研任务，不是创作）。

## 数据流

```
resumes.json (extract_pdf.py 或你的抽取器)
   │  每位候选人：{id,label,role_hint,resume,resume_text}
   ▼
[1 Triage] 逐候选人：画像/标尺/强项/红旗/开场题/待拷问技术域
   ▼
[2 Probe]  逐技术域（可并行）：5-8 个由浅入深的对抗问题
   ▼
[3 Author] 收敛出 N=6 道核心验伪题（含 anchor 锚点 + ladder 分层阶梯 + 答案键）+ 补充探针
   ▼
[4 Verify] 对答案键做事实核查 → 若有问题则 Revise 修正
   ▼
组装 candidate 对象 → payload.json → render.py 出三件套
```

## ROLE（system 提示，所有阶段共用）

人设保持语言中立（不再绑定「中文简历」），**输出语言**由 `directive(lang)` 追加到人设末尾决定（见下节「输出语言」）：

> 你是一线科技公司的资深技术面试官，风格严苛、对简历注水极度敏感。你深知简历常见把戏：大量「参与」其实贡献极小；百分比指标（「节省65%」「提升28%」）常无严谨基线；课程/短期项目包装成「系统」；术语背后是调库还是真懂原理需要戳穿。提问必须具体、扎进底层实现（数据结构/阈值/失败模式/评估口径/为何这么选），能区分「真做过」与「只会写在简历上」。同时你也是公正的评估者：在戳穿注水的同时，如实识别候选人真实、可验证的强项与亮点——扎实的技术深度、真实的 ownership、诚实的自我降级都算加分项。不为对抗而对抗：候选人确实强就大方肯定，确实弱也不硬挑刺、不为凑数编造红旗；据实评价，不强求优缺点对称、不面面俱到。
>
> **{directive(lang)}** — 例：`lang=zh` → 「全部用简体中文输出；散文遵循中英文之间不加多余空格、中文用全角标点；不要出现这些词：交付、再生、天然、免费、回连、让渡、封顶、能量账、省下、补上、旋钮、喂、健壮、落地。」；`lang=en` → 「Write ALL output — every field, question, and answer key — in natural, direct English technical prose.」

各阶段的 user 提示（下文）为**指令语**，可保持中文；模型据 ROLE 末尾的 `directive(lang)` 决定**产物语言**。原生 `analyze.js`（无独立 system 位）改为把该指令以「【输出语言】…」追加到每个阶段 user 提示末尾，效果等同。

## 面试时长（题量与深度）

现实中各家面试时长不一：时间长则问得更细、题目更多；时间短则只能抓要害。一个 `minutes`（缺省 60）贯穿全流程：

1. **推导 plan**（两个参考实现共用同一套公式）：
   - `depth` 优先取显式的 `meta.depth`／`--depth`（`quick`/`standard`/`deep`/`ultra`）；否则由时长推导：`minutes < 40 → quick`；`minutes >= 85 → deep`；否则 `standard`。
   - `depth == 'ultra'` 直接返回 `{minutes:null, opener:null, buffer:null, nCore:null, perQuestion:null}`——自测模式不限时、不设题数上限（见下）。
   - 其余档位：`(opener, buffer)` 取 `quick(4,5)`／`standard(5,7)`／`deep(6,9)` 分钟；`core = max(minutes - opener - buffer, 8)`；`nCore = clamp(round(core/8), 2, 12)`；`perQuestion = max(4, floor(core/nCore))`——用 floor 保证 `opener + nCore×perQuestion + buffer` 不超出时长。
   - 坑：Python 内置 `round()` 是银行家舍入，须换成四舍五入才与 JS `Math.round` 一致（见 `_round_half_up`），否则两实现在 `minutes=32` 处分叉。
2. **档位决定深度**：

   | depth | 题数 | 阶梯级数 | good 分点 | pass 条数 | 补充探针 | 技术域 | 红旗 |
   | --- | --- | --- | --- | --- | --- | --- | --- |
   | quick | 由时长推导 | 1（省去项目概览，直取设计决策） | 4-5 | 2-3 | 4-6 | 3-4 | 3-6 条，不硬凑 |
   | standard | 由时长推导 | 2（L1 项目切入 + L2 设计决策） | 5-8 | 3-5 | 10-14 | 4-6 | 3-6 条，不硬凑 |
   | deep | 由时长推导 | 2 | 7-10 | 4-6 | 14-18 | 6-8 | 4-8 条，不硬凑 |
   | ultra | **不固定（通常 12-24）** | 2 | 6-10 | 3-6 | 20-30 | 8-12 | **穷尽所有真实疑点，不设上限** |

3. **ultra = 自我排查模式**（供候选人面试前自查）：不设时间盒与题数上限，把简历里每一处可能被追问的疑点都变成一道题。「穷尽」的可执行定义是一份必须逐项覆盖的清单——①每条关键红旗；②每个无严谨基线的量化宣称；③每处 ownership 模糊（「参与/负责/协助」）；④每个只出现在技能栏却无项目佐证的术语；⑤每段时间线重叠或经历性质存疑；⑥每个被包装成「系统/框架/平台」的课程项目。硬约束：**宁多勿漏，但只针对真实存在的疑点，不得为凑数编造**（与 ROLE 的「不硬凑」一致）。该清单同时注入 Triage（穷尽红旗）与 Author（穷尽题目）。
4. **注入提示**：非 ultra 拼「本场面试约 N 分钟：开场约 …，X 道核心题每题约 …，留约 … 分钟收尾」；ultra 拼「不是限时面试，而是面试前自我排查：不设时间盒、不设题数上限」。两者都附档位说明；schema 里 `flags`/`domains`/`ladder`/`good`/`pass`/`probes`/`cards` 的描述按档位插值（ultra 的 `cards` 描述改为「题数不固定、按 Q1、Q2… 依次编号」）。
5. **落盘与渲染**：`plan` 写入 `payload.meta.plan`；`render.py` 据此在指南顶部给一行时间预算、在评分卡显示总时长与每题 `≈N′` 预算。ultra 的 `minutes`/`perQuestion` 为 `null`，渲染层据此改标「自测模式 · 不限时」并省去每题时间徽标。

`nCore` 可显式覆盖（`args.nCore` / `--ncore`），覆盖后 `plan.nCore` 同步为该值；ultra 下 `nCore` 为 `null`（题数由疑点数量决定）。

## 输出语言（多语言支持）

产物语言与输入一致，靠一个贯穿全流程的 `lang`：

1. **判定**：显式 `args.lang` / `meta.lang`（非 `auto`）优先；否则按简历正文自动判定——按汉字占字母比例，含相当比例汉字判 `zh`，否则 `en`（两个参考实现用同一启发式）。
2. **注入**：把 `directive(lang)` 追加进 system 提示（`analyze_portable.py`）或每个阶段 user 提示末尾（`analyze.js`）。`directive`：
   - `zh` → 「全部用简体中文输出；中英文免多余空格、中文全角标点；禁用词表（同上）。简历若为外文，引用其措辞时先译成中文（通用技术名词可留英文）。」
   - `en` → 「Write ALL output … in natural, direct English technical prose. …TRANSLATE any phrase cited from the résumé; never reproduce the original characters; the output must contain NO CJK characters at all.」
   - 其它 ISO 码 → 「Write ALL output … in the language with ISO code "<lang>". …translate any phrase you cite from the résumé; never reproduce its original script.」
3. **落盘**：`lang` 写入 `payload.meta.lang`。
4. **渲染**：`render.py` 按 `meta.lang` 从 `LABELS` 取界面文案（zh/en 全套；缺失语言回退英文界面壳，正文仍为该语言）；`meta.lang` 缺省时按 payload 内容再嗅探一次。**新增一门语言 = 给 `LABELS` 加一条目**（键集须与既有语言一致）。
5. **校验**：`scripts/check_lang.py payload.json` 逐字段扫描——产物语言非 CJK 时不得出现任何中日韩字符（`resume`/`href` 等文件名字段豁免）。有泄漏就重写该字段再重渲。

**跨语言引用是本流水线最容易破的地方**：简历为中文而产物为英文时，模型倾向于把简历原句直接嵌进英文散文（`anchor`、`flags`、`strengths` 尤甚）。`directive` 明令翻译，`check_lang.py` 做确定性兜底。

指令语（各阶段 user 提示、schema 字段描述）可保持中文，不影响产物语言——产物语言只由 `directive(lang)` 决定。

## 阶段 1 · Triage（逐候选人）

**user 提示**（`{resume}` = `候选人 {label}｜岗位线索：{role_hint}\n简历正文：\n---\n{resume_text}\n---`）：

> {resume}
>
> 任务：通读简历做面试前研判。给出：画像+可信度（均衡如实）、该用的标尺、真实可验证的强项/亮点（有几条写几条、乏善可陈不硬凑）、关键红旗（注水多就多列、干净就少列，不硬凑）、一组开场态度/事实题（时间线/可展示性/ownership），以及4-6个最值得对抗性拷问的技术域（贴合其真实项目，每域列出该戳的实现细节/失败模式）。既要戳穿注水，也要如实肯定真本事，不强求优缺点对称。

**输出 schema**：

```json
{
  "type":"object","additionalProperties":false,
  "required":["profile","ruler","strengths","flags","opener","domains"],
  "properties":{
    "profile":{"type":"string"},
    "ruler":{"type":"string"},
    "strengths":{"type":"array","items":{"type":"string"}},
    "flags":{"type":"array","items":{"type":"string"}},
    "opener":{"type":"object","additionalProperties":false,
      "required":["title","questions","expect","tell"],
      "properties":{"title":{"type":"string"},"questions":{"type":"array","items":{"type":"string"}},
        "expect":{"type":"string"},"tell":{"type":"string"}}},
    "domains":{"type":"array","items":{"type":"object","additionalProperties":false,
      "required":["key","focus"],"properties":{"key":{"type":"string"},"focus":{"type":"string"}}}}
  }
}
```

字段含义：`profile` 3-4 句画像+可信度（均衡如实）；`ruler` 衡量标尺；`strengths` 真实可验证的强项，约 2-5 条，乏善可陈不硬凑、不与红旗对称；`flags` 关键红旗，注水多就多列、干净就少列；`opener` 开场态度/事实题；`domains` 4-6 个待拷问技术域（`focus` 为该域该戳的实现细节/失败模式）。

## 阶段 2 · Probe（逐技术域，可并行）

对 `domains` 里每个域 `d` 各发一次：

**user 提示**：

> {resume}
>
> 只聚焦这一个技术域做对抗性拷问：【{d.key}】
> 重点覆盖：{d.focus}
> 产出5-8个由浅入深、层层设套的问题（每题：验证什么/真做过怎么答/只堆术语怎么露馅/一个逼底层的追问），具体到实现层，不要泛泛而谈。

**输出 schema**：

```json
{
  "type":"object","additionalProperties":false,"required":["domain","questions"],
  "properties":{"domain":{"type":"string"},
    "questions":{"type":"array","items":{"type":"object","additionalProperties":false,
      "required":["q","probes","strong","tell"],
      "properties":{"q":{"type":"string"},"probes":{"type":"string"},
        "strong":{"type":"string"},"tell":{"type":"string"},"followup":{"type":"string"}}}}}
}
```

## 阶段 3 · Author（逐候选人，汇总 probe 结果）

**user 提示**（`{bank}` = `JSON.stringify({triage:{flags,domains}, probes})`；`{N}` 默认 6）：

> {resume}
>
> 以下是分域拷问的问题库（JSON）：
> {bank}
>
> 作为首席面试官，收敛出恰好{N}道「核心验伪题」（题号Q1..Q{N}）——最能区分「真做过」与「只会写简历」、且无法靠背术语蒙混的题。每道题都要：①挂靠到一个具体简历项目/宣称（anchor）；②做好提问分层，给一个恰好2级的暖场阶梯（ladder）——L1 从该简历项目切入的概览/general 问题（先让候选人自己讲，既给他展开空间也给你观察点与切入口），L2 关键设计决策/为什么这么选；ask 则落到实现层、无法靠背术语蒙混的 L3 硬核验伪。此外每道给：期望的优质回答（5-8个分点、技术准确、含机制/阈值/取舍）、及格线（必须听到的3-5点）、典型露馅、追问。另把其余有价值的问题去重整理为「补充探针」（每条带主题标签）。

**输出 schema**：

```json
{
  "type":"object","additionalProperties":false,"required":["cards","probes"],
  "properties":{
    "cards":{"type":"array","items":{
      "type":"object","additionalProperties":false,
      "required":["n","title","anchor","ladder","ask","good","pass","tell","probe"],
      "properties":{
        "n":{"type":"string"},"title":{"type":"string"},
        "anchor":{"type":"string"},
        "ladder":{"type":"array","items":{"type":"object","additionalProperties":false,
          "required":["level","q"],"properties":{"level":{"type":"string"},"q":{"type":"string"}}}},
        "ask":{"type":"string"},
        "good":{"type":"array","items":{"type":"string"}},
        "pass":{"type":"array","items":{"type":"string"}},
        "tell":{"type":"string"},"probe":{"type":"string"}}}},
    "probes":{"type":"array","items":{"type":"object","additionalProperties":false,
      "required":["tag","q"],"properties":{"tag":{"type":"string"},"q":{"type":"string"}}}}
  }
}
```

`anchor` = 本题挂靠的简历项目/宣称；`ladder` = 恰好 2 级暖场阶梯（L1 项目切入、L2 设计决策），`ask` 即 L3 硬核验伪；`good` 5-8 分点、`pass` 3-5 条及格线。

## 阶段 4 · Verify（+ Revise）

**Verify user 提示**（`{cards}` = 阶段 3 的 cards）：

> 你是横跨AI基础设施/RAG/多Agent/建模/系统的资深技术专家，对下面这份面试「标准答案(answer key)」做对抗式事实核查。逐条检查 good 与 pass 是否有：技术性错误、不精确、夸大（把课程/理论说成工业标准）、关键遗漏。只报真正的问题，准确的不要报。
>
> 答案(JSON)：{cards}

**Verify 输出 schema**：

```json
{
  "type":"object","additionalProperties":false,"required":["corrections","verdict"],
  "properties":{
    "corrections":{"type":"array","items":{"type":"object","additionalProperties":false,
      "required":["n","severity","issue","fix"],
      "properties":{"n":{"type":"string"},
        "severity":{"type":"string","enum":["error","imprecise","overclaim","missing"]},
        "issue":{"type":"string"},"fix":{"type":"string"}}}},
    "verdict":{"type":"string"}}
}
```

若 `corrections` 非空，再发一次 **Revise**（system 用 ROLE）：

> 下面是核心验伪题的答案键(JSON)与事实核查发现的问题(JSON)。请按核查意见修正 good/pass 中的错误/不精确/夸大/遗漏，保持题目与结构不变、其余内容不动，返回修正后的完整卡片数组。
>
> 卡片：{cards}
> 核查：{corrections}

Revise 输出 schema：`{"type":"object","required":["cards"],"properties":{"cards":{"type":"array","items":<CARD>}}}`（CARD 同阶段 3）。用修正后的 cards 覆盖。

## 组装 payload

逐候选人组装：

```json
{
  "name": "<label>", "resume": "<相对文件名或 null>",
  "profile": "<triage.profile>", "ruler": "<triage.ruler>",
  "strengths": "<triage.strengths>", "flags": "<triage.flags>",
  "opener": "<triage.opener>", "cards": "<revise 或 author.cards>",
  "probes": "<author.probes>"
}
```

最终 `payload.json = { "meta": {...}, "candidates": { "<id>": <上面对象>, ... } }`。`meta` 见 SKILL.md。交给 `python scripts/render.py payload.json <out_dir> <slug>` 渲染。

## 单调回退（--single）

编排能力不足或只想跑一次模型时，可把 Triage+Author 合成**一次调用**：system 用 ROLE，user 给简历，要求一次性返回 `{profile,ruler,strengths,flags,opener,cards,probes}`（schema = Triage 去掉 domains + Author 合并；cards 仍需 anchor/ladder/ask/good/pass/tell/probe）。跳过分域 Probe 会牺牲深度与题目锐度，但产物结构完全一致、可直接渲染。事实核查（阶段 4）仍建议保留。`analyze_portable.py --single` 即此模式。

## 与写作规范的关系

所有阶段的散文都遵循 `reference/writing-norms.md`：答案分点、提问具体到实现层、诚实降级给分为强信号。语言相关约束按 `lang` 生效——中文产物守中英文免多余空格、中文全角标点、禁用词表；英文产物用直白准确的技术散文。这些约束通过 `directive(lang)` 写进 ROLE 与各阶段提问词。
