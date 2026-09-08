# Putting Nibble on the internet

From nothing to a URL you can send someone. Like
[`first-week.md`](./first-week.md), this assumes you have never done it before.
If you get stuck following it, **the document is wrong** — fix it for the next
person.

Nibble deploys to two places, and it has to, because the two halves need
different things. [`adr/0003-hosting.md`](./adr/0003-hosting.md) is the full
reasoning; the short version is that the frontend is a folder of files and the
backend needs a real computer with a real disk.

| Half | Goes to | Why |
| --- | --- | --- |
| `frontend/` | Vercel | It is a pile of static files. This is what Vercel is for. |
| `backend/` | A Hugging Face Space | It needs a filesystem for `nibble.db` and room for the embedding model. |

**Everything below is free and none of it asks for a card.**

Do the backend first. The frontend needs the backend's address, and the backend
does not need the frontend's until the very end.

---

## Before you start

You need three accounts, all free: [Hugging Face](https://huggingface.co/join),
[Vercel](https://vercel.com/signup), and the project's existing
[Clerk](https://dashboard.clerk.com/) and [Groq](https://console.groq.com/keys)
logins. Ask Alif for the Clerk and Groq ones rather than making new ones — a new
Clerk application means new keys and a different set of users.

---

## Part 1 — the backend, on a Hugging Face Space

### 1. Make the Space

On <https://huggingface.co/new-space>:

- **Space name:** `nibble-api`
- **License:** whatever you like
- **SDK:** **Docker** → **Blank**
- **Hardware:** CPU basic (free)
- **Visibility:** Public

Create it. You get an empty repository and a page that says it is not running
yet. That is expected — nothing has been pushed.

### 2. Give it the settings it needs

Still on the Space, go to **Settings → Variables and secrets**. Add these.
"Secret" and "Variable" are different buttons; the difference is that a secret
is hidden after you save it.

| Name | Kind | Value |
| --- | --- | --- |
| `GROQ_API_KEY` | Secret | The key from your `.env` |
| `CLERK_ISSUER` | Variable | Clerk dashboard → API keys → **Frontend API URL** |
| `CORS_ORIGINS` | Variable | Leave this until Part 3 — you do not know it yet |

`CLERK_ISSUER` looks like `https://something-12.clerk.accounts.dev`. It is not a
secret, but the backend refuses to start without it, on purpose: see
[`config.py`](../backend/app/config.py).

### 3. Push the backend to it

A Space is a git repository, so this is `git push` to a second remote. From the
project folder:

```bash
git remote add space https://huggingface.co/spaces/YOUR-USERNAME/nibble-api
git subtree push --prefix backend space main
```

`git subtree push --prefix backend` is the interesting part. The Space needs
`backend/` to be at the *top* of its repository — its `Dockerfile` and its
`README.md` have to be at the root — but in our repository they are one folder
down. This pushes just that folder, with its contents lifted to the top, and
leaves our repository exactly as it was.

You will be asked for a username and password. The password is **not** your
Hugging Face password — it is an access token from
<https://huggingface.co/settings/tokens>, created with **Write** permission.

### 4. Watch it build

Back on the Space page, open the **Logs** tab. The first build takes several
minutes, most of it installing `onnxruntime` and downloading the embedding
model — the `Dockerfile` does that on purpose so the running app never has to.

When it finishes, the Space says **Running**. Its address is

```
https://YOUR-USERNAME-nibble-api.hf.space
```

**Check it worked:** open `https://YOUR-USERNAME-nibble-api.hf.space/health`.
You should see `{"status":"ok"}`. Write that address down; the frontend needs it
next.

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
| `VITE_API_URL` | Your Space address, no trailing slash |
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

Space → **Settings → Variables and secrets** → set `CORS_ORIGINS`:

```
http://localhost:5173,https://nibble-xxxx.vercel.app
```

Both, comma-separated, **no trailing slashes**. Keep localhost in the list so
the deployed backend still works while you develop against it.

Changing a variable restarts the Space. Wait for **Running** again.

### 2. Tell Clerk about the frontend

Clerk dashboard → your application → **Domains**, and add the Vercel address.
Without this, Clerk refuses to load on the deployed site and the page stays
blank — which looks like a broken build and is not one.

---

## Check it actually works

Not "it loaded". These four, in order:

- [ ] `https://your-space.hf.space/health` returns `{"status":"ok"}`
- [ ] The Vercel site loads and shows the sign-in button
- [ ] Signed in, you can upload a note, search it, and ask a question about it
- [ ] **In a private window, sign in as a different account.** You should see an
      empty Nibble — none of the first account's notes. This is the whole point
      of the auth work in Slice 4.5, and it is the one check that cannot be done
      on one laptop.

---

## Things that will happen, and what they mean

**"The first question takes forever."** A free Space goes to sleep after about
48 hours with no visitors, and waking up takes a minute. Open the site before a
demo starts, not during it.

**"All my notes are gone."** A free Space has no permanent disk, so `nibble.db`
starts empty again whenever the Space restarts or rebuilds — including every
time you push. Re-upload. This is a known, accepted trade, written down in
`adr/0003-hosting.md`, and the honest answer if somebody asks about it at the
demo.

**"It says I am not signed in, on every single request."** `CLERK_ISSUER` on the
Space does not match the Clerk application the frontend is using. They have to be
the same Clerk application.

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
- **Backend:** `git subtree push --prefix backend space main` again. The Space
  rebuilds, and the database starts empty.
