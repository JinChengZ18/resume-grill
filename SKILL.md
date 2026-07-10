---
name: resume-grill
description: 从简历 PDF 生成一整套对抗性技术面试材料——先分域拷问、再产出「完整指南(md，含真实亮点与关键红旗、从简历项目起手的 L1→L3 分层提问) + 现场评分卡(html, A4可打印) + 提问-回答攻防卡片(html, 可折叠自测)」，答案键经事实核查。产物语言自动匹配简历/输入语言（中文简历出中文、英文简历出英文，亦可显式指定）。当用户想根据一份或多份简历准备/复盘技术面试、生成面试题库、评分卡、攻防卡片，或批量处理积压简历时使用。触发词：对抗性面试、简历面试题、面试卡片、面试评分卡、interview scorecard、resume interview questions、把简历做成面试题。
---

# 对抗性技术面试材料生成

给定一份或多份简历 PDF，产出三件套（同目录、互相以本地相对路径链接）：

- `<slug>_guide.md` — 完整指南：画像、亮点/真实强项、关键红旗、开场态度题、核心验伪题（每题：挂靠简历项目的提问阶梯 L1 项目切入 → L2 设计决策 → L3 硬核验伪 → 期望的优质回答分点 → 及格线 → 典型露馅 → 追问）、补充探针。
- `<slug>_scorecard.html` — 现场评分卡：一位候选人一页 A4，每题「强/中/露馅」勾选位 + 判分线索，可直接打印。
- `<slug>_qa_cards.html` — 提问-回答攻防卡片：A/B… 标签页切换、答案可一键折叠自测、色块分区（含亮点/红旗、每题分层阶梯）、每人链到原始简历 PDF。

引擎是一个自适应多智能体工作流：读简历 → 判研（画像/强项/红旗/该拷问的技术域）→ 分域拷问 → 收敛出挂靠简历项目、分层提问的核心验伪题并写答案键 → 事实核查并修正。对任意岗位/简历都适用，无需为每份简历重写题目。评价均衡如实：戳穿注水的同时如实肯定真本事，不强求优缺点对称、很强/很弱都不硬凑。

## 何时用
用户给了简历（PDF/文本）并想要面试题、判分标准、评分卡或攻防卡片；或想把积压的多份简历批量转成面试材料。

## 运行流程（照此执行）

设技能目录为 `SK = <本 SKILL.md 所在目录>`。

**1. 抽取简历文本**
```
python "SK/scripts/extract_pdf.py" "<resume1.pdf>" "<resume2.pdf>" --out "<work>/resumes.json"
```
若某份 PDF 抽出为空（扫描件/图片版），改用 Read 工具的 PDF 分页渲染/OCR 取文本。

**2. 组织工作流输入**（用 Read 看过 `resumes.json` 后，构造 `args`）：
```json
{
  "meta": {
    "title": "对抗性技术面试 · <批次名>",
    "subtitle": "建议提问 → 期望的优质回答（分点）→ 及格线 → 典型露馅 → 追问",
    "date": "<YYYY-MM-DD，从环境取当前日期，勿用 Date.now()>",
    "by": "J.C.",
    "lang": "auto",
    "links": [
      {"label":"▤ 现场评分卡","href":"<slug>_scorecard.html"},
      {"label":"▤ 完整指南(md)","href":"<slug>_guide.md"}
    ],
    "footer": "题号与评分卡 ★ 一一对应。诚实降级应视为强信号。"
  },
  "candidates": [
    {"id":"A","label":"候选人A · <岗位>（<年限>）","role_hint":"<从文件名/JD>","resume":"<简历PDF文件名，空格转%20>","resume_text":"<resumes.json 里对应 text>"},
    {"id":"B","label":"候选人B · ...","role_hint":"...","resume":"...","resume_text":"..."}
  ]
}
```
`resume` 用**相对文件名**（与三件套同目录）；含空格用 `%20`，中文/`【】` 可保留。匿名交付时置 `resume:null`。

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
- 语言一致：产物语言与 `meta.lang`/简历语言一致，界面文案与正文同语言、无中英混杂残留。
- HTML 自包含（无 `http`/CDN 外链）；跨文件链接为本地相对路径；`resume` 链接指向真实存在的 PDF。
- 如需目视确认渲染：把 HTML 副本放 scratchpad、用 `python -m http.server --bind 127.0.0.1` 起在本机（**勿**对外暴露含简历 PII 的目录），preview_eval 检查 DOM，然后清理。

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
- SKILL.md 采用开放的 Agent Skills 格式（frontmatter + 指令），Claude Code / Claude.ai / Agent SDK 直接识别；上面的 CLI 让不认 SKILL.md 的系统也能纯脚本调用。渲染层（`render.py` + 模板）本就零依赖、与运行时无关。

## 目录约定（应对简历积压）
见交付根目录的 `README.md`。约定：新简历放 `inbox/`；每批产物放 `output/<slug>/`（含三件套，PDF 复制或软链进同目录以便 `resume` 本地链接可用）；`BG/` 保留首个人工样例。命名一律 `<YYYYMMDD>_<批次名>_{guide.md,scorecard.html,qa_cards.html}`。

## 质量与风格
遵循 `reference/writing-norms.md`：答案分点、提问具体到实现层、诚实降级给分为强信号。中文产物另守：中英文免多余空格、中文全角标点、禁用词表；英文产物用直白准确的技术散文。答案键必须经工作流 Verify 阶段的事实核查；核查报错就应用修正。

## 备注
- 单份/双份简历是常态；批量时 `candidates` 放多个，工作流按候选人并行。
- 想只改内容不重跑：直接编辑 `payload.json` 再跑第 4 步 `render.py`。
- 想改版式：编辑 `templates/*.tmpl`（`/*__PAYLOAD__*/{}` 是 JSON 注入点，`__TITLE__` 是标题占位）。
