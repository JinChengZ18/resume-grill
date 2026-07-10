#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
install.py — install the resume-grill skill into one or more agents' skills dirs.

SKILL.md is a cross-agent standard: the same skill folder works in Claude Code
(~/.claude/skills), Codex CLI (~/.codex/skills), and any other agent that reads
SKILL.md skills — no modification needed.

Usage:
  python scripts/install.py                # auto: install into every detected agent
  python scripts/install.py --claude       # -> ~/.claude/skills/resume-grill
  python scripts/install.py --codex        # -> ~/.codex/skills/resume-grill
  python scripts/install.py --all          # every known agent
  python scripts/install.py --target DIR   # -> DIR/resume-grill (any agent's skills dir)

Pure Python, cross-platform, no dependencies — no PowerShell / execution-policy hassle.
"""
import argparse, shutil, sys
from pathlib import Path

SKILL_NAME = "resume-grill"
OLD_NAME = "adversarial-interview"          # predecessor name; flagged if a stale copy lingers
REPO = Path(__file__).resolve().parent.parent
PAYLOAD = ["SKILL.md", "scripts", "templates", "reference"]
EXCLUDE = {"__pycache__", "deploy.ps1", "install.py", ".DS_Store"}

# agent home dir -> its skills dir
AGENTS = {
    "claude": Path.home() / ".claude" / "skills",
    "codex":  Path.home() / ".codex" / "skills",
}


def _ignore(_dir, names):
    return [n for n in names if n in EXCLUDE or n.endswith(".pyc")]


def install_to(skills_dir):
    dest = skills_dir / SKILL_NAME
    skills_dir.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        shutil.rmtree(dest)                 # clean re-install of our own skill dir only
    dest.mkdir()
    for item in PAYLOAD:
        src = REPO / item
        if not src.exists():
            continue
        if src.is_dir():
            shutil.copytree(src, dest / item, ignore=_ignore)
        else:
            shutil.copy2(src, dest / item)
    old = skills_dir / OLD_NAME
    note = ("  (注意：旧技能目录 %s 仍在，可手动删除)" % old) if old.exists() else ""
    return dest, note


def detect():
    return [k for k, d in AGENTS.items() if d.parent.exists()]


def main():
    ap = argparse.ArgumentParser(description="Install the resume-grill skill (cross-agent).")
    ap.add_argument("--claude", action="store_true", help="install into ~/.claude/skills")
    ap.add_argument("--codex", action="store_true", help="install into ~/.codex/skills")
    ap.add_argument("--all", action="store_true", help="install into every known agent")
    ap.add_argument("--target", help="install into this skills dir (any agent)")
    a = ap.parse_args()

    if a.target:
        targets = [Path(a.target).expanduser()]
    else:
        if a.all:
            keys = list(AGENTS)
        else:
            keys = [k for k, on in (("claude", a.claude), ("codex", a.codex)) if on]
            if not keys:
                keys = detect() or ["claude"]   # auto: detected agents, else Claude Code
        targets = [AGENTS[k] for k in keys]

    print("installing %s from %s" % (SKILL_NAME, REPO))
    for skills_dir in targets:
        try:
            dest, note = install_to(skills_dir)
            print("  installed -> %s%s" % (dest, note))
        except OSError as e:
            print("  FAILED  -> %s : %s" % (skills_dir, e), file=sys.stderr)
    print()
    print("装好了。新开一个会话，把简历拖进对话说一句「拷打这份简历」即可（多份就都拖进来）；")
    print("或对 agent 说「用 resume-grill 处理 inbox 里的简历」。")


if __name__ == "__main__":
    main()
