# -*- coding: utf-8 -*-
"""Interviewer kit (面试官手册): one self-contained HTML page per candidate.

Layout follows how an interviewer works — before / during / after:
  * before: who the candidate is, the three questions this interview must answer, what to verify,
    the time plan, strengths and notes; the resume is embedded (folded), never linked.
  * during: the opener, each theme, and the wrap-up. Every question is followed directly by what to
    listen for (★ = pass line) and a folded model answer — no jump links, no appendix.
  * after: score each dimension 4/3/2/1, see the suggested verdict, generate a review draft.
Long text is folded in place (<details>); printing outputs only what is expanded.
Older payloads without the kit fields still render: listen points fall back to pass/good, danger
signals to tell, dimensions to one per theme plus a credibility gate."""
import base64
import json
import os
import re

import pages

esc, fmt = pages.esc, pages.fmt

T = {
    "zh": {
        "title": "面试官手册", "min": "分钟", "colon": "：", "sep": "；", "list": "、",
        "before": "面试前", "before_hint": "开场前花5分钟读完这一部分",
        "during": "面试中", "during_hint": "L1、L2由浅入深；情境题和追问按条件选问。每道题下面是要听的点（★为及格线），示范回答折叠在其后，点开即看。勾选和记录自动保存在本机浏览器。",
        "after": "面试后", "after_hint": "按维度打分（4超出预期、3达到要求、2部分达到、1未达到），再生成面评草稿",
        "decide_h": "这场面试要回答的问题", "verify_h": "先核实的事项", "item": "事项", "when": "时机",
        "time_h": "时间安排", "time_cols": ("分钟", "内容", "时长", "优先级"), "untimed": "不限时：按主题逐一覆盖，深度优先。",
        "strengths_h": "简历里的优势", "notes_h": "注意事项", "dims_line": "评分维度", "dims_tail": "。评分标准和结论规则在“面试后”部分。",
        "ruler_h": "标尺（点开查看）", "profile_h": "画像与可信度（点开查看）", "resume_h": "原始简历（点开查看）",
        "resume_big": "简历文件较大，未嵌入页面：", "opener": "开场", "opener_h": "开场", "wrap": "收尾", "wrap_h": "材料确认、合作与提问",
        "focus": "考察", "anchor_h": "简历原文", "listen_h": "要听的点（<span class=\"star\">★</span>为及格线）",
        "answer_h": "示范回答（点开查看）", "good_h": "期望的优质回答（点开查看）", "flags_h": "危险信号", "expect": "期望", "asked": "已问",
        "ask": "情境题", "probe": "追问", "followup": "延伸追问",
        "when_ask": "前两问答得扎实再问", "when_probe": "上一问答得好再追问",
        "note_ph": "记录要点、原话或疑点", "note_short": "记录", "wrap_listen": "要听",
        "prio": {"must": "必问", "opt": "视时间", "role": "视岗位"},
        "kind": {"core": "核心", "ref": "参考", "gate": "门槛"},
        "from_h": "证据来源", "ev_ph": "证据（题号＋要点），生成面评时会用到",
        "verdict_h": "结论", "rule_h": "建议规则（最终由面试官判断）", "rule_parts": ("通过——", "；不通过——", "；待定——", "。"),
        "verdicts": ("通过", "待定", "不通过"), "next_h": "如果待定，下一轮可以这样安排",
        "memo_h": "面评草稿", "draft": "根据记录生成草稿", "copy": "复制", "clear": "清空本页记录",
        "memo_ph": "点“根据记录生成草稿”，再按实际情况修改", "local": "记录只保存在当前浏览器，换设备不会同步；需要存档时导出PDF或复制面评。",
        "timer": "开始计时", "print": "导出PDF", "expand": "展开全部", "collapse": "收起全部",
        "print_tip": "打印时只输出已展开的内容",
        "gate_name": "表达与可信度", "gate_from": ("开场", "收尾"),
        "anchors_theme": {4: "超出预期：取舍和证据讲得清楚，并能主动指出局限", 3: "达到要求：命中及格线，理由合理",
                          2: "部分达到：方向对但缺关键环节，需要提示", 1: "未达到：停在术语层面或有明显错误"},
        "anchors_gate": {4: "主动说明本人范围、项目阶段和数字口径", 3: "问到时能说清本人范围和数字口径",
                         2: "范围和口径含糊，需要反复追问", 1: "关键事实前后矛盾"},
        "rule_default": {"pass": "核心维度均≥3，表达与可信度≥3，且没有维度为1分",
                         "fail": "任一核心维度为1分，或表达与可信度为1分", "hold": "其余情况；在面评里写明下一轮要确认的具体问题"},
        "js": {
            "by_rule": "按建议规则：", "pass": "通过", "hold": "待定", "fail": "不通过", "todo_fill": "待填",
            "incomplete": "评分未完成（核心维度和门槛项都打分后给出建议）", "transfer_done": "已问迁移类问题：",
            "transfer_none": "迁移类问题尚无记录", "not_rec": "未记录", "pass_pts": "：及格点", "flags": "，危险信号",
            "summary": "记录汇总：", "sum_pass": "及格点 ", "sum_flags": "　危险信号 ",
            "h_cand": "【候选人】", "h_verdict": "【结论】", "h_dims": "【维度评分】", "h_heard": "【听到的要点】",
            "h_risks": "【风险与不足】", "h_todo": "【待下一轮确认】", "h_notes": "【面试记录】",
            "pts": "分", "unscored": "未打分", "evidence": "证据：", "none_rec": "- 无记录", "no_flags": "- 未勾选危险信号",
            "unheard": "未听到的及格点：", "must_missing": "：必问但没有记录", "ref": "- 参考：", "none": "- 无",
            "pause": "暂停", "resume": "继续计时", "start": "开始计时", "at": "应在：", "mins": "分）", "over": "已超过", "minute": "分钟",
            "confirm": "再点一次确认清空", "clear": "清空本页记录", "cleared": "已清空", "copied": "已复制", "copy": "复制",
            "expand": "展开全部", "collapse": "收起全部", "lp": "（", "rp": "）", "dot": "。", "colon": "：", "sep": "；", "list": "、",
        },
    },
    "en": {
        "title": "Interviewer Kit", "min": " min", "colon": ": ", "sep": "; ", "list": ", ",
        "before": "Before", "before_hint": "Read this part in the five minutes before the interview",
        "during": "During", "during_hint": "L1 and L2 go from basic to deep; situational questions and probes are asked when their condition holds. Each question is followed by what to listen for (★ = pass line) and a folded model answer. Ticks and notes save in this browser.",
        "after": "After", "after_hint": "Score each dimension (4 exceeds, 3 meets, 2 partly, 1 below), then generate a review draft",
        "decide_h": "What this interview must answer", "verify_h": "Verify first", "item": "Item", "when": "When",
        "time_h": "Time plan", "time_cols": ("Minutes", "Segment", "Length", "Priority"), "untimed": "Untimed: cover theme by theme, depth first.",
        "strengths_h": "Strengths on the resume", "notes_h": "Notes", "dims_line": "Dimensions", "dims_tail": ". Anchors and the decision rule are under After.",
        "ruler_h": "Yardstick (expand)", "profile_h": "Profile and credibility (expand)", "resume_h": "Original resume (expand)",
        "resume_big": "Resume file too large to embed: ", "opener": "Opener", "opener_h": "Opener", "wrap": "Wrap-up", "wrap_h": "Materials, collaboration and questions",
        "focus": "Assesses", "anchor_h": "Resume text", "listen_h": "Listen for (<span class=\"star\">★</span> = pass line)",
        "answer_h": "Model answer (expand)", "good_h": "What a strong answer covers (expand)", "flags_h": "Danger signals", "expect": "Expect", "asked": "Asked",
        "ask": "Situational", "probe": "Probe", "followup": "Extra probe",
        "when_ask": "Ask when the first two answers are solid", "when_probe": "Ask when the previous answer is strong",
        "note_ph": "Notes, quotes or doubts", "note_short": "Notes", "wrap_listen": "Listen for",
        "prio": {"must": "Must ask", "opt": "If time", "role": "If role needs"},
        "kind": {"core": "core", "ref": "reference", "gate": "gate"},
        "from_h": "Evidence from", "ev_ph": "Evidence (question + point), used in the review draft",
        "verdict_h": "Verdict", "rule_h": "Suggested rule (the interviewer decides)", "rule_parts": ("Pass: ", "; No: ", "; Hold: ", "."),
        "verdicts": ("Pass", "Hold", "No"), "next_h": "If on hold, the next round could",
        "memo_h": "Review draft", "draft": "Draft from my notes", "copy": "Copy", "clear": "Clear this page",
        "memo_ph": "Click “Draft from my notes”, then edit", "local": "Notes stay in this browser only; export to PDF or copy the review to keep them.",
        "timer": "Start timer", "print": "Export PDF", "expand": "Expand all", "collapse": "Collapse all",
        "print_tip": "Printing outputs only expanded content",
        "gate_name": "Communication and credibility", "gate_from": ("Opener", "Wrap-up"),
        "anchors_theme": {4: "Exceeds: clear trade-offs and evidence, names limits unprompted", 3: "Meets: hits the pass line with sound reasons",
                          2: "Partly: right direction, missing a key step, needs prompting", 1: "Below: stays at buzzwords or is clearly wrong"},
        "anchors_gate": {4: "States own scope, project stage and metric definitions unprompted", 3: "States scope and definitions when asked",
                         2: "Scope and definitions stay vague after follow-ups", 1: "Key facts contradict each other"},
        "rule_default": {"pass": "every core dimension ≥ 3, credibility ≥ 3, and no dimension at 1",
                         "fail": "any core dimension at 1, or credibility at 1", "hold": "anything else; list what the next round must confirm"},
        "js": {
            "by_rule": "Suggested by rule: ", "pass": "Pass", "hold": "Hold", "fail": "No", "todo_fill": "to fill",
            "incomplete": "scoring incomplete (score every core and gate dimension)", "transfer_done": "Situational questions asked: ",
            "transfer_none": "no situational question recorded", "not_rec": " not recorded", "pass_pts": ": pass points ", "flags": ", danger signals ",
            "summary": "From notes: ", "sum_pass": "pass points ", "sum_flags": "  danger signals ",
            "h_cand": "[Candidate] ", "h_verdict": "[Verdict] ", "h_dims": "[Dimensions]", "h_heard": "[Heard]",
            "h_risks": "[Risks and gaps]", "h_todo": "[Confirm next round]", "h_notes": "[Interview notes]",
            "pts": "", "unscored": "not scored", "evidence": "Evidence: ", "none_rec": "- nothing recorded", "no_flags": "- no danger signal ticked",
            "unheard": " pass points not heard: ", "must_missing": ": must-ask, no notes", "ref": "- idea: ", "none": "- none",
            "pause": "Pause", "resume": "Resume", "start": "Start timer", "at": "Planned: ", "mins": " min)", "over": "Past ", "minute": " min",
            "confirm": "Click again to clear", "clear": "Clear this page", "cleared": "Cleared", "copied": "Copied", "copy": "Copy",
            "expand": "Expand all", "collapse": "Collapse all", "lp": " (", "rp": ")", "dot": ". ", "colon": ": ", "sep": "; ", "list": ", ",
        },
    },
}

CSS = r"""
.phase{display:flex;align-items:baseline;gap:12px;margin:26px 0 6px;flex-wrap:wrap}
.phase h2{font-size:19px;margin:0;color:var(--accent)}
.phase .hint{font-size:12.5px;color:var(--soft);flex:1;min-width:260px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:12px 0}
.grid2>.panel{margin:0}
@media (max-width:760px){.grid2{grid-template-columns:1fr}}
h3.s2{font-size:14.5px;margin:0 0 6px;color:var(--ink)}
.small{font-size:12.5px;color:var(--soft)}
.dl{margin:8px 0 0}
table.t{width:100%;border-collapse:collapse;font-size:13.5px}
table.t th,table.t td{border-bottom:1px solid var(--line);padding:5px 6px;text-align:left;vertical-align:top}
table.t th{font-size:12px;color:var(--soft);font-weight:600;white-space:nowrap}
table.t td.num{white-space:nowrap;color:var(--soft)}
.tag{display:inline-block;font-size:11.5px;font-weight:700;border-radius:10px;padding:1px 8px;white-space:nowrap;border:1px solid var(--line);background:var(--card);color:var(--soft)}
.tag.must,.tag.core{background:var(--bad-bg);color:var(--bad);border-color:var(--bad-line)}
.tag.opt{background:var(--accent-soft);color:var(--accent)}
.tag.role,.tag.gate{background:var(--warn-bg);color:var(--warn);border-color:var(--warn-line)}
.tag.dim{background:var(--good-bg);color:var(--good);border-color:var(--good-line)}
details.fold{margin:6px 0}
details.fold>summary,details.ans>summary{cursor:pointer;font-size:12.5px;font-weight:700;color:var(--accent);list-style-position:inside}
details.fold>.body{font-size:13.5px;margin-top:6px}
details.resume img,details.resume object{width:100%;border:1px solid var(--line);border-radius:8px;margin-top:8px}
details.resume object{height:80vh}
.qb{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 16px 14px;margin:14px 0}
.qb.now{border-color:var(--accent);box-shadow:0 0 0 2px var(--accent-soft)}
.qb>h3{font-size:16.5px;margin:0 0 4px;display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.qn{font-weight:800;color:var(--accent)}
.sum{margin-left:auto;font-size:12px;font-weight:600;color:var(--good)}
.focus{font-size:13px;color:var(--soft);margin:2px 0 4px}
.anchor{font-size:12.5px;color:var(--soft);background:var(--quote-bg);border-left:3px solid var(--quote-line);padding:4px 8px;border-radius:0 6px 6px 0}
.sq{border-top:1px dashed var(--line);padding:12px 0 4px;margin-top:8px}
.sqh{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.lv{display:inline-block;font-size:11.5px;font-weight:700;color:var(--accent);background:var(--accent-soft);border-radius:8px;padding:0 8px;white-space:nowrap}
.lv.ask{color:var(--probe);background:var(--probe-bg)}
.cond{font-size:12px;color:var(--probe);font-weight:600}
.askd{margin-left:auto;font-size:12.5px;color:var(--soft);display:inline-flex;gap:5px;align-items:center;cursor:pointer}
.mainq{font-size:15.5px;font-weight:600;margin:6px 0 6px;line-height:1.6}
.lbl{font-size:12px;font-weight:700;color:var(--soft);margin:6px 0 2px}
ul.chk{list-style:none;margin:0;padding:0}
ul.chk li{margin:2px 0}
ul.chk label{display:flex;gap:8px;align-items:flex-start;font-size:14px;cursor:pointer}
ul.chk input{margin-top:4px;flex:none}
.star{color:var(--good);font-weight:800}
ul.flag label{color:var(--bad)}
details.ans{background:var(--good-bg);border:1px solid var(--good-line);border-radius:8px;padding:6px 11px;margin:8px 0 4px}
details.ans[open]>summary{margin-bottom:4px}
details.ans>.body{font-size:14px;line-height:1.65}
.expect{font-size:13.5px;margin:6px 0 0}
.tail{border-top:1px solid var(--line);margin-top:10px;padding-top:6px}
.fb{font-size:12.5px;color:var(--warn);margin:8px 0 0}
textarea.note,textarea.memo{width:100%;border:1px dashed var(--line);border-radius:8px;background:transparent;color:var(--ink);font:inherit;font-size:13.5px;padding:6px 8px;resize:vertical;margin-top:8px}
textarea.note{min-height:46px}
textarea.memo{min-height:280px;border-style:solid}
.dimrow{border-top:1px solid var(--line);padding:10px 0}
.dimrow:first-child{border-top:0;padding-top:0}
.dimh{display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-size:14.5px}
.auto{font-size:12px;color:var(--good);margin:3px 0}
.anchors label{display:flex;gap:8px;align-items:flex-start;font-size:13px;margin:3px 0;cursor:pointer}
.anchors b{min-width:12px}
.suggest{font-weight:700;color:var(--accent);margin:6px 0}
.verdict{display:flex;gap:18px;font-size:14.5px;flex-wrap:wrap}
.verdict label,.toggle{cursor:pointer}
.toggle{font-size:13.5px;display:flex;gap:8px;align-items:flex-start;margin:4px 0 8px}
.tools2{display:flex;gap:8px;flex-wrap:wrap}
.clock{font-variant-numeric:tabular-nums;font-weight:700;color:var(--accent);font-size:13px}
.seg{font-size:12px;color:var(--soft)}
@media print{
  .noprint,.tools2,.sum,details.resume{display:none!important}
  details:not([open]){display:none!important}
  details>summary{list-style:none}
  #during,#after{break-before:page}
  .qb[data-seg]:not([data-seg="OP"]){break-before:page}
  .sq{break-inside:avoid}
  .qb>h3,.focus{break-after:avoid}
  .qb.now{box-shadow:none;border-color:var(--line)}
  textarea.note{min-height:15mm;border:1px solid #c9d1db}
  textarea.memo{min-height:60mm;border:1px solid #c9d1db}
  .grid2{grid-template-columns:1fr 1fr}
  #before{font-size:9.6pt}
  #before .phase{margin:4px 0}
  #before .panel{padding:7px 10px;margin:6px 0}
  #before .grid2{gap:8px;margin:6px 0}
  #before table.t{font-size:8.8pt}
  #before table.t td,#before table.t th{padding:2px 4px}
  #before ul.plain,#before ol.plain{font-size:9.4pt}
  #before ul.plain li,#before ol.plain li{margin:2px 0}
}
"""

JS = r"""(function(){
var body=document.body,KEY='rgkit:'+body.getAttribute('data-key'),mem={};
try{var s=localStorage.getItem(KEY);if(s){mem=JSON.parse(s)||{};}}catch(e){mem={};}
function save(){try{localStorage.setItem(KEY,JSON.stringify(mem));}catch(e){}}
var D=JSON.parse(document.getElementById('kitdata').textContent),W=D.t;
var inputs=[].slice.call(document.querySelectorAll('[data-k]'));
function restore(){inputs.forEach(function(el){var k=el.getAttribute('data-k'),v=mem[k];
 if(el.type==='checkbox'){el.checked=!!v;}else if(el.type==='radio'){el.checked=(v===el.value);}else{el.value=(v==null?'':v);}});}
restore();
inputs.forEach(function(el){el.addEventListener(el.tagName==='TEXTAREA'?'input':'change',function(){
 var k=el.getAttribute('data-k');
 if(el.type==='checkbox'){mem[k]=el.checked;}else if(el.type==='radio'){if(el.checked){mem[k]=el.value;}}else{mem[k]=el.value;}
 save();refresh();});});
function on(k){return !!mem[k];}
function asked(t){var p=t.n+':';for(var k in mem){if(k.indexOf(p)===0&&mem[k]===true)return true;}
 return !!(mem['note:'+t.n]&&String(mem['note:'+t.n]).trim());}
function subAsked(t,i){var s=t.subs[i];if(!s.optional)return asked(t);if(on(t.n+':S'+i+':A'))return true;
 for(var j=0;j<s.listen.length;j++){if(on(t.n+':S'+i+':L'+j))return true;}return false;}
function stat(t){var pt=0,ph=0,fl=0;
 t.subs.forEach(function(s,i){if(!subAsked(t,i))return;s.listen.forEach(function(l,j){if(l.pass){pt++;if(on(t.n+':S'+i+':L'+j))ph++;}});});
 t.flags.forEach(function(f,i){if(on(t.n+':R'+i))fl++;});return {pt:pt,ph:ph,fl:fl};}
function byN(n){for(var i=0;i<D.themes.length;i++){if(D.themes[i].n===n)return D.themes[i];}return null;}
function scores(){var sc={};D.dims.forEach(function(d){var v=mem['score:'+d.id];if(v){sc[d.id]=+v;}});return sc;}
function suggest(){var core=[],gate=[],sc=scores();
 D.dims.forEach(function(d){if(d.kind==='core'||(D.toggle&&d.id===D.toggle.dim&&on('toggle')))core.push(d.id);if(d.kind==='gate')gate.push(d.id);});
 var need=core.concat(gate),i;
 for(i=0;i<need.length;i++){if(sc[need[i]]===1)return W.fail;}
 for(i=0;i<need.length;i++){if(!sc[need[i]])return W.incomplete;}
 var anyOne=D.dims.some(function(d){return sc[d.id]===1;});
 if(need.every(function(id){return sc[id]>=3;})&&!anyOne)return W.pass;
 return W.hold;}
function dimSummary(d){
 if(d.transfer){var a=[];D.themes.forEach(function(t){var i=t.transferIdx;if(i>=0&&subAsked(t,i))a.push(t.n);});
  return a.length?(W.transfer_done+a.join(W.list)):W.transfer_none;}
 var parts=[];d.qs.forEach(function(n){var t=byN(n);if(!t)return;if(!asked(t)){parts.push(n+W.not_rec);return;}
  var s=stat(t);parts.push(n+W.pass_pts+s.ph+'/'+s.pt+(s.fl?(W.flags+s.fl):''));});
 return parts.length?(W.summary+parts.join(W.sep)):'';}
function refresh(){
 D.themes.forEach(function(t){var el=document.getElementById('sum-'+t.n);if(!el)return;
  if(!asked(t)){el.textContent='';return;}var s=stat(t);el.textContent=W.sum_pass+s.ph+'/'+s.pt+(s.fl?(W.sum_flags+s.fl):'');});
 D.dims.forEach(function(d){var el=document.getElementById('auto-'+d.id);if(el)el.textContent=dimSummary(d);});
 var sg=document.getElementById('suggest');if(sg)sg.textContent=W.by_rule+suggest();}
refresh();
function draft(){var L=[],sc=scores(),v=mem.verdict||W.todo_fill,sug=suggest();
 L.push(W.h_cand+D.cand+' · '+D.role);
 L.push(W.h_verdict+v+W.lp+W.by_rule+sug+W.rp);
 L.push(W.h_dims);
 D.dims.forEach(function(d){var ev=(mem['ev:'+d.id]||'').trim();
  L.push(d.id+' '+d.name+W.lp+d.kindLabel+W.rp+W.colon+(sc[d.id]?sc[d.id]+W.pts:W.unscored)+W.dot+(ev?(W.evidence+ev):dimSummary(d)));});
 var heard=[],risks=[],todo=[];
 D.themes.forEach(function(t){var h=[],r=[],u=[];
  t.subs.forEach(function(s,i){var sa=subAsked(t,i);s.listen.forEach(function(l,j){
   if(on(t.n+':S'+i+':L'+j))h.push(l.t);else if(sa&&l.pass)u.push(s.label+W.colon+l.t);});});
  t.flags.forEach(function(f,i){if(on(t.n+':R'+i))r.push(f);});
  if(h.length)heard.push(t.n+' '+t.title+W.colon+h.join(W.sep));
  if(r.length)risks.push(t.n+W.colon+r.join(W.sep));
  if(asked(t)){if(u.length)todo.push(t.n+W.unheard+u.join(W.sep));}
  else if(t.must){todo.push(t.n+' '+t.title+W.must_missing);}});
 L.push(W.h_heard);if(heard.length){heard.forEach(function(x){L.push('- '+x);});}else{L.push(W.none_rec);}
 L.push(W.h_risks);if(risks.length){risks.forEach(function(x){L.push('- '+x);});}else{L.push(W.no_flags);}
 L.push(W.h_todo);todo.forEach(function(x){L.push('- '+x);});
 if(v===W.hold||(v===W.todo_fill&&sug===W.hold)){D.next.forEach(function(x){L.push(W.ref+x);});}
 else if(!todo.length){L.push(W.none);}
 var notes=[];D.themes.forEach(function(t){var x=(mem['note:'+t.n]||'').trim();if(x)notes.push(t.n+W.colon+x.replace(/\s*\n\s*/g,W.sep));});
 if(notes.length){L.push(W.h_notes);notes.forEach(function(x){L.push('- '+x);});}
 return L.join('\n');}
var memo=document.getElementById('memo');
var db=document.getElementById('draftBtn');if(db)db.addEventListener('click',function(){memo.value=draft();mem.memo=memo.value;save();});
var cb=document.getElementById('copyBtn');if(cb)cb.addEventListener('click',function(){var t=memo.value;
 function done(){cb.textContent=W.copied;setTimeout(function(){cb.textContent=W.copy;},1500);}
 function fallback(){memo.focus();memo.select();try{document.execCommand('copy');done();}catch(e){}}
 if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(t).then(done,fallback);}else{fallback();}});
var T=mem.__timer||{start:null,acc:0};
var clock=document.getElementById('clock'),segEl=document.getElementById('seg'),tb=document.getElementById('timerBtn');
function pad(n){return (n<10?'0':'')+n;}
function elapsed(){return T.acc+(T.start?(Date.now()-T.start):0);}
function tick(){var ms=elapsed(),m=Math.floor(ms/60000),s=Math.floor(ms/1000)%60;
 if(clock)clock.textContent=pad(m)+':'+pad(s);
 if(tb)tb.textContent=T.start?W.pause:(ms>0?W.resume:W.start);
 var cur=null;D.segs.forEach(function(g){if(m>=g.start&&m<g.end)cur=g;});
 if(segEl)segEl.textContent=(ms===0||!D.segs.length)?'':(cur?(W.at+cur.label+W.lp+cur.start+'–'+cur.end+W.mins):W.over+D.minutes+W.minute);
 [].forEach.call(document.querySelectorAll('.qb'),function(b){b.classList.toggle('now',!!(cur&&ms>0&&b.getAttribute('data-seg')===cur.key));});}
if(tb)tb.addEventListener('click',function(){if(T.start){T.acc=elapsed();T.start=null;}else{T.start=Date.now();}mem.__timer=T;save();tick();});
setInterval(tick,1000);tick();
var clr=document.getElementById('clearBtn'),armed=false;
if(clr)clr.addEventListener('click',function(){if(!armed){armed=true;clr.textContent=W.confirm;
  setTimeout(function(){armed=false;clr.textContent=W.clear;},3000);return;}
 mem={};T={start:null,acc:0};save();restore();refresh();tick();armed=false;clr.textContent=W.cleared;
 setTimeout(function(){clr.textContent=W.clear;},1500);});
var xb=document.getElementById('expandBtn');
if(xb)xb.addEventListener('click',function(){var ds=[].slice.call(document.querySelectorAll('main details:not(.resume)'));
 var open=!ds.every(function(d){return d.open;});ds.forEach(function(d){d.open=open;});xb.textContent=open?W.collapse:W.expand;});
var pb=document.getElementById('printBtn');if(pb)pb.addEventListener('click',function(){window.print();});
var sized=[];
window.addEventListener('beforeprint',function(){[].forEach.call(document.querySelectorAll('textarea'),function(t){if(t.value){sized.push([t,t.style.height]);t.style.height=(t.scrollHeight+4)+'px';}});});
window.addEventListener('afterprint',function(){sized.forEach(function(p){p[0].style.height=p[1];});sized=[];});
})();"""

IMG = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}
EMBED_LIMIT = 15 * 1024 * 1024


def labels(lang):
    return T["zh"] if str(lang or "").lower().startswith("zh") else T["en"]


def kit_filename(slug, cid):
    return "%s_kit_%s.html" % (slug, re.sub(r"[^A-Za-z0-9_-]+", "_", str(cid)) or "x")


def _split(text):
    parts = [p.strip() for p in re.split(r"[；;]\s*", str(text or "")) if p.strip()]
    return parts


def _listen(items):
    out = []
    for it in items or []:
        if isinstance(it, dict):
            t = it.get("t") or it.get("text") or ""
            if t:
                out.append({"t": t, "pass": bool(it.get("pass"))})
        elif isinstance(it, (list, tuple)) and len(it) == 2:
            out.append({"t": it[1], "pass": bool(it[0])})
        elif isinstance(it, str) and it:
            out.append({"t": it, "pass": False})
    return out


def _anchors(d, default):
    a = d.get("anchors") or {}
    got = {}
    for s in (4, 3, 2, 1):
        v = d.get("a%d" % s) or a.get(s) or a.get(str(s))
        got[s] = v or default[s]
    return got


def normalize(cand, meta, W):
    """Turn a candidate object (kit fields optional) into the structures the page needs."""
    kit = cand.get("kit") or {}
    plan = meta.get("plan") or {}
    cards = cand.get("cards") or []
    per_q = plan.get("perQuestion") or 8
    untimed = plan.get("depth") == "ultra" or meta.get("depth") == "ultra"
    must_n = -(-len(cards) * 2 // 3) if cards else 0
    themes = []
    for i, c in enumerate(cards):
        subs = []
        for j, s in enumerate(c.get("ladder") or []):
            subs.append({"kind": "L%d" % (j + 1), "label": s.get("level") or "L%d" % (j + 1), "q": s.get("q", ""),
                         "a": s.get("answer", ""), "listen": _listen(s.get("listen")), "when": ""})
        if c.get("ask"):
            subs.append({"kind": "ask", "label": W["ask"], "q": c["ask"], "a": c.get("ask_answer", ""),
                         "listen": _listen(c.get("ask_listen")), "when": c.get("ask_when") or W["when_ask"]})
        if c.get("probe"):
            subs.append({"kind": "probe", "label": W["probe"], "q": c["probe"], "a": c.get("probe_answer", ""),
                         "listen": _listen(c.get("probe_listen")), "when": c.get("probe_when") or W["when_probe"]})
        for f in c.get("followups") or []:
            if f.get("q"):
                subs.append({"kind": "followup", "label": W["followup"], "q": f["q"], "a": f.get("answer", ""),
                             "listen": _listen(f.get("listen")), "when": f.get("when") or W["when_probe"]})
        if subs and not any(s["listen"] for s in subs):  # older payloads: the pass line becomes listen points
            subs[0]["listen"] = [{"t": x, "pass": True} for x in c.get("pass") or []]
        legacy_good = list(c.get("good") or []) if not any(s["a"] for s in subs) else []
        n = c.get("n") or "Q%d" % (i + 1)
        tkey = c.get("transfer") or "ask"
        tidx = next((k for k, s in enumerate(subs) if s["kind"] == tkey), -1)
        themes.append({"n": n, "title": c.get("title", ""), "anchor": c.get("anchor", ""), "focus": c.get("focus", ""),
                       "prio": c.get("prio") if c.get("prio") in W["prio"] else ("must" if i < must_n else "opt"),
                       "min": None if untimed else int(c.get("minutes") or per_q),
                       "dims": list(c.get("dims") or []), "flags": list(c.get("flags") or _split(c.get("tell"))),
                       "fallback": c.get("fallback", ""), "tidx": tidx, "subs": subs, "good": legacy_good})
    dims = []
    for d in kit.get("dims") or []:
        kind = d.get("kind") if d.get("kind") in W["kind"] else "core"
        dims.append({"id": d.get("id"), "name": d.get("name", ""), "kind": kind, "from": list(d.get("from") or []),
                     "anchors": _anchors(d, W["anchors_gate"] if kind == "gate" else W["anchors_theme"])})
    if not dims:  # older payloads: one dimension per theme plus a credibility gate
        for k, t in enumerate(themes):
            did = "D%d" % (k + 1)
            dims.append({"id": did, "name": t["title"], "kind": "core" if t["prio"] == "must" else "ref",
                         "from": [t["n"]], "anchors": dict(W["anchors_theme"])})
            t["dims"] = t["dims"] or [did]
        dims.append({"id": "D%d" % (len(themes) + 1), "name": W["gate_name"], "kind": "gate",
                     "from": list(W["gate_from"]), "anchors": dict(W["anchors_gate"])})
    known = {d["id"] for d in dims}
    for t in themes:
        t["dims"] = [x for x in t["dims"] if x in known]
    op = cand.get("opener") or {}
    tog = kit.get("role_toggle") or {}
    rule = dict(W["rule_default"])
    rule.update({k: v for k, v in (kit.get("rule") or {}).items() if v})
    return {
        "themes": themes, "dims": dims, "rule": rule,
        "toggle": {"dim": tog.get("dim"), "label": tog.get("label")} if tog.get("dim") in known and tog.get("label") else None,
        "opener": {"title": op.get("title") or W["opener_h"], "questions": op.get("questions") or [], "expect": op.get("expect", ""),
                   "listen": _listen(kit.get("opener_listen")), "flags": list(kit.get("opener_flags") or _split(op.get("tell"))),
                   "min": None if untimed else int(kit.get("opener_minutes") or plan.get("opener") or 5)},
        "wrap": {"items": [p for p in cand.get("probes") or [] if p.get("q")],
                 "min": None if untimed else int(kit.get("wrap_minutes") or plan.get("buffer") or 7)},
        "decide": list(kit.get("decide") or []),
        "verify": [(v.get("text", ""), v.get("when", "")) if isinstance(v, dict) else (str(v), "") for v in kit.get("verify") or []]
                  or [(f, "") for f in cand.get("flags") or []],
        "strengths": list(cand.get("strengths") or []), "notes": list(kit.get("notes") or []),
        "time_note": kit.get("time_note", ""), "next": list(kit.get("next_round") or []),
        "summary": kit.get("summary") or "", "role": kit.get("role") or meta.get("role") or meta.get("title") or "",
        "untimed": untimed,
    }


def _ul(items):
    return '<ul class="plain">%s</ul>' % "".join("<li>%s</li>" % esc(x) for x in items)


def _checks(prefix, items, flag=False):
    out = []
    for i, it in enumerate(items):
        if flag:
            key, text, star = "%s:R%d" % (prefix, i), it, ""
        else:
            key, text = "%s:L%d" % (prefix, i), it["t"]
            star = '<span class="star">★</span> ' if it["pass"] else ""
        out.append('<li><label><input type="checkbox" data-k="%s"><span>%s%s</span></label></li>' % (key, star, esc(text)))
    return '<ul class="chk%s">%s</ul>' % (" flag" if flag else "", "".join(out))


def _fold(cls, summary, inner):
    return '<details class="%s"><summary>%s</summary><div class="body">%s</div></details>' % (cls, summary, inner)


def _resume_block(cand, outdir, W):
    name = cand.get("resume")
    if not name:
        return ""
    path = os.path.join(outdir or "", name)
    if not os.path.isfile(path):
        return ""
    ext = os.path.splitext(name)[1].lower()
    if os.path.getsize(path) > EMBED_LIMIT or (ext not in IMG and ext != ".pdf"):
        return '<p class="small">%s%s</p>' % (esc(W["resume_big"]), esc(name))
    with open(path, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode("ascii")
    if ext == ".pdf":
        inner = '<object type="application/pdf" data="data:application/pdf;base64,%s"><p class="small">%s</p></object>' % (b64, esc(name))
    else:
        inner = '<img alt="%s" src="data:%s;base64,%s">' % (esc(name), IMG[ext], b64)
    return '<details class="resume"><summary>%s</summary>%s</details>' % (esc(W["resume_h"]), inner)


def kit_page(payload, cid, cand, lang, slug, outdir=None):
    meta = payload.get("meta") or {}
    W = labels(lang)
    N = normalize(cand, meta, W)
    short = re.split(r"\s*[·•|｜]\s*", str(cand.get("name") or cid))[0]
    segs, t0 = [], 0

    def seg(key, label, m):
        nonlocal t0
        if m is None:
            return
        segs.append({"key": key, "label": label, "start": t0, "end": t0 + m})
        t0 += m

    seg("OP", W["opener"], N["opener"]["min"])
    for t in N["themes"]:
        seg(t["n"], "%s %s" % (t["n"], re.split(r"[：:]", t["title"])[0]), t["min"])
    seg("W", W["wrap"], N["wrap"]["min"])
    minutes = t0 or None

    # ---------- before
    parts = ['<section id="before"><div class="phase"><h2>%s</h2><span class="hint">%s</span></div>' % (esc(W["before"]), esc(W["before_hint"]))]
    head = '<p class="lead"><b>%s</b>%s%s</p>' % (esc(short), W["colon"], esc(N["summary"])) if N["summary"] else '<p class="lead"><b>%s</b></p>' % esc(cand.get("name") or short)
    folds = ""
    if cand.get("ruler"):
        folds += _fold("fold", esc(W["ruler_h"]), "<p>%s</p>" % fmt(cand["ruler"]))
    if cand.get("profile"):
        folds += _fold("fold", esc(W["profile_h"]), "<p>%s</p>" % fmt(cand["profile"]))
    parts.append('<div class="panel">%s%s</div>' % (head, folds))
    if N["decide"]:
        parts.append('<div class="panel"><h3 class="s2">%s</h3><ol class="plain">%s</ol></div>'
                     % (esc(W["decide_h"]), "".join("<li>%s</li>" % esc(x) for x in N["decide"])))
    vrows = "".join('<tr><td>%s</td><td class="num">%s</td></tr>' % (esc(a), esc(b)) for a, b in N["verify"])
    verify = ('<div class="panel"><h3 class="s2">%s</h3><table class="t"><tr><th>%s</th><th>%s</th></tr>%s</table></div>'
              % (esc(W["verify_h"]), esc(W["item"]), esc(W["when"]), vrows)) if N["verify"] else ""
    if segs:
        rows = []
        prio_of = {t["n"]: t["prio"] for t in N["themes"]}
        for g in segs:
            pr = prio_of.get(g["key"])
            tag = '<span class="tag %s">%s</span>' % (pr, esc(W["prio"][pr])) if pr else "—"
            rows.append('<tr><td class="num">%d–%d</td><td>%s</td><td class="num">%d%s</td><td>%s</td></tr>'
                        % (g["start"], g["end"], esc(g["label"]), g["end"] - g["start"], esc(W["min"]), tag))
        cols = "".join("<th>%s</th>" % esc(c) for c in W["time_cols"])
        timing = '<table class="t"><tr>%s</tr>%s</table>' % (cols, "".join(rows))
        title_t = "%s（%d%s）" % (W["time_h"], minutes, W["min"].strip()) if W is T["zh"] else "%s (%d min)" % (W["time_h"], minutes)
    else:
        timing, title_t = '<p class="small">%s</p>' % esc(W["untimed"]), W["time_h"]
    tnote = '<p class="small">%s</p>' % esc(N["time_note"]) if N["time_note"] else ""
    plan_panel = '<div class="panel"><h3 class="s2">%s</h3>%s%s</div>' % (esc(title_t), timing, tnote)
    parts.append('<div class="grid2">%s%s</div>' % (verify or "<div></div>", plan_panel))
    dim_line = W["sep"].join("%s %s%s%s%s" % (d["id"], d["name"], "（" if W is T["zh"] else " (", W["kind"][d["kind"]], "）" if W is T["zh"] else ")") for d in N["dims"])
    notes = _ul(N["notes"]) if N["notes"] else ""
    parts.append('<div class="grid2"><div class="panel"><h3 class="s2">%s</h3>%s</div><div class="panel"><h3 class="s2">%s</h3>%s'
                 '<p class="small dl"><b>%s%s</b>%s%s</p></div></div>'
                 % (esc(W["strengths_h"]), _ul(N["strengths"]), esc(W["notes_h"]), notes,
                    esc(W["dims_line"]), W["colon"], esc(dim_line), esc(W["dims_tail"])))
    parts.append(_resume_block(cand, outdir, W))
    parts.append("</section>")
    before = "".join(parts)

    # ---------- during
    th_data = []
    op = N["opener"]
    d = ['<section id="during"><div class="phase"><h2>%s</h2><span class="hint">%s</span></div>' % (esc(W["during"]), esc(W["during_hint"]))]
    op_min = '<span class="tag">%d%s</span>' % (op["min"], esc(W["min"])) if op["min"] is not None else ""
    op_title = re.sub(r"^(开场|Opener)[：:]\s*", "", op["title"])
    d.append("".join([
        '<div class="qb" data-seg="OP"><h3><span class="qn">%s</span>%s%s<span class="sum" id="sum-OP"></span></h3>' % (esc(W["opener"]), esc(op_title), op_min),
        '<ol class="plain">%s</ol>' % "".join("<li>%s</li>" % esc(q) for q in op["questions"]),
        ('<div class="lbl">%s</div>%s' % (W["listen_h"], _checks("OP:S0", op["listen"]))) if op["listen"] else "",
        ('<p class="expect"><b>%s%s</b>%s</p>' % (esc(W["expect"]), W["colon"], esc(op["expect"]))) if op["expect"] else "",
        '<div class="tail">', ('<div class="lbl">%s</div>%s' % (esc(W["flags_h"]), _checks("OP", op["flags"], True))) if op["flags"] else "",
        '<textarea class="note" data-k="note:OP" placeholder="%s"></textarea></div></div>' % esc(W["note_short"]),
    ]))
    th_data.append({"n": "OP", "title": W["opener"], "must": True, "transferIdx": -1,
                    "subs": [{"label": W["opener"], "optional": False, "listen": op["listen"]}], "flags": op["flags"]})
    dmap = {x["id"]: x for x in N["dims"]}
    for t in N["themes"]:
        tags = '<span class="tag %s">%s</span>' % (t["prio"], esc(W["prio"][t["prio"]]))
        if t["min"] is not None:
            tags += '<span class="tag">%d%s</span>' % (t["min"], esc(W["min"]))
        tags += "".join('<span class="tag dim">%s %s</span>' % (x, esc(dmap[x]["name"])) for x in t["dims"])
        sub_html, sub_data = [], []
        for i, s in enumerate(t["subs"]):
            optional = s["kind"] not in ("L1", "L2", "L3")
            head = '<span class="lv%s">%s</span>' % (" ask" if optional else "", esc(s["label"]))
            if optional:
                head += '<span class="cond">%s</span><label class="askd"><input type="checkbox" data-k="%s:S%d:A">%s</label>' % (
                    esc(s["when"]), t["n"], i, esc(W["asked"]))
            listen = ('<div class="lbl">%s</div>%s' % (W["listen_h"], _checks("%s:S%d" % (t["n"], i), s["listen"]))) if s["listen"] else ""
            ans = _fold("ans", esc(W["answer_h"]), fmt(s["a"])) if s["a"] else ""
            sub_html.append('<div class="sq"><div class="sqh">%s</div><p class="mainq">%s</p>%s%s</div>' % (head, esc(s["q"]), listen, ans))
            short_label = s["label"].split(" ")[0] if re.match(r"^L\d", s["label"]) else s["label"]
            sub_data.append({"label": short_label, "optional": optional, "listen": s["listen"]})
        focus = '<p class="focus">%s%s%s</p>' % (esc(W["focus"]), W["colon"], esc(t["focus"])) if t["focus"] else ""
        anchor = _fold("fold", esc(W["anchor_h"]), '<div class="anchor">%s</div>' % esc(t["anchor"])) if t["anchor"] else ""
        flags = ('<div class="lbl">%s</div>%s' % (esc(W["flags_h"]), _checks(t["n"], t["flags"], True))) if t["flags"] else ""
        fb = '<p class="fb">%s</p>' % esc(t["fallback"]) if t["fallback"] else ""
        if t["good"]:  # older payloads keep their strong-answer notes, folded under the questions
            sub_html.append(_fold("ans", esc(W["good_h"]), '<ul class="plain">%s</ul>' % "".join("<li>%s</li>" % fmt(x) for x in t["good"])))
        d.append("".join([
            '<div class="qb" id="%s" data-seg="%s"><h3><span class="qn">%s</span>%s%s<span class="sum" id="sum-%s"></span></h3>'
            % (esc(t["n"]), esc(t["n"]), esc(t["n"]), esc(t["title"]), tags, esc(t["n"])),
            focus, anchor, "".join(sub_html),
            '<div class="tail">%s%s<textarea class="note" data-k="note:%s" placeholder="%s"></textarea></div></div>'
            % (flags, fb, esc(t["n"]), esc(W["note_ph"])),
        ]))
        th_data.append({"n": t["n"], "title": t["title"], "must": t["prio"] == "must", "transferIdx": t["tidx"],
                        "subs": sub_data, "flags": t["flags"]})
    if N["wrap"]["items"]:
        items = []
        for i, it in enumerate(N["wrap"]["items"]):
            lis = '<p class="small"><b>%s%s</b>%s</p>' % (esc(W["wrap_listen"]), W["colon"], esc(it["listen"])) if it.get("listen") else ""
            ans = _fold("ans", esc(W["answer_h"]), fmt(it["answer"])) if it.get("answer") else ""
            items.append('<div class="sq"><div class="sqh"><span class="lv ask">%s</span><label class="askd"><input type="checkbox" data-k="W:S%d:A">%s</label></div>'
                         '<p class="mainq">%s</p>%s%s</div>' % (esc(it.get("tag", "")), i, esc(W["asked"]), esc(it["q"]), lis, ans))
        wmin = '<span class="tag">%d%s</span>' % (N["wrap"]["min"], esc(W["min"])) if N["wrap"]["min"] is not None else ""
        d.append('<div class="qb" data-seg="W"><h3><span class="qn">%s</span>%s%s</h3>%s<textarea class="note" data-k="note:W" placeholder="%s"></textarea></div>'
                 % (esc(W["wrap"]), esc(W["wrap_h"]), wmin, "".join(items), esc(W["note_short"])))
    d.append("</section>")
    during = "".join(d)

    # ---------- after
    rows = []
    for x in N["dims"]:
        anchors = "".join('<label><input type="radio" name="%s" value="%d" data-k="score:%s"><b>%d</b><span>%s</span></label>'
                          % (esc(x["id"]), s, esc(x["id"]), s, esc(x["anchors"][s])) for s in (4, 3, 2, 1))
        rows.append('<div class="dimrow"><div class="dimh"><b>%s %s</b><span class="tag %s">%s</span><span class="small">%s%s%s</span></div>'
                    '<div class="auto" id="auto-%s"></div><div class="anchors">%s</div>'
                    '<textarea class="note" data-k="ev:%s" placeholder="%s"></textarea></div>'
                    % (esc(x["id"]), esc(x["name"]), x["kind"], esc(W["kind"][x["kind"]]), esc(W["from_h"]), W["colon"],
                       esc(W["list"].join(x["from"])), esc(x["id"]), anchors, esc(x["id"]), esc(W["ev_ph"])))
    toggle = ('<label class="toggle"><input type="checkbox" data-k="toggle"><span>%s</span></label>' % esc(N["toggle"]["label"])) if N["toggle"] else ""
    rp = W["rule_parts"]
    rule = "%s%s%s%s%s%s%s" % (rp[0], esc(N["rule"]["pass"]), rp[1], esc(N["rule"]["fail"]), rp[2], esc(N["rule"]["hold"]), rp[3])
    nxt = '<div class="panel"><h3 class="s2">%s</h3>%s</div>' % (esc(W["next_h"]), _ul(N["next"])) if N["next"] else ""
    after = "".join([
        '<section id="after"><div class="phase"><h2>%s</h2><span class="hint">%s</span></div>' % (esc(W["after"]), esc(W["after_hint"])),
        '<div class="panel">%s%s</div>' % (toggle, "".join(rows)),
        '<div class="panel"><h3 class="s2">%s</h3><p class="small">%s%s%s</p><p class="suggest" id="suggest"></p><div class="verdict">%s</div></div>'
        % (esc(W["verdict_h"]), esc(W["rule_h"]), W["colon"], rule,
           "".join('<label><input type="radio" name="verdict" value="%s" data-k="verdict"> %s</label>' % (esc(v), esc(v)) for v in W["verdicts"])),
        nxt,
        '<div class="panel"><h3 class="s2">%s</h3><div class="tools2"><button class="btn primary" id="draftBtn">%s</button>'
        '<button class="btn" id="copyBtn">%s</button><button class="btn" id="clearBtn">%s</button></div>'
        '<textarea class="memo" id="memo" data-k="memo" placeholder="%s"></textarea><p class="small">%s</p></div></section>'
        % (esc(W["memo_h"]), esc(W["draft"]), esc(W["copy"]), esc(W["clear"]), esc(W["memo_ph"]), esc(W["local"])),
    ])

    data = {
        "cand": short, "role": N["role"], "minutes": minutes, "segs": segs, "themes": th_data, "t": W["js"],
        "dims": [{"id": x["id"], "name": x["name"], "kind": x["kind"], "kindLabel": W["kind"][x["kind"]],
                  "transfer": any(("情境" in f) or ("ituational" in f) for f in x["from"]),
                  "qs": [{W["gate_from"][0]: "OP", W["gate_from"][1]: "W", "开场": "OP", "收尾": "W"}.get(f, f) for f in x["from"]]}
                 for x in N["dims"]],
        "toggle": N["toggle"], "next": N["next"],
    }
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    title = "%s · %s" % (W["title"], short)
    sub_bits = [b for b in (N["role"], ("%d%s" % (minutes, W["min"].strip())) if minutes else "", meta.get("date") or "") if b]
    tools = ('<span class="clock" id="clock">00:00</span><span class="seg" id="seg"></span>'
             '<button class="btn" id="timerBtn">%s</button><button class="btn" id="expandBtn">%s</button>'
             '<button class="btn primary" id="printBtn" title="%s">%s</button>'
             % (esc(W["timer"]), esc(W["expand"]), esc(W["print_tip"]), esc(W["print"])))
    key = "%s:%s" % (slug, cid)
    return "".join([
        "<!doctype html>\n<html lang=\"%s\">\n<head>\n<meta charset=\"utf-8\">\n" % esc(lang or "zh"),
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n<title>%s</title>\n" % esc(title),
        "<style>\n", pages.css(), CSS, "</style>\n</head>\n<body data-key=\"%s\">\n" % esc(key),
        "<header class=\"top\"><div class=\"inner\"><h1>%s</h1><div class=\"sub\">%s</div>" % (esc(title), esc("｜".join(sub_bits) if W is T["zh"] else " | ".join(sub_bits))),
        "<nav class=\"bar noprint\"><span class=\"tools\">%s</span></nav></div></header>\n" % tools,
        "<main class=\"wrap\">\n", before, during, after, "\n</main>\n",
        "<footer class=\"foot\"><div class=\"brand\">resume-grill</div></footer>\n",
        "<script type=\"application/json\" id=\"kitdata\">", blob, "</script>\n<script>", JS, "</script>\n</body>\n</html>\n",
    ])
