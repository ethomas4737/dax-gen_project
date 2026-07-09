# User Guidance (Project-Local)

Project-specific preferences and instructions. Grows as the human gives feedback during this project.

Project-local guidance overrides global (`../dax/user-guidance/`) on conflict.

Each guidance file gets YAML frontmatter:

```yaml
---
name: <short-kebab-case-slug>
description: <one-line description used to assess relevance>
type: feedback | preference | reference
---
```

The orchestrator reads everything in this directory at session start (per `CLAUDE.md` step 4).
