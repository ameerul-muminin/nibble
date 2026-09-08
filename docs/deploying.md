# Putting Nibble on the internet

From nothing to a URL you can send someone. Like
[`first-week.md`](./first-week.md), this assumes you have never done it before.
If you get stuck following it, **the document is wrong** — fix it for the next
person.

Nibble deploys to two places, and it has to, because the two halves need
different things. [`adr/0003-hosting.md`](./adr/0003-hosting.md) is why the
backend cannot go where the frontend goes, and
[`adr/0005-render.md`](./adr/0005-render.md) is why it goes to Render. The short
version is that the frontend is a folder of files and the backend needs a real
computer with a real disk.

| Half | Goes to | Why |
| --- | --- | --- |
| `frontend/` | Vercel | It is a pile of static files. This is what Vercel is for. |
| `backend/` | Render | It needs a filesystem for `nibble.db` and room for the embedding model. |

**Everything below is free and none of it asks for a card.**

Do the backend first. The frontend needs the backend's address, and the backend
does not need the frontend's until the very end.

---

## Before you start

You need two accounts, both free and neither asking for a card:
[Render](https://render.com/register) and [Vercel](https://vercel.com/signup).
You also need the project's existing [Clerk](https://dashboard.clerk.com/) and
[Groq](https://console.groq.com/keys) logins — ask Alif for those rather than
making new ones, because a new Clerk application means new keys and a different
set of users.

> **This used to say Hugging Face.** A free Docker Space was the plan until
> Hugging Face made the Docker SDK a paid feature in July 2026, with no
> announcement. Everything in this project is free, so the backend moved to
> Render. [`adr/0005-render.md`](./adr/0005-render.md) is the reasoning, and it
> is worth two minutes before you start — it explains the one thing about the
> free tier that will surprise you.

---

## Part 1 — the backend, on Render

### 1. Push your branch first

Render builds from GitHub, so it can only deploy code that is on GitHub. Make
sure the backend is merged into `main` before you start, or Render will
cheerfully build an older version and you will spend twenty minutes wondering
why your changes are not there.

### 2. Make the web service

On <https://dashboard.render.com/> choose **New → Web Service**, connect your
GitHub account, and pick the Nibble repository.

Then change these, because the defaults are wrong for this repository:

- **Language / Runtime:** **Docker**. Render will probably guess Python and try
  to install from a `requirements.txt` we do not have.
- **Root Directory:** `backend` — this is the one everybody misses. Without it
  Render looks for a `Dockerfile` at the top of the repository, does not find
  one, and fails.
- **Instance Type:** **Free**.
- **Name:** `nibble-api`, which gives you `https://nibble-api.onrender.com`.
  If somebody has taken that name you get a different one; write down whatever
  you actually get, because the frontend needs it.

Do **not** deploy yet. Add the settings first, or the first build starts, fails
on a missing `CLERK_ISSUER`, and you wait through it twice.

### 3. Give it the settings it needs

On the same screen, open **Environment Variables** and add these:

| Name | Value |
| --- | --- |
| `GROQ_API_KEY` | The key from your `.env` |
| `CLERK_ISSUER` | Clerk dashboard → API keys → **Frontend API URL** |
| `CORS_ORIGINS` | Leave this until Part 3 — you do not know it yet |

`CLERK_ISSUER` looks like `https://something-12.clerk.accounts.dev`. It is not a
secret — it is inside every token any browser holds — but the backend refuses to
start without it, on purpose: see [`config.py`](../backend/app/config.py).

**Do not set `PORT`.** Render sets it itself, and the
[`Dockerfile`](../backend/Dockerfile) reads it.

### 4. Watch it build

Now deploy, and open the **Logs** tab. The first build takes several minutes,
most of it installing `onnxruntime` and downloading the embedding model — the
`Dockerfile` does that at build time on purpose, so the running app never has to.

When it finishes, the service says **Live**.

**Check it worked:** open `https://nibble-api.onrender.com/health`. You should
see `{"status":"ok"}`. Write that address down; the frontend needs it next.

### 5. The one check nobody has done yet

Render's free tier gives this service **0.1 of a CPU**, and every timing in this
project was measured on a laptop. Nobody has yet measured how slow embedding is
on a fraction of a shared core.

So before you rely on it: sign in, **upload one real chapter, and time it.** A
30-page PDF should take seconds, not minutes. If it is unusable, say so — it is
recorded as an open risk in
[`adr/0005-render.md`](./adr/0005-render.md), and the fallback written down there
is running the backend on a laptop behind a free `cloudflared` tunnel.

---

## Part 2 — the frontend, on Vercel

### 1. Import the repository

On <https://vercel.com/new>, pick the Nibble repository. Vercel will guess how
to build it, and it will guess wrong, because our frontend is not at the top of
the repository.

Change these two:

- **Root Directory:** `frontend` — this is the one everybody misses. Without it
  Vercel looks for `package.json` at the top, does not find one, and fails.
- **Framework Preset:** Vite (it usually detects this once the root is right)

### 2. Environment variables

Still on the import screen, add both:

| Name | Value |
| --- | --- |
| `VITE_API_URL` | Your Render address, no trailing slash |
| `VITE_CLERK_PUBLISHABLE_KEY` | The same one in your `frontend/.env.local` |

Both start with `VITE_` because Vite only passes variables into the browser
bundle if they do. Both are safe in a browser; nothing secret goes here, and a
Clerk **secret** key must never be one of these.

Deploy. You get an address like `https://nibble-xxxx.vercel.app`.

---

## Part 3 — introduce them to each other

The site is up and **nothing works yet**. Open it and the browser console shows
a CORS error. That is correct and expected: the backend has never heard of this
address, and a browser will not let a page call a server that has not said it is
allowed to.

Two things left.

### 1. Tell the backend about the frontend

Render dashboard → your service → **Environment** → set `CORS_ORIGINS`:

```
http://localhost:5173,https://nibble-xxxx.vercel.app
```

Both, comma-separated, **no trailing slashes**. Keep localhost in the list so
the deployed backend still works while you develop against it.

Changing a variable redeploys the service. Wait for **Live** again.

### 2. Tell Clerk about the frontend — **only if you are on a production instance**

**On a development Clerk instance there is nothing to do here.** Development
instances are not domain-locked, so the Vercel address just works. This was
checked on 2026-09-08: the deployed site loaded and signed in with nothing added
to Clerk at all.

**You can tell which you are on by looking at the key you already have.** Open
`frontend/.env.local` — or the same variable in Vercel — and read the start of
`VITE_CLERK_PUBLISHABLE_KEY`:

| It starts with | You are on | What to do here |
| --- | --- | --- |
| `pk_test_` | a development instance | **Nothing. Skip to "Check it actually works".** |
| `pk_live_` | a production instance | Read the rest of this step |

No tool to install, and nothing to run. The prefix is the whole check, and it is
the same key that is already in front of you.

**On a production instance, you cannot use the `.vercel.app` address at all.**
This is the part worth reading slowly, because it is the opposite of what the
development instance taught you. A production Clerk instance is domain-locked to
a domain *you* own, and `nibble-xxxx.vercel.app` is Vercel's domain, not yours.
There is no field in Clerk you can paste it into that will work.

So on a production instance the order is:

1. **Buy a domain**, or use one you already own.
2. Add it to Vercel: project → **Settings** → **Domains**, and follow the DNS
   records it gives you.
3. Add that same domain to Clerk: dashboard → your application → **Domains**,
   and set the DNS records Clerk asks for.
4. Update `CORS_ORIGINS` on Render to the new address, and
   `VITE_API_URL` / `VITE_CLERK_PUBLISHABLE_KEY` on Vercel if they changed.

Until all of that is done, Clerk refuses to load and the page stays blank —
which looks like a broken build and is not one.

**Nibble does not have a real domain, so it runs on a development instance, and
that is a deliberate choice rather than an unfinished one.** Development
instances are not domain-locked, which is exactly why the free `.vercel.app`
address works. Everything above starts mattering the day somebody buys a domain,
and not before.

---

## Check it actually works

Not "it loaded". These four, in order:

- [ ] `https://nibble-api.onrender.com/health` returns `{"status":"ok"}`
- [ ] The Vercel site loads and shows the sign-in button
- [ ] Signed in, you can upload a note, search it, and ask a question about it
- [ ] **In a private window, sign in as a different account.** You should see an
      empty Nibble — none of the first account's notes. This is the whole point
      of the auth work in Slice 4.5, and it is the one check that cannot be done
      on one laptop.

---

## Things that will happen, and what they mean

**"The first question takes forever."** A free Render service goes to sleep
after **15 minutes** with no visitors, and waking up takes about 50 seconds.
That is much more often than it sounds — a quiet lunch break is enough. **Open
the site a minute before a demo starts**, not during it. This is the cost
[`adr/0005-render.md`](./adr/0005-render.md) accepted, and it is the thing about
the free tier most likely to embarrass you.

**"All my notes are gone."** A free Render service has no permanent disk, so
`nibble.db` starts empty again whenever the service restarts or redeploys —
including every time you merge to `main`, and every time it wakes from sleep.
Re-upload. This is a known, accepted trade, written down in
[`adr/0005-render.md`](./adr/0005-render.md), and the honest answer if somebody
asks about it at the demo.

**"It says I am not signed in, on every single request."** `CLERK_ISSUER` on the
Render service does not match the Clerk application the frontend is using. They
have to be the same Clerk application.

**"The page is completely blank."** Almost always the Vercel address missing from
Clerk's Domains list. Check the browser console.

**A CORS error in the console.** The Vercel address is not in `CORS_ORIGINS`, or
it is in there with a trailing slash. An origin is scheme + host + port and
nothing else, so `https://x.vercel.app/` does not match `https://x.vercel.app`.

**"It worked yesterday and today it 404s."** Vercel gives every deployment its
own address. The one that stays stable is the project's main domain — use that
when sending the link to anybody.

---

## Deploying again, after a change

- **Frontend:** merge to `main`. Vercel rebuilds on its own.
- **Backend:** merge to `main`. Render rebuilds on its own, the same as Vercel,
  because both are watching the branch. The database starts empty again.
