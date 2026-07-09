# dax-demo

*A bootstrappable skeleton for a new DAX project — copy this directory, rename, and start.*

`dax-demo` is the template that new DAX projects are cloned from. The folder structure, file headers, and `dax-state/` schema mirror `dax-peizhou-collab` (a fully-worked exemplar) but every content slot is empty — you fill it via the orchestrator after bootstrapping.

> **New to DAX?** Read [../dax/README.md](../dax/README.md) first — that's the canonical tutorial for setting up the three sibling repos (`dax/`, `dax-demo/`, `ai-utils/`), bootstrapping a project from this template, and the philosophical shifts (verify-not-write, spike → canonical promotion, continuity-as-design-property) that make DAX different from "AI writes my code." Then come back here for what's specifically inside this template.

## Prerequisite — the harness must be a sibling

A DAX project assumes a sibling `dax/` repo containing the manifesto, agent configs, and global user-guidance:

```
~/work/<you>/repos/
├── dax/                # harness — MANIFESTO, agent-configs, user-guidance (clone first)
├── dax-demo/           # this template
├── ai-utils/           # Claude Code skills (rohit-dax-session, rohit-dcc-*, rohit-precise-workflow, …)
├── dax-peizhou-collab/ # exemplar — a fully-worked DAX project (PRECISE virtual screening)
└── dax-<your-project>/ # what you'll create from this template
```

If `../dax/` is missing when you start a session, the orchestrator halts with a clear error. The harness is a hard dependency (Manifesto Article 2 — human intent lives in visible artifacts; without the harness, there are no artifacts to load).

## Quick bootstrap

The full step-by-step lives in [../dax/README.md § Bootstrapping a new project](../dax/README.md#bootstrapping-a-new-project). Short version:

```bash
cd ~/work/<you>/repos/
cp -r dax-demo dax-<your-project>
cd dax-<your-project>
git init -b main && git add . && git commit -m "init from dax-demo template"
git remote add origin git@github.com:<your-org>/dax-<your-project>.git
git push -u origin main

claude --dangerously-skip-permissions --add-dir ~/work/<you>/repos/ai-utils
# then in Claude:
#   /effort max
#   /rohit-dax-session
# then ask the orchestrator to rewrite README.md, CLAUDE.md, spec/spec.md,
# and the YYYY-MM-DD placeholders in dax-state/ for your actual project.
# Once it looks right: "commit and push."
```

The orchestrator does the rewrites; you do the verification. That's the rhythm — see [../dax/README.md § Philosophy](../dax/README.md#philosophy-whats-different-about-working-this-way) for the longer version of why.

## What's in this template

```
dax-demo/
├── README.md            <- this file; the orchestrator rewrites it per project
├── CLAUDE.md            <- Claude Code instructions; points at ../dax/MANIFESTO.md
├── .gitignore
├── spec/spec.md         <- project spec template (front-matter + section skeletons)
├── src/                 <- working code
│   └── spikes/          <- exploratory / study code (Article 6)
├── qa/                  <- tests + validation
├── reading/             <- cached papers, lit notes
├── docs/
│   └── walkthrough.md   <- deeper reference (lifecycles, skill ecosystem, exemplar pointers)
├── logs/                <- execution logs (gitignored except .gitkeep)
├── dax-state/           <- plans, journal, decisions, run-notes, QA — the audit trail
│   ├── README.md        <- index of dax-state files
│   ├── session-handoff.md
│   ├── journal.md
│   ├── decisions.md
│   ├── plan-phase1.md
│   └── pinned-dax-sha.txt
├── user-guidance/       <- project-specific durable preferences
├── data/                <- *NOT tracked* — gitignored locally; symlinked on DCC
├── runs/                <- *NOT tracked*
└── rawdata/             <- *NOT tracked* (DCC symlink to shared lab raw data)
```

The three "NOT tracked" directories (`data/`, `runs/`, `rawdata/`) are environment-local: gitignored on your laptop, symlinked into shared lab storage on DCC (per `rohit-dcc-onnode`). They never round-trip through git.

## Deeper reference

- **[docs/walkthrough.md](docs/walkthrough.md)** — per-step lifecycle, phase lifecycle, the skill ecosystem (`rohit-dax-session`, `rohit-dcc-workflow`, `rohit-dcc-onnode`, `rohit-precise-workflow`, `pymol-visualization`), and "where to look when stuck" pointers into `dax-peizhou-collab` for what real DAX execution looks like end-to-end. Read this once you're past bootstrap.
- **[../dax/MANIFESTO.md](../dax/MANIFESTO.md)** — the Constitution (Articles 1–9) and Legislation (Sections 1–6) that govern projects. Article 1 (human sovereignty) and Article 2 (intent in visible artifacts) come up constantly.
- **[../dax/dax_philosophy.md](../dax/dax_philosophy.md)** — the longform essay on why DAX exists (Memento analogy, day-one-employee analogy, OS analogy, verification-as-the-new-bottleneck).
- **[../dax/phase-lifecycle.md](../dax/phase-lifecycle.md)** — the open/during/close protocol per phase.

After bootstrapping a new project, **rename or delete `docs/walkthrough.md`** — it's about `dax-demo`, not your project. The parts worth carrying forward (lifecycle conventions, `dax-peizhou-collab` audit-trail pointers) are also referenced from the harness; you won't lose them.

## What this template intentionally doesn't include

- **No DCC bootstrap script.** Rohit's `CREATENEWPROJECT` lives in his shell setup; run it manually on DCC after the local-side bootstrap (or write your own for your environment).
- **No CI / pre-commit hooks.** Most DAX projects don't need them; add deliberately if yours does.
- **No tests.** `qa/` is where validation lives; QA artifacts get written as the project executes, not seeded by the template.
- **No specific tooling.** The template is tool-agnostic — PRECISE, Uni-Dock, scanpy, scvi-tools, etc. all live inside the per-project `src/` and `src/spikes/` once chosen.

The template's job is to give you the scaffold + the conventions. The content is yours.
