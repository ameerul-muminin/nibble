# How we work

## Who owns what

Ownership is by **folder**, not by feature. Two people editing the same file is
where merge conflicts and bad feelings come from.

| Person | Owns | Never edits without asking |
|---|---|---|
| Backend dev | `backend/` | `frontend/` |
| Frontend dev | `frontend/`, `assets/` | `backend/` |
| Tech lead | `docs/`, `infra/`, `.github/`, reviews every PR | — |

`docs/api.md` is shared ground. Changing it needs both devs to agree first.

## Git, the short version

```bash
git checkout main
git pull                              # always start from the latest main
git checkout -b feat/upload-ui        # one branch per piece of work
# ...write code...
git add .
git commit -m "add file picker to notes card"
git push -u origin feat/upload-ui
```

Then open a pull request on GitHub. The tech lead reviews it. When CI is green
and it is approved, squash-merge it.

**Branch names:** `feat/` for new things, `fix/` for bugs, `docs/` for writing.
Lower case, dashes, no spaces.

**Commit messages:** finish the sentence "this commit will…". So
`add page numbers to source chips`, not `update` or `changes`.

**If git yells at you**, stop and ask. Do not run commands you found online that
mention `--force`. Nothing is ever lost until someone force-pushes.

## Rules

1. Never push to `main`. Ever. Branch protection will block it anyway.
2. Never commit `.env` or an API key.
3. Never merge with red CI.
4. Pull `main` before starting anything new.
5. Keep pull requests small. A 200-line PR gets a real review; a 2,000-line one
   gets a rubber stamp.

## Build order

Build a thin slice that works end to end before building anything wide. A demo
where one thing works completely beats four half-finished features.

**Phase 1 — the skeleton (must work).**
Upload a PDF → chunk → embed → store → ask a question → get a grounded answer
with sources. Ugly UI is fine. This is the whole project; everything else is
decoration.

**Phase 2 — make it feel like Nibble.**
Real design system, mascot in the loading and empty states, chat history that
survives a refresh, summaries.

**Phase 3 — the fun features, in this order.**
1. **Nibble's personality** — mostly prompt engineering, almost free.
2. **Quiz battles + leaderboard** — plain frontend and backend logic, no AI
   needed beyond generating questions from chunks you already have.
3. **Knowledge map** — needs topic tagging on top of chunks. Genuinely hard.
   Present it as a planned next step, not a promise.

**Do not start phase 2 until phase 1 works.**

## Weekly rhythm

- Monday: 20 minutes. What is everyone doing this week, what is blocked.
- Wednesday: everyone pushes something, even if unfinished. No week-long silence.
- Friday: demo whatever exists to each other. Ten minutes.

## When you are stuck

Try for 30 minutes. Then ask, and include: what you were trying to do, what you
ran, and the exact error text. Being stuck is normal; being stuck silently for
two days is the actual problem.
