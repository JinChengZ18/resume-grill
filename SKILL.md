---
name: resume-grill
description: 从简历 PDF 生成一整套对抗性技术面试材料——先分域拷问、再产出「完整指南(md，含真实亮点与关键红旗、从简历项目起手的 L1→L3 分层提问) + 现场评分卡(html, A4可打印) + 提问-回答攻防卡片(html, 可折叠自测)」，答案键经事实核查。产物语言自动匹配简历/输入语言（中文简历出中文、英文简历出英文，亦可显式指定）。当用户想根据一份或多份简历准备/复盘技术面试、生成面试题库、评分卡、攻防卡片，或批量处理积压简历时使用；**候选人拿自己的简历做面试前自我排查（ultra 自测模式，穷尽所有疑点）时同样使用**；用户直接上传/拖入/粘贴简历文件时也应触发（先把文件纳入 workspace/inbox/ 再处理）。触发词（含口语化说法）：拷打这份简历、拷打简历、锤一锤这个候选人、狠狠面试他、这份简历能问什么、帮我面这个人、把简历做成面试题、生成面试题/评分卡/攻防卡片、对抗性面试、简历面试题、自我排查、简历自查、面试前自查、模拟拷打我的简历、我会被问到什么、interview scorecard、grill this resume、resume self-check、resume interview questions。
---

# 对抗性技术面试材料生成

给定一份或多份简历 PDF，产出三件套（同目录、互相以本地相对路径链接）：

- `<slug>_guide.md` — 完整指南：画像、亮点/真实强项、关键红旗、开场态度题、核心验伪题（每题：挂靠简历项目的提问阶梯 L1 项目切入 → L2 设计决策 → L3 硬核验伪 → 期望的优质回答分点 → 及格线 → 典型露馅 → 追问）、补充探针。
- `<slug>_scorecard.html` — 现场评分卡：一位候选人一页 A4，每题「强/中/露馅」勾选位 + 判分线索，可直接打印。
- `<slug>_qa_cards.html` — 提问-回答攻防卡片：A/B… 标签页切换、答案可一键折叠自测、色块分区（含亮点/红旗、每题分层阶梯）、每人链到原始简历 PDF。

引擎是一个自适应多智能体工作流：读简历 → 判研（画像/强项/红旗/该拷问的技术域）→ 分域拷问 → 收敛出挂靠简历项目、分层提问的核心验伪题并写答案键 → 事实核查并修正。对任意岗位/简历都适用，无需为每份简历重写题目。评价均衡如实：戳穿注水的同时如实肯定真本事，不强求优缺点对称、很强/很弱都不硬凑。

## 何时用
用户给了简历（PDF/文本）并想要面试题、判分标准、评分卡或攻防卡片；或想把积压的多份简历批量转成面试材料。**用户在对话里上传/拖入/附上简历文件、或只丢来一句「拷打这份简历」时也算**——按下面「第 0 步」自动把文件纳入本地工作区再处理，不必要求用户手动放文件。

两种立场都支持：**面试官**要一套限时可用的题目与判分标准（按时长裁剪，见「面试时长」）；**候选人**要拿自己的简历自查、看看会被问到什么——这时用 `meta.depth:"ultra"` 穷尽所有疑点，不设时长与题数上限。用户说「自我排查」「面试前自查」「我会被问到什么」「模拟拷打我的简历」即属后者。

## 运行流程（照此执行）

设技能目录为 `SK = <本 SKILL.md 所在目录>`，工作区为 `WS = SK/workspace`（约定见 `WS/README.md`）。

**0. 纳入输入文件**（用户上传/附件/给路径时）
用户上传或引用的 PDF 往往落在对话临时目录或仓库外。先把它们**复制**进 `WS/inbox/`（缺失则建目录），后续都对 inbox 内的副本操作，不改动/不删除用户原文件：
```
python - <<'PY'
import os, shutil, unicodedata
inbox = os.path.join("SK","workspace","inbox"); os.makedirs(inbox, exist_ok=True)
for src in [ "<用户上传/给出的每个 PDF 绝对路径>" ]:
    dst = os.path.join(inbox, unicodedata.normalize("NFC", os.path.basename(src)))
    shutil.copy2(src, dst); print("ingested ->", dst)
PY
```
用户直接粘贴简历纯文本（无文件）时跳过本步，第 1 步改为把文本写进 `resumes.json`（结构 `[{"file":"<名>","text":"<正文>"}]`）。已在 `WS/inbox/` 里的文件直接用。

**1. 抽取简历文本**
```
python "SK/scripts/extract_pdf.py" "WS/inbox/<resume1.pdf>" "WS/inbox/<resume2.pdf>" --out "<work>/resumes.json"
```
`extract_pdf.py` 已做 NFKC 规整（修复 pypdf 常见的部首字/连字乱码）。若某份 PDF 抽出为空（扫描件/图片版），改用 Read 工具的 PDF 分页渲染/OCR 取文本。

**2. 组织工作流输入**（用 Read 看过 `resumes.json` 后，构造 `args`）：
```json
{
  "meta": {
    "title": "对抗性技术面试 · <批次名>",
    "subtitle": "建议提问 → 期望的优质回答（分点）→ 及格线 → 典型露馅 → 追问",
    "date": "<YYYY-MM-DD，从环境取当前日期，勿用 Date.now()>",
    "lang": "auto",
    "minutes": 60,
    "links": [
      {"label":"▤ 现场评分卡","href":"<slug>_scorecard.html"}
    ],
    "footer": "题号与评分卡 ★ 一一对应。诚实降级应视为强信号。"
  },
  "candidates": [
    {"id":"A","label":"候选人A · <岗位>（<年限>）","role_hint":"<从文件名/JD>","resume":"<简历PDF文件名，空格转%20>","resume_text":"<resumes.json 里对应 text>"},
    {"id":"B","label":"候选人B · ...","role_hint":"...","resume":"...","resume_text":"..."}
  ]
}
```
`resume` 用**相对文件名**（与三件套同目录）；含空格用 `%20`，中文/`【】` 可保留。**尽量别置 null**：把简历 PDF 复制进产物目录并填这里，评分卡与攻防卡片就会给出「原始简历」内链，方便与题目一一对应；仅在需匿名交付时才 `resume:null`。
`meta.links` **只放评分卡**，不要放 `_guide.md`（指南是给面试官深挖的 md，不适合作为交付页内链）。交付页署名统一显示项目名 `resume-grill`，不放个人作者名，故 `meta` 无需 `by`。

**面试时长**：`meta.minutes` 控制题量与拷问深度——现实中各家面试时长不一，时间长就问得更细更多，时间短就只能抓要害。用户说了时长（「30 分钟电话面」「一个半小时现场」）就换算成分钟填进去；没说则用 60，拿不准就直接问一句「这场面试大概多长时间？」。工作流据此推导每场的题数、每题时间预算与深度档位，并把 `plan` 写回 `payload.meta`，评分卡与指南会显示时间分配。

| 时长 | 核心题 | 每题 | 深度档位 | 变化 |
| --- | --- | --- | --- | --- |
| 30 分钟 | 3 | ≈7′ | quick | 阶梯只留 1 级、答案键写精不写多、技术域 3-4 个 |
| 60 分钟 | 6 | ≈8′ | standard | 2 级阶梯 + 硬核验伪（默认） |
| 90 分钟 | 9 | ≈8′ | deep | 答案键分点更多、追问再压一层、技术域 6-8 个 |
| 不限时 | 12-24 | — | **ultra** | 自测模式，见下 |

题数由时长推导（`nCore` 可在 args 顶层显式覆盖）。也可用 `meta.depth` 显式指定档位（`quick`/`standard`/`deep`/`ultra`），覆盖由时长推出的档位。

**自测模式 ultra**（`meta.depth: "ultra"`，与 `minutes` 无关）：给**候选人面试前自我排查**用——不设时间盒、不设题数上限，把简历里每一处可能被追问、被质疑、被要求举证的地方都挖出来，逐项覆盖：每条关键红旗；每个没有严谨基线的量化宣称；每处「参与/负责/协助」的 ownership 模糊；每个只写在技能栏却无项目佐证的术语；每段时间线重叠或经历性质存疑；每个被包装成「系统/框架/平台」的课程项目。宁多勿漏——但**只针对简历里真实存在的疑点，不得为凑数编造**。产物远多于常规档（通常 12-24 题 + 20-30 条探针，技术域 8-12 个），跑得也更久、更贵。此时评分卡与指南不显示时间分配，改标「自测模式 · 不限时」；攻防卡片的折叠自测正是给候选人逐题过一遍用的。

**输出语言**：`meta.lang` 控制全部产物语言。缺省 `"auto"`（或省略）时按简历正文自动判定，使产物语言与输入一致（中文简历出中文、英文简历出英文）；也可显式设 `"zh"`/`"en"`/ISO 码，或按用户要求设定。工作流据此写作模型内容，`render.py` 据同一 `lang` 本地化界面文案（zh/en 全套，其余语言回退英文界面壳、内容仍为该语言）。`title`/`subtitle`/`footer`/`links[].label` 等你自定义的文案也应写成目标语言（省略则用本地化默认值）。

**3. 跑分析工作流**（返回 `{meta, candidates}` 载荷）：
用 Workflow 工具，`scriptPath = "SK/scripts/analyze.js"`，`args = <上面的对象>`。
把返回的 JSON 载荷写到 `<work>/payload.json`（用 Write 工具，勿改动数值）。

**4. 渲染三件套**
```
python "SK/scripts/render.py" "<work>/payload.json" "<output_dir>" "<slug>"
```
`<slug>` 建议 `<YYYYMMDD>_<批次名>`。三件套写入 `<output_dir>`。

**5. 自检**（务必做）
- 违禁词扫描（仅中文产物）：`交付|再生|天然|免费|回连|让渡|封顶|能量账|省下|补上|旋钮|喂|健壮|落地` 应为 0。非中文产物跳过此项。
- **跨语言泄漏扫描**（简历语言与产物语言不同时必做，例如中文简历出英文材料）：
  ```
  python "SK/scripts/check_lang.py" "<work>/payload.json"
  ```
  非 CJK 产物里不得出现任何中日韩字符：引用简历措辞必须**译成产物语言**，不得照抄原文（`anchor`、`flags`、`strengths` 最容易漏）。脚本报错就把相应字段改写（或重跑该阶段）后重渲，直至通过。
- HTML 自包含（无 `http`/CDN 外链）；跨文件链接为本地相对路径；`resume` 链接指向真实存在的 PDF。
- 如需目视确认渲染：把 HTML 副本放 scratchpad、用 `python -m http.server --bind 127.0.0.1` 起在本机（**勿**对外暴露含简历 PII 的目录），preview_eval 检查 DOM，然后清理。

**6. 交付给用户**（别让用户翻文件夹）
产出后，用 markdown 链接把三件套的**本地路径**直接回给用户（多数 agent 界面会渲染成可点击链接），一句话点出各文件用途，例如：
- [现场评分卡](<output_dir>/<slug>_scorecard.html) — 一页 A4，打印现场打分
- [攻防卡片](<output_dir>/<slug>_qa_cards.html) — 答案折叠自测
- [完整指南](<output_dir>/<slug>_guide.md) — 深挖

再附一两句判研要点（真实强项、关键红旗；多人时谁更强），并给出 `<output_dir>` 路径，让用户零成本打开，无需自己在文件夹里翻找。

## 在其它 agent 系统里运行（运行无关）

分析逻辑与 Claude Code 的 Workflow 运行时解耦，可被任意 agent 框架调用：

- 契约在 `reference/pipeline-spec.md`：四阶段（Triage→Probe→Author→Verify）的 system/user 提示与 JSON schema 全在此。任何能做「结构化输出」的框架照它实现即可。
- 参考实现 `scripts/analyze_portable.py`：只需接入一个 `call_llm(system,user,schema)`（内置 OpenAI/Anthropic 适配，或 `RG_LLM_PROVIDER=custom` 挂你自己的模型），跑出与原生同构的 `payload.json`，再交给 `render.py`。纯脚本三步：
  ```
  python scripts/extract_pdf.py <resume.pdf> --out resumes.json
  RG_LLM_PROVIDER=openai python scripts/analyze_portable.py --resumes resumes.json --out payload.json [--lang auto]
  python scripts/render.py payload.json <out_dir> <slug>
  ```
  编排能力有限时加 `--single`（单次调用产出全部，深度略降、结构一致）。
- SKILL.md 是**跨 agent 通用标准**：同一技能目录在 Claude Code（`~/.claude/skills`）、Codex CLI（`~/.codex/skills`）等支持 skills 的 agent 里都能直接识别、按描述模糊触发——`python scripts/install.py` 会自动装进检测到的各家（详见仓库 README）。不认 SKILL.md 的系统用上面的纯脚本 CLI 调用即可。渲染层（`render.py` + 模板）本就零依赖、与运行时无关。

## 目录约定（应对简历积压）
见交付根目录的 `README.md`。约定：新简历放 `inbox/`；每批产物放 `output/<slug>/`（含三件套，PDF 复制或软链进同目录以便 `resume` 本地链接可用）；`BG/` 保留首个人工样例。命名一律 `<YYYYMMDD>_<批次名>_{guide.md,scorecard.html,qa_cards.html}`。

## 质量与风格
遵循 `reference/writing-norms.md`：答案分点、提问具体到实现层、诚实降级给分为强信号。中文产物另守：中英文免多余空格、中文全角标点、禁用词表；英文产物用直白准确的技术散文。答案键必须经工作流 Verify 阶段的事实核查；核查报错就应用修正。

## 备注
- 单份/双份简历是常态；批量时 `candidates` 放多个，工作流按候选人并行。
- 想只改内容不重跑：直接编辑 `payload.json` 再跑第 4 步 `render.py`。
- 想改版式：编辑 `templates/*.tmpl`（`/*__PAYLOAD__*/{}` 是 JSON 注入点，`__TITLE__` 是标题占位）。
