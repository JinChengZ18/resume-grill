#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render.py — turn one analysis payload (JSON) into the three interview deliverables:
  <slug>_guide.md            full adversarial guide (prose + bulleted answer keys)
  <slug>_scorecard.html      one-A4-per-candidate live scoring sheet
  <slug>_qa_cards.html       reading-friendly Q&A attack-defense cards

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

HERE = os.path.dirname(os.path.abspath(__file__))
TMPL = os.path.join(os.path.dirname(HERE), "templates")
BRAND = "resume-grill"   # delivered pages carry the project name, not an author name

# ---- interface-chrome strings, keyed by language ----
# Bare noun phrases; punctuation (colon/sep) is applied at the use site so both
# full-width (zh) and spaced (en) styles come out right.
LABELS = {
    "zh": {
        "colon": "：", "sep": "｜", "list_sep": "；",
        "guide_title": "对抗性技术面试指南",
        "date": "日期", "prep_by": "整理", "interviewer": "面试官",
        "guide_lead": "每题：建议提问 → 期望的优质回答（分点）→ 及格线 → 典型露馅 → 追问。题号与评分卡 ★ 一一对应。",
        "profile_h": "画像与可信度", "ruler_h": "标尺",
        "strengths_plain": "亮点 · 真实强项", "flags_plain": "关键红旗",
        "opener_expect": "期望的行为", "opener_tell": "露馅",
        "core_h": "核心验伪题（含答案键；题号对应评分卡 ★）",
        "anchor_h": "挂靠简历项目",
        "ladder_h": "提问阶梯（由浅入深，从简历项目起手）",
        "l3_label": "L3 硬核验伪", "ask_label": "建议提问",
        "good_h": "期望的优质回答", "pass_h": "及格线（必须听到）",
        "tell_h": "典型露馅", "probe_h": "追问",
        "probes_h": "补充探针（无标准答案，答顺后继续加压）",
        # qa_cards
        "doc_title": "提问-回答攻防卡片",
        "sub_default": "对抗性技术面试 · 建议提问 → 期望的优质回答（分点）→ 及格线 → 典型露馅 → 追问",
        "collapse_all": "收起全部答案（自测）", "expand_all": "展开全部答案",
        "ask_k": "建议提问 · L3 硬核验伪", "ans_summary": "参考答案与判分要点",
        "pass_bt": "及格线 · 必须听到",
        "strengths_title": "★ 亮点 · 真实强项", "flags_title": "▲ 关键红旗",
        "opener_badge": "开场", "resume_link": "📄 原始简历 PDF",
        "probes_pre": "补充探针（", "probes_post": " 条 · 无标准答案，答顺后继续加压）",
        "footer_default": "诚实降级（承认课程demo/没上生产/gold自标）应视为强信号，不扣分。",
        # scorecard
        "scorecard_suffix": "现场评分卡", "scorecard_h1": "现场技术面试评分卡",
        "legend": "打分：强=命中及格线、到实现层；中=方向对但缺细节/只答一半；露馅=停在术语层或明显错误。★为核心验伪题（对应攻防卡片）。",
        "col_q": "题目与判分线索", "col_strong": "强", "col_mid": "中", "col_tell": "露馅",
        "verdict_label": "综合结论", "advance": "进入下一轮", "hold": "待定", "reject": "淘汰",
        "count_label": "强/中/露馅 计数", "sign_label": "签名",
        "print_btn": "🖨 打印", "reset_btn": "↺ 重置本页", "score_hint": "点格子打分，自动记忆",
        "duration": "时长", "min_unit": "分钟", "q_unit": "题",
        "opener_word": "开场", "wrap_word": "收尾",
    },
    "en": {
        "colon": ": ", "sep": " · ", "list_sep": "; ",
        "guide_title": "Adversarial Technical Interview Guide",
        "date": "Date", "prep_by": "Prepared by", "interviewer": "Interviewer",
        "guide_lead": "Each question: suggested prompt → strong answer (bulleted) → pass bar → common tell → follow-up. Question numbers map one-to-one to the scorecard ★s.",
        "profile_h": "Profile & Credibility", "ruler_h": "Yardstick",
        "strengths_plain": "Highlights · Genuine Strengths", "flags_plain": "Key Red Flags",
        "opener_expect": "What good looks like", "opener_tell": "Tell",
        "core_h": "Core Kill Questions (with answer keys; numbers map to the scorecard ★s)",
        "anchor_h": "Anchored to résumé project",
        "ladder_h": "Question ladder (shallow → deep, starting from the résumé project)",
        "l3_label": "L3 hard probe", "ask_label": "Suggested prompt",
        "good_h": "Strong answer", "pass_h": "Pass bar (must hear)",
        "tell_h": "Common tell", "probe_h": "Follow-up",
        "probes_h": "Extra probes (no fixed answer; press further if they cruise)",
        # qa_cards
        "doc_title": "Q&A Attack-Defense Cards",
        "sub_default": "Adversarial technical interview · prompt → strong answer → pass bar → tell → follow-up",
        "collapse_all": "Collapse all answers (self-test)", "expand_all": "Expand all answers",
        "ask_k": "Suggested prompt · L3 hard probe", "ans_summary": "Answer key & scoring cues",
        "pass_bt": "Pass bar · must hear",
        "strengths_title": "★ Highlights · Genuine Strengths", "flags_title": "▲ Key Red Flags",
        "opener_badge": "Opener", "resume_link": "📄 Original résumé PDF",
        "probes_pre": "Extra probes (", "probes_post": " · no fixed answer; press further if they cruise)",
        "footer_default": "Honest self-downgrade (admitting “coursework demo / never shipped / self-labeled gold”) is a strong signal — do not penalize it.",
        # scorecard
        "scorecard_suffix": "Live Scorecard", "scorecard_h1": "Live Technical Interview Scorecard",
        "legend": "Scoring: Strong = hits the pass bar, reaches implementation level; Mid = right direction but missing detail / half-answered; Tell = stuck at buzzword level or clearly wrong. ★ = core kill questions (map to the Q&A cards).",
        "col_q": "Question & scoring cues", "col_strong": "Strong", "col_mid": "Mid", "col_tell": "Tell",
        "verdict_label": "Verdict", "advance": "Advance", "hold": "Hold", "reject": "Reject",
        "count_label": "Strong/Mid/Tell count", "sign_label": "Signature",
        "print_btn": "🖨 Print", "reset_btn": "↺ Reset page", "score_hint": "click a cell to score — saved automatically",
        "duration": "Duration", "min_unit": "min", "q_unit": "",
        "opener_word": "Opener", "wrap_word": "Wrap-up",
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
    if m.get("plan"):     out.append(f"> {pacing_line(L, m['plan'])}")
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
                out.append(f"- *{L['l3_label']}*{co}{c.get('ask','')}\n")
            else:
                out.append(f"**{L['ask_label']}**{co}{c.get('ask','')}\n")
            out.append(f"**{L['good_h']}**\n")
            for g in c.get("good", []): out.append(f"- {g}")
            out.append(f"\n**{L['pass_h']}**\n")
            for p in c.get("pass", []): out.append(f"- {p}")
            out.append(f"\n**{L['tell_h']}**{co}{c.get('tell','')}\n")
            out.append(f"**{L['probe_h']}**{co}{c.get('probe','')}\n")
        if d.get("probes"):
            out.append(f"## {L['probes_h']}\n")
            for p in d["probes"]: out.append(f"- **{p.get('tag','')}**{co}{p.get('q','')}")
            out.append("")
    return "\n".join(out) + "\n"


def main():
    if len(sys.argv) < 3:
        print("usage: python render.py <payload.json> <output_dir> [slug]"); sys.exit(1)
    payload_path, outdir = sys.argv[1], sys.argv[2]
    slug = sys.argv[3] if len(sys.argv) > 3 else "interview"
    with io.open(payload_path, encoding="utf-8") as f:
        payload = json.load(f)
    os.makedirs(outdir, exist_ok=True)
    lang, L = resolve_labels(payload)
    title = payload.get("meta", {}).get("title") or L["guide_title"]

    wfile(os.path.join(outdir, f"{slug}_qa_cards.html"),  inject("qa_cards.html.tmpl",  payload, title, L))
    wfile(os.path.join(outdir, f"{slug}_scorecard.html"), inject("scorecard.html.tmpl", payload, title, L))
    wfile(os.path.join(outdir, f"{slug}_guide.md"),       md_guide(payload, L))
    print("wrote (lang=%s):" % lang)
    for suff in ("_qa_cards.html", "_scorecard.html", "_guide.md"):
        print("  " + os.path.join(outdir, slug + suff))

if __name__ == "__main__":
    main()
