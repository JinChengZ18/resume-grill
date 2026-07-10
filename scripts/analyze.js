export const meta = {
  name: 'resume-grill-analyze',
  description: 'From resume text, produce a per-candidate adversarial interview payload (profile, red flags, opener, 6 answer-keyed kill questions, supplementary probes), fact-checked. Output language follows the résumé (or an explicit lang override).',
  phases: [
    { title: 'Triage', detail: 'read each resume → profile, red flags, probe-worthy domains' },
    { title: 'Probe', detail: 'one interrogator per domain' },
    { title: 'Author', detail: 'pick ~6 kill questions and write bulleted answer keys' },
    { title: 'Verify', detail: 'fact-check answer keys, apply corrections' },
  ],
}

// args = { meta:{title,subtitle,date,by,links,footer,lang}, lang?, candidates:[{id,label,role_hint,resume,resume_text}] , nCore? }
// lang: 'zh' | 'en' | any ISO code | 'auto'（缺省）。auto 时按简历正文自动判定，使产物语言与输入一致。
// Tolerate args arriving as a JSON string (some launch paths stringify it).
const A = (typeof args === 'string' ? JSON.parse(args) : args) || {}
const CANDS = A.candidates || []
const NCORE = A.nCore || 6

// ---- output language: explicit override wins, else auto-detect from résumé text ----
function detectLang(text){
  const s = String(text || '')
  const han = (s.match(/[㐀-鿿豈-﫿]/g) || []).length
  const latin = (s.match(/[A-Za-z]/g) || []).length
  if (han === 0) return 'en'
  return han / (han + latin + 1) > 0.1 ? 'zh' : 'en'
}
const LANG = (() => {
  // explicit override wins per tier (skip 'auto'); mirrors analyze_portable.resolve_lang
  for (const cand of [A.lang, A.meta && A.meta.lang]) {
    const x = String(cand || '').toLowerCase()
    if (x && x !== 'auto') return x
  }
  return detectLang(CANDS.map(c => c.resume_text || '').join('\n'))
})()

const BANNED = '交付、再生、天然、免费、回连、让渡、封顶、能量账、省下、补上、旋钮、喂、健壮、落地'
function directive(lang){
  if (lang === 'zh') return `全部用简体中文输出；散文遵循中英文之间不加多余空格、中文用全角标点；不要出现这些词：${BANNED}。`
  if (lang === 'en') return `Write ALL output — every field, question, and answer key — in natural, direct English technical prose.`
  return `Write ALL output — every field, question, level label, and answer key — in the language with ISO code "${lang}" (the résumé's own language). Keep it natural and idiomatic.`
}
const LANGNOTE = `【输出语言】${directive(LANG)}`

const ROLE = `你是一线科技公司的资深技术面试官，风格严苛、对简历注水极度敏感。你深知简历常见把戏：大量"参与"其实贡献极小；百分比指标（"节省65%""提升28%"）常无严谨基线；课程/短期项目包装成"系统"；术语背后是调库还是真懂原理需要戳穿。提问必须具体、扎进底层实现（数据结构/阈值/失败模式/评估口径/为何这么选），能区分"真做过"与"只会写在简历上"。同时你也是公正的评估者：在戳穿注水的同时，如实识别候选人真实、可验证的强项与亮点——扎实的技术深度、真实的 ownership、诚实的自我降级都算加分项。不为对抗而对抗：候选人确实强就大方肯定，确实弱也不硬挑刺、不为凑数编造红旗；据实评价，不强求优缺点对称、不面面俱到。`

const TRIAGE = {
  type:'object', additionalProperties:false,
  properties:{
    profile:{type:'string', description:'3-4句画像+整体可信度判断（真本事约几成、包装约几成）；均衡如实，既不美化也不刻意贬低'},
    ruler:{type:'string', description:'该用什么标尺衡量（应届/初级/中级；点出关键事实如真实全职月数）'},
    strengths:{type:'array', items:{type:'string'}, description:'真实、可验证的强项/亮点：直接引用简历依据+为何算加分（真实生产经历、扎实底层细节、诚实降级、稀缺/对口技能栈等）；有几条写几条（约2-5条），确实乏善可陈就少列或说明，不硬凑、不与红旗强行对称'},
    flags:{type:'array', items:{type:'string'}, description:'关键红旗，直接引用可疑话术+为何可疑；注水多就多列、简历干净就少列（通常3-6条），不硬凑'},
    opener:{type:'object', additionalProperties:false, properties:{
      title:{type:'string'}, questions:{type:'array', items:{type:'string'}},
      expect:{type:'string', description:'期望的行为（强信号）'}, tell:{type:'string', description:'露馅信号'}
    }, required:['title','questions','expect','tell'], description:'开场态度/事实题（时间线/可展示性/ownership核对）'},
    domains:{type:'array', items:{type:'object', additionalProperties:false, properties:{
      key:{type:'string'}, focus:{type:'string', description:'该域最该拷问的实现细节/失败模式清单'}
    }, required:['key','focus']}, description:'4-6个最值得对抗性拷问的技术域，须贴合本简历的真实项目'}
  }, required:['profile','ruler','strengths','flags','opener','domains']
}
const PROBE = {
  type:'object', additionalProperties:false,
  properties:{ domain:{type:'string'},
    questions:{type:'array', items:{type:'object', additionalProperties:false, properties:{
      q:{type:'string'}, probes:{type:'string', description:'这一问在验证什么'},
      strong:{type:'string', description:'真做过的人会怎么答'}, tell:{type:'string', description:'只堆术语的人会怎么露馅'},
      followup:{type:'string'}
    }, required:['q','probes','strong','tell']}}
  }, required:['domain','questions']
}
const CARD = {
  type:'object', additionalProperties:false, properties:{ n:{type:'string'}, title:{type:'string'},
    anchor:{type:'string', description:'本题挂靠的简历项目/宣称（从简历出发的锚点，如「TraceFix 多Agent」「NL2SQL 实习」）'},
    ladder:{type:'array', items:{type:'object', additionalProperties:false, properties:{
      level:{type:'string', description:'L1 项目切入 或 L2 设计决策'}, q:{type:'string'} }, required:['level','q']},
      description:'由浅入深的提问阶梯（恰好2级，作为硬核题的暖场引子）：L1=从该简历项目切入的概览/general 问题，让候选人先自述、暴露信息与切入点；L2=关键设计决策/为什么这么选。ask 本身即 L3 硬核验伪题。'},
    ask:{type:'string', description:'L3 建议提问（硬核验伪）：完整、具体、能戳穿话术'},
    good:{type:'array', items:{type:'string'}, description:'期望的优质回答，5-8个分点，技术准确、含取舍/阈值/机制'},
    pass:{type:'array', items:{type:'string'}, description:'及格线：必须听到的关键点，3-5条'},
    tell:{type:'string', description:'典型露馅'}, probe:{type:'string', description:'逼到底层的追问'} },
  required:['n','title','anchor','ladder','ask','good','pass','tell','probe']
}
const AUTHOR = {
  type:'object', additionalProperties:false, properties:{
    cards:{type:'array', items:CARD, description:`恰好${NCORE}张核心验伪题卡，题号Q1..Q${NCORE}，选最能一击验伪的`},
    probes:{type:'array', items:{type:'object', additionalProperties:false, properties:{
      tag:{type:'string', description:'行首主题标签，如 RAG/可观测性'}, q:{type:'string'} }, required:['tag','q']},
      description:'补充探针（无标准答案），去重后按主题标签排列'}
  }, required:['cards','probes']
}
const VERIFY = { type:'object', additionalProperties:false, properties:{
  corrections:{type:'array', items:{type:'object', additionalProperties:false, properties:{
    n:{type:'string'}, severity:{type:'string', enum:['error','imprecise','overclaim','missing']},
    issue:{type:'string'}, fix:{type:'string'} }, required:['n','severity','issue','fix']}},
  verdict:{type:'string'} }, required:['corrections','verdict'] }

async function analyzeOne(c){
  const resume = `候选人 ${c.label||c.id}｜岗位线索：${c.role_hint||'（未指定）'}\n简历正文：\n---\n${c.resume_text||''}\n---`

  // 1) Triage
  const tri = await agent(`${ROLE}\n\n${resume}\n\n任务：通读简历做面试前研判。给出：画像+可信度（均衡如实）、该用的标尺、真实可验证的强项/亮点（有几条写几条、乏善可陈不硬凑）、关键红旗（注水多就多列、干净就少列，不硬凑）、一组开场态度/事实题（时间线/可展示性/ownership），以及4-6个最值得对抗性拷问的技术域（贴合其真实项目，每域列出该戳的实现细节/失败模式）。既要戳穿注水，也要如实肯定真本事，不强求优缺点对称。\n\n${LANGNOTE}`,
    { label:`triage:${c.id}`, phase:'Triage', schema:TRIAGE, effort:'high' })
  if(!tri) return null

  // 2) Probe each domain in parallel
  const probes = (await parallel((tri.domains||[]).map(d => () =>
    agent(`${ROLE}\n\n${resume}\n\n只聚焦这一个技术域做对抗性拷问：【${d.key}】\n重点覆盖：${d.focus}\n产出5-8个由浅入深、层层设套的问题（每题：验证什么/真做过怎么答/只堆术语怎么露馅/一个逼底层的追问），具体到实现层，不要泛泛而谈。\n\n${LANGNOTE}`,
      { label:`probe:${c.id}:${d.key}`, phase:'Probe', schema:PROBE, effort:'high' })
  ))).filter(Boolean)

  // 3) Author kill questions + answer keys
  const authored = await agent(`${ROLE}\n\n${resume}\n\n以下是分域拷问的问题库（JSON）：\n${JSON.stringify({triage:{flags:tri.flags,domains:tri.domains}, probes}, null, 1)}\n\n作为首席面试官，收敛出恰好${NCORE}道"核心验伪题"（题号Q1..Q${NCORE}）——最能区分"真做过"与"只会写简历"、且无法靠背术语蒙混的题。每道题都要：①挂靠到一个具体简历项目/宣称（anchor）；②做好提问分层，给一个恰好2级的暖场阶梯（ladder）——L1 从该简历项目切入的概览/general 问题（先让候选人自己讲，既给他展开空间也给你观察点与切入口），L2 关键设计决策/为什么这么选；ask 则落到实现层、无法靠背术语蒙混的 L3 硬核验伪。此外每道给：期望的优质回答（5-8个分点、技术准确、含机制/阈值/取舍）、及格线（必须听到的3-5点）、典型露馅、追问。另把其余有价值的问题去重整理为"补充探针"（每条带主题标签）。\n\n${LANGNOTE}`,
    { label:`author:${c.id}`, phase:'Author', schema:AUTHOR, effort:'high' })
  if(!authored) return null

  // 4) Fact-check the answer keys
  const ver = await agent(`你是横跨AI基础设施/RAG/多Agent/建模/系统的资深技术专家，对下面这份面试"标准答案(answer key)"做对抗式事实核查。逐条检查 good 与 pass 是否有：技术性错误、不精确、夸大（把课程/理论说成工业标准）、关键遗漏。只报真正的问题，准确的不要报。\n\n答案(JSON)：\n${JSON.stringify(authored.cards, null, 1)}\n\n${LANGNOTE}`,
    { label:`verify:${c.id}`, phase:'Verify', schema:VERIFY, effort:'high' })

  let cards = authored.cards
  if(ver && (ver.corrections||[]).length){
    const revised = await agent(`${ROLE}\n\n下面是核心验伪题的答案键(JSON)与事实核查发现的问题(JSON)。请按核查意见修正 good/pass 中的错误/不精确/夸大/遗漏，保持题目与结构不变、其余内容不动，返回修正后的完整卡片数组。\n\n卡片：\n${JSON.stringify(authored.cards, null, 1)}\n\n核查：\n${JSON.stringify(ver.corrections, null, 1)}\n\n${LANGNOTE}`,
      { label:`revise:${c.id}`, phase:'Verify', schema:{type:'object', additionalProperties:false, properties:{cards:{type:'array', items:CARD}}, required:['cards']}, effort:'high' })
    if(revised && revised.cards && revised.cards.length) cards = revised.cards
  }

  return { id:c.id, cand:{
    name: c.label || c.id, resume: c.resume || null,
    profile: tri.profile, ruler: tri.ruler, strengths: tri.strengths, flags: tri.flags,
    opener: tri.opener, cards, probes: authored.probes,
    _factcheck: ver ? ver.verdict : null
  }}
}

phase('Triage')
const results = (await parallel(CANDS.map(c => () => analyzeOne(c)))).filter(Boolean)

const candidates = {}
for(const r of results) candidates[r.id] = r.cand
return { meta: { ...(A.meta || {}), lang: LANG }, candidates }
