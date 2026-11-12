# -*- coding: utf-8 -*-
"""
pages.py — static, self-contained HTML pages rendered from the shared payload.

render.py calls these to write, next to the Q&A cards and the scorecard:
  <slug>_index.html     batch index: every page for every candidate, one click away
  <slug>_guide.html     the full interview guide as a readable page (the .md stays as source)
  <slug>_weakness.html  weakness analysis      (candidate["weakness"])
  <slug>_resume.html    resume optimization    (candidate["resume_opt"])
  <slug>_jd.html        job-description match  (candidate["jd_match"])

Every page inlines templates/page.css, escapes every payload string, highlights fact
placeholders (【待补充：…】 / [TBD: …]), links its sibling pages with relative hrefs and
prints to A4, so "Save as PDF" in the browser's print dialog gives a clean PDF.
Section shapes are specified in reference/modes-spec.md. No third-party dependencies.
"""
import html
import io
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
TMPL = os.path.join(os.path.dirname(HERE), "templates")
BRAND = "resume-grill"

PLACEHOLDER_RE = re.compile(r"【待补充[：:][^】]*】|\[TBD:[^\]]*\]")
CODE_RE = re.compile(r"`([^`\n]+)`")
SEVERITIES = ("high", "medium", "low")
STATUSES = ("met", "partial", "gap")
PRIORITIES = ("must", "nice")

JS = """(function(){
var opened=[];
function openAll(){opened=[];document.querySelectorAll('details:not([open])').forEach(function(d){d.open=true;opened.push(d);});}
function restore(){opened.forEach(function(d){d.open=false;});opened=[];document.body.classList.remove('print-resume');}
window.addEventListener('beforeprint',openAll);
window.addEventListener('afterprint',restore);
document.addEventListener('click',function(e){
  var b=e.target.closest('[data-print]');
  if(b){if(b.getAttribute('data-print')==='resume'){document.body.classList.add('print-resume');}window.print();return;}
  var t=e.target.closest('[data-toggle]');
  if(t){var open=t.getAttribute('data-state')==='closed';
    document.querySelectorAll('details.fold').forEach(function(d){d.open=open;});
    t.setAttribute('data-state',open?'open':'closed');
    t.textContent=t.getAttribute(open?'data-close':'data-open');}
});
})();"""

_CSS = None


def css():
    global _CSS
    if _CSS is None:
        with io.open(os.path.join(TMPL, "page.css"), encoding="utf-8") as f:
            _CSS = f.read()
    return _CSS


def esc(s):
    return html.escape("" if s is None else str(s), quote=True)


def fmt(s):
    """Escape payload text, then mark `code` spans and fact placeholders."""
    t = CODE_RE.sub(r"<code>\1</code>", esc(s))
    return PLACEHOLDER_RE.sub(lambda m: '<mark class="tbd">%s</mark>' % m.group(0), t)


def count_placeholders(obj):
    if isinstance(obj, str):
        return len(PLACEHOLDER_RE.findall(obj))
    if isinstance(obj, dict):
        return sum(count_placeholders(v) for v in obj.values())
    if isinstance(obj, list):
        return sum(count_placeholders(v) for v in obj)
    return 0


# ---------------------------------------------------------------- building blocks

def shell(L, lang, title, subtitle, nav, body, tools="", toggle=False):
    links = "".join('<a href="%s">%s</a>' % (esc(n["href"]), esc(n["label"])) for n in nav)
    toggle_btn = ""
    if toggle:
        toggle_btn = ('<button class="btn" data-toggle data-state="open" data-close="%s" data-open="%s">%s</button>'
                      % (esc(L["collapse_all"]), esc(L["expand_all"]), esc(L["collapse_all"])))
    sub = '<div class="sub">%s</div>' % esc(subtitle) if subtitle else ""
    return "".join([
        "<!doctype html>\n<html lang=\"", esc(lang), "\">\n<head>\n<meta charset=\"utf-8\">\n",
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n",
        "<title>", esc(title), "</title>\n<style>\n", css(), "</style>\n</head>\n<body>\n",
        "<header class=\"top\"><div class=\"inner\"><h1>", esc(title), "</h1>", sub,
        "<nav class=\"bar noprint\"><span class=\"links\">", links, "</span><span class=\"tools\">",
        toggle_btn, tools,
        "<button class=\"btn primary\" data-print=\"all\" title=\"", esc(L["export_pdf_hint"]), "\">",
        esc(L["export_pdf"]), "</button></span></nav></div></header>\n",
        "<main class=\"wrap\">\n", body, "\n</main>\n",
        "<footer class=\"foot\"><div class=\"brand\">", BRAND, "</div></footer>\n",
        "<script>", JS, "</script>\n</body>\n</html>\n",
    ])


def subtitle_line(meta, L):
    bits = []
    if meta.get("date"):
        bits.append("%s%s%s" % (L["date"], L["colon"], meta["date"]))
    if meta.get("title"):
        bits.append(meta["title"])
    return L["sep"].join(bits)


def cand_head(cid, d, L):
    link = ""
    if d.get("resume"):
        link = ' <a class="rlink" href="%s">%s</a>' % (esc(d["resume"]), esc(L["resume_link"]))
    return '<div class="cand-h"><h2>%s</h2>%s</div>' % (esc(d.get("name") or cid), link)


def toc(items):
    """In-page links when a page holds more than one candidate."""
    if len(items) < 2:
        return ""
    return '<nav class="toc noprint">%s</nav>' % "".join(
        '<a href="#cand-%d">%s</a>' % (i, esc(d.get("name") or cid)) for i, (cid, d) in items)


def answer(text, L):
    if not text:
        return ""
    return '<details class="fold" open><summary>%s</summary><p>%s</p></details>' % (
        esc(L["sample_answer"]), fmt(text))


def followups(items, L, title):
    if not items:
        return ""
    out = ['<span class="k probe">%s</span>' % esc(title)]
    for f in items:
        when = ""
        if f.get("when"):
            when = '<p class="when">%s%s%s</p>' % (esc(L["when"]), esc(L["colon"]), fmt(f["when"]))
        out.append('<div class="fu">%s<p>%s</p>%s</div>' % (when, fmt(f.get("q")), answer(f.get("answer"), L)))
    return "".join(out)


def ul(items, cls="plain"):
    return '<ul class="%s">%s</ul>' % (cls, "".join("<li>%s</li>" % fmt(x) for x in items or []))


def ol(items, cls="plain"):
    return '<ol class="%s">%s</ol>' % (cls, "".join("<li>%s</li>" % fmt(x) for x in items or []))


def blk(kind, title, inner):
    return '<div class="blk %s"><div class="bt">%s</div>%s</div>' % (kind, esc(title), inner)


def para(text):
    return "<p>%s</p>" % fmt(text) if text else ""


def with_section(payload, key):
    """(index, (cid, candidate)) for candidates that carry `key`; index anchors the toc."""
    items = list(payload.get("candidates", {}).items())
    return [(i, (cid, d)) for i, (cid, d) in enumerate(items) if key is None or d.get(key)]


# ---------------------------------------------------------------- interview guide

def guide_card(c, L):
    anchor = '<span class="anchor">%s</span>' % esc(c["anchor"]) if c.get("anchor") else ""
    out = ['<article class="card"><div class="card-h"><span class="badge">%s</span><h4>%s%s</h4></div><div class="card-b">'
           % (esc(c.get("n")), esc(c.get("title")), anchor)]
    if c.get("ladder"):
        out.append('<span class="k">%s</span>' % esc(L["ladder_h"]))
        for step in c["ladder"]:
            out.append('<div class="rung"><span class="lv">%s</span>%s%s</div>'
                       % (esc(step.get("level")), fmt(step.get("q")), answer(step.get("answer"), L)))
        ask_label = L["l3_label"]
    else:
        ask_label = L["ask_label"]
    out.append('<span class="k">%s</span><div class="rung">%s%s</div>'
               % (esc(ask_label), fmt(c.get("ask")), answer(c.get("ask_answer"), L)))
    if not c.get("ask_answer") and c.get("good"):
        out.append(blk("good", L["good_h"], ul(c["good"])))   # legacy payloads: bulleted answer key
    if c.get("probe"):
        out.append('<span class="k probe">%s</span><div class="fu"><p>%s</p>%s</div>'
                   % (esc(L["probe_h"]), fmt(c["probe"]), answer(c.get("probe_answer"), L)))
    out.append(followups(c.get("followups"), L, L["followups_h"]))
    if c.get("pass"):
        out.append(blk("good", L["pass_h"], ul(c["pass"])))
    if c.get("tell"):
        out.append(blk("bad", L["tell_h"], para(c["tell"])))
    out.append("</div></article>")
    return "".join(out)


def guide_page(payload, L, lang, nav, leads=()):
    meta = payload.get("meta", {})
    title = meta.get("title") or L["guide_title"]
    items = with_section(payload, None)
    body = []
    if leads:
        body.append('<div class="panel">%s</div>' % "".join(para(x) for x in leads if x))
    body.append(toc(items))
    for i, (cid, d) in items:
        s = ['<section class="cand" id="cand-%d">' % i, cand_head(cid, d, L)]
        if d.get("profile") or d.get("ruler"):
            ruler = '<div class="ruler"><b>%s</b>%s%s</div>' % (
                esc(L["ruler_h"]), esc(L["colon"]), fmt(d["ruler"])) if d.get("ruler") else ""
            s.append('<div class="panel"><span class="k">%s</span><p class="lead">%s</p>%s</div>'
                     % (esc(L["profile_h"]), fmt(d.get("profile")), ruler))
        if d.get("strengths"):
            s.append(blk("good", L["strengths_plain"], ol(d["strengths"])))
        if d.get("flags"):
            s.append(blk("bad", L["flags_plain"], ol(d["flags"])))
        o = d.get("opener") or {}
        if o.get("title"):
            note = ""
            if o.get("expect"):
                note += '<p><b>%s</b>%s%s</p>' % (esc(L["opener_expect"]), esc(L["colon"]), fmt(o["expect"]))
            if o.get("tell"):
                note += '<p><b>%s</b>%s%s</p>' % (esc(L["opener_tell"]), esc(L["colon"]), fmt(o["tell"]))
            s.append('<article class="card"><div class="card-h"><span class="badge">%s</span><h4>%s</h4></div>'
                     '<div class="card-b">%s%s</div></article>'
                     % (esc(L["opener_badge"]), esc(o["title"]), ul(o.get("questions")), note))
        if d.get("cards"):
            s.append('<h3 class="sec">%s</h3>' % esc(L["core_h"]))
            s.extend(guide_card(c, L) for c in d["cards"])
        if d.get("probes"):
            s.append('<h3 class="sec">%s</h3>' % esc(L["probes_h"]))
            for p in d["probes"]:
                s.append('<div class="fu"><p><b>%s</b>%s%s</p>%s</div>'
                         % (esc(p.get("tag")), esc(L["colon"]), fmt(p.get("q")), answer(p.get("answer"), L)))
        s.append("</section>")
        body.append("".join(s))
    return shell(L, lang, title, meta.get("subtitle") or "", nav, "\n".join(body), toggle=True)


# ---------------------------------------------------------------- weakness analysis

def weakness_page(payload, L, lang, nav):
    meta = payload.get("meta", {})
    items = with_section(payload, "weakness")
    body = [toc(items)]
    for i, (cid, d) in items:
        w = d["weakness"]
        entries = sorted(w.get("items") or [],
                         key=lambda it: SEVERITIES.index(it.get("severity")) if it.get("severity") in SEVERITIES else 9)
        s = ['<section class="cand" id="cand-%d">' % i, cand_head(cid, d, L)]
        chips = "".join('<span class="chip %s">%s %d</span>'
                        % (sev, esc(L["sev_" + sev]), sum(1 for it in entries if it.get("severity") == sev))
                        for sev in SEVERITIES)
        s.append('<div class="panel">%s<div class="chips">%s</div></div>'
                 % (para(w.get("summary")), chips))
        if w.get("actions"):
            s.append('<h3 class="sec">%s</h3>%s' % (esc(L["actions_h"]), ol(w["actions"])))
        if w.get("keep"):
            s.append('<h3 class="sec">%s</h3><div class="blk good">%s</div>' % (esc(L["keep_h"]), ul(w["keep"])))
        if entries:
            s.append('<h3 class="sec">%s</h3>' % esc(L["items_h"]))
        for it in entries:
            sev = it.get("severity") if it.get("severity") in SEVERITIES else ""
            pill = '<span class="chip %s">%s</span>' % (sev, esc(L["sev_" + sev])) if sev else ""
            b = []
            if it.get("quote"):
                b.append('<span class="k">%s</span><blockquote class="q">%s</blockquote>' % (esc(L["quote_h"]), fmt(it["quote"])))
            if it.get("issue"):
                b.append('<span class="k bad">%s</span>%s' % (esc(L["issue_h"]), para(it["issue"])))
            if it.get("why"):
                b.append('<span class="k warn">%s</span>%s' % (esc(L["why_h"]), para(it["why"])))
            b.append(followups(it.get("followups"), L, L["fu_h"]))
            if it.get("fix"):
                b.append(blk("good", L["fix_h"], para(it["fix"])))
            if it.get("rewrite"):
                b.append(blk("warn", L["rewrite_h"], para(it["rewrite"])))
            s.append('<article class="card %s"><div class="card-h"><span class="badge">%s</span><h4>%s %s</h4></div>'
                     '<div class="card-b">%s</div></article>'
                     % (sev, esc(it.get("id")), esc(it.get("category")), pill, "".join(b)))
        s.append("</section>")
        body.append("".join(s))
    return shell(L, lang, L["weakness_title"], subtitle_line(meta, L), nav, "\n".join(body), toggle=True)


# ---------------------------------------------------------------- resume optimization

def resume_paper(o):
    out = ['<div class="paper">']
    if o.get("name"):
        out.append('<p class="pn">%s</p>' % fmt(o["name"]))
    if o.get("headline"):
        out.append('<p class="ph">%s</p>' % fmt(o["headline"]))
    if o.get("contact"):
        out.append('<p class="pc">%s</p>' % fmt(o["contact"]))
    for sec in o.get("sections") or []:
        out.append("<h5>%s</h5>" % fmt(sec.get("title")))
        for e in sec.get("entries") or []:
            org = ' <span class="eo">%s</span>' % fmt(e["org"]) if e.get("org") else ""
            period = '<span class="ep">%s</span>' % fmt(e["period"]) if e.get("period") else ""
            bullets = ul(e.get("bullets"), "") if e.get("bullets") else ""
            out.append('<div class="entry"><div class="eh"><span>%s%s</span>%s</div>%s</div>'
                       % (fmt(e.get("title")), org, period, bullets))
    out.append("</div>")
    return "".join(out)


def resume_page(payload, L, lang, nav):
    meta = payload.get("meta", {})
    items = with_section(payload, "resume_opt")
    body = [toc(items)]
    for i, (cid, d) in items:
        r = d["resume_opt"]
        s = ['<section class="cand" id="cand-%d">' % i, cand_head(cid, d, L)]
        if r.get("summary"):
            s.append('<div class="panel">%s</div>' % para(r["summary"]))
        if r.get("questions"):
            lis = []
            for q in r["questions"]:
                aff = ""
                if q.get("affects"):
                    aff = '<div class="chips">%s</div>' % "".join(
                        '<span class="chip">%s %s</span>' % (esc(L["affects"]), esc(a)) for a in q["affects"])
                lis.append('<li><b>%s</b> %s<div class="when">%s</div>%s</li>'
                           % (esc(q.get("id")), fmt(q.get("q")), fmt(q.get("why")), aff))
            s.append('<h3 class="sec">%s</h3><p class="sub">%s</p><ol class="plain">%s</ol>'
                     % (esc(L["questions_h"]), esc(L["questions_lead"]), "".join(lis)))
        if r.get("edits"):
            s.append('<h3 class="sec">%s</h3>' % esc(L["edits_h"]))
            for e in r["edits"]:
                why = '<span class="k">%s</span>%s' % (esc(L["reason_h"]), para(e["why"])) if e.get("why") else ""
                s.append('<article class="card"><div class="card-h"><span class="badge">%s</span><h4>%s</h4></div>'
                         '<div class="card-b"><div class="ba"><div class="before"><span class="k bad">%s</span>%s</div>'
                         '<div class="after"><span class="k good">%s</span>%s</div></div>%s</div></article>'
                         % (esc(e.get("id")), fmt(e.get("section")), esc(L["before_h"]), fmt(e.get("before")),
                            esc(L["after_h"]), fmt(e.get("after")), why))
        if r.get("optimized"):
            s.append('<h3 class="sec">%s</h3>' % esc(L["optimized_h"]))
            n = count_placeholders(r["optimized"])
            if n:
                s.append('<div class="notice">%s</div>' % esc(L["tbd_left"].replace("{n}", str(n))))
            s.append(resume_paper(r["optimized"]))
        s.append("</section>")
        body.append("".join(s))
    tools = '<button class="btn" data-print="resume" title="%s">%s</button>' % (
        esc(L["export_pdf_hint"]), esc(L["export_resume"]))
    return shell(L, lang, L["resume_title"], subtitle_line(meta, L), nav, "\n".join(body), tools=tools)


# ---------------------------------------------------------------- JD match

def jd_page(payload, L, lang, nav):
    meta = payload.get("meta", {})
    items = with_section(payload, "jd_match")
    body = [toc(items)]
    co = L["colon"]
    for i, (cid, d) in items:
        j = d["jd_match"]
        reqs = j.get("requirements") or []
        s = ['<section class="cand" id="cand-%d">' % i, cand_head(cid, d, L)]
        head = []
        if j.get("jd_title"):
            head.append('<p><b>%s</b>%s%s</p>' % (esc(L["jd_h"]), esc(co), fmt(j["jd_title"])))
        if j.get("jd_source"):
            src = j["jd_source"]
            shown = '<a href="%s">%s</a>' % (esc(src), esc(src)) if re.match(r"https?://", str(src)) else fmt(src)
            head.append('<p class="when">%s%s%s</p>' % (esc(L["jd_source_h"]), esc(co), shown))
        head.append(para(j.get("summary")))
        for prio in PRIORITIES:
            group = [r for r in reqs if r.get("priority") == prio]
            if group:
                chips = "".join('<span class="chip %s">%s %d</span>'
                                % (st, esc(L["status_" + st]), sum(1 for r in group if r.get("status") == st))
                                for st in STATUSES)
                head.append('<div class="chips"><span class="chip">%s %d</span>%s</div>'
                            % (esc(L["prio_" + prio]), len(group), chips))
        s.append('<div class="panel">%s</div>' % "".join(head))
        if reqs:
            rows = []
            for r in reqs:
                st = r.get("status") if r.get("status") in STATUSES else ""
                prio = r.get("priority") if r.get("priority") in PRIORITIES else ""
                status = '<span class="chip %s">%s</span>' % (st, esc(L["status_" + st])) if st else ""
                prio_chip = ' <span class="chip">%s</span>' % esc(L["prio_" + prio]) if prio else ""
                note = para(r.get("note"))
                if r.get("action"):
                    note += '<span class="k">%s</span>%s' % (esc(L["action_h"]), para(r["action"]))
                rows.append('<tr><td class="id">%s</td><td>%s%s</td><td>%s</td><td>%s</td><td>%s</td></tr>'
                            % (esc(r.get("id")), fmt(r.get("text")), prio_chip, status,
                               ul(r.get("evidence"), "") if r.get("evidence") else "", note))
            s.append('<h3 class="sec">%s</h3><table class="req"><thead><tr><th>#</th><th>%s</th><th>%s</th>'
                     '<th>%s</th><th>%s</th></tr></thead><tbody>%s</tbody></table>'
                     % (esc(L["req_h"]), esc(L["col_req"]), esc(L["col_status"]), esc(L["col_evidence"]),
                        esc(L["col_note"]), "".join(rows)))
        kw = j.get("keywords") or {}
        if kw.get("present") or kw.get("missing"):
            line = lambda words, cls: "".join('<span class="chip kw %s">%s</span>' % (cls, esc(w)) for w in words or [])
            s.append('<h3 class="sec">%s</h3><span class="k good">%s</span><div class="chips">%s</div>'
                     '<span class="k bad">%s</span><div class="chips">%s</div>'
                     % (esc(L["kw_h"]), esc(L["kw_present"]), line(kw.get("present"), "met"),
                        esc(L["kw_missing"]), line(kw.get("missing"), "gap")))
        if j.get("gaps"):
            s.append('<h3 class="sec">%s</h3>' % esc(L["gaps_h"]))
            for g in j["gaps"]:
                s.append('<article class="card high"><div class="card-h"><h4>%s</h4></div><div class="card-b">%s%s</div></article>'
                         % (fmt(g.get("gap")), blk("good", L["plan_h"], para(g.get("plan"))),
                            blk("probe", L["talk_h"], para(g.get("talk")))))
        if j.get("questions"):
            s.append('<h3 class="sec">%s</h3>%s' % (esc(L["jdq_h"]), followups(j["questions"], L, L["jdq_h"])))
        s.append("</section>")
        body.append("".join(s))
    return shell(L, lang, L["jd_title"], subtitle_line(meta, L), nav, "\n".join(body), toggle=True)


# ---------------------------------------------------------------- batch index

def index_page(payload, L, lang, nav, artifacts):
    """artifacts: [{kind, href, label, desc, key}] — key is the candidate field the page needs (None = all)."""
    meta = payload.get("meta", {})
    items = with_section(payload, None)
    body = ['<div class="panel">%s</div>' % para(L["index_lead"]), toc(items)]
    for i, (cid, d) in items:
        tiles = []
        for a in artifacts:
            if a["kind"] == "index" or (a["key"] and not d.get(a["key"])):
                continue
            tiles.append('<a class="tile" href="%s"><span class="tl">%s</span><span class="td">%s</span>'
                         '<span class="tf">%s</span></a>'
                         % (esc(a["href"]), esc(a["label"]), esc(a["desc"]), esc(a["href"])))
        body.append('<section class="cand" id="cand-%d">%s<div class="tiles">%s</div></section>'
                    % (i, cand_head(cid, d, L), "".join(tiles)))
    return shell(L, lang, L["index_title"], subtitle_line(meta, L), nav, "\n".join(body))
