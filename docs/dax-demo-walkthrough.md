# dax-demo walkthrough

## What this is

`dax-demo` is a **bootstrappable skeleton** for a new DAX project in Rohit's `~/work/rohitsinghlab/repos/` layout. The folder structure, file headers, and dax-state schema mirror `dax-peizhou-collab` (the canonical fully-worked DAX project) but every content slot is empty.

The intended use is `cp -r dax-demo dax-<your-project>`, followed by a quick bootstrap sequence (below) and then writing the Phase 1 spec.

This walkthrough does **not** re-explain the DAX harness conventions — those live in `../dax/MANIFESTO.md` (Constitution + Legislation), `../dax/phase-lifecycle.md`, `../dax/agent-configs/run-note-template.md`, and `../dax/agent-configs/promotion-rules.md`. The orchestrator loads them at session start; this walkthrough only describes the **project-side** patterns and how the project relates to the harness + the relevant Claude Code skills.

## Prerequisite — the harness must be present

A DAX project assumes a sibling `dax/` repo containing the manifesto, agent configs, and global user-guidance:

```
~/work/rohitsinghlab/repos/
├── dax/                # harness (clone first)
├── dax-demo/           # this template
├── dax-peizhou-collab/ # exemplar (look here when in doubt)
└── dax-<your-project>/ # what you'll create
```

If `../dax/` is missing when you start a session, the orchestrator (`/rohit-dax-session`) halts immediately with a clear error. The harness is a hard dependency. Article 2 of the manifesto: human intent lives in visible artifacts — without the harness, there are no artifacts to load.

## Bootstrap

The canonical bootstrap lives in **[`../../dax/README.md § Bootstrapping a new project`](../../dax/README.md#bootstrapping-a-new-project)** — clone the template, init git + push to GitHub, launch Claude with `--add-dir <ai-utils>`, set `/effort max`, invoke `/rohit-dax-session`. Short form for context:

```bash
cd ~/work/<you>/repos/
cp -r dax-demo dax-<project>
cd dax-<project>
git init -b main && git add . && git commit -m "init from dax-demo template"
gh repo create <your-org>/dax-<project> --public --source=. --push   # or git remote add + git push

claude --dangerously-skip-permissions --add-dir ~/work/<you>/repos/ai-utils
# In Claude:
#   /effort max
#   /rohit-dax-session
```

### Let DAX rewrite the placeholders

Once `/rohit-dax-session` has booted and reported state, ask the orchestrator to do the placeholder rewrites. This is the path the rest of the harness assumes — you'll be talking to DAX about your project anyway, so let it own the mechanical boilerplate substitution. A concrete sequence:

1. **Rewrite the spec.** Tell DAX what the project is, in your own words, with whatever context you have. Example:

   > *"Rewrite `spec/spec.md` for a project about &lt;your goal in 1–3 sentences&gt;. Background: &lt;a paragraph or three — paste collaborator emails, paper abstracts, prior work links; DAX will weave them in&gt;. Inputs we'll use: &lt;data sources, with paths or URLs if known&gt;. Phase 1 deliverables I have in mind: &lt;bullets, however rough&gt;. Open questions: &lt;bullets&gt;. Use the front-matter and sections from the template; we'll be append-only at section granularity going forward."*

   The orchestrator will either dispatch the spec-writer subagent or (for a small project) write the spec inline. When the draft comes back, **read it carefully** — the spec is the load-bearing artifact for everything downstream. Iterate via comments and redirects until it reflects what you actually want.

2. **Update `README.md` + `CLAUDE.md` for the new project.**

   > *"Update `README.md` and `CLAUDE.md` for the project name `dax-<your-project>` and the goal we just wrote into the spec. Drop the dax-demo-specific framing in `README.md` — this isn't a template anymore. Keep the operational protocol in `CLAUDE.md` intact; only the project-name references and the project-description should change."*

3. **Replace the `YYYY-MM-DD` placeholders + bring `dax-state/` to life.**

   > *"Replace the `YYYY-MM-DD` placeholders in `dax-state/session-handoff.md`, `dax-state/journal.md`, and `dax-state/decisions.md` with today's date. Update the `Current position` and `Next action` sections of `session-handoff.md` to reflect the actual project state (spec just drafted, no phase open yet)."*

4. **Refresh the pinned harness SHA.**

   > *"Refresh `dax-state/pinned-dax-sha.txt` to the current `../dax/` HEAD."*

   (Or run it yourself: `git -C ../dax rev-parse HEAD > dax-state/pinned-dax-sha.txt`.)

5. **Retire this walkthrough.**

   > *"Rename `docs/walkthrough.md` → `docs/dax-demo-walkthrough.md` so future readers know it's about the dax-demo template, not this project. Or delete it — the conventions it documents are also referenced from the harness."*

6. **Commit + push.**

   > *"Commit and push. Use a sensible subject line referencing the project init."*

After this sequence you have a working DAX project: spec reflecting your goal, project-correct README + CLAUDE.md, dated and current `dax-state/`, pinned harness SHA, all on GitHub. The next action is to **open Phase 1** — draft `dax-state/plan-phase1.md`, surface to the human, wait for approval (Article 1), then execute. Don't draft the plan until the spec is approved.

A few patterns that help when iterating with DAX during bootstrap:

- **Paste raw context generously.** The orchestrator handles long context well. If you have a project document, an email thread with a collaborator, a paper abstract, a brain-dump of what you want to do — paste it in. Trying to summarize before you paste loses information; DAX will do the summarization for the spec.
- **Ask the orchestrator to surface its plan before executing.** Per Article 1 it should already do this, but if you ask "show me what you're about to change and where," you'll get a clean diff-style preview.
- **Verify before commit.** After DAX rewrites the spec / README / CLAUDE.md / dax-state, ask "show me a git diff" or "summarize what changed in each file." Sign off explicitly before "commit and push."
- **One-shot rewrites are fine for a fresh template.** The spec is going to be heavily revised once the project gets real; the first version just needs to be coherent enough to plan Phase 1 against. Don't over-engineer the bootstrap.

### Manual / sed-based alternative

If you want to do the placeholder substitution without launching Claude first (scripting the bootstrap, or saving tokens on a mechanical find/replace), the path is:

```bash
cd dax-<project>
grep -rl 'dax-demo\|<project\|<projname\|YYYY-MM-DD' \
    README.md CLAUDE.md spec/ dax-state/ user-guidance/ docs/ \
    | xargs sed -i \
        -e "s/dax-demo/dax-<project>/g" \
        -e "s/<projname>/dax-<project>/g" \
        -e "s/<project-name>/dax-<project>/g" \
        -e "s/YYYY-MM-DD/$(date -I)/g"
git -C ../dax rev-parse HEAD > dax-state/pinned-dax-sha.txt
rm docs/walkthrough.md   # or rename to docs/dax-demo-walkthrough.md
```

Eyeball the diff before committing — the sed will also touch some commentary blocks (in `CLAUDE.md`, this walkthrough, `spec/spec.md`'s commentary) that you may want to keep as-is. The let-DAX approach above is friendlier precisely because the orchestrator can be told what to preserve.

## Session start (every session)

When you open Claude Code in this project's working directory, invoke `/rohit-dax-session` (or the harness will auto-invoke when you reference dax work). That skill is the kernel boot — it:

1. Locates the project root (the nearest ancestor `dax-*` directory).
2. Verifies `../dax/MANIFESTO.md` exists. Halts loudly if not.
3. Reads the manifesto + `../dax/user-guidance/*` + `./user-guidance/*` + the session-handoff + the spec/plan front-matter + the journal tail.
4. Runs a DCC preflight (mount, SSH master, GPU allocation status).
5. Reports the state of both the WSL side and the DCC side.
6. Stops and waits for instruction. **It does not auto-execute** — Article 1 (human sovereignty) says the human picks the next action.

The skill subsumes the base Claude Code `while(1)` loop into the orchestrator's `while(1)`. For the rest of the session, Claude is in orchestrator mode — dispatching subagents (instruction-interpreter, spec-writer, architect, executor, qa-executor, reviewer) as warranted, with continuous session-hygiene rules (passive handoff sync after material work blocks; idle-checkpoint prompt at the start of each new user turn if more than ~30 minutes have passed since the last sync).

## Skill ecosystem

DAX projects rely on a handful of project-shape-aware Claude Code skills. None of these are mandatory in the manifesto sense — they're operational ergonomics. But for projects that fit, invoking them saves a lot of reinventing.

| Skill | When it fires | What it does |
|---|---|---|
| **`rohit-dax-session`** | Session start in a `dax-*` directory; `/rohit-dax-session`. | Boots the orchestrator (the above). |
| **`rohit-dcc-workflow`** | Working on DCC from WSL via the `dcc`/`dcc-gpu` shell wrappers + SSHFS mount at `~/dcc/`. | Path-translation, allocation discipline, `bash -lc` invocation pattern, "don't auto-start GPU" rule. |
| **`rohit-dcc-onnode`** | Claude is running ON DCC itself (login or compute node), not from WSL. | Direct SLURM; lab filesystem map; login-vs-compute etiquette; tenant-env conventions. |
| **`rohit-precise-workflow`** | The project uses PRECISE (virtual screening) and/or Uni-Dock re-docking. | Env activation; the 4 PRECISE subcommands + staging pattern + HF cache caveat; sbatch wrapper template; cluster-level filter on `code`; Meeko prep; Uni-Dock invocation; PyMOL rendering. |
| **`pymol-visualization`** | Any molecular visualization task (publication-quality figures). | PyMOL ray-tracing, surface styles, scene composition. Complementary to the PRECISE-skill's pose-rendering style for paper figures. |

The DCC-onnode and PRECISE skills are the two new additions that turn a generic dax-* project into a Singh-Lab-on-DCC-flavored project. If your project doesn't touch DCC, skip both. If it touches DCC but doesn't use PRECISE, take the DCC pair only. If it does both: all four skills in active rotation, with the orchestrator dispatching subagents that themselves invoke the relevant skill at their decision points.

To add a project-specific reference to one of these skills, edit `CLAUDE.md` § Relevant skills and/or `dax-state/session-handoff.md` § Recovery recipe to mention the canonical invocation pattern.

## Folder semantics

After bootstrap, the project tree looks like this. The WSL side has the small / git-tracked content; the DCC side has the large / environment-local content. The same directory names appear on both sides — but on DCC, `data/`, `runs/`, and `rawdata/` are symlinks into shared lab storage.

```
~/work/rohitsinghlab/repos/dax-<project>/   (WSL — git-tracked unless noted)
├── README.md
├── CLAUDE.md
├── .gitignore
├── spec/                       # spec/spec.md is the project intent
├── src/                        # working code
│   └── spikes/                 # exploratory code per Article 6
├── qa/                         # tests + validation
├── reading/                    # cached papers, lit notes
├── docs/                       # drafts, writeups, figures
│   └── handoffs/               # collaborator-facing packages (gitignored bodies)
├── logs/                       # execution logs (gitignored except .gitkeep)
├── dax-state/                  # plans, journal, decisions, run-notes, QA
├── user-guidance/              # project-specific durable preferences
├── data/                       # *NOT tracked* — gitignored on WSL; symlinked on DCC
├── runs/                       # *NOT tracked*
└── rawdata/                    # *NOT tracked* (DCC-only symlink to shared lab raw data)
```

On DCC, after `CREATENEWPROJECT dax-<project>` (Rohit's setup command), the equivalent tree at `~/projects/dax-<project>/` has:

```
~/projects/dax-<project>/                   (DCC)
├── src/ qa/ spec/ dax-state/ user-guidance/  # real dirs, git-tracked
├── data/    -> /hpc/group/singhlab/user/<netid>/projects/dax-<project>/data
├── runs/    -> /hpc/group/singhlab/user/<netid>/projects/dax-<project>/runs
└── rawdata/ -> /hpc/group/singhlab/rawdata
```

The symlinks resolve transparently. `ls ~/projects/dax-<project>/runs/` reads from the lab fileserver. Read large files (checkpoints, big tensors, screen outputs) via `dcc-gpu python -c '...'` instead of through the WSL SSHFS mount — SSHFS round-trips each stat, and big sequential reads are slow.

## The `dax-state/` directory

This is the project's audit trail. See `dax-state/README.md` for the canonical index; the short version:

| File | What it answers |
|---|---|
| `session-handoff.md` | "If you Ctrl-D right now, what does the next session need to know?" |
| `journal.md` | "What happened, in order?" |
| `decisions.md` | "What did I decide without asking the human, and why?" |
| `plan-phase{N}.md` | "What are the steps of the current phase, and where am I in them?" |
| `architecture-phase{N}.md` (optional) | "What structural decisions did the architect make for this phase?" |
| `runs/<step>.md` | "Exactly what was run, with what args, producing what files, with what observed behavior?" |
| `qa/<step>.md` | "Did the step's outputs satisfy the spec, tested independently?" |
| `pinned-dax-sha.txt` | "Which harness SHA was this project bootstrapped against?" |

**Read order on resume:** `session-handoff.md` → last 20 rows of `journal.md` → active plan → `decisions.md` only if session-handoff references an open decision.

**Update order on step completion:** plan Status/Outcome cells → journal row → `decisions.md` if relevant → `session-handoff.md` rewrite → commit `[<step-id>] <short action>`. The CLAUDE.md "Operational protocol for executing steps" section spells this out.

**Session-handoff hard cap: 120 lines.** Anything historical migrates to per-phase run-notes / decisions index. If `session-handoff.md` starts growing, the cure is "rewrite the cursor," not "patch in another section" — see Legislation §3.

## Per-step lifecycle

The harness defines this in `../dax/phase-lifecycle.md` and the project's CLAUDE.md mirrors it. Every numbered plan step goes through:

1. **Before start.** Read the role config (`../dax/agent-configs/<role>.md`). Mark plan row Status = `in progress`. DCC preflight if applicable.
2. **During.** Log every dispatch + cost as a single journal row. Log any autonomous decision to `decisions.md`. Write the run-note as you go, using the template at `../dax/agent-configs/run-note-template.md`.
3. **On completion (or block).** Update plan Status + Outcome cells. Append journal row. Rewrite affected `session-handoff.md` sections. Commit with subject `[<step-id>] <short action>`. If the step produced something that warrants human verification (not just QA adversarial pass — actual scientific output), ask DAX to refactor + produce a notebook. The clean code is the verification artifact; the QA pass is necessary but not sufficient.

The Outcome cell convention: `done — see runs/<step>.md`, `blocked — <one-line reason>`, or `partial — <one-line note>`. ≤80 chars. The plan is a cursor + index, not the narrative — the narrative belongs in the run-note.

## Phase lifecycle

Phases are coherent blocks of work toward a deliverable. Most projects are 2–6 phases. A phase has:

- A **spec section** in `spec/spec.md`.
- A **plan** at `dax-state/plan-phase{N}.md`.
- **Run-notes per step** under `dax-state/runs/phase{N}-*.md`.
- **Spike code** under `src/spikes/phase{N}/` during execution.
- A **phase-summary run-note** at `dax-state/runs/phase{N}-summary.md` at close.

**Opening a phase.** Spec-writer (or orchestrator inline for a small task) writes the spec section. Architect decides whether to write a separate `architecture-phase{N}.md` (threshold: >5 plan rows OR new tools/coord-systems). Orchestrator writes `plan-phase{N}.md`. Present to human. **Wait for approval** (Article 1) before any execution.

**Closing a phase.** Communicator pass (if the phase produces a verifiable / shareable artifact — see `../dax/agent-configs/communicator.md`). Spike → src promotion pass per `../dax/agent-configs/promotion-rules.md`. Phase-summary run-note. `decisions.md` index update (which entries remain load-bearing). `session-handoff.md` rewrite (phase narrative migrates out of the cursor). Commit `[phase{N}-done] <short>`. Push.

**Smaller-than-a-phase work** (one-shot fixes, handoffs, follow-ups) collapses the lifecycle: one task, one journal row, one run-note, one commit; no plan-phase file, no promotion pass.

## Your first project — worked sequence

Concretely, the first few hours of a new project look like this:

1. **Bootstrap** (5–10 min). Follow the **Bootstrap** section above: `cp -r dax-demo dax-<project>`; init git + push to GitHub; launch Claude with `--add-dir <ai-utils>`; let DAX rewrite the placeholders (spec, README, CLAUDE.md, dax-state dates) per the example prompts; commit + push.
2. **Open Claude Code** in the new directory. Invoke `/rohit-dax-session`. Confirm it loads cleanly and reports "Phase: None. Spec not yet drafted."
3. **Write the Phase 1 spec.** Either ask the orchestrator to dispatch the spec-writer subagent, or write it inline if the project is small. The spec.md template has every section you need; replace placeholder content with real content. Append-only at section granularity once Phase 1 is in flight.
4. **Surface the spec to the human.** Article 1. Iterate until approved.
5. **Open Phase 1.** The orchestrator (or the architect if dispatched) writes `dax-state/plan-phase1.md` with the step table. Decide if `architecture-phase1.md` is warranted (threshold: >5 plan rows OR new tools).
6. **Present the plan to the human.** Wait for approval.
7. **Execute step 0** (typically DCC bringup / repo sync / env verify). Update Status, write `runs/step0.md`, journal row, commit.
8. **Execute steps 1+ in dependency order.** For each: per-step lifecycle (above). For long-running computations, write a sbatch script and let it run detached.
9. **Verify each step — two layers:**
    - **QA (adversarial, DAX-side).** Dispatch the qa-executor against a different surface from the implementation (Article 7). QA writes `qa/<step>.md`.
    - **Human verification (after convergence).** When a step's results look right, ask the orchestrator to refactor → promote → produce a notebook (often via the communicator). Read the notebook cell by cell; re-run it. This is YOUR verification — distinct from the QA pass above; the QA pass is necessary, not sufficient.
10. **Close Phase 1.** Spike → src promotion; phase-summary; decisions index; handoff rewrite; `[phase1-done]` commit.

If your project uses PRECISE: invoke `rohit-precise-workflow` when designing screens or writing Uni-Dock code. The skill gives you the env, the CLI gotchas, the sbatch template, and the cluster-level filter design — all worked out in `dax-peizhou-collab` and captured as transferable patterns.

If your project uses DCC: invoke `rohit-dcc-workflow` for WSL-side operations (the SSHFS mount + `dcc`/`dcc-gpu` wrappers); invoke `rohit-dcc-onnode` when you're SSH'd into DCC and need direct SLURM idioms.

## Where to look when stuck

| Question | Look at |
|---|---|
| "What does a real phase plan look like?" | `dax-peizhou-collab/dax-state/plan-phase1.md`, `plan-phase2.md` |
| "What does a real spec look like?" | `dax-peizhou-collab/spec/spec.md` |
| "What does a real architecture doc look like?" | `dax-peizhou-collab/dax-state/architecture-phase1.md` |
| "What does a real run-note look like?" | `dax-peizhou-collab/dax-state/runs/precise-example.md`, `screen-PaLpxH_closed.md`, `phase2-stage1.md` |
| "What does a real decisions.md look like?" | `dax-peizhou-collab/dax-state/decisions.md` |
| "What does a sbatch wrapper for PRECISE look like?" | `dax-peizhou-collab/src/sbatch/screen.sbatch` + `submit_screens.sh` |
| "What does Uni-Dock + Meeko code look like?" | `dax-peizhou-collab/src/phase2/{dock_one.py, prep_receptor.sh}` |
| "What does a PyMOL render script for a docked pose look like?" | `dax-peizhou-collab/src/phase2/render_pose.py` |
| "What's the phase-close-out commit + summary pattern?" | `dax-peizhou-collab/dax-state/runs/phase2-close-out.md` + the `[phase2-done]` commit. |
| "How does a collaborator handoff get packaged?" | `dax-peizhou-collab/src/spikes/handoffs/` + `dax-state/runs/peizhou-handoff-2026-05-07.md` + the `user-guidance/handoff-framing.md` durable feedback file. |

The `dax-peizhou-collab` audit trail captures roughly two phases of real work end-to-end with full provenance. It's the highest-density reference for "what good DAX execution actually looks like" — when in doubt, pattern-match from there.

## What this template intentionally doesn't include

- **No DCC bootstrap script.** Rohit's `CREATENEWPROJECT` lives in his shell setup, not in the project template. Run it manually on DCC after the WSL-side bootstrap.
- **No CI / pre-commit hooks.** Most DAX projects don't need them; if yours does, add them deliberately.
- **No tests.** `qa/` is where validation lives; QA artifacts get written as the project executes, not seeded by the template.
- **No specific tooling.** The template is tool-agnostic. PRECISE, Uni-Dock, PyMOL, Concise, scanpy, scvi-tools, etc. all live inside the per-project `src/` and `src/spikes/` once chosen.

The template's job is to give you the scaffold + the conventions. The content is yours.
