# ADR 0002 — One repository for frontend and backend

**Status:** accepted · **Date:** 2026-08-07 · **Decided by:** tech lead

## Context

Frontend and backend could live in two repositories or one.

## Decision

One repository, with `frontend/` and `backend/` as sibling folders. No monorepo
tooling (Turborepo, Nx) — plain folders and one CI file with two jobs.

## Why

A change to the API contract usually touches both sides. In one repository that
is a single pull request a reviewer can read end to end. Across two, it is two
PRs that have to merge in the right order, which is exactly the coordination
overhead a small team should avoid.

There is also only one place to clone, one README, one CI configuration, and one
place where issues live.

## Trade-offs accepted

- Frontend and backend deploy together, so a frontend-only change still runs the
  backend CI job. At our size this costs seconds, not minutes.
- If the project ever grew separate teams with separate release cadences, this
  would be worth revisiting. It will not, within this project's lifetime.
