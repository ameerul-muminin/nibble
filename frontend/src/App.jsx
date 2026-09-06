/**
 * The whole app, for now.
 *
 * Slice 0 does exactly one thing: ask the backend whether it is awake, and say
 * so on screen. That sounds trivial, but it proves the hardest part of any web
 * app is working — two separate programs, talking to each other.
 *
 * Later slices grow this file: uploading notes, listing them, searching, and
 * finally chatting with Nibble.
 */

import { useEffect, useRef, useState } from 'react'
import { Show, SignInButton, SignUpButton, UserButton } from '@clerk/react'
import { deleteDocument, getHealth, listDocuments, uploadDocument } from './api'
import { Mascot } from './components/Mascot'
import './styles/global.css'

// What we say for each state. Errors tell you what to DO, never just "error".
const MESSAGES = {
  checking: 'Looking for the backend…',
  up: 'Backend is up. Nibble is ready to learn.',
  down: 'Can’t reach the backend. Open a second terminal, go to the backend folder, and run: uvicorn app.main:app --reload',
}

export default function App() {
  // useState remembers a value between redraws. Calling setStatus tells React
  // the value changed, and React redraws whatever uses it.
  const [status, setStatus] = useState('checking')

  // useEffect with an empty list at the end runs once, right after the page
  // first appears. Asking the backend for things belongs here.
  useEffect(() => {
    getHealth()
      .then(() => setStatus('up'))
      .catch(() => setStatus('down'))
  }, [])

  // -------------------------------------------------------------------------
  // Slice 1 — issues #5 and #7
  //
  // Everything below this line is scaffolding: the layout, the classes and the
  // hidden-file-input plumbing are done, and each piece of behaviour is a TODO.
  // Work down them in order; each one is small on its own.
  // -------------------------------------------------------------------------

  // The list of notes. It starts as an empty array rather than null, so the
  // rendering code below can always call .map on it without checking first.
  const [docs, setDocs] = useState([])

  // Three separate small states rather than one big one, because they change
  // at different times and mixing them makes it harder to see what is going on.
  const [docsStatus, setDocsStatus] = useState('loading') // loading | ready | failed
  // True while an upload is in flight. A typed file is instant; a scan or a
  // photo goes to the vision model a page at a time and takes seconds, which
  // is why the button says "Reading…" rather than nothing at all.
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState(null) // a plain sentence, or null

  // A ref is a handle onto a real DOM element. This one lets the visible button
  // below click the invisible file input for us. Built for you — it is the
  // fiddly bit, and it is the same three lines in every React app.
  const fileInput = useRef(null)

  // Bumping this re-runs the load below. It is how the "Try again" button on
  // the failed state works: change the value, the effect runs again.
  const [reloadKey, setReloadKey] = useState(0)

  // Load the notes. This is the one place that REPLACES the whole list rather
  // than adjusting it, which makes it the one place that can throw away a
  // change made while it was still in flight.
  //
  // `ignore` is the guard against that. When this effect is torn down — or run
  // again — the old request is still out there and will still resolve, and
  // without the flag its rows would land on top of whatever happened since.
  // React's StrictMode runs every effect twice in development on purpose, to
  // make exactly this bug show up on a laptop rather than in front of an
  // audience. The cleanup function marks the old run as stale, so only the
  // newest one is allowed to write anything.
  useEffect(() => {
    let ignore = false
    setDocsStatus('loading')

    listDocuments()
      .then((rows) => {
        if (ignore) return
        setDocs(rows)
        setDocsStatus('ready')
      })
      .catch(() => {
        if (ignore) return
        setDocsStatus('failed')
      })

    return () => {
      ignore = true
    }
  }, [reloadKey])

  /** #5 — runs when a file has been chosen in the hidden input. */
  async function handleFileChosen(event) {
    const file = event.target.files[0]
    if (!file) return

    // Clearing the input's value means picking the SAME file twice in a row
    // still fires this. Without it, the second pick does nothing and looks
    // broken. Built for you because it is pure trivia, not a React idea.
    event.target.value = ''

    setBusy(true)
    setNotice(null)
    try {
      const created = await uploadDocument(file)

      // The new note goes at the FRONT, because the backend returns newest
      // first and the screen should agree with it.
      //
      // setDocs is given a FUNCTION rather than a value. Written as
      // setDocs([created, ...docs]), `docs` would be the list as it was when
      // this upload started — so a delete that finished while the upload was
      // in flight would be undone, and the deleted note would reappear. The
      // function form is handed the list as it is right now instead.
      //
      // Either way it builds a NEW array rather than calling push(). React
      // only redraws when it sees a different value, and push() changes the
      // old array in place, so the note would be in the list and never show.
      setDocs((current) => [created, ...current])
    } catch (error) {
      // The backend already writes a plain sentence for anything a person
      // caused, and it is more useful than anything guessable here — it says
      // whether the file was the wrong type, unreadable, or too long. Fall
      // back to a generic line only if there was no sentence to show.
      setNotice(
        error.message ||
          'That upload did not work. Check it is a PDF, TXT, MD or a photo, under 20 MB.',
      )
    } finally {
      setBusy(false)
    }
  }

  /** #7 — runs when the X on a row is clicked. */
  async function handleDelete(id) {
    setNotice(null)
    try {
      await deleteDocument(id)

      // Same function form as the upload, and for the same reason: delete two
      // notes quickly and the second one would otherwise filter the list as it
      // was before the first finished, putting the first note back on screen.
      //
      // filter returns a new array and leaves the old one alone, which is what
      // React wants — the same "a new value, not a changed one" idea as above.
      setDocs((current) => current.filter((d) => d.id !== id))
    } catch {
      setNotice('Could not delete that note. Try again in a moment.')
    }
  }

  return (
    <main style={{ maxWidth: 620, margin: '0 auto', padding: 'var(--gap-xl) var(--gap-lg)' }}>
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--gap)',
          marginBottom: 'var(--gap-lg)',
        }}
      >
        <Mascot size={80} mood={status === 'checking' ? 'thinking' : 'idle'} />
        <div>
          <h1>Nibble</h1>
          <p style={{ margin: 0, color: 'var(--text-muted)' }}>
            Bite-sized answers from your own notes
          </p>
        </div>

        {/*
          Show picks one branch based on whether somebody is signed in. Clerk
          knows the answer because ClerkProvider wraps the whole app in main.jsx.
          marginLeft: 'auto' pushes this cluster to the right-hand end of the row.
        */}
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 'var(--gap-sm)' }}>
          <Show when="signed-out">
            <SignInButton mode="modal" />
            <SignUpButton mode="modal" />
          </Show>
          <Show when="signed-in">
            <UserButton />
          </Show>
        </div>
      </header>

      <section className="card">
        <h2 style={{ marginBottom: 'var(--gap-sm)' }}>Slice 0 — is everything talking?</h2>

        <p style={{ margin: 0 }}>{MESSAGES[status]}</p>

        <p style={{ marginBottom: 0, color: 'var(--text-muted)' }}>
          {status === 'up'
            ? 'Next up: Slice 1, uploading a PDF.'
            : 'This page asks the backend for /health when it loads.'}
        </p>
      </section>

      {/*
        Slice 1 — your notes. Issues #5 (list and upload) and #7 (delete).
        The layout, classes and file-input plumbing are built; the behaviour
        is marked TODO in the handlers above.
      */}
      <section className="card" style={{ marginTop: 'var(--gap-lg)' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 'var(--gap)',
            marginBottom: 'var(--gap)',
          }}
        >
          <h2 style={{ margin: 0 }}>Your notes</h2>

          {/*
            The real file input is hidden, because a raw one cannot be styled
            and looks nothing like the rest of the page. The button below is
            what people see, and clicking it clicks this through the ref.
          */}
          <input
            type="file"
            ref={fileInput}
            hidden
            accept=".pdf,.txt,.md,.png,.jpg,.jpeg,.webp"
            onChange={handleFileChosen}
          />

          <button
            type="button"
            className="btn btn--primary"
            style={{ marginLeft: 'auto' }}
            disabled={busy || docsStatus !== 'ready'}
            onClick={() => fileInput.current.click()}
          >
            {busy ? 'Reading…' : 'Add a note'}
          </button>
        </div>

        {/* One plain sentence when something went wrong. Never a raw error. */}
        {notice && (
          <p role="status" style={{ color: 'var(--danger, #b3261e)' }}>
            {notice}
          </p>
        )}

        {docsStatus === 'loading' && (
          <p style={{ color: 'var(--text-muted)' }}>Fetching your notes…</p>
        )}

        {/*
          A failed load used to be a dead end: the upload button stays disabled
          until the list is known, and nothing here offered a way to try again,
          so one dropped request meant a page refresh. This retries in place.
        */}
        {docsStatus === 'failed' && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--gap)' }}>
            <p style={{ color: 'var(--text-muted)', margin: 0 }}>
              Could not load your notes. Check the backend is running.
            </p>
            <button
              type="button"
              className="btn btn--secondary"
              onClick={() => setReloadKey((n) => n + 1)}
            >
              Try again
            </button>
          </div>
        )}

        {/*
          The empty state. Worth having from the start: the very first thing
          anybody sees when they open Nibble is this, not a list.
        */}
        {docsStatus === 'ready' && docs.length === 0 && (
          <p style={{ color: 'var(--text-muted)', marginBottom: 0 }}>
            Nothing here yet. Add a chapter and Nibble will read it.
          </p>
        )}

        {docsStatus === 'ready' && docs.length > 0 && (
          <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
            {/*
              One <li> per document. Every row needs key={doc.id}: React uses
              the key to tell rows apart between redraws, and without it,
              deleting the middle row can leave the wrong one on screen. The
              database id is a perfect key — never the array index, which
              changes the moment something is removed.
            */}
            {docs.map((doc) => (
              <li
                key={doc.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 'var(--gap-sm)',
                  padding: 'var(--gap-sm) 0',
                  borderBottom: '2px solid var(--border, #eee)',
                }}
              >
                <span style={{ flex: 1 }}>{doc.filename}</span>
                <span style={{ color: 'var(--text-muted)' }}>
                  {doc.page_count} {doc.page_count === 1 ? 'page' : 'pages'}
                </span>
                <button
                  type="button"
                  className="btn btn--secondary"
                  aria-label={`Delete ${doc.filename}`}
                  onClick={() => handleDelete(doc.id)}
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  )
}
