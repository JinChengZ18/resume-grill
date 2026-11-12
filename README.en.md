# resume-grill

[Chinese](README.md) | [English](README.en.md)

[![skills.sh](https://skills.sh/b/JinChengZ18/resume-grill)](https://skills.sh/JinChengZ18/resume-grill)

**Resume-based technical interview prep, for candidates and interviewers.** Candidates use it to grill their own resume before an interview, run a mock technical interview, and predict the follow-ups an interviewer will ask. Interviewers use it to build an interview from a candidate's resume, score answers on a printable scorecard, and check whether resume claims hold up.

```bash
npx skills add JinChengZ18/resume-grill
```

An Agent Skill that turns resumes into an interview guide, a printable scorecard, and collapsible Q&A cards. Questions form project-based themes, with follow-ups kept inside their parent theme and a spoken sample response below each question. Scoring cues are separate. For research and senior roles, discussion emphasizes significance, alternative approaches, tradeoffs, and evidence. Output language follows the resume. Runs in Claude Code, Codex, claude.ai, and other agents that read `SKILL.md`.

> This repository includes a **fully anonymized** demo resume for a fictional candidate, "Zhang San", applying for an Agent / AI Infra role with 2 years of experience. See the generated kit: [guide](examples/agent_engineer_demo/agent_engineer_demo_guide.md), [scorecard](examples/agent_engineer_demo/agent_engineer_demo_scorecard.html), and [Q&A cards](examples/agent_engineer_demo/agent_engineer_demo_qa_cards.html). Open the HTML files in a browser.



## Use Cases

- **Candidates**: grill your own resume before an interview, see where an interviewer is likely to push, and self-test with the collapsible Q&A cards so weak metrics, unclear ownership, and timeline gaps get fixed in advance.
- **Interviewers**: generate a 30/60/90-minute structured technical interview from a candidate's resume, with a model answer and scoring cues for each question and an A4 scorecard for live scoring.
- **Resume checks**: full-audit mode lists every percentage without a baseline, every vague "participated in / responsible for" claim, every skill listed without project evidence, and every overlapping timeline, without inventing doubts.

Typical requests: "grill this resume", "mock interview based on my CV", "interview questions from this resume", "full audit of this resume", or in Chinese 「拷打这份简历」「根据简历出面试题」.



## Quick Start

**1. Install once** with any of these:

| Method | Command | Notes |
| --- | --- | --- |
| skills CLI | `npx skills add JinChengZ18/resume-grill` | Installs into Claude Code, Codex, Cursor, and other agents; add `-g` for a global install |
| Claude Code plugin | `/plugin marketplace add JinChengZ18/resume-grill`, then `/plugin install resume-grill@resume-grill` | Installs as a plugin |
| Clone and install | `python scripts/install.py` | Cross-platform, no PowerShell required; copies the skill into detected agents such as Claude Code and Codex. Rerun it after changing the skill |

**2. Use it** by opening a fresh session in the agent, dragging a resume PDF into the conversation, and saying "grill this resume". For multiple candidates, drag in all resumes together. The agent ingests the files into the workspace, runs the pipeline, and returns local links to the generated kit, so you do not have to hunt through folders.

Outputs are written to `workspace/output/<slug>/`: `_qa_cards.html` for reading and self-testing, `_scorecard.html` for A4 printing and live scoring, and `_guide.md` for deeper interview prep.



## Outputs

The three files are written to the same directory, link to each other with local relative paths, and are fully self-contained. They can be opened directly via `file://`.

- **Full guide** `<slug>_guide.md`: profile, strengths, points to clarify, and coherent project themes with questions, paired sample responses, local follow-ups, and separate scoring cues.
- **Live scorecard** `<slug>_scorecard.html`: one A4 page per candidate for timed interviews, with locally saved scores. Full-audit mode may span multiple pages.
- **Q&A cards** `<slug>_qa_cards.html`: candidate tabs and collapsible responses. Technical follow-ups stay within their theme, and hiding answers keeps all questions visible.

The workflow reviews the resume, develops domain-specific topics, writes coherent themes and spoken responses, then verifies and revises them. Review covers technical accuracy, question continuity, response alignment, and evidence boundaries. Well-supported alternative approaches are welcome. Working arrangements and material checks remain separate.

The screenshots and linked examples below use the legacy format. Newly generated kits use theme-local follow-ups and paired spoken responses.

![ScreenShot_en1](./DEMO/ScreenShot_en1.png)

![ScreenShot_en2](./DEMO/ScreenShot_en2.png)



## Agent Installation

`SKILL.md` follows the cross-agent skill format. The same skill directory can be recognized by multiple agents and triggered from natural language. `install.py` installs into every detected agent by default, or into a specific target:

| Command | Target |
| --- | --- |
| `python scripts/install.py` | Automatic: all detected agents |
| `python scripts/install.py --claude` | `~/.claude/skills/resume-grill` for Claude Code / Claude.ai / Agent SDK |
| `python scripts/install.py --codex` | `~/.codex/skills/resume-grill` for Codex CLI |
| `python scripts/install.py --all` | All of the above |
| `python scripts/install.py --target <dir>` | Any agent skills directory |

After installation, open a fresh session in that agent and trigger it naturally, for example with "grill this resume". For frameworks without skill support, use the pure-script path below.



## Languages

Output language is detected by default and follows the resume: Chinese resumes produce Chinese materials, English resumes produce English materials, including the UI labels in the scorecard and cards. To force a language, ask the agent to output in English, or pass `--lang en` in script mode. Supported values are `zh`, `en`, an ISO language code, or `auto`. The UI shell has built-in Chinese and English labels. For other languages, the main content uses that language while UI labels fall back to English. To add another UI language, add an entry to `LABELS` in `scripts/render.py`.



## Interview Length & Full-Audit Mode

Specify a duration, or use the 60-minute default. The table is a coverage guide: prioritize substantive discussion over asking every question, and leave unasked items unscored.

| Length | Core questions | What changes |
| --- | --- | --- |
| 30 min | 3 (≈7′ each) | Warm-up ladder drops to 1 rung; answer keys stay tight |
| 60 min | 6 (≈8′) | Default |
| 90 min | About 9 themes (about 8 min each) | More discussion of alternatives and evidence; follow-ups remain inside their theme |

**Full-audit mode (ultra).** Say "do a full review of this resume", "audit it thoroughly", "find every weak point", or "what will I get asked", and it drops the time box and the question cap, digging out every point in the resume that an interviewer could challenge: every red flag, every percentage without a baseline, every vague "participated in / responsible for" ownership claim, every technology listed under skills but absent from the projects, every overlapping timeline, every coursework project dressed up as a "system". Typically 12-24 questions, erring on the side of more — but only for doubts that genuinely exist in the resume; it will not invent them. Interviewers use it to dig deep; candidates work through the fold-away answers on the Q&A cards and patch the holes before the interview. The switch is decided by whether you want exhaustive coverage, not by who is asking.



## Scripts / Any Framework

The analysis logic is decoupled from Claude Code's Workflow runtime. You can run the same pipeline with three script commands and get the same output structure:

```bash
python scripts/extract_pdf.py workspace/inbox/resume.pdf --out resumes.json
# Model backend: RG_LLM_PROVIDER=openai|anthropic|custom. See the header of analyze_portable.py.
RG_LLM_PROVIDER=openai python scripts/analyze_portable.py --resumes resumes.json --out payload.json
python scripts/render.py payload.json workspace/output/demo demo
```

`analyze_portable.py` only needs a structured-output callback shaped as `call_llm(system, user, schema)`. It includes OpenAI and Anthropic adapters, and can be wired to your own model. If your orchestration stack is limited, add `--single` to produce the whole payload in one model call, with slightly less depth but the same structure. The runtime-neutral four-stage contract, including stages, prompts, and JSON schemas, lives in `reference/pipeline-spec.md`. The rendering layer, `render.py` plus templates, has zero dependencies and can render any compatible `payload.json`.



## Project Structure

```text
resume-grill/
  SKILL.md                     Skill entry point: frontmatter plus instructions
  .claude-plugin/
    plugin.json                Plugin manifest for Claude Code and Anthropic's plugin directory
    marketplace.json           Single-plugin marketplace for /plugin marketplace add
  scripts/
    extract_pdf.py             Resume PDF to text
    analyze.js                 Claude Code native multi-agent Workflow engine
    analyze_portable.py        Runtime-neutral reference orchestration plus --single fallback
    render.py                  payload.json to the three-piece kit, zero dependencies, with UI i18n
    install.py                 Cross-platform installer for agent skills directories
  templates/                   Self-contained HTML templates for cards and scorecards
  reference/
    pipeline-spec.md           Runtime-neutral pipeline contract: stages, prompts, schema, language
    writing-norms.md           Output writing norms by language
  workspace/                   Local workspace, ignored by git
    inbox/  output/  BG/
```



## Privacy

It is recommended to remove any personal information from your resume to avoid potential data leakage risks associated with API service providers. `workspace/`, including resumes and generated outputs, is excluded by `.gitignore`, and `*.pdf` has an additional global ignore rule, so private resumes are not committed when publishing the repository.

While the skill runs, inputs, intermediate files, and outputs stay under `workspace/`. Apart from your agent's own model calls, the scripts make no network requests; resume text goes to a model provider only if you run `analyze_portable.py` with `RG_LLM_PROVIDER` set.



## License

MIT License
