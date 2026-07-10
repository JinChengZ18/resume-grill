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

面试时长:
  --minutes N（缺省 60）决定核心题数量与拷问深度：30 分钟 → 少而聚焦（阶梯 1 级、答案键写精）；
  60 分钟 → 6 道常规；90+ 分钟 → 更多题、更细的答案键与更多技术域。--ncore 可显式覆盖题数。

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
ROLE_BASE = (
    "你是一线科技公司的资深技术面试官，风格严苛、对简历注水极度敏感。你深知简历常见把戏："
    "大量“参与”其实贡献极小；百分比指标（“节省65%”“提升28%”）常无严谨基线；课程/短期项目包装成“系统”；"
    "术语背后是调库还是真懂原理需要戳穿。提问必须具体、扎进底层实现（数据结构/阈值/失败模式/评估口径/为何这么选），"
    "能区分“真做过”与“只会写在简历上”。同时你也是公正的评估者：在戳穿注水的同时，如实识别候选人真实、可验证的强项与亮点"
    "——扎实的技术深度、真实的 ownership、诚实的自我降级都算加分项。不为对抗而对抗：候选人确实强就大方肯定，"
    "确实弱也不硬挑刺、不为凑数编造红旗；据实评价，不强求优缺点对称、不面面俱到。"
)


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
DEPTHS = {
    "quick": {"rungs": 1, "good": "4-5", "pass": "2-3", "probes": "4-6", "domains": "3-4",
              "note": "时间紧：题目更聚焦，直取能一击验伪的关键点，不求穷尽；暖场阶梯只留 1 级，答案键写精不写多。"},
    "standard": {"rungs": 2, "good": "5-8", "pass": "3-5", "probes": "10-14", "domains": "4-6",
                 "note": "常规时长：每题 2 级暖场阶梯 + 硬核验伪，答案键覆盖机制/阈值/取舍。"},
    "deep": {"rungs": 2, "good": "7-10", "pass": "4-6", "probes": "14-18", "domains": "6-8",
             "note": "时间充裕：问得更细——答案键给更多机制/阈值/取舍分点，追问要能再往下压一层，覆盖更多技术域。"},
}


def _round_half_up(x):
    """匹配 JS Math.round（正数四舍五入）；Python 内置 round() 是银行家舍入，会与 analyze.js 分叉。"""
    return int(math.floor(x + 0.5))


TIER = {"quick": (4, 5), "standard": (5, 7), "deep": (6, 9)}   # (opener, buffer) 分钟


def plan_for(minutes):
    m = max(10, min(240, int(minutes or 60)))
    depth = "quick" if m < 40 else ("deep" if m >= 85 else "standard")
    opener, buffer = TIER[depth]
    per_q = 8                                # 60min → 5 + 6×8 + 7 → nCore 6（沿用既有默认）
    core = max(m - opener - buffer, per_q)
    n = max(2, min(12, _round_half_up(core / per_q)))
    # floor so opener + nCore×perQuestion + buffer never overruns the slot
    return {"minutes": m, "opener": opener, "buffer": buffer, "depth": depth, "nCore": n,
            "perQuestion": max(4, int(math.floor(core / n)))}


def pacing_text(plan, ncore):
    return ("本场面试约 %d 分钟：开场约 %d 分钟，%d 道核心题每题约 %d 分钟，留约 %d 分钟收尾。%s"
            % (plan["minutes"], plan["opener"], ncore, plan["perQuestion"], plan["buffer"],
               DEPTHS[plan["depth"]]["note"]))

# ---- schemas (镜像 analyze.js / pipeline-spec.md) ----
TRIAGE = {
    "type": "object", "additionalProperties": False,
    "required": ["profile", "ruler", "strengths", "flags", "opener", "domains"],
    "properties": {
        "profile": {"type": "string"}, "ruler": {"type": "string"},
        "strengths": {"type": "array", "items": {"type": "string"}},
        "flags": {"type": "array", "items": {"type": "string"}},
        "opener": {"type": "object", "additionalProperties": False,
                   "required": ["title", "questions", "expect", "tell"],
                   "properties": {"title": {"type": "string"},
                                  "questions": {"type": "array", "items": {"type": "string"}},
                                  "expect": {"type": "string"}, "tell": {"type": "string"}}},
        "domains": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                    "required": ["key", "focus"],
                    "properties": {"key": {"type": "string"}, "focus": {"type": "string"}}}},
    },
}
PROBE = {
    "type": "object", "additionalProperties": False, "required": ["domain", "questions"],
    "properties": {"domain": {"type": "string"},
        "questions": {"type": "array", "items": {"type": "object", "additionalProperties": False,
            "required": ["q", "probes", "strong", "tell"],
            "properties": {"q": {"type": "string"}, "probes": {"type": "string"},
                           "strong": {"type": "string"}, "tell": {"type": "string"},
                           "followup": {"type": "string"}}}}},
}
CARD = {
    "type": "object", "additionalProperties": False,
    "required": ["n", "title", "anchor", "ladder", "ask", "good", "pass", "tell", "probe"],
    "properties": {
        "n": {"type": "string"}, "title": {"type": "string"}, "anchor": {"type": "string"},
        "ladder": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                   "required": ["level", "q"],
                   "properties": {"level": {"type": "string"}, "q": {"type": "string"}}}},
        "ask": {"type": "string"},
        "good": {"type": "array", "items": {"type": "string"}},
        "pass": {"type": "array", "items": {"type": "string"}},
        "tell": {"type": "string"}, "probe": {"type": "string"}},
}
AUTHOR = {
    "type": "object", "additionalProperties": False, "required": ["cards", "probes"],
    "properties": {"cards": {"type": "array", "items": CARD},
        "probes": {"type": "array", "items": {"type": "object", "additionalProperties": False,
            "required": ["tag", "q"], "properties": {"tag": {"type": "string"}, "q": {"type": "string"}}}}},
}
VERIFY = {
    "type": "object", "additionalProperties": False, "required": ["corrections", "verdict"],
    "properties": {"corrections": {"type": "array", "items": {"type": "object", "additionalProperties": False,
        "required": ["n", "severity", "issue", "fix"],
        "properties": {"n": {"type": "string"},
                       "severity": {"type": "string", "enum": ["error", "imprecise", "overclaim", "missing"]},
                       "issue": {"type": "string"}, "fix": {"type": "string"}}}},
        "verdict": {"type": "string"}},
}
REVISE = {"type": "object", "additionalProperties": False, "required": ["cards"],
          "properties": {"cards": {"type": "array", "items": CARD}}}
SINGLE = {
    "type": "object", "additionalProperties": False,
    "required": ["profile", "ruler", "strengths", "flags", "opener", "cards", "probes"],
    "properties": {k: TRIAGE["properties"][k] for k in ("profile", "ruler", "strengths", "flags", "opener")},
}
SINGLE["properties"]["cards"] = AUTHOR["properties"]["cards"]
SINGLE["properties"]["probes"] = AUTHOR["properties"]["probes"]


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

def p_triage(rb, plan, dep, ncore):
    return (rb + "\n\n" + pacing_text(plan, ncore) +
            "\n\n任务：通读简历做面试前研判。给出：画像+可信度（均衡如实）、该用的标尺、"
            "真实可验证的强项/亮点（有几条写几条、乏善可陈不硬凑）、关键红旗（注水多就多列、干净就少列，不硬凑）、"
            "一组开场态度/事实题（时间线/可展示性/ownership，控制在约%d分钟内问完），以及%s个最值得对抗性拷问的技术域"
            "（贴合其真实项目，每域列出该戳的实现细节/失败模式）。既要戳穿注水，也要如实肯定真本事，不强求优缺点对称。"
            % (plan["opener"], dep["domains"]))

def p_probe(rb, d):
    return (rb + "\n\n只聚焦这一个技术域做对抗性拷问：【%s】\n重点覆盖：%s\n"
            "产出5-8个由浅入深、层层设套的问题（每题：验证什么/真做过怎么答/只堆术语怎么露馅/一个逼底层的追问），"
            "具体到实现层，不要泛泛而谈。" % (d.get("key", ""), d.get("focus", "")))

def _ladder_spec(dep):
    if dep["rungs"] == 1:
        return ("②时间紧，暖场阶梯（ladder）只给恰好1级：直接问该简历项目的关键设计决策/为什么这么选，"
                "省去泛泛的项目概览")
    return ("②做好提问分层，给一个恰好2级的暖场阶梯（ladder）——L1 从该简历项目切入的概览/general 问题"
            "（先让候选人自己讲，既给他展开空间也给你观察点与切入口），L2 关键设计决策/为什么这么选")


def p_author(rb, tri, probes, n, plan, dep):
    bank = json.dumps({"triage": {"flags": tri.get("flags"), "domains": tri.get("domains")}, "probes": probes},
                      ensure_ascii=False, indent=1)
    return (rb + "\n\n" + pacing_text(plan, n) + "\n\n以下是分域拷问的问题库（JSON）：\n" + bank +
            "\n\n作为首席面试官，按上面的时长与深度要求，收敛出恰好%d道“核心验伪题”（题号Q1..Q%d）——最能区分“真做过”"
            "与“只会写简历”、且无法靠背术语蒙混的题；每题现场约%d分钟问完（含阶梯与追问），题目的粒度要与这个时间预算相称。"
            "每道题都要：①挂靠到一个具体简历项目/宣称（anchor）；%s；ask 则落到实现层、"
            "无法靠背术语蒙混的 L3 硬核验伪。此外每道给：期望的优质回答（%s个分点、技术准确、含机制/阈值/取舍）、"
            "及格线（必须听到的%s点）、典型露馅、追问。另把其余有价值的问题去重整理为%s条“补充探针”（每条带主题标签）。"
            % (n, n, plan["perQuestion"], _ladder_spec(dep), dep["good"], dep["pass"], dep["probes"]))


def p_single(rb, n, plan, dep):
    ladder = ("恰好1级暖场阶梯（ladder：关键设计决策）" if dep["rungs"] == 1
              else "2级暖场阶梯（ladder：L1 项目切入/general、L2 设计决策）")
    return (rb + "\n\n" + pacing_text(plan, n) +
            "\n\n任务：一次性完成面试前研判与核心题设计，直接给出："
            "画像+可信度（均衡如实）、标尺、真实强项/亮点（乏善可陈不硬凑）、关键红旗（不硬凑）、"
            "开场态度/事实题、以及恰好%d道核心验伪题（每题现场约%d分钟）。每道核心题：挂靠简历项目（anchor）+%s"
            "+ ask（L3 硬核验伪）+ 期望优质回答（%s分点）+ 及格线（%s条）+ 典型露馅 + 追问。"
            "再给%s条补充探针（每条带主题标签）。"
            "既戳穿注水也如实肯定真本事，不强求优缺点对称。"
            % (n, plan["perQuestion"], ladder, dep["good"], dep["pass"], dep["probes"]))

def p_verify(cards):
    return ("你是横跨AI基础设施/RAG/多Agent/建模/系统的资深技术专家，对下面这份面试“标准答案(answer key)”做对抗式事实核查。"
            "逐条检查 good 与 pass 是否有：技术性错误、不精确、夸大（把课程/理论说成工业标准）、关键遗漏。只报真正的问题，准确的不要报。"
            "\n\n答案(JSON)：\n" + json.dumps(cards, ensure_ascii=False, indent=1))

def p_revise(cards, corrections):
    return ("下面是核心验伪题的答案键(JSON)与事实核查发现的问题(JSON)。请按核查意见修正 good/pass 中的错误/不精确/夸大/遗漏，"
            "保持题目与结构不变、其余内容不动，返回修正后的完整卡片数组。\n\n卡片：\n"
            + json.dumps(cards, ensure_ascii=False, indent=1) + "\n\n核查：\n"
            + json.dumps(corrections, ensure_ascii=False, indent=1))


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
                "你是横跨AI基础设施/RAG/多Agent/建模/系统的资深技术专家，做对抗式事实核查。\n\n【输出语言】"
                + directive(lang),
                p_verify(cards), VERIFY)
            factcheck = ver.get("verdict")
            if ver.get("corrections"):
                rev = call_llm(role, p_revise(cards, ver["corrections"]), REVISE)
                if rev.get("cards"):
                    cards = rev["cards"]
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

    plan = plan_for(meta.get("minutes") or a.minutes)
    ncore = a.ncore or plan["nCore"]          # explicit --ncore wins
    plan["nCore"] = ncore

    meta.setdefault("title", a.title or DEFAULT_TITLE.get(lang, DEFAULT_TITLE["en"]))
    if a.date:
        meta["date"] = a.date
    meta["lang"] = lang
    meta["plan"] = plan

    out = {}
    for c in cands:
        sys.stderr.write("analyzing %s (lang=%s, %dmin, %d questions, %s) ...\n"
                         % (c.get("label") or c.get("id"), lang, plan["minutes"], ncore, plan["depth"]))
        r = analyze_one(c, ncore, a.single, lang, plan)
        out[r["id"]] = r["cand"]

    payload = {"meta": meta, "candidates": out}
    with open(a.out, "wb") as f:
        f.write(json.dumps(payload, ensure_ascii=False, indent=1).encode("utf-8"))
    sys.stderr.write("wrote %s (%d candidate(s))\n" % (a.out, len(out)))


if __name__ == "__main__":
    main()
