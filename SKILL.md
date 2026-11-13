---
name: resume-grill
description: Resume grill (简历拷打) — resume-based interview prep in four modes, each started with one sentence and refined through follow-ups in chat; results are self-contained HTML pages that export to PDF. Grilling gives each candidate an interviewer kit — a briefing before the interview, deep questions with what to listen for and a folded model answer right under each question during it, and dimension scoring with a review draft after it (30/60/90 minutes or a full audit, optionally tailored to the hiring team). The other modes are weakness analysis, resume optimization that never invents facts and job-description match. Use it when someone wants to grill a resume, run a mock interview, find weak claims, improve resume bullets, check fit against a JD, or build interview questions from a candidate's resume, even if the skill isn't named. Not for writing a resume from scratch, translating one, or cover letters. 简历拷打：面试拷打（每位候选人一份面试官手册）、弱点分析、简历优化（不编造事实）、JD匹配，一句话启动，可继续追问；发来简历要求拷打、深挖、模拟面试、找弱点、优化简历、对照JD，或按简历出题时使用。
---

# 简历技术面试材料

产物全部是同目录的自包含HTML，每批都有总入口`<slug>_index.html`，每页都能在浏览器打印窗口导出A4 PDF。面试拷打为每位候选人生成一份面试官手册`<slug>_kit_<id>.html`，另附纯文本存档`<slug>_guide.md`；扩展模式生成`<slug>_weakness.html`、`<slug>_resume.html`、`<slug>_jd.html`。材料语言默认跟随简历。真实强项与待确认事项都据实写，不为平衡而凑数量。

## 工作模式

| 模式 | 一句话启动（示例） | 页面 |
| --- | --- | --- |
| 面试拷打（默认） | 「拷打这份简历」「根据简历出面试题」「全面审查这份简历」 | `_kit_<id>.html`（每人一份面试官手册） |
| 弱点分析 | 「分析这份简历的弱点」「我的简历哪里会被问住」 | `_weakness.html` |
| 简历优化 | 「帮我优化这份简历」「按面试标准改写简历」 | `_resume.html` |
| JD匹配 | 「对照这个JD看看我的简历」，附JD文字或链接 | `_jd.html` |

- 识别出模式就按默认设置直接完成，不先列计划征求确认；只有JD匹配缺少JD时，先请用户提供。未指明模式时，求职者自查类说法（「帮我看看简历有什么问题」）做弱点分析，其余按面试拷打处理。
- 模式可以组合（「拷打并优化这份简历」「全套」），写入同一份载荷与同一`slug`。「全套」是面试拷打、弱点分析与简历优化，用户给了JD时再加JD匹配。
- 追问：用户对已生成内容的追问或补充的事实，在原载荷上修改后以同一`slug`重新渲染，文件名保持不变，回复中说明改了哪些条目。简历优化缺少关键事实时，把问题写进`resume_opt.questions`并在对话里一次问完；用户回答前照常给出带占位符的版本。
- 用户说明了招聘方背景（团队做什么、岗位要解决什么问题）时，写入`meta.context`，情境题按这个背景出；没说明就按岗位线索出题，不为此停下来追问。
- 扩展模式的内容规则、追问流程与schema见[扩展模式契约](reference/modes-spec.md)。下面的「内容取向」「面试官手册」「时长与覆盖」主要针对面试拷打。

## 内容取向

先读[写作与主题规范](reference/writing-norms.md)。问题要有水平有深度：从候选人本人的设计出发，问原则与取舍、失败怎么归因、怎样设计可证伪的评估、方法在什么条件下失效；命令、参数、指标复述和实现细节不单独成题，除非它决定一个判断。研究及高级岗位优先讨论问题的意义、替代路线、机制与适用边界；工程岗位按实际职责调整深度，用户明确要实现审计时可集中核验细节。用户要求题目更具体时，补充讨论对象、目标或约束，不把研究问题降成工具排查、参数记忆与计算题。

有`meta.context`时，每个主题的情境题（`ask`）把候选人的做法放进招聘方的真实难题里推演，题目先交代必要背景（约束、代价、规模），考迁移推理，不考对方领域的专门知识。每道题里对方可能不懂的术语第一次出现时用全角括号简短解释（AI术语照顾领域工程师，领域术语照顾AI候选人），含义模糊的指代也加括号说明。

礼貌、自然地交流；“拷打”表示严格检验论证，不表示预设注水或使用质问语气。HR评价属于待确认转述。允许不同合理路线，评价依据是观点与证据的联系。

每个核心主题形成完整阅读单元：项目背景与主问题、路线选择、情境题、承接回答的追问。技术追问写入所属卡片，不得集中放到末尾：主线的顺势追问写`probe`（没有必要时留空），根据回答选择的其他分支写`followups`，两者不重复；每个追问说明何时选问，不为数量凑问题。仅合作安排、材料确认等独立事项可以在文末保留。

示范回答应实际回答问题，包含观点、理由、取舍或可能改变结论的证据，不能只写“能说清”“应当提到”。不知道的本人经历、数据与贡献用明确占位符；可用标明假设的例子说明推理，不能替候选人编造结果。

## 面试官手册

每位候选人一个自包含文件，按面试官的使用顺序组织，页面内没有跳转链接：

- 面试前：一句话画像（标尺与画像折叠）、这场面试要回答的2到3个问题、先核实的事项及在哪一问核实、时间安排、简历里的优势、注意事项、评分维度；原始简历嵌入页面（图片或PDF，折叠）。
- 面试中：开场、各主题、收尾。每道题下面紧跟“要听的点”（★为及格线，可勾选）和折叠的示范回答；情境题和追问标出选问条件并可勾选“已问”；主题末尾是危险信号和记录框。
- 面试后：各维度按4/3/2/1锚点打分，页面按建议规则给出通过、待定或不通过，并能根据勾选和记录生成面评草稿。
- 大段文字（示范回答、标尺、画像、简历原文）一律折叠；页头可以计时、“展开全部”和导出PDF，打印只输出已展开的内容。勾选、打分和记录保存在本机浏览器。

## 输入与目录

令`SK`为本技能目录，`WS=SK/workspace`。输入复制到`WS/inbox/`，不改原件；本批内部文件放`WS/.agents/<slug>/`，读者材料放`WS/output/<slug>/`。文件名使用ASCII。

- PDF用`python SK/scripts/extract_pdf.py <pdf...> --out <work>/resumes.json`抽取。
- 扫描件或图片用视觉读取；保留原图，标明是截图，不伪称PDF。
- 文本简历直接保存为`[{"file":"name","text":"..."}]`。
- 将简历副本放在输出目录，`resume`用同目录相对文件名；渲染时嵌入面试官手册（超过15 MB的文件只写文件名）。不得公开发布候选人材料。
- JD文字保存为`<work>/jd.txt`；用户给的是链接时，抓取正文后保存，并在`jd_match.jd_source`记录链接。

## 时长与覆盖

未指定时默认60分钟。30/60/90分钟通常约3/6/9个主题；讨论深度优先于问完题目，主题标出必问、视时间或视岗位，各主题分钟数之和加上开场和收尾等于总时长。明确要求全面审查、自查所有疑点时用`meta.depth="ultra"`，不限时，但仍按主题组织，不把穷尽变成无关联题目列表。审查覆盖量化结果、本人贡献、时间线与缺少依据的能力声明，不编造疑点。

## 分析与渲染

流程为Triage → 分域Probe → Author → Verify/Revise；问题库仅供选题，不能直接拼成最终散题。详细提示和schema见[流水线契约](reference/pipeline-spec.md)。`meta`包含`title/date/lang/minutes/depth/links`，可选`context`（招聘方背景）与`views`；候选人输入包含`id/label/role_hint/resume/resume_text`；日期取当前会话。

可用Workflow时运行`scripts/analyze.js`。无该运行时则按同一契约组织当前agent分析或使用`scripts/analyze_portable.py`（`--context`传招聘方背景）；不要为了运行脚本擅自配置付费API。分域工作可由子agent执行，最终独立检查技术准确性、问题深度、术语解释与逐问回答对应。参考回答不是唯一标准答案。

最终载荷为`{"meta":{...},"candidates":{"A":{...}}}`。每张卡片包含`ladder[{level,q,answer,listen}]`、`ask/ask_answer/ask_when/ask_listen`、`probe/probe_answer/probe_when/probe_listen`、`followups[{q,answer,when,listen}]`、`prio/minutes/dims/focus/flags/fallback/transfer`以及单列的`pass/tell`；候选人级`kit`写画像、要回答的问题、核实事项、维度与锚点、建议规则和下一轮安排；`probes[{tag,q,answer,listen}]`仅容纳独立合作或材料问题。字段定义见契约的「KIT扩展」；旧载荷缺少这些字段时渲染器自动降级。

扩展模式由当前agent按[扩展模式契约](reference/modes-spec.md)直接撰写`weakness`、`resume_opt`、`jd_match`，写入同一候选人对象；只做扩展模式时可以没有`cards`。

运行：

```text
python SK/scripts/render.py <work>/payload.json <output_dir> <slug>
```

渲染器只为载荷中存在的部分生成页面，每次都重写总入口。新增内容使用逐问字段，不依赖输出后手改或项目私有的渲染补丁。需要旧版的面试指南、问答卡片或A4评分卡时，在`meta.views`里写`["guide","cards","scorecard"]`中需要的项。

## 核验与返回

- 内容检查：每问是否有清楚的讨论对象、是否有深度（不是能背下来的细节题）；对方可能不懂的术语是否加了括号解释；是否承接主题；是否一问对应一答；答案是否遗漏子问题或虚构经历；要听的点是否与示范回答一致。改题目措辞时同步检查示范回答和要听的点。
- 技术与事实检查：不同版本和口径先列待确认；不要把未搜索到当作不存在。按实际工具可用性核实一手资料，并把来源与局限写进材料。领域背景按通用知识写时，在回复里说明没有对照招聘方的实际流程。
- 结构检查：Markdown存档与HTML中的技术追问都位于所属主题内；独立事项不混入技术主题。
- 页面检查：没有远程依赖，面试官手册里没有跳转链接；示范回答紧跟所属问题并默认折叠，全部折叠后仍能看见所有问题；勾选、打分、面评草稿与本地保存有效；打印时面试前占一页、每个主题另起一页。对变更运行`scripts/test_render.py`（如存在），并用实际材料检查页面。
- 扩展模式检查：引用确实出自简历或JD；没有简历和对话之外的数字、职责、归属或日期，未知事实都是占位符（见[扩展模式契约](reference/modes-spec.md)的「核验」）。
- 中文风格与禁用词按写作规范；跨语言输出运行`python SK/scripts/check_lang.py <work>/payload.json`。

把每位候选人的面试官手册直接发给用户（单个文件即可使用），再给总入口与其他页面；说明本次主要修改和实际验证范围。更新技能时同时对齐说明、生成提示/schema和渲染行为，不能只在文档末尾追加一条与原工作流冲突的规则。
