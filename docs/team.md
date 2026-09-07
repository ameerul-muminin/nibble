# How we work

## Who owns what

Ownership is by **folder**, not by feature. Two people editing the same file is
where merge conflicts and bad feelings come from.

| Person | Owns | Never edits without asking |
|---|---|---|
| Fahim (backend) | `backend/app/routes.py`, `backend/tests/` | `frontend/` |
| Arman (frontend) | `frontend/src/`, `assets/` | `backend/` |
| Alif (tech lead) | `backend/app/db.py`, `embeddings.py`, `llm.py`, `config.py`, `docs/`, `.github/`, reviews every PR | — |

The split inside `backend/` is deliberate. Routes follow a repeating pattern, so
each one is a little easier than the last — that's the learning path. The three
engine modules have non-obvious failure modes (threading, model loading, network
errors), so Alif absorbs those and nobody sits blocked on them.

`docs/api.md` is the contract. **Alif writes the entry there before either side
starts a slice**, so both can build at the same time without waiting.

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

We build in **vertical slices**. Every slice ends in something you could demo
that day — never a half-finished layer. A demo where one thing works completely
beats four things that half work.

**What each slice is, and how far along it is, lives in
[`scope.md`](./scope.md).** It used to be listed here too, and that copy went
stale — it still had a tick against slice 0 long after slices 1 and 1.5 had
merged, and it never learned slice 1.5 existed at all. Status kept in three
places is status kept in none of them, so this file no longer keeps it.

Where to look, in order: **GitHub is the truth for status** — an issue is done
when it is closed. `scope.md` is the truth for *why* something was built the way
it was. This file is the truth for how we work together.

Each slice is a GitHub milestone, and each task in it is an issue assigned to
one person. Take the next issue in the current milestone; don't skip ahead.

**Finish a slice before starting the next one.** The point of the ordering is
that the demo is safe from the end of slice 4 — everything after that is polish
we can drop if time runs out.

## Using AI

Use it. It's a good teacher and nobody is pretending otherwise.

The one rule: **don't merge code you can't explain.** Every pull request asks you
to describe your change in your own words, and the reviewer asks one question
about it. Can't answer it? That's not a telling-off — go back and read your own
change until you can, and ask the AI to *explain* rather than to write more.

## Weekly rhythm

- Monday: 20 minutes. What is everyone doing this week, what is blocked.
- Wednesday: everyone pushes something, even if unfinished. No week-long silence.
- Friday: demo whatever exists to each other. Ten minutes.

## When you are stuck

Try for 30 minutes. Then ask, and include: what you were trying to do, what you
ran, and the exact error text. Being stuck is normal; being stuck silently for
two days is the actual problem.
