# Your first week

For Fahim and Arman. Written assuming you have never used a terminal. Nothing
here is obvious, and nobody is born knowing it — work top to bottom and ask when
you're stuck.

After every step there is a **Check** telling you how to know it worked. Do the
check. Half of all setup pain comes from something failing quietly three steps
back.

---

## 1. Install four things

| What | Where | Why |
|---|---|---|
| **Git** | <https://git-scm.com/downloads> | Shares code between the three of us |
| **Python 3.12+** | <https://www.python.org/downloads/> | The backend is written in it |
| **Node 22+** | <https://nodejs.org/> | Runs the frontend |
| **VS Code** | <https://code.visualstudio.com/> | Where you write code |

> **Windows, installing Python:** on the very first screen of the installer,
> tick **"Add python.exe to PATH"** before clicking anything else. If you miss
> it, the terminal won't find Python later and the error won't mention this.

**Check.** Open a terminal (in VS Code: `Terminal → New Terminal`) and run these
three, one at a time:

```bash
git --version
python --version
node --version
```

Three version numbers means you're fine. `command not found` or
`'python' is not recognized` means that one didn't install properly — redo it,
then **close and reopen the terminal** (it only reads the PATH at startup).

---

## 2. Get the code

```bash
git clone https://github.com/ameerul-muminin/nibble.git
cd nibble
```

**Check.** `ls` (or `dir` on Windows) lists `backend`, `frontend`, `docs`.

---

## 3. Set up the backend

From inside the `nibble` folder:

```bash
cd backend
python -m venv .venv
```

That makes a private box for this project's Python packages, so installing
something here can never break another project. Now switch into it:

```bash
# Windows (PowerShell)
.venv\Scripts\activate

# Mac / Linux
source .venv/bin/activate
```

**Check.** Your prompt now starts with `(.venv)`. **If it doesn't, stop — the
next command will install into the wrong place.**

> You must run the activate command **every time you open a new terminal**. It
> is the single most commonly forgotten step in this project. Symptom:
> `ModuleNotFoundError: No module named 'fastapi'`.

Now install everything:

```bash
pip install -e ".[dev]"
```

Takes a few minutes the first time. Then make your settings file:

```bash
# Windows
copy .env.example .env

# Mac / Linux
cp .env.example .env
```

You can leave it empty for now. Everything works without it **except reading
handwriting** — a scanned PDF or a photo of your notes needs the Groq key,
because it is a picture and has to be read by a vision model rather than
extracted. Typed PDFs, `.txt` and `.md` never touch it. Slice 4 needs it too.

The key is free and does not ask for a card: <https://console.groq.com/keys>

**Check.**

```bash
pytest -q
```

Two passing tests.

---

## 4. Set up the frontend

Open a **second** terminal, and from the `nibble` folder:

```bash
cd frontend
npm install
```

Then make your settings file, the same way you did for the backend:

```bash
# Windows
copy .env.example .env.local

# Mac / Linux
cp .env.example .env.local
```

This one you **cannot** leave empty. Open `.env.local` and paste the Clerk
publishable key next to `VITE_CLERK_PUBLISHABLE_KEY=`. Ask Alif for it.

Without that key the page does not draw at all — you get a Clerk error instead
of Nibble, because the sign-in wrapper refuses to start without it. If that is
what you are looking at, this is why.

**Check.** A `node_modules` folder appears. Never open it. Never commit it.

---

## 5. Run the whole thing

You need **two terminals running at the same time**, and they both stay running.
This surprises people — you don't get your prompt back, and that's correct.

**Terminal 1 — the backend:**

```bash
cd backend
.venv\Scripts\activate        # Mac/Linux: source .venv/bin/activate
uvicorn app.main:app --reload
```

**Check.** Open <http://localhost:8000/health>. You should see `{"status":"ok"}`.

**Terminal 2 — the frontend:**

```bash
cd frontend
npm run dev
```

**Check.** Open <http://localhost:5173>. Nibble appears and says
**"Backend is up. Nibble is ready to learn."**

If it says it can't reach the backend, terminal 1 isn't running. That message is
telling you the truth.

`--reload` and `npm run dev` both watch your files: save, and the change appears
immediately. You almost never need to restart either one.

---

## 6. The six commands you'll actually use

```bash
git status                       # what have I changed?
git checkout -b feat/my-thing    # start a new piece of work
git add .                        # mark everything I changed
git commit -m "add page numbers" # save it, with a note
git push -u origin feat/my-thing # send it to GitHub
git checkout main && git pull    # get everyone else's latest work
```

---

## 7. How to actually do a task

1. **Start fresh.** `git checkout main` then `git pull`.
2. **Make a branch.** `git checkout -b feat/upload-button`.
   `feat/` for new things, `fix/` for bugs, `docs/` for writing.
3. **Write the code.** Small steps. Check the page after each one.
4. **Check it yourself** before anyone else sees it:
   - backend: `ruff format .` then `ruff check .` then `pytest -q`
   - frontend: `npm run lint`
5. **Commit and push**, using the commands above.
6. **Open a pull request** on GitHub. Fill in the template honestly — especially
   *"explain how it works in your own words"*. That section is the actual point
   of this project.
7. **Wait for the green tick**, then for Alif's review.

---

## 8. When something goes wrong

Read the error. Real advice, not a platitude: the last line usually says exactly
what's wrong. Then check this list.

**`git push` was rejected, something about "protected branch"**
You're on `main`. Nobody can push to `main`, including Alif — that's deliberate,
so nothing can break for everyone at once. Make a branch:
`git checkout -b feat/my-thing` and push that.

**`ModuleNotFoundError: No module named 'fastapi'`**
You forgot to activate the virtual environment in this terminal. Go back to
step 3.

**`'python' is not recognized` / `command not found`**
Either it isn't installed, or you didn't tick "Add to PATH", or you haven't
reopened the terminal since installing.

**CI is red and the error is about formatting or lint**
This is normal and it happens to everyone. Run `ruff format .` (backend) or
`npm run lint` (frontend), commit the result, and push again. The robot cares
about spacing; it is not judging you.

**The page loads but nothing happens, and the browser console mentions CORS**
The backend has a list of who's allowed to call it, in `backend/app/config.py`.
If you changed the frontend's port, add the new one there.

**Port already in use**
An old server is still running from earlier. Close the other terminal, or
restart your computer if you can't find it.

**`sqlite3.OperationalError: no such table`**
The database file is out of date. Delete `backend/nibble.db` and restart the
backend — it will rebuild it empty.

**Still stuck after 30 minutes?**
Ask. Post three things: what you were trying to do, the exact command you ran,
and the **full** error text — screenshot or copy-paste, not a summary. Being
stuck is normal. Being stuck silently for two days is the actual problem.

---

## 9. About using AI

Use it. It's a good teacher and nobody is pretending otherwise.

The one rule: **don't merge code you can't explain.** The pull request template
asks you to describe how your change works in your own words, and Alif will ask
you one question about it in review. If you can't answer, that's not a telling-off
— it just means go back and read it until you can, and ask the AI to explain it
rather than to write more.

A good habit: after AI writes something, delete it and write it again yourself
from memory. You'll find out fast how much you actually absorbed.
