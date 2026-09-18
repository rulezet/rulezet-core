# Workspace — planning space

This folder tracks where the Workspace feature is today and where we want to
take it. One markdown file per topic, so this can grow without turning into
a single unmanageable document.

## Files

- [`current_state.md`](current_state.md) — what exists today: routes, data
  model, backend logic, UI/UX, known gaps. Read this first — every future
  proposal in this folder should build on it, not repeat it.
- [`connector_research.md`](connector_research.md) — how the real
  detection-rule ecosystem (YARA, Sigma, Suricata, Wazuh) actually gets
  consumed by tools today, and what that implies for a Workspace Connector.
- [`roadmap_ideas.md`](roadmap_ideas.md) — brainstormed feature ideas and
  suggested sequencing (Suricata pull connector first, then push
  connectors, draft rules, Sigma, publish checklist, test history,
  activity feed). Nothing here is decided or built — it's the running
  memory of what's been discussed.

*(more files land here as we flesh out each direction into an actual spec
— drafts, collaboration, etc.)*

## Why this folder exists

Workspace started as a simple personal "folder of rules" feature and is
becoming a priority: the goal is for it to become the natural starting point
of a user's workflow on Rulezet (draft → test → publish), not just a place
things get filed after the fact. This folder is the working memory for that
effort across sessions.
