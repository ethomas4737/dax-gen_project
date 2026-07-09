# dax-gen_project

Curate three independent, publicly-available biological sequence-interaction datasets — a protein-protein interaction (PPI) benchmark, an antibody-antigen binding benchmark, and a viral antigenic-evolution dataset — keeping them separate, and produce descriptive EDA for each. See [spec/spec.md](spec/spec.md) for the full goal, data sources, and Phase 1 deliverables/acceptance criteria. The downstream modeling task is deliberately not yet decided; this phase is a data-foundation and characterization step.

## Datasets (Phase 1)

- **PPI** — [D-SCRIPT](https://github.com/samsledje/D-SCRIPT) repo-included pair files (human/mouse/fly/yeast/worm/ecoli), excluding COVID/antibody data.
- **Antibody-antigen** — [AVIDa-hIL6](https://huggingface.co/datasets/COGNANO/AVIDa-hIL6) + [AVIDa-hTNFa](https://huggingface.co/datasets/COGNANO/AVIDa-hTNFa) (COGNANO), excluding AVIDa-SARS-CoV-2.
- **Viral antigenic evolution** — [MLAEP](https://github.com/WHan-alter/MLAEP) repo-included preprocessed SARS-CoV-2 files (raw GISAID corpus deferred).

## Harness

This is a DAX project repo. The harness (manifesto, agent configs, global user-guidance) lives at the sibling `../dax/` directory. See `../dax/MANIFESTO.md` for the governing Constitution + Legislation, and `../dax/README.md` for the general DAX tutorial.

## Session start

Invoke `/rohit-dax-session` (or it auto-triggers when you reference DAX work in this directory). It boots the orchestrator: loads the manifesto + guidance + spec + plan + session-handoff + journal tail, runs a DCC preflight, reports state, and waits for instruction (Manifesto Article 1 — human sovereignty; no auto-execution).

## Folder structure

```
dax-gen_project/
├── README.md
├── CLAUDE.md
├── .gitignore
├── spec/spec.md         <- project intent: goal, data sources, deliverables, acceptance criteria
├── src/                 <- working code
│   └── spikes/          <- exploratory / study code (Article 6)
├── qa/                  <- tests + validation
├── reading/              <- cached papers, lit notes
├── docs/                 <- drafts, writeups, EDA reports/figures
├── logs/                 <- execution logs (gitignored except .gitkeep)
├── dax-state/            <- plans, journal, decisions, run-notes — the audit trail
│   ├── README.md
│   ├── session-handoff.md
│   ├── journal.md
│   ├── decisions.md
│   ├── plan-phase1.md
│   └── pinned-dax-sha.txt
├── user-guidance/        <- project-specific durable preferences
├── data/                 <- *NOT tracked* — gitignored locally; symlinked on DCC
├── runs/                 <- *NOT tracked*
└── rawdata/              <- *NOT tracked* — the three curated datasets land here
```

`data/`, `runs/`, `rawdata/` are environment-local: gitignored here, symlinked into shared lab storage on DCC. They never round-trip through git.

## Reference

- **[../dax/MANIFESTO.md](../dax/MANIFESTO.md)** — Constitution (Articles 1–9) + Legislation (Sections 1–6).
- **[../dax/phase-lifecycle.md](../dax/phase-lifecycle.md)** — open/during/close protocol per phase.
- **[dax-state/README.md](dax-state/README.md)** — index of the audit-trail files.
