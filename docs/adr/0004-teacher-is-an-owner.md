# ADR 0004 — A teacher is an owner, not a role

**Status:** accepted · **Date:** 2026-09-08 · **Decided by:** tech lead

## Context

Nibble is growing a classroom: a teacher generates a quiz from a chapter, opens a
room, students join with a code, and the teacher marks what comes back. The
landing page offers two doors — come in as a regular user, or as a teacher.

Two doors on a sign-in screen looks like a request for a role system, and that is
the trap. The requirement is explicitly that **anyone can be a teacher**. There is
no fixed admin account, no approval step, and nobody grants anybody anything. A
person is a teacher on Monday for the class they run and a student on Tuesday for
the class they sit in.

Meanwhile `db.py` already carries a promise about how this project stores people:

> There is no `users` table and no foreign key to one. Clerk owns the people; we
> only ever hold the id, so a second table would be a copy of someone else's data
> that we would then have to keep in step.

Any role system reopens that.

## Decision

- **A teacher is someone who owns a room.** `rooms.owner_id` holds a Clerk `sub`,
  exactly as `documents.user_id` already does.
- **A student is someone with a row in `room_members`.** Nothing else.
- **The two buttons on the landing page are navigation, not permission.** They
  choose which screen you land on. They grant nothing, they are never sent to the
  backend, and the backend would ignore them if they were.
- **Authority is always a `WHERE owner_id = ?` in SQL**, in the route that needs
  it, the same way every existing route already scopes to `user_id`.
- **No `users` table, no `roles` table, no `role` column, no allowlist, and no
  Clerk dashboard configuration.**

## Why

**It reuses the one idea this codebase already has.** Ownership as a column
holding a Clerk `sub` appears in five places today. A sixth is not a new concept
for anybody to learn — it is the same sentence about a different noun, and that is
the whole test in `CLAUDE.md`: can the person who owns this file explain it at the
demo?

**It cannot be forged.** This is the part worth being precise about, because it is
where a role system would have gone quietly wrong. If "am I a teacher?" were a
value the browser sent — a header, a field in a request body, a claim the frontend
put there — then a student could send it too. Nothing about a button on a landing
page is a security boundary. Deriving authority from a row we wrote ourselves, and
checking it in the same query that fetches the data, means there is no request a
student can construct that makes them the teacher of somebody else's room.

**It matches what was actually asked for.** "Anyone can be a teacher" *is* "there
is no role". Building a role system to express the absence of roles would be
machinery in the shape of its own opposite.

**Nobody is locked in.** Because the door is only navigation, a student can join a
class from inside the regular app and a teacher can quiz himself from his own
notes. A role column would have had to allow both anyway, at which point it is
storing something that never says no.

## Why not an allowlist in `config.py`

`TEACHER_USER_IDS` as one comma-separated environment variable, read the way
`CORS_ORIGINS` already is. It is genuinely cheap — one setting, one check — and it
gives you a literal "admin" to point at.

Rejected because it answers a question nobody asked. It makes teaching something
granted rather than something done, so adding a teacher means editing `.env` and
restarting the backend, and on the deployed Space that is a redeploy. For a demo
where the audience may want to try being a teacher, it is precisely the wrong
shape.

## Why not a `role` claim in Clerk's session token

Set `role: "teacher"` on the user's public metadata, add a Clerk JWT template so
the claim rides in the session token, and read it in `auth.py` next to `sub`.

This is the most "real" of the options and it is the one to reach for if Nibble
ever needs an actual administrator — somebody who can act across other people's
data. Rejected here for three reasons: it puts configuration outside the repository
that every developer and the deployed app must set up identically and that no test
can see; it adds a second claim to `auth.py`, whose whole virtue today is that it
reads exactly one; and it still would not answer the real question, which is not
"is this person a teacher" but "is this person the teacher **of this room**".

## Why not a local roles table

A `user_roles` table would be the first record of a human being in our database,
and it directly contradicts the reasoning already written into the schema. It also
carries a synchronisation problem the current design does not have: a row that says
somebody is a teacher outlives the account being deleted in Clerk, and nothing
would ever tell us.

## Trade-offs accepted

- **There is no way to stop somebody creating a room.** Any signed-in person can.
  On a free demo backend with no real data that is the intended behaviour, not a
  gap — but it is the first thing to revisit if Nibble is ever used by a real
  school, and the answer then is probably Clerk Organizations rather than a role
  column.
- **There is no administrator.** Nobody can see, moderate, or delete another
  person's room. If that is ever needed it is a new decision, and this ADR is the
  one to supersede.
- **"Teacher" is not a thing a person can be shown.** There is no badge, no
  profile, nothing to display, because there is nothing stored. The UI can only
  say "the rooms you run" and "the class you joined" — which is, on reflection,
  more accurate than a badge would have been.
