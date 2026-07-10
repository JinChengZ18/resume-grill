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
           "links":[{"label":..., "href":...}], "footer":...},
  "candidates": {
    "<id>": {
      "name":..., "resume": <relative-href-or-null>, "profile":..., "ruler":...,
      "strengths":[...],   # 真实强项/亮点（可空）
      "flags":[...],
      "opener":{"title":..., "questions":[...], "expect":..., "tell":...},
      "cards":[{"n":"Q1","title":..., "anchor":..., "ladder":[{"level":..., "q":...}],
                "ask":..., "good":[...], "pass":[...], "tell":..., "probe":...}],
      "probes":[{"tag":..., "q":...}]
    }
  }
}

Writes with UTF-8 + LF endings (Windows-safe). No third-party deps.
"""
import json, sys, os, io

HERE = os.path.dirname(os.path.abspath(__file__))
TMPL = os.path.join(os.path.dirname(HERE), "templates")

def wfile(path, text):
    # binary write with explicit LF to avoid CRLF churn on Windows
    with open(path, "wb") as f:
        f.write(text.replace("\r\n", "\n").encode("utf-8"))

def inject(tmpl_name, payload, title):
    with io.open(os.path.join(TMPL, tmpl_name), encoding="utf-8") as f:
        t = f.read()
    data = json.dumps(payload, ensure_ascii=False)
    data = data.replace("</", "<\\/")            # keep </script> from closing the tag
    t = t.replace("/*__PAYLOAD__*/{}", data)
    t = t.replace("__TITLE__", title)
    return t

def md_guide(payload):
    m = payload.get("meta", {})
    out = []
    out.append(f"# {m.get('title','对抗性技术面试指南')}\n")
    if m.get("subtitle"): out.append(f"> {m['subtitle']}")
    if m.get("date"):     out.append(f"> 日期：{m['date']}｜整理：{m.get('by','J.C.')}")
    out.append("> 每题：建议提问 → 期望的优质回答（分点）→ 及格线 → 典型露馅 → 追问。题号 Q1–Q6 与评分卡 ★1–★6 对应。\n")
    for cid, d in payload.get("candidates", {}).items():
        out.append(f"---\n\n# {d.get('name', cid)}\n")
        if d.get("profile"): out.append(f"## 画像与可信度\n\n{d['profile']}\n")
        if d.get("ruler"):   out.append(f"> **标尺：** {d['ruler']}\n")
        if d.get("strengths"):
            out.append("## 亮点 · 真实强项\n")
            for i, s in enumerate(d["strengths"], 1): out.append(f"{i}. {s}")
            out.append("")
        if d.get("flags"):
            out.append("## 关键红旗\n")
            for i, f in enumerate(d["flags"], 1): out.append(f"{i}. {f}")
            out.append("")
        o = d.get("opener") or {}
        if o.get("title"):
            out.append(f"## {o['title']}\n")
            for q in o.get("questions", []): out.append(f"- {q}")
            out.append("")
            if o.get("expect"): out.append(f"**期望的行为**：{o['expect']}")
            if o.get("tell"):   out.append(f"**露馅**：{o['tell']}\n")
        out.append("## 核心验伪题（含答案键；题号对应评分卡 ★1–★6）\n")
        for c in d.get("cards", []):
            out.append(f"### {c.get('n','')} · {c.get('title','')}\n")
            if c.get("anchor"): out.append(f"> 挂靠简历项目：{c['anchor']}\n")
            if c.get("ladder"):
                out.append("**提问阶梯（由浅入深，从简历项目起手）**\n")
                for step in c["ladder"]:
                    out.append(f"- *{step.get('level','')}*：{step.get('q','')}")
                out.append(f"- *L3 硬核验伪*：{c.get('ask','')}\n")
            else:
                out.append(f"**建议提问**：{c.get('ask','')}\n")
            out.append("**期望的优质回答**\n")
            for g in c.get("good", []): out.append(f"- {g}")
            out.append("\n**及格线（必须听到）**\n")
            for p in c.get("pass", []): out.append(f"- {p}")
            out.append(f"\n**典型露馅**：{c.get('tell','')}\n")
            out.append(f"**追问**：{c.get('probe','')}\n")
        if d.get("probes"):
            out.append("## 补充探针（无标准答案，答顺后继续加压）\n")
            for p in d["probes"]: out.append(f"- **{p.get('tag','')}**：{p.get('q','')}")
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
    title = payload.get("meta", {}).get("title", "对抗性技术面试")

    wfile(os.path.join(outdir, f"{slug}_qa_cards.html"),  inject("qa_cards.html.tmpl",  payload, title))
    wfile(os.path.join(outdir, f"{slug}_scorecard.html"), inject("scorecard.html.tmpl", payload, title))
    wfile(os.path.join(outdir, f"{slug}_guide.md"),       md_guide(payload))
    print("wrote:")
    for suff in ("_qa_cards.html", "_scorecard.html", "_guide.md"):
        print("  " + os.path.join(outdir, slug + suff))

if __name__ == "__main__":
    main()
