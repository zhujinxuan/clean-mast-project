---
name: post-edit-verification-gates
description: "After Python code edits, run ty check and ruff fix before committing or yielding"
condition: "Committed:|Done\\.|\\byield\\b|\\byielding\\b"
scope: "text"
---

After any Python file edit, ALWAYS run verification before committing or yielding to user:

1. `uv run ty check packages/<pkg>` — type check
2. `uv run ruff check packages/<pkg> --fix` — auto-fix lint
3. `uv run ruff check packages/<pkg>` — verify clean

Only proceed to commit or yield once all three pass. If any step fails, fix errors first.

Do NOT wait for the user to ask for these checks. They are mandatory after every code change session.