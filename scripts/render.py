#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render.py — turn one analysis payload (JSON) into linked, printable HTML pages:
  <slug>_index.html          batch index linking every page below (always written)
  <slug>_guide.html          full interview guide as a readable page   } written when a
  <slug>_guide.md            the same guide as Markdown source         } candidate has
  <slug>_scorecard.html      one-A4-per-candidate live scoring sheet   } "cards"
  <slug>_qa_cards.html       reading-friendly Q&A attack-defense cards }
  <slug>_weakness.html       weakness analysis      (candidate "weakness")
  <slug>_resume.html         resume optimization    (candidate "resume_opt")
  <slug>_jd.html             job-description match  (candidate "jd_match")
Every page links its siblings with relative hrefs and exports to PDF via the browser's
print dialog. The three extra sections are specified in reference/modes-spec.md and
rendered by pages.py.

Usage:
  python render.py <payload.json> <output_dir> [slug]

payload.json shape:
{
  "meta": {"title":..., "subtitle":..., "date":"YYYY-MM-DD", "by":"J.C.",
           "lang":"zh|en|...", "links":[{"label":..., "href":...}], "footer":...},
  "candidates": {
    "<id>": {
      "name":..., "resume": <relative-href-or-null>, "profile":..., "ruler":...,
      "strengths":[...],   # genuine strengths / highlights (may be empty)
      "flags":[...],
      "opener":{"title":..., "questions":[...], "expect":..., "tell":...},
      "cards":[{"n":"Q1","title":..., "anchor":..., "ladder":[{"level":..., "q":...}],
                "ask":..., "good":[...], "pass":[...], "tell":..., "probe":...}],
      "probes":[{"tag":..., "q":...}]
    }
  }
}

The interface chrome (headers, buttons, scorecard labels) is localized from LABELS by
meta.lang; the model-generated content is already in that language. Unknown langs fall
back to the English chrome. To add a language, add one entry to LABELS.

Writes with UTF-8 + LF endings (Windows-safe). No third-party deps.
"""
import json, sys, os, io, re

import pages
import kit

HERE = os.path.dirname(os.path.abspath(__file__))
TMPL = os.path.join(os.path.dirname(HERE), "templates")
BRAND = "resume-grill"   # delivered pages carry the project name, not an author name

# ---- interface-chrome strings, keyed by language ----
# Bare noun phrases; punctuation (colon/sep) is applied at the use site so both
# full-width (zh) and spaced (en) styles come out right.
LABELS = {
    "zh": {
        "colon": "：", "sep": "｜", "list_sep": "；",
        "sample_answer": "示范回答", "followups_h": "本主题延伸讨论", "when": "选问时机",
        "guide_title": "对抗性技术面试指南",
        "date": "日期", "prep_by": "整理", "interviewer": "面试官",
        "guide_lead": "每题：建议提问 → 期望的优质回答（分点）；追问留在本主题，判分提示单列。题号与评分卡 ★ 一一对应。",
        "profile_h": "画像与可信度", "ruler_h": "标尺",
        "strengths_plain": "亮点 · 真实强项", "flags_plain": "待确认事项",
        "opener_expect": "期望的行为", "opener_tell": "待深入",
        "core_h": "核心验伪题（含答案键；题号对应评分卡 ★）",
        "anchor_h": "挂靠简历项目",
        "ladder_h": "提问阶梯（由浅入深，从简历项目起手）",
        "l3_label": "L3 情境讨论", "ask_label": "建议提问",
        "good_h": "期望的优质回答", "pass_h": "及格线（必须听到）",
        "tell_h": "需进一步了解", "probe_h": "追问",
        "probes_h": "合作安排与材料确认",
        # qa_cards
        "doc_title": "提问-回答攻防卡片",
        "sub_default": "对抗性技术面试 · 建议提问 → 期望的优质回答（分点）；追问留在本主题，判分提示单列",
        "collapse_all": "收起全部答案（自测）", "expand_all": "展开全部答案",
        "ask_k": "建议提问 · L3 情境讨论", "ans_summary": "面试官判分提示",
        "pass_bt": "及格线 · 必须听到",
        "strengths_title": "★ 亮点 · 真实强项", "flags_title": "▲ 待确认事项",
        "opener_badge": "开场", "resume_link": "📄 原始简历",
        "probes_pre": "独立事项（", "probes_post": " 条 · 按需确认）",
        "footer_default": "诚实降级（承认课程demo/没上生产/gold自标）应视为强信号，不扣分。",
        # scorecard
        "scorecard_suffix": "现场评分卡", "scorecard_h1": "现场技术面试评分卡",
        "legend": "打分：强=命中及格线、到实现层；中=方向对但缺细节/只答一半；待深入=停在术语层或明显错误。★为核心验伪题（对应攻防卡片）。",
        "col_q": "题目与判分线索", "col_strong": "强", "col_mid": "中", "col_tell": "待深入",
        "verdict_label": "综合结论", "advance": "进入下一轮", "hold": "待定", "reject": "淘汰",
        "count_label": "强/中/待深入 计数", "sign_label": "签名",
        "print_btn": "🖨 打印 / 导出PDF", "reset_btn": "↺ 重置本页", "score_hint": "点格子打分，自动记忆",
        "duration": "时长", "min_unit": "分钟", "q_unit": "题",
        "opener_word": "开场", "wrap_word": "收尾",
        "audit_mode": "全面审查 · 不限时",
        "audit_lead": "全面审查 · 不限时｜逐一覆盖简历中的全部疑点（亦可用于面试前自我排查）",
        # navigation, PDF export and the batch index
        "export_pdf": "⤓ 导出PDF", "export_pdf_hint": "在打印窗口选择「另存为PDF」",
        "nav_kit": "☑ 面试官手册",
        "desc_kit": "每位候选人一页：面试前速览，面试中逐题提问（要听的点和折叠的示范回答紧跟在题下），面试后按维度打分并生成面评草稿",
        "nav_index": "⌂ 总入口", "nav_guide": "▤ 面试指南", "nav_cards": "☰ 问答卡片",
        "nav_scorecard": "▦ 评分卡", "nav_weakness": "▲ 弱点分析", "nav_resume": "✎ 简历优化", "nav_jd": "◎ JD匹配",
        "index_title": "面试准备材料总入口",
        "index_lead": "以下页面都是可直接打开的本地HTML；每页右上角都可导出PDF。",
        "desc_guide": "完整阅读版：画像、面试主题、逐问示范回答与判分提示",
        "desc_cards": "逐问折叠答案，适合自测和快速翻阅",
        "desc_scorecard": "A4现场评分表，点击打分自动保存",
        "desc_weakness": "按严重程度排列的薄弱点、可能的追问与回答、修改建议",
        "desc_resume": "需要你补充的事实、逐条改前改后对照、可打印的优化版简历",
        "desc_jd": "逐条对照岗位要求、缺口补强计划与可能的面试问题",
        # weakness analysis
        "weakness_title": "简历弱点分析", "sev_high": "高", "sev_medium": "中", "sev_low": "低",
        "actions_h": "优先处理", "keep_h": "保持不变的强项", "items_h": "逐条分析",
        "quote_h": "简历原文", "issue_h": "问题", "why_h": "面试官会怎样理解", "fu_h": "可能的追问",
        "fix_h": "怎么改", "rewrite_h": "改写示例",
        # resume optimization
        "resume_title": "简历优化", "questions_h": "需要你补充的事实",
        "questions_lead": "在对话里回答这些问题后，占位符会替换为你的真实信息，本页随之重新生成。",
        "affects": "影响", "edits_h": "逐条改前改后", "before_h": "改前", "after_h": "改后", "reason_h": "理由",
        "optimized_h": "优化版简历", "export_resume": "⤓ 只导出简历PDF",
        "tbd_left": "还有{n}处待补充（黄色标记），导出前请先确认。",
        # JD match
        "jd_title": "JD匹配分析", "jd_h": "目标岗位", "jd_source_h": "JD来源",
        "status_met": "匹配", "status_partial": "部分匹配", "status_gap": "缺口",
        "prio_must": "必须", "prio_nice": "加分", "req_h": "逐条对照",
        "col_req": "岗位要求", "col_status": "状态", "col_evidence": "简历证据", "col_note": "判断与建议",
        "action_h": "建议", "kw_h": "关键词覆盖", "kw_present": "简历已体现", "kw_missing": "简历未体现",
        "gaps_h": "缺口补强计划", "plan_h": "怎么补强", "talk_h": "面试中怎么说", "jdq_h": "可能的面试问题",
    },
    "en": {
        "colon": ": ", "sep": " · ", "list_sep": "; ",
        "sample_answer": "Sample response", "followups_h": "Follow-ups in this theme", "when": "When to ask",
        "guide_title": "Adversarial Technical Interview Guide",
        "date": "Date", "prep_by": "Prepared by", "interviewer": "Interviewer",
        "guide_lead": "Each question: suggested prompt → strong answer (bulleted) → pass bar → common tell → follow-up. Question numbers map one-to-one to the scorecard ★s.",
        "profile_h": "Profile & Credibility", "ruler_h": "Yardstick",
        "strengths_plain": "Highlights · Genuine Strengths", "flags_plain": "Key Red Flags",
        "opener_expect": "What good looks like", "opener_tell": "Tell",
        "core_h": "Interview themes (numbers map to the scorecard)",
        "anchor_h": "Anchored to résumé project",
        "ladder_h": "Question ladder (shallow → deep, starting from the résumé project)",
        "l3_label": "L3 hard probe", "ask_label": "Suggested prompt",
        "good_h": "Strong answer", "pass_h": "Pass bar (must hear)",
        "tell_h": "Common tell", "probe_h": "Follow-up",
        "probes_h": "Working arrangements and material checks",
        # qa_cards
        "doc_title": "Q&A Attack-Defense Cards",
        "sub_default": "Adversarial technical interview · prompt → strong answer → pass bar → tell → follow-up",
        "collapse_all": "Collapse all answers (self-test)", "expand_all": "Expand all answers",
        "ask_k": "Suggested prompt · L3 hard probe", "ans_summary": "Interviewer scoring cues",
        "pass_bt": "Pass bar · must hear",
        "strengths_title": "★ Highlights · Genuine Strengths", "flags_title": "▲ Key Red Flags",
        "opener_badge": "Opener", "resume_link": "📄 Original résumé",
        "probes_pre": "Separate items (", "probes_post": " · ask when relevant)",
        "footer_default": "Honest self-downgrade (admitting “coursework demo / never shipped / self-labeled gold”) is a strong signal — do not penalize it.",
        # scorecard
        "scorecard_suffix": "Live Scorecard", "scorecard_h1": "Live Technical Interview Scorecard",
        "legend": "Scoring: Strong = hits the pass bar, reaches implementation level; Mid = right direction but missing detail / half-answered; Tell = stuck at buzzword level or clearly wrong. ★ = core kill questions (map to the Q&A cards).",
        "col_q": "Question & scoring cues", "col_strong": "Strong", "col_mid": "Mid", "col_tell": "Tell",
        "verdict_label": "Verdict", "advance": "Advance", "hold": "Hold", "reject": "Reject",
        "count_label": "Strong/Mid/Tell count", "sign_label": "Signature",
        "print_btn": "🖨 Print / Save PDF", "reset_btn": "↺ Reset page", "score_hint": "click a cell to score — saved automatically",
        "duration": "Duration", "min_unit": "min", "q_unit": "",
        "opener_word": "Opener", "wrap_word": "Wrap-up",
        "audit_mode": "Full audit · untimed",
        "audit_lead": "Full audit · untimed — covers every doubt in the résumé (also for pre-interview self-check)",
        # navigation, PDF export and the batch index
        "export_pdf": "⤓ Export PDF", "export_pdf_hint": "Choose “Save as PDF” in the print dialog",
        "nav_kit": "☑ Interviewer kit",
        "desc_kit": "One page per candidate: a briefing before, every question with what to listen for and a folded model answer during, dimension scoring and a review draft after",
        "nav_index": "⌂ Index", "nav_guide": "▤ Interview guide", "nav_cards": "☰ Q&A cards",
        "nav_scorecard": "▦ Scorecard", "nav_weakness": "▲ Weakness analysis", "nav_resume": "✎ Résumé optimization",
        "nav_jd": "◎ JD match",
        "index_title": "Interview Prep Index",
        "index_lead": "Every page below is a self-contained local HTML file; each one exports to PDF from its toolbar.",
        "desc_guide": "Full reading copy: profile, interview themes, model answers and scoring cues",
        "desc_cards": "Collapsible answers for self-testing and quick review",
        "desc_scorecard": "A4 live scoring sheet; clicks are saved automatically",
        "desc_weakness": "Weak points by severity, likely follow-ups with answers, and fixes",
        "desc_resume": "Facts we need from you, before/after rewrites, and a printable optimized résumé",
        "desc_jd": "Requirement-by-requirement match, a plan for the gaps, and likely interview questions",
        # weakness analysis
        "weakness_title": "Résumé Weakness Analysis", "sev_high": "High", "sev_medium": "Medium", "sev_low": "Low",
        "actions_h": "Do these first", "keep_h": "Keep as is", "items_h": "Item by item",
        "quote_h": "On the résumé", "issue_h": "Issue", "why_h": "How an interviewer reads it",
        "fu_h": "Likely follow-ups", "fix_h": "How to fix", "rewrite_h": "Suggested rewrite",
        # resume optimization
        "resume_title": "Résumé Optimization", "questions_h": "Facts we need from you",
        "questions_lead": "Answer these in the chat; the placeholders are replaced with your real facts and this page is regenerated.",
        "affects": "Affects", "edits_h": "Before and after, line by line", "before_h": "Before", "after_h": "After",
        "reason_h": "Why", "optimized_h": "Optimized résumé", "export_resume": "⤓ Export résumé only",
        "tbd_left": "{n} placeholder(s) still need your facts (highlighted); check them before exporting.",
        # JD match
        "jd_title": "Job Description Match", "jd_h": "Target role", "jd_source_h": "Source",
        "status_met": "Met", "status_partial": "Partial", "status_gap": "Gap",
        "prio_must": "Must", "prio_nice": "Nice to have", "req_h": "Requirement by requirement",
        "col_req": "Requirement", "col_status": "Status", "col_evidence": "Résumé evidence",
        "col_note": "Assessment and action", "action_h": "Action", "kw_h": "Keyword coverage",
        "kw_present": "On the résumé", "kw_missing": "Missing", "gaps_h": "Closing the gaps",
        "plan_h": "Plan", "talk_h": "How to talk about it", "jdq_h": "Likely interview questions",
    },
}


def detect_lang(text):
    s = text or ""
    han = len(re.findall(r"[㐀-鿿豈-﫿]", s))
    latin = len(re.findall(r"[A-Za-z]", s))
    if han == 0:
        return "en"
    return "zh" if han / (han + latin + 1) > 0.1 else "en"


def resolve_labels(payload):
    """Pick the chrome language: meta.lang if present, else sniff the content."""
    meta = payload.get("meta", {})
    lang = str(meta.get("lang") or "").lower()
    if lang not in LABELS:
        if not lang:
            sample = []
            for d in payload.get("candidates", {}).values():
                sample.append(d.get("profile") or "")
                for c in (d.get("cards") or [])[:1]:
                    sample.append(c.get("title") or "")
            lang = detect_lang("\n".join(sample))
        lang = lang if lang in LABELS else "en"
    return lang, LABELS[lang]


def wfile(path, text):
    # binary write with explicit LF to avoid CRLF churn on Windows
    with open(path, "wb") as f:
        f.write(text.replace("\r\n", "\n").encode("utf-8"))


def inject(tmpl_name, payload, title, L):
    with io.open(os.path.join(TMPL, tmpl_name), encoding="utf-8") as f:
        t = f.read()
    for placeholder, obj in (("/*__PAYLOAD__*/{}", payload), ("/*__LABELS__*/{}", L)):
        data = json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")  # keep </script> intact
        t = t.replace(placeholder, data)
    t = t.replace("__TITLE__", title)
    return t


def pacing_line(L, plan):
    """一句话时间预算：时长｜开场 + N题 × 每题 + 收尾。"""
    co, sep = L["colon"], L["sep"]
    n, pq = plan.get("nCore"), plan.get("perQuestion")
    return (f"{L['duration']}{co}{plan.get('minutes')} {L['min_unit']}{sep}"
            f"{L['opener_word']} {plan.get('opener')}′ + {n}{L['q_unit']} × {pq}′"
            f" + {L['wrap_word']} {plan.get('buffer')}′")


def md_guide(payload, L):
    m = payload.get("meta", {})
    co, sep = L["colon"], L["sep"]
    out = []
    out.append(f"# {m.get('title', L['guide_title'])}\n")
    if m.get("subtitle"): out.append(f"> {m['subtitle']}")
    if m.get("date"):     out.append(f"> {L['date']}{co}{m['date']}{sep}{BRAND}")
    plan = m.get("plan") or {}
    if plan.get("depth") == "ultra":
        out.append(f"> {L['audit_lead']}")
    elif plan.get("minutes") and plan.get("nCore") and plan.get("perQuestion"):
        out.append(f"> {pacing_line(L, plan)}")
    out.append(f"> {L['guide_lead']}\n")
    for cid, d in payload.get("candidates", {}).items():
        out.append(f"---\n\n# {d.get('name', cid)}\n")
        if d.get("profile"): out.append(f"## {L['profile_h']}\n\n{d['profile']}\n")
        if d.get("ruler"):   out.append(f"> **{L['ruler_h']}**{co}{d['ruler']}\n")
        if d.get("strengths"):
            out.append(f"## {L['strengths_plain']}\n")
            for i, s in enumerate(d["strengths"], 1): out.append(f"{i}. {s}")
            out.append("")
        if d.get("flags"):
            out.append(f"## {L['flags_plain']}\n")
            for i, f in enumerate(d["flags"], 1): out.append(f"{i}. {f}")
            out.append("")
        o = d.get("opener") or {}
        if o.get("title"):
            out.append(f"## {o['title']}\n")
            for q in o.get("questions", []): out.append(f"- {q}")
            out.append("")
            if o.get("expect"): out.append(f"**{L['opener_expect']}**{co}{o['expect']}")
            if o.get("tell"):   out.append(f"**{L['opener_tell']}**{co}{o['tell']}\n")
        out.append(f"## {L['core_h']}\n")
        for c in d.get("cards", []):
            out.append(f"### {c.get('n','')} · {c.get('title','')}\n")
            if c.get("anchor"): out.append(f"> {L['anchor_h']}{co}{c['anchor']}\n")
            if c.get("ladder"):
                out.append(f"**{L['ladder_h']}**\n")
                for step in c["ladder"]:
                    out.append(f"- *{step.get('level','')}*{co}{step.get('q','')}")
                    if step.get("answer"):
                        out.append(f"\n**{L['sample_answer']}**{co}{step['answer']}\n")
                out.append(f"- *{L['l3_label']}*{co}{c.get('ask','')}\n")
            else:
                out.append(f"**{L['ask_label']}**{co}{c.get('ask','')}\n")
            if c.get("ask_answer"):
                out.append(f"**{L['sample_answer']}**{co}{c['ask_answer']}\n")
            else:
                out.append(f"**{L['good_h']}**\n")
                for g in c.get("good", []): out.append(f"- {g}")
            if c.get("probe"):
                out.append(f"**{L['probe_h']}**{co}{c['probe']}\n")
                if c.get("probe_answer"):
                    out.append(f"**{L['sample_answer']}**{co}{c['probe_answer']}\n")
            if c.get("followups"):
                out.append(f"#### {L['followups_h']}\n")
                for f in c["followups"]:
                    if f.get("when"): out.append(f"*{L['when']}*{co}{f['when']}\n")
                    out.append(f"**{L['ask_label']}**{co}{f.get('q','')}\n")
                    out.append(f"**{L['sample_answer']}**{co}{f.get('answer','')}\n")
            out.append(f"\n**{L['pass_h']}**\n")
            for p in c.get("pass", []): out.append(f"- {p}")
            out.append(f"\n**{L['tell_h']}**{co}{c.get('tell','')}\n")
        if d.get("probes"):
            out.append(f"## {L['probes_h']}\n")
            for p in d["probes"]:
                out.append(f"- **{p.get('tag','')}**{co}{p.get('q','')}")
                if p.get("answer"): out.append(f"\n**{L['sample_answer']}**{co}{p['answer']}\n")
            out.append("")
    return "\n".join(out) + "\n"


# kind, file suffix, nav label key, index description key, candidate field the page needs
ARTIFACTS = (
    ("index",     "_index.html",     "nav_index",     None,             None),
    ("guide",     "_guide.html",     "nav_guide",     "desc_guide",     "cards"),
    ("cards",     "_qa_cards.html",  "nav_cards",     "desc_cards",     "cards"),
    ("scorecard", "_scorecard.html", "nav_scorecard", "desc_scorecard", "cards"),
    ("weakness",  "_weakness.html",  "nav_weakness",  "desc_weakness",  "weakness"),
    ("resume",    "_resume.html",    "nav_resume",    "desc_resume",    "resume_opt"),
    ("jd",        "_jd.html",        "nav_jd",        "desc_jd",        "jd_match"),
)


def plan_leads(payload, L):
    """Date / pacing / reading notes shown at the top of the guide."""
    m = payload.get("meta", {})
    leads = []
    if m.get("date"):
        leads.append(f"{L['date']}{L['colon']}{m['date']}{L['sep']}{BRAND}")
    plan = m.get("plan") or {}
    if plan.get("depth") == "ultra":
        leads.append(L["audit_lead"])
    elif plan.get("minutes") and plan.get("nCore") and plan.get("perQuestion"):
        leads.append(pacing_line(L, plan))
    leads.append(L["guide_lead"])
    return leads


LEGACY_VIEWS = ("guide", "cards", "scorecard")


def render_all(payload, outdir, slug):
    """Write every page the payload supports; return (lang, written paths, index first).

    Grilling content (cards) renders as one self-contained interviewer kit per candidate
    (`<slug>_kit_<id>.html`) plus `<slug>_guide.md` as a plain-text archive. The older guide,
    Q&A cards and scorecard pages are written only when meta.views asks for them."""
    os.makedirs(outdir, exist_ok=True)
    lang, L = resolve_labels(payload)
    meta = payload.get("meta", {})
    cands = payload.get("candidates", {})
    title = meta.get("title") or L["guide_title"]
    views = set(meta.get("views") or ())

    present = [a for a in ARTIFACTS
               if (a[4] is None or any(d.get(a[4]) for d in cands.values()))
               and (a[0] not in LEGACY_VIEWS or a[0] in views)]
    artifacts = [dict(kind=k, href=slug + suf, label=L[lk], desc=L[dk] if dk else "", key=key)
                 for k, suf, lk, dk, key in present]
    kit_hrefs = {cid: kit.kit_filename(slug, cid) for cid, d in cands.items() if d.get("cards")}
    if kit_hrefs:
        artifacts.insert(1, dict(kind="kit", href=next(iter(kit_hrefs.values())), href_by_cid=kit_hrefs,
                                 label=L["nav_kit"], desc=L["desc_kit"], key="cards"))
    # Hand-written links to our own pages (any slug) are superseded by the generated nav.
    own_suffixes = tuple(a[1] for a in ARTIFACTS) + ("_guide.md",)
    extra = [l for l in (meta.get("links") or []) if not str(l.get("href", "")).endswith(own_suffixes)
             and "_kit_" not in str(l.get("href", ""))]

    def nav(kind):
        return [dict(label=a["label"], href=a["href"]) for a in artifacts
                if a["kind"] not in (kind, "kit")] + extra

    def with_meta(**kw):
        p = dict(payload)
        p["meta"] = dict(meta, **kw)
        return p

    written = []

    def put(kind, text):
        path = os.path.join(outdir, slug + dict((a[0], a[1]) for a in ARTIFACTS)[kind])
        wfile(path, text)
        written.append(path)

    kinds = {a["kind"] for a in artifacts}
    put("index", pages.index_page(payload, L, lang, nav("index"), artifacts))
    for cid, href in kit_hrefs.items():
        path = os.path.join(outdir, href)
        wfile(path, kit.kit_page(payload, cid, cands[cid], lang, slug, outdir))
        written.append(path)
    if kit_hrefs:
        md_path = os.path.join(outdir, f"{slug}_guide.md")
        wfile(md_path, md_guide(payload, L))
        written.append(md_path)
    if "guide" in kinds:
        put("guide", pages.guide_page(payload, L, lang, nav("guide"), plan_leads(payload, L)))
    if "cards" in kinds:
        put("cards", inject("qa_cards.html.tmpl", with_meta(links=nav("cards")), title, L))
    if "scorecard" in kinds:
        put("scorecard", inject("scorecard.html.tmpl", with_meta(_index=slug + "_index.html"), title, L))
    if "weakness" in kinds:
        put("weakness", pages.weakness_page(payload, L, lang, nav("weakness")))
    if "resume" in kinds:
        put("resume", pages.resume_page(payload, L, lang, nav("resume")))
    if "jd" in kinds:
        put("jd", pages.jd_page(payload, L, lang, nav("jd")))
    return lang, written


def main():
    if len(sys.argv) < 3:
        print("usage: python render.py <payload.json> <output_dir> [slug]"); sys.exit(1)
    payload_path, outdir = sys.argv[1], sys.argv[2]
    slug = sys.argv[3] if len(sys.argv) > 3 else "interview"
    with io.open(payload_path, encoding="utf-8") as f:
        payload = json.load(f)
    lang, written = render_all(payload, outdir, slug)
    print("wrote (lang=%s):" % lang)
    for path in written:
        print("  " + os.path.abspath(path))

if __name__ == "__main__":
    main()
