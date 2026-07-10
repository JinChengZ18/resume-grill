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

接入模型（三选一）:
  1) 环境变量 ADV_LLM_PROVIDER=openai    + OPENAI_API_KEY   (+ ADV_LLM_MODEL, 默认 gpt-4.1)
  2) 环境变量 ADV_LLM_PROVIDER=anthropic + ANTHROPIC_API_KEY(+ ADV_LLM_MODEL, 默认 claude-opus-4-8)
  3) 环境变量 ADV_LLM_PROVIDER=custom    + ADV_LLM_CALL=your_module:your_func
     其中 your_func(system, user, schema)->dict 用你自己的模型返回符合 schema 的 JSON。
"""
import argparse, importlib, json, os, sys

NCORE_DEFAULT = 6
BANNED = "交付、再生、天然、免费、回连、让渡、封顶、能量账、省下、补上、旋钮、喂、健壮、落地"

ROLE = (
    "你是国内一线 AI 公司的资深技术面试官，风格严苛、对简历注水极度敏感。你深知中文简历常见把戏："
    "大量“参与”其实贡献极小；百分比指标（“节省65%”“提升28%”）常无严谨基线；课程/短期项目包装成“系统”；"
    "术语背后是调库还是真懂原理需要戳穿。提问必须具体、扎进底层实现（数据结构/阈值/失败模式/评估口径/为何这么选），"
    "能区分“真做过”与“只会写在简历上”。同时你也是公正的评估者：在戳穿注水的同时，如实识别候选人真实、可验证的强项与亮点"
    "——扎实的技术深度、真实的 ownership、诚实的自我降级都算加分项。不为对抗而对抗：候选人确实强就大方肯定，"
    "确实弱也不硬挑刺、不为凑数编造红旗；据实评价，不强求优缺点对称、不面面俱到。全部用中文；"
    "散文遵循中英文之间不加多余空格、中文用全角标点；不要出现这些词：" + BANNED + "。"
)

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
    spec = os.environ.get("ADV_LLM_CALL", "")
    if ":" not in spec:
        raise RuntimeError("ADV_LLM_PROVIDER=custom 需要 ADV_LLM_CALL=module:function")
    mod, fn = spec.split(":", 1)
    return getattr(importlib.import_module(mod), fn)

def call_llm(system, user, schema):
    """返回符合 schema 的 dict。按 ADV_LLM_PROVIDER 分派；也可整体替换本函数。"""
    provider = os.environ.get("ADV_LLM_PROVIDER", "").lower()
    model = os.environ.get("ADV_LLM_MODEL", "")
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
        "未接入模型。设 ADV_LLM_PROVIDER=openai|anthropic|custom（见文件头），或直接替换 call_llm()。")


# ---- prompts ----
def resume_block(c):
    return ("候选人 %s｜岗位线索：%s\n简历正文：\n---\n%s\n---"
            % (c.get("label") or c.get("id"), c.get("role_hint") or "（未指定）", c.get("resume_text") or ""))

def p_triage(rb):
    return (rb + "\n\n任务：通读简历做面试前研判。给出：画像+可信度（均衡如实）、该用的标尺、"
            "真实可验证的强项/亮点（有几条写几条、乏善可陈不硬凑）、关键红旗（注水多就多列、干净就少列，不硬凑）、"
            "一组开场态度/事实题（时间线/可展示性/ownership），以及4-6个最值得对抗性拷问的技术域"
            "（贴合其真实项目，每域列出该戳的实现细节/失败模式）。既要戳穿注水，也要如实肯定真本事，不强求优缺点对称。")

def p_probe(rb, d):
    return (rb + "\n\n只聚焦这一个技术域做对抗性拷问：【%s】\n重点覆盖：%s\n"
            "产出5-8个由浅入深、层层设套的问题（每题：验证什么/真做过怎么答/只堆术语怎么露馅/一个逼底层的追问），"
            "具体到实现层，不要泛泛而谈。" % (d.get("key", ""), d.get("focus", "")))

def p_author(rb, tri, probes, n):
    bank = json.dumps({"triage": {"flags": tri.get("flags"), "domains": tri.get("domains")}, "probes": probes},
                      ensure_ascii=False, indent=1)
    return (rb + "\n\n以下是分域拷问的问题库（JSON）：\n" + bank +
            "\n\n作为首席面试官，收敛出恰好%d道“核心验伪题”（题号Q1..Q%d）——最能区分“真做过”与“只会写简历”、"
            "且无法靠背术语蒙混的题。每道题都要：①挂靠到一个具体简历项目/宣称（anchor）；②做好提问分层，"
            "给一个恰好2级的暖场阶梯（ladder）——L1 从该简历项目切入的概览/general 问题（先让候选人自己讲，"
            "既给他展开空间也给你观察点与切入口），L2 关键设计决策/为什么这么选；ask 则落到实现层、"
            "无法靠背术语蒙混的 L3 硬核验伪。此外每道给：期望的优质回答（5-8个分点、技术准确、含机制/阈值/取舍）、"
            "及格线（必须听到的3-5点）、典型露馅、追问。另把其余有价值的问题去重整理为“补充探针”（每条带主题标签）。"
            % (n, n))

def p_single(rb, n):
    return (rb + "\n\n任务：一次性完成面试前研判与核心题设计，直接给出："
            "画像+可信度（均衡如实）、标尺、真实强项/亮点（乏善可陈不硬凑）、关键红旗（不硬凑）、"
            "开场态度/事实题、以及恰好%d道核心验伪题。每道核心题：挂靠简历项目（anchor）+2级暖场阶梯"
            "（ladder：L1 项目切入/general、L2 设计决策）+ ask（L3 硬核验伪）+ 期望优质回答（5-8分点）"
            "+ 及格线（3-5条）+ 典型露馅 + 追问。再给补充探针（每条带主题标签）。"
            "既戳穿注水也如实肯定真本事，不强求优缺点对称。" % n)

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
def analyze_one(c, ncore, single):
    rb = resume_block(c)
    if single:
        s = call_llm(ROLE, p_single(rb, ncore), SINGLE)
        cards = s.get("cards", [])
        tri = s
        probes = s.get("probes", [])
    else:
        tri = call_llm(ROLE, p_triage(rb), TRIAGE)
        probes = []
        for d in (tri.get("domains") or []):
            try:
                probes.append(call_llm(ROLE, p_probe(rb, d), PROBE))
            except Exception as e:
                sys.stderr.write("probe failed [%s]: %s\n" % (d.get("key"), e))
        authored = call_llm(ROLE, p_author(rb, tri, probes, ncore), AUTHOR)
        cards = authored.get("cards", [])
        probes = authored.get("probes", [])
    # fact-check + revise
    factcheck = None
    if cards:
        try:
            ver = call_llm(
                "你是横跨AI基础设施/RAG/多Agent/建模/系统的资深技术专家，做对抗式事实核查。全部用中文。",
                p_verify(cards), VERIFY)
            factcheck = ver.get("verdict")
            if ver.get("corrections"):
                rev = call_llm(ROLE, p_revise(cards, ver["corrections"]), REVISE)
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


def build_candidates_from_resumes(items):
    cands = []
    for i, it in enumerate(items):
        cands.append({"id": chr(65 + i), "label": "候选人%s · %s" % (chr(65 + i), it.get("file", "")),
                      "role_hint": "", "resume": it.get("file"), "resume_text": it.get("text", "")})
    return cands


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", help="analyze.js 同构 args.json（{meta,candidates}）")
    ap.add_argument("--resumes", help="extract_pdf.py 产出的 resumes.json（自动编排候选人）")
    ap.add_argument("--out", required=True, help="输出 payload.json 路径")
    ap.add_argument("--meta", help="可选 meta.json")
    ap.add_argument("--title", default="对抗性技术面试")
    ap.add_argument("--date", default="")
    ap.add_argument("--single", action="store_true", help="单调回退：一次调用产出全部")
    ap.add_argument("--ncore", type=int, default=NCORE_DEFAULT)
    a = ap.parse_args()

    meta, cands = {}, []
    if a.inp:
        obj = json.load(open(a.inp, encoding="utf-8"))
        meta, cands = obj.get("meta", {}), obj.get("candidates", [])
    elif a.resumes:
        cands = build_candidates_from_resumes(json.load(open(a.resumes, encoding="utf-8")))
    else:
        ap.error("需要 --in 或 --resumes 之一")
    if a.meta:
        meta = json.load(open(a.meta, encoding="utf-8"))
    meta.setdefault("title", a.title)
    if a.date:
        meta["date"] = a.date
    meta.setdefault("by", "J.C.")

    out = {}
    for c in cands:
        sys.stderr.write("analyzing %s ...\n" % (c.get("label") or c.get("id")))
        r = analyze_one(c, a.ncore, a.single)
        out[r["id"]] = r["cand"]

    payload = {"meta": meta, "candidates": out}
    with open(a.out, "wb") as f:
        f.write(json.dumps(payload, ensure_ascii=False, indent=1).encode("utf-8"))
    sys.stderr.write("wrote %s (%d candidate(s))\n" % (a.out, len(out)))


if __name__ == "__main__":
    main()
