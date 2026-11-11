#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_portable.py — 运行无关的分析编排（不依赖 Claude Code 的 Workflow 运行时）。

实现 reference/pipeline-spec.md 的四阶段流水线（Triage → Probe → Author → Verify/Revise），
只依赖一个你接入自己模型的结构化输出回调 call_llm(system, user, schema) -> dict。
产出的 payload.json 与原生 analyze.js 完全同构，交给 render.py 渲染三件套。

用法:
  # 直接给 analyze.js 同构的 args（{meta, candidates:[{id,label,role_hint,resume,resume_text}]}）
  python analyze_portable.py --in args.json --out payload.json
  # 或给 extract_pdf.py 产出的 resumes.json，自动编排候选人 A/B/...
  python analyze_portable.py --resumes resumes.json --out payload.json [--title "..."] [--date YYYY-MM-DD]
  # 单调回退：一次模型调用产出全部（跳过分域 Probe，深度略降，结构一致）
  python analyze_portable.py --resumes resumes.json --out payload.json --single

输出语言:
  缺省 --lang auto：按简历正文自动判定（中文简历出中文、英文简历出英文），使产物语言与输入一致。
  也可显式指定 --lang zh|en|<ISO 码>（写进 payload.meta.lang，render.py 据此本地化界面文案）。

面试时长与深度档位:
  --minutes N（缺省 60）决定核心题数量与拷问深度：30 分钟 → 少而聚焦（阶梯 1 级、答案键写精）；
  60 分钟 → 6 道常规；90+ 分钟 → 更多题、更细的答案键与更多技术域。--ncore 可显式覆盖题数。
  --depth quick|standard|deep|ultra 显式指定档位（覆盖 --minutes 推导）。
  ultra = 全面审查模式（面试官逐条深挖 / 候选人面试前自查）：不限时、不设题数上限，
  穷尽简历中每一处真实存在的疑点（通常 12-24 题），但不得为凑数编造。例：
    python analyze_portable.py --resumes resumes.json --out payload.json --depth ultra

接入模型（三选一）:
  1) 环境变量 RG_LLM_PROVIDER=openai    + OPENAI_API_KEY   (+ RG_LLM_MODEL, 默认 gpt-4.1)
  2) 环境变量 RG_LLM_PROVIDER=anthropic + ANTHROPIC_API_KEY(+ RG_LLM_MODEL, 默认 claude-opus-4-8)
  3) 环境变量 RG_LLM_PROVIDER=custom    + RG_LLM_CALL=your_module:your_func
     其中 your_func(system, user, schema)->dict 用你自己的模型返回符合 schema 的 JSON。
"""
import argparse, importlib, json, math, os, re, sys

NCORE_DEFAULT = 6
BANNED = "交付、再生、天然、免费、回连、让渡、封顶、能量账、省下、补上、旋钮、喂、健壮、落地"

# 面试官人设（语言中立；输出语言由 directive() 追加进 system 提示决定）
ROLE_BASE = '你是公正而有技术判断力的资深面试官。根据岗位与经历选择评价层次：研究及高级岗位优先讨论研究意义、机制、替代路线、取舍、证据与适用边界；工程岗位围绕真实任务的设计判断与结果。具体上下文不等于操作盘问，不能用命令、参数或指标核对取代主要问题。问题礼貌、开放、可讨论，不设套、不预设注水、动机或人格结论；材料差异是待澄清信息。HR评价仅作有来源的转述，转成合作预期的中性问题。肯定有依据的强项，诚实限定已知范围是正面信号；合理替代路线同样得分。避免空泛套话与人为二分，允许第三条路线及任务依赖的答案。每问的示范回答须可以直接口述，回答该问并说明理由；示范不是候选人真实经历，不编造其贡献、实验、数值或承诺。需要实例时明确标为假设示例，不用占位符绕过核心推理。good/pass只写面试官判分依据，与示范回答分离。所有技术追问就近归入原主题的probe或followups，不在文末堆放技术题；probes仅用于独立合作安排或材料确认。'

def detect_lang(text):
    """按简历正文粗判输出语言：含相当比例汉字 → zh，否则 en。"""
    s = text or ""
    han = len(re.findall(r"[㐀-鿿豈-﫿]", s))
    latin = len(re.findall(r"[A-Za-z]", s))
    if han == 0:
        return "en"
    return "zh" if han / (han + latin + 1) > 0.1 else "en"


def directive(lang):
    """输出语言指令，追加到 system 提示末尾，令产物语言与输入一致。

    简历语言可能与输出语言不同：引用简历措辞时必须译成输出语言，绝不照抄原文字符。
    """
    if lang == "zh":
        return ("全部用简体中文输出；散文遵循中英文之间不加多余空格、中文用全角标点；"
                "不要出现这些词：" + BANNED + "。简历若为外文，引用其措辞时先译成中文再引用"
                "（通用技术名词可保留英文原词）。")
    if lang == "en":
        return ("Write ALL output — every field, question, level label, and answer key — in natural, direct "
                "English technical prose. The résumé itself may be written in another language: when you cite "
                "its wording to ground a strength or a red flag, TRANSLATE the cited phrase into English. Never "
                "reproduce the original characters. Your output must contain NO CJK characters at all — not in "
                'quotes, not in parentheses, not as examples. Write e.g. "participated in", never the original word.')
    return ('Write ALL output — every field, question, level label, and answer key — in the language with ISO '
            'code "%s". The résumé may be written in a different language: translate any phrase you cite from it '
            "into that language, and never reproduce the résumé's original script. Keep it natural and idiomatic." % lang)


def role_for(lang):
    return ROLE_BASE + "\n\n【输出语言】" + directive(lang)


# ---- 面试时长 → 核心题数量与拷问深度（与 analyze.js 同一套公式） ----
# depth 由 minutes 推导，也可显式指定。'ultra' 是全面审查模式：不限时、不设题数上限，
# 穷尽简历里每一处可能被追问的疑点（面试官深挖 / 候选人面试前自查）。
FLAGS_NORMAL = '只列材料支持的待澄清事项，不推断动机、不凑数量'
DEPTHS = {'quick': {'rungs': 1, 'good': '4-5', 'pass': '2-3', 'probes': '按需', 'domains': '3-4', 'flags': '只列材料支持的待澄清事项，不推断动机、不凑数量', 'note': '时间紧：聚焦关键判断，保留1级切入与开放推演；技术追问在主题内按需选问。'}, 'standard': {'rungs': 2, 'good': '5-8', 'pass': '3-5', 'probes': '按需', 'domains': '4-6', 'flags': '只列材料支持的待澄清事项，不推断动机、不凑数量', 'note': '常规时长：L1问题与价值、L2路线取舍、ask开放推演；每问给口述示范，判分另列。'}, 'deep': {'rungs': 2, 'good': '7-10', 'pass': '4-6', 'probes': '按需', 'domains': '6-8', 'flags': '只列材料支持的待澄清事项，不推断动机、不凑数量', 'note': '时间充裕：加强竞争解释、机制与证据讨论，不把深度等同于操作细节；追问仍归原主题。'}, 'ultra': {'rungs': 2, 'good': '6-10', 'pass': '3-6', 'probes': '按需', 'domains': '8-12', 'flags': '只列材料支持的待澄清事项，不推断动机、不凑数量', 'note': '全面审查：覆盖重要判断与待澄清事项，按主题合并，不为每个细节独立造题；追问数量不设配额。'}}

ULTRA_CHECKLIST = '覆盖材料中有依据的重要主张、量化口径、本人贡献、技术能力、时间线与经历性质；按主题整合，普通合作或版本确认独立列出。缺少证明不等于虚构，重叠经历不自动构成矛盾。'

def _round_half_up(x):
    """匹配 JS Math.round（正数四舍五入）；Python 内置 round() 是银行家舍入，会与 analyze.js 分叉。"""
    return int(math.floor(x + 0.5))


TIER = {"quick": (4, 5), "standard": (5, 7), "deep": (6, 9)}   # (opener, buffer) 分钟


def plan_for(minutes, depth_override=None):
    forced = str(depth_override or "").lower()
    if forced == "ultra":                    # 全面审查：不限时、题数由疑点数量决定
        return {"minutes": None, "opener": None, "buffer": None, "depth": "ultra",
                "nCore": None, "perQuestion": None}
    m = max(10, min(240, int(minutes or 60)))
    depth = forced if forced in TIER else ("quick" if m < 40 else ("deep" if m >= 85 else "standard"))
    opener, buffer = TIER[depth]
    per_q = 8                                # 60min → 5 + 6×8 + 7 → nCore 6（沿用既有默认）
    core = max(m - opener - buffer, per_q)
    n = max(2, min(12, _round_half_up(core / per_q)))
    # floor so opener + nCore×perQuestion + buffer never overruns the slot
    return {"minutes": m, "opener": opener, "buffer": buffer, "depth": depth, "nCore": n,
            "perQuestion": max(4, int(math.floor(core / n)))}


def pacing_text(plan, ncore):
    note = DEPTHS[plan["depth"]]["note"]
    if plan["depth"] == "ultra":
        return "本次不是限时面试，而是对这份简历做【全面审查】：不设时间盒、不设题数上限，穷尽其中所有疑点。" + note
    return ("本场面试约 %d 分钟：开场约 %d 分钟，%d 道核心题每题约 %d 分钟，留约 %d 分钟收尾。%s"
            % (plan["minutes"], plan["opener"], ncore, plan["perQuestion"], plan["buffer"], note))

# ---- schemas (镜像 analyze.js / pipeline-spec.md) ----
TRIAGE = {'type': 'object',
 'additionalProperties': False,
 'required': ['profile', 'ruler', 'strengths', 'flags', 'opener', 'domains'],
 'properties': {'profile': {'type': 'string'},
                'ruler': {'type': 'string'},
                'strengths': {'type': 'array', 'items': {'type': 'string'}},
                'flags': {'type': 'array', 'items': {'type': 'string'}},
                'opener': {'type': 'object',
                           'additionalProperties': False,
                           'required': ['title', 'questions', 'expect', 'tell'],
                           'properties': {'title': {'type': 'string'},
                                          'questions': {'type': 'array', 'items': {'type': 'string'}},
                                          'expect': {'type': 'string'},
                                          'tell': {'type': 'string'}}},
                'domains': {'type': 'array',
                            'items': {'type': 'object',
                                      'additionalProperties': False,
                                      'required': ['key', 'focus'],
                                      'properties': {'key': {'type': 'string'},
                                                     'focus': {'type': 'string'}}}}}}

PROBE = {'type': 'object',
 'additionalProperties': False,
 'required': ['domain', 'questions'],
 'properties': {'domain': {'type': 'string'},
                'questions': {'type': 'array',
                              'items': {'type': 'object',
                                        'additionalProperties': False,
                                        'required': ['q',
                                                     'probes',
                                                     'strong',
                                                     'tell',
                                                     'followup',
                                                     'followup_answer',
                                                     'when'],
                                        'properties': {'q': {'type': 'string'},
                                                       'probes': {'type': 'string'},
                                                       'strong': {'type': 'string'},
                                                       'tell': {'type': 'string'},
                                                       'followup': {'type': 'string'},
                                                       'followup_answer': {'type': 'string'},
                                                       'when': {'type': 'string'}}}}}}

CARD = {'type': 'object',
 'additionalProperties': False,
 'required': ['n',
              'title',
              'anchor',
              'ladder',
              'ask',
              'good',
              'pass',
              'tell',
              'probe',
              'ask_answer',
              'probe_answer',
              'followups'],
 'properties': {'n': {'type': 'string'},
                'title': {'type': 'string'},
                'anchor': {'type': 'string'},
                'ladder': {'type': 'array',
                           'items': {'type': 'object',
                                     'additionalProperties': False,
                                     'required': ['level', 'q', 'answer'],
                                     'properties': {'level': {'type': 'string'},
                                                    'q': {'type': 'string'},
                                                    'answer': {'type': 'string'}}}},
                'ask': {'type': 'string'},
                'good': {'type': 'array', 'items': {'type': 'string'}},
                'pass': {'type': 'array', 'items': {'type': 'string'}},
                'tell': {'type': 'string'},
                'probe': {'type': 'string'},
                'ask_answer': {'type': 'string'},
                'probe_answer': {'type': 'string'},
                'followups': {'type': 'array',
                              'items': {'type': 'object',
                                        'additionalProperties': False,
                                        'required': ['q', 'answer', 'when'],
                                        'properties': {'q': {'type': 'string'},
                                                       'answer': {'type': 'string'},
                                                       'when': {'type': 'string'}}}}}}

AUTHOR = {'type': 'object',
 'additionalProperties': False,
 'required': ['cards', 'probes'],
 'properties': {'cards': {'type': 'array',
                          'items': {'type': 'object',
                                    'additionalProperties': False,
                                    'required': ['n',
                                                 'title',
                                                 'anchor',
                                                 'ladder',
                                                 'ask',
                                                 'good',
                                                 'pass',
                                                 'tell',
                                                 'probe',
                                                 'ask_answer',
                                                 'probe_answer',
                                                 'followups'],
                                    'properties': {'n': {'type': 'string'},
                                                   'title': {'type': 'string'},
                                                   'anchor': {'type': 'string'},
                                                   'ladder': {'type': 'array',
                                                              'items': {'type': 'object',
                                                                        'additionalProperties': False,
                                                                        'required': ['level', 'q', 'answer'],
                                                                        'properties': {'level': {'type': 'string'},
                                                                                       'q': {'type': 'string'},
                                                                                       'answer': {'type': 'string'}}}},
                                                   'ask': {'type': 'string'},
                                                   'good': {'type': 'array', 'items': {'type': 'string'}},
                                                   'pass': {'type': 'array', 'items': {'type': 'string'}},
                                                   'tell': {'type': 'string'},
                                                   'probe': {'type': 'string'},
                                                   'ask_answer': {'type': 'string'},
                                                   'probe_answer': {'type': 'string'},
                                                   'followups': {'type': 'array',
                                                                 'items': {'type': 'object',
                                                                           'additionalProperties': False,
                                                                           'required': ['q',
                                                                                        'answer',
                                                                                        'when'],
                                                                           'properties': {'q': {'type': 'string'},
                                                                                          'answer': {'type': 'string'},
                                                                                          'when': {'type': 'string'}}}}}}},
                'probes': {'type': 'array',
                           'items': {'type': 'object',
                                     'additionalProperties': False,
                                     'required': ['tag', 'q', 'answer'],
                                     'properties': {'tag': {'type': 'string'},
                                                    'q': {'type': 'string'},
                                                    'answer': {'type': 'string'}}}}}}

VERIFY = {'type': 'object',
 'additionalProperties': False,
 'required': ['corrections', 'verdict'],
 'properties': {'corrections': {'type': 'array',
                                'items': {'type': 'object',
                                          'additionalProperties': False,
                                          'required': ['n', 'severity', 'issue', 'fix'],
                                          'properties': {'n': {'type': 'string'},
                                                         'severity': {'type': 'string',
                                                                      'enum': ['error',
                                                                               'imprecise',
                                                                               'overclaim',
                                                                               'missing']},
                                                         'issue': {'type': 'string'},
                                                         'fix': {'type': 'string'}}}},
                'verdict': {'type': 'string'}}}

REVISE = AUTHOR

SINGLE = {'type': 'object',
 'additionalProperties': False,
 'required': ['profile', 'ruler', 'strengths', 'flags', 'opener', 'cards', 'probes'],
 'properties': {'profile': {'type': 'string'},
                'ruler': {'type': 'string'},
                'strengths': {'type': 'array', 'items': {'type': 'string'}},
                'flags': {'type': 'array', 'items': {'type': 'string'}},
                'opener': {'type': 'object',
                           'additionalProperties': False,
                           'required': ['title', 'questions', 'expect', 'tell'],
                           'properties': {'title': {'type': 'string'},
                                          'questions': {'type': 'array', 'items': {'type': 'string'}},
                                          'expect': {'type': 'string'},
                                          'tell': {'type': 'string'}}},
                'cards': {'type': 'array',
                          'items': {'type': 'object',
                                    'additionalProperties': False,
                                    'required': ['n',
                                                 'title',
                                                 'anchor',
                                                 'ladder',
                                                 'ask',
                                                 'good',
                                                 'pass',
                                                 'tell',
                                                 'probe',
                                                 'ask_answer',
                                                 'probe_answer',
                                                 'followups'],
                                    'properties': {'n': {'type': 'string'},
                                                   'title': {'type': 'string'},
                                                   'anchor': {'type': 'string'},
                                                   'ladder': {'type': 'array',
                                                              'items': {'type': 'object',
                                                                        'additionalProperties': False,
                                                                        'required': ['level', 'q', 'answer'],
                                                                        'properties': {'level': {'type': 'string'},
                                                                                       'q': {'type': 'string'},
                                                                                       'answer': {'type': 'string'}}}},
                                                   'ask': {'type': 'string'},
                                                   'good': {'type': 'array', 'items': {'type': 'string'}},
                                                   'pass': {'type': 'array', 'items': {'type': 'string'}},
                                                   'tell': {'type': 'string'},
                                                   'probe': {'type': 'string'},
                                                   'ask_answer': {'type': 'string'},
                                                   'probe_answer': {'type': 'string'},
                                                   'followups': {'type': 'array',
                                                                 'items': {'type': 'object',
                                                                           'additionalProperties': False,
                                                                           'required': ['q',
                                                                                        'answer',
                                                                                        'when'],
                                                                           'properties': {'q': {'type': 'string'},
                                                                                          'answer': {'type': 'string'},
                                                                                          'when': {'type': 'string'}}}}}}},
                'probes': {'type': 'array',
                           'items': {'type': 'object',
                                     'additionalProperties': False,
                                     'required': ['tag', 'q', 'answer'],
                                     'properties': {'tag': {'type': 'string'},
                                                    'q': {'type': 'string'},
                                                    'answer': {'type': 'string'}}}}}}

# ---- pluggable model call ----
def _load_custom():
    spec = os.environ.get("RG_LLM_CALL", "")
    if ":" not in spec:
        raise RuntimeError("RG_LLM_PROVIDER=custom 需要 RG_LLM_CALL=module:function")
    mod, fn = spec.split(":", 1)
    return getattr(importlib.import_module(mod), fn)

def call_llm(system, user, schema):
    """返回符合 schema 的 dict。按 RG_LLM_PROVIDER 分派；也可整体替换本函数。"""
    provider = os.environ.get("RG_LLM_PROVIDER", "").lower()
    model = os.environ.get("RG_LLM_MODEL", "")
    if provider == "custom":
        return _load_custom()(system, user, schema)
    if provider == "openai":
        from openai import OpenAI
        client = OpenAI()
        r = client.chat.completions.create(
            model=model or "gpt-4.1", temperature=0.2,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            response_format={"type": "json_schema",
                             "json_schema": {"name": "out", "schema": schema, "strict": True}})
        return json.loads(r.choices[0].message.content)
    if provider == "anthropic":
        import anthropic
        client = anthropic.Anthropic()
        r = client.messages.create(
            model=model or "claude-opus-4-8", max_tokens=8000, system=system,
            tools=[{"name": "emit", "description": "return the result", "input_schema": schema}],
            tool_choice={"type": "tool", "name": "emit"},
            messages=[{"role": "user", "content": user}])
        for block in r.content:
            if getattr(block, "type", None) == "tool_use":
                return block.input
        raise RuntimeError("anthropic 未返回 tool_use")
    raise RuntimeError(
        "未接入模型。设 RG_LLM_PROVIDER=openai|anthropic|custom（见文件头），或直接替换 call_llm()。")


# ---- prompts ----
def resume_block(c):
    return ("候选人 %s｜岗位线索：%s\n简历正文：\n---\n%s\n---"
            % (c.get("label") or c.get("id"), c.get("role_hint") or "（未指定）", c.get("resume_text") or ""))

AUTHOR_RULES = (
    "各题围绕一个具体项目背景和重要判断组织，避免只是把通用问题换上项目名。"
    "研究及高级岗位由意义与问题进入路线取舍，再用ask讨论开放推演、竞争解释、证据或边界；"
    "其他岗位匹配其实际设计职责，不能一律降为底层操作核对。每问只推进一个主要判断，不堆砌多个考试点。"
    "ladder每项给answer，ask给ask_answer，probe给probe_answer；这些都是直接回答对应问题的可口述示范，"
    "说明观点、理由和边界；good/pass另写判分维度，不能用评分要点冒充逐问回答。"
    "允许不同研究路线，不把一种示范设成唯一答案。不虚构候选人事实；需要例子则明确标为假设，且完成推理。"
    "probe是主题主线的顺势追问（可空）；followups只放根据回答选用的额外技术分支，不重复ladder、ask或probe，每项含q、answer、when。"
    "when说明何时值得选问，followups可为空，不凑数；没有必要的probe时probe与probe_answer都为空串。"
    "probes仅收录独立合作安排或材料确认，每项tag、q、answer；技术问题不得散落在文末。"
    "HR转述不能变成事实或人格结论；把相关内容改成中性、可澄清的合作预期问题。"
)
VERIFY_RULES = (
    "独立审核完整面试内容与参考回答。检查问题层次是否匹配岗位，是否有研究意义、机制、替代路线、取舍与论据；"
    "检查人为二分、暗含结论、设套、不礼貌、空泛套话，以及用操作盘问取代主要判断。"
    "逐问检查ladder.answer、ask_answer、probe_answer、followups[].answer、probes[].answer是否直接回答对应问题，"
    "是否技术正确、逻辑成立、边界准确，是否编造候选人经历、数字、贡献或承诺。假设示例应明确标注。"
    "检查good/pass是否与口述示范分离，是否允许合理替代答案；HR仅作转述。"
    "检查技术追问是否归属原主题、文末probes是否仅独立合作安排/材料确认。"
    "只报实质问题；n填题号或字段路径。缺少外部来源时标明待核实，不能声称已完成外部事实确认。"
)

def p_triage(rb, plan, dep, ncore):
    return (rb + "\n\n" + pacing_text(plan, ncore) +
            "\n通读材料，给出有依据的画像、岗位标尺、强项与待澄清事项，不估算包装比例、不预设嫌疑。"
            "开场邀请候选人选择参与深入的问题展开；独立安排事项留到收尾。"
            "提炼贴合项目的主题，每域focus写重要问题、机制、路线选择及证据边界。"
            "技术域建议数量为" + dep["domains"] + "，不为数量重复主题。" +
            (ULTRA_CHECKLIST if plan["depth"] == "ultra" else ""))

def p_probe(rb, d):
    return (rb + "\n聚焦主题：" + d.get("key", "") + "\n关注：" + d.get("focus", "") +
            "\n提出由浅入深的问题，数量按需要，不凑配额。先讨论意义、机制和路线取舍，再按需要追问证据。"
            "q为礼貌的具体问题；probes说明评价目的；strong为可口述示范；tell只写论证缺口；"
            "followup、followup_answer、when给同主题追问、对应口述示范及选问条件，无必要追问则置空。"
            "避免设套与预设嫌疑。所有技术问题最终须合并回原主题，不能散落文末。")

def _ladder_spec(dep):
    if dep["rungs"] == 1:
        return "ladder恰好1级，聚焦项目的重要判断或路线取舍，并给本问answer。"
    return "ladder恰好2级，L1问题与意义、L2路线与取舍，每级分别给answer。"

def _mission_spec(n, plan, dep):
    if plan["depth"] == "ultra":
        return "按主题组织覆盖全部重要主张的核心题，按Q1、Q2编号，不设题数配额。" + ULTRA_CHECKLIST
    return "组织恰好%d道核心主题题，按Q1..Q%d编号，每题约%d分钟，追问选用。" % (n, n, plan["perQuestion"])

def p_author(rb, tri, probes, n, plan, dep):
    bank = json.dumps({"triage": tri, "probes": probes}, ensure_ascii=False, indent=1)
    return (rb + "\n" + pacing_text(plan, n) + "\n分域材料：\n" + bank + "\n" +
            _mission_spec(n, plan, dep) + _ladder_spec(dep) + AUTHOR_RULES)

def p_single(rb, n, plan, dep):
    return (p_triage(rb, plan, dep, n) + "\n一次完成画像与核心主题设计。" +
            _mission_spec(n, plan, dep) + _ladder_spec(dep) + AUTHOR_RULES)

def p_verify(content, rb=""):
    return VERIFY_RULES + "\n材料供归因核对：\n" + rb + "\n完整内容：\n" + json.dumps(content, ensure_ascii=False, indent=1)

def p_revise(content, corrections, rb=""):
    return ("按审核意见修订受影响的问题、逐问示范与判分，不得只改good/pass而遗留错误问题。"
            "保持题号和主题归属；必要时将技术尾部题迁回相应followups。返回完整cards与probes。"
            "未受影响内容保持原意，修改后检查每问回答与题意一致。" + AUTHOR_RULES +
            "\n原材料：\n" + rb + "\n内容：\n" + json.dumps(content, ensure_ascii=False, indent=1) +
            "\n审核：\n" + json.dumps(corrections, ensure_ascii=False, indent=1))


# ---- orchestration ----
def analyze_one(c, ncore, single, lang, plan):
    rb = resume_block(c)
    role = role_for(lang)
    dep = DEPTHS[plan["depth"]]
    if single:
        s = call_llm(role, p_single(rb, ncore, plan, dep), SINGLE)
        cards = s.get("cards", [])
        tri = s
        probes = s.get("probes", [])
    else:
        tri = call_llm(role, p_triage(rb, plan, dep, ncore), TRIAGE)
        probes = []
        for d in (tri.get("domains") or []):
            try:
                probes.append(call_llm(role, p_probe(rb, d), PROBE))
            except Exception as e:
                sys.stderr.write("probe failed [%s]: %s\n" % (d.get("key"), e))
        authored = call_llm(role, p_author(rb, tri, probes, ncore, plan, dep), AUTHOR)
        cards = authored.get("cards", [])
        probes = authored.get("probes", [])
    # fact-check + revise
    factcheck = None
    if cards:
        try:
            ver = call_llm(
                ROLE_BASE + "\n\n【输出语言】"
                + directive(lang),
                p_verify({"cards": cards, "probes": probes}, rb), VERIFY)
            factcheck = ver.get("verdict")
            if ver.get("corrections"):
                rev = call_llm(role, p_revise({"cards": cards, "probes": probes}, ver["corrections"], rb), REVISE)
                if rev.get("cards"):
                    cards = rev["cards"]
                    probes = rev["probes"]
        except Exception as e:
            sys.stderr.write("verify skipped: %s\n" % e)
    return {"id": c.get("id"), "cand": {
        "name": c.get("label") or c.get("id"), "resume": c.get("resume") or None,
        "profile": tri.get("profile"), "ruler": tri.get("ruler"),
        "strengths": tri.get("strengths"), "flags": tri.get("flags"),
        "opener": tri.get("opener"), "cards": cards, "probes": probes,
        "_factcheck": factcheck}}


DEFAULT_TITLE = {"zh": "对抗性技术面试", "en": "Adversarial Technical Interview"}
CAND_WORD = {"zh": "候选人", "en": "Candidate "}


def build_candidates_from_resumes(items, lang):
    word = CAND_WORD.get(lang, CAND_WORD["en"])
    cands = []
    for i, it in enumerate(items):
        cands.append({"id": chr(65 + i), "label": "%s%s · %s" % (word, chr(65 + i), it.get("file", "")),
                      "role_hint": "", "resume": it.get("file"), "resume_text": it.get("text", "")})
    return cands


def resolve_lang(explicit, meta, text):
    """显式 --lang / meta.lang（非 auto）优先，否则按简历正文自动判定。"""
    for cand in (explicit, meta.get("lang")):
        c = str(cand or "").lower()
        if c and c != "auto":
            return c
    return detect_lang(text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", help="analyze.js 同构 args.json（{meta,candidates}）")
    ap.add_argument("--resumes", help="extract_pdf.py 产出的 resumes.json（自动编排候选人）")
    ap.add_argument("--out", required=True, help="输出 payload.json 路径")
    ap.add_argument("--meta", help="可选 meta.json")
    ap.add_argument("--title", default="")
    ap.add_argument("--date", default="")
    ap.add_argument("--lang", default="auto",
                    help="输出语言 zh|en|<ISO>|auto（缺省 auto：按简历正文自动判定，使产物语言与输入一致）")
    ap.add_argument("--minutes", type=int, default=60,
                    help="面试时长（分钟，缺省 60）：决定核心题数量与拷问深度，短则少而聚焦、长则多而细")
    ap.add_argument("--depth", default="", choices=["", "quick", "standard", "deep", "ultra"],
                    help="显式指定深度档位（覆盖 --minutes 推导）。ultra=全面审查：不限时、穷尽简历所有疑点")
    ap.add_argument("--single", action="store_true", help="单调回退：一次调用产出全部")
    ap.add_argument("--ncore", type=int, default=0, help="显式指定核心题数量（覆盖 --minutes 推导出的数量）")
    a = ap.parse_args()

    meta, cands, items = {}, [], None
    if a.inp:
        obj = json.load(open(a.inp, encoding="utf-8"))
        meta, cands = obj.get("meta", {}), obj.get("candidates", [])
    elif a.resumes:
        items = json.load(open(a.resumes, encoding="utf-8"))
    else:
        ap.error("需要 --in 或 --resumes 之一")
    if a.meta:
        meta = json.load(open(a.meta, encoding="utf-8"))

    sample = "\n".join((c.get("resume_text") or "") for c in cands) if cands \
        else "\n".join((it.get("text") or "") for it in (items or []))
    lang = resolve_lang(a.lang, meta, sample)
    if items is not None:
        cands = build_candidates_from_resumes(items, lang)

    plan = plan_for(meta.get("minutes") or a.minutes, a.depth or meta.get("depth"))
    ncore = a.ncore or plan["nCore"] or 0     # explicit --ncore wins; 0 = 由疑点数量决定（ultra）
    plan["nCore"] = ncore or None

    meta.setdefault("title", a.title or DEFAULT_TITLE.get(lang, DEFAULT_TITLE["en"]))
    if a.date:
        meta["date"] = a.date
    meta["lang"] = lang
    meta["plan"] = plan

    scope = "ultra/self-check, exhaustive" if plan["depth"] == "ultra" \
        else "%dmin, %d questions, %s" % (plan["minutes"], ncore, plan["depth"])
    out = {}
    for c in cands:
        sys.stderr.write("analyzing %s (lang=%s, %s) ...\n" % (c.get("label") or c.get("id"), lang, scope))
        r = analyze_one(c, ncore, a.single, lang, plan)
        out[r["id"]] = r["cand"]

    payload = {"meta": meta, "candidates": out}
    with open(a.out, "wb") as f:
        f.write(json.dumps(payload, ensure_ascii=False, indent=1).encode("utf-8"))
    sys.stderr.write("wrote %s (%d candidate(s))\n" % (a.out, len(out)))


if __name__ == "__main__":
    main()
