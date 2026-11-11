export const meta = {
  name: 'resume-grill-analyze',
  description: 'From resume text, produce a per-candidate adversarial interview payload (profile, red flags, opener, role-appropriate topic questions with per-question spoken examples and nested follow-ups), fact-checked. Output language follows the résumé (or an explicit lang override).',
  phases: [
    { title: 'Triage', detail: 'read each resume → profile, red flags, probe-worthy domains' },
    { title: 'Probe', detail: 'one reviewer per topic' },
    { title: 'Author', detail: 'organize topic questions, spoken examples and separate grading criteria' },
    { title: 'Verify', detail: 'review question logic and every answer, apply corrections' },
  ],
}

// args = { meta:{title,subtitle,date,by,links,footer,lang,minutes}, lang?, minutes?, candidates:[{id,label,role_hint,resume,resume_text}] , nCore? }
// lang: 'zh' | 'en' | any ISO code | 'auto'（缺省）。auto 时按简历正文自动判定，使产物语言与输入一致。
// minutes: 面试时长（分钟，缺省 60）。时长决定核心题数量与拷问深度：短则少而聚焦、长则多而细。
// Tolerate args arriving as a JSON string (some launch paths stringify it).
const A = (typeof args === 'string' ? JSON.parse(args) : args) || {}
const CANDS = A.candidates || []

// ---- interview duration → how many core questions, and how deep to dig ----
// depth 档位由 minutes 推导；也可用 meta.depth 显式指定。'ultra' 是全面审查模式：
// 不限时、不设题数上限，穷尽简历里每一处可能被追问的疑点（面试官深挖 / 候选人面试前自查）。
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v))
const TIER = { quick:{opener:4,buffer:5}, standard:{opener:5,buffer:7}, deep:{opener:6,buffer:9} }
const FLAGS_NORMAL = "只列材料支持的待澄清事项，不推断动机、不凑数量"
const DEPTHS = {
  "quick": {
    "rungs": 1,
    "good": "4-5",
    "pass": "2-3",
    "probes": "按需",
    "domains": "3-4",
    "flags": "只列材料支持的待澄清事项，不推断动机、不凑数量",
    "note": "时间紧：聚焦关键判断，保留1级切入与开放推演；技术追问在主题内按需选问。"
  },
  "standard": {
    "rungs": 2,
    "good": "5-8",
    "pass": "3-5",
    "probes": "按需",
    "domains": "4-6",
    "flags": "只列材料支持的待澄清事项，不推断动机、不凑数量",
    "note": "常规时长：L1问题与价值、L2路线取舍、ask开放推演；每问给口述示范，判分另列。"
  },
  "deep": {
    "rungs": 2,
    "good": "7-10",
    "pass": "4-6",
    "probes": "按需",
    "domains": "6-8",
    "flags": "只列材料支持的待澄清事项，不推断动机、不凑数量",
    "note": "时间充裕：加强竞争解释、机制与证据讨论，不把深度等同于操作细节；追问仍归原主题。"
  },
  "ultra": {
    "rungs": 2,
    "good": "6-10",
    "pass": "3-6",
    "probes": "按需",
    "domains": "8-12",
    "flags": "只列材料支持的待澄清事项，不推断动机、不凑数量",
    "note": "全面审查：覆盖重要判断与待澄清事项，按主题合并，不为每个细节独立造题；追问数量不设配额。"
  }
}
function planFor(minutes, depthOverride){
  const forced = String(depthOverride || '').toLowerCase()
  const hasForced = Object.prototype.hasOwnProperty.call(DEPTHS, forced)
  if (hasForced && forced === 'ultra')             // 全面审查：不限时、题数由疑点数量决定
    return { minutes:null, opener:null, buffer:null, depth:'ultra', nCore:null, perQuestion:null }
  const m = clamp(Number(minutes) || 60, 10, 240)
  const depth = hasForced ? forced : (m < 40 ? 'quick' : (m >= 85 ? 'deep' : 'standard'))
  const { opener, buffer } = TIER[depth]
  const perQ = 8                                  // 60min → 5 + 6×8 + 7 → nCore 6（沿用既有默认）
  const core = Math.max(m - opener - buffer, perQ)
  const nCore = clamp(Math.round(core / perQ), 2, 12)
  // floor so opener + nCore×perQuestion + buffer never overruns the slot
  return { minutes: m, opener, buffer, depth, nCore, perQuestion: Math.max(4, Math.floor(core / nCore)) }
}
const PLAN = planFor(A.minutes || (A.meta && A.meta.minutes), A.depth || (A.meta && A.meta.depth))
const ULTRA = PLAN.depth === 'ultra'
const NCORE = A.nCore || PLAN.nCore || 0         // explicit nCore wins; 0 = 由疑点数量决定（ultra）
const DEPTH = DEPTHS[PLAN.depth]

// ultra 必须逐项覆盖的疑点清单——这是"穷尽"的可执行定义
const ULTRA_CHECKLIST = "覆盖材料中有依据的重要主张、量化口径、本人贡献、技术能力、时间线与经历性质；按主题整合，普通合作或版本确认独立列出。缺少证明不等于虚构，重叠经历不自动构成矛盾。"
const PACING = ULTRA
  ? `本次不是限时面试，而是对这份简历做【全面审查】：不设时间盒、不设题数上限，穷尽其中所有疑点。${DEPTH.note}`
  : `本场面试约 ${PLAN.minutes} 分钟：开场约 ${PLAN.opener} 分钟，${NCORE} 道核心题每题约 ${PLAN.perQuestion} 分钟，留约 ${PLAN.buffer} 分钟收尾。${DEPTH.note}`

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
// 简历语言可能与输出语言不同：引用简历措辞时必须译成输出语言，绝不照抄原文字符。
function directive(lang){
  if (lang === 'zh') return `全部用简体中文输出；散文遵循中英文之间不加多余空格、中文用全角标点；不要出现这些词：${BANNED}。简历若为外文，引用其措辞时先译成中文再引用（通用技术名词可保留英文原词）。`
  if (lang === 'en') return `Write ALL output — every field, question, level label, and answer key — in natural, direct English technical prose. The résumé itself may be written in another language: when you cite its wording to ground a strength or a red flag, TRANSLATE the cited phrase into English. Never reproduce the original characters. Your output must contain NO CJK characters at all — not in quotes, not in parentheses, not as examples. Write e.g. "participated in", never the original word.`
  return `Write ALL output — every field, question, level label, and answer key — in the language with ISO code "${lang}". The résumé may be written in a different language: translate any phrase you cite from it into that language, and never reproduce the résumé's original script. Keep it natural and idiomatic.`
}
const LANGNOTE = `【输出语言】${directive(LANG)}`

const ROLE = "你是公正而有技术判断力的资深面试官。根据岗位与经历选择评价层次：研究及高级岗位优先讨论研究意义、机制、替代路线、取舍、证据与适用边界；工程岗位围绕真实任务的设计判断与结果。具体上下文不等于操作盘问，不能用命令、参数或指标核对取代主要问题。问题礼貌、开放、可讨论，不设套、不预设注水、动机或人格结论；材料差异是待澄清信息。HR评价仅作有来源的转述，转成合作预期的中性问题。肯定有依据的强项，诚实限定已知范围是正面信号；合理替代路线同样得分。避免空泛套话与人为二分，允许第三条路线及任务依赖的答案。每问的示范回答须可以直接口述，回答该问并说明理由；示范不是候选人真实经历，不编造其贡献、实验、数值或承诺。需要实例时明确标为假设示例，不用占位符绕过核心推理。good/pass只写面试官判分依据，与示范回答分离。所有技术追问就近归入原主题的probe或followups，不在文末堆放技术题；probes仅用于独立合作安排或材料确认。"

const TRIAGE = {
  "type": "object",
  "additionalProperties": false,
  "required": [
    "profile",
    "ruler",
    "strengths",
    "flags",
    "opener",
    "domains"
  ],
  "properties": {
    "profile": {
      "type": "string"
    },
    "ruler": {
      "type": "string"
    },
    "strengths": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "flags": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "opener": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "title",
        "questions",
        "expect",
        "tell"
      ],
      "properties": {
        "title": {
          "type": "string"
        },
        "questions": {
          "type": "array",
          "items": {
            "type": "string"
          }
        },
        "expect": {
          "type": "string"
        },
        "tell": {
          "type": "string"
        }
      }
    },
    "domains": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "key",
          "focus"
        ],
        "properties": {
          "key": {
            "type": "string"
          },
          "focus": {
            "type": "string"
          }
        }
      }
    }
  }
}
const PROBE = {
  "type": "object",
  "additionalProperties": false,
  "required": [
    "domain",
    "questions"
  ],
  "properties": {
    "domain": {
      "type": "string"
    },
    "questions": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "q",
          "probes",
          "strong",
          "tell",
          "followup",
          "followup_answer",
          "when"
        ],
        "properties": {
          "q": {
            "type": "string"
          },
          "probes": {
            "type": "string"
          },
          "strong": {
            "type": "string"
          },
          "tell": {
            "type": "string"
          },
          "followup": {
            "type": "string"
          },
          "followup_answer": {
            "type": "string"
          },
          "when": {
            "type": "string"
          }
        }
      }
    }
  }
}
const CARD = {
  "type": "object",
  "additionalProperties": false,
  "required": [
    "n",
    "title",
    "anchor",
    "ladder",
    "ask",
    "good",
    "pass",
    "tell",
    "probe",
    "ask_answer",
    "probe_answer",
    "followups"
  ],
  "properties": {
    "n": {
      "type": "string"
    },
    "title": {
      "type": "string"
    },
    "anchor": {
      "type": "string"
    },
    "ladder": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "level",
          "q",
          "answer"
        ],
        "properties": {
          "level": {
            "type": "string"
          },
          "q": {
            "type": "string"
          },
          "answer": {
            "type": "string"
          }
        }
      }
    },
    "ask": {
      "type": "string"
    },
    "good": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "pass": {
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "tell": {
      "type": "string"
    },
    "probe": {
      "type": "string"
    },
    "ask_answer": {
      "type": "string"
    },
    "probe_answer": {
      "type": "string"
    },
    "followups": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "q",
          "answer",
          "when"
        ],
        "properties": {
          "q": {
            "type": "string"
          },
          "answer": {
            "type": "string"
          },
          "when": {
            "type": "string"
          }
        }
      }
    }
  }
}
const AUTHOR = {
  "type": "object",
  "additionalProperties": false,
  "required": [
    "cards",
    "probes"
  ],
  "properties": {
    "cards": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "n",
          "title",
          "anchor",
          "ladder",
          "ask",
          "good",
          "pass",
          "tell",
          "probe",
          "ask_answer",
          "probe_answer",
          "followups"
        ],
        "properties": {
          "n": {
            "type": "string"
          },
          "title": {
            "type": "string"
          },
          "anchor": {
            "type": "string"
          },
          "ladder": {
            "type": "array",
            "items": {
              "type": "object",
              "additionalProperties": false,
              "required": [
                "level",
                "q",
                "answer"
              ],
              "properties": {
                "level": {
                  "type": "string"
                },
                "q": {
                  "type": "string"
                },
                "answer": {
                  "type": "string"
                }
              }
            }
          },
          "ask": {
            "type": "string"
          },
          "good": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "pass": {
            "type": "array",
            "items": {
              "type": "string"
            }
          },
          "tell": {
            "type": "string"
          },
          "probe": {
            "type": "string"
          },
          "ask_answer": {
            "type": "string"
          },
          "probe_answer": {
            "type": "string"
          },
          "followups": {
            "type": "array",
            "items": {
              "type": "object",
              "additionalProperties": false,
              "required": [
                "q",
                "answer",
                "when"
              ],
              "properties": {
                "q": {
                  "type": "string"
                },
                "answer": {
                  "type": "string"
                },
                "when": {
                  "type": "string"
                }
              }
            }
          }
        }
      }
    },
    "probes": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "tag",
          "q",
          "answer"
        ],
        "properties": {
          "tag": {
            "type": "string"
          },
          "q": {
            "type": "string"
          },
          "answer": {
            "type": "string"
          }
        }
      }
    }
  }
}
const VERIFY = {
  "type": "object",
  "additionalProperties": false,
  "required": [
    "corrections",
    "verdict"
  ],
  "properties": {
    "corrections": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": [
          "n",
          "severity",
          "issue",
          "fix"
        ],
        "properties": {
          "n": {
            "type": "string"
          },
          "severity": {
            "type": "string",
            "enum": [
              "error",
              "imprecise",
              "overclaim",
              "missing"
            ]
          },
          "issue": {
            "type": "string"
          },
          "fix": {
            "type": "string"
          }
        }
      }
    },
    "verdict": {
      "type": "string"
    }
  }
}

const AUTHOR_RULES = "各题围绕一个具体项目背景和重要判断组织，避免只是把通用问题换上项目名。研究及高级岗位由意义与问题进入路线取舍，再用ask讨论开放推演、竞争解释、证据或边界；其他岗位匹配其实际设计职责，不能一律降为底层操作核对。每问只推进一个主要判断，不堆砌多个考试点。ladder每项给answer，ask给ask_answer，probe给probe_answer；这些都是直接回答对应问题的可口述示范，说明观点、理由和边界；good/pass另写判分维度，不能用评分要点冒充逐问回答。允许不同研究路线，不把一种示范设成唯一答案。不虚构候选人事实；需要例子则明确标为假设，且完成推理。probe是主题主线的顺势追问（可空）；followups只放根据回答选用的额外技术分支，不重复ladder、ask或probe，每项含q、answer、when。when说明何时值得选问，followups可为空，不凑数；没有必要的probe时probe与probe_answer都为空串。probes仅收录独立合作安排或材料确认，每项tag、q、answer；技术问题不得散落在文末。HR转述不能变成事实或人格结论；把相关内容改成中性、可澄清的合作预期问题。"
const VERIFY_RULES = "独立审核完整面试内容与参考回答。检查问题层次是否匹配岗位，是否有研究意义、机制、替代路线、取舍与论据；检查人为二分、暗含结论、设套、不礼貌、空泛套话，以及用操作盘问取代主要判断。逐问检查ladder.answer、ask_answer、probe_answer、followups[].answer、probes[].answer是否直接回答对应问题，是否技术正确、逻辑成立、边界准确，是否编造候选人经历、数字、贡献或承诺。假设示例应明确标注。检查good/pass是否与口述示范分离，是否允许合理替代答案；HR仅作转述。检查技术追问是否归属原主题、文末probes是否仅独立合作安排/材料确认。只报实质问题；n填题号或字段路径。缺少外部来源时标明待核实，不能声称已完成外部事实确认。"
async function analyzeOne(c){
  const resume = `候选人 ${c.label||c.id}｜岗位线索：${c.role_hint||'（未指定）'}\n简历正文：\n---\n${c.resume_text||''}\n---`
  const tri = await agent(`${ROLE}\n${resume}\n${PACING}\n通读材料，给出有依据的画像、岗位标尺、强项与待澄清事项，不估算包装比例、不预设嫌疑。开场邀请选择参与深入的问题展开。提炼贴合项目的主题，每域focus写重要问题、机制、路线选择和证据边界。主题建议${DEPTH.domains}个，不为数量重复。${ULTRA ? ULTRA_CHECKLIST : ''}\n${LANGNOTE}`,
    {label:`triage:${c.id}`, phase:'Triage', schema:TRIAGE, effort:'high'})
  if(!tri) return null
  const probes = (await parallel((tri.domains||[]).map(d => () =>
    agent(`${ROLE}\n${resume}\n聚焦主题：${d.key}\n关注：${d.focus}\n提出由浅入深的问题，数量按需要，不凑配额。先讨论意义、机制与取舍，按需要追问证据。q为礼貌的具体问题；probes说明评价目的；strong为可口述示范；tell只写论证缺口；followup、followup_answer、when给同主题追问、对应示范及选问条件，无必要则置空。技术问题最终合并回原主题，不能散落文末。\n${LANGNOTE}`,
      {label:`probe:${c.id}:${d.key}`, phase:'Probe', schema:PROBE, effort:'high'})
  ))).filter(Boolean)
  const ladderSpec = DEPTH.rungs === 1
    ? 'ladder恰好1级，聚焦项目的重要判断或路线取舍，并给本问answer。'
    : 'ladder恰好2级，L1问题与意义、L2路线与取舍，每级分别给answer。'
  const mission = ULTRA
    ? `按主题覆盖全部重要主张，按Q1、Q2编号，不设题数配额。${ULTRA_CHECKLIST}`
    : `组织恰好${NCORE}道核心主题题，按Q1..Q${NCORE}编号，每题约${PLAN.perQuestion}分钟，追问选用。`
  const authored = await agent(`${ROLE}\n${resume}\n${PACING}\n分域材料：\n${JSON.stringify({triage:tri,probes})}\n${mission}${ladderSpec}${AUTHOR_RULES}\n${LANGNOTE}`,
    {label:`author:${c.id}`, phase:'Author', schema:AUTHOR, effort:'high'})
  if(!authored) return null
  const ver = await agent(`${ROLE}\n${VERIFY_RULES}\n材料供归因核对：\n${resume}\n完整内容：\n${JSON.stringify(authored)}\n${LANGNOTE}`,
    {label:`verify:${c.id}`, phase:'Verify', schema:VERIFY, effort:'high'})
  let content = authored
  if(ver && (ver.corrections||[]).length){
    const revised = await agent(`${ROLE}\n按审核意见修订受影响的问题、逐问示范与判分，不得只改good/pass而遗留错误问题。保持题号和主题归属；必要时把技术尾部题迁回相应followups。返回完整cards与probes。未受影响内容保持原意，检查每问回答与题意一致。${AUTHOR_RULES}\n原材料：\n${resume}\n内容：\n${JSON.stringify(authored)}\n审核：\n${JSON.stringify(ver.corrections)}\n${LANGNOTE}`,
      {label:`revise:${c.id}`, phase:'Verify', schema:AUTHOR, effort:'high'})
    if(revised && revised.cards && revised.cards.length) content = revised
  }
  return {id:c.id, cand:{
    name:c.label||c.id, resume:c.resume||null,
    profile:tri.profile, ruler:tri.ruler, strengths:tri.strengths, flags:tri.flags,
    opener:tri.opener, cards:content.cards, probes:content.probes,
    _factcheck:ver ? ver.verdict : null
  }}
}

phase('Triage')
const results = (await parallel(CANDS.map(c => () => analyzeOne(c)))).filter(Boolean)

const candidates = {}
for(const r of results) candidates[r.id] = r.cand
return { meta: { ...(A.meta || {}), lang: LANG, plan: { ...PLAN, nCore: NCORE || null } }, candidates }
