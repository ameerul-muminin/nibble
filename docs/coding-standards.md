# Coding standards

`CLAUDE.md` holds the rules and [`scope.md`](./scope.md) holds the reasoning and the
plan. This file is the mechanical layer between them: the exact commands, and which
rules a machine actually checks.

The split matters more than the list. **Green CI does not mean the standards were
met**, because most of what this project cares about — whether the person who wrote
the code can explain it — cannot be checked by a tool. Those rules live in their own
section below, and they are the ones that need a person.

## Two commands, one per side

This is one repository with two toolchains, so there is no single `check`. Run the
side you touched. Both must be green before a pull request is ready.

```bash
cd backend  && ruff check . && ruff format --check . && pytest -q
cd frontend && npm run lint && npm run build
```

That is exactly what CI runs, in the same order, so a green run locally means a green
run on GitHub.

### Backend

| Command                | What it does                            |
| ---------------------- | --------------------------------------- |
| `uvicorn app.main:app --reload` | Dev server                     |
| `ruff check .`         | Lint                                    |
| `ruff check --fix .`   | Lint, fixing what it safely can         |
| `ruff format .`        | Format, writes                          |
| `ruff format --check .`| Format, reports only — this is what CI runs |
| `pytest -q`            | Tests                                   |

### Frontend

| Command           | What it does                            |
| ----------------- | --------------------------------------- |
| `npm run dev`     | Dev server                              |
| `npm run lint`    | ESLint over `src`, zero warnings allowed |
| `npm run build`   | Real production build                   |
| `npm run preview` | Serve the built output                  |

**The build is not redundant with the lint.** ESLint reads one file at a time; `vite
build` resolves every import and fails on a path that does not exist. Anything that
only breaks when the whole app is assembled is invisible to the linter.

## CI, and the one thing not to touch

`.github/workflows/ci.yml` defines two jobs, `backend` and `frontend`. **Those two
names are wired into the branch protection ruleset as required checks. Renaming a job
silently switches protection off for that check.** Change the steps freely; leave the
names alone. There is a comment saying so at the top of the file.

Never merge with red CI. If CI is red for a reason you do not understand, that is a
question for the review thread, not a reason to merge and fix later.

## What the tools actually enforce

**Backend, ruff.** Line length 100, targeting Python 3.12, with rule sets `E`
(pycodestyle), `F` (pyflakes), `I` (import sorting), `UP` (pyupgrade) and `B`
(bugbear). Configured in `backend/pyproject.toml`, in one place, on purpose.

`I` means **imports are sorted by the tool, never by hand** — do not rearrange them
manually and do not argue with the result. `B` is the one that catches real bugs
rather than style: mutable default arguments, loop variables captured in closures,
`except` clauses that swallow everything.

**Frontend, ESLint.** `eslint src --max-warnings 0`, with the React and React Hooks
plugins. A warning is a failure here, deliberately — a warning nobody has to fix is a
warning everybody stops reading.

The hooks plugin is the one worth trusting. If it complains about a dependency array,
it is almost always right and the fix is almost never to silence it.

**The frontend has no formatter, and the backend does.** `ruff format` is enforced in
CI for Python; there is no Prettier for JavaScript, so JS formatting is whatever the
author's editor did. That asymmetry is a real gap, not a decision — it is listed as an
open question at the bottom of this file.

## What no tool can check, but which still holds

These are the ones that need a person, and they are the ones that matter most here.

**Can the owner explain it?** The rule that outranks everything. A pull request where
the author cannot answer one question about their own diff does not merge yet — not as
a punishment, but because the whole point of the project is that the team can present a
system they understand. Send it back kindly and specifically.

**One new idea at a time.** A task that already introduces three unfamiliar concepts
should not quietly acquire a fourth because it would be tidier. Tidier later is fine.

**Never trust a value that came from the client.** Filenames, paths, ids, sizes,
content types. `Path(filename).name` before writing an upload; parameterised SQL,
always, with no exceptions and no "it's just an integer".

**Errors reach the user as a sentence, not a stack trace.** A raw exception or a raw
provider error in the interface is a bug regardless of what caused it. Say what
happened in plain words and give a way to try again. The real detail goes to the
server log.

**Settings live in `backend/app/config.py`.** One place, read once. A missing required
setting fails loudly at startup, naming what is missing — never silently at the moment
someone uploads their first PDF.

**The embedding model loads once, at module level.** Never inside a request handler.

**`PRAGMA foreign_keys = ON` on every connection.** SQLite defaults it off, so a
cascade delete silently does nothing without it.

**Connections get closed in `finally`.** Every one, every path out of the function.

**`docs/api.md` and the code say the same thing.** The contract is written before a
slice starts. If they disagree, one of them is a bug — say which, and fix both.

**Keep pull requests small.** A 200-line PR gets a real review; a 2,000-line one gets a
rubber stamp. This is a standard, not a preference.

**Verify by running it.** A dev server and a real browser, or `curl`. Reading the code
and concluding it looks right is not verification, and it is the single most common way
something ships broken here.

## Deliberately not installed

Each of these has been considered and rejected. Do not add one to check that something
works; ask first if you think the decision is wrong.

- **Docker.** Docker Desktop on Windows was the biggest predictable time-sink for a
  beginner and bought nothing at this data size. SQLite is a file.
- **TypeScript.** A second language to learn on top of React, in a few weeks.
- **An ORM.** Plain SQL is readable and explainable; an ORM hides the thing being
  learned behind a second thing to learn.
- **Postgres and pgvector.** See
  [`adr/0001-sqlite-and-numpy.md`](./adr/0001-sqlite-and-numpy.md).
- **A browser automation framework.** Verification is a real browser, driven by a
  person, at this size.
- **Commitlint or conventional commits.** `docs/team.md` asks that a message finish the
  sentence "this commit will…". That is enough, and it is reviewed by a human anyway.
- **Type checking on Python (mypy, pyright).** Worth revisiting after the demo. Right
  now it would mean explaining type errors on top of everything else.

## Tests

`pytest`, in `backend/tests/`, running in CI on every pull request. This is the one
place the project does have an automated gate, and it exists because `chunk_text()` in
Slice 2 is exactly the kind of pure function where a test is faster than clicking
through the UI.

Write tests for pure functions — chunking, parsing, scoring. Do not chase coverage on
route handlers; a real request through a running server tells you more, faster.

There is no frontend test runner and none is planned before the demo.

## Open questions

- **No JavaScript formatter.** Python formatting is enforced and JavaScript formatting
  is not, so JS diffs carry editor noise. Adding Prettier to `frontend/` with a
  `format:check` step in the `frontend` CI job would close it. The cost is one more
  tool for a beginner to meet, and one more way for CI to go red on something that is
  not logic. Worth deciding before Slice 5, when the frontend grows the most.
- **A clean checkout has no single setup command.** Both sides install separately, and
  the steps live in [`first-week.md`](./first-week.md). Fine for three people; worth a
  script if the team grows.
