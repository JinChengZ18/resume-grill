---
name: resume-grill
description: Resume grill (简历拷打) — turns a resume or CV into a technical interview guide, a printable A4 scorecard and collapsible Q&A cards, with a spoken model answer for every question; supports 30/60/90-minute interviews or a full audit. Use it when someone wants to grill a resume, run a mock technical interview, predict interviewer follow-ups, or find weak and unverifiable resume claims, and when an interviewer wants questions and a scorecard built from a candidate's resume, even if the skill isn't named. Not for polishing, rewriting or translating a resume, tailoring it to a job description, or writing a cover letter. 简历拷打：根据简历生成技术面试指南、A4评分卡和问答卡片，每问附示范回答。用户发来简历（PDF、图片或文字）并要求拷打、深挖、追问、模拟面试、预测面试官会问什么、找简历疑点或核验简历真实性时使用；面试官要按候选人简历出题、准备结构化面试或现场评分卡时也用；即使没提技能名，只要是拿简历准备技术面试或出题就用。只想润色、改写、翻译简历，按JD改简历或写求职信时不用。
---

# 简历技术面试材料

输出同目录三件套：`<slug>_guide.md`、`<slug>_scorecard.html`、`<slug>_qa_cards.html`。卡片与评分卡使用本地相对链接，附原简历副本；HTML自包含，评分卡支持本地保存和A4打印。材料语言默认跟随简历。真实强项与待确认事项都据实写，不为平衡而凑数量。

## 内容取向

先读[写作与主题规范](reference/writing-norms.md)。研究及高级技术岗位优先讨论问题的意义、替代路线、机制、取舍与适用边界；具体项目提供背景，必要的实现证据支撑判断。用户要求更具体时，补充讨论对象、目标或约束，避免把研究问题降成工具排查、参数记忆与计算题。工程岗位按实际职责调整深度，用户明确要实现审计时可集中核验细节。

礼貌、自然地交流；“拷打”表示严格检验论证，不表示预设注水或使用质问语气。HR评价属于待确认转述。允许不同合理路线，评价依据是观点与证据的联系。

每个核心主题形成完整阅读单元：项目背景与主问题、路线选择、情境或边界讨论、承接回答的追问。每一问紧邻可口述的示范回答，面试官判分提示单列。技术追问写入所属卡片的`followups`，不得集中放到末尾；每个追问说明何时选问，不为数量凑问题。仅合作安排、材料确认等独立事项可以在文末保留。

`probe/probe_answer`是主题主线的顺势追问，没有必要时两者留空；`followups`是根据候选人回答选择的其他分支，不能重复主线追问。两者都在所属主题内显示。

示范回答应实际回答问题，包含观点、理由、取舍或可能改变结论的证据，不能只写“能说清”“应当提到”。不知道的本人经历、数据与贡献用明确占位符；可用标明假设的例子说明推理，不能替候选人编造结果。

## 输入与目录

令`SK`为本技能目录，`WS=SK/workspace`。输入复制到`WS/inbox/`，不改原件；本批内部文件放`WS/.agents/<slug>/`，读者材料放`WS/output/<slug>/`。文件名使用ASCII。

- PDF用`python SK/scripts/extract_pdf.py <pdf...> --out <work>/resumes.json`抽取。
- 扫描件或图片用视觉读取；保留原图，链接标明截图，不伪称PDF。
- 文本简历直接保存为`[{"file":"name","text":"..."}]`。
- 将简历副本放在输出目录，`resume`用同目录相对文件名。不得公开发布候选人材料。

## 时长与覆盖

未指定时默认60分钟。30/60/90分钟通常约3/6/9个主题；讨论深度优先于问完题目，未问留空。明确要求全面审查、自查所有疑点时用`meta.depth="ultra"`，不限时，但仍按主题组织，不把穷尽变成无关联题目列表。审查覆盖量化结果、本人贡献、时间线与缺少依据的能力声明，不编造疑点。

## 分析与渲染

流程为Triage → 分域Probe → Author → Verify/Revise；问题库仅供选题，不能直接拼成最终散题。详细提示和schema见[流水线契约](reference/pipeline-spec.md)。`meta`包含`title/date/lang/minutes/depth/links`，候选人输入包含`id/label/role_hint/resume/resume_text`；日期取当前会话。`meta.links`仅放评分卡入口。

可用Workflow时运行`scripts/analyze.js`。无该运行时则按同一契约组织当前agent分析或使用`scripts/analyze_portable.py`；不要为了运行脚本擅自配置付费API。分域工作可由子agent执行，最终独立检查技术准确性、问题衔接、研究层次与逐问回答对应。参考回答不是唯一标准答案。

最终载荷为`{"meta":{...},"candidates":{"A":{...}}}`。每张卡片包含`ladder[{level,q,answer}]`、`ask/ask_answer`、`probe/probe_answer`、`followups[{q,answer,when}]`以及单列的`pass/tell`；`good`保留给旧格式兼容。候选人级`probes[{tag,q,answer}]`仅容纳独立合作或材料问题。结构详见契约。

运行：

```text
python SK/scripts/render.py <work>/payload.json <output_dir> <slug>
```

渲染器直接把技术追问放入所属主题，并将示范回答放在对应问题下面。旧载荷可显示，但新增内容应使用逐问字段，不依赖输出后手改或项目私有渲染补丁。

## 核验与返回

- 内容检查：每问是否有清楚的讨论对象；是否承接主题；是否仍以岗位所需判断为主；是否一问对应一答；答案是否遗漏子问题或虚构经历。修改措辞时同时检查答案和评分提示。
- 技术与事实检查：不同版本和口径先列待确认；不要把未搜索到当作不存在。按实际工具可用性核实一手资料，并把来源与局限写进指南。
- 结构检查：Markdown与HTML中技术追问都位于对应主题内；独立事项不混入技术主题。折叠答案后仍能看见所有问题。
- 页面检查：本地链接存在、没有远程依赖，评分保存与折叠有效；限时单人评分卡检查A4分页。对变更运行`scripts/test_render.py`（如存在），并用实际材料检查页面。
- 中文风格与禁用词按写作规范；跨语言输出运行`python SK/scripts/check_lang.py <work>/payload.json`。

返回三件套的绝对路径链接，说明本次主要修改和实际验证范围。更新技能时同时对齐说明、生成提示/schema和渲染行为，不能只在文档末尾追加一条与原工作流冲突的规则。
